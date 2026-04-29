package api

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	tenantauth "github.com/thynaptic/oricli-go/pkg/auth"
	"github.com/thynaptic/oricli-go/pkg/searchintent"
	"github.com/thynaptic/oricli-go/pkg/tasks"
)

// ─── Task CRUD ────────────────────────────────────────────────────────────────

func (s *ServerV2) handleCreateTask(c *gin.Context) {
	tenantID := tenantauth.TenantID(c.Request.Context())
	var req struct {
		Title       string            `json:"title" binding:"required"`
		Description string            `json:"description"`
		Surface     string            `json:"surface"`
		SessionID   string            `json:"session_id"`
		Priority    int               `json:"priority"`
		Metadata    map[string]string `json:"metadata"`
		Steps       []struct {
			Title     string            `json:"title" binding:"required"`
			Action    tasks.StepAction  `json:"action" binding:"required"`
			Args      map[string]string `json:"args"`
			DependsOn []string          `json:"depends_on"`
			OrderNum  int               `json:"order_num"`
		} `json:"steps"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if req.Surface == "" {
		req.Surface = "api"
	}

	t := &tasks.Task{
		TenantID:    tenantID,
		SessionID:   req.SessionID,
		Surface:     req.Surface,
		Title:       req.Title,
		Description: req.Description,
		Priority:    req.Priority,
		Metadata:    req.Metadata,
	}
	if err := s.Tasks.CreateTask(c.Request.Context(), t); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	for i, rs := range req.Steps {
		step := &tasks.Step{
			TaskID:    t.ID,
			OrderNum:  rs.OrderNum,
			Title:     rs.Title,
			Action:    rs.Action,
			Args:      rs.Args,
			DependsOn: rs.DependsOn,
		}
		if step.OrderNum == 0 {
			step.OrderNum = i + 1
		}
		_ = s.Tasks.AddStep(c.Request.Context(), step)
	}

	created, _ := s.Tasks.GetTask(c.Request.Context(), t.ID, tenantID)
	c.JSON(http.StatusCreated, created)
}

func (s *ServerV2) handleListTasks(c *gin.Context) {
	tenantID := tenantauth.TenantID(c.Request.Context())
	f := tasks.TaskFilter{
		Status:    tasks.TaskStatus(c.Query("status")),
		Surface:   c.Query("surface"),
		SessionID: c.Query("session_id"),
	}
	if lim, err := strconv.Atoi(c.DefaultQuery("limit", "50")); err == nil {
		f.Limit = lim
	}
	if off, err := strconv.Atoi(c.DefaultQuery("offset", "0")); err == nil {
		f.Offset = off
	}

	list, err := s.Tasks.ListTasks(c.Request.Context(), tenantID, f)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if list == nil {
		list = []tasks.Task{}
	}
	c.JSON(http.StatusOK, gin.H{"tasks": list, "count": len(list)})
}

func (s *ServerV2) handleGetTask(c *gin.Context) {
	tenantID := tenantauth.TenantID(c.Request.Context())
	t, err := s.Tasks.GetTask(c.Request.Context(), c.Param("id"), tenantID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "task not found"})
		return
	}
	c.JSON(http.StatusOK, t)
}

func (s *ServerV2) handleUpdateTask(c *gin.Context) {
	tenantID := tenantauth.TenantID(c.Request.Context())
	var req map[string]interface{}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	// Only allow safe fields to be patched.
	allowed := map[string]bool{"title": true, "description": true, "status": true, "priority": true, "surface": true}
	patch := make(map[string]interface{}, len(req))
	for k, v := range req {
		if allowed[k] {
			patch[k] = v
		}
	}
	if len(patch) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "no patchable fields provided"})
		return
	}
	if err := s.Tasks.UpdateTask(c.Request.Context(), c.Param("id"), tenantID, patch); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	t, _ := s.Tasks.GetTask(c.Request.Context(), c.Param("id"), tenantID)
	c.JSON(http.StatusOK, t)
}

func (s *ServerV2) handleDeleteTask(c *gin.Context) {
	tenantID := tenantauth.TenantID(c.Request.Context())
	if err := s.Tasks.DeleteTask(c.Request.Context(), c.Param("id"), tenantID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"deleted": c.Param("id")})
}

// ─── Steps ────────────────────────────────────────────────────────────────────

func (s *ServerV2) handleAddStep(c *gin.Context) {
	var req struct {
		Title     string            `json:"title" binding:"required"`
		Action    tasks.StepAction  `json:"action" binding:"required"`
		Args      map[string]string `json:"args"`
		DependsOn []string          `json:"depends_on"`
		OrderNum  int               `json:"order_num"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	step := &tasks.Step{
		TaskID:    c.Param("id"),
		OrderNum:  req.OrderNum,
		Title:     req.Title,
		Action:    req.Action,
		Args:      req.Args,
		DependsOn: req.DependsOn,
	}
	if err := s.Tasks.AddStep(c.Request.Context(), step); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusCreated, step)
}

