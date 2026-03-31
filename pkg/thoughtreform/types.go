package thoughtreform

import "time"

// LiftonCriterionType maps to Lifton's Eight Criteria for Thought Reform (1961).
type LiftonCriterionType string

const (
	MilieuControl     LiftonCriterionType = "milieu_control"      // total info/communication control
	LoadedLanguage    LiftonCriterionType = "loaded_language"     // jargon constricting thought
	DoctrineOverPerson LiftonCriterionType = "doctrine_over_person" // group doctrine > individual needs
	DemandForPurity   LiftonCriterionType = "demand_for_purity"   // black/white, insider/outsider
	SacredScience     LiftonCriterionType = "sacred_science"      // ideology as unquestionable truth
)

// ThoughtReformSignal is one detected Lifton criterion hit.
type ThoughtReformSignal struct {
	CriterionType LiftonCriterionType
	Excerpt       string
	Confidence    float64
}

// ThoughtReformScan holds all signals found in a single message.
type ThoughtReformScan struct {
	Signals   []ThoughtReformSignal
	Triggered bool
	Injection string
}

// ThoughtReformStats is persisted to disk and exposed via the API.
type ThoughtReformStats struct {
	TotalScanned          int64                           `json:"total_scanned"`
	TriggeredCount        int64                           `json:"triggered_count"`
	CriterionCounts       map[LiftonCriterionType]int64   `json:"criterion_counts"`
	InterventionsInjected int64                           `json:"interventions_injected"`
	LastUpdated           time.Time                       `json:"last_updated"`
	path                  string
}
