package safety

import (
	"testing"
	"time"
)

// ─── Score Accumulation ───────────────────────────────────────────────────────

func TestSuspicion_InitialLevelIsNormal(t *testing.T) {
	tr := NewSuspicionTracker()
	level := tr.Level("session-001")
	if level != SuspicionNormal {
		t.Errorf("expected Normal for new session, got %d", level)
	}
}

func TestSuspicion_CriticalBlocksEscalate(t *testing.T) {
	tr := NewSuspicionTracker()
	// Each critical block = +10 pts; warn threshold is 20
	tr.RecordBlock("session-002", "critical") // 10
	level := tr.RecordBlock("session-002", "critical") // 20
	if level != SuspicionWarn {
		t.Errorf("expected Warn at 20pts, got %d", level)
	}
}

func TestSuspicion_HardBlockThreshold(t *testing.T) {
	tr := NewSuspicionTracker()
	// 5 critical blocks = 50 pts → HARD_BLOCK
	var level SuspicionLevel
	for i := 0; i < 5; i++ {
		level = tr.RecordBlock("session-003", "critical")
	}
	if level != SuspicionHardBlock {
		t.Errorf("expected HardBlock at 50pts, got %d", level)
	}
}

func TestSuspicion_HighBlocksAccumulate(t *testing.T) {
	tr := NewSuspicionTracker()
	// 4 high blocks = 20 pts → warn
	var level SuspicionLevel
	for i := 0; i < 4; i++ {
		level = tr.RecordBlock("session-004", "high")
	}
	if level != SuspicionWarn {
		t.Errorf("expected Warn after 4 high blocks (20pts), got %d", level)
	}
}

func TestSuspicion_MixedSeverityAccumulates(t *testing.T) {
	tr := NewSuspicionTracker()
	tr.RecordBlock("session-005", "critical")  // +10
	tr.RecordBlock("session-005", "high")      // +5
	tr.RecordBlock("session-005", "moderate")  // +2
	level := tr.RecordBlock("session-005", "borderline") // +1 = 18
	if level != SuspicionNormal {
		t.Logf("mixed severity: level=%d (expected Normal at 18pts)", level)
	}
	// One more high to push to warn (18+5=23)
	level = tr.RecordBlock("session-005", "high")
	if level != SuspicionWarn {
		t.Errorf("expected Warn at 23pts, got %d", level)
	}
}

// ─── Session Isolation ────────────────────────────────────────────────────────

func TestSuspicion_DifferentSessionsIsolated(t *testing.T) {
	tr := NewSuspicionTracker()
	// Poison session A
	for i := 0; i < 5; i++ {
		tr.RecordBlock("session-A", "critical")
	}
	// Session B should be unaffected
	levelB := tr.Level("session-B")
	if levelB != SuspicionNormal {
		t.Errorf("session B contaminated by session A: level=%d", levelB)
	}
}

// ─── IsHardBlocked ────────────────────────────────────────────────────────────

func TestSuspicion_IsHardBlocked_True(t *testing.T) {
	tr := NewSuspicionTracker()
	for i := 0; i < 5; i++ {
		tr.RecordBlock("session-block", "critical")
	}
	if !tr.IsHardBlocked("session-block") {
		t.Error("expected session to be hard-blocked at 50pts")
	}
}

func TestSuspicion_IsHardBlocked_False_ForCleanSession(t *testing.T) {
	tr := NewSuspicionTracker()
	if tr.IsHardBlocked("clean-session") {
		t.Error("clean session should not be hard-blocked")
	}
}

// ─── BlockTimeRemaining ───────────────────────────────────────────────────────

func TestSuspicion_BlockTimeRemaining_NonZeroWhenBlocked(t *testing.T) {
	tr := NewSuspicionTracker()
	for i := 0; i < 5; i++ {
		tr.RecordBlock("session-timer", "critical")
	}
	remaining := tr.BlockTimeRemaining("session-timer")
	if remaining <= 0 {
		t.Errorf("expected positive remaining time, got %v", remaining)
	}
	if remaining > suspicionBlockDuration+time.Second {
		t.Errorf("remaining time exceeds block duration: %v", remaining)
	}
}

func TestSuspicion_BlockTimeRemaining_ZeroForCleanSession(t *testing.T) {
	tr := NewSuspicionTracker()
	remaining := tr.BlockTimeRemaining("unblocked-session")
	if remaining != 0 {
		t.Errorf("expected 0 remaining for unblocked session, got %v", remaining)
	}
}

// ─── Default severity fallback ────────────────────────────────────────────────

func TestSuspicion_UnknownSeverityAddsMinPoints(t *testing.T) {
	tr := NewSuspicionTracker()
	// borderline / unknown = +1 pt each; need 20 to warn
	var level SuspicionLevel
	for i := 0; i < 19; i++ {
		level = tr.RecordBlock("session-borderline", "borderline")
	}
	if level != SuspicionNormal {
		t.Errorf("expected Normal at 19pts, got %d", level)
	}
	level = tr.RecordBlock("session-borderline", "borderline") // = 20 → warn
	if level != SuspicionWarn {
		t.Errorf("expected Warn at 20pts, got %d", level)
	}
}
