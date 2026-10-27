export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function fetchHealth() {
  const response = await fetch(`${API_BASE_URL}/health`)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} - ${response.statusText}`)
  }
  return response.json()
}

export async function fetchTasks(params = {}) {
  const query = new URLSearchParams()
  if (params.status) query.append('status', params.status)
  if (params.priority) query.append('priority', params.priority)
  if (params.search) query.append('search', params.search)
  const qs = query.toString() ? `?${query.toString()}` : ''
  const response = await fetch(`${API_BASE_URL}/api/v1/tasks${qs}`)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} - ${response.statusText}`)
  }
  return response.json()
}
