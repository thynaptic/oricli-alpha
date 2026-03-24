package service

import (
	"context"
	"log"
	"regexp"
	"strings"
	"sync"
)

// ActionType identifies what kind of agent task was detected.
type ActionType string

const (
	ActionResearch  ActionType = "research"
	ActionSearch    ActionType = "search"
	ActionTask      ActionType = "task"
	ActionCreate    ActionType = "create"
	ActionWorkflow  ActionType = "workflow"
	ActionSummarize ActionType = "summarize"
	ActionAnalyze   ActionType = "analyze"
)

// DetectedAction holds the parsed intent from a user message.
type DetectedAction struct {
	Type       ActionType `json:"action"`
	Subject    string     `json:"subject"`
	Confidence float64    `json:"confidence"`
}

// ActionResult is the completed output broadcast back via WS.
type ActionResult struct {
	JobID   string     `json:"job_id"`
	Action  ActionType `json:"action"`
	Subject string     `json:"subject"`
	Status  string     `json:"status"` // "running" | "done" | "error"
	Summary string     `json:"summary,omitempty"`
	Error   string     `json:"error,omitempty"`
}

// pattern wires a regex to an ActionType.
type actionPattern struct {
	re         *regexp.Regexp
	actionType ActionType
}

var patterns = []actionPattern{
	// Research — explicit research-intent verbs only.
	// "tell me about" and "what is/are" are omitted: they're conversational and fire
	// on self-referential questions like "tell me about yourself".
	{regexp.MustCompile(`(?i)\b(?:research|investigate|look\s+into|deep\s+dive(?:\s+into|\s+on)?|find\s+out\s+(?:about|more\s+about)|study\s+(?:up\s+on|about)|do\s+(?:a\s+)?research\s+on)\s+(.+)`), ActionResearch},
	// Search
	{regexp.MustCompile(`(?i)\b(?:search(?:\s+for)?|google|look\s+up|find)\s+(.+)`), ActionSearch},
	// Task / Reminder — must come before Create to capture "create a task/todo/reminder"
	{regexp.MustCompile(`(?i)\b(?:remind\s+me\s+to|add\s+(?:a\s+)?(?:task|todo|reminder)(?:\s+to)?|create\s+(?:a\s+)?(?:task|todo|reminder)(?:\s+to)?|note\s+(?:that|to))\s+(.+)`), ActionTask},
	// Create — generate a document/code artifact on the Canvas.
	// Anchored to start of message (with optional polite preamble) to avoid firing
	// on conversational uses of "make/write/build" mid-sentence.
	{regexp.MustCompile(`(?i)^\s*(?:(?:hey|hi|ok|okay|so|alright|please|can\s+you|could\s+you|i\s+(?:want|need)\s+(?:you\s+to|to)?|let(?:'s|\s+us?))\s+)?(?:create|write|build|generate|make|draft|implement|code|develop)\s+(?:(?:a|an|the|me\s+a?n?\s+)?(.{10,}))`), ActionCreate},
	// Workflow
	{regexp.MustCompile(`(?i)\b(?:run\s+(?:the\s+)?workflow|execute\s+(?:the\s+)?workflow|start\s+(?:the\s+)?workflow|trigger\s+workflow)\s+(.+)`), ActionWorkflow},
	// Summarize
	{regexp.MustCompile(`(?i)\b(?:summarize|recap|give\s+me\s+a\s+(?:summary|tldr|recap)\s+of|tl;?dr)\s+(.+)`), ActionSummarize},
	// Analyze
	{regexp.MustCompile(`(?i)\b(?:analyze|analyse|do\s+an?\s+analysis\s+of|break\s+down)\s+(.+)`), ActionAnalyze},
}

// DetectAction inspects a message and returns the first matched action, or nil.
func DetectAction(message string) *DetectedAction {
	msg := strings.TrimSpace(message)
	for _, p := range patterns {
		m := p.re.FindStringSubmatch(msg)
		if len(m) >= 2 {
			subject := strings.TrimRight(strings.TrimSpace(m[1]), ".!?")
			if subject == "" {
				continue
			}
			return &DetectedAction{
				Type:       p.actionType,
				Subject:    subject,
				Confidence: 0.9,
			}
		}
	}
	return nil
}

// JobStatus tracks the completion state of a dispatched job.
type JobStatus string

const (
	JobStatusPending   JobStatus = "pending"
	JobStatusRunning   JobStatus = "running"
	JobStatusCompleted JobStatus = "completed"
	JobStatusFailed    JobStatus = "failed"
)

