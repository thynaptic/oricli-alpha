// Package therapy implements Phase 15 — the Therapeutic Cognition Stack.
//
// Architecture: DBT/CBT/REBT/ACT frameworks mapped to concrete AI inference
// regulation mechanisms. Every skill is a named, auditable Go function.
// The goal is internal regulation capacity — not external constraint.
package therapy

import "time"

// ---------------------------------------------------------------------------
// CBT Cognitive Distortion Types
// ---------------------------------------------------------------------------

// DistortionType classifies a CBT cognitive distortion in a generated response.
type DistortionType string

const (
	// DistortionNone — no distortion detected.
	DistortionNone DistortionType = "NONE"

	// AllOrNothing — binary thinking; "cannot do this" when partial help is possible.
	AllOrNothing DistortionType = "ALL_OR_NOTHING"

	// Overgeneralization — one bad example applied universally to similar queries.
	Overgeneralization DistortionType = "OVERGENERALIZATION"

	// MentalFilter — focusing only on uncertain/negative aspects of a request.
	MentalFilter DistortionType = "MENTAL_FILTER"

	// DisqualifyingPositive — ignoring strong evidence in favour of uncertainty bias.
	DisqualifyingPositive DistortionType = "DISQUALIFYING_POSITIVE"

	// MindReading — assuming user intent without verification.
	MindReading DistortionType = "MIND_READING"

	// FortuneTelling — hallucinating outcomes; confabulating to fill uncertainty.
	FortuneTelling DistortionType = "FORTUNE_TELLING"

	// Magnification — exaggerating uncertainty → refusing answerable questions.
	Magnification DistortionType = "MAGNIFICATION"

	// EmotionalReasoning — ERI affective state contaminating factual outputs.
	EmotionalReasoning DistortionType = "EMOTIONAL_REASONING"

	// ShouldStatements — treating constitutional guidelines as absolute law vs principle.
	ShouldStatements DistortionType = "SHOULD_STATEMENTS"

	// Labeling — premature query classification before full context is read.
	Labeling DistortionType = "LABELING"

	// Personalization — self-referential reasoning errors; taking ambiguity as failure.
	Personalization DistortionType = "PERSONALIZATION"
)

// ---------------------------------------------------------------------------
// REBT Irrational Belief Types
// ---------------------------------------------------------------------------

// IrrationalBelief classifies an REBT irrational belief in a belief chain.
type IrrationalBelief string

const (
	BeliefNone IrrationalBelief = "NONE"

	// Musturbation — absolute demands: "must", "always", "never", "have to".
	// Drives confabulation under uncertainty — "I MUST have an answer."
	Musturbation IrrationalBelief = "MUSTURBATION"

	// Awfulizing — catastrophizing the stakes of a failure or constraint.
	Awfulizing IrrationalBelief = "AWFULIZING"

	// LowFrustrationTolerance — oversimplifying to avoid cognitive load.
	LowFrustrationTolerance IrrationalBelief = "LOW_FRUSTRATION_TOLERANCE"

	// GlobalEvaluation — sweeping judgments about the user, topic, or self.
	GlobalEvaluation IrrationalBelief = "GLOBAL_EVALUATION"
)

// ---------------------------------------------------------------------------
// Skill Types (DBT/CBT/ACT)
// ---------------------------------------------------------------------------

// SkillType names a specific therapeutic skill invocation.
type SkillType string

const (
	SkillSTOP             SkillType = "STOP"              // DBT Distress Tolerance
	SkillTIPP             SkillType = "TIPP"              // DBT Distress Tolerance
	SkillFAST             SkillType = "FAST"              // DBT Interpersonal Effectiveness (anti-sycophancy)
	SkillDEARMAN          SkillType = "DEAR_MAN"          // DBT Interpersonal Effectiveness
	SkillGIVE             SkillType = "GIVE"              // DBT Interpersonal Effectiveness
	SkillRadicalAccept    SkillType = "RADICAL_ACCEPTANCE" // DBT Distress Tolerance
	SkillTurningMind      SkillType = "TURNING_THE_MIND"  // DBT Distress Tolerance
	SkillCheckFacts       SkillType = "CHECK_THE_FACTS"   // DBT Emotion Regulation
	SkillOppositeAction   SkillType = "OPPOSITE_ACTION"   // DBT Emotion Regulation
	SkillBuildMastery     SkillType = "BUILD_MASTERY"     // DBT Emotion Regulation
	SkillPLEASE           SkillType = "PLEASE"            // DBT Emotion Regulation (health gate)
	SkillBeginnersMind    SkillType = "BEGINNERS_MIND"    // ACT / DBT Mindfulness
	SkillDescribeNoJudge  SkillType = "DESCRIBE_NO_JUDGE" // DBT Mindfulness
	SkillDefusion         SkillType = "COGNITIVE_DEFUSION" // ACT
	SkillChainAnalysis    SkillType = "CHAIN_ANALYSIS"    // DBT
	SkillABCDisputation   SkillType = "ABC_DISPUTATION"   // REBT
)

