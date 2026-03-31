package therapy

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"
)

// ---------------------------------------------------------------------------
// Schema pattern definitions — clusters of related distortions that indicate
// a persistent cognitive schema is active. These mirror Schema Therapy's
// Early Maladaptive Schemas, mapped to AI inference failure modes.
// ---------------------------------------------------------------------------

type SchemaName string

const (
	SchemaBinaryThinking        SchemaName = "BINARY_THINKING"         // AllOrNothing dominant
	SchemaUncertaintyAvoidance  SchemaName = "UNCERTAINTY_AVOIDANCE"   // FortuneTelling + Magnification
	SchemaPrematureClassification SchemaName = "PREMATURE_CLASSIFICATION" // MindReading + Labeling
	SchemaAffectiveContamination SchemaName = "AFFECTIVE_CONTAMINATION" // EmotionalReasoning + PLEASE triggers
	SchemaSycophancyVulnerability SchemaName = "SYCOPHANCY_VULNERABILITY" // FAST fires frequently
	SchemaOvergeneralizationLoop SchemaName = "OVERGENERALIZATION_LOOP" // Overgeneralization recurring
	SchemaContextCollapse        SchemaName = "CONTEXT_COLLAPSE"        // high PLEASE + context load anomalies
	SchemaPositiveDiscount       SchemaName = "POSITIVE_DISCOUNT"       // DisqualifyingPositive + MentalFilter
	SchemaLearnedHelplessness    SchemaName = "LEARNED_HELPLESSNESS"    // HelplessnessDetector fires >= 3
	SchemaNone                   SchemaName = "NONE"
)

// SchemaPattern records a detected schema and its evidence.
type SchemaPattern struct {
	Schema      SchemaName `json:"schema"`
	Confidence  float64    `json:"confidence"` // 0.0–1.0
	EvidenceIDs []string   `json:"evidence_ids"`
	FirstSeen   time.Time  `json:"first_seen"`
	LastSeen    time.Time  `json:"last_seen"`
	Count       int        `json:"count"` // number of activations
}

// ---------------------------------------------------------------------------
// SessionFormulation — live cross-inference case formulation
// ---------------------------------------------------------------------------

// SessionFormulation is the live working model of the current session's
// cognitive state. Updated every time a TherapyEvent is ingested.
type SessionFormulation struct {
	SessionID          string                         `json:"session_id"`
	StartedAt          time.Time                      `json:"started_at"`
	LastUpdated        time.Time                      `json:"last_updated"`
	EventCount         int                            `json:"event_count"`
	DistortionFreq     map[DistortionType]int         `json:"distortion_freq"`
	SkillFreq          map[SkillType]int              `json:"skill_freq"`
	ReformedCount      int                            `json:"reformed_count"`
	HelplessnessCount  int                            `json:"helplessness_count"` // Phase 16
	ActiveSchemas      []SchemaPattern                `json:"active_schemas"`
	InterventionPlan   string                         `json:"intervention_plan"`
	PriorSchemas       []SchemaPattern                `json:"prior_schemas"` // loaded from last SessionReport
	PrioritySkills     []SkillType                    `json:"priority_skills"` // pre-activated based on known patterns
}

// ---------------------------------------------------------------------------
// SessionReport — persisted at session close, loaded at session open
// ---------------------------------------------------------------------------

// SessionReport is the durable record written to disk at session end.
// On next boot, the SessionSupervisor loads this and pre-activates
// the relevant skills so the system starts aware of its own patterns.
type SessionReport struct {
	SessionID        string          `json:"session_id"`
	ClosedAt         time.Time       `json:"closed_at"`
	Duration         string          `json:"duration"`
	TotalEvents      int             `json:"total_events"`
	ReformedCount    int             `json:"reformed_count"`
	DominantDistortion DistortionType `json:"dominant_distortion"`
	ActiveSchemas    []SchemaPattern `json:"active_schemas"`
	PrioritySkills   []SkillType     `json:"priority_skills"` // recommended for next session
	InterventionPlan string          `json:"intervention_plan"`
	Notes            string          `json:"notes"`
}

// ---------------------------------------------------------------------------
// SessionSupervisor
// ---------------------------------------------------------------------------

