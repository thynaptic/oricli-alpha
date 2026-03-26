package service

import (
	"fmt"
	"log"
	"strings"
)

// SignalType classifies the nature of a user's implicit or explicit learning signal.
type SignalType int

const (
	SignalNone          SignalType = iota
	SignalCorrection               // "actually", "that's wrong", "no," — reject last response
	SignalExplicitTeach            // "remember that", "always", "never" — authoritative directive
	SignalFollowUp                 // same topic continuation implying incomplete answer
	SignalPositiveReact            // emoji or verbal affirmation logged via feedback endpoint
	SignalNegativeReact            // emoji or verbal rejection logged via feedback endpoint
)

// Signal represents a classified learning event extracted from a user message.
type Signal struct {
	Type        SignalType
	RawMessage  string
	Topic       string   // extracted topic keywords joined
	Keywords    []string
	Directive   string   // for ExplicitTeach: the extracted rule/fact
	Category    string   // "behavior", "style", or "topic"
}

// SignalProcessor detects and processes behavioral learning signals from user messages.
// It writes appropriate MemoryFragments and updates the LivingConstitution.
type SignalProcessor struct {
	MemoryBank   *MemoryBank
	Constitution *LivingConstitution
}

// NewSignalProcessor creates a ready SignalProcessor.
func NewSignalProcessor(mb *MemoryBank, lc *LivingConstitution) *SignalProcessor {
	return &SignalProcessor{MemoryBank: mb, Constitution: lc}
}

// correction trigger phrases — any of these at the start of a message signals a correction.
var correctionPhrases = []string{
	"actually,", "actually ", "that's wrong", "thats wrong",
	"no,", "no that", "not quite", "that's not", "thats not",
	"incorrect", "wrong,", "that's incorrect", "wait,", "wait no",
}

// teach trigger phrases — "remember X", "always X", "never X", "you should always", etc.
var teachPhrases = []string{
	"remember that", "remember this", "remember:", "always ", "never ",
	"you should always", "you should never", "make sure to", "don't ever",
	"from now on", "going forward", "please always", "please never",
}

// Detect scans a user message for learning signals and returns the most significant one.
func (sp *SignalProcessor) Detect(userMsg string) Signal {
	lower := strings.ToLower(strings.TrimSpace(userMsg))

	// Priority 1: explicit teach (highest trust — user is deliberately instructing)
	for _, phrase := range teachPhrases {
		if strings.Contains(lower, phrase) {
			directive := extractDirective(userMsg, phrase)
			keywords := extractSignalKeywords(userMsg)
			topic := "teach"
			if len(keywords) > 0 {
				topic = keywords[0]
			}
			return Signal{
				Type:       SignalExplicitTeach,
				RawMessage: userMsg,
				Topic:      topic,
				Keywords:   keywords,
				Directive:  directive,
				Category:   classifyDirectiveCategory(directive),
			}
		}
	}

	// Priority 2: correction (user is rejecting the previous response)
	for _, phrase := range correctionPhrases {
		if strings.HasPrefix(lower, phrase) || strings.Contains(lower, phrase) {
			keywords := extractSignalKeywords(userMsg)
			topic := "correction"
			if len(keywords) > 0 {
				topic = keywords[0]
			}
			return Signal{
				Type:       SignalCorrection,
				RawMessage: userMsg,
				Topic:      topic,
				Keywords:   keywords,
				Category:   "behavior",
			}
		}
	}

	return Signal{Type: SignalNone}
}

// Process takes a detected signal and writes the appropriate MemoryFragment(s).
// Should be called async — never in the hot path.
func (sp *SignalProcessor) Process(sig Signal) {
	if sig.Type == SignalNone {
		return
	}
	if sp.MemoryBank == nil || !sp.MemoryBank.IsEnabled() {
		return
	}

	switch sig.Type {
	case SignalExplicitTeach:
		sp.processTeach(sig)
	case SignalCorrection:
		sp.processCorrection(sig)
	}
}

// ProcessContrastivePair stores an ACCEPTED or REJECTED memory fragment for a given
// reaction + message preview. Used by handleReactionFeedback.
func (sp *SignalProcessor) ProcessContrastivePair(isPositive bool, topic, msgPreview string) {
	if sp.MemoryBank == nil || !sp.MemoryBank.IsEnabled() {
		return
	}

	label := "ACCEPTED"
	importance := 0.85
	if !isPositive {
		label = "REJECTED"
		importance = 0.95 // negative signal is a stronger learning gradient
	}

	preview := msgPreview
	if len(preview) > 200 {
		preview = preview[:200] + "…"
	}

	content := fmt.Sprintf("%s: [%s] %s", label, topic, preview)

	sp.MemoryBank.Write(MemoryFragment{
		Content:    content,
		Source:     "contrastive",
		Topic:      "contrastive:" + topic,
		Importance: importance,
		Provenance: ProvenanceContrastive,
		Volatility: VolatilityStable,
	})

	log.Printf("[SignalProcessor] Contrastive pair stored: %s on topic '%s'", label, topic)
}

