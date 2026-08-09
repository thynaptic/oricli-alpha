package memory

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

// TaskStatus is a DAG-aware task/step lifecycle state.
type TaskStatus string

const (
	StatusPending   TaskStatus = "pending"
	StatusRunning   TaskStatus = "running"
	StatusDone      TaskStatus = "done"
	StatusFailed    TaskStatus = "failed"
	StatusCancelled TaskStatus = "cancelled"
)

// TaskStore is a local SQLite task list with optional step DAG.
type TaskStore struct {
	db *sql.DB
}

type Task struct {
	ID          int64      `json:"id"`
	Title       string     `json:"title"`
	Description string     `json:"description,omitempty"`
	Status      TaskStatus `json:"status"`
	Priority    int        `json:"priority"`
	Done        bool       `json:"done"` // derived from status for backward compat
	CreatedAt   time.Time  `json:"created_at"`
	UpdatedAt   time.Time  `json:"updated_at"`
	Steps       []Step     `json:"steps,omitempty"`
}

type Step struct {
	ID          string     `json:"id"`
	TaskID      int64      `json:"task_id"`
	Title       string     `json:"title"`
	OrderNum    int        `json:"order_num"`
	DependsOn   []string   `json:"depends_on"`
	Status      TaskStatus `json:"status"`
	Result      string     `json:"result,omitempty"`
	CreatedAt   time.Time  `json:"created_at"`
	CompletedAt *time.Time `json:"completed_at,omitempty"`
}

type StepInput struct {
	ID        string   `json:"id,omitempty"`
	Title     string   `json:"title"`
	OrderNum  int      `json:"order_num,omitempty"`
	DependsOn []string `json:"depends_on,omitempty"`
}

func OpenTaskStore(dir string) (*TaskStore, error) {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, err
	}
	path := filepath.Join(dir, "tasks.db")
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, err
	}
	store := &TaskStore{db: db}
	if err := store.migrate(); err != nil {
		_ = db.Close()
		return nil, err
	}
	return store, nil
}

func (t *TaskStore) migrate() error {
	if _, err := t.db.Exec(`CREATE TABLE IF NOT EXISTS tasks (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		done INTEGER NOT NULL DEFAULT 0,
		created_at TEXT NOT NULL
	)`); err != nil {
		return err
	}
	// Additive columns for DAG deepen (ignore if already present).
	for _, stmt := range []string{
		`ALTER TABLE tasks ADD COLUMN description TEXT NOT NULL DEFAULT ''`,
		`ALTER TABLE tasks ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'`,
		`ALTER TABLE tasks ADD COLUMN priority INTEGER NOT NULL DEFAULT 0`,
		`ALTER TABLE tasks ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''`,
	} {
		_, _ = t.db.Exec(stmt)
	}
	if _, err := t.db.Exec(`CREATE TABLE IF NOT EXISTS task_steps (
		id TEXT PRIMARY KEY,
		task_id INTEGER NOT NULL,
		order_num INTEGER NOT NULL DEFAULT 0,
		title TEXT NOT NULL,
		status TEXT NOT NULL DEFAULT 'pending',
		depends_on TEXT NOT NULL DEFAULT '[]',
		result TEXT NOT NULL DEFAULT '',
		created_at TEXT NOT NULL,
		completed_at TEXT
	)`); err != nil {
		return err
	}
	// Backfill status from done for rows that still look legacy.
	_, _ = t.db.Exec(`UPDATE tasks SET status='done' WHERE done=1 AND (status='' OR status='pending')`)
	_, _ = t.db.Exec(`UPDATE tasks SET updated_at=created_at WHERE updated_at=''`)
	return nil
}

func (t *TaskStore) Close() error {
	if t == nil || t.db == nil {
		return nil
	}
	return t.db.Close()
}

func (t *TaskStore) Add(title string) (Task, error) {
	return t.AddFull(title, "", 0, nil)
}

func (t *TaskStore) AddFull(title, description string, priority int, steps []StepInput) (Task, error) {
	title = strings.TrimSpace(title)
	if title == "" {
		return Task{}, fmt.Errorf("title required")
	}
	now := time.Now().UTC()
	res, err := t.db.Exec(
		`INSERT INTO tasks(title, description, status, priority, done, created_at, updated_at) VALUES(?,?,?,?,?,?,?)`,
		title, description, string(StatusPending), priority, 0, now.Format(time.RFC3339), now.Format(time.RFC3339),
	)
	if err != nil {
		return Task{}, err
	}
	id, _ := res.LastInsertId()
	for i, s := range steps {
		if strings.TrimSpace(s.Title) == "" {
			continue
		}
		order := s.OrderNum
		if order == 0 {
			order = i + 1
		}
		sid := strings.TrimSpace(s.ID)
		if sid == "" {
			sid = fmt.Sprintf("s%d_%d", id, order)
		}
		deps, _ := json.Marshal(s.DependsOn)
		if _, err := t.db.Exec(
			`INSERT INTO task_steps(id, task_id, order_num, title, status, depends_on, result, created_at) VALUES(?,?,?,?,?,?,?,?)`,
			sid, id, order, s.Title, string(StatusPending), string(deps), "", now.Format(time.RFC3339),
		); err != nil {
			return Task{}, err
		}
	}
	return t.Get(id, true)
}

