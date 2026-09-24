import React, {
  useState,
  useMemo,
  useEffect,
  useCallback,
  createContext,
  useContext,
} from "react";
import "./App.css";

/* =========================================================
   TYPES / CONSTANTS
========================================================= */

const TASK_STATUS = {
  TODO: "todo",
  IN_PROGRESS: "in-progress",
  COMPLETED: "completed",
};

const PRIORITY = {
  LOW: "low",
  MEDIUM: "medium",
  HIGH: "high",
};

const initialTasks = [
  {
    id: 1,
    title: "Build authentication system",
    description: "Implement JWT authentication with refresh tokens.",
    status: TASK_STATUS.IN_PROGRESS,
    priority: PRIORITY.HIGH,
    assignee: "Aman",
    dueDate: "2026-09-28",
    tags: ["backend", "security"],
    createdAt: "2026-09-20",
  },
  {
    id: 2,
    title: "Create dashboard UI",
    description: "Build the main dashboard using React and Tailwind.",
    status: TASK_STATUS.TODO,
    priority: PRIORITY.MEDIUM,
    assignee: "Rahul",
    dueDate: "2026-09-30",
    tags: ["frontend", "ui"],
    createdAt: "2026-09-21",
  },
  {
    id: 3,
    title: "Optimize database queries",
    description: "Review slow MongoDB queries and add indexes.",
    status: TASK_STATUS.COMPLETED,
    priority: PRIORITY.HIGH,
    assignee: "Aman",
    dueDate: "2026-09-25",
    tags: ["database", "optimization"],
    createdAt: "2026-09-18",
  },
  {
    id: 4,
    title: "Write API documentation",
    description: "Document all REST API endpoints.",
    status: TASK_STATUS.TODO,
    priority: PRIORITY.LOW,
    assignee: "Priya",
    dueDate: "2026-10-02",
    tags: ["documentation"],
    createdAt: "2026-09-22",
  },
  {
    id: 5,
    title: "Fix mobile navigation",
    description: "Resolve navigation issues on small screens.",
    status: TASK_STATUS.IN_PROGRESS,
    priority: PRIORITY.MEDIUM,
    assignee: "Rahul",
    dueDate: "2026-09-27",
    tags: ["frontend", "bug"],
    createdAt: "2026-09-23",
  },
];

/* =========================================================
   CONTEXT
========================================================= */

const TaskContext = createContext(null);

function TaskProvider({ children }) {
  const [tasks, setTasks] = useState(initialTasks);

  const addTask = useCallback((task) => {
    setTasks((currentTasks) => [
      ...currentTasks,
      {
        ...task,
        id: Date.now(),
        createdAt: new Date().toISOString().split("T")[0],
      },
    ]);
  }, []);

  const updateTask = useCallback((id, updates) => {
    setTasks((currentTasks) =>
      currentTasks.map((task) =>
        task.id === id ? { ...task, ...updates } : task
      )
    );
  }, []);

  const deleteTask = useCallback((id) => {
    setTasks((currentTasks) =>
      currentTasks.filter((task) => task.id !== id)
    );
  }, []);

  const toggleTaskStatus = useCallback((id) => {
    setTasks((currentTasks) =>
      currentTasks.map((task) => {
        if (task.id !== id) {
          return task;
        }

        const nextStatus =
          task.status === TASK_STATUS.COMPLETED
            ? TASK_STATUS.TODO
            : TASK_STATUS.COMPLETED;

        return {
          ...task,
          status: nextStatus,
        };
      })
    );
  }, []);

  const value = {
    tasks,
    addTask,
    updateTask,
    deleteTask,
    toggleTaskStatus,
  };

  return (
    <TaskContext.Provider value={value}>
      {children}
    </TaskContext.Provider>
  );
}

function useTasks() {
  const context = useContext(TaskContext);

  if (!context) {
    throw new Error("useTasks must be used inside TaskProvider");
  }

  return context;
}

/* =========================================================
   APP
========================================================= */

export default function App() {
  return (
    <TaskProvider>
      <Dashboard />
    </TaskProvider>
  );
}

/* =========================================================
   DASHBOARD
========================================================= */

