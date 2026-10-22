import { useState, useEffect } from 'react'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const INITIAL_TASKS = [
  { id: 1, title: 'Inspect existing repository setup', priority: 'high', completed: true },
  { id: 2, title: 'Configure FastAPI endpoints and tests', priority: 'high', completed: true },
  { id: 3, title: 'Initialize Alembic and SQLite migrations', priority: 'medium', completed: true },
  { id: 4, title: 'Setup GitHub Actions CI pipeline', priority: 'medium', completed: true },
  { id: 5, title: 'Day 1: Implement user authentication and models', priority: 'low', completed: false },
]

const ROADMAP_STEPS = [
  { day: 'Day 0', title: 'Repository & Environment Setup', desc: 'FastAPI, React/Vite, SQLite, Alembic, Docker, CI.', active: true, done: true },
  { day: 'Day 1', title: 'Data Models & Auth', desc: 'User & Task SQLAlchemy models, JWT auth endpoints.', active: false, done: false },
  { day: 'Day 2', title: 'Task CRUD Operations', desc: 'REST endpoints for creating, updating, and filtering tasks.', active: false, done: false },
  { day: 'Day 3', title: 'Interactive Frontend', desc: 'React components for task boards and user login.', active: false, done: false },
  { day: 'Day 4', title: 'Advanced Filtering & State', desc: 'Search, tag filters, sorting, and optimistic UI updates.', active: false, done: false },
  { day: 'Day 5', title: 'Testing & Hardening', desc: 'E2E testing, backend test coverage, and security audit.', active: false, done: false },
  { day: 'Day 6', title: 'Dockerization & Deployment', desc: 'Multi-stage Docker compose & production readiness.', active: false, done: false },
  { day: 'Day 7', title: 'Review & Retrospective', desc: 'Final polish, documentation walkthrough, and demo release.', active: false, done: false },
]

function App() {
  // Health check state
  const [healthData, setHealthData] = useState(null)
  const [healthLoading, setHealthLoading] = useState(false)
  const [healthError, setHealthError] = useState(null)
  const [latency, setLatency] = useState(null)

  // Interactive demo tasks
  const [tasks, setTasks] = useState(INITIAL_TASKS)
  const [newTaskTitle, setNewTaskTitle] = useState('')
  const [newTaskPriority, setNewTaskPriority] = useState('medium')

  const checkHealth = async () => {
    setHealthLoading(true)
    setHealthError(null)
    const startTime = performance.now()
    try {
      const response = await fetch(`${API_BASE_URL}/health`)
      const elapsed = Math.round(performance.now() - startTime)
      setLatency(elapsed)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status} - ${response.statusText}`)
      }
      const data = await response.json()
      setHealthData(data)
    } catch (err) {
      setHealthError(err.message || 'Unable to connect to backend')
      setHealthData(null)
    } finally {
      setHealthLoading(false)
    }
  }

  useEffect(() => {
    let active = true

    const fetchInitialHealth = async () => {
      const startTime = performance.now()
      try {
        const response = await fetch(`${API_BASE_URL}/health`)
        const elapsed = Math.round(performance.now() - startTime)
        if (!active) return

        setLatency(elapsed)
        if (!response.ok) {
          throw new Error(`HTTP ${response.status} - ${response.statusText}`)
        }
        const data = await response.json()
        setHealthData(data)
      } catch (err) {
        if (active) {
          setHealthError(err.message || 'Unable to connect to backend')
        }
      }
    }

    fetchInitialHealth()

    return () => {
      active = false
    }
  }, [])

  const handleAddTask = (e) => {
    e.preventDefault()
    if (!newTaskTitle.trim()) return
    const newTask = {
      id: Date.now(),
      title: newTaskTitle.trim(),
      priority: newTaskPriority,
      completed: false,
    }
    setTasks([newTask, ...tasks])
    setNewTaskTitle('')
  }

  const toggleTask = (id) => {
    setTasks(tasks.map(t => t.id === id ? { ...t, completed: !t.completed } : t))
  }

  const deleteTask = (id) => {
    setTasks(tasks.filter(t => t.id !== id))
  }

  const completedCount = tasks.filter(t => t.completed).length

  return (
    <div className="app-container">
      {/* Navbar */}
      <header className="navbar">
        <div className="brand">
          <div className="brand-icon">TF</div>
          <span className="brand-name">TaskFlow</span>
        </div>

        <div className="nav-badges">
          <span className="phase-badge">Day 0: Setup Ready</span>
          <div className="status-pill">
            <span className={`dot ${healthData ? 'dot-green' : healthError ? 'dot-red' : 'dot-yellow'}`} />
            <span>{healthData ? 'API Online' : healthError ? 'API Offline' : 'Connecting...'}</span>
          </div>
        </div>
      </header>

      {/* Hero */}
      <main>
        <section className="hero">
          <span className="hero-tag">Full-Stack Development Sprint</span>
          <h1 className="hero-title">
            Task Orchestration <span>Engine</span>
          </h1>
          <p className="hero-desc">
            Full-stack task management architecture powered by FastAPI, SQLite, and React with Vite.
            Repository environment initialized and ready for feature implementation.
          </p>
        </section>

        {/* Dashboard Grid */}
        <section className="dashboard-grid">
          {/* API Health Inspector */}
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

              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.25rem' }}>
                <a
                  href={`${API_BASE_URL}/docs`}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-secondary"
                  style={{ fontSize: '0.8rem', padding: '0.45rem 0.85rem' }}
                >
                  Interactive Swagger Docs ↗
                </a>
                <a
                  href={`${API_BASE_URL}/health`}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-secondary"
                  style={{ fontSize: '0.8rem', padding: '0.45rem 0.85rem' }}
                >
                  Raw /health ↗
                </a>
              </div>
            </div>
          </div>

          {/* Interactive Tasks Sandbox */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Task Sandbox</h2>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                {completedCount} / {tasks.length} Completed
              </span>
            </div>

            <form className="task-form" onSubmit={handleAddTask}>
              <input
                type="text"
                className="task-input"
                placeholder="Create new task..."
                value={newTaskTitle}
                onChange={(e) => setNewTaskTitle(e.target.value)}
              />
              <select
                className="task-input"
                style={{ width: 'auto', cursor: 'pointer' }}
                value={newTaskPriority}
                onChange={(e) => setNewTaskPriority(e.target.value)}
              >
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
              <button type="submit" className="btn btn-primary" style={{ padding: '0.65rem 1rem' }}>
                Add
              </button>
            </form>

            <div className="task-list">
              {tasks.map((task) => (
                <div key={task.id} className="task-item">
                  <div className="task-left">
                    <input
                      type="checkbox"
                      className="task-checkbox"
                      checked={task.completed}
                      onChange={() => toggleTask(task.id)}
                    />
                    <span className={`task-title ${task.completed ? 'done' : ''}`}>
                      {task.title}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className={`priority-tag priority-${task.priority}`}>
                      {task.priority}
                    </span>
                    <button
                      type="button"
                      className="delete-btn"
                      onClick={() => deleteTask(task.id)}
                      title="Delete task"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
            </div>
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
          <span className="tech-badge">SQLite</span>
          <span className="tech-badge">Docker Compose</span>
        </footer>
      </main>
    </div>
  )
}

export default App
