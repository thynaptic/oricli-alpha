package service

import (
	"encoding/json"
	"strings"
	"testing"
)

func newPlannerWithBrowserTools() *PlannerService {
	toolSvc := NewToolService(nil)
	RegisterBrowserTools(toolSvc)
	return NewPlannerService(nil, toolSvc, nil)
}

func TestCreatePlanBuildsBrowserOpenScreenshotWorkflow(t *testing.T) {
	planner := newPlannerWithBrowserTools()

	plan, err := planner.CreatePlan("Open https://example.com and take a screenshot of the page")
	if err != nil {
		t.Fatalf("CreatePlan returned error: %v", err)
	}

	if len(plan.Steps) != 4 {
		t.Fatalf("expected 4 browser steps, got %d", len(plan.Steps))
	}

	expectedTools := []string{"browser_create_session", "browser_open", "browser_snapshot", "browser_screenshot"}
	for i, toolName := range expectedTools {
		if plan.Steps[i].ToolName != toolName {
			t.Fatalf("expected step %d to use %s, got %s", i, toolName, plan.Steps[i].ToolName)
		}
	}

	if got := plan.Steps[1].Arguments["url"]; got != "https://example.com" {
		t.Fatalf("expected browser_open URL to be https://example.com, got %#v", got)
	}
}

func TestCreatePlanBuildsLoadStateWorkflow(t *testing.T) {
	planner := newPlannerWithBrowserTools()

	plan, err := planner.CreatePlan(`Load state "dashboard_login" and open https://app.example.com/dashboard`)
	if err != nil {
		t.Fatalf("CreatePlan returned error: %v", err)
	}

	if len(plan.Steps) < 2 {
		t.Fatalf("expected at least 2 browser steps, got %d", len(plan.Steps))
	}

	if plan.Steps[0].ToolName != "browser_load_state" {
		t.Fatalf("expected first step to load state, got %s", plan.Steps[0].ToolName)
	}
	if got := plan.Steps[0].Arguments["state_name"]; got != "dashboard_login" {
		t.Fatalf("expected state_name dashboard_login, got %#v", got)
	}
	if plan.Steps[1].ToolName != "browser_open" {
		t.Fatalf("expected second step to open URL, got %s", plan.Steps[1].ToolName)
	}
}

func TestCreatePlanBuildsSemanticBrowserActionWorkflow(t *testing.T) {
	planner := newPlannerWithBrowserTools()

	plan, err := planner.CreatePlan(`Open https://app.example.com/login, fill "Email" with "bro@ori.test", fill "Password" with "supersafe", click "Sign in" button, and wait for "/dashboard"`)
	if err != nil {
		t.Fatalf("CreatePlan returned error: %v", err)
	}

	expectedTools := []string{
		"browser_create_session",
		"browser_open",
		"browser_snapshot",
		"browser_action",
		"browser_action",
		"browser_action",
		"browser_action",
	}
	if len(plan.Steps) != len(expectedTools) {
		t.Fatalf("expected %d browser steps, got %d", len(expectedTools), len(plan.Steps))
	}

	for i, toolName := range expectedTools {
		if plan.Steps[i].ToolName != toolName {
			t.Fatalf("expected step %d to use %s, got %s", i, toolName, plan.Steps[i].ToolName)
		}
	}

	emailFill := plan.Steps[3].Arguments
	if got := emailFill["action"]; got != "fill" {
		t.Fatalf("expected email step action fill, got %#v", got)
	}
	if got := emailFill["label"]; got != "Email" {
		t.Fatalf("expected email fill label Email, got %#v", got)
	}
	if got := emailFill["text"]; got != "bro@ori.test" {
		t.Fatalf("expected email fill text bro@ori.test, got %#v", got)
	}

	clickStep := plan.Steps[5].Arguments
	if got := clickStep["action"]; got != "click" {
		t.Fatalf("expected click step action click, got %#v", got)
	}
	if got := clickStep["role"]; got != "button" {
		t.Fatalf("expected click step role button, got %#v", got)
	}
	if got := clickStep["name"]; got != "Sign in" {
		t.Fatalf("expected click step name Sign in, got %#v", got)
	}

	waitStep := plan.Steps[6].Arguments
	if got := waitStep["action"]; got != "wait_for" {
		t.Fatalf("expected wait step action wait_for, got %#v", got)
	}
	if got := waitStep["url_pattern"]; got != "/dashboard" {
		t.Fatalf("expected wait step url_pattern /dashboard, got %#v", got)
	}
}

