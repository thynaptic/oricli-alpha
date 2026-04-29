package tasks

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"
	_ "modernc.org/sqlite"
)

const schema = `
CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL,
    session_id  TEXT NOT NULL DEFAULT '',
    surface     TEXT NOT NULL DEFAULT 'api',
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'pending',
    priority    INTEGER NOT NULL DEFAULT 0,
    metadata    TEXT NOT NULL DEFAULT '{}',
    created_at  DATETIME NOT NULL,
    updated_at  DATETIME NOT NULL,
    resolved_at DATETIME
);

CREATE TABLE IF NOT EXISTS task_steps (
    id           TEXT PRIMARY KEY,
    task_id      TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    order_num    INTEGER NOT NULL DEFAULT 0,
    title        TEXT NOT NULL,
    action       TEXT NOT NULL,
    args         TEXT NOT NULL DEFAULT '{}',
    depends_on   TEXT NOT NULL DEFAULT '[]',
    status       TEXT NOT NULL DEFAULT 'pending',
    result       TEXT NOT NULL DEFAULT '',
    created_at   DATETIME NOT NULL,
    completed_at DATETIME
);

CREATE TABLE IF NOT EXISTS entities (
    id         TEXT PRIMARY KEY,
    tenant_id  TEXT NOT NULL,
    name       TEXT NOT NULL,
    kind       TEXT NOT NULL DEFAULT 'unknown',
    aliases    TEXT NOT NULL DEFAULT '[]',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS entity_events (
    id          TEXT PRIMARY KEY,
    entity_id   TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    task_id     TEXT NOT NULL DEFAULT '',
    kind        TEXT NOT NULL,
    content     TEXT NOT NULL DEFAULT '',
    metadata    TEXT NOT NULL DEFAULT '{}',
    occurred_at DATETIME NOT NULL,
    created_at  DATETIME NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_tenant   ON tasks(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status   ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_surface  ON tasks(surface);
CREATE INDEX IF NOT EXISTS idx_steps_task     ON task_steps(task_id);
CREATE INDEX IF NOT EXISTS idx_entities_tenant ON entities(tenant_id);
CREATE INDEX IF NOT EXISTS idx_entity_events_entity   ON entity_events(entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_events_occurred ON entity_events(occurred_at);
`

// Store is the SQLite-backed task and entity store.
// Uses database/sql so the driver can be swapped to postgres in production.
type Store struct {
	db *sql.DB
}

// Open opens (or creates) the SQLite database at path and runs schema migrations.
func Open(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("tasks: open %s: %w", path, err)
	}
	db.SetMaxOpenConns(1) // SQLite: single writer
	if _, err := db.Exec(schema); err != nil {
		return nil, fmt.Errorf("tasks: migrate: %w", err)
	}
	return &Store{db: db}, nil
}

func (s *Store) Close() error { return s.db.Close() }

// ─── Tasks ────────────────────────────────────────────────────────────────────

func (s *Store) CreateTask(ctx context.Context, t *Task) error {
	if t.ID == "" {
		t.ID = uuid.NewString()
	}
	now := time.Now().UTC()
	t.CreatedAt = now
	t.UpdatedAt = now
	if t.Status == "" {
		t.Status = TaskPending
	}
	meta, _ := json.Marshal(t.Metadata)
	_, err := s.db.ExecContext(ctx, `
		INSERT INTO tasks (id, tenant_id, session_id, surface, title, description, status, priority, metadata, created_at, updated_at)
		VALUES (?,?,?,?,?,?,?,?,?,?,?)`,
		t.ID, t.TenantID, t.SessionID, t.Surface, t.Title, t.Description,
		t.Status, t.Priority, string(meta), t.CreatedAt, t.UpdatedAt,
	)
	return err
}

func (s *Store) GetTask(ctx context.Context, id, tenantID string) (*Task, error) {
	row := s.db.QueryRowContext(ctx, `
		SELECT id, tenant_id, session_id, surface, title, description, status, priority, metadata, created_at, updated_at, resolved_at
		FROM tasks WHERE id=? AND tenant_id=?`, id, tenantID)
	t, err := scanTask(row)
	if err != nil {
		return nil, err
	}
	steps, err := s.ListSteps(ctx, id)
	if err != nil {
		return nil, err
	}
	t.Steps = steps
	return t, nil
}

