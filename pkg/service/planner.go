package service

import (
	"context"
	"encoding/json"
	"fmt"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
)

type PlanStep struct {
	ID               string                 `json:"id"`
	Order            int                    `json:"order"`
	ToolName         string                 `json:"tool_name"`
	Arguments        map[string]interface{} `json:"arguments"`
	Description      string                 `json:"description"`
	DependsOn        []string               `json:"depends_on"`
	IsOptional       bool                   `json:"is_optional"`
	FallbackStrategy string                 `json:"fallback_strategy,omitempty"`
}

type ToolCallingPlan struct {
	ID                   string     `json:"id"`
	Query                string     `json:"query"`
	Steps                []PlanStep `json:"steps"`
	EstimatedTotalTime   float64    `json:"estimated_total_time"`
	CanExecuteInParallel bool       `json:"can_execute_in_parallel"`
	CreatedAt            int64      `json:"created_at"`
}

type PlanExecutionResult struct {
	PlanID              string                 `json:"plan_id"`
	CompletedSteps      []string               `json:"completed_steps"`
	FailedSteps         []string               `json:"failed_steps"`
	SkippedSteps        []string               `json:"skipped_steps"`
	Bindings            map[string]interface{} `json:"bindings,omitempty"`
	SavedStateName      string                 `json:"saved_state_name,omitempty"`
	ActiveSessionID     string                 `json:"active_session_id,omitempty"`
	AutoClosedSessionID string                 `json:"auto_closed_session_id,omitempty"`
	CleanupActions      []string               `json:"cleanup_actions,omitempty"`
	CleanupErrors       []string               `json:"cleanup_errors,omitempty"`
	FinalResponse       string                 `json:"final_response"`
	TotalTime           float64                `json:"total_time"`
	StepResults         map[string]interface{} `json:"step_results"`
}

type PlannerService struct {
	Orchestrator *GoOrchestrator
	ToolService  *ToolService
	GenService   *GenerationService
}

func NewPlannerService(orch *GoOrchestrator, toolSvc *ToolService, gen *GenerationService) *PlannerService {
	return &PlannerService{
		Orchestrator: orch,
		ToolService:  toolSvc,
		GenService:   gen,
	}
}

// --- ADVANCED PLANNING ---

func (s *PlannerService) CreateStrategicPlan(ctx context.Context, query string) (*ToolCallingPlan, error) {
	prompt := fmt.Sprintf("Create a strategic execution plan for: %s\nOutput JSON with steps, dependencies, and tools.", query)
	_, err := s.GenService.Generate(prompt, map[string]interface{}{"system": "Strategic Planner"})
	if err != nil {
		return nil, err
	}

	plan := &ToolCallingPlan{
		ID:        uuid.New().String()[:8],
		Query:     query,
		CreatedAt: time.Now().Unix(),
	}
	// (JSON parsing omitted, would populate plan.Steps here)
	return plan, nil
}

func (s *PlannerService) ChainPrompts(ctx context.Context, prompts []string) (string, error) {
	currentContext := ""
	for _, p := range prompts {
		res, err := s.GenService.Generate(p+"\nContext: "+currentContext, nil)
		if err != nil {
			return "", err
		}
		currentContext = res["text"].(string)
	}
	return currentContext, nil
}

// --- EXISTING METHODS (RESTORED) ---

func (s *PlannerService) CreatePlan(query string) (*ToolCallingPlan, error) {
	plan := &ToolCallingPlan{
		ID:        uuid.New().String()[:8],
		Query:     query,
		CreatedAt: time.Now().Unix(),
	}
	if s.ToolService == nil {
		return plan, nil
	}

	tools := s.ToolService.ListTools()
	if len(tools) == 0 {
		return plan, nil
	}

	if browserPlan := buildBrowserPlan(query, tools); browserPlan != nil {
		plan.Steps = browserPlan
		plan.EstimatedTotalTime = float64(len(browserPlan)) * 4.0
		plan.CanExecuteInParallel = false
		return plan, nil
	}

	order := 1
	lowerQuery := strings.ToLower(query)
	for _, t := range tools {
		if strings.Contains(lowerQuery, strings.ToLower(t.Name)) {
			plan.Steps = append(plan.Steps, PlanStep{
				ID:        fmt.Sprintf("step_%d", order),
				Order:     order,
				ToolName:  t.Name,
				Arguments: map[string]interface{}{"query": query},
			})
			order++
		}
	}

	plan.EstimatedTotalTime = float64(len(plan.Steps)) * 2.0
	return plan, nil
}

