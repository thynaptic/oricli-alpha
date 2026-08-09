package memory

import (
	"fmt"
	"regexp"
	"strings"
	"sync"
	"time"
)

type KnowledgeLevel string

const (
	KnowledgeNovice       KnowledgeLevel = "novice"
	KnowledgeIntermediate KnowledgeLevel = "intermediate"
	KnowledgeExpert       KnowledgeLevel = "expert"
)

// BeliefState is the per-session fog-of-war model (CPU-only, no I/O).
type BeliefState struct {
	SessionID       string
	CurrentGoal     string
	KnowledgeLevel  KnowledgeLevel
	UnstatedCtx     string
	FrustrationRisk float32
	SessionTopic    string
	TurnCount       int
	LastUpdate      time.Time
	mu              sync.Mutex
}

type BeliefTracker struct {
	sessions sync.Map
}

func NewBeliefTracker() *BeliefTracker { return &BeliefTracker{} }

func (t *BeliefTracker) Get(sessionID string) *BeliefState {
	if sessionID == "" {
		sessionID = "_anon"
	}
	if v, ok := t.sessions.Load(sessionID); ok {
		return v.(*BeliefState)
	}
	bs := &BeliefState{
		SessionID:      sessionID,
		KnowledgeLevel: KnowledgeIntermediate,
		LastUpdate:     time.Now(),
	}
	t.sessions.Store(sessionID, bs)
	return bs
}

func (bs *BeliefState) Update(stimulus string) {
	bs.mu.Lock()
	defer bs.mu.Unlock()
	bs.TurnCount++
	bs.LastUpdate = time.Now()
	s := strings.ToLower(strings.TrimSpace(stimulus))

	if reExpertVocab.MatchString(stimulus) {
		bs.KnowledgeLevel = KnowledgeExpert
	} else if reNoviceVocab.MatchString(stimulus) && bs.KnowledgeLevel != KnowledgeExpert {
		bs.KnowledgeLevel = KnowledgeNovice
	}
	if reFrustration.MatchString(s) {
		bs.FrustrationRisk = clampF32(bs.FrustrationRisk+0.25, 0, 1)
	} else {
		bs.FrustrationRisk = clampF32(bs.FrustrationRisk-0.05, 0, 1)
	}
	if goal := extractGoal(stimulus); goal != "" {
		bs.CurrentGoal = goal
	}
	if reProductContext.MatchString(s) && bs.UnstatedCtx == "" {
		bs.UnstatedCtx = "building/shipping a product"
	}
	if reDebugContext.MatchString(s) {
		bs.UnstatedCtx = "debugging/fixing a live issue"
	}
	if reLearningContext.MatchString(s) {
		bs.UnstatedCtx = "learning/studying this topic"
	}
	if topic := extractTopic(stimulus); topic != "" {
		bs.SessionTopic = topic
	}
}

func (bs *BeliefState) FormatForPrompt() string {
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
		sb.WriteString(fmt.Sprintf("Frustration signal: %.0f%% — be direct, skip preamble\n", bs.FrustrationRisk*100))
	}
	sb.WriteString("### END BELIEF STATE")
	return sb.String()
}

var (
	reExpertVocab = regexp.MustCompile(
		`(?i)(syscall|goroutine|mutex|semaphore|O\(n\)|idempotent|polymorphism|` +
			`eigenvector|backpropagation|gradient descent|heap allocation|` +
			`race condition|deadlock|sharding|consensus|byzantine)`,
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
		`(?i)(in production|live (issue|bug|error)|hotfix|urgent|down|outage)`,
	)
	reLearningContext = regexp.MustCompile(
		`(?i)(i('?m| am) (learning|studying|trying to understand)|curious (about|why))`,
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
		"are": true, "to": true, "of": true, "in": true, "it": true,
		"this": true, "that": true, "do": true, "can": true, "my": true,
		"me": true, "you": true, "we": true,
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
