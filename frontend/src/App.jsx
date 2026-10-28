import { useState, useEffect, useCallback } from 'react'
import './App.css'
import {
  API_BASE_URL,
  fetchHealth,
  fetchProjects,
  fetchProjectSummary,
  fetchTasks,
  createTask,
  updateTask,
  deleteTask,
} from './api'

const ROADMAP_STEPS = [
  { day: 'Day 0', title: 'Repository & Environment Setup', desc: 'FastAPI, React/Vite, SQLite, Alembic, Docker, CI.', active: false, done: true },
  { day: 'Day 1', title: 'Data Models & Auth', desc: 'User & Task SQLAlchemy models, JWT auth endpoints.', active: false, done: true },
  { day: 'Day 2', title: 'Task CRUD Operations', desc: 'REST endpoints for creating, updating, and filtering tasks.', active: false, done: true },
  { day: 'Day 3', title: 'Interactive Frontend', desc: 'React components for task boards and user login.', active: false, done: true },
  { day: 'Day 4', title: 'Advanced Filtering & State', desc: 'Search, tag filters, sorting, and optimistic UI updates.', active: false, done: true },
  { day: 'Day 5', title: 'Testing & Hardening', desc: 'E2E testing, backend test coverage, and security audit.', active: false, done: true },
  { day: 'Day 6', title: 'Full-Stack Integration', desc: 'FastAPI REST API, project views, task lifecycle & RTL suite.', active: true, done: true },
  { day: 'Day 7', title: 'Review & Retrospective', desc: 'Final polish, documentation walkthrough, and demo release.', active: false, done: false },
]