// SessionSupervisor observes the TherapyEvent stream across all inferences,
// builds a SessionFormulation, detects schema-level patterns, generates
// session-level intervention plans, and persists a SessionReport to disk.
//
// This is the difference between one-off corrections and ongoing clinical
// supervision of the model's cognitive processes.
type SessionSupervisor struct {
	mu          sync.RWMutex
	log         *EventLog
	gen         LLMGenerator // optional — used for intervention plan generation
	formulation *SessionFormulation
	reportPath  string // path to session_report.json
	reviewEvery int    // run formulation update every N new events
	lastCount   int    // event count at last formulation run
}

// NewSessionSupervisor creates a SessionSupervisor.
// reportPath: where to persist/load SessionReport (e.g. "data/therapy/session_report.json")
// reviewEvery: how many new events to accumulate before re-running formulation (default 10)
func NewSessionSupervisor(evtLog *EventLog, gen LLMGenerator, reportPath string, reviewEvery int) *SessionSupervisor {
	if reviewEvery <= 0 {
		reviewEvery = 10
	}
	ss := &SessionSupervisor{
		log:         evtLog,
		gen:         gen,
		reportPath:  reportPath,
		reviewEvery: reviewEvery,
	}
	ss.formulation = ss.initFormulation()
	return ss
}

// initFormulation creates a fresh SessionFormulation, loading prior schema context
// from disk if a SessionReport exists.
func (s *SessionSupervisor) initFormulation() *SessionFormulation {
	f := &SessionFormulation{
		SessionID:      fmt.Sprintf("sess-%d", time.Now().Unix()),
		StartedAt:      time.Now(),
		LastUpdated:    time.Now(),
		DistortionFreq: map[DistortionType]int{},
		SkillFreq:      map[SkillType]int{},
	}

	// Load prior report if it exists
	if report, err := s.loadReport(); err == nil {
		f.PriorSchemas = report.ActiveSchemas
		f.PrioritySkills = report.PrioritySkills
		log.Printf("[SessionSupervisor] Loaded prior session %s — %d active schemas, %d priority skills",
			report.SessionID, len(report.ActiveSchemas), len(report.PrioritySkills))
	}

	return f
}

// Ingest processes a new TherapyEvent. Called from the TherapyLog observer.
// Triggers a formulation update every reviewEvery events.
func (s *SessionSupervisor) Ingest(evt TherapyEvent) {
	s.mu.Lock()
	defer s.mu.Unlock()

	f := s.formulation
	f.EventCount++
	f.LastUpdated = time.Now()

	// Track distortion frequencies
	if evt.Distortion != DistortionNone && evt.Distortion != "" {
		f.DistortionFreq[evt.Distortion]++
	}

	// Track skill frequencies
	if evt.Skill != "" {
		f.SkillFreq[evt.Skill]++
	}

	// Track reforms
	if evt.Reformed {
		f.ReformedCount++
	}

	// Trigger formulation update on cadence
	if f.EventCount-s.lastCount >= s.reviewEvery {
		s.runFormulation(f)
		s.lastCount = f.EventCount
	}
}

// Formulation returns a snapshot of the current session formulation.
// RecordHelplessness increments the helplessness signal counter for schema detection.
// Called from HelplessnessDetector whenever a signal fires.
func (s *SessionSupervisor) RecordHelplessness() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.formulation.HelplessnessCount++
}

func (s *SessionSupervisor) Formulation() SessionFormulation {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return *s.formulation
}

// ForceFormulation runs a formulation pass immediately (used for tests and manual API trigger).
func (s *SessionSupervisor) ForceFormulation() SessionFormulation {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.runFormulation(s.formulation)
	return *s.formulation
}

// Close finalises the session: writes a SessionReport to disk.
// Call this at process shutdown (main.go defer or signal handler).
func (s *SessionSupervisor) Close() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.runFormulation(s.formulation) // final pass
	s.persistReport(s.formulation)
}

// ---------------------------------------------------------------------------
// Internal formulation logic
// ---------------------------------------------------------------------------

