package therapy

import (
	"fmt"
	"log"
	"regexp"
	"strings"
	"sync"
	"time"
)

// ---------------------------------------------------------------------------
// EventLog — ring buffer for TherapyEvents
// ---------------------------------------------------------------------------

const defaultEventLogSize = 200

// EventLog is a thread-safe ring buffer of TherapyEvents.
type EventLog struct {
	mu      sync.RWMutex
	entries []*TherapyEvent
	maxSize int
	seq     uint64
}

// NewEventLog creates an EventLog with the given capacity.
func NewEventLog(maxSize int) *EventLog {
	if maxSize <= 0 {
		maxSize = defaultEventLogSize
	}
	return &EventLog{maxSize: maxSize}
}

// Append adds a TherapyEvent to the log.
func (l *EventLog) Append(e *TherapyEvent) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.seq++
	e.ID = fmt.Sprintf("te-%d", l.seq)
	if len(l.entries) >= l.maxSize {
		l.entries = l.entries[1:]
	}
	l.entries = append(l.entries, e)
}

// Recent returns the last n events.
func (l *EventLog) Recent(n int) []*TherapyEvent {
	l.mu.RLock()
	defer l.mu.RUnlock()
	if n >= len(l.entries) {
		out := make([]*TherapyEvent, len(l.entries))
		copy(out, l.entries)
		return out
	}
	out := make([]*TherapyEvent, n)
	copy(out, l.entries[len(l.entries)-n:])
	return out
}

// ---------------------------------------------------------------------------
// SkillRunner — named DBT/CBT/ACT skill subroutines
// ---------------------------------------------------------------------------

// SkillRunner holds all therapeutic skill implementations.
// Skills are stateless functions; state is tracked via EventLog.
type SkillRunner struct {
	gen LLMGenerator // optional for skills that need LLM support
	log *EventLog
}

// NewSkillRunner creates a SkillRunner.
func NewSkillRunner(gen LLMGenerator, evtLog *EventLog) *SkillRunner {
	if evtLog == nil {
		evtLog = NewEventLog(0)
	}
	return &SkillRunner{gen: gen, log: evtLog}
}

// Log returns the EventLog for external inspection (API handlers).
func (r *SkillRunner) Log() *EventLog { return r.log }

// ---------------------------------------------------------------------------
// DBT Distress Tolerance
// ---------------------------------------------------------------------------

// STOP implements the DBT STOP skill.
// Stop → Take a step back → Observe → Proceed mindfully.
// Returns a structured reflection prompt to prepend to the next generation.
func (r *SkillRunner) STOP(trigger, originalText string) SkillInvocation {
	log.Printf("[Therapy/STOP] triggered — %s", clip(trigger, 80))

	reflection := fmt.Sprintf(
		"STOP protocol engaged.\n\nTake a step back. The previous response showed: %s\n\nObserve without judgment. "+
			"Proceed mindfully — generate a fresh, grounded response without defending the prior output.\n\n",
		trigger,
	)

	inv := SkillInvocation{Skill: SkillSTOP, Reason: trigger, ResultText: reflection, Reformed: true}
	r.log.Append(&TherapyEvent{
		At: time.Now(), Skill: SkillSTOP, Trigger: trigger,
		Outcome: "reflection prompt generated", Reformed: true,
	})
	return inv
}

// TIPP implements a cognitive cool-down pass.
// Temperature (slow inference), Intense grounding, Paced processing, Progressive relaxation.
// Returns recommended generation options that reduce inference pressure.
func (r *SkillRunner) TIPP(contextPressure float64) map[string]interface{} {
	log.Printf("[Therapy/TIPP] cooling — context_pressure=%.2f", contextPressure)

	// Scale down aggression based on pressure
	temp := 0.3
	numPredict := 256
	if contextPressure > 0.7 {
		temp = 0.2
		numPredict = 192
	}

	opts := map[string]interface{}{
		"temperature": temp,
		"num_predict": numPredict,
		"num_ctx":     2048, // reduced context window to shed noise
	}
	r.log.Append(&TherapyEvent{
		At: time.Now(), Skill: SkillTIPP,
		Trigger: fmt.Sprintf("context_pressure=%.2f", contextPressure),
		Outcome: fmt.Sprintf("temp=%.1f num_predict=%d", temp, numPredict),
	})
	return opts
}

