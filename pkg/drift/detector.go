// Package drift implements the Drift Detection system —
// ported from Aurora's DriftMonitor.swift / DriftEvent.swift.
//
// Compares Ori's current ERI against her 7-day temporal baseline and
// emits DriftEvents when she's deviating meaningfully from her own norm.
// 30-minute cooldown prevents nudge spam.
package drift

import (
	"sync"
	"time"

	"github.com/thynaptic/oricli-go/pkg/temporal"
)

// DriftType classifies what dimension is drifting.
type DriftType string

const (
	DriftCoherence DriftType = "coherence" // Success/error ratio off baseline
	DriftPacing    DriftType = "pacing"    // Throughput stability degraded
	DriftEnergy    DriftType = "energy"    // Overall ERI trending below baseline
)

// Event is a single detected drift occurrence (mirrors DriftEvent.swift).
type Event struct {
	Type          DriftType
	Severity      float32   // 0.0-1.0
	Expected      float32   // Baseline value
	Actual        float32   // Current value
	Deviation     float32   // |actual - expected|
	Confidence    float32   // How reliable this detection is
	DetectedAt    time.Time
	WasActedOn    bool
	ActionTaken   string
}

const (
	driftThreshold = 0.15  // ERI delta that constitutes meaningful drift
	cooldown       = 30 * time.Minute
)

// Detector watches ERI updates and emits drift events when warranted.
type Detector struct {
	mu          sync.Mutex
	lastEvent   time.Time
	lastDrift   *Event
	active      bool     // currently drifting?
	severity    float32

	// Channel-based pub — consumers subscribe for real-time events
	events chan Event
}

// NewDetector returns a ready Detector. Buffer 16 events to avoid blocking callers.
func NewDetector() *Detector {
	return &Detector{
		events: make(chan Event, 16),
	}
}

// Events returns a read-only channel of drift events.
func (d *Detector) Events() <-chan Event {
	return d.events
}

// Evaluate is called on every ERI update. Compares current ERI to the
// temporal baseline and emits an event when drift exceeds threshold.
//
// currentERI:  the freshly computed ERI value
// coherence:   node 1 value (success ratio)
// pacing:      node 2 value (throughput stability)
// baseline:    result of temporal.Memory.Compute()
func (d *Detector) Evaluate(currentERI, coherence, pacing float32, baseline temporal.Baseline) {
	d.mu.Lock()
	defer d.mu.Unlock()

	// Need enough history to have a reliable baseline
	if baseline.Confidence < 0.2 {
		d.active = false
		return
	}

	// Cooldown — don't emit more than once per 30 minutes
	if time.Since(d.lastEvent) < cooldown {
		return
	}

	ref := baseline.SevenDay
	delta := currentERI - ref
	absDelta := delta
	if absDelta < 0 {
		absDelta = -absDelta
	}

	if absDelta < driftThreshold {
		d.active = false
		d.severity = 0
		return
	}

	// Classify which dimension is the primary driver
	driftType := classifyDrift(currentERI, coherence, pacing, baseline)

	severity := absDelta / (1.0 - driftThreshold) // normalize to [0,1] above threshold
	if severity > 1.0 {
		severity = 1.0
	}

	evt := Event{
		Type:       driftType,
		Severity:   severity,
		Expected:   ref,
		Actual:     currentERI,
		Deviation:  absDelta,
		Confidence: baseline.Confidence,
		DetectedAt: time.Now(),
	}

	d.active = true
	d.severity = severity
	d.lastEvent = time.Now()
	d.lastDrift = &evt

	// Non-blocking send — drop if nobody is consuming
	select {
	case d.events <- evt:
	default:
	}
}

// State returns the current drift status without blocking.
func (d *Detector) State() (active bool, severity float32, lastEvt *Event) {
	d.mu.Lock()
	defer d.mu.Unlock()
	return d.active, d.severity, d.lastDrift
}

// classifyDrift picks the most degraded ERI node as the drift type.
func classifyDrift(eri, coherence, pacing float32, baseline temporal.Baseline) DriftType {
	// Energy drift: overall ERI is below baseline (broad degradation)
	if eri < baseline.SevenDay-driftThreshold {
		// Dig into which node drove it most
		if coherence < 0.5 {
			return DriftCoherence
		}
		if pacing < 0.4 {
			return DriftPacing
		}
		return DriftEnergy
	}
	// ERI above baseline but volatile — pacing anomaly
	if baseline.Volatility > 0.6 {
		return DriftPacing
	}
	return DriftEnergy
}
