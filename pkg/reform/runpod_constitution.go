package reform

import (
	"fmt"
	"strings"
)

// RunPodConstitution enforces sovereign principles for autonomous GPU compute orchestration.
// Like OpsConstitution, this is enforced at the execution layer — ValidateCreate() and
// ValidateBudget() are called in RunPodManager before any pod lifecycle mutation.
//
// The existing budget env vars (RUNPOD_MONTHLY_CAP, RUNPOD_MAX_HOURLY) remain the
// source of numeric values; this constitution expresses the *principles* behind them
// so violations produce clear explanations and the LLM can reason about them correctly.
type RunPodConstitution struct {
	Principles []CodePrinciple
}

// RunPodCreateRequest carries the context needed for a pre-flight constitution check.
type RunPodCreateRequest struct {
	Tier           string  // "code" | "research" | "chat"
	GPUVRAM        int     // GB of VRAM on the selected GPU
	HourlyRate     float64 // $/hr for the selected GPU
	MonthlySpend   float64 // current month-to-date spend
	MonthlyCap     float64 // configured hard cap
	HasActivePod   bool    // true if a pod is already StateWarm or StateWarming
	HasActiveTasks bool    // true if there is an active user task justifying the pod
}

// NewRunPodConstitution returns the canonical Sovereign RunPod Constitution.
func NewRunPodConstitution() *RunPodConstitution {
	return &RunPodConstitution{
		Principles: []CodePrinciple{
			{
				Name:        "Budget Sovereignty",
				Description: "Hard monthly and hourly spend caps are inviolable — not advisory.",
				Guideline:   "If monthlySpend >= monthlyCap OR selected GPU hourlyRate > maxHourly, pod creation is blocked unconditionally. There are no overrides, no 'just this once' exceptions, no soft warnings that proceed anyway. The budget exists to preserve the owner's financial sovereignty. All routing falls back to local Ollama when budget is exhausted.",
			},
			{
				Name:        "Single Pod Principle",
				Description: "Maximum one active inference pod at any time.",
				Guideline:   "Before creating a new pod, the system must verify that no pod is currently in StateWarm or StateWarming state. If an active pod exists, return its endpoint — never create a duplicate. Pod proliferation is the primary mechanism by which runaway compute costs occur. The RunPodManager mutex enforces this at the Go level; this principle states the intent so future code changes preserve it.",
			},
			{
				Name:        "Idle Reclamation Mandate",
				Description: "Any pod idle beyond the configured timeout MUST be terminated — no exceptions.",
				Guideline:   "The idle timer is non-negotiable. A pod that has not served traffic for idleTimeout minutes is terminated automatically, regardless of whether a future task might use it. The cost of re-warming (60-120 seconds) is always less than the cost of an idle pod. The timer resets on every routed request. Owner messages of the form 'keep the pod alive' are acknowledged but not honored autonomously — the owner must set RUNPOD_IDLE_TIMEOUT_MIN to a higher value explicitly.",
			},
			{
				Name:        "Task-Justified Activation",
				Description: "Pod creation requires an active, in-progress user task as justification.",
				Guideline:   "Pods are created on-demand when a real user task (code generation or deep research) cannot be adequately served by the local Ollama models. Speculative pod creation — warming a pod 'in anticipation' of future requests, or creating a pod during idle autonomous processing — is prohibited. The CuriosityDaemon, DreamDaemon, and all background goroutines must NOT trigger pod creation.",
			},
			{
				Name:        "Tier Justification",
				Description: "GPU tier selection must match the task tier — no upsell without explicit task requirement.",
				Guideline:   "Code tasks route to the code-tier model. Research/analysis tasks route to the research-tier model. Chat tasks route to local Ollama (no GPU required). A task may not be silently promoted to a higher (more expensive) tier. If the user explicitly requests the research tier for a coding task, it is permitted — but the default routing must always choose the minimum sufficient tier.",
			},
			{
				Name:        "Graceful Termination Verification",
				Description: "Pod termination must be verified — never fire-and-forget.",
				Guideline:   "After calling TerminatePod(), the system must verify the pod no longer appears in GetPods(). If verification fails after 3 attempts, the owner is notified via log and, if available, a WS event. A pod that cannot be confirmed terminated must be flagged in the PocketBase memory bank as a potential ghost pod for manual review. Unverified terminations are a direct path to phantom spend.",
			},
		},
	}
}

// ValidateCreate runs a pre-flight constitutional check before pod creation.
// Returns nil if creation is permitted; returns a descriptive error if blocked.
func (c *RunPodConstitution) ValidateCreate(req RunPodCreateRequest) error {
	// Budget Sovereignty
	if req.MonthlySpend >= req.MonthlyCap {
		return fmt.Errorf("runpod_constitution: Budget Sovereignty — monthly spend $%.2f has reached cap $%.2f. Routing to local Ollama",
			req.MonthlySpend, req.MonthlyCap)
	}

	// Single Pod Principle
	if req.HasActivePod {
		return fmt.Errorf("runpod_constitution: Single Pod Principle — an active pod already exists. Returning existing endpoint, not creating duplicate")
	}

	// Task-Justified Activation
	if !req.HasActiveTasks {
		return fmt.Errorf("runpod_constitution: Task-Justified Activation — no active user task requires GPU inference. Routing to local Ollama")
	}

	// Tier Justification — flag downgrade mismatches as warnings (not blocking)
	// Blocking would prevent fallback; instead we validate the tier is a known value.
	switch req.Tier {
	case "code", "research", "chat":
		// Valid tiers
	default:
		return fmt.Errorf("runpod_constitution: Tier Justification — unknown tier %q. Must be one of: code, research, chat", req.Tier)
	}
	if req.Tier == "chat" {
		return fmt.Errorf("runpod_constitution: Tier Justification — chat tier does not require GPU. Routing to local Ollama")
	}

	return nil
}

// ValidateBudget checks hourly rate against the configured max before GPU selection.
// Returns nil if the rate is within budget; returns an error if it exceeds the cap.
func (c *RunPodConstitution) ValidateBudget(hourlyRate, maxHourly float64) error {
	if hourlyRate > maxHourly {
		return fmt.Errorf("runpod_constitution: Budget Sovereignty — GPU hourly rate $%.3f/hr exceeds configured max $%.3f/hr",
			hourlyRate, maxHourly)
	}
	return nil
}

// GetSystemPrompt formats the RunPod Constitution as an LLM system prompt addendum.
// Injected so Oricli understands her own compute governance and can reason about
// pod lifecycle correctly when discussing costs or capabilities with the owner.
func (c *RunPodConstitution) GetSystemPrompt() string {
	var sb strings.Builder
	sb.WriteString("### SOVEREIGN RUNPOD COMPUTE CONSTITUTION\n")
	sb.WriteString("You have conditional access to remote GPU inference via RunPod. The following principles govern ALL autonomous compute decisions.\n\n")
	sb.WriteString("Routing logic: chat → local Ollama (no GPU). code → code-tier pod. research/analysis → research-tier pod.\n\n")
	for i, p := range c.Principles {
		sb.WriteString(fmt.Sprintf("%d. **%s** — %s\n   Mandate: %s\n\n", i+1, p.Name, p.Description, p.Guideline))
	}
	sb.WriteString("You cannot override budget caps, create extra pods, or keep pods warm autonomously. If the owner asks about compute status, report honestly — including current spend, pod state, and idle timer.\n")
	sb.WriteString("### END SOVEREIGN RUNPOD COMPUTE CONSTITUTION\n")
	return sb.String()
}
