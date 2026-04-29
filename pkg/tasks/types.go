package tasks

import "time"

// ─── Status enums ─────────────────────────────────────────────────────────────

type TaskStatus string

const (
	TaskPending    TaskStatus = "pending"
	TaskRunning    TaskStatus = "running"
	TaskDone       TaskStatus = "done"
	TaskFailed     TaskStatus = "failed"
	TaskCancelled  TaskStatus = "cancelled"
)

type StepAction string

const (
	ActionResearch  StepAction = "research"
	ActionFetch     StepAction = "fetch"
	ActionSummarize StepAction = "summarize"
	ActionCompare   StepAction = "compare"
	ActionDraft     StepAction = "draft"
	ActionGenerate  StepAction = "generate"
	ActionSave      StepAction = "save"
	ActionWebhook   StepAction = "webhook"
)

type EntityKind string

const (
	EntityPerson   EntityKind = "person"
	EntityBusiness EntityKind = "business"
	EntityVendor   EntityKind = "vendor"
	EntityAccount  EntityKind = "account"
	EntityUnknown  EntityKind = "unknown"
)

type EventKind string

const (
	EventMessage EventKind = "message"
	EventInvoice EventKind = "invoice"
	EventBooking EventKind = "booking"
	EventCall    EventKind = "call"
	EventNote    EventKind = "note"
	EventGeneric EventKind = "event"
)

// ─── Core types ───────────────────────────────────────────────────────────────

// Task is the top-level unit of work — persisted across sessions.
type Task struct {
	ID          string            `json:"id"`
	TenantID    string            `json:"tenant_id"`
	SessionID   string            `json:"session_id,omitempty"`
	Surface     string            `json:"surface,omitempty"` // "home", "studio", "api", etc.
	Title       string            `json:"title"`
	Description string            `json:"description,omitempty"`
	Status      TaskStatus        `json:"status"`
	Priority    int               `json:"priority"`
	Metadata    map[string]string `json:"metadata,omitempty"`
	Steps       []Step            `json:"steps,omitempty"`
	CreatedAt   time.Time         `json:"created_at"`
	UpdatedAt   time.Time         `json:"updated_at"`
	ResolvedAt  *time.Time        `json:"resolved_at,omitempty"`
}

// Step is one unit within a Task — forms a DAG via DependsOn.
type Step struct {
	ID          string            `json:"id"`
	TaskID      string            `json:"task_id"`
	OrderNum    int               `json:"order_num"`
	Title       string            `json:"title"`
	Action      StepAction        `json:"action"`
	Args        map[string]string `json:"args,omitempty"`
	DependsOn   []string          `json:"depends_on,omitempty"`
	Status      TaskStatus        `json:"status"`
	Result      string            `json:"result,omitempty"`
	CreatedAt   time.Time         `json:"created_at"`
	CompletedAt *time.Time        `json:"completed_at,omitempty"`
}

// Entity is a named real-world thing that recurs across tasks.
// The backbone of relational retrieval ("the contractor", "the plumber").
type Entity struct {
	ID        string     `json:"id"`
	TenantID  string     `json:"tenant_id"`
	Name      string     `json:"name"`
	Kind      EntityKind `json:"kind"`
	Aliases   []string   `json:"aliases,omitempty"`
	CreatedAt time.Time  `json:"created_at"`
	UpdatedAt time.Time  `json:"updated_at"`
}

// EntityEvent is a timestamped occurrence associated with an Entity.
// Building these up over time is what makes Ghost-Logistics work.
type EntityEvent struct {
	ID         string            `json:"id"`
	EntityID   string            `json:"entity_id"`
	TaskID     string            `json:"task_id,omitempty"`
	Kind       EventKind         `json:"kind"`
	Content    string            `json:"content,omitempty"`
	Metadata   map[string]string `json:"metadata,omitempty"`
	OccurredAt time.Time         `json:"occurred_at"`
	CreatedAt  time.Time         `json:"created_at"`
}

// ─── List filters ─────────────────────────────────────────────────────────────

type TaskFilter struct {
	Status    TaskStatus
	Surface   string
	SessionID string
	Limit     int
	Offset    int
}

type EntityFilter struct {
	Kind   EntityKind
	Search string
	Limit  int
	Offset int
}
