import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fetchHealth, fetchTasks, API_BASE_URL } from './api'

describe('TaskFlow API Client Module', () => {
  beforeEach(() => {
    global.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('fetchHealth queries /health and returns parsed JSON', async () => {
    const mockHealth = { status: 'healthy', version: '1.0.0' }
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockHealth,
    })

    const result = await fetchHealth()

    expect(global.fetch).toHaveBeenCalledWith(`${API_BASE_URL}/health`)
    expect(result).toEqual(mockHealth)
  })

  it('fetchHealth throws an Error when the response is not ok', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
    })

    await expect(fetchHealth()).rejects.toThrow('HTTP 503 - Service Unavailable')
  })

  it('fetchTasks requests /api/v1/tasks without params', async () => {
    const mockData = { items: [], total: 0 }
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockData,
    })

    const result = await fetchTasks()

    expect(global.fetch).toHaveBeenCalledWith(`${API_BASE_URL}/api/v1/tasks`)
    expect(result).toEqual(mockData)
  })

  it('fetchTasks serializes query filters for status, priority, and search', async () => {
    const mockData = { items: [{ id: '1', title: 'Task 1' }], total: 1 }
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockData,
    })

    const result = await fetchTasks({ status: 'done', priority: 'high', search: 'login' })

    expect(global.fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/v1/tasks?status=done&priority=high&search=login`
    )
    expect(result).toEqual(mockData)
  })

  it('fetchTasks throws an Error when backend returns error response', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
    })

    await expect(fetchTasks({ status: 'invalid' })).rejects.toThrow('HTTP 400 - Bad Request')
  })
})
