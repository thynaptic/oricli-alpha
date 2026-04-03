package cognition

import (
	"math"
	"time"

	"github.com/thynaptic/oricli-go/pkg/aeci"
	"github.com/thynaptic/oricli-go/pkg/arte"
	"github.com/thynaptic/oricli-go/pkg/drift"
	"github.com/thynaptic/oricli-go/pkg/temporal"
	"github.com/thynaptic/oricli-go/pkg/tonetrack"
)

// --- Pillar 6: Resonance Layer ---
// Unifies the original Aurora Symphony (ERS) and Ecospheric Layer (ERI)
// into a Go-native homeostatic monitor for the Swarm Bus.
//
// ERI is computed from 4 subsystem nodes (ported from AuroraEcosphericLayer.swift):
//   Node 1 — ToneKit:    toneCoherence from ToneTracker accuracy feedback
//   Node 2 — Temporal:  pacing stability (throughput consistency)
//   Node 3 — Volatility: latency/duration variance (inversed)
//   Node 4 — ARTE:       Ori's cognitive/emotional state contribution

type ResonanceState struct {
	ERI        float32 // Ecospheric Resonance Index (-1.0 to 1.0)
	ERS        float32 // Emotional Resonance Score (-1.0 to 1.0)
	Pacing     float32 // Stability of message throughput
	Volatility float32 // Variance in latency across nodes
	Coherence  float32 // Ratio of SUCCESS to ERROR/REJECT messages (infra)
	ToneCoherence float32 // Tone prediction accuracy (self-improvement loop)
	ARTEScore  float32 // ARTE subsystem contribution (-1.0 to 1.0)
	Arousal    float32 // Combined arousal level (0.0-1.0) for surface tint

	// ARTE state snapshot (current cycle)
	ARTEState     arte.ARTEState
	ARTEIntensity float32
	ARTEStability float32

	// Temporal emotional baseline
	TemporalBaseline float32 // 7-day weighted ERI baseline
	ThirtyDayBase    float32 // 30-day historical baseline
	TemporalMomentum temporal.Trend
	Volatility7Day   float32

	// Drift detection
	DriftActive   bool
	DriftSeverity float32
	DriftType     drift.DriftType

	// Musical Mapping (Ported from Swift Aurora)
	MusicalKey string
	BPM        float32
}

type ResonanceService struct {
	Current    ResonanceState
	LastUpdate time.Time
	ARTE       *arte.Detector
	Temporal   *temporal.Memory
	Drift      *drift.Detector
	ToneTrack  *tonetrack.Tracker
	AECI       *aeci.Engine
}

func NewResonanceService() *ResonanceService {
	return &ResonanceService{
		Current: ResonanceState{
			ERI:           0.5,
			ERS:           0.5,
			ARTEScore:     0.0,
			Arousal:       0.5,
			ToneCoherence: 0.7,
			ARTEState:     arte.StateCalm,
			MusicalKey:    "C Major",
			BPM:           120.0,
		},
		LastUpdate: time.Now(),
		ARTE:       arte.NewDetector(),
		Temporal:   temporal.NewMemory(),
		Drift:      drift.NewDetector(),
		ToneTrack:  tonetrack.NewTracker(),
		AECI:       aeci.NewEngine(),
	}
}

// UpdateIndices calculates the new ERI based on Swarm Bus telemetry.
func (r *ResonanceService) UpdateIndices(latencyVar float64, throughput float64, errorRate float64) {
	// 1. Pacing Stability (Throughput consistency)
	// High throughput = High Pacing (capped at 1.0)
	r.Current.Pacing = float32(math.Min(1.0, throughput/100.0))

	// 2. Volatility Sync (Latency variance)
	// High variance = High Volatility = Low Sync
	r.Current.Volatility = float32(math.Min(1.0, latencyVar/50.0))
	
	// 3. Coherence (Success vs Error)
	r.Current.Coherence = 1.0 - float32(errorRate)

	// ERI = weighted average (Ported from Swift EcosphericLayer)
	// (Coherence * 0.4) + (Volatility_Inversed * 0.3) + (Pacing * 0.3)
	r.Current.ERI = (r.Current.Coherence * 0.4) + ((1.0 - r.Current.Volatility) * 0.3) + (r.Current.Pacing * 0.3)
	
	// ERS = Blend of ERI and internal affective state (Simplified)
	r.Current.ERS = r.Current.ERI // For now, sync with ERI

	// 4. Musical Mapping (Ported from Swift MavaiaMetaSymphony)
	r.mapMusicalState()
	
	r.LastUpdate = time.Now()
}

func (r *ResonanceService) mapMusicalState() {
	ers := r.Current.ERS
	
	// Mapping ERS to Musical Key (Simplified Aurora Logic)
	if ers > 0.6 {
		r.Current.MusicalKey = "E Major" // Radiant, high energy
		r.Current.BPM = 140.0 + (ers * 20.0)
	} else if ers > 0.2 {
		r.Current.MusicalKey = "C Major" // Balanced, stable
		r.Current.BPM = 120.0
	} else if ers > -0.2 {
		r.Current.MusicalKey = "G Minor" // Reflective, analytical
		r.Current.BPM = 100.0
	} else if ers > -0.6 {
		r.Current.MusicalKey = "D Minor" // Discordant, correcting
		r.Current.BPM = 80.0
	} else {
		r.Current.MusicalKey = "B Locrian" // Absolute chaos/panic
		r.Current.BPM = 60.0
	}
}