func (s *ServerV2) handleUpdateStep(c *gin.Context) {
	var req struct {
		Status tasks.TaskStatus `json:"status"`
		Result string           `json:"result"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err := s.Tasks.UpdateStep(c.Request.Context(), c.Param("step_id"), req.Status, req.Result); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"updated": c.Param("step_id")})
}

func (s *ServerV2) handleDeleteStep(c *gin.Context) {
	if err := s.Tasks.DeleteStep(c.Request.Context(), c.Param("step_id"), c.Param("id")); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"deleted": c.Param("step_id")})
}

// ─── Execute ──────────────────────────────────────────────────────────────────

// handleExecuteTask runs a task's step DAG and streams step updates via SSE.
// GET /v1/tasks/execute/:id returns current execution status.
// POST /v1/tasks/execute/:id starts execution.
func (s *ServerV2) handleExecuteTask(c *gin.Context) {
	tenantID := tenantauth.TenantID(c.Request.Context())
	taskID := c.Param("id")

	// GET — return current task state (status check without running)
	if c.Request.Method == http.MethodGet {
		t, err := s.Tasks.GetTask(c.Request.Context(), taskID, tenantID)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "task not found"})
			return
		}
		c.JSON(http.StatusOK, t)
		return
	}

	// POST — execute with SSE stream
	useSSE := c.GetHeader("Accept") == "text/event-stream"
	if useSSE {
		c.Header("Content-Type", "text/event-stream")
		c.Header("Cache-Control", "no-cache")
		c.Header("Connection", "keep-alive")
		c.Header("X-Accel-Buffering", "no")
	}

	emit := func(update tasks.StepUpdate) {
		if !useSSE {
			return
		}
		data, _ := json.Marshal(update)
		c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
		c.Writer.Flush()
	}

	exec := tasks.NewExecutor(s.Tasks, s.taskDispatch(), emit)

	// Run synchronously — caller can move to background with their own goroutine.
	if err := exec.Run(c.Request.Context(), taskID, tenantID); err != nil {
		if useSSE {
			errData, _ := json.Marshal(map[string]string{"error": err.Error()})
			c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(errData)))
			c.Writer.Flush()
		} else {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		}
		return
	}

	t, _ := s.Tasks.GetTask(c.Request.Context(), taskID, tenantID)
	if useSSE {
		finalData, _ := json.Marshal(map[string]interface{}{"done": true, "task": t})
		c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(finalData)))
		c.Writer.Flush()
	} else {
		c.JSON(http.StatusOK, t)
	}
}

// taskDispatch returns the ExecuteFunc wired to ORI's service backends.
func (s *ServerV2) taskDispatch() tasks.ExecuteFunc {
	return func(ctx context.Context, step tasks.Step) (string, error) {
		topic := step.Args["topic"]
		if topic == "" {
			topic = step.Args["query"]
		}

		switch step.Action {
		case tasks.ActionResearch, tasks.ActionFetch:
			if s.Agent != nil && s.Agent.SovEngine != nil && s.Agent.SovEngine.SearXNG != nil {
				intent := searchintent.ClassifySearchIntent(topic)
				sq := searchintent.BuildSearchQuery(topic, intent)
				result, err := s.Agent.SovEngine.SearXNG.SearchWithIntent(sq)
				if err == nil {
					return result, nil
				}
			}
			return fmt.Sprintf("research: %s (no search backend available)", topic), nil

		case tasks.ActionDraft, tasks.ActionGenerate, tasks.ActionSummarize:
			if s.Agent != nil && s.Agent.GenService != nil {
				prompt := step.Args["prompt"]
				if prompt == "" {
					prompt = "Generate a response for: " + topic
				}
				res, err := s.Agent.GenService.Generate(prompt, nil)
				if err != nil {
					return "", err
				}
				text, _ := res["text"].(string)
				return text, nil
			}
			return fmt.Sprintf("draft stub: %s", topic), nil

		case tasks.ActionWebhook:
			url := step.Args["url"]
			if url == "" {
				return "", fmt.Errorf("webhook: missing url arg")
			}
			body := step.Args["body"]
			req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, strings.NewReader(body))
			if err != nil {
				return "", err
			}
			req.Header.Set("Content-Type", "application/json")
			resp, err := http.DefaultClient.Do(req)
			if err != nil {
				return "", err
			}
			defer resp.Body.Close()
			return fmt.Sprintf("webhook: %s → %d", url, resp.StatusCode), nil

		case tasks.ActionSave:
			content := step.Args["content"]
			if s.MemoryBank != nil && content != "" {
				s.MemoryBank.WriteKnowledgeFragment(topic, "task", content, 0.7)
			}
			return "saved", nil

		default:
			return "", fmt.Errorf("unknown action: %s", step.Action)
		}
	}
}

// ─── Entities ─────────────────────────────────────────────────────────────────

func (s *ServerV2) handleListEntities(c *gin.Context) {
	tenantID := tenantauth.TenantID(c.Request.Context())
	f := tasks.EntityFilter{
		Kind:   tasks.EntityKind(c.Query("kind")),
		Search: c.Query("search"),
	}
	if lim, err := strconv.Atoi(c.DefaultQuery("limit", "50")); err == nil {
		f.Limit = lim
	}
	list, err := s.Tasks.ListEntities(c.Request.Context(), tenantID, f)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if list == nil {
		list = []tasks.Entity{}
	}
	c.JSON(http.StatusOK, gin.H{"entities": list, "count": len(list)})
}

func (s *ServerV2) handleGetEntity(c *gin.Context) {
	tenantID := tenantauth.TenantID(c.Request.Context())
	e, err := s.Tasks.GetEntity(c.Request.Context(), c.Param("id"), tenantID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "entity not found"})
		return
	}
	limit := 50
	if lim, err := strconv.Atoi(c.DefaultQuery("event_limit", "50")); err == nil {
		limit = lim
	}
	events, _ := s.Tasks.ListEntityEvents(c.Request.Context(), e.ID, limit)
	if events == nil {
		events = []tasks.EntityEvent{}
	}
	c.JSON(http.StatusOK, gin.H{"entity": e, "events": events})
}

func (s *ServerV2) handleCreateEntityEvent(c *gin.Context) {
	tenantID := tenantauth.TenantID(c.Request.Context())
	entityID := c.Param("id")

	// Verify entity belongs to this tenant.
	if _, err := s.Tasks.GetEntity(c.Request.Context(), entityID, tenantID); err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "entity not found"})
		return
	}

	var req struct {
		Kind       tasks.EventKind   `json:"kind" binding:"required"`
		Content    string            `json:"content"`
		TaskID     string            `json:"task_id"`
		Metadata   map[string]string `json:"metadata"`
		OccurredAt *time.Time        `json:"occurred_at"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ev := &tasks.EntityEvent{
		EntityID: entityID,
		TaskID:   req.TaskID,
		Kind:     req.Kind,
		Content:  req.Content,
		Metadata: req.Metadata,
	}
	if req.OccurredAt != nil {
		ev.OccurredAt = *req.OccurredAt
	}
	if err := s.Tasks.AddEntityEvent(c.Request.Context(), ev); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusCreated, ev)
}

func (s *ServerV2) handleUpsertEntity(c *gin.Context) {
	tenantID := tenantauth.TenantID(c.Request.Context())
	var req struct {
		ID      string           `json:"id"`
		Name    string           `json:"name" binding:"required"`
		Kind    tasks.EntityKind `json:"kind"`
		Aliases []string         `json:"aliases"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	e := &tasks.Entity{
		ID:       req.ID,
		TenantID: tenantID,
		Name:     req.Name,
		Kind:     req.Kind,
		Aliases:  req.Aliases,
	}
	if e.Kind == "" {
		e.Kind = tasks.EntityUnknown
	}
	if err := s.Tasks.UpsertEntity(c.Request.Context(), e); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, e)
}
