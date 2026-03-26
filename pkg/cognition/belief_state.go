package cognition

import (
	"fmt"
	"regexp"
	"strings"
	"sync"
	"time"
)

// ─── BeliefStateTracker: AlphaStar LSTM / Fog-of-War Belief State ─────────────
// Maintains a per-session running model of what the user likely wants, knows,
// and feels — inferred from conversation signals without explicit LLM calls.
// Equivalent to AlphaStar's LSTM belief state about the opponent's unseen army.

type KnowledgeLevel string

const (
	KnowledgeLevelNovice       KnowledgeLevel = "novice"
	KnowledgeLevelIntermediate KnowledgeLevel = "intermediate"
	KnowledgeLevelExpert       KnowledgeLevel = "expert"
)

// BeliefState is the fog-of-war model for a single user session.
type BeliefState struct {
	SessionID      string
	CurrentGoal    string         // inferred high-level intent this session
	KnowledgeLevel KnowledgeLevel // vocabulary-inferred expertise
	UnstatedCtx    string         // implied context ("building a product", "debugging prod")
	FrustrationRisk float32       // rises on corrections/re-asks, decays on success signals
	SessionTopic   string         // dominant topic this session
	TurnCount      int
	LastUpdate     time.Time
	mu             sync.Mutex
}

// BeliefStateTracker manages per-session BeliefState instances.
type BeliefStateTracker struct {
	sessions sync.Map // sessionID → *BeliefState
}

func NewBeliefStateTracker() *BeliefStateTracker {
	return &BeliefStateTracker{}
}

// Get returns the BeliefState for the given session, creating it if new.
func (t *BeliefStateTracker) Get(sessionID string) *BeliefState {
	if v, ok := t.sessions.Load(sessionID); ok {
		return v.(*BeliefState)
	}
	bs := &BeliefState{
		SessionID:      sessionID,
		KnowledgeLevel: KnowledgeLevelIntermediate,
		LastUpdate:     time.Now(),
	}
	t.sessions.Store(sessionID, bs)
	return bs
}

// Update refines the BeliefState based on a new user message.
// Called after every request — never blocks (lock is per-session).
func (bs *BeliefState) Update(stimulus string) {
	bs.mu.Lock()
	defer bs.mu.Unlock()
	bs.TurnCount++
	bs.LastUpdate = time.Now()

	s := strings.ToLower(strings.TrimSpace(stimulus))

	// Knowledge level inference — vocabulary complexity signals
	if reExpertVocab.MatchString(stimulus) {
		bs.KnowledgeLevel = KnowledgeLevelExpert
	} else if reNoviceVocab.MatchString(stimulus) && bs.KnowledgeLevel != KnowledgeLevelExpert {
		bs.KnowledgeLevel = KnowledgeLevelNovice
	}

	// Frustration signals — corrections, re-asks, explicit dissatisfaction
	if reFrustration.MatchString(s) {
		bs.FrustrationRisk = clampF32(bs.FrustrationRisk+0.25, 0, 1)
	} else {
		bs.FrustrationRisk = clampF32(bs.FrustrationRisk-0.05, 0, 1) // slow decay on normal turns
	}

	// Goal inference — extract high-level intent from imperative constructs
	if goal := extractGoal(stimulus); goal != "" {
		bs.CurrentGoal = goal
	}

	// Unstated context inference — detect project/work/prod signals
	if reProductContext.MatchString(s) && bs.UnstatedCtx == "" {
		bs.UnstatedCtx = "building/shipping a product"
	}
	if reDebugContext.MatchString(s) {
		bs.UnstatedCtx = "debugging/fixing a live issue"
	}
	if reLearningContext.MatchString(s) {
		bs.UnstatedCtx = "learning/studying this topic"
	}

	// Topic tracking — first 4 significant words of dominant noun phrase
	topic := extractTopic(stimulus)
	if topic != "" {
		bs.SessionTopic = topic
	}
}