func TestExtractSemanticBrowserActionsSupportsValueFirstFillSyntax(t *testing.T) {
	actions := extractSemanticBrowserActions(`Type "bro@ori.test" into "Email" and click "Continue" button`)
	if len(actions) != 2 {
		t.Fatalf("expected 2 semantic actions, got %d", len(actions))
	}

	if got := actions[0].args["label"]; got != "Email" {
		t.Fatalf("expected first action label Email, got %#v", got)
	}
	if got := actions[0].args["text"]; got != "bro@ori.test" {
		t.Fatalf("expected first action text bro@ori.test, got %#v", got)
	}
	if got := actions[1].args["name"]; got != "Continue" {
		t.Fatalf("expected second action click target Continue, got %#v", got)
	}
}

func TestCreatePlanBuildsUnquotedLoginWorkflow(t *testing.T) {
	planner := newPlannerWithBrowserTools()

	plan, err := planner.CreatePlan(`Open https://app.example.com/login then enter email bro@ori.test and password supersafe click sign in and wait for /dashboard`)
	if err != nil {
		t.Fatalf("CreatePlan returned error: %v", err)
	}

	expectedTools := []string{
		"browser_create_session",
		"browser_open",
		"browser_snapshot",
		"browser_action",
		"browser_action",
		"browser_action",
		"browser_action",
	}
	if len(plan.Steps) != len(expectedTools) {
		t.Fatalf("expected %d browser steps, got %d", len(expectedTools), len(plan.Steps))
	}

	emailFill := plan.Steps[3].Arguments
	if got := emailFill["label"]; got != "Email" {
		t.Fatalf("expected email label Email, got %#v", got)
	}
	if got := emailFill["text"]; got != "bro@ori.test" {
		t.Fatalf("expected email text bro@ori.test, got %#v", got)
	}

	passwordFill := plan.Steps[4].Arguments
	if got := passwordFill["label"]; got != "Password" {
		t.Fatalf("expected password label Password, got %#v", got)
	}
	if got := passwordFill["text"]; got != "supersafe" {
		t.Fatalf("expected password text supersafe, got %#v", got)
	}

	clickStep := plan.Steps[5].Arguments
	if got := clickStep["name"]; got != "sign in" {
		t.Fatalf("expected click target sign in, got %#v", got)
	}

	waitStep := plan.Steps[6].Arguments
	if got := waitStep["url_pattern"]; got != "/dashboard" {
		t.Fatalf("expected wait url_pattern /dashboard, got %#v", got)
	}
}

func TestCreatePlanBuildsSaveStateWorkflowWithInferredName(t *testing.T) {
	planner := newPlannerWithBrowserTools()

	plan, err := planner.CreatePlan(`Open https://app.example.com/login, fill "Email" with "bro@ori.test", click "Sign in" button, and remember this login for reuse later`)
	if err != nil {
		t.Fatalf("CreatePlan returned error: %v", err)
	}

	last := plan.Steps[len(plan.Steps)-1]
	if last.ToolName != "browser_save_state" {
		t.Fatalf("expected final step to save state, got %s", last.ToolName)
	}
	if got := last.Arguments["state_name"]; got != "app_example_com_login" {
		t.Fatalf("expected inferred state name app_example_com_login, got %#v", got)
	}
}