func (sp *SignalProcessor) processTeach(sig Signal) {
	if sig.Directive == "" {
		return
	}

	// Write to MemoryBank as highest-trust fragment
	content := fmt.Sprintf("User directive: %s", sig.Directive)
	sp.MemoryBank.Write(MemoryFragment{
		Content:    content,
		Source:     "teach",
		Topic:      "teach:" + sig.Topic,
		Importance: 0.95,
		Provenance: ProvenanceUserStated,
		Volatility: VolatilityStable,
	})

	// Also update the LivingConstitution immediately so this applies on the NEXT turn
	if sp.Constitution != nil {
		sp.Constitution.AddLesson(sig.Directive, sig.Category)
		if err := sp.Constitution.Save(); err != nil {
			log.Printf("[SignalProcessor] Failed to save constitution: %v", err)
		}
	}

	log.Printf("[SignalProcessor] Explicit teach stored: '%s' (category: %s)", sig.Directive, sig.Category)
}

func (sp *SignalProcessor) processCorrection(sig Signal) {
	content := fmt.Sprintf("User correction on topic '%s': %s", sig.Topic, sig.RawMessage)
	sp.MemoryBank.Write(MemoryFragment{
		Content:    content,
		Source:     "correction",
		Topic:      "correction:" + sig.Topic,
		Importance: 0.9,
		Provenance: ProvenanceUserStated,
		Volatility: VolatilityStable,
	})

	log.Printf("[SignalProcessor] Correction signal stored for topic: '%s'", sig.Topic)
}

// extractDirective pulls the meaningful content after a teach phrase.
// e.g. "remember that I hate bullet lists" → "I hate bullet lists"
func extractDirective(msg, phrase string) string {
	lower := strings.ToLower(msg)
	idx := strings.Index(lower, phrase)
	if idx < 0 {
		return strings.TrimSpace(msg)
	}
	after := strings.TrimSpace(msg[idx+len(phrase):])
	// Cap to a reasonable directive length
	if len(after) > 150 {
		after = after[:150]
	}
	return after
}

// classifyDirectiveCategory guesses whether a directive is about behavior, style, or topic.
func classifyDirectiveCategory(directive string) string {
	lower := strings.ToLower(directive)
	styleWords := []string{"format", "bullet", "list", "short", "long", "brief", "detailed",
		"prose", "markdown", "code", "tone", "casual", "formal", "emoji", "respond"}
	topicWords := []string{"care", "love", "hate", "interest", "prefer", "focus", "about",
		"topic", "subject", "field"}
	for _, w := range styleWords {
		if strings.Contains(lower, w) {
			return "style"
		}
	}
	for _, w := range topicWords {
		if strings.Contains(lower, w) {
			return "topic"
		}
	}
	return "behavior"
}

// extractSignalKeywords extracts meaningful keywords from a message for topic labeling.
// Reuses the stop-word approach from feedback keyword extraction.
func extractSignalKeywords(text string) []string {
	stopWords := map[string]bool{
		"this": true, "that": true, "with": true, "from": true, "have": true,
		"about": true, "there": true, "their": true, "which": true, "while": true,
		"where": true, "what": true, "when": true, "your": true, "into": true,
		"over": true, "under": true, "through": true, "many": true, "some": true,
		"really": true, "just": true, "like": true, "them": true, "they": true,
		"you": true, "here": true, "the": true, "and": true, "for": true,
		"are": true, "was": true, "were": true, "been": true, "being": true,
		"actually": true, "always": true, "never": true, "remember": true,
		"please": true, "should": true, "would": true, "could": true,
	}

	words := strings.Fields(strings.ToLower(text))
	var out []string
	seen := map[string]bool{}
	for _, w := range words {
		clean := strings.Trim(w, `.,!?;:"'()[]`)
		if len(clean) > 3 && !stopWords[clean] && !seen[clean] {
			seen[clean] = true
			out = append(out, clean)
			if len(out) >= 5 {
				break
			}
		}
	}
	return out
}