func (s *Store) ListTasks(ctx context.Context, tenantID string, f TaskFilter) ([]Task, error) {
	q := `SELECT id, tenant_id, session_id, surface, title, description, status, priority, metadata, created_at, updated_at, resolved_at FROM tasks WHERE tenant_id=?`
	args := []interface{}{tenantID}
	if f.Status != "" {
		q += " AND status=?"
		args = append(args, f.Status)
	}
	if f.Surface != "" {
		q += " AND surface=?"
		args = append(args, f.Surface)
	}
	if f.SessionID != "" {
		q += " AND session_id=?"
		args = append(args, f.SessionID)
	}
	q += " ORDER BY priority DESC, created_at DESC"
	if f.Limit > 0 {
		q += fmt.Sprintf(" LIMIT %d", f.Limit)
	}
	if f.Offset > 0 {
		q += fmt.Sprintf(" OFFSET %d", f.Offset)
	}

	rows, err := s.db.QueryContext(ctx, q, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []Task
	for rows.Next() {
		t, err := scanTask(rows)
		if err != nil {
			continue
		}
		out = append(out, *t)
	}
	return out, rows.Err()
}

func (s *Store) UpdateTask(ctx context.Context, id, tenantID string, updates map[string]interface{}) error {
	updates["updated_at"] = time.Now().UTC()
	setClauses := make([]string, 0, len(updates))
	args := make([]interface{}, 0, len(updates)+2)
	for k, v := range updates {
		setClauses = append(setClauses, k+"=?")
		args = append(args, v)
	}
	args = append(args, id, tenantID)
	_, err := s.db.ExecContext(ctx,
		"UPDATE tasks SET "+strings.Join(setClauses, ",")+" WHERE id=? AND tenant_id=?",
		args...,
	)
	return err
}

func (s *Store) DeleteTask(ctx context.Context, id, tenantID string) error {
	_, err := s.db.ExecContext(ctx, "DELETE FROM tasks WHERE id=? AND tenant_id=?", id, tenantID)
	return err
}

// ─── Steps ────────────────────────────────────────────────────────────────────

func (s *Store) AddStep(ctx context.Context, step *Step) error {
	if step.ID == "" {
		step.ID = uuid.NewString()
	}
	step.CreatedAt = time.Now().UTC()
	if step.Status == "" {
		step.Status = TaskPending
	}
	args, _ := json.Marshal(step.Args)
	deps, _ := json.Marshal(step.DependsOn)
	_, err := s.db.ExecContext(ctx, `
		INSERT INTO task_steps (id, task_id, order_num, title, action, args, depends_on, status, result, created_at)
		VALUES (?,?,?,?,?,?,?,?,?,?)`,
		step.ID, step.TaskID, step.OrderNum, step.Title, step.Action,
		string(args), string(deps), step.Status, step.Result, step.CreatedAt,
	)
	return err
}

func (s *Store) ListSteps(ctx context.Context, taskID string) ([]Step, error) {
	rows, err := s.db.QueryContext(ctx, `
		SELECT id, task_id, order_num, title, action, args, depends_on, status, result, created_at, completed_at
		FROM task_steps WHERE task_id=? ORDER BY order_num ASC`, taskID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []Step
	for rows.Next() {
		st, err := scanStep(rows)
		if err != nil {
			continue
		}
		out = append(out, *st)
	}
	return out, rows.Err()
}

func (s *Store) UpdateStep(ctx context.Context, stepID string, status TaskStatus, result string) error {
	now := time.Now().UTC()
	_, err := s.db.ExecContext(ctx,
		"UPDATE task_steps SET status=?, result=?, completed_at=? WHERE id=?",
		status, result, now, stepID,
	)
	return err
}

func (s *Store) DeleteStep(ctx context.Context, stepID, taskID string) error {
	_, err := s.db.ExecContext(ctx, "DELETE FROM task_steps WHERE id=? AND task_id=?", stepID, taskID)
	return err
}

// ─── Entities ─────────────────────────────────────────────────────────────────

func (s *Store) UpsertEntity(ctx context.Context, e *Entity) error {
	if e.ID == "" {
		e.ID = uuid.NewString()
	}
	now := time.Now().UTC()
	e.CreatedAt = now
	e.UpdatedAt = now
	aliases, _ := json.Marshal(e.Aliases)
	_, err := s.db.ExecContext(ctx, `
		INSERT INTO entities (id, tenant_id, name, kind, aliases, created_at, updated_at)
		VALUES (?,?,?,?,?,?,?)
		ON CONFLICT(id) DO UPDATE SET name=excluded.name, kind=excluded.kind, aliases=excluded.aliases, updated_at=excluded.updated_at`,
		e.ID, e.TenantID, e.Name, e.Kind, string(aliases), e.CreatedAt, e.UpdatedAt,
	)
	return err
}

func (s *Store) GetEntity(ctx context.Context, id, tenantID string) (*Entity, error) {
	row := s.db.QueryRowContext(ctx, `
		SELECT id, tenant_id, name, kind, aliases, created_at, updated_at
		FROM entities WHERE id=? AND tenant_id=?`, id, tenantID)
	return scanEntity(row)
}

func (s *Store) ListEntities(ctx context.Context, tenantID string, f EntityFilter) ([]Entity, error) {
	q := `SELECT id, tenant_id, name, kind, aliases, created_at, updated_at FROM entities WHERE tenant_id=?`
	args := []interface{}{tenantID}
	if f.Kind != "" {
		q += " AND kind=?"
		args = append(args, f.Kind)
	}
	if f.Search != "" {
		q += " AND (name LIKE ? OR aliases LIKE ?)"
		pat := "%" + f.Search + "%"
		args = append(args, pat, pat)
	}
	q += " ORDER BY name ASC"
	if f.Limit > 0 {
		q += fmt.Sprintf(" LIMIT %d", f.Limit)
	}

	rows, err := s.db.QueryContext(ctx, q, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []Entity
	for rows.Next() {
		e, err := scanEntity(rows)
		if err != nil {
			continue
		}
		out = append(out, *e)
	}
	return out, rows.Err()
}

// ─── Entity Events ────────────────────────────────────────────────────────────

func (s *Store) AddEntityEvent(ctx context.Context, ev *EntityEvent) error {
	if ev.ID == "" {
		ev.ID = uuid.NewString()
	}
	ev.CreatedAt = time.Now().UTC()
	if ev.OccurredAt.IsZero() {
		ev.OccurredAt = ev.CreatedAt
	}
	meta, _ := json.Marshal(ev.Metadata)
	_, err := s.db.ExecContext(ctx, `
		INSERT INTO entity_events (id, entity_id, task_id, kind, content, metadata, occurred_at, created_at)
		VALUES (?,?,?,?,?,?,?,?)`,
		ev.ID, ev.EntityID, ev.TaskID, ev.Kind, ev.Content, string(meta), ev.OccurredAt, ev.CreatedAt,
	)
	return err
}

func (s *Store) ListEntityEvents(ctx context.Context, entityID string, limit int) ([]EntityEvent, error) {
	if limit <= 0 {
		limit = 50
	}
	rows, err := s.db.QueryContext(ctx, `
		SELECT id, entity_id, task_id, kind, content, metadata, occurred_at, created_at
		FROM entity_events WHERE entity_id=? ORDER BY occurred_at DESC LIMIT ?`, entityID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []EntityEvent
	for rows.Next() {
		ev, err := scanEntityEvent(rows)
		if err != nil {
			continue
		}
		out = append(out, *ev)
	}
	return out, rows.Err()
}

// ─── Scanners ─────────────────────────────────────────────────────────────────

type rowScanner interface {
	Scan(dest ...interface{}) error
}

func scanTask(r rowScanner) (*Task, error) {
	var t Task
	var meta string
	var resolvedAt sql.NullTime
	err := r.Scan(&t.ID, &t.TenantID, &t.SessionID, &t.Surface, &t.Title,
		&t.Description, &t.Status, &t.Priority, &meta, &t.CreatedAt, &t.UpdatedAt, &resolvedAt)
	if err != nil {
		return nil, err
	}
	_ = json.Unmarshal([]byte(meta), &t.Metadata)
	if resolvedAt.Valid {
		t.ResolvedAt = &resolvedAt.Time
	}
	return &t, nil
}

func scanStep(r rowScanner) (*Step, error) {
	var s Step
	var args, deps string
	var completedAt sql.NullTime
	err := r.Scan(&s.ID, &s.TaskID, &s.OrderNum, &s.Title, &s.Action,
		&args, &deps, &s.Status, &s.Result, &s.CreatedAt, &completedAt)
	if err != nil {
		return nil, err
	}
	_ = json.Unmarshal([]byte(args), &s.Args)
	_ = json.Unmarshal([]byte(deps), &s.DependsOn)
	if completedAt.Valid {
		s.CompletedAt = &completedAt.Time
	}
	return &s, nil
}

func scanEntity(r rowScanner) (*Entity, error) {
	var e Entity
	var aliases string
	err := r.Scan(&e.ID, &e.TenantID, &e.Name, &e.Kind, &aliases, &e.CreatedAt, &e.UpdatedAt)
	if err != nil {
		return nil, err
	}
	_ = json.Unmarshal([]byte(aliases), &e.Aliases)
	return &e, nil
}

func scanEntityEvent(r rowScanner) (*EntityEvent, error) {
	var ev EntityEvent
	var meta string
	err := r.Scan(&ev.ID, &ev.EntityID, &ev.TaskID, &ev.Kind, &ev.Content, &meta, &ev.OccurredAt, &ev.CreatedAt)
	if err != nil {
		return nil, err
	}
	_ = json.Unmarshal([]byte(meta), &ev.Metadata)
	return &ev, nil
}
