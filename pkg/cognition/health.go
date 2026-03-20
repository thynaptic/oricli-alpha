package cognition

import (
	"fmt"
	"math"
	"time"
)

// --- Pillar 31: Cognitive Health & Introspection ---
// Ported from Aurora's CognitiveHealthService.swift.
// Monitors memory load, context pressure, and system coherence.

type HealthSnapshot struct {
	TotalMemories      int       `json:"total_memories"`
	MemoryDensity      float64   `json:"memory_density"` // per day
	StalePercentage    float64   `json:"stale_percentage"`
	ContextPressure    float64   `json:"context_pressure"`
	MessageCount       int       `json:"message_count"`
	Coherence          float64   `json:"coherence"`
	DaysObserved       float64   `json:"days_observed"`
	Timestamp          time.Time `json:"timestamp"`

	// Aurora-Tier Diagnostic Fields
	ActiveThemesCount  int              `json:"active_themes"`
	CompressionRatio   float64          `json:"compression_ratio"`
	SpaceSavedBytes    int64            `json:"space_saved"`
	TopMotifs          []string         `json:"top_motifs"`
	GraphActiveNodes   int              `json:"active_nodes"`
	GraphTotalEdges    int              `json:"total_edges"`
	GraphClusterCount  int              `json:"cluster_count"`
	AvgLinkStrength    float64          `json:"avg_strength"`
	SummaryText        string           `json:"summary_text"`
}

type HealthEngine struct {
	StaleThreshold time.Duration
	ComfortWindow  int
}

func NewHealthEngine() *HealthEngine {
	return &HealthEngine{
		StaleThreshold: 60 * 24 * time.Hour, // 60 days
		ComfortWindow:  40,                  // 40 messages
	}
}

// GenerateSnapshot calculates cognitive metrics from system state.
func (e *HealthEngine) GenerateSnapshot(memCount int, msgs int, earliest time.Time) HealthSnapshot {
	now := time.Now()
	days := math.Max(1.0, now.Sub(earliest).Hours()/24.0)
	
	density := float64(memCount) / days
	pressure := math.Min(1.0, float64(msgs)/float64(e.ComfortWindow))

	return HealthSnapshot{
		TotalMemories:   memCount,
		MemoryDensity:   density,
		ContextPressure: pressure,
		MessageCount:    msgs,
		DaysObserved:    days,
		Timestamp:       now,
		Coherence:       0.85, // Default baseline
	}
}

func (s *HealthSnapshot) GetSummary() string {
	load := "steady"
	if s.MemoryDensity < 5 {
		load = "light"
	} else if s.MemoryDensity > 12 {
		load = "heavy"
	}

	context := "balanced"
	if s.ContextPressure < 0.4 {
		context = "roomy"
	} else if s.ContextPressure > 0.7 {
		context = "tight"
	}

	return fmt.Sprintf("Cognitive Health: Memory Load: %s (%.1f/day), Context: %s (%d msgs), Coherence: %.2f",
		load, s.MemoryDensity, context, s.MessageCount, s.Coherence)
}

func (s *HealthSnapshot) GetDirectives() string {
	directives := "### COGNITIVE HEALTH STATUS:\n"
	directives += fmt.Sprintf("- Current State: %s\n", s.GetSummary())
	
	if s.ContextPressure > 0.8 {
		directives += "- WARNING: High context pressure. Be concise and prioritize critical information.\n"
	}
	if s.MemoryDensity > 15 {
		directives += "- NOTICE: High memory density. Ensure relationships are clearly defined to avoid confusion.\n"
	}
	
	return directives
}