// FormatForComposite returns a compact injection string for the system prompt.
func (bs *BeliefState) FormatForComposite() string {
	bs.mu.Lock()
	defer bs.mu.Unlock()

	if bs.TurnCount == 0 {
		return ""
	}

	var sb strings.Builder
	sb.WriteString("### USER BELIEF STATE\n")
	sb.WriteString(fmt.Sprintf("Knowledge level: %s\n", bs.KnowledgeLevel))
	if bs.CurrentGoal != "" {
		sb.WriteString(fmt.Sprintf("Inferred goal: %s\n", bs.CurrentGoal))
	}
	if bs.UnstatedCtx != "" {
		sb.WriteString(fmt.Sprintf("Unstated context: %s\n", bs.UnstatedCtx))
	}
	if bs.SessionTopic != "" {
		sb.WriteString(fmt.Sprintf("Session topic: %s\n", bs.SessionTopic))
	}
	if bs.FrustrationRisk > 0.4 {
		sb.WriteString(fmt.Sprintf("Frustration signal: %.0f%% — be direct, skip preamble, address the core issue first\n",
			bs.FrustrationRisk*100))
	}
	sb.WriteString("### END BELIEF STATE")
	return sb.String()
}

// ─── Signal patterns ─────────────────────────────────────────────────────────

var (
	reExpertVocab = regexp.MustCompile(
		`(?i)(syscall|goroutine|mutex|semaphore|O\(n\)|idempotent|polymorphism|` +
			`eigenvector|backpropagation|gradient descent|heap allocation|` +
			`race condition|deadlock|monadic|monad|functor|lambda calculus|` +
			`cardinality|normalization|sharding|consensus|byzantine)`,
	)
	reNoviceVocab = regexp.MustCompile(
		`(?i)(what does .* mean|how do i (start|begin|install)|` +
			`i('?m| am) new to|beginner|just started|don'?t understand|` +
			`can you explain|what is a|what is an)`,
	)
	reFrustration = regexp.MustCompile(
		`(?i)(that('?s| is) (wrong|not right|incorrect|not what i (meant|asked|wanted))|` +
			`no,?\s+i (meant|said|want)|you (missed|didn'?t|don'?t)|` +
			`again|still not|doesn'?t work|same (issue|problem|error))`,
	)
	reProductContext = regexp.MustCompile(
		`(?i)(our (app|product|service|api|backend|frontend|platform|system)|` +
			`we('?re| are) building|production|deploy|release|ship|users|customers)`,
	)
	reDebugContext = regexp.MustCompile(
		`(?i)(in production|live (issue|bug|error)|users (are|is) (seeing|getting)|` +
			`just (went|broke|crashed)|hotfix|urgent|down|outage)`,
	)
	reLearningContext = regexp.MustCompile(
		`(?i)(i('?m| am) (learning|studying|trying to understand)|` +
			`how does .* work internally|curious (about|why)|` +
			`(reading|working through) .* book|taking .* course)`,
	)
	reGoalVerb = regexp.MustCompile(
		`(?i)^(i (want|need|('?m trying|am trying) to|('?d like|would like) to)|` +
			`help me|i('?m| am) (building|creating|working on|trying to))`,
	)
)

func extractGoal(s string) string {
	loc := reGoalVerb.FindStringIndex(s)
	if loc == nil {
		return ""
	}
	rest := strings.TrimSpace(s[loc[1]:])
	words := strings.Fields(rest)
	if len(words) > 6 {
		words = words[:6]
	}
	if len(words) == 0 {
		return ""
	}
	return strings.Join(words, " ")
}

func extractTopic(s string) string {
	words := strings.Fields(s)
	var sig []string
	stop := map[string]bool{
		"i": true, "a": true, "an": true, "the": true, "is": true,
		"are": true, "was": true, "be": true, "to": true, "of": true,
		"in": true, "it": true, "this": true, "that": true, "do": true,
		"can": true, "my": true, "me": true, "you": true, "we": true,
	}
	for _, w := range words {
		clean := strings.ToLower(strings.Trim(w, ".,!?;:\"'()"))
		if len(clean) > 3 && !stop[clean] {
			sig = append(sig, clean)
			if len(sig) == 4 {
				break
			}
		}
	}
	return strings.Join(sig, " ")
}

func clampF32(v, min, max float32) float32 {
	if v < min {
		return min
	}
	if v > max {
		return max
	}
	return v
}