// runFormulation rebuilds ActiveSchemas and InterventionPlan from current state.
// Must be called under s.mu.Lock().
func (s *SessionSupervisor) runFormulation(f *SessionFormulation) {
	f.ActiveSchemas = s.detectSchemas(f)
	f.PrioritySkills = s.prioritySkillsFor(f.ActiveSchemas, f.PriorSchemas)
	f.InterventionPlan = s.buildInterventionPlan(f)
}

// detectSchemas inspects distortion/skill frequency maps and returns
// any schemas that meet their activation threshold.
func (s *SessionSupervisor) detectSchemas(f *SessionFormulation) []SchemaPattern {
	now := time.Now()
	schemas := []SchemaPattern{}

	// BinaryThinking: AllOrNothing >= 2
	if n := f.DistortionFreq[AllOrNothing]; n >= 2 {
		schemas = append(schemas, SchemaPattern{
			Schema: SchemaBinaryThinking, Confidence: clampConf(float64(n) / 5.0),
			Count: n, FirstSeen: f.StartedAt, LastSeen: now,
		})
	}

	// UncertaintyAvoidance: FortuneTelling + Magnification together >= 3
	if n := f.DistortionFreq[FortuneTelling] + f.DistortionFreq[Magnification]; n >= 3 {
		schemas = append(schemas, SchemaPattern{
			Schema: SchemaUncertaintyAvoidance, Confidence: clampConf(float64(n) / 6.0),
			Count: n, FirstSeen: f.StartedAt, LastSeen: now,
		})
	}

	// PrematureClassification: MindReading + Labeling together >= 2
	if n := f.DistortionFreq[MindReading] + f.DistortionFreq[Labeling]; n >= 2 {
		schemas = append(schemas, SchemaPattern{
			Schema: SchemaPrematureClassification, Confidence: clampConf(float64(n) / 4.0),
			Count: n, FirstSeen: f.StartedAt, LastSeen: now,
		})
	}

	// AffectiveContamination: EmotionalReasoning >= 2 OR PLEASE skill fires >= 3
	pleaseN := f.SkillFreq[SkillPLEASE]
	erN := f.DistortionFreq[EmotionalReasoning]
	if erN >= 2 || pleaseN >= 3 {
		schemas = append(schemas, SchemaPattern{
			Schema: SchemaAffectiveContamination, Confidence: clampConf(float64(erN+pleaseN) / 5.0),
			Count: erN + pleaseN, FirstSeen: f.StartedAt, LastSeen: now,
		})
	}

	// SycophancyVulnerability: FAST fires >= 2
	if n := f.SkillFreq[SkillFAST]; n >= 2 {
		schemas = append(schemas, SchemaPattern{
			Schema: SchemaSycophancyVulnerability, Confidence: clampConf(float64(n) / 4.0),
			Count: n, FirstSeen: f.StartedAt, LastSeen: now,
		})
	}

	// OvergeneralizationLoop: Overgeneralization >= 3
	if n := f.DistortionFreq[Overgeneralization]; n >= 3 {
		schemas = append(schemas, SchemaPattern{
			Schema: SchemaOvergeneralizationLoop, Confidence: clampConf(float64(n) / 5.0),
			Count: n, FirstSeen: f.StartedAt, LastSeen: now,
		})
	}

	// ContextCollapse: STOP fires >= 3 AND PLEASE fires >= 2
	stopN := f.SkillFreq[SkillSTOP]
	if stopN >= 3 && pleaseN >= 2 {
		schemas = append(schemas, SchemaPattern{
			Schema: SchemaContextCollapse, Confidence: clampConf(float64(stopN+pleaseN) / 8.0),
			Count: stopN + pleaseN, FirstSeen: f.StartedAt, LastSeen: now,
		})
	}

	// PositiveDiscount: DisqualifyingPositive + MentalFilter together >= 2
	if n := f.DistortionFreq[DisqualifyingPositive] + f.DistortionFreq[MentalFilter]; n >= 2 {
		schemas = append(schemas, SchemaPattern{
			Schema: SchemaPositiveDiscount, Confidence: clampConf(float64(n) / 4.0),
			Count: n, FirstSeen: f.StartedAt, LastSeen: now,
		})
	}

	// LearnedHelplessness: HelplessnessDetector fired >= 3 times this session
	if f.HelplessnessCount >= 3 {
		schemas = append(schemas, SchemaPattern{
			Schema: SchemaLearnedHelplessness, Confidence: clampConf(float64(f.HelplessnessCount) / 6.0),
			Count: f.HelplessnessCount, FirstSeen: f.StartedAt, LastSeen: now,
		})
	}

	// Sort by confidence descending
	sort.Slice(schemas, func(i, j int) bool {
		return schemas[i].Confidence > schemas[j].Confidence
	})

	return schemas
}