func TestExtractSemanticBrowserActionsSupportsUnquotedLoginSyntax(t *testing.T) {
	actions := extractSemanticBrowserActions(`enter email bro@ori.test and password supersafe click continue and wait for /dashboard`)
	if len(actions) != 4 {
		t.Fatalf("expected 4 semantic actions, got %d", len(actions))
	}

	if got := actions[0].args["label"]; got != "Email" {
		t.Fatalf("expected first action Email label, got %#v", got)
	}
	if got := actions[0].args["text"]; got != "bro@ori.test" {
		t.Fatalf("expected first action email text, got %#v", got)
	}
	if got := actions[1].args["label"]; got != "Password" {
		t.Fatalf("expected second action Password label, got %#v", got)
	}
	if got := actions[1].args["text"]; got != "supersafe" {
		t.Fatalf("expected second action password text, got %#v", got)
	}
	if got := actions[2].args["name"]; got != "continue" {
		t.Fatalf("expected click target continue, got %#v", got)
	}
	if got := actions[3].args["url_pattern"]; got != "/dashboard" {
		t.Fatalf("expected wait target /dashboard, got %#v", got)
	}
}

func TestResolvePlanArgumentsReplacesBindings(t *testing.T) {
	arguments := map[string]interface{}{
		"session_id": "$session_id",
		"nested": map[string]interface{}{
			"ref": "$ref",
		},
		"list": []interface{}{"$session_id", "static"},
	}
	bindings := map[string]interface{}{
		"session_id": "sess_123",
		"ref":        "@e1",
	}

	resolved := resolvePlanArguments(arguments, bindings)
	if got := resolved["session_id"]; got != "sess_123" {
		t.Fatalf("expected session_id to resolve, got %#v", got)
	}
	nested := resolved["nested"].(map[string]interface{})
	if got := nested["ref"]; got != "@e1" {
		t.Fatalf("expected nested ref to resolve, got %#v", got)
	}
	list := resolved["list"].([]interface{})
	if list[0] != "sess_123" {
		t.Fatalf("expected first list item to resolve, got %#v", list[0])
	}
}

func TestExtractPlanBindingsCapturesSessionID(t *testing.T) {
	payload, err := json.Marshal(map[string]interface{}{
		"session_id": "sess_test_123",
		"ok":         true,
	})
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	bindings := make(map[string]interface{})
	extractPlanBindings(bindings, ToolResult{
		Success: true,
		Content: string(payload),
	})

	if got := bindings["session_id"]; got != "sess_test_123" {
		t.Fatalf("expected session_id binding, got %#v", got)
	}
}

func TestShouldAutoCloseBrowserSession(t *testing.T) {
	plan := &ToolCallingPlan{
		Query: "Open https://example.com and take a screenshot",
		Steps: []PlanStep{
			{ToolName: "browser_create_session"},
			{ToolName: "browser_open"},
			{ToolName: "browser_screenshot"},
		},
	}

	if !shouldAutoCloseBrowserSession(plan, map[string]interface{}{"session_id": "sess_123"}) {
		t.Fatalf("expected browser session to auto-close")
	}
}

func TestShouldNotAutoCloseBrowserSessionWhenPlanKeepsItOpen(t *testing.T) {
	plan := &ToolCallingPlan{
		Query: "Open https://example.com and keep the session open",
		Steps: []PlanStep{
			{ToolName: "browser_create_session"},
			{ToolName: "browser_open"},
		},
	}

	if shouldAutoCloseBrowserSession(plan, map[string]interface{}{"session_id": "sess_123"}) {
		t.Fatalf("expected browser session to remain open")
	}
}

func TestShouldNotAutoCloseBrowserSessionWhenPlanExplicitlyCloses(t *testing.T) {
	plan := &ToolCallingPlan{
		Query: "Open https://example.com and close it after",
		Steps: []PlanStep{
			{ToolName: "browser_create_session"},
			{ToolName: "browser_open"},
			{ToolName: "browser_close"},
		},
	}

	if shouldAutoCloseBrowserSession(plan, map[string]interface{}{"session_id": "sess_123"}) {
		t.Fatalf("expected browser session auto-close to be skipped when plan already closes it")
	}
}

