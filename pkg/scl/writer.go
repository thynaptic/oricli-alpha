package scl

import "context"

// ---------------------------------------------------------------------------
// SCLWriter adapter — satisfies service.SCLWriter without an import cycle.
// service.JITDaemon holds a service.SCLWriter interface; this is the concrete
// implementation that wraps a *Ledger.
// ---------------------------------------------------------------------------

// LedgerWriter wraps *Ledger and implements service.SCLWriter.
type LedgerWriter struct {
	l *Ledger
}

// NewLedgerWriter returns a LedgerWriter that can be injected as service.SCLWriter.
func NewLedgerWriter(l *Ledger) *LedgerWriter {
	return &LedgerWriter{l: l}
}

// WriteLesson writes a skill lesson from the JIT JSONL buffer to the SCL
// under TierSkills with ProvenanceSynthetic.
func (w *LedgerWriter) WriteLesson(ctx context.Context, topic, content string, confidence float64) error {
	if w.l == nil || !w.l.IsEnabled() {
		return nil
	}
	_, err := w.l.Write(ctx, SCLRecord{
		Tier:       TierSkills,
		Content:    content,
		Subject:    topic,
		Provenance: ProvenanceSynthetic,
		Confidence: confidence,
		Author:     "jit_daemon",
		Tags:       []string{"jit_lesson", topic},
	})
	return err
}

// WriteFact writes a CuriosityDaemon research finding to the SCL
// under TierFacts with ProvenanceSynthetic or ProvenanceWebVerified.
func (w *LedgerWriter) WriteFact(ctx context.Context, topic, content string, confidence float64, webVerified bool) error {
	if w.l == nil || !w.l.IsEnabled() {
		return nil
	}
	prov := ProvenanceSynthetic
	if webVerified {
		prov = ProvenanceWebVerified
	}
	_, err := w.l.Write(ctx, SCLRecord{
		Tier:       TierFacts,
		Content:    content,
		Subject:    topic,
		Provenance: prov,
		Confidence: confidence,
		Author:     "curiosity_daemon",
		Tags:       []string{"curiosity", topic},
	})
	return err
}

// WriteCorrection writes a LearningSystem correction to TierCorrections.
func (w *LedgerWriter) WriteCorrection(ctx context.Context, original, corrected, skill string) error {
	if w.l == nil || !w.l.IsEnabled() {
		return nil
	}
	content := "When asked: " + original + "\nPrefer: " + corrected
	_, err := w.l.Write(ctx, SCLRecord{
		Tier:       TierCorrections,
		Content:    content,
		Subject:    skill,
		Provenance: ProvenanceUserStated,
		Confidence: 0.92,
		Author:     "learning_system",
		Tags:       []string{"correction", skill},
	})
	return err
}