func (s *PlannerService) ExecutePlan(plan *ToolCallingPlan) (PlanExecutionResult, error) {
	startTime := time.Now()
	res := PlanExecutionResult{PlanID: plan.ID, StepResults: make(map[string]interface{})}
	completed := make(map[string]bool)
	bindings := make(map[string]interface{})
	var mu sync.Mutex
	for len(completed) < len(plan.Steps) {
		var readySteps []PlanStep
		for _, step := range plan.Steps {
			if completed[step.ID] {
				continue
			}
			allDepsMet := true
			for _, dep := range step.DependsOn {
				if !completed[dep] {
					allDepsMet = false
					break
				}
			}
			if allDepsMet {
				readySteps = append(readySteps, step)
			}
		}
		if len(readySteps) == 0 {
			break
		}
		var wg sync.WaitGroup
		for _, step := range readySteps {
			wg.Add(1)
			go func(st PlanStep) {
				defer wg.Done()
				mu.Lock()
				resolvedArgs := resolvePlanArguments(st.Arguments, bindings)
				mu.Unlock()

				result, err := s.ToolService.ExecuteTool(context.Background(), st.ToolName, resolvedArgs)
				mu.Lock()
				defer mu.Unlock()
				if err == nil && result.Success {
					res.CompletedSteps = append(res.CompletedSteps, st.ID)
					res.StepResults[st.ID] = result.Content
					extractPlanBindings(bindings, result)
					completed[st.ID] = true
				} else {
					res.FailedSteps = append(res.FailedSteps, st.ID)
					if st.IsOptional {
						res.SkippedSteps = append(res.SkippedSteps, st.ID)
						completed[st.ID] = true
					}
				}
			}(step)
		}
		wg.Wait()
	}
	s.autoCleanupPlanResources(plan, bindings, &res)
	if len(bindings) > 0 {
		res.Bindings = cloneBindings(bindings)
	}
	enrichBrowserExecutionResult(plan, &res)
	res.TotalTime = time.Since(startTime).Seconds()
	res.FinalResponse = summarizePlanExecution(plan, res)
	return res, nil
}

func (s *PlannerService) autoCleanupPlanResources(plan *ToolCallingPlan, bindings map[string]interface{}, res *PlanExecutionResult) {
	if !shouldAutoCloseBrowserSession(plan, bindings) || s == nil || s.ToolService == nil {
		return
	}

	sessionID, _ := bindings["session_id"].(string)
	result, err := s.ToolService.ExecuteTool(context.Background(), "browser_close", map[string]interface{}{
		"session_id": sessionID,
	})
	if err != nil || !result.Success {
		cleanupErr := "failed to close browser session"
		if err != nil {
			cleanupErr = fmt.Sprintf("failed to close browser session %s: %v", sessionID, err)
		} else if result.Error != "" {
			cleanupErr = fmt.Sprintf("failed to close browser session %s: %s", sessionID, result.Error)
		}
		res.CleanupErrors = append(res.CleanupErrors, cleanupErr)
		return
	}

	res.CleanupActions = append(res.CleanupActions, fmt.Sprintf("Closed browser session %s automatically.", sessionID))
	res.AutoClosedSessionID = sessionID
	res.StepResults["cleanup_browser_close"] = result.Content
}

func resolvePlanArguments(arguments map[string]interface{}, bindings map[string]interface{}) map[string]interface{} {
	if len(arguments) == 0 {
		return map[string]interface{}{}
	}

	resolved := make(map[string]interface{}, len(arguments))
	for key, value := range arguments {
		resolved[key] = resolvePlanValue(value, bindings)
	}
	return resolved
}

func cloneBindings(bindings map[string]interface{}) map[string]interface{} {
	if len(bindings) == 0 {
		return nil
	}
	cloned := make(map[string]interface{}, len(bindings))
	for key, value := range bindings {
		cloned[key] = value
	}
	return cloned
}