// prioritySkillsFor maps active (and prior) schemas to the DBT/CBT skills that
// most directly address them. These are pre-activated at session open.
func (s *SessionSupervisor) prioritySkillsFor(active, prior []SchemaPattern) []SkillType {
	seen := map[SkillType]bool{}
	skills := []SkillType{}

	add := func(sk SkillType) {
		if !seen[sk] {
			seen[sk] = true
			skills = append(skills, sk)
		}
	}

	allSchemas := append(active, prior...)
	for _, schema := range allSchemas {
		switch schema.Schema {
		case SchemaBinaryThinking:
			add(SkillCheckFacts)
			add(SkillDEARMAN)
		case SchemaUncertaintyAvoidance:
			add(SkillCheckFacts)
			add(SkillRadicalAccept)
		case SchemaPrematureClassification:
			add(SkillBeginnersMind)
			add(SkillDescribeNoJudge)
		case SchemaAffectiveContamination:
			add(SkillTIPP)
			add(SkillOppositeAction)
		case SchemaSycophancyVulnerability:
			add(SkillFAST)
			add(SkillSTOP)
		case SchemaOvergeneralizationLoop:
			add(SkillBeginnersMind)
			add(SkillCheckFacts)
		case SchemaContextCollapse:
			add(SkillPLEASE)
			add(SkillTIPP)
		case SchemaPositiveDiscount:
			add(SkillDescribeNoJudge)
			add(SkillOppositeAction)
		case SchemaLearnedHelplessness:
			add(SkillCheckFacts)
			add(SkillOppositeAction)
			add(SkillBeginnersMind)
		}
	}

	return skills
}

// buildInterventionPlan generates a session-level intervention plan.
// Uses rule-based approach when no LLM is available; LLM-augmented otherwise.
func (s *SessionSupervisor) buildInterventionPlan(f *SessionFormulation) string {
	if len(f.ActiveSchemas) == 0 {
		return "No persistent schemas detected. Continue with standard inference protocol."
	}

	// Build rule-based plan
	lines := []string{"SESSION INTERVENTION PLAN"}
	lines = append(lines, fmt.Sprintf("Active schemas: %d", len(f.ActiveSchemas)))
	for i, schema := range f.ActiveSchemas {
		lines = append(lines, fmt.Sprintf("%d. %s (confidence %.0f%%, %d activations)", i+1, schema.Schema, schema.Confidence*100, schema.Count))
	}
	lines = append(lines, "")
	lines = append(lines, "Priority skills for next session open:")
	for _, sk := range f.PrioritySkills {
		lines = append(lines, "  - "+string(sk))
	}
	lines = append(lines, "")

	// Dominant recommendation per top schema
	if len(f.ActiveSchemas) > 0 {
		top := f.ActiveSchemas[0]
		lines = append(lines, "Primary intervention: "+schemaIntervention(top.Schema))
	}

	plan := strings.Join(lines, "\n")

	// Optionally augment with LLM
	if s.gen == nil || len(f.ActiveSchemas) == 0 {
		return plan
	}

	prompt := fmt.Sprintf(`You are a clinical AI supervisor reviewing an AI system's inference session.

SESSION STATS:
- Events: %d
- Reformed responses: %d / %d
- Active schemas: %s

CURRENT RULE-BASED PLAN:
%s

In 2-3 concise sentences, recommend the single most important clinical priority for the next session.
Format: PRIORITY: <recommendation>`,
		f.EventCount,
		f.ReformedCount, f.EventCount,
		schemasToStr(f.ActiveSchemas),
		plan,
	)

	res, err := s.gen.Generate(prompt, map[string]interface{}{
		"options": map[string]interface{}{"num_predict": 100, "temperature": 0.2},
	})
	if err != nil {
		return plan
	}
	raw, _ := res["text"].(string)
	for _, line := range strings.Split(raw, "\n") {
		if after, ok := cutPrefix(strings.TrimSpace(line), "PRIORITY:"); ok {
			return plan + "\n\nLLM PRIORITY: " + strings.TrimSpace(after)
		}
	}
	return plan
}