// ActionRouter dispatches detected actions to the appropriate backend services.
type ActionRouter struct {
	ResearchOrchestrator *ResearchOrchestrator
	CuriosityDaemon      *CuriosityDaemon
	WSHub                interface {
		BroadcastEvent(eventType string, payload interface{})
	}

	jobMu  sync.Mutex
	jobs   map[string]JobStatus // jobID → status
}

func NewActionRouter(
	research *ResearchOrchestrator,
	curiosity *CuriosityDaemon,
	hub interface{ BroadcastEvent(string, interface{}) },
) *ActionRouter {
	return &ActionRouter{
		ResearchOrchestrator: research,
		CuriosityDaemon:      curiosity,
		WSHub:                hub,
		jobs:                 make(map[string]JobStatus),
	}
}

// JobStatus returns the current status of a dispatched job.
// Returns JobStatusPending if the jobID is unknown.
func (r *ActionRouter) JobStatus(jobID string) JobStatus {
	r.jobMu.Lock()
	defer r.jobMu.Unlock()
	if s, ok := r.jobs[jobID]; ok {
		return s
	}
	return JobStatusPending
}

// Dispatch runs the action in a goroutine and broadcasts progress/results via WS.
func (r *ActionRouter) Dispatch(ctx context.Context, jobID string, action *DetectedAction) {
	log.Printf("[ActionRouter] Dispatching %s job %s for: %s", action.Type, jobID, action.Subject)

	r.broadcast(jobID, action, "running", "", "")

	go func() {
		switch action.Type {
		case ActionResearch, ActionSearch, ActionSummarize, ActionAnalyze:
			r.runResearch(ctx, jobID, action)
		case ActionTask:
			r.runTask(ctx, jobID, action)
		case ActionCreate:
			r.runCreate(ctx, jobID, action)
		case ActionWorkflow:
			r.runWorkflow(ctx, jobID, action)
		default:
			r.runResearch(ctx, jobID, action)
		}
	}()
}

func (r *ActionRouter) runResearch(ctx context.Context, jobID string, action *DetectedAction) {
	if r.ResearchOrchestrator == nil {
		r.broadcast(jobID, action, "error", "", "Research orchestrator unavailable")
		return
	}
	result, err := r.ResearchOrchestrator.ConductResearch(ctx, action.Subject)
	if err != nil {
		r.broadcast(jobID, action, "error", "", err.Error())
		return
	}
	summary := result.FinalText
	if len(summary) > 500 {
		summary = summary[:500] + "…"
	}
	r.broadcast(jobID, action, "done", summary, "")
}

func (r *ActionRouter) runTask(ctx context.Context, jobID string, action *DetectedAction) {
	// Tasks are recorded via the backbone's task system; here we just acknowledge.
	log.Printf("[ActionRouter] Task created: %s", action.Subject)
	r.broadcast(jobID, action, "done", "Task added: "+action.Subject, "")
}

func (r *ActionRouter) runCreate(ctx context.Context, jobID string, action *DetectedAction) {
	// Create actions are handled entirely on the frontend (Canvas page).
	// We just confirm the dispatch so the UI knows to open the Canvas.
	log.Printf("[ActionRouter] Canvas create: %s", action.Subject)
	r.broadcast(jobID, action, "done", "Opening Canvas for: "+action.Subject, "")
}

func (r *ActionRouter) runWorkflow(ctx context.Context, jobID string, action *DetectedAction) {
	log.Printf("[ActionRouter] Workflow dispatch: %s", action.Subject)
	r.broadcast(jobID, action, "done", "Workflow '"+action.Subject+"' queued — check the Workflows page.", "")
}

func (r *ActionRouter) broadcast(jobID string, action *DetectedAction, status, summary, errMsg string) {
	// Update internal job status map
	r.jobMu.Lock()
	switch status {
	case "done":
		r.jobs[jobID] = JobStatusCompleted
	case "error":
		r.jobs[jobID] = JobStatusFailed
	case "running":
		r.jobs[jobID] = JobStatusRunning
	}
	r.jobMu.Unlock()

	if r.WSHub == nil {
		return
	}
	r.WSHub.BroadcastEvent("agent_action", ActionResult{
		JobID:   jobID,
		Action:  action.Type,
		Subject: action.Subject,
		Status:  status,
		Summary: summary,
		Error:   errMsg,
	})
}