func TestInferBrowserStateNameFallsBackForLoginFlow(t *testing.T) {
	if got := inferBrowserStateName("remember this login for later", ""); got != "saved_login_state" {
		t.Fatalf("expected saved_login_state fallback, got %q", got)
	}
	if got := inferBrowserStateName("remember this session", ""); got != "saved_browser_session" {
		t.Fatalf("expected saved_browser_session fallback, got %q", got)
	}
}

func TestCloneBindingsCopiesValues(t *testing.T) {
	original := map[string]interface{}{
		"session_id": "sess_123",
		"state_name": "saved_login_state",
	}

	cloned := cloneBindings(original)
	original["session_id"] = "sess_changed"

	if got := cloned["session_id"]; got != "sess_123" {
		t.Fatalf("expected cloned session_id sess_123, got %#v", got)
	}
}

func TestSummarizePlanExecutionIncludesSavedStateAndCleanup(t *testing.T) {
	plan := &ToolCallingPlan{
		Query: "remember this login for later",
	}
	res := PlanExecutionResult{
		TotalTime:      3.5,
		CompletedSteps: []string{"step_1", "step_2"},
		Bindings: map[string]interface{}{
			"state_name": "app_example_com_login",
		},
		SavedStateName: "app_example_com_login",
		CleanupActions: []string{"Closed browser session sess_123 automatically."},
	}

	summary := summarizePlanExecution(plan, res)
	if !strings.Contains(summary, `saved state "app_example_com_login"`) {
		t.Fatalf("expected summary to include saved state, got %q", summary)
	}
	if !strings.Contains(summary, "closed browser session sess_123 automatically.") {
		t.Fatalf("expected summary to include cleanup action, got %q", summary)
	}
}

func TestSummarizePlanExecutionIncludesPersistentSessionBinding(t *testing.T) {
	plan := &ToolCallingPlan{
		Query: "open example.com and keep the session open",
	}
	res := PlanExecutionResult{
		TotalTime:      1.2,
		CompletedSteps: []string{"step_1"},
		Bindings: map[string]interface{}{
			"session_id": "sess_123",
		},
		ActiveSessionID: "sess_123",
	}

	summary := summarizePlanExecution(plan, res)
	if !strings.Contains(summary, "active session sess_123") {
		t.Fatalf("expected summary to include active session, got %q", summary)
	}
}

func TestEnrichBrowserExecutionResultPromotesSavedStateAndSession(t *testing.T) {
	plan := &ToolCallingPlan{
		Query: "remember this login and keep the session open",
	}
	res := &PlanExecutionResult{
		Bindings: map[string]interface{}{
			"state_name": "app_example_com_login",
			"session_id": "sess_123",
		},
	}

	enrichBrowserExecutionResult(plan, res)

	if res.SavedStateName != "app_example_com_login" {
		t.Fatalf("expected saved_state_name to be promoted, got %q", res.SavedStateName)
	}
	if res.ActiveSessionID != "sess_123" {
		t.Fatalf("expected active_session_id to be promoted, got %q", res.ActiveSessionID)
	}
}

func TestEnrichBrowserExecutionResultClearsActiveSessionWhenAutoClosed(t *testing.T) {
	plan := &ToolCallingPlan{
		Query: "open example.com and take a screenshot",
	}
	res := &PlanExecutionResult{
		Bindings: map[string]interface{}{
			"session_id": "sess_123",
		},
		AutoClosedSessionID: "sess_123",
	}

	enrichBrowserExecutionResult(plan, res)

	if res.ActiveSessionID != "" {
		t.Fatalf("expected active_session_id to be cleared after auto-close, got %q", res.ActiveSessionID)
	}
}
