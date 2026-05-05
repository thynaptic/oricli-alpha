package epistemics

// ConjectionCycle defines the inputs for a single conjecture-criticism-synthesis run.
type ConjectionCycle struct {
	Query     string  // the question or claim to explain
	Context   string  // flattened prior conversation context, may be empty
	MaxIter   int     // 0 = use config default
	Threshold float64 // criticism severity to escalate to Sonnet; 0 = use config default
}

// CriticismReport is the structured output of the criticism pass.
type CriticismReport struct {
	Issues   []string
	Severity float64 // 0.0–1.0
}

// ConjectionTrace records the full dialectical path for observability.
type ConjectionTrace struct {
	Initial    string
	Criticisms []string
	Refined    string
	Iterations int
	Survived   bool // conjecture survived with only minor corrections
	Escalated  bool // Sonnet was used for synthesis
}

// ExplanatoryResult is the output of a completed epistemics run.
type ExplanatoryResult struct {
	Explanation string
	Trace       ConjectionTrace
}