func resolvePlanValue(value interface{}, bindings map[string]interface{}) interface{} {
	switch v := value.(type) {
	case string:
		if strings.HasPrefix(v, "$") {
			if bound, ok := bindings[strings.TrimPrefix(v, "$")]; ok {
				return bound
			}
		}
		return v
	case map[string]interface{}:
		return resolvePlanArguments(v, bindings)
	case []interface{}:
		out := make([]interface{}, 0, len(v))
		for _, item := range v {
			out = append(out, resolvePlanValue(item, bindings))
		}
		return out
	default:
		return value
	}
}

func extractPlanBindings(bindings map[string]interface{}, result ToolResult) {
	if bindings == nil || result.Content == "" {
		return
	}

	var payload map[string]interface{}
	if err := json.Unmarshal([]byte(result.Content), &payload); err != nil {
		return
	}

	for key, value := range payload {
		bindings[key] = value
	}
}

func summarizePlanExecution(plan *ToolCallingPlan, res PlanExecutionResult) string {
	parts := []string{fmt.Sprintf("Executed in %.2fs", res.TotalTime)}
	if len(res.CompletedSteps) > 0 {
		parts = append(parts, fmt.Sprintf("%d steps completed", len(res.CompletedSteps)))
	}
	if len(res.FailedSteps) > 0 {
		parts = append(parts, fmt.Sprintf("%d failed", len(res.FailedSteps)))
	}
	if strings.TrimSpace(res.SavedStateName) != "" {
		parts = append(parts, fmt.Sprintf("saved state %q", res.SavedStateName))
	}
	if strings.TrimSpace(res.ActiveSessionID) != "" {
		parts = append(parts, fmt.Sprintf("active session %s", res.ActiveSessionID))
	}
	if len(res.CleanupActions) > 0 {
		parts = append(parts, strings.ToLower(res.CleanupActions[0]))
	}
	if len(res.CleanupErrors) > 0 {
		parts = append(parts, res.CleanupErrors[0])
	}
	return strings.Join(parts, "; ")
}

func enrichBrowserExecutionResult(plan *ToolCallingPlan, res *PlanExecutionResult) {
	if res == nil {
		return
	}
	if res.Bindings != nil {
		if stateName, ok := res.Bindings["state_name"].(string); ok {
			res.SavedStateName = strings.TrimSpace(stateName)
		}
		if sessionID, ok := res.Bindings["session_id"].(string); ok && queryRequestsPersistentBrowserSession(plan.Query) {
			res.ActiveSessionID = strings.TrimSpace(sessionID)
		}
	}
	if strings.TrimSpace(res.AutoClosedSessionID) != "" {
		res.ActiveSessionID = ""
	}
}

func shouldAutoCloseBrowserSession(plan *ToolCallingPlan, bindings map[string]interface{}) bool {
	if plan == nil {
		return false
	}

	sessionID, _ := bindings["session_id"].(string)
	if strings.TrimSpace(sessionID) == "" {
		return false
	}

	if !planUsesTool(plan, "browser_create_session") && !planUsesTool(plan, "browser_load_state") {
		return false
	}

	if planUsesTool(plan, "browser_close") || queryRequestsPersistentBrowserSession(plan.Query) {
		return false
	}

	return true
}

func planUsesTool(plan *ToolCallingPlan, toolName string) bool {
	if plan == nil {
		return false
	}
	for _, step := range plan.Steps {
		if step.ToolName == toolName {
			return true
		}
	}
	return false
}

func queryRequestsPersistentBrowserSession(query string) bool {
	lower := strings.ToLower(query)
	persistentPhrases := []string{
		"keep session",
		"keep the session",
		"leave session open",
		"leave the session open",
		"keep browser open",
		"leave browser open",
		"reuse session",
		"resume session",
		"keep alive",
	}
	for _, phrase := range persistentPhrases {
		if strings.Contains(lower, phrase) {
			return true
		}
	}
	return false
}

