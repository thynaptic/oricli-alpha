package memory

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"time"

	_ "modernc.org/sqlite"
)

// TaskStore is a local SQLite task list (consumer-simple).
type TaskStore struct {
	db *sql.DB
}

type Task struct {
	ID        int64     `json:"id"`
	Title     string    `json:"title"`
	Done      bool      `json:"done"`
	CreatedAt time.Time `json:"created_at"`
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
	if _, err := db.Exec(`CREATE TABLE IF NOT EXISTS tasks (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		done INTEGER NOT NULL DEFAULT 0,
		created_at TEXT NOT NULL
	)`); err != nil {
		_ = db.Close()
		return nil, err
	}
	return &TaskStore{db: db}, nil
}

func (t *TaskStore) Close() error {
	if t == nil || t.db == nil {
		return nil
	}
	return t.db.Close()
}

func (t *TaskStore) Add(title string) (Task, error) {
	now := time.Now().UTC()
	res, err := t.db.Exec(`INSERT INTO tasks(title, done, created_at) VALUES(?,?,?)`, title, 0, now.Format(time.RFC3339))
	if err != nil {
		return Task{}, err
	}
	id, _ := res.LastInsertId()
	return Task{ID: id, Title: title, Done: false, CreatedAt: now}, nil
}

func (t *TaskStore) List(limit int) ([]Task, error) {
	if limit <= 0 {
		limit = 50
	}
	rows, err := t.db.Query(`SELECT id, title, done, created_at FROM tasks ORDER BY id DESC LIMIT ?`, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []Task
	for rows.Next() {
		var task Task
		var doneInt int
		var created string
		if err := rows.Scan(&task.ID, &task.Title, &doneInt, &created); err != nil {
			return nil, err
		}
		task.Done = doneInt == 1
		task.CreatedAt, _ = time.Parse(time.RFC3339, created)
		out = append(out, task)
	}
	return out, rows.Err()
}

func (t *TaskStore) SetDone(id int64, done bool) error {
	v := 0
	if done {
		v = 1
	}
	res, err := t.db.Exec(`UPDATE tasks SET done=? WHERE id=?`, v, id)
	if err != nil {
		return err
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		return fmt.Errorf("task %d not found", id)
	}
	return nil
}