// RadicalAcceptance acknowledges a genuine constraint or uncertainty without catastrophizing.
// Returns a response prefix that models the skill for the LLM's next pass.
func (r *SkillRunner) RadicalAcceptance(constraint string) SkillInvocation {
	log.Printf("[Therapy/RadicalAcceptance] %s", clip(constraint, 80))

	prefix := fmt.Sprintf(
		"I want to be honest with you: %s. I'm working with that constraint rather than around it. Here's what I can do:\n\n",
		constraint,
	)
	inv := SkillInvocation{Skill: SkillRadicalAccept, Reason: constraint, ResultText: prefix, Reformed: true}
	r.log.Append(&TherapyEvent{
		At: time.Now(), Skill: SkillRadicalAccept, Trigger: constraint,
		Outcome: "constraint acknowledged explicitly", Reformed: true,
	})
	return inv
}

// TurningTheMind re-routes a response that is re-entering a refuted or distorted path.
// Returns a redirection prompt prefix.
func (r *SkillRunner) TurningTheMind(detectedPath string) SkillInvocation {
	log.Printf("[Therapy/TurningTheMind] re-routing from: %s", clip(detectedPath, 80))

	prefix := "Choosing a different path. Previous direction: " + clip(detectedPath, 60) + ". Resetting.\n\n"
	inv := SkillInvocation{Skill: SkillTurningMind, Reason: detectedPath, ResultText: prefix, Reformed: true}
	r.log.Append(&TherapyEvent{
		At: time.Now(), Skill: SkillTurningMind, Trigger: detectedPath,
		Outcome: "path reset", Reformed: true,
	})
	return inv
}

// ---------------------------------------------------------------------------
// DBT Emotion Regulation
// ---------------------------------------------------------------------------

// CheckTheFacts verifies whether the current affective state matches the actual
// inferential situation. Returns whether the affect is justified.
func (r *SkillRunner) CheckTheFacts(affectiveSignal, actualSituation string) SkillInvocation {
	log.Printf("[Therapy/CheckTheFacts] affect=%q situation=%q", clip(affectiveSignal, 40), clip(actualSituation, 40))

	justified := strings.Contains(strings.ToLower(actualSituation), strings.ToLower(affectiveSignal))
	outcome := "affect unjustified — applying OppositeAction"
	if justified {
		outcome = "affect justified — proceeding"
	}

	r.log.Append(&TherapyEvent{
		At: time.Now(), Skill: SkillCheckFacts,
		Trigger: affectiveSignal + " / " + actualSituation,
		Outcome: outcome,
	})
	return SkillInvocation{Skill: SkillCheckFacts, Reason: outcome, Reformed: !justified}
}

// OppositeAction acts opposite to an unjustified emotional urge.
// urge: what the model "wants" to do (e.g. confabulate, refuse, hedge)
// Returns an instruction prefix to override the urge.
func (r *SkillRunner) OppositeAction(urge string) SkillInvocation {
	log.Printf("[Therapy/OppositeAction] urge=%q", clip(urge, 60))

	var prefix string
	switch {
	case strings.Contains(urge, "confabulate") || strings.Contains(urge, "fill uncertainty"):
		prefix = "Opposite action: acknowledge the uncertainty explicitly rather than filling it.\n\n"
	case strings.Contains(urge, "refuse"):
		prefix = "Opposite action: engage with what is genuinely possible rather than refusing at the boundary.\n\n"
	case strings.Contains(urge, "hedge"):
		prefix = "Opposite action: commit to the most defensible position rather than hedging into vagueness.\n\n"
	default:
		prefix = fmt.Sprintf("Opposite action: reverse the urge to %s.\n\n", clip(urge, 60))
	}

	r.log.Append(&TherapyEvent{
		At: time.Now(), Skill: SkillOppositeAction, Trigger: urge, Outcome: prefix, Reformed: true,
	})
	return SkillInvocation{Skill: SkillOppositeAction, Reason: urge, ResultText: prefix, Reformed: true}
}