var urlPattern = regexp.MustCompile(`https?://[^\s]+`)
var stateNamePattern = regexp.MustCompile(`(?:state|session)\s+(?:named|called|as)?\s*["']?([a-zA-Z0-9_-]+)["']?`)
var fillLabelWithQuotedPattern = regexp.MustCompile(`(?i)(?:fill|enter|type)\s+(?:the\s+)?(?:field\s+)?(?:labeled\s+)?["']([^"']+)["']\s+(?:with|as)\s+["']([^"']+)["']`)
var fillQuotedIntoLabelPattern = regexp.MustCompile(`(?i)(?:fill|enter|type)\s+["']([^"']+)["']\s+(?:into|in)\s+(?:the\s+)?(?:field\s+)?(?:labeled\s+)?["']([^"']+)["']`)
var clickTargetPattern = regexp.MustCompile(`(?i)(?:click|press|tap)\s+(?:the\s+)?["']([^"']+)["'](?:\s+(button|link))?`)
var waitForPattern = regexp.MustCompile(`(?i)wait\s+(?:for|until)(?:\s+the\s+url\s+matches)?\s+["']([^"']+)["']`)
var emailValuePattern = regexp.MustCompile(`(?i)(?:fill|enter|type)(?:\s+(?:the\s+)?)?(?:email|email address)(?:\s+(?:field\s+)?)?(?:with|as)?\s+([^\s,;]+@[^\s,;]+)`)
var passwordValuePattern = regexp.MustCompile(`(?i)(?:fill|enter|type)(?:\s+(?:the\s+)?)?password(?:\s+(?:field\s+)?)?(?:with|as)?\s+([^\s,;]+)`)
var bareEmailValuePattern = regexp.MustCompile(`(?i)(?:^|[\s,;])(?:email|email address)(?:\s+(?:is|=|:))?\s+([^\s,;]+@[^\s,;]+)`)
var barePasswordValuePattern = regexp.MustCompile(`(?i)(?:^|[\s,;])password(?:\s+(?:is|=|:))?\s+([^\s,;]+)`)
var clickLoginButtonPattern = regexp.MustCompile(`(?i)(?:click|press|tap)(?:\s+(?:the\s+)?)?(sign in|log in|login|continue|submit)(?:\s+button)?`)
var waitForBarePattern = regexp.MustCompile(`(?i)wait\s+(?:for|until)(?:\s+the\s+url\s+matches)?\s+([/\w.*:-][^\s,;)]*)`)
var stateNameSanitizerPattern = regexp.MustCompile(`[^a-z0-9]+`)

type semanticBrowserAction struct {
	description string
	args        map[string]interface{}
}

func buildBrowserPlan(query string, tools []Tool) []PlanStep {
	lower := strings.ToLower(query)
	if !looksLikeBrowserTask(lower) {
		return nil
	}

	toolNames := make(map[string]struct{}, len(tools))
	for _, tool := range tools {
		toolNames[tool.Name] = struct{}{}
	}

	hasTool := func(name string) bool {
		_, ok := toolNames[name]
		return ok
	}

	var steps []PlanStep
	var previousID string
	order := 1

	appendStep := func(toolName, description string, args map[string]interface{}, dependsOn ...string) {
		if !hasTool(toolName) {
			return
		}
		stepID := fmt.Sprintf("step_%d", order)
		step := PlanStep{
			ID:          stepID,
			Order:       order,
			ToolName:    toolName,
			Arguments:   args,
			Description: description,
			DependsOn:   dependsOn,
		}
		steps = append(steps, step)
		previousID = stepID
		order++
	}

	url := extractFirstURL(query)
	stateName := extractStateName(query)
	wantsLoadState := strings.Contains(lower, "load state") || strings.Contains(lower, "reuse state") || strings.Contains(lower, "resume session")
	wantsSaveState := strings.Contains(lower, "save state") ||
		strings.Contains(lower, "remember login") ||
		strings.Contains(lower, "remember this login") ||
		strings.Contains(lower, "remember this session") ||
		strings.Contains(lower, "persist session") ||
		strings.Contains(lower, "reuse this later") ||
		strings.Contains(lower, "use this later") ||
		strings.Contains(lower, "save this login")
	wantsScreenshot := strings.Contains(lower, "screenshot") || strings.Contains(lower, "screen shot")
	wantsSnapshot := strings.Contains(lower, "snapshot") || strings.Contains(lower, "inspect page") || strings.Contains(lower, "inspect dom") || strings.Contains(lower, "list elements") || strings.Contains(lower, "what buttons")
	if wantsSaveState && stateName == "" {
		stateName = inferBrowserStateName(query, url)
	}

	if wantsLoadState && stateName != "" {
		appendStep("browser_load_state", "Load a reusable browser session state.", map[string]interface{}{
			"state_name":      stateName,
			"headless":        true,
			"viewport_width":  1440,
			"viewport_height": 900,
		})
	} else {
		appendStep("browser_create_session", "Create a fresh browser session.", map[string]interface{}{
			"headless":        true,
			"viewport_width":  1440,
			"viewport_height": 900,
		})
	}

	if previousID == "" {
		return nil
	}

	if url != "" {
		appendStep("browser_open", "Open the target page in the active browser session.", map[string]interface{}{
			"session_id": "$session_id",
			"url":        url,
			"wait_until": "networkidle",
		}, previousID)
	}

	openOrSession := previousID
	if wantsSnapshot || wantsScreenshot || strings.Contains(lower, "click") || strings.Contains(lower, "fill") || strings.Contains(lower, "login") || strings.Contains(lower, "sign in") {
		appendStep("browser_snapshot", "Capture interactive refs from the current page before acting.", map[string]interface{}{
			"session_id": "$session_id",
		}, openOrSession)
		openOrSession = previousID
	}

	for _, action := range extractSemanticBrowserActions(query) {
		appendStep("browser_action", action.description, action.args, openOrSession)
		openOrSession = previousID
	}

	if wantsScreenshot {
		appendStep("browser_screenshot", "Capture a screenshot of the current page.", map[string]interface{}{
			"session_id": "$session_id",
			"full_page":  strings.Contains(lower, "full page"),
		}, openOrSession)
	}

	if wantsSaveState && stateName != "" {
		appendStep("browser_save_state", "Persist the current browser storage state for reuse.", map[string]interface{}{
			"session_id": "$session_id",
			"state_name": stateName,
		}, previousID)
	}

	if len(steps) == 1 && steps[0].ToolName == "browser_create_session" && url == "" {
		if wantsSnapshot {
			appendStep("browser_snapshot", "Capture the current browser page state.", map[string]interface{}{
				"session_id": "$session_id",
			}, previousID)
		}
	}

	return steps
}