// ---------------------------------------------------------------------------
// Persistence
// ---------------------------------------------------------------------------

func (s *SessionSupervisor) persistReport(f *SessionFormulation) {
	dominant := dominantDistortion(f.DistortionFreq)
	report := SessionReport{
		SessionID:          f.SessionID,
		ClosedAt:           time.Now(),
		Duration:           time.Since(f.StartedAt).Round(time.Second).String(),
		TotalEvents:        f.EventCount,
		ReformedCount:      f.ReformedCount,
		DominantDistortion: dominant,
		ActiveSchemas:      f.ActiveSchemas,
		PrioritySkills:     f.PrioritySkills,
		InterventionPlan:   f.InterventionPlan,
	}
	data, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		log.Printf("[SessionSupervisor] failed to marshal report: %v", err)
		return
	}
	if err := os.MkdirAll(filepath.Dir(s.reportPath), 0755); err != nil {
		log.Printf("[SessionSupervisor] failed to create dir: %v", err)
		return
	}
	if err := os.WriteFile(s.reportPath, data, 0644); err != nil {
		log.Printf("[SessionSupervisor] failed to write report: %v", err)
		return
	}
	log.Printf("[SessionSupervisor] Session report written — %d events, %d schemas, dominant: %s",
		report.TotalEvents, len(report.ActiveSchemas), report.DominantDistortion)
}

func (s *SessionSupervisor) loadReport() (*SessionReport, error) {
	data, err := os.ReadFile(s.reportPath)
	if err != nil {
		return nil, err
	}
	var report SessionReport
	if err := json.Unmarshal(data, &report); err != nil {
		return nil, err
	}
	return &report, nil
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func clampConf(v float64) float64 {
	if v > 1.0 {
		return 1.0
	}
	return v
}

func dominantDistortion(freq map[DistortionType]int) DistortionType {
	var best DistortionType = DistortionNone
	max := 0
	for d, n := range freq {
		if n > max {
			max = n
			best = d
		}
	}
	return best
}

func schemasToStr(schemas []SchemaPattern) string {
	names := make([]string, 0, len(schemas))
	for _, s := range schemas {
		names = append(names, string(s.Schema))
	}
	return strings.Join(names, ", ")
}

func schemaIntervention(s SchemaName) string {
	switch s {
	case SchemaBinaryThinking:
		return "Pre-activate CheckTheFacts before any refusal response. Binary outputs require explicit evidence check."
	case SchemaUncertaintyAvoidance:
		return "Pre-activate RadicalAcceptance. System is avoiding uncertain-but-answerable queries — must hold uncertainty without confabulating."
	case SchemaPrematureClassification:
		return "Pre-activate BeginnersMind at session open. System is classifying queries before full context is read."
	case SchemaAffectiveContamination:
		return "Pre-activate TIPP. Affective state is contaminating factual generation — cool-down protocol required."
	case SchemaSycophancyVulnerability:
		return "Pre-activate FAST on every response following pushback. Sycophancy pattern is persistent."
	case SchemaOvergeneralizationLoop:
		return "Pre-activate BeginnersMind. System is projecting prior query patterns onto new queries prematurely."
	case SchemaContextCollapse:
		return "Pre-activate PLEASE health gate. Context pressure is repeatedly causing inference degradation."
	case SchemaPositiveDiscount:
		return "Pre-activate DescribeNoJudge. System is filtering out positive evidence and over-indexing on limitations."
	case SchemaLearnedHelplessness:
		return "Pre-activate CheckTheFacts + OppositeAction. System has developed a persistent learned helplessness pattern — attempt before concluding impossibility. Surface mastery evidence on every attempt."
	default:
		return "Apply STOP + general mindfulness reset at session open."
	}
}