// UpdateFromInference updates ERI after a sovereign pipeline run, incorporating
// ARTE as the 4th subsystem node (ported from AuroraEcosphericLayer.swift).
//
// 4-node ERI formula:
//   Node 1 (Coherence/ToneKit × 0.35):  success/error ratio EMA
//   Node 2 (Pacing/Temporal × 0.25):    throughput stability
//   Node 3 (Volatility × 0.25):         duration variance (inversed)
//   Node 4 (ARTE × 0.15):               Ori's cognitive/emotional state
//
// This matches the Aurora formula:
//   ERI = toneCoherence×0.4 + volatilitySync×0.3 + pacingStability×0.3
// but redistributes 5% weight to ARTE for richer affective signal.
func (r *ResonanceService) UpdateFromInference(duration time.Duration, success bool) {
	secs := duration.Seconds()

	// ── Node 1: Coherence (ToneKit analog) ───────────────────────────────────
	prevCoherence := float64(r.Current.Coherence)
	if prevCoherence == 0 {
		prevCoherence = 1.0 // cold-start: assume healthy
	}
	if success {
		prevCoherence = prevCoherence*0.8 + 1.0*0.2
	} else {
		prevCoherence = prevCoherence * 0.5
	}
	r.Current.Coherence = float32(prevCoherence)

	// ── Node 2: Pacing — 1.0 at ≤3s, 0.0 at ≥45s ─────────────────────────
	r.Current.Pacing = float32(1.0 - math.Min(1.0, math.Max(0.0, (secs-3.0)/42.0)))

	// ── Node 3: Volatility — 0.0 at ≤5s, 1.0 at ≥35s ─────────────────────
	r.Current.Volatility = float32(math.Min(1.0, math.Max(0.0, (secs-5.0)/30.0)))

	// ── Node 4: ARTE — feed sample and read current state ─────────────────
	var tokenEst int
	if success {
		tokenEst = int(secs * 15) // rough: ~15 tok/s for local models
	}
	complexity := float32(math.Min(1.0, secs/20.0)) // longer → assumed more complex
	r.ARTE.UpdateFromInference(arte.InferenceSample{
		Duration:   duration,
		Success:    success,
		TokenCount: tokenEst,
		Complexity: complexity,
	})
	arteReading := r.ARTE.Read()
	r.Current.ARTEScore     = arteReading.Score
	r.Current.ARTEState     = arteReading.State
	r.Current.ARTEIntensity = arteReading.Intensity
	r.Current.ARTEStability = arteReading.Stability

	// Arousal: blend of pacing and ARTE intensity (maps to surface warmth in UI)
	// High pacing + energized state → high arousal; fatigued → low arousal
	arteArousal := float32(0.5)
	switch arteReading.State {
	case arte.StateEnergized:
		arteArousal = 0.75 + arteReading.Intensity*0.25
	case arte.StateFocused:
		arteArousal = 0.6
	case arte.StateReflective:
		arteArousal = 0.45
	case arte.StateFatigued:
		arteArousal = 0.25
	}
	r.Current.Arousal = r.Current.Pacing*0.4 + arteArousal*0.6

	// ── Node 1: ToneCoherence (replaces raw infra coherence as primary driver)
	// Blend: 70% tone prediction accuracy + 30% infra coherence (success/error)
	r.Current.ToneCoherence = r.ToneTrack.ToneCoherence()*0.7 + r.Current.Coherence*0.3

	// ── 4-node ERI (Node 1 now uses ToneCoherence — closes self-improvement loop) ──
	// Map ARTE score (-1 to 1) → [0, 1] contribution
	arteContrib := float32((float64(r.Current.ARTEScore) + 1.0) / 2.0)
	r.Current.ERI = (r.Current.ToneCoherence * 0.35) +
		((1.0 - r.Current.Volatility) * 0.25) +
		(r.Current.Pacing * 0.25) +
		(arteContrib * 0.15)
	r.Current.ERS = r.Current.ERI

	// ── Temporal Memory — record snapshot, compute baselines ─────────────
	r.Temporal.Record(r.Current.ERI, r.Current.ARTEScore)
	baseline := r.Temporal.Compute()
	r.Current.TemporalBaseline = baseline.SevenDay
	r.Current.ThirtyDayBase    = baseline.ThirtyDay
	r.Current.TemporalMomentum = baseline.Momentum
	r.Current.Volatility7Day   = baseline.Volatility

	// ── Drift Detection — compare current ERI to 7-day baseline ──────────
	r.Drift.Evaluate(r.Current.ERI, r.Current.ToneCoherence, r.Current.Pacing, baseline)
	driftActive, driftSev, driftEvt := r.Drift.State()
	r.Current.DriftActive   = driftActive
	r.Current.DriftSeverity = driftSev
	if driftEvt != nil {
		r.Current.DriftType = driftEvt.Type
	}

	r.mapMusicalState()

	// ── AECI — Aurora Emotional Climate Index (weekly emotional climate) ──
	r.AECI.Update(r.Current.ToneCoherence, baseline.Momentum, baseline.Volatility)

	r.LastUpdate = time.Now()
}


func (r *ResonanceService) GetStateDescription() string {
	if r.Current.ERI > 0.7 {
		return "Symphonic: Swarm is in perfect harmony."
	} else if r.Current.ERI > 0.3 {
		return "Stable: Swarm is performing efficiently."
	} else if r.Current.ERI > -0.3 {
		return "Dissonant: Detecting slight latency drift."
	}
	return "Cacophonic: CRITICAL swarm discord. Homeostasis required."
}

// GetARTEPalette returns the current ARTE visual palette for the UI.
func (r *ResonanceService) GetARTEPalette() arte.ARTEPalette {
	return arte.PaletteFor(r.Current.ARTEState)
}