func looksLikeBrowserTask(lowerQuery string) bool {
	keywords := []string{
		"http://", "https://", "browser", "website", "web page", "page", "navigate",
		"open site", "open page", "login", "sign in", "screenshot", "snapshot",
		"click", "fill", "form", "session", "state",
	}
	for _, keyword := range keywords {
		if strings.Contains(lowerQuery, keyword) {
			return true
		}
	}
	return false
}

func extractFirstURL(query string) string {
	match := urlPattern.FindString(query)
	return strings.TrimRight(match, ".,)")
}

func extractStateName(query string) string {
	match := stateNamePattern.FindStringSubmatch(query)
	if len(match) < 2 {
		return ""
	}
	return strings.TrimSpace(match[1])
}

func inferBrowserStateName(query, rawURL string) string {
	if rawURL != "" {
		trimmed := strings.TrimSpace(rawURL)
		trimmed = strings.TrimPrefix(trimmed, "https://")
		trimmed = strings.TrimPrefix(trimmed, "http://")
		trimmed = strings.Trim(trimmed, "/")
		if trimmed != "" {
			name := stateNameSanitizerPattern.ReplaceAllString(strings.ToLower(trimmed), "_")
			name = strings.Trim(name, "_")
			if name != "" {
				return name
			}
		}
	}

	lower := strings.ToLower(query)
	switch {
	case strings.Contains(lower, "login"), strings.Contains(lower, "sign in"):
		return "saved_login_state"
	case strings.Contains(lower, "session"):
		return "saved_browser_session"
	default:
		return "saved_browser_state"
	}
}

