import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import App from './App'

describe('TaskFlow Frontend Application Tests', () => {
  beforeEach(() => {
    // Default fetch mock returning successful health payload
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: async () => ({
        status: 'healthy',
        timestamp: '2026-10-27T10:00:00Z',
        version: '1.0.0',
      }),
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  const renderAppAndWait = async () => {
    const utils = render(<App />)
    await waitFor(() => {
      expect(screen.getByText(/API Online|API Offline/)).toBeInTheDocument()
    })
    return utils
  }

  it('renders task list correctly with initial tasks and completion count', async () => {
    await renderAppAndWait()

    // Verify header title and task sandbox card
    expect(screen.getByText('Task Sandbox')).toBeInTheDocument()
    expect(screen.getByText('4 / 5 Completed')).toBeInTheDocument()

    // Verify initial task items are rendered
    expect(screen.getByText('Inspect existing repository setup')).toBeInTheDocument()
    expect(screen.getByText('Configure FastAPI endpoints and tests')).toBeInTheDocument()
    expect(screen.getByText('Initialize Alembic and SQLite migrations')).toBeInTheDocument()
    expect(screen.getByText('Setup GitHub Actions CI pipeline')).toBeInTheDocument()
    expect(screen.getByText('Day 1: Implement user authentication and models')).toBeInTheDocument()

    // Verify API Online badge
    expect(screen.getByText('API Online')).toBeInTheDocument()
  })

  it('renders empty state when all tasks are deleted', async () => {
    await renderAppAndWait()

    // Delete tasks one by one until list is empty
    while (screen.queryAllByTitle('Delete task').length > 0) {
      fireEvent.click(screen.getAllByTitle('Delete task')[0])
    }

    // Verify empty state is displayed
    const emptyState = screen.getByTestId('task-empty-state')
    expect(emptyState).toBeInTheDocument()
    expect(emptyState).toHaveTextContent('No tasks found.')
    expect(screen.getByText('0 / 0 Completed')).toBeInTheDocument()
  })

  it('filters tasks correctly when changing status filter', async () => {
    await renderAppAndWait()

    const filterSelect = screen.getByLabelText('Filter tasks')
    expect(filterSelect).toHaveValue('all')

    // Filter to "Active" (only incomplete tasks)
    act(() => {
      fireEvent.change(filterSelect, { target: { value: 'active' } })
    })
    expect(screen.getByText('Day 1: Implement user authentication and models')).toBeInTheDocument()
    expect(screen.queryByText('Inspect existing repository setup')).not.toBeInTheDocument()
    expect(screen.queryByText('Configure FastAPI endpoints and tests')).not.toBeInTheDocument()

    // Filter to "Completed" (only completed tasks)
    act(() => {
      fireEvent.change(filterSelect, { target: { value: 'completed' } })
    })
    expect(screen.getByText('Inspect existing repository setup')).toBeInTheDocument()
    expect(screen.getByText('Configure FastAPI endpoints and tests')).toBeInTheDocument()
    expect(screen.queryByText('Day 1: Implement user authentication and models')).not.toBeInTheDocument()

    // Reset filter to "All Tasks"
    act(() => {
      fireEvent.change(filterSelect, { target: { value: 'all' } })
    })
    expect(screen.getByText('Inspect existing repository setup')).toBeInTheDocument()
    expect(screen.getByText('Day 1: Implement user authentication and models')).toBeInTheDocument()
  })

  it('toggles task completion status and updates count', async () => {
    await renderAppAndWait()

    // Find the incomplete task checkbox
    const incompleteCheckbox = screen.getByLabelText(
      'Toggle Day 1: Implement user authentication and models'
    )
    expect(incompleteCheckbox).not.toBeChecked()
    expect(screen.getByText('4 / 5 Completed')).toBeInTheDocument()

    // Toggle to completed
    act(() => {
      fireEvent.click(incompleteCheckbox)
    })
    expect(incompleteCheckbox).toBeChecked()
    expect(screen.getByText('5 / 5 Completed')).toBeInTheDocument()

    // Toggle back to incomplete
    act(() => {
      fireEvent.click(incompleteCheckbox)
    })
    expect(incompleteCheckbox).not.toBeChecked()
    expect(screen.getByText('4 / 5 Completed')).toBeInTheDocument()
  })

  it('adds a new task through the creation form', async () => {
    await renderAppAndWait()

    const input = screen.getByPlaceholderText('Create new task...')
    const submitBtn = screen.getByRole('button', { name: 'Add' })

    act(() => {
      fireEvent.change(input, { target: { value: 'Write Vitest frontend suite' } })
      fireEvent.click(submitBtn)
    })

    expect(screen.getByText('Write Vitest frontend suite')).toBeInTheDocument()
    expect(screen.getByText('4 / 6 Completed')).toBeInTheDocument()
    expect(input).toHaveValue('')
  })

  it('handles backend connection failure and displays error status', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error: connection refused'))

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('API Offline')).toBeInTheDocument()
    })

    expect(screen.getByText(/Status: Connection Failed/i)).toBeInTheDocument()
    expect(screen.getByText(/Network error: connection refused/i)).toBeInTheDocument()
  })

  it('triggers manual health check when Ping button is clicked', async () => {
    await renderAppAndWait()

    const pingButton = screen.getByRole('button', { name: 'Ping Health Endpoint' })
    await act(async () => {
      fireEvent.click(pingButton)
    })

    await waitFor(() => {
      // 1 initial mount fetch + 1 manual ping fetch
      expect(global.fetch).toHaveBeenCalledTimes(2)
    })
  })
})
