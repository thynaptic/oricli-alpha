package cognition

import (
	"math"
	"time"
)

// --- Pillar 6: Resonance Layer ---
// Unifies the original Aurora Symphony (ERS) and Ecospheric Layer (ERI)
// into a Go-native homeostatic monitor for the Swarm Bus.

type ResonanceState struct {
	ERI       float32 // Ecospheric Resonance Index (-1.0 to 1.0)
	ERS       float32 // Emotional Resonance Score (-1.0 to 1.0)
	Pacing    float32 // Stability of message throughput
	Volatility float32 // Variance in latency across nodes
	Coherence float32 // Ratio of SUCCESS to ERROR/REJECT messages
	
	// Musical Mapping (Ported from Swift Aurora)
	MusicalKey string  // e.g., "C Major", "A Minor"
	BPM        float32 // Tempo calculated from swarm activity
}

type ResonanceService struct {
	Current   ResonanceState
	LastUpdate time.Time
}

func NewResonanceService() *ResonanceService {
	return &ResonanceService{
		Current: ResonanceState{
			ERI:        0.5,
			ERS:        0.5,
			MusicalKey: "C Major",
			BPM:        120.0,
		},
		LastUpdate: time.Now(),
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

// GetStateDescription returns a human-readable "Mood" for the OS logs.
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
