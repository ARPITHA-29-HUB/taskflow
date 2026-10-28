import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import App from './App'

const MOCK_PROJECTS = {
  items: [
    {
      id: 'proj-1',
      name: 'Project Alpha',
      description: 'Alpha workspace description',
      user_id: 'user-1',
      created_at: '2026-10-27T10:00:00Z',
    },
    {
      id: 'proj-2',
      name: 'Project Beta',
      description: 'Beta workspace description',
      user_id: 'user-1',
      created_at: '2026-10-27T10:00:00Z',
    },
  ],
  total: 2,
  limit: 50,
  offset: 0,
}

const MOCK_SUMMARY = {
  project_id: 'proj-1',
  total_tasks: 2,
  todo: 1,
  in_progress: 0,
  done: 1,
}

const MOCK_TASKS = {
  items: [
    {
      id: 'task-1',
      title: 'Task Alpha 1',
      description: 'First task',
      priority: 'high',
      status: 'todo',
      project_id: 'proj-1',
      user_id: 'user-1',
    },
    {
      id: 'task-2',
      title: 'Task Alpha 2',
      description: 'Second task',
      priority: 'low',
      status: 'done',
      project_id: 'proj-1',
      user_id: 'user-1',
    },
  ],
  total: 2,
  limit: 20,
  offset: 0,
}

const setupFetchMock = (overrides = {}) => {
  return vi.fn().mockImplementation(async (url, options = {}) => {
    const urlStr = String(url)

    if (urlStr.includes('/health')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({ status: 'healthy', version: '1.0.0' }),
      }
    }

    if (urlStr.includes('/api/v1/projects') && !urlStr.includes('/summary')) {
      if (overrides.projectsError) {
        return {
          ok: false,
          status: 500,
          statusText: 'Internal Server Error',
        }
      }
      return {
        ok: true,
        status: 200,
        json: async () => (overrides.projects !== undefined ? overrides.projects : MOCK_PROJECTS),
      }
    }

    if (urlStr.includes('/summary')) {
      return {
        ok: true,
        status: 200,
        json: async () => (overrides.summary !== undefined ? overrides.summary : MOCK_SUMMARY),
      }
    }

    if (urlStr.includes('/api/v1/tasks')) {
      if (options.method === 'POST') {
        const body = JSON.parse(options.body)
        return {
          ok: true,
          status: 201,
          json: async () => ({
            id: 'task-new-id',
            ...body,
          }),
        }
      }
      if (options.method === 'PATCH' || options.method === 'PUT') {
        const body = JSON.parse(options.body)
        return {
          ok: true,
          status: 200,
          json: async () => ({
            id: 'task-1',
            title: body.title || 'Task Alpha 1',
            priority: body.priority || 'high',
            status: body.status || 'done',
          }),
        }
      }
      if (options.method === 'DELETE') {
        return {
          ok: true,
          status: 204,
        }
      }

      // GET /tasks
      let items = overrides.tasks !== undefined ? [...overrides.tasks.items] : [...MOCK_TASKS.items]
      if (urlStr.includes('status=todo')) items = items.filter((t) => t.status === 'todo')
      if (urlStr.includes('status=done')) items = items.filter((t) => t.status === 'done')
      if (urlStr.includes('priority=high')) items = items.filter((t) => t.priority === 'high')
      if (urlStr.includes('priority=low')) items = items.filter((t) => t.priority === 'low')

      return {
        ok: true,
        status: 200,
        json: async () => ({
          items,
          total: items.length,
          limit: 20,
          offset: 0,
        }),
      }
    }

    return Promise.reject(new Error(`Unhandled URL: ${urlStr}`))
  })
}

describe('TaskFlow Frontend Application Integration Tests', () => {
  beforeEach(() => {
    global.fetch = setupFetchMock()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  const renderAppAndWait = async () => {
    const utils = render(<App />)
    await waitFor(() => {
      expect(screen.getByText(/API Online|API Offline/)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Select project Project Alpha/i })).toBeInTheDocument()
      expect(screen.getByText('Task Alpha 1')).toBeInTheDocument()
    })
    return utils
  }

  it('renders projects list and automatically selects first project with tasks and stats', async () => {
    await renderAppAndWait()

    // Verify projects list rendered
    expect(screen.getByText('Projects')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Select project Project Alpha/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Select project Project Beta/i })).toBeInTheDocument()
    expect(screen.getByText('Selected')).toBeInTheDocument()

    // Verify project detail and summary stats
    expect(screen.getByRole('heading', { level: 2, name: 'Project Alpha' })).toBeInTheDocument()
    expect(screen.getAllByText('Alpha workspace description').length).toBeGreaterThan(0)
    expect(screen.getByText(/Total:/)).toBeInTheDocument()

    // Verify tasks rendered
    expect(screen.getByText('Task Alpha 1')).toBeInTheDocument()
    expect(screen.getByText('Task Alpha 2')).toBeInTheDocument()
  })

  it('switches selected project when clicking another project', async () => {
    await renderAppAndWait()

    const projectBetaBtn = screen.getByRole('button', { name: 'Select project Project Beta' })
    await act(async () => {
      fireEvent.click(projectBetaBtn)
    })

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'Project Beta' })).toBeInTheDocument()
      expect(screen.getAllByText('Beta workspace description').length).toBeGreaterThan(0)
    })
  })

  it('renders empty state when projects list is empty', async () => {
    global.fetch = setupFetchMock({ projects: { items: [], total: 0, limit: 50, offset: 0 } })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByTestId('project-empty-state')).toBeInTheDocument()
      expect(screen.getByText('No projects found.')).toBeInTheDocument()
    })
  })

  it('renders empty state when selected project has no tasks', async () => {
    global.fetch = setupFetchMock({ tasks: { items: [], total: 0, limit: 20, offset: 0 } })

    render(<App />)

    await waitFor(() => {
      const emptyState = screen.getByTestId('task-empty-state')
      expect(emptyState).toBeInTheDocument()
      expect(emptyState).toHaveTextContent('No tasks found.')
    })
  })

  it('filters tasks correctly when changing status and priority filters', async () => {
    await renderAppAndWait()

    const statusFilter = screen.getByLabelText('Filter tasks by status')
    const priorityFilter = screen.getByLabelText('Filter tasks by priority')

    // Filter to todo
    await act(async () => {
      fireEvent.change(statusFilter, { target: { value: 'todo' } })
    })

    await waitFor(() => {
      expect(screen.getByText('Task Alpha 1')).toBeInTheDocument()
      expect(screen.queryByText('Task Alpha 2')).not.toBeInTheDocument()
    })

    // Filter to priority high
    await act(async () => {
      fireEvent.change(priorityFilter, { target: { value: 'high' } })
    })

    await waitFor(() => {
      expect(screen.getByText('Task Alpha 1')).toBeInTheDocument()
      expect(screen.queryByText('Task Alpha 2')).not.toBeInTheDocument()
    })
  })

  it('validates task creation form with client validation error', async () => {
    await renderAppAndWait()

    const submitBtn = screen.getByRole('button', { name: 'Add' })
    await act(async () => {
      fireEvent.click(submitBtn)
    })

    expect(screen.getByRole('alert')).toHaveTextContent('Task title is required.')
  })

  it('creates a new task through creation form', async () => {
    await renderAppAndWait()

    const titleInput = screen.getByLabelText('New task title')
    const prioritySelect = screen.getByLabelText('New task priority')
    const statusSelect = screen.getByLabelText('New task status')
    const submitBtn = screen.getByRole('button', { name: 'Add' })

    await act(async () => {
      fireEvent.change(titleInput, { target: { value: 'New Test Task' } })
      fireEvent.change(prioritySelect, { target: { value: 'high' } })
      fireEvent.change(statusSelect, { target: { value: 'todo' } })
      fireEvent.click(submitBtn)
    })

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/tasks'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            title: 'New Test Task',
            priority: 'high',
            status: 'todo',
            project_id: 'proj-1',
            user_id: 'user-1',
          }),
        })
      )
    })
  })

  it('toggles task status when checkbox is clicked', async () => {
    await renderAppAndWait()

    const checkbox = screen.getByLabelText('Toggle Task Alpha 1')
    await act(async () => {
      fireEvent.click(checkbox)
    })

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/tasks/task-1'),
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ status: 'done' }),
        })
      )
    })
  })

  it('edits task title and priority', async () => {
    await renderAppAndWait()

    const editBtn = screen.getByLabelText('Edit Task Alpha 1')
    await act(async () => {
      fireEvent.click(editBtn)
    })

    const editInput = screen.getByLabelText('Edit title for Task Alpha 1')
    const saveBtn = screen.getByRole('button', { name: 'Save' })

    await act(async () => {
      fireEvent.change(editInput, { target: { value: 'Updated Task Alpha 1' } })
      fireEvent.click(saveBtn)
    })

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/tasks/task-1'),
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({
            title: 'Updated Task Alpha 1',
            priority: 'high',
            status: 'todo',
          }),
        })
      )
    })
  })

  it('deletes a task when delete button is clicked', async () => {
    await renderAppAndWait()

    const deleteBtn = screen.getByLabelText('Delete Task Alpha 1')
    await act(async () => {
      fireEvent.click(deleteBtn)
    })

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/tasks/task-1'),
        expect.objectContaining({
          method: 'DELETE',
        })
      )
    })
  })

  it('handles backend error when fetching projects', async () => {
    global.fetch = setupFetchMock({ projectsError: true })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Failed to load projects: HTTP 500 - Internal Server Error')
    })
  })

  it('handles backend connection failure and displays error status', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error: connection refused'))

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('API Offline')).toBeInTheDocument()
    })

    expect(screen.getByText(/Status: Connection Failed/i)).toBeInTheDocument()
    expect(screen.getAllByText(/Network error: connection refused/i).length).toBeGreaterThan(0)
  })

  it('triggers manual health check when Ping button is clicked', async () => {
    await renderAppAndWait()

    const pingButton = screen.getByRole('button', { name: 'Ping Health Endpoint' })
    await act(async () => {
      fireEvent.click(pingButton)
    })

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/health')
    })
  })
})
