export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function handleResponse(response) {
  if (!response.ok) {
    let message = `HTTP ${response.status} - ${response.statusText}`
    try {
      const data = await response.json()
      if (data?.detail) {
        message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
      } else if (data?.title) {
        message = data.title
      }
    } catch {
      // response was not JSON
    }
    const error = new Error(message)
    error.status = response.status
    throw error
  }
  if (response.status === 204) {
    return null
  }
  return response.json()
}

export async function fetchHealth() {
  const response = await fetch(`${API_BASE_URL}/health`)
  return handleResponse(response)
}

export async function fetchProjects(params = {}) {
  const query = new URLSearchParams()
  if (params.limit !== undefined && params.limit !== null) query.append('limit', params.limit)
  if (params.offset !== undefined && params.offset !== null) query.append('offset', params.offset)
  if (params.user_id) query.append('user_id', params.user_id)
  const qs = query.toString() ? `?${query.toString()}` : ''
  const response = await fetch(`${API_BASE_URL}/api/v1/projects${qs}`)
  return handleResponse(response)
}

export async function fetchProjectById(projectId) {
  const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}`)
  return handleResponse(response)
}

export async function fetchProjectSummary(projectId) {
  const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}/summary`)
  return handleResponse(response)
}

export async function fetchTasks(params = {}) {
  const query = new URLSearchParams()
  if (params.project_id) query.append('project_id', params.project_id)
  if (params.user_id) query.append('user_id', params.user_id)
  if (params.status) query.append('status', params.status)
  if (params.priority) query.append('priority', params.priority)
  if (params.search) query.append('search', params.search)
  if (params.limit !== undefined && params.limit !== null) query.append('limit', params.limit)
  if (params.offset !== undefined && params.offset !== null) query.append('offset', params.offset)
  const qs = query.toString() ? `?${query.toString()}` : ''
  const response = await fetch(`${API_BASE_URL}/api/v1/tasks${qs}`)
  return handleResponse(response)
}

export async function createTask(payload) {
  const response = await fetch(`${API_BASE_URL}/api/v1/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return handleResponse(response)
}

export async function updateTask(taskId, payload) {
  const response = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return handleResponse(response)
}

export async function deleteTask(taskId) {
  const response = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}`, {
    method: 'DELETE',
  })
  return handleResponse(response)
}