function App() {
  // Backend health connectivity state
  const [healthData, setHealthData] = useState(null)
  const [healthLoading, setHealthLoading] = useState(false)
  const [healthError, setHealthError] = useState(null)
  const [latency, setLatency] = useState(null)

  // Projects state
  const [projects, setProjects] = useState([])
  const [projectsLoading, setProjectsLoading] = useState(true)
  const [projectsError, setProjectsError] = useState(null)
  const [selectedProjectId, setSelectedProjectId] = useState(null)

  // Selected project tasks & summary
  const [tasks, setTasks] = useState([])
  const [tasksLoading, setTasksLoading] = useState(false)
  const [tasksError, setTasksError] = useState(null)
  const [summary, setSummary] = useState(null)

  // Filter controls
  const [statusFilter, setStatusFilter] = useState('all')
  const [priorityFilter, setPriorityFilter] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')

  // Task creation form
  const [newTaskTitle, setNewTaskTitle] = useState('')
  const [newTaskPriority, setNewTaskPriority] = useState('medium')
  const [newTaskStatus, setNewTaskStatus] = useState('todo')
  const [taskSubmitting, setTaskSubmitting] = useState(false)
  const [validationError, setValidationError] = useState(null)

  // Task editing state
  const [editingTaskId, setEditingTaskId] = useState(null)
  const [editTitle, setEditTitle] = useState('')
  const [editPriority, setEditPriority] = useState('medium')
  const [editStatus, setEditStatus] = useState('todo')

  const selectedProject = projects.find((p) => p.id === selectedProjectId) || null

  const checkHealth = async () => {
    setHealthLoading(true)
    setHealthError(null)
    const startTime = performance.now()
    try {
      const data = await fetchHealth()
      setLatency(Math.round(performance.now() - startTime))
      setHealthData(data)
    } catch (err) {
      setHealthError(err.message || 'Unable to connect to backend')
      setHealthData(null)
    } finally {
      setHealthLoading(false)
    }
  }

  // Initial health check on mount
  useEffect(() => {
    let active = true
    const checkInitial = async () => {
      const startTime = performance.now()
      try {
        const data = await fetchHealth()
        if (!active) return
        setLatency(Math.round(performance.now() - startTime))
        setHealthData(data)
      } catch (err) {
        if (active) setHealthError(err.message || 'Unable to connect to backend')
      }
    }
    checkInitial()
    return () => {
      active = false
    }
  }, [])

  // Load projects list
  const loadProjects = async () => {
    setProjectsLoading(true)
    setProjectsError(null)
    try {
      const data = await fetchProjects({ limit: 50 })
      const items = data?.items || []
      setProjects(items)
      if (items.length > 0) {
        setSelectedProjectId((prev) => (prev && items.some((p) => p.id === prev) ? prev : items[0].id))
      } else {
        setSelectedProjectId(null)
      }
    } catch (err) {
      setProjectsError(err.message || 'Failed to load projects')
    } finally {
      setProjectsLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    const fetchInitialProjects = async () => {
      try {
        const data = await fetchProjects({ limit: 50 })
        if (!active) return
        const items = data?.items || []
        setProjects(items)
        if (items.length > 0) {
          setSelectedProjectId((prev) => (prev && items.some((p) => p.id === prev) ? prev : items[0].id))
        } else {
          setSelectedProjectId(null)
        }
      } catch (err) {
        if (active) setProjectsError(err.message || 'Failed to load projects')
      } finally {
        if (active) setProjectsLoading(false)
      }
    }
    fetchInitialProjects()
    return () => {
      active = false
    }
  }, [])

  // Fetch tasks and summary when selected project or filters change
  const refreshProjectData = useCallback(async () => {
    if (!selectedProjectId) return
    const params = {
      project_id: selectedProjectId,
      status: statusFilter !== 'all' ? statusFilter : undefined,
      priority: priorityFilter !== 'all' ? priorityFilter : undefined,
      search: searchQuery.trim() || undefined,
    }
    try {
      const [taskData, summaryData] = await Promise.all([
        fetchTasks(params),
        fetchProjectSummary(selectedProjectId).catch(() => null),
      ])
      setTasks(taskData?.items || [])
      if (summaryData) setSummary(summaryData)
    } catch (err) {
      setTasksError(err.message || 'Failed to load tasks')
    }
  }, [selectedProjectId, statusFilter, priorityFilter, searchQuery])

  useEffect(() => {
    if (!selectedProjectId) return

    let active = true

    const params = {
      project_id: selectedProjectId,
      status: statusFilter !== 'all' ? statusFilter : undefined,
      priority: priorityFilter !== 'all' ? priorityFilter : undefined,
      search: searchQuery.trim() || undefined,
    }

    Promise.all([
      fetchTasks(params),
      fetchProjectSummary(selectedProjectId).catch(() => null),
    ])
      .then(([taskData, summaryData]) => {
        if (!active) return
        setTasks(taskData?.items || [])
        if (summaryData) setSummary(summaryData)
      })
      .catch((err) => {
        if (!active) return
        setTasksError(err.message || 'Failed to load tasks')
      })
      .finally(() => {
        if (active) setTasksLoading(false)
      })

    return () => {
      active = false
    }
  }, [selectedProjectId, statusFilter, priorityFilter, searchQuery])

  // Task creation handler
  const handleCreateTask = async (e) => {
    e.preventDefault()
    if (!newTaskTitle.trim()) {
      setValidationError('Task title is required.')
      return
    }
    if (!selectedProject) {
      setValidationError('Please select a project first.')
      return
    }

    setTaskSubmitting(true)
    setValidationError(null)
    try {
      await createTask({
        title: newTaskTitle.trim(),
        priority: newTaskPriority,
        status: newTaskStatus,
        project_id: selectedProject.id,
        user_id: selectedProject.user_id,
      })
      setNewTaskTitle('')
      await refreshProjectData()
    } catch (err) {
      setValidationError(err.message || 'Failed to create task')
    } finally {
      setTaskSubmitting(false)
    }
  }

  // Status toggle handler
  const handleToggleTaskStatus = async (task) => {
    const nextStatus = task.status === 'done' ? 'todo' : 'done'
    try {
      await updateTask(task.id, { status: nextStatus })
      await refreshProjectData()
    } catch (err) {
      setTasksError(err.message || 'Failed to update task status')
    }
  }

  // Direct status change handler
  const handleChangeStatus = async (taskId, nextStatus) => {
    try {
      await updateTask(taskId, { status: nextStatus })
      await refreshProjectData()
    } catch (err) {
      setTasksError(err.message || 'Failed to update task status')
    }
  }

  // Edit task handlers
  const startEdit = (task) => {
    setEditingTaskId(task.id)
    setEditTitle(task.title)
    setEditPriority(task.priority)
    setEditStatus(task.status)
    setValidationError(null)
  }

  const cancelEdit = () => {
    setEditingTaskId(null)
  }

  const handleSaveEdit = async (e, taskId) => {
    e.preventDefault()
    if (!editTitle.trim()) {
      setValidationError('Task title cannot be empty.')
      return
    }
    try {
      await updateTask(taskId, {
        title: editTitle.trim(),
        priority: editPriority,
        status: editStatus,
      })
      setEditingTaskId(null)
      await refreshProjectData()
    } catch (err) {
      setValidationError(err.message || 'Failed to save task edits')
    }
  }

  // Task deletion handler
  const handleDeleteTask = async (taskId) => {
    try {
      await deleteTask(taskId)
      await refreshProjectData()
    } catch (err) {
      setTasksError(err.message || 'Failed to delete task')
    }
  }

  return (
    <div className="app-container">
      {/* Navbar */}
      <header className="navbar">
        <div className="brand">
          <div className="brand-icon">TF</div>
          <span className="brand-name">TaskFlow</span>
        </div>

        <div className="nav-badges">
          <span className="phase-badge">Day 6: Integrated</span>
          <div className="status-pill">
            <span className={`dot ${healthData ? 'dot-green' : healthError ? 'dot-red' : 'dot-yellow'}`} />
            <span>{healthData ? 'API Online' : healthError ? 'API Offline' : 'Connecting...'}</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main>
        <section className="hero">
          <span className="hero-tag">Day 6 • Full-Stack Workspace</span>
          <h1 className="hero-title">
            Task Orchestration <span>Engine</span>
          </h1>
          <p className="hero-desc">
            Production task and project orchestration connected to FastAPI and PostgreSQL.
          </p>
        </section>

        {/* Backend Health Inspector */}
        <section style={{ marginBottom: '2rem' }}>
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Backend Connectivity</h2>
              <button
                type="button"
                className="btn btn-primary"
                onClick={checkHealth}
                disabled={healthLoading}
              >
                {healthLoading ? 'Pinging...' : 'Ping Health Endpoint'}
              </button>
            </div>

            <div className="api-inspector">
              <div className="inspector-meta">
                <div>
                  <span className="method-tag">GET</span>
                  <span className="endpoint-url">{API_BASE_URL}/health</span>
                </div>
                {latency !== null && (
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {latency} ms
                  </span>
                )}
              </div>

              <pre className="json-box">
                {healthLoading && 'Fetching response from backend...'}
                {!healthLoading && healthData && JSON.stringify(healthData, null, 2)}
                {!healthLoading && healthError && (
                  `Status: Connection Failed\nError: ${healthError}\n\nTip: Start the backend server using:\n  uvicorn app.main:app --reload`
                )}
              </pre>
            </div>
          </div>
        </section>

        {/* Dashboard Grid: Left Projects, Right Tasks */}
        <section className="dashboard-grid">
          {/* Projects Column */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">
                Projects
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                  ({projects.length})
                </span>
              </h2>
            </div>

            {projectsLoading && (
              <div className="task-empty-state" data-testid="projects-loading">
                Loading projects...
              </div>
            )}

            {projectsError && (
              <div className="error-banner" role="alert">
                Failed to load projects: {projectsError}
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ marginLeft: '0.75rem', padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                  onClick={loadProjects}
                >
                  Retry
                </button>
              </div>
            )}

            {!projectsLoading && !projectsError && projects.length === 0 && (
              <div className="task-empty-state" data-testid="project-empty-state">
                No projects found.
              </div>
            )}

            {!projectsLoading && projects.length > 0 && (
              <div className="project-list" role="list">
                {projects.map((project) => (
                  <button
                    type="button"
                    key={project.id}
                    className={`project-item ${selectedProjectId === project.id ? 'active' : ''}`}
                    onClick={() => setSelectedProjectId(project.id)}
                    aria-label={`Select project ${project.name}`}
                  >
                    <div className="project-item-header">
                      <span className="project-item-name">{project.name}</span>
                      {selectedProjectId === project.id && (
                        <span className="active-pill">Selected</span>
                      )}
                    </div>
                    {project.description && (
                      <p className="project-item-desc">{project.description}</p>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Project Details & Tasks Column */}
          <div className="card">
            {!selectedProject ? (
              <div className="task-empty-state">
                Select a project from the left panel to inspect tasks.
              </div>
            ) : (
              <div>
                {/* Project Header & Summary Stats */}
                <div className="project-detail-header">
                  <h2 className="project-detail-title">{selectedProject.name}</h2>
                  {selectedProject.description && (
                    <p className="project-detail-desc">{selectedProject.description}</p>
                  )}
                  {summary && (
                    <div className="summary-stats">
                      <span className="summary-stat">Total: <strong>{summary.total_tasks}</strong></span>
                      <span className="summary-stat">Todo: <strong>{summary.todo}</strong></span>
                      <span className="summary-stat">In Progress: <strong>{summary.in_progress}</strong></span>
                      <span className="summary-stat">Done: <strong>{summary.done}</strong></span>
                    </div>
                  )}
                </div>

                {/* Filter Controls Bar */}
                <div className="filter-bar">
                  <select
                    className="task-input filter-select"
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    aria-label="Filter tasks by status"
                  >
                    <option value="all">All Statuses</option>
                    <option value="todo">Todo</option>
                    <option value="in_progress">In Progress</option>
                    <option value="done">Done</option>
                  </select>

                  <select
                    className="task-input filter-select"
                    value={priorityFilter}
                    onChange={(e) => setPriorityFilter(e.target.value)}
                    aria-label="Filter tasks by priority"
                  >
                    <option value="all">All Priorities</option>
                    <option value="high">High Priority</option>
                    <option value="medium">Medium Priority</option>
                    <option value="low">Low Priority</option>
                  </select>

                  <input
                    type="text"
                    className="task-input search-input"
                    placeholder="Search tasks..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    aria-label="Search tasks"
                  />
                </div>

                {/* Task Creation Form */}
                <form className="task-form" onSubmit={handleCreateTask}>
                  <input
                    type="text"
                    className="task-input"
                    placeholder="Create new task..."
                    value={newTaskTitle}
                    onChange={(e) => {
                      setNewTaskTitle(e.target.value)
                      if (validationError) setValidationError(null)
                    }}
                    aria-label="New task title"
                  />
                  <select
                    className="task-input"
                    style={{ width: 'auto', cursor: 'pointer' }}
                    value={newTaskPriority}
                    onChange={(e) => setNewTaskPriority(e.target.value)}
                    aria-label="New task priority"
                  >
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                  <select
                    className="task-input"
                    style={{ width: 'auto', cursor: 'pointer' }}
                    value={newTaskStatus}
                    onChange={(e) => setNewTaskStatus(e.target.value)}
                    aria-label="New task status"
                  >
                    <option value="todo">Todo</option>
                    <option value="in_progress">In Progress</option>
                    <option value="done">Done</option>
                  </select>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    style={{ padding: '0.65rem 1rem' }}
                    disabled={taskSubmitting}
                  >
                    {taskSubmitting ? 'Adding...' : 'Add'}
                  </button>
                </form>

                {/* Validation / Form Error */}
                {validationError && (
                  <div className="error-banner" role="alert">
                    {validationError}
                  </div>
                )}

                {/* Tasks Network / Server Error */}
                {tasksError && (
                  <div className="error-banner" role="alert">
                    {tasksError}
                  </div>
                )}

                {/* Tasks List */}
                <div className="task-list">
                  {tasksLoading && (
                    <div className="task-empty-state" data-testid="tasks-loading">
                      Loading tasks...
                    </div>
                  )}

                  {!tasksLoading && tasks.length === 0 && (
                    <div className="task-empty-state" data-testid="task-empty-state">
                      No tasks found.
                    </div>
                  )}

                  {!tasksLoading &&
                    tasks.map((task) =>
                      editingTaskId === task.id ? (
                        <form
                          key={task.id}
                          className="task-edit-form"
                          onSubmit={(e) => handleSaveEdit(e, task.id)}
                        >
                          <input
                            type="text"
                            className="task-input"
                            value={editTitle}
                            onChange={(e) => setEditTitle(e.target.value)}
                            aria-label={`Edit title for ${task.title}`}
                          />
                          <select
                            className="task-input"
                            style={{ width: 'auto' }}
                            value={editPriority}
                            onChange={(e) => setEditPriority(e.target.value)}
                            aria-label="Edit priority"
                          >
                            <option value="high">High</option>
                            <option value="medium">Medium</option>
                            <option value="low">Low</option>
                          </select>
                          <select
                            className="task-input"
                            style={{ width: 'auto' }}
                            value={editStatus}
                            onChange={(e) => setEditStatus(e.target.value)}
                            aria-label="Edit status"
                          >
                            <option value="todo">Todo</option>
                            <option value="in_progress">In Progress</option>
                            <option value="done">Done</option>
                          </select>
                          <button
                            type="submit"
                            className="btn btn-primary"
                            style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                          >
                            Save
                          </button>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                            onClick={cancelEdit}
                          >
                            Cancel
                          </button>
                        </form>
                      ) : (
                        <div key={task.id} className="task-item">
                          <div className="task-left">
                            <input
                              type="checkbox"
                              className="task-checkbox"
                              checked={task.status === 'done'}
                              onChange={() => handleToggleTaskStatus(task)}
                              aria-label={`Toggle ${task.title}`}
                            />
                            <div>
                              <span className={`task-title ${task.status === 'done' ? 'done' : ''}`}>
                                {task.title}
                              </span>
                              {task.description && (
                                <p className="project-item-desc" style={{ marginTop: '0.15rem' }}>
                                  {task.description}
                                </p>
                              )}
                            </div>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <select
                              className="status-select"
                              value={task.status}
                              onChange={(e) => handleChangeStatus(task.id, e.target.value)}
                              aria-label={`Change status for ${task.title}`}
                            >
                              <option value="todo">Todo</option>
                              <option value="in_progress">In Progress</option>
                              <option value="done">Done</option>
                            </select>
                            <span className={`priority-tag priority-${task.priority}`}>
                              {task.priority}
                            </span>
                            <button
                              type="button"
                              className="btn btn-secondary"
                              style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                              onClick={() => startEdit(task)}
                              aria-label={`Edit ${task.title}`}
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              className="delete-btn"
                              onClick={() => handleDeleteTask(task.id)}
                              title="Delete task"
                              aria-label={`Delete ${task.title}`}
                            >
                              ✕
                            </button>
                          </div>
                        </div>
                      )
                    )}
                </div>
              </div>
            )}
          </div>
        </section>

        {/* 7-Day Roadmap */}
        <section className="roadmap-section">
          <div className="section-header">
            <h2 className="section-title">7-Day Development Sprint Roadmap</h2>
            <p className="section-desc">Architecture timeline from initial bootstrap to release.</p>
          </div>

          <div className="roadmap-grid">
            {ROADMAP_STEPS.map((step) => (
              <div key={step.day} className={`roadmap-card ${step.active ? 'active' : ''}`}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="roadmap-day">{step.day}</span>
                  {step.done && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--accent-emerald)', fontWeight: 600 }}>
                      ✓ READY
                    </span>
                  )}
                </div>
                <h3 className="roadmap-name">{step.title}</h3>
                <p className="roadmap-desc">{step.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Telemetry Stack Badges */}
        <footer className="tech-badges">
          <span className="tech-badge">Python 3.12</span>
          <span className="tech-badge">FastAPI 0.153</span>
          <span className="tech-badge">SQLAlchemy 2.1</span>
          <span className="tech-badge">Alembic 1.20</span>
          <span className="tech-badge">React 19</span>
          <span className="tech-badge">Vite 8</span>
          <span className="tech-badge">PostgreSQL</span>
          <span className="tech-badge">Docker Compose</span>
        </footer>
      </main>
    </div>
  )
}

export default App
