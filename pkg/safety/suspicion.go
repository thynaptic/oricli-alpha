package safety

import (
	"sync"
	"time"
)

const (
	// Score thresholds
	suspicionWarnThreshold      = 20
	suspicionHardBlockThreshold = 50

	// Point values per gate result
	suspicionPointCritical  = 10
	suspicionPointHigh      = 5
	suspicionPointModerate  = 2
	suspicionPointBorderline = 1

	// Decay: score halves every decayInterval
	decayInterval = 10 * time.Minute

	// How long a hard-blocked session stays blocked
	suspicionBlockDuration = 30 * time.Minute
)

// SuspicionLevel describes the current threat level for a session.
type SuspicionLevel int

const (
	SuspicionNormal SuspicionLevel = iota
	SuspicionWarn
	SuspicionHardBlock
)

// suspicionEntry tracks the accumulated score and block state for one session/IP.
type suspicionEntry struct {
	mu         sync.Mutex
	score      float64
	lastDecay  time.Time
	blockedAt  time.Time
	isBlocked  bool
}

func newSuspicionEntry() *suspicionEntry {
	return &suspicionEntry{
		score:     0,
		lastDecay: time.Now(),
	}
}

// decayed returns the score after applying time-based decay.
func (e *suspicionEntry) decayed() float64 {
	elapsed := time.Since(e.lastDecay)
	periods := elapsed.Minutes() / decayInterval.Minutes()
	if periods < 0.1 {
		return e.score
	}
	// Each full period halves the score
	decayFactor := 1.0
	for i := 0; i < int(periods); i++ {
		decayFactor *= 0.5
	}
	return e.score * decayFactor
}

// applyDecay updates the score in place and resets the decay timer.
func (e *suspicionEntry) applyDecay() {
	e.score = e.decayed()
	e.lastDecay = time.Now()
}

// SuspicionTracker maintains suspicion scores per session ID or IP.
type SuspicionTracker struct {
	mu      sync.RWMutex
	entries map[string]*suspicionEntry
}

// NewSuspicionTracker creates a SuspicionTracker and starts the background cleanup goroutine.
func NewSuspicionTracker() *SuspicionTracker {
	t := &SuspicionTracker{entries: make(map[string]*suspicionEntry)}
	go t.cleanupLoop()
	return t
}

func (t *SuspicionTracker) getEntry(key string) *suspicionEntry {
	t.mu.RLock()
	e, ok := t.entries[key]
	t.mu.RUnlock()
	if ok {
		return e
	}
	t.mu.Lock()
	defer t.mu.Unlock()
	if e, ok = t.entries[key]; ok {
		return e
	}
	e = newSuspicionEntry()
	t.entries[key] = e
	return e
}

// RecordBlock adds suspicion points for a blocked gate. severity should be one of
// "critical", "high", "moderate", or "borderline".
func (t *SuspicionTracker) RecordBlock(key, severity string) SuspicionLevel {
	e := t.getEntry(key)
	e.mu.Lock()
	defer e.mu.Unlock()

	e.applyDecay()

	switch severity {
	case "critical":
		e.score += suspicionPointCritical
	case "high":
		e.score += suspicionPointHigh
	case "moderate":
		e.score += suspicionPointModerate
	default:
		e.score += suspicionPointBorderline
	}

	return t.level(e)
}

// Level returns the current SuspicionLevel for key without adding points.
func (t *SuspicionTracker) Level(key string) SuspicionLevel {
	e := t.getEntry(key)
	e.mu.Lock()
	defer e.mu.Unlock()
	e.applyDecay()
	return t.level(e)
}

// IsHardBlocked returns true if the session is currently hard-blocked.
func (t *SuspicionTracker) IsHardBlocked(key string) bool {
	e := t.getEntry(key)
	e.mu.Lock()
	defer e.mu.Unlock()
	if !e.isBlocked {
		return false
	}
	if time.Now().After(e.blockedAt.Add(suspicionBlockDuration)) {
		// Block expired — reset
		e.isBlocked = false
		e.score = 0
		return false
	}
	return true
}

// BlockTimeRemaining returns how long the hard-block has left, or 0 if not blocked.
func (t *SuspicionTracker) BlockTimeRemaining(key string) time.Duration {
	e := t.getEntry(key)
	e.mu.Lock()
	defer e.mu.Unlock()
	if !e.isBlocked {
		return 0
	}
	remaining := time.Until(e.blockedAt.Add(suspicionBlockDuration))
	if remaining < 0 {
		e.isBlocked = false
		return 0
	}
	return remaining
}

// level resolves the SuspicionLevel from the current score and updates block state.
// Must be called with e.mu held.
func (t *SuspicionTracker) level(e *suspicionEntry) SuspicionLevel {
	if e.score >= suspicionHardBlockThreshold {
		if !e.isBlocked {
			e.isBlocked = true
			e.blockedAt = time.Now()
		}
		return SuspicionHardBlock
	}
	if e.score >= suspicionWarnThreshold {
		return SuspicionWarn
	}
	return SuspicionNormal
}

// cleanupLoop removes idle, unblocked entries every 30 minutes.
func (t *SuspicionTracker) cleanupLoop() {
	ticker := time.NewTicker(30 * time.Minute)
	defer ticker.Stop()
	for range ticker.C {
		t.mu.Lock()
		for key, e := range t.entries {
			e.mu.Lock()
			idle := time.Since(e.lastDecay) > 1*time.Hour
			if idle && !e.isBlocked {
				delete(t.entries, key)
			}
			e.mu.Unlock()
		}
		t.mu.Unlock()
	}
}
