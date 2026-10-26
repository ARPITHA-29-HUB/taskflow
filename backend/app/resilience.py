"""
TaskFlow Resilient HTTP Client Module
-------------------------------------
Implements an isolated, deterministic HTTP execution helper featuring:
- Strict per-attempt connection & read timeouts (2.0s default)
- Exponential backoff with jitter and delay capping
- Distinction between transient (retryable) and semantic (non-retryable) failures
- Injectable sleep and jitter functions for 100% deterministic unit testing
"""

import logging
import random
import time
from typing import Callable, Optional, Set
import httpx

logger = logging.getLogger("taskflow.resilience")
logger.setLevel(logging.INFO)

# Transient HTTP status codes representing temporary upstream unreachability/overload
RETRYABLE_STATUS_CODES: Set[int] = {502, 503, 504}

# Transient network exceptions suitable for retry
RETRYABLE_EXCEPTIONS = (
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.ConnectError,
    httpx.NetworkError,
)


class MaxRetriesExceededError(Exception):
    """Raised when an outbound HTTP request exhausts all allocated retry attempts."""

    def __init__(self, attempts: int, last_error: Optional[Exception] = None, last_response: Optional[httpx.Response] = None):
        self.attempts = attempts
        self.last_error = last_error
        self.last_response = last_response
        msg = f"Request failed after {attempts} attempts."
        if last_response is not None:
            msg += f" Last status: {last_response.status_code}"
        elif last_error is not None:
            msg += f" Last exception: {type(last_error).__name__}: {last_error}"
        super().__init__(msg)


def calculate_backoff_delay(
    attempt: int,
    base_delay: float = 0.5,
    max_delay: float = 5.0,
    jitter_func: Optional[Callable[[float, float], float]] = None,
) -> float:
    """Calculate exponential backoff delay with full jitter.
    
    Formula: delay = random.uniform(0, min(max_delay, base_delay * (2 ** attempt)))
    """
    if jitter_func is None:
        jitter_func = random.uniform

    exponential = min(max_delay, base_delay * (2 ** attempt))
    # Full jitter: uniformly distribute between 0 and the exponential cap
    return max(0.0, jitter_func(0.0, exponential))


def call_with_retry(
    client: httpx.Client,
    method: str,
    url: str,
    max_retries: int = 3,
    timeout: float = 2.0,
    base_delay: float = 0.5,
    max_delay: float = 5.0,
    sleep_func: Callable[[float], None] = time.sleep,
    jitter_func: Optional[Callable[[float, float], float]] = None,
    **kwargs,
) -> tuple[httpx.Response, int]:
    """Execute an outbound HTTP request with exponential backoff and jitter.
    
    Returns:
        tuple[httpx.Response, int]: The successful or final response and total attempts made.
    
    Raises:
        MaxRetriesExceededError: If all retry attempts are exhausted due to transient failures.
    """
    total_allowed_attempts = 1 + max_retries
    last_exception: Optional[Exception] = None
    last_response: Optional[httpx.Response] = None

    for attempt in range(total_allowed_attempts):
        attempt_number = attempt + 1
        is_last_attempt = (attempt_number == total_allowed_attempts)

        try:
            logger.info(f"[OUTBOUND HTTP] Attempt {attempt_number}/{total_allowed_attempts} -> {method.upper()} {url}")
            response = client.request(method, url, timeout=timeout, **kwargs)

            # 1. Non-retryable HTTP status check
            if response.status_code not in RETRYABLE_STATUS_CODES:
                # 2xx Success or 4xx Client Error (400, 401, 403, 404, 422) return immediately!
                return response, attempt_number

            # Transient 502/503/504 error
            last_response = response
            logger.warning(
                f"[TRANSIENT HTTP ERROR] Attempt {attempt_number} received status {response.status_code}."
            )

        except RETRYABLE_EXCEPTIONS as exc:
            # Transient Network or Timeout Error
            last_exception = exc
            logger.warning(
                f"[TRANSIENT NETWORK ERROR] Attempt {attempt_number} encountered {type(exc).__name__}: {exc}"
            )

        # If not the last attempt, calculate backoff delay and sleep
        if not is_last_attempt:
            delay = calculate_backoff_delay(
                attempt=attempt,
                base_delay=base_delay,
                max_delay=max_delay,
                jitter_func=jitter_func,
            )
            logger.info(f"[RETRY BACKOFF] Sleeping for {delay:.3f}s before next attempt...")
            sleep_func(delay)

    # Exhausted all attempts
    raise MaxRetriesExceededError(
        attempts=total_allowed_attempts,
        last_error=last_exception,
        last_response=last_response,
    )