function Dashboard() {
  const { tasks } = useTasks();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [showModal, setShowModal] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);

  const filteredTasks = useMemo(() => {
    return tasks.filter((task) => {
      const matchesSearch =
        task.title.toLowerCase().includes(search.toLowerCase()) ||
        task.description.toLowerCase().includes(search.toLowerCase()) ||
        task.assignee.toLowerCase().includes(search.toLowerCase());

      const matchesStatus =
        statusFilter === "all" ||
        task.status === statusFilter;

      const matchesPriority =
        priorityFilter === "all" ||
        task.priority === priorityFilter;

      return (
        matchesSearch &&
        matchesStatus &&
        matchesPriority
      );
    });
  }, [tasks, search, statusFilter, priorityFilter]);

  const handleEditTask = (task) => {
    setSelectedTask(task);
    setShowModal(true);
  };

  const handleCreateTask = () => {
    setSelectedTask(null);
    setShowModal(true);
  };

  return (
    <div className="app">
      <Sidebar />

      <main className="main-content">
        <Header onCreateTask={handleCreateTask} />

        <section className="content">
          <Stats />

          <div className="toolbar">
            <SearchBox
              value={search}
              onChange={setSearch}
            />

            <FilterSelect
              label="Status"
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { value: "all", label: "All Statuses" },
                { value: TASK_STATUS.TODO, label: "Todo" },
                {
                  value: TASK_STATUS.IN_PROGRESS,
                  label: "In Progress",
                },
                {
                  value: TASK_STATUS.COMPLETED,
                  label: "Completed",
                },
              ]}
            />

            <FilterSelect
              label="Priority"
              value={priorityFilter}
              onChange={setPriorityFilter}
              options={[
                { value: "all", label: "All Priorities" },
                { value: PRIORITY.LOW, label: "Low" },
                { value: PRIORITY.MEDIUM, label: "Medium" },
                { value: PRIORITY.HIGH, label: "High" },
              ]}
            />
          </div>

          <div className="task-section">
            <div className="section-header">
              <div>
                <h2>Tasks</h2>
                <p>
                  Showing {filteredTasks.length} of {tasks.length} tasks
                </p>
              </div>
            </div>

            <TaskList
              tasks={filteredTasks}
              onEdit={handleEditTask}
            />
          </div>
        </section>
      </main>

      {showModal && (
        <TaskModal
          task={selectedTask}
          onClose={() => {
            setShowModal(false);
            setSelectedTask(null);
          }}
        />
      )}
    </div>
  );
}

/* =========================================================
   SIDEBAR
========================================================= */