func (t *TaskStore) Get(id int64, withSteps bool) (Task, error) {
	row := t.db.QueryRow(
		`SELECT id, title, COALESCE(description,''), COALESCE(status,'pending'), COALESCE(priority,0), done, created_at, COALESCE(updated_at,'') FROM tasks WHERE id=?`,
		id,
	)
	task, err := scanTask(row)
	if err != nil {
		return Task{}, err
	}
	if withSteps {
		steps, err := t.listSteps(id)
		if err != nil {
			return Task{}, err
		}
		task.Steps = steps
	}
	return task, nil
}

func (t *TaskStore) List(limit int) ([]Task, error) {
	return t.ListFilter(limit, "")
}

func (t *TaskStore) ListFilter(limit int, status string) ([]Task, error) {
	if limit <= 0 {
		limit = 50
	}
	var (
		rows *sql.Rows
		err  error
	)
	if status != "" {
		rows, err = t.db.Query(
			`SELECT id, title, COALESCE(description,''), COALESCE(status,'pending'), COALESCE(priority,0), done, created_at, COALESCE(updated_at,'')
			 FROM tasks WHERE status=? ORDER BY priority DESC, id DESC LIMIT ?`, status, limit)
	} else {
		rows, err = t.db.Query(
			`SELECT id, title, COALESCE(description,''), COALESCE(status,'pending'), COALESCE(priority,0), done, created_at, COALESCE(updated_at,'')
			 FROM tasks ORDER BY priority DESC, id DESC LIMIT ?`, limit)
	}
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []Task
	for rows.Next() {
		task, err := scanTask(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, task)
	}
	return out, rows.Err()
}

func (t *TaskStore) SetDone(id int64, done bool) error {
	status := StatusPending
	if done {
		status = StatusDone
	}
	return t.SetStatus(id, status)
}

func (t *TaskStore) SetStatus(id int64, status TaskStatus) error {
	status = normalizeStatus(status)
	done := 0
	if status == StatusDone {
		done = 1
	}
	now := time.Now().UTC().Format(time.RFC3339)
	res, err := t.db.Exec(`UPDATE tasks SET status=?, done=?, updated_at=? WHERE id=?`, string(status), done, now, id)
	if err != nil {
		return err
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		return fmt.Errorf("task %d not found", id)
	}
	return nil
}

func (t *TaskStore) AddStep(taskID int64, in StepInput) (Step, error) {
	if _, err := t.Get(taskID, false); err != nil {
		return Step{}, err
	}
	title := strings.TrimSpace(in.Title)
	if title == "" {
		return Step{}, fmt.Errorf("title required")
	}
	order := in.OrderNum
	if order == 0 {
		var max sql.NullInt64
		_ = t.db.QueryRow(`SELECT MAX(order_num) FROM task_steps WHERE task_id=?`, taskID).Scan(&max)
		order = int(max.Int64) + 1
	}
	sid := strings.TrimSpace(in.ID)
	if sid == "" {
		sid = fmt.Sprintf("s%d_%d_%d", taskID, order, time.Now().UnixNano()%100000)
	}
	now := time.Now().UTC()
	deps, _ := json.Marshal(in.DependsOn)
	if _, err := t.db.Exec(
		`INSERT INTO task_steps(id, task_id, order_num, title, status, depends_on, result, created_at) VALUES(?,?,?,?,?,?,?,?)`,
		sid, taskID, order, title, string(StatusPending), string(deps), "", now.Format(time.RFC3339),
	); err != nil {
		return Step{}, err
	}
	_ = t.touch(taskID)
	return t.getStep(sid)
}