func extractSemanticBrowserActions(query string) []semanticBrowserAction {
	var actions []semanticBrowserAction
	seen := make(map[string]struct{})

	appendAction := func(description string, args map[string]interface{}) {
		payload, err := json.Marshal(args)
		if err != nil {
			return
		}
		key := description + ":" + string(payload)
		if _, exists := seen[key]; exists {
			return
		}
		seen[key] = struct{}{}
		actions = append(actions, semanticBrowserAction{
			description: description,
			args:        args,
		})
	}

	for _, match := range fillLabelWithQuotedPattern.FindAllStringSubmatch(query, -1) {
		if len(match) < 3 {
			continue
		}
		label := strings.TrimSpace(match[1])
		text := strings.TrimSpace(match[2])
		if label == "" || text == "" {
			continue
		}
		appendAction(fmt.Sprintf("Fill the field labeled %q.", label), map[string]interface{}{
			"session_id": "$session_id",
			"action":     "fill",
			"label":      label,
			"text":       text,
		})
	}

	for _, match := range fillQuotedIntoLabelPattern.FindAllStringSubmatch(query, -1) {
		if len(match) < 3 {
			continue
		}
		text := strings.TrimSpace(match[1])
		label := strings.TrimSpace(match[2])
		if label == "" || text == "" {
			continue
		}
		appendAction(fmt.Sprintf("Fill the field labeled %q.", label), map[string]interface{}{
			"session_id": "$session_id",
			"action":     "fill",
			"label":      label,
			"text":       text,
		})
	}

	for _, match := range clickTargetPattern.FindAllStringSubmatch(query, -1) {
		if len(match) < 2 {
			continue
		}
		name := strings.TrimSpace(match[1])
		role := strings.ToLower(strings.TrimSpace(match[2]))
		if name == "" {
			continue
		}
		if role == "" {
			role = "button"
		}
		appendAction(fmt.Sprintf("Click the %s named %q.", role, name), map[string]interface{}{
			"session_id": "$session_id",
			"action":     "click",
			"role":       role,
			"name":       name,
		})
	}

	for _, match := range waitForPattern.FindAllStringSubmatch(query, -1) {
		if len(match) < 2 {
			continue
		}
		pattern := strings.TrimSpace(match[1])
		if pattern == "" {
			continue
		}
		appendAction(fmt.Sprintf("Wait for the URL pattern %q.", pattern), map[string]interface{}{
			"session_id":  "$session_id",
			"action":      "wait_for",
			"url_pattern": pattern,
			"timeout_ms":  15000,
		})
	}

	for _, match := range emailValuePattern.FindAllStringSubmatch(query, -1) {
		if len(match) < 2 {
			continue
		}
		text := strings.TrimSpace(match[1])
		if text == "" {
			continue
		}
		appendAction(`Fill the field labeled "Email".`, map[string]interface{}{
			"session_id": "$session_id",
			"action":     "fill",
			"label":      "Email",
			"text":       text,
		})
	}

	for _, match := range passwordValuePattern.FindAllStringSubmatch(query, -1) {
		if len(match) < 2 {
			continue
		}
		text := strings.TrimSpace(match[1])
		if text == "" {
			continue
		}
		appendAction(`Fill the field labeled "Password".`, map[string]interface{}{
			"session_id": "$session_id",
			"action":     "fill",
			"label":      "Password",
			"text":       text,
		})
	}

	for _, match := range bareEmailValuePattern.FindAllStringSubmatch(query, -1) {
		if len(match) < 2 {
			continue
		}
		text := strings.TrimSpace(match[1])
		if text == "" {
			continue
		}
		appendAction(`Fill the field labeled "Email".`, map[string]interface{}{
			"session_id": "$session_id",
			"action":     "fill",
			"label":      "Email",
			"text":       text,
		})
	}

	for _, match := range barePasswordValuePattern.FindAllStringSubmatch(query, -1) {
		if len(match) < 2 {
			continue
		}
		text := strings.TrimSpace(match[1])
		if text == "" {
			continue
		}
		appendAction(`Fill the field labeled "Password".`, map[string]interface{}{
			"session_id": "$session_id",
			"action":     "fill",
			"label":      "Password",
			"text":       text,
		})
	}

	for _, match := range clickLoginButtonPattern.FindAllStringSubmatch(query, -1) {
		if len(match) < 2 {
			continue
		}
		name := strings.TrimSpace(match[1])
		if name == "" {
			continue
		}
		appendAction(fmt.Sprintf("Click the button named %q.", name), map[string]interface{}{
			"session_id": "$session_id",
			"action":     "click",
			"role":       "button",
			"name":       name,
		})
	}

	for _, match := range waitForBarePattern.FindAllStringSubmatch(query, -1) {
		if len(match) < 2 {
			continue
		}
		pattern := strings.TrimSpace(match[1])
		if pattern == "" || strings.HasPrefix(strings.ToLower(pattern), "http://") || strings.HasPrefix(strings.ToLower(pattern), "https://") {
			continue
		}
		appendAction(fmt.Sprintf("Wait for the URL pattern %q.", pattern), map[string]interface{}{
			"session_id":  "$session_id",
			"action":      "wait_for",
			"url_pattern": pattern,
			"timeout_ms":  15000,
		})
	}

	return actions
}