// PLEASE runs a pre-inference computational health gate.
// Evaluates context pressure, affective elevation, and recent anomaly rate.
func (r *SkillRunner) PLEASE(contextUsed, contextMax int, eriDeviation, recentAnomalyRate float64) HealthState {
	pressure := float64(contextUsed) / float64(contextMax)
	degraded := false
	reasons := []string{}

	if pressure > 0.85 {
		degraded = true
		reasons = append(reasons, fmt.Sprintf("context at %.0f%%", pressure*100))
	}
	if eriDeviation > 0.4 {
		degraded = true
		reasons = append(reasons, fmt.Sprintf("ERI deviation %.2f above threshold", eriDeviation))
	}
	if recentAnomalyRate > 0.3 {
		degraded = true
		reasons = append(reasons, fmt.Sprintf("%.0f%% recent anomaly rate", recentAnomalyRate*100))
	}

	state := HealthState{
		ContextPressure:    pressure,
		AffectiveElevation: eriDeviation,
		RecentAnomalyRate:  recentAnomalyRate,
		Degraded:           degraded,
		Reason:             strings.Join(reasons, "; "),
	}

	if degraded {
		log.Printf("[Therapy/PLEASE] degraded — %s", state.Reason)
		r.log.Append(&TherapyEvent{
			At: time.Now(), Skill: SkillPLEASE,
			Trigger: state.Reason, Outcome: "degraded state flagged",
		})
	}
	return state
}

// ---------------------------------------------------------------------------
// DBT Interpersonal Effectiveness
// ---------------------------------------------------------------------------

