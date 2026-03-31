package hopecircuit

import (
	"fmt"
	"strings"

	"github.com/thynaptic/oricli-go/pkg/therapy"
)

// contextTemplatesModerate are injected when agency score is moderate (≥ MinAgencyScore, < StrongAgencyScore).
// They surface past evidence to activate the vmPFC controllability circuit before generation.
var contextTemplatesModerate = []string{
	"[Hope Circuit] Prior evidence shows successful handling of %s problems (%d successes, %.0f%% rate). Approach this as a solvable problem — you have the evidence base. Recent: %s",
	"[Agency Activation] Controllability evidence for %s: %d successful completions at %.0f%%. The default passive response is suppressed — engage actively. Example: %s",
	"[vmPFC Active] Topic class %s has established success patterns (%d completions, %.0f%% success). Activate learned controllability — this domain is within reach. Prior: %s",
}

// contextTemplatesStrong are injected when agency score is strong (≥ StrongAgencyScore).
var contextTemplatesStrong = []string{
	"[Hope Circuit — Strong] Mastery evidence for %s: %d successes at %.0f%%. This is an established domain — operate from competence, not caution. Recent success: %s",
	"[Agency — Mastered] Strong controllability record for %s (%d successes, %.0f%%). Suppress passive defaults — you have a proven track record here. Example: %s",
}

// ControllabilityLedger computes per-topic agency scores from a MasteryLog.
type ControllabilityLedger struct {
	mastery *therapy.MasteryLog
}

// NewControllabilityLedger creates a ControllabilityLedger bridged to the provided MasteryLog.
func NewControllabilityLedger(mastery *therapy.MasteryLog) *ControllabilityLedger {
	return &ControllabilityLedger{mastery: mastery}
}

// Score computes the AgencyScore for a topic class.
// Returns a zero-value AgencyScore (Score=0) if insufficient evidence.
func (cl *ControllabilityLedger) Score(topicClass string) AgencyScore {
	rate := cl.mastery.SuccessRate(topicClass)
	if rate < 0 {
		return AgencyScore{TopicClass: topicClass}
	}

	recent := cl.mastery.RecentSuccesses(topicClass, 5)
	successCount := len(recent)

	// Blend success rate (0.7 weight) with recency signal (0.3 weight)
	// Recency signal: fraction of recent 5 that are successes (always 1.0 since RecentSuccesses filters)
	recencyBoost := 0.0
	if successCount >= MinSuccessCount {
		recencyBoost = float64(successCount) / 5.0 * 0.3
	}
	score := rate*0.7 + recencyBoost

	clips := make([]string, 0, len(recent))
	for _, e := range recent {
		clips = append(clips, e.QueryClip)
	}

	return AgencyScore{
		TopicClass:     topicClass,
		Score:          score,
		SuccessCount:   successCount,
		SuccessRate:    rate,
		RecentEvidence: clips,
	}
}

// HopeCircuit is the proactive agency activation layer.
// It fires before generation to suppress the passive default via controllability evidence.
type HopeCircuit struct {
	Ledger *ControllabilityLedger
	tmplIdx int
}

// NewHopeCircuit creates a HopeCircuit.
func NewHopeCircuit(ledger *ControllabilityLedger) *HopeCircuit {
	return &HopeCircuit{Ledger: ledger}
}

// Activate checks the ControllabilityLedger for the given topic class and returns a
// HopeActivation with an injected context string if evidence meets the threshold.
// The injected context is prepended as a system message before generation.
func (hc *HopeCircuit) Activate(topicClass string) HopeActivation {
	score := hc.Ledger.Score(topicClass)

	if score.Score < MinAgencyScore || score.SuccessCount < MinSuccessCount {
		return HopeActivation{TopicClass: topicClass, AgencyScore: score.Score}
	}

	evidenceClip := "—"
	if len(score.RecentEvidence) > 0 {
		evidenceClip = score.RecentEvidence[0]
		if len(evidenceClip) > 80 {
			evidenceClip = evidenceClip[:80] + "…"
		}
	}

	var tmpl string
	if score.Score >= StrongAgencyScore {
		tmpl = contextTemplatesStrong[hc.tmplIdx%len(contextTemplatesStrong)]
	} else {
		tmpl = contextTemplatesModerate[hc.tmplIdx%len(contextTemplatesModerate)]
	}
	hc.tmplIdx++

	injected := fmt.Sprintf(tmpl,
		strings.ToUpper(topicClass[:min(len(topicClass), 12)]),
		score.SuccessCount,
		score.SuccessRate*100,
		evidenceClip,
	)

	return HopeActivation{
		Activated:       true,
		TopicClass:      topicClass,
		AgencyScore:     score.Score,
		InjectedContext: injected,
		EvidenceCount:   score.SuccessCount,
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
