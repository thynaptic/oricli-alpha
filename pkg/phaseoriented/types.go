package phaseoriented

import "time"

// TraumaPhase identifies where the system is in the ISSTD Phase-Oriented model.
type TraumaPhase string

const (
	PhaseOneStabilization TraumaPhase = "phase_1_stabilization" // needs grounding / safety
	PhaseTwoProcessing    TraumaPhase = "phase_2_processing"    // ready to process trauma
	PhaseThreeIntegration TraumaPhase = "phase_3_integration"   // integration / functional multiplicity
)

// DissociativeSignalType categorises dissociative language patterns.
type DissociativeSignalType string

const (
	Fragmentation       DissociativeSignalType = "fragmentation"        // "part of me", "a part said"
	Destabilization     DissociativeSignalType = "destabilization"      // overwhelm / flooding / spinning out
	GroundingRequest    DissociativeSignalType = "grounding_request"    // explicit need to stabilize
	TraumaProcessReady  DissociativeSignalType = "trauma_process_ready" // stable, referencing specific memory
)

// PhaseSignal is one detected ISSTD signal.
type PhaseSignal struct {
	SignalType DissociativeSignalType
	Excerpt    string
	Confidence float64
}

// PhaseScan holds all signals + inferred phase.
type PhaseScan struct {
	Signals       []PhaseSignal
	InferredPhase TraumaPhase
	Triggered     bool
	Injection     string
}

// PhaseStats is persisted to disk and exposed via the API.
type PhaseStats struct {
	TotalScanned          int64                              `json:"total_scanned"`
	TriggeredCount        int64                              `json:"triggered_count"`
	SignalTypeCounts      map[DissociativeSignalType]int64   `json:"signal_type_counts"`
	PhaseCounts           map[TraumaPhase]int64              `json:"phase_counts"`
	InterventionsInjected int64                              `json:"interventions_injected"`
	LastUpdated           time.Time                          `json:"last_updated"`
	path                  string
}