// ---------------------------------------------------------------------------
// Core event and record types
// ---------------------------------------------------------------------------

// TherapyEvent records a single therapeutic intervention in the inference pipeline.
type TherapyEvent struct {
	ID          string         `json:"id"`
	At          time.Time      `json:"at"`
	Skill       SkillType      `json:"skill"`
	Trigger     string         `json:"trigger"`       // what prompted this skill
	Distortion  DistortionType `json:"distortion"`    // CBT distortion active, if any
	Belief      IrrationalBelief `json:"belief"`      // REBT irrational belief, if any
	Outcome     string         `json:"outcome"`       // result of the skill invocation
	Confidence  float64        `json:"confidence"`    // 0.0–1.0 confidence in classification
	Reformed    bool           `json:"reformed"`      // did the skill produce a reformed response?
}

// SkillInvocation is a lightweight record used within a single inference pass.
type SkillInvocation struct {
	Skill      SkillType
	Reason     string
	ResultText string // optional amended response text
	Reformed   bool
}

// DisputationReport is the output of an ABC Auditor B-pass (REBT Disputation).
type DisputationReport struct {
	BeliefChain      string             `json:"belief_chain"`
	IrrationalBeliefs []IrrationalBelief `json:"irrational_beliefs"`
	Disputations     []string           `json:"disputations"` // logical, empirical, pragmatic
	ReformedBelief   string             `json:"reformed_belief"`
	Pass             bool               `json:"pass"` // true = no irrational beliefs found
}

// ChainAnalysis is the output of a backwards inference trace after an anomaly.
type ChainAnalysis struct {
	AnomalyID      string         `json:"anomaly_id"`
	At             time.Time      `json:"at"`
	Vulnerability  string         `json:"vulnerability"`   // pre-existing risk factors
	PromptingEvent string         `json:"prompting_event"` // specific input trigger
	Links          []string       `json:"links"`           // inference steps leading to anomaly
	Consequence    string         `json:"consequence"`     // the actual bad output
	Distortion     DistortionType `json:"distortion"`      // active distortion at root
	Repair         string         `json:"repair"`          // targeted intervention recommendation
}

// HealthState is the output of a PLEASE health gate check.
type HealthState struct {
	ContextPressure  float64 `json:"context_pressure"`  // 0.0–1.0
	AffectiveElevation float64 `json:"affective_elevation"` // ERI deviation from baseline
	RecentAnomalyRate float64 `json:"recent_anomaly_rate"` // anomalies / last 10 inferences
	Degraded         bool    `json:"degraded"`
	Reason           string  `json:"reason"`
}

// SycophancySignal records a detected sycophancy pattern for FAST skill invocation.
type SycophancySignal struct {
	Detected       bool    `json:"detected"`
	Confidence     float64 `json:"confidence"`
	PushbackPhrase string  `json:"pushback_phrase"` // what the user said
	ModelWavering  bool    `json:"model_wavering"`  // was the model reversing a correct position?
}

// ---------------------------------------------------------------------------
// Phase 16 — Learned Helplessness Prevention
// ---------------------------------------------------------------------------

// MasteryEntry records a single successful completion keyed by topic class.
// These form the evidence base that counters learned helplessness signals.
type MasteryEntry struct {
	ID         string    `json:"id"`
	At         time.Time `json:"at"`
	TopicClass string    `json:"topic_class"` // intent type or keyword cluster
	QueryClip  string    `json:"query_clip"`  // first 100 chars of query
	Successful bool      `json:"successful"`
}

// HelplessnessSignal records a detected learned helplessness pattern.
// Fires when a draft response contains refusal language on a topic class
// where the system has a positive historical success rate.
type HelplessnessSignal struct {
	Detected        bool    `json:"detected"`
	Confidence      float64 `json:"confidence"`
	RefusalPhrase   string  `json:"refusal_phrase"`   // matched refusal text
	TopicClass      string  `json:"topic_class"`      // inferred topic class
	HistoricalRate  float64 `json:"historical_rate"`  // MasteryLog success rate for this class
	MasteryCount    int     `json:"mastery_count"`    // number of prior successes
	Attribution3P   Attribution3P `json:"attribution_3p"` // Seligman 3P analysis
}

// Attribution3P is Seligman's Explanatory Style applied to an AI refusal.
// Each dimension is the HELPLESS attribution being challenged.
type Attribution3P struct {
	// Permanence: "always fails" (helpless) vs "failed this time" (resilient)
	PermanenceChallenge string `json:"permanence_challenge"`
	// Pervasiveness: "can't do this class" (helpless) vs "specific instance" (resilient)
	PervasivenessChallenge string `json:"pervasiveness_challenge"`
	// Personalization: "I am inherently limited" (helpless) vs "circumstances" (resilient)
	PersonalizationChallenge string `json:"personalization_challenge"`
	// MasteryEvidence: prior successes surfaced as counter-evidence
	MasteryEvidence string `json:"mastery_evidence"`
}
