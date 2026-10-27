"""
Unit Tests for Resilient Outbound HTTP Client
---------------------------------------------
Tests cover:
1. Immediate success (1 attempt, 0 sleeps)
2. Network timeout transient failure with recovery
3. HTTP 503/502 transient failure with recovery
4. Exhaustion of all 4 attempts (1 initial + 3 retries)
5. Non-retryable 4xx client errors (400, 404) failing immediately without retry
6. Deterministic exponential backoff calculation and delay capping
"""

import httpx
import pytest

from app.resilience import (
    MaxRetriesExceededError,
    calculate_backoff_delay,
    call_with_retry,
)


def test_success_on_first_attempt():
    """Verify that a successful request succeeds on attempt 1 without sleeping."""
    recorded_sleeps = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "created", "id": 101})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    response, attempts = call_with_retry(
        client=client,
        method="POST",
        url="http://mock-service.local/api/tasks",
        sleep_func=recorded_sleeps.append,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "created"
    assert attempts == 1
    assert len(recorded_sleeps) == 0  # No retry sleeps needed


def test_transient_failure_then_success():
    """Verify that transient 503 and 502 errors trigger retries, succeeding on attempt 3."""
    recorded_sleeps = []
    attempt_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            return httpx.Response(503, text="Service Unavailable")
        elif attempt_count == 2:
            return httpx.Response(502, text="Bad Gateway")
        else:
            return httpx.Response(200, json={"status": "recovered"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    # Inject deterministic jitter: always returns exact upper bound
    response, attempts = call_with_retry(
        client=client,
        method="GET",
        url="http://mock-service.local/health",
        base_delay=1.0,
        jitter_func=lambda low, high: high,
        sleep_func=recorded_sleeps.append,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "recovered"
    assert attempts == 3
    assert len(recorded_sleeps) == 2  # Slept twice
    assert recorded_sleeps[0] == 1.0  # 1.0 * (2^0) = 1.0s
    assert recorded_sleeps[1] == 2.0  # 1.0 * (2^1) = 2.0s


def test_timeout_retry_then_success():
    """Verify that a transient ReadTimeout is caught and retried, succeeding on attempt 2."""
    recorded_sleeps = []
    attempt_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            raise httpx.ReadTimeout("Connection timed out after 2.0s", request=request)
        return httpx.Response(200, json={"status": "ok"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    response, attempts = call_with_retry(
        client=client,
        method="POST",
        url="http://mock-service.local/webhook",
        sleep_func=recorded_sleeps.append,
    )

    assert response.status_code == 200
    assert attempts == 2
    assert len(recorded_sleeps) == 1


def test_exhausted_attempts_raises_error():
    """Verify that continuous transient 503 errors exhaust all 4 attempts (1 initial + 3 retries)."""
    recorded_sleeps = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Overloaded")

    client = httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(MaxRetriesExceededError) as exc_info:
        call_with_retry(
            client=client,
            method="POST",
            url="http://mock-service.local/data",
            max_retries=3,
            sleep_func=recorded_sleeps.append,
        )

    assert exc_info.value.attempts == 4  # 1 initial + 3 retries
    assert exc_info.value.last_response.status_code == 503
    assert len(recorded_sleeps) == 3  # Slept 3 times between the 4 attempts


def test_non_retryable_400_error_does_not_retry():
    """Verify that semantic 400 Bad Request client errors fail immediately without wasteful retries."""
    recorded_sleeps = []
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(400, json={"detail": "Invalid task title length"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    response, attempts = call_with_retry(
        client=client,
        method="POST",
        url="http://mock-service.local/api/tasks",
        sleep_func=recorded_sleeps.append,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid task title length"
    assert attempts == 1  # Exactly 1 attempt
    assert call_count == 1
    assert len(recorded_sleeps) == 0  # No retries


def test_non_retryable_404_error_does_not_retry():
    """Verify that 404 Not Found returns immediately on attempt 1."""
    recorded_sleeps = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "Project not found"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    response, attempts = call_with_retry(
        client=client,
        method="GET",
        url="http://mock-service.local/projects/missing",
        sleep_func=recorded_sleeps.append,
    )

    assert response.status_code == 404
    assert attempts == 1
    assert len(recorded_sleeps) == 0


def test_backoff_delay_calculation_and_cap():
    """Verify that exponential backoff respects base delay, power of 2 growth, and maximum cap."""

    # Deterministic mock jitter: always return upper bound
    def max_jitter(low, high):
        return high

    # Attempt 0: 0.5 * (2^0) = 0.5s
    assert calculate_backoff_delay(0, base_delay=0.5, max_delay=3.0, jitter_func=max_jitter) == 0.5
    # Attempt 1: 0.5 * (2^1) = 1.0s
    assert calculate_backoff_delay(1, base_delay=0.5, max_delay=3.0, jitter_func=max_jitter) == 1.0
    # Attempt 2: 0.5 * (2^2) = 2.0s
    assert calculate_backoff_delay(2, base_delay=0.5, max_delay=3.0, jitter_func=max_jitter) == 2.0
    # Attempt 3: 0.5 * (2^3) = 4.0s -> Capped at max_delay 3.0s!
    assert calculate_backoff_delay(3, base_delay=0.5, max_delay=3.0, jitter_func=max_jitter) == 3.0