func (t *TaskStore) SetStepStatus(taskID int64, stepID string, status TaskStatus, result string) (Step, error) {
	status = normalizeStatus(status)
	var completed any
	if status == StatusDone || status == StatusFailed || status == StatusCancelled {
		completed = time.Now().UTC().Format(time.RFC3339)
	}
	res, err := t.db.Exec(
		`UPDATE task_steps SET status=?, result=?, completed_at=? WHERE id=? AND task_id=?`,
		string(status), result, completed, stepID, taskID,
	)
	if err != nil {
		return Step{}, err
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		return Step{}, fmt.Errorf("step %s not found", stepID)
	}
	_ = t.touch(taskID)
	// Roll up task status when all steps done.
	steps, _ := t.listSteps(taskID)
	if len(steps) > 0 {
		allDone := true
		anyFailed := false
		for _, s := range steps {
			if s.Status == StatusFailed {
				anyFailed = true
			}
			if s.Status != StatusDone && s.Status != StatusCancelled {
				allDone = false
			}
		}
		if anyFailed {
			_ = t.SetStatus(taskID, StatusFailed)
		} else if allDone {
			_ = t.SetStatus(taskID, StatusDone)
		}
	}
	return t.getStep(stepID)
}

// ReadySteps returns steps whose dependencies are all done.
func (t *TaskStore) ReadySteps(taskID int64) ([]Step, error) {
	steps, err := t.listSteps(taskID)
	if err != nil {
		return nil, err
	}
	byID := map[string]Step{}
	for _, s := range steps {
		byID[s.ID] = s
	}
	var ready []Step
	for _, s := range steps {
		if s.Status != StatusPending {
			continue
		}
		ok := true
		for _, dep := range s.DependsOn {
			d, exists := byID[dep]
			if !exists || d.Status != StatusDone {
				ok = false
				break
			}
		}
		if ok {
			ready = append(ready, s)
		}
	}
	return ready, nil
}

func (t *TaskStore) touch(id int64) error {
	_, err := t.db.Exec(`UPDATE tasks SET updated_at=? WHERE id=?`, time.Now().UTC().Format(time.RFC3339), id)
	return err
}

func (t *TaskStore) listSteps(taskID int64) ([]Step, error) {
	rows, err := t.db.Query(
		`SELECT id, task_id, order_num, title, status, depends_on, result, created_at, completed_at
		 FROM task_steps WHERE task_id=? ORDER BY order_num ASC, id ASC`, taskID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []Step
	for rows.Next() {
		s, err := scanStep(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, s)
	}
	return out, rows.Err()
}

func (t *TaskStore) getStep(id string) (Step, error) {
	row := t.db.QueryRow(
		`SELECT id, task_id, order_num, title, status, depends_on, result, created_at, completed_at FROM task_steps WHERE id=?`, id)
	return scanStep(row)
}

type scanner interface {
	Scan(dest ...any) error
}

func scanTask(row scanner) (Task, error) {
	var task Task
	var doneInt int
	var created, updated, status string
	if err := row.Scan(&task.ID, &task.Title, &task.Description, &status, &task.Priority, &doneInt, &created, &updated); err != nil {
		if err == sql.ErrNoRows {
			return Task{}, fmt.Errorf("task not found")
		}
		return Task{}, err
	}
	task.Status = normalizeStatus(TaskStatus(status))
	if doneInt == 1 {
		task.Done = true
		if task.Status == StatusPending {
			task.Status = StatusDone
		}
	} else {
		task.Done = task.Status == StatusDone
	}
	task.CreatedAt, _ = time.Parse(time.RFC3339, created)
	if updated != "" {
		task.UpdatedAt, _ = time.Parse(time.RFC3339, updated)
	} else {
		task.UpdatedAt = task.CreatedAt
	}
	return task, nil
}

func scanStep(row scanner) (Step, error) {
	var s Step
	var deps, created string
	var completed sql.NullString
	var status string
	if err := row.Scan(&s.ID, &s.TaskID, &s.OrderNum, &s.Title, &status, &deps, &s.Result, &created, &completed); err != nil {
		if err == sql.ErrNoRows {
			return Step{}, fmt.Errorf("step not found")
		}
		return Step{}, err
	}
	s.Status = normalizeStatus(TaskStatus(status))
	_ = json.Unmarshal([]byte(deps), &s.DependsOn)
	if s.DependsOn == nil {
		s.DependsOn = []string{}
	}
	s.CreatedAt, _ = time.Parse(time.RFC3339, created)
	if completed.Valid && completed.String != "" {
		tm, _ := time.Parse(time.RFC3339, completed.String)
		s.CompletedAt = &tm
	}
	return s, nil
}

func normalizeStatus(s TaskStatus) TaskStatus {
	switch TaskStatus(strings.ToLower(string(s))) {
	case StatusRunning, StatusDone, StatusFailed, StatusCancelled:
		return TaskStatus(strings.ToLower(string(s)))
	default:
		return StatusPending
	}
}