function Sidebar() {
  const [activeItem, setActiveItem] = useState("Dashboard");

  const menuItems = [
    {
      name: "Dashboard",
      icon: "▦",
    },
    {
      name: "My Tasks",
      icon: "✓",
    },
    {
      name: "Projects",
      icon: "▤",
    },
    {
      name: "Team",
      icon: "♟",
    },
    {
      name: "Calendar",
      icon: "□",
    },
  ];

  return (
    <aside className="sidebar">
      <div className="logo">
        <div className="logo-icon">T</div>
        <span>TaskFlow</span>
      </div>

      <nav className="navigation">
        <p className="nav-label">WORKSPACE</p>

        {menuItems.map((item) => (
          <button
            key={item.name}
            className={`nav-item ${
              activeItem === item.name ? "active" : ""
            }`}
            onClick={() => setActiveItem(item.name)}
          >
            <span className="nav-icon">{item.icon}</span>
            {item.name}
          </button>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <button className="nav-item">
          <span className="nav-icon">⚙</span>
          Settings
        </button>

        <div className="user-card">
          <div className="avatar">AJ</div>

          <div className="user-info">
            <strong>Aman Jeet</strong>
            <span>Developer</span>
          </div>

          <button className="more-button">⋮</button>
        </div>
      </div>
    </aside>
  );
}

/* =========================================================
   HEADER
========================================================= */

function Header({ onCreateTask }) {
  const [notifications, setNotifications] = useState(3);

  const clearNotifications = () => {
    setNotifications(0);
  };

  return (
    <header className="header">
      <div>
        <h1>Good evening, Aman 👋</h1>
        <p>Here's what's happening with your projects today.</p>
      </div>

      <div className="header-actions">
        <button
          className="notification-button"
          onClick={clearNotifications}
        >
          🔔

          {notifications > 0 && (
            <span className="notification-badge">
              {notifications}
            </span>
          )}
        </button>

        <button
          className="primary-button"
          onClick={onCreateTask}
        >
          + New Task
        </button>
      </div>
    </header>
  );
}

/* =========================================================
   STATS
========================================================= */

function Stats() {
  const { tasks } = useTasks();

  const stats = useMemo(() => {
    const completed = tasks.filter(
      (task) => task.status === TASK_STATUS.COMPLETED
    ).length;

    const inProgress = tasks.filter(
      (task) => task.status === TASK_STATUS.IN_PROGRESS
    ).length;

    const todo = tasks.filter(
      (task) => task.status === TASK_STATUS.TODO
    ).length;

    const highPriority = tasks.filter(
      (task) => task.priority === PRIORITY.HIGH
    ).length;

    return {
      completed,
      inProgress,
      todo,
      highPriority,
    };
  }, [tasks]);

  const cards = [
    {
      title: "Total Tasks",
      value: tasks.length,
      icon: "▦",
      description: "Across all projects",
    },
    {
      title: "Completed",
      value: stats.completed,
      icon: "✓",
      description: "Tasks completed",
    },
    {
      title: "In Progress",
      value: stats.inProgress,
      icon: "◷",
      description: "Currently working on",
    },
    {
      title: "High Priority",
      value: stats.highPriority,
      icon: "!",
      description: "Need attention",
    },
  ];

  return (
    <div className="stats-grid">
      {cards.map((card) => (
        <StatCard
          key={card.title}
          {...card}
        />
      ))}
    </div>
  );
}

function StatCard({
  title,
  value,
  icon,
  description,
}) {
  return (
    <div className="stat-card">
      <div className="stat-top">
        <div className="stat-icon">{icon}</div>

        <span className="stat-menu">⋮</span>
      </div>

      <div className="stat-value">{value}</div>

      <div className="stat-title">{title}</div>

      <div className="stat-description">
        {description}
      </div>
    </div>
  );
}

/* =========================================================
   SEARCH
========================================================= */

function SearchBox({ value, onChange }) {
  return (
    <div className="search-box">
      <span>⌕</span>

      <input
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Search tasks..."
      />

      {value && (
        <button
          className="clear-search"
          onClick={() => onChange("")}
        >
          ×
        </button>
      )}
    </div>
  );
}

/* =========================================================
   FILTER
========================================================= */

function FilterSelect({
  label,
  value,
  onChange,
  options,
}) {
  return (
    <div className="filter">
      <label>{label}</label>

      <select
        value={value}
        onChange={(event) =>
          onChange(event.target.value)
        }
      >
        {options.map((option) => (
          <option
            key={option.value}
            value={option.value}
          >
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

/* =========================================================
   TASK LIST
========================================================= */

function TaskList({ tasks, onEdit }) {
  const { deleteTask, toggleTaskStatus } = useTasks();

  if (tasks.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">⌕</div>

        <h3>No tasks found</h3>

        <p>
          Try changing your search or filter options.
        </p>
      </div>
    );
  }

  return (
    <div className="task-list">
      {tasks.map((task) => (
        <TaskCard
          key={task.id}
          task={task}
          onEdit={onEdit}
          onDelete={deleteTask}
          onToggle={toggleTaskStatus}
        />
      ))}
    </div>
  );
}

/* =========================================================
   TASK CARD
========================================================= */

function TaskCard({
  task,
  onEdit,
  onDelete,
  onToggle,
}) {
  const [showMenu, setShowMenu] = useState(false);

  const statusLabel = {
    [TASK_STATUS.TODO]: "Todo",
    [TASK_STATUS.IN_PROGRESS]: "In Progress",
    [TASK_STATUS.COMPLETED]: "Completed",
  };

  const priorityLabel = {
    [PRIORITY.LOW]: "Low",
    [PRIORITY.MEDIUM]: "Medium",
    [PRIORITY.HIGH]: "High",
  };

  return (
    <article className="task-card">
      <div className="task-checkbox-wrapper">
        <button
          className={`task-checkbox ${
            task.status === TASK_STATUS.COMPLETED
              ? "checked"
              : ""
          }`}
          onClick={() => onToggle(task.id)}
        >
          {task.status === TASK_STATUS.COMPLETED
            ? "✓"
            : ""}
        </button>
      </div>

      <div className="task-main">
        <div className="task-heading">
          <h3
            className={
              task.status === TASK_STATUS.COMPLETED
                ? "completed-title"
                : ""
            }
          >
            {task.title}
          </h3>

          <span
            className={`priority ${task.priority}`}
          >
            {priorityLabel[task.priority]}
          </span>
        </div>

        <p className="task-description">
          {task.description}
        </p>

        <div className="task-meta">
          <span
            className={`status ${task.status}`}
          >
            {statusLabel[task.status]}
          </span>

          <span className="meta-separator">•</span>

          <span>👤 {task.assignee}</span>

          <span className="meta-separator">•</span>

          <span>📅 {task.dueDate}</span>
        </div>

        <div className="tag-list">
          {task.tags.map((tag) => (
            <span
              className="tag"
              key={tag}
            >
              #{tag}
            </span>
          ))}
        </div>
      </div>

      <div className="task-actions">
        <button
          className="more-button"
          onClick={() => setShowMenu(!showMenu)}
        >
          ⋮
        </button>

        {showMenu && (
          <div className="task-menu">
            <button
              onClick={() => {
                onEdit(task);
                setShowMenu(false);
              }}
            >
              Edit
            </button>

            <button
              onClick={() => {
                onToggle(task.id);
                setShowMenu(false);
              }}
            >
              Mark{" "}
              {task.status === TASK_STATUS.COMPLETED
                ? "Todo"
                : "Completed"}
            </button>

            <button
              className="danger"
              onClick={() => {
                onDelete(task.id);
                setShowMenu(false);
              }}
            >
              Delete
            </button>
          </div>
        )}
      </div>
    </article>
  );
}

/* =========================================================
   TASK MODAL
========================================================= */

function TaskModal({ task, onClose }) {
  const { addTask, updateTask } = useTasks();

  const [form, setForm] = useState({
    title: task?.title || "",
    description: task?.description || "",
    status: task?.status || TASK_STATUS.TODO,
    priority: task?.priority || PRIORITY.MEDIUM,
    assignee: task?.assignee || "",
    dueDate: task?.dueDate || "",
    tags: task?.tags?.join(", ") || "",
  });

  const [errors, setErrors] = useState({});

  const isEditing = Boolean(task);

  useEffect(() => {
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = "auto";
    };
  }, []);

  const updateField = (field, value) => {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));

    setErrors((current) => ({
      ...current,
      [field]: "",
    }));
  };

  const validate = () => {
    const nextErrors = {};

    if (!form.title.trim()) {
      nextErrors.title = "Title is required";
    }

    if (!form.description.trim()) {
      nextErrors.description =
        "Description is required";
    }

    if (!form.assignee.trim()) {
      nextErrors.assignee =
        "Assignee is required";
    }

    if (!form.dueDate) {
      nextErrors.dueDate =
        "Due date is required";
    }

    return nextErrors;
  };

  const handleSubmit = (event) => {
    event.preventDefault();

    const validationErrors = validate();

    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    const taskData = {
      ...form,
      tags: form.tags
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean),
    };

    if (isEditing) {
      updateTask(task.id, taskData);
    } else {
      addTask(taskData);
    }

    onClose();
  };

  return (
    <div
      className="modal-overlay"
      onMouseDown={onClose}
    >
      <div
        className="modal"
        onMouseDown={(event) =>
          event.stopPropagation()
        }
      >
        <div className="modal-header">
          <div>
            <h2>
              {isEditing
                ? "Edit Task"
                : "Create New Task"}
            </h2>

            <p>
              {isEditing
                ? "Update the task details."
                : "Add a new task to your workspace."}
            </p>
          </div>

          <button
            className="close-button"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <FormField
            label="Title"
            error={errors.title}
          >
            <input
              value={form.title}
              onChange={(event) =>
                updateField(
                  "title",
                  event.target.value
                )
              }
              placeholder="Enter task title"
            />
          </FormField>

          <FormField
            label="Description"
            error={errors.description}
          >
            <textarea
              value={form.description}
              onChange={(event) =>
                updateField(
                  "description",
                  event.target.value
                )
              }
              placeholder="Describe the task..."
              rows={4}
            />
          </FormField>

          <div className="form-row">
            <FormField label="Status">
              <select
                value={form.status}
                onChange={(event) =>
                  updateField(
                    "status",
                    event.target.value
                  )
                }
              >
                <option value={TASK_STATUS.TODO}>
                  Todo
                </option>

                <option
                  value={TASK_STATUS.IN_PROGRESS}
                >
                  In Progress
                </option>

                <option
                  value={TASK_STATUS.COMPLETED}
                >
                  Completed
                </option>
              </select>
            </FormField>

            <FormField label="Priority">
              <select
                value={form.priority}
                onChange={(event) =>
                  updateField(
                    "priority",
                    event.target.value
                  )
                }
              >
                <option value={PRIORITY.LOW}>
                  Low
                </option>

                <option value={PRIORITY.MEDIUM}>
                  Medium
                </option>

                <option value={PRIORITY.HIGH}>
                  High
                </option>
              </select>
            </FormField>
          </div>

          <div className="form-row">
            <FormField
              label="Assignee"
              error={errors.assignee}
            >
              <input
                value={form.assignee}
                onChange={(event) =>
                  updateField(
                    "assignee",
                    event.target.value
                  )
                }
                placeholder="e.g. Aman"
              />
            </FormField>

            <FormField
              label="Due Date"
              error={errors.dueDate}
            >
              <input
                type="date"
                value={form.dueDate}
                onChange={(event) =>
                  updateField(
                    "dueDate",
                    event.target.value
                  )
                }
              />
            </FormField>
          </div>

          <FormField label="Tags">
            <input
              value={form.tags}
              onChange={(event) =>
                updateField(
                  "tags",
                  event.target.value
                )
              }
              placeholder="frontend, react, bug"
            />

            <small>
              Separate tags using commas.
            </small>
          </FormField>

          <div className="modal-footer">
            <button
              type="button"
              className="secondary-button"
              onClick={onClose}
            >
              Cancel
            </button>

            <button
              type="submit"
              className="primary-button"
            >
              {isEditing
                ? "Save Changes"
                : "Create Task"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* =========================================================
   FORM FIELD
========================================================= */

function FormField({
  label,
  error,
  children,
}) {
  return (
    <div className="form-field">
      <label>{label}</label>

      {children}

      {error && (
        <span className="error">
          {error}
        </span>
      )}
    </div>
  );
}

/* =========================================================
   CUSTOM HOOK
========================================================= */

function useDebounce(value, delay = 500) {
  const [debouncedValue, setDebouncedValue] =
    useState(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

/* =========================================================
   EXAMPLE API HOOK
========================================================= */

function useTasksApi() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchTasks = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        "/api/tasks"
      );

      if (!response.ok) {
        throw new Error(
          "Failed to fetch tasks"
        );
      }

      const result = await response.json();

      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    data,
    loading,
    error,
    fetchTasks,
  };
}

/* =========================================================
   UTILITY FUNCTIONS
========================================================= */

function formatDate(dateString) {
  if (!dateString) {
    return "";
  }

  const date = new Date(dateString);

  return date.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function getPriorityWeight(priority) {
  switch (priority) {
    case PRIORITY.HIGH:
      return 3;

    case PRIORITY.MEDIUM:
      return 2;

    case PRIORITY.LOW:
      return 1;

    default:
      return 0;
  }
}

function sortTasksByPriority(tasks) {
  return [...tasks].sort(
    (a, b) =>
      getPriorityWeight(b.priority) -
      getPriorityWeight(a.priority)
  );
}

function sortTasksByDate(tasks) {
  return [...tasks].sort(
    (a, b) =>
      new Date(a.dueDate) -
      new Date(b.dueDate)
  );
}

/* =========================================================
   EXAMPLE TASK SERVICE
========================================================= */

const taskService = {
  async getAll() {
    const response = await fetch("/api/tasks");

    if (!response.ok) {
      throw new Error("Could not fetch tasks");
    }

    return response.json();
  },

  async getById(id) {
    const response = await fetch(
      `/api/tasks/${id}`
    );

    if (!response.ok) {
      throw new Error("Task not found");
    }

    return response.json();
  },

  async create(task) {
    const response = await fetch("/api/tasks", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(task),
    });

    if (!response.ok) {
      throw new Error("Could not create task");
    }

    return response.json();
  },

  async update(id, task) {
    const response = await fetch(
      `/api/tasks/${id}`,
      {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(task),
      }
    );

    if (!response.ok) {
      throw new Error("Could not update task");
    }

    return response.json();
  },

  async delete(id) {
    const response = await fetch(
      `/api/tasks/${id}`,
      {
        method: "DELETE",
      }
    );

    if (!response.ok) {
      throw new Error("Could not delete task");
    }

    return true;
  },
};

/* =========================================================
   PERFORMANCE EXAMPLE
========================================================= */

const ExpensiveTaskList = React.memo(
  function ExpensiveTaskList({
    tasks,
  }) {
    return (
      <div>
        {tasks.map((task) => (
          <div key={task.id}>
            {task.title}
          </div>
        ))}
      </div>
    );
  }
);

/* =========================================================
   ERROR BOUNDARY
========================================================= */

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error, errorInfo) {
    console.error(
      "React error:",
      error,
      errorInfo
    );
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-page">
          <h1>Something went wrong.</h1>

          <p>
            {this.state.error?.message}
          </p>

          <button
            onClick={() =>
              window.location.reload()
            }
          >
            Reload
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

/* =========================================================
   APP ENTRY
========================================================= */

function Root() {
  return (
    <ErrorBoundary>
      <TaskProvider>
        <Dashboard />
      </TaskProvider>
    </ErrorBoundary>
  );
}