import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  fetchHealth,
  fetchProjects,
  fetchProjectById,
  fetchProjectSummary,
  fetchTasks,
  createTask,
  updateTask,
  deleteTask,
  API_BASE_URL,
} from './api'

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

  it('fetchProjects queries /api/v1/projects with pagination and user_id', async () => {
    const mockProjects = { items: [{ id: 'p1', name: 'Alpha' }], total: 1 }
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockProjects,
    })

    const result = await fetchProjects({ limit: 10, offset: 0, user_id: 'u1' })

    expect(global.fetch).toHaveBeenCalledWith(`${API_BASE_URL}/api/v1/projects?limit=10&offset=0&user_id=u1`)
    expect(result).toEqual(mockProjects)
  })

  it('fetchProjectById queries project detail endpoint', async () => {
    const mockProject = { id: 'p1', name: 'Alpha' }
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockProject,
    })

    const result = await fetchProjectById('p1')

    expect(global.fetch).toHaveBeenCalledWith(`${API_BASE_URL}/api/v1/projects/p1`)
    expect(result).toEqual(mockProject)
  })

  it('fetchProjectSummary queries project summary endpoint', async () => {
    const mockSummary = { project_id: 'p1', total_tasks: 5, todo: 2, in_progress: 1, done: 2 }
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockSummary,
    })

    const result = await fetchProjectSummary('p1')

    expect(global.fetch).toHaveBeenCalledWith(`${API_BASE_URL}/api/v1/projects/p1/summary`)
    expect(result).toEqual(mockSummary)
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

    const result = await fetchTasks({ project_id: 'p1', status: 'done', priority: 'high', search: 'login' })

    expect(global.fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/v1/tasks?project_id=p1&status=done&priority=high&search=login`
    )
    expect(result).toEqual(mockData)
  })

  it('createTask sends POST request with JSON payload', async () => {
    const payload = { title: 'New Task', user_id: 'u1', project_id: 'p1', priority: 'high', status: 'todo' }
    const mockCreated = { id: 't1', ...payload }
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => mockCreated,
    })

    const result = await createTask(payload)

    expect(global.fetch).toHaveBeenCalledWith(`${API_BASE_URL}/api/v1/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    expect(result).toEqual(mockCreated)
  })

  it('updateTask sends PATCH request with update payload', async () => {
    const payload = { status: 'done' }
    const mockUpdated = { id: 't1', title: 'Task 1', status: 'done' }
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockUpdated,
    })

    const result = await updateTask('t1', payload)

    expect(global.fetch).toHaveBeenCalledWith(`${API_BASE_URL}/api/v1/tasks/t1`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    expect(result).toEqual(mockUpdated)
  })

  it('deleteTask sends DELETE request and returns null on 204', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
    })

    const result = await deleteTask('t1')

    expect(global.fetch).toHaveBeenCalledWith(`${API_BASE_URL}/api/v1/tasks/t1`, {
      method: 'DELETE',
    })
    expect(result).toBeNull()
  })

  it('parses detail field from error response when available', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Cannot transition task status from todo to invalid' }),
    })

    await expect(updateTask('t1', { status: 'invalid' })).rejects.toThrow(
      'Cannot transition task status from todo to invalid'
    )
  })
})
