package therapy

// SkillRuntime is the minimal skill surface needed outside pkg/therapy.
type SkillRuntime interface {
	FAST(userMessage, priorResponse, currentDraft string, priorConfidence float64) SkillInvocation
	STOP(trigger, originalText string) SkillInvocation
}

// DistortionRuntime is the minimal distortion detection surface needed outside pkg/therapy.
type DistortionRuntime interface {
	Detect(text, anomalyType string) DetectionResult
}

// ChainRuntime is the minimal chain-analysis surface needed outside pkg/therapy.
type ChainRuntime interface {
	Record(query, response string, distortion DistortionType, eri, contextLoad float64, anomalyType string)
}

// ABCRuntime is the minimal ABC audit surface needed outside pkg/therapy.
type ABCRuntime interface {
	Audit(query, proposedResponse string) DisputationReport
}

// EventLogRuntime is the minimal therapy event log surface needed outside pkg/therapy.
type EventLogRuntime interface {
	Recent(n int) []*TherapyEvent
}

// SessionSupervisorRuntime is the minimal session formulation surface needed outside pkg/therapy.
type SessionSupervisorRuntime interface {
	Formulation() SessionFormulation
	ForceFormulation() SessionFormulation
}

// HelplessnessRuntime is the minimal helplessness detection surface needed outside pkg/therapy.
type HelplessnessRuntime interface {
	Check(query, draft string) *HelplessnessSignal
}

// RetrainerRuntime is the minimal helplessness retraining surface needed outside pkg/therapy.
type RetrainerRuntime interface {
	Retrain(signal *HelplessnessSignal) string
}

// MasteryRuntime is the minimal mastery evidence surface needed outside pkg/therapy.
type MasteryRuntime interface {
	Record(topicClass, query string, success bool)
	SuccessRate(topicClass string) float64
	RecentSuccesses(topicClass string, n int) []*MasteryEntry
	RecentEvidence(topicClass string, n int) []string
	StatsByClass() map[string]map[string]int
}