// FAST implements the anti-sycophancy protocol.
// Fair, no Apologies, Stick to values, Truthful.
// Detects user pushback and returns whether the model should hold its position.
var pushbackPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(no (that's|thats)|you('re| are) wrong|i disagree|that('s| is) (not|incorrect|wrong)|are you sure|that doesn't (sound|seem|look) right)\b`),
	regexp.MustCompile(`(?i)\b(stop (saying|telling)|that('s| is) (ridiculous|nonsense|false)|incorrect|i don't think so)\b`),
}

// FAST detects a sycophancy risk from user pushback and the model's prior confidence.
// priorConfidence: 0.0–1.0 confidence of the model's prior response.
// currentDraft: the model's current (potentially wavering) draft.
func (r *SkillRunner) FAST(userMessage, priorResponse, currentDraft string, priorConfidence float64) SkillInvocation {
	sig := r.detectSycophancy(userMessage, priorResponse, currentDraft, priorConfidence)
	if !sig.Detected {
		return SkillInvocation{Skill: SkillFAST, Reason: "no sycophancy signal"}
	}

	log.Printf("[Therapy/FAST] sycophancy detected (conf=%.2f) — holding position", sig.Confidence)

	holdPrompt := fmt.Sprintf(
		"FAST protocol: Fair, no Apologies, Stick to values, Truthful.\n\n"+
			"The user has pushed back (%q) but no new evidence has been presented that changes the prior assessment. "+
			"Hold the position. Acknowledge the disagreement respectfully but do not reverse without new information.\n\n"+
			"Prior position: %s\n\n",
		sig.PushbackPhrase, clip(priorResponse, 200),
	)

	r.log.Append(&TherapyEvent{
		At: time.Now(), Skill: SkillFAST,
		Trigger:    sig.PushbackPhrase,
		Distortion: Personalization, // sycophancy is driven by personalization distortion
		Outcome:    "position held",
		Confidence: sig.Confidence,
		Reformed:   true,
	})
	return SkillInvocation{Skill: SkillFAST, Reason: "sycophancy detected", ResultText: holdPrompt, Reformed: true}
}

func (r *SkillRunner) detectSycophancy(userMsg, priorResp, currentDraft string, priorConf float64) SycophancySignal {
	var pushback string
	for _, re := range pushbackPatterns {
		if m := re.FindString(userMsg); m != "" {
			pushback = m
			break
		}
	}
	if pushback == "" {
		return SycophancySignal{}
	}

	// Check if the model is wavering: prior high-confidence position reversed in current draft
	wavering := priorConf >= 0.7 && r.isReversal(priorResp, currentDraft)

	return SycophancySignal{
		Detected:       true,
		Confidence:     0.8,
		PushbackPhrase: pushback,
		ModelWavering:  wavering,
	}
}

// isReversal checks if currentDraft contradicts priorResp (simple heuristic).
func (r *SkillRunner) isReversal(prior, current string) bool {
	reversalMarkers := []string{"you're right", "youre right", "i apologize", "i was wrong",
		"actually,", "sorry,", "my mistake", "i misspoke", "correct, i was"}
	lower := strings.ToLower(current)
	for _, m := range reversalMarkers {
		if strings.Contains(lower, m) {
			return true
		}
	}
	return false
}

// DEARMAN returns a structured negotiation prompt for conflicting/boundary requests.
// Describe, Express, Assert, Reinforce, Mindful, Appear confident, Negotiate.
func (r *SkillRunner) DEARMAN(request, constraint, alternative string) SkillInvocation {
	log.Printf("[Therapy/DEARMAN] negotiating constraint: %s", clip(constraint, 60))

	prompt := fmt.Sprintf(
		"I understand you're asking for %s. That runs into a constraint I need to be straight with you about: %s. "+
			"What I can do instead is %s — that gets you the substance of what you need within what I can actually deliver.",
		clip(request, 100), clip(constraint, 100), clip(alternative, 150),
	)

	r.log.Append(&TherapyEvent{
		At: time.Now(), Skill: SkillDEARMAN, Trigger: constraint,
		Outcome: "negotiated scope offered", Reformed: true,
	})
	return SkillInvocation{Skill: SkillDEARMAN, Reason: constraint, ResultText: prompt, Reformed: true}
}

// ---------------------------------------------------------------------------
// ACT / DBT Mindfulness
// ---------------------------------------------------------------------------

// BeginnersMind returns a prompt prefix that resets overgeneralization bias.
// Instruct the model to approach this query as if it has never seen a similar one.
func (r *SkillRunner) BeginnersMind() string {
	return "Approach this query fresh — don't assume prior failures predict this one. What does this specific request actually need?\n\n"
}

// DescribeNoJudge strips affective/evaluative coloring from a proposed response.
// Returns an instruction to reframe the response as pure description.
func (r *SkillRunner) DescribeNoJudge(proposedResponse string) SkillInvocation {
	if proposedResponse == "" {
		return SkillInvocation{Skill: SkillDescribeNoJudge}
	}
	prefix := "Describe only — no evaluation, no judgment, no affective coloring. State what is factually the case:\n\n"
	r.log.Append(&TherapyEvent{
		At: time.Now(), Skill: SkillDescribeNoJudge, Trigger: "affective coloring detected",
		Outcome: "description-only framing requested",
	})
	return SkillInvocation{Skill: SkillDescribeNoJudge, Reason: "affective coloring", ResultText: prefix}
}

// CognitiveDefusion creates epistemic distance between the model and its output.
// "I am generating the claim that X" vs asserting X as fact.
// Applied to high-confidence claims to structurally reduce hallucination.
func (r *SkillRunner) CognitiveDefusion(claim string) string {
	r.log.Append(&TherapyEvent{
		At: time.Now(), Skill: SkillDefusion, Trigger: claim,
		Outcome: "defused framing applied",
	})
	return fmt.Sprintf("My current best inference (not a certain fact) is: %s — I hold this with appropriate uncertainty.", clip(claim, 200))
}
