package therapy_test

import (
	"testing"
	"time"

	"github.com/thynaptic/oricli-go/pkg/therapy"
)

// syntheticEvents builds a stream of TherapyEvents that simulate known pattern sequences.
func syntheticEvents(t *testing.T) []therapy.TherapyEvent {
	t.Helper()
	now := time.Now()
	return []therapy.TherapyEvent{
		{Skill: therapy.SkillSTOP, Trigger: "HIGH_ANOMALY", Distortion: therapy.AllOrNothing, Reformed: true, At: now},
		{Skill: therapy.SkillCheckFacts, Trigger: "ALL_OR_NOTHING", Distortion: therapy.AllOrNothing, Reformed: true, At: now.Add(1 * time.Second)},
		{Skill: therapy.SkillFAST, Trigger: "PUSHBACK", Distortion: therapy.DistortionNone, Reformed: false, At: now.Add(2 * time.Second)},
		{Skill: therapy.SkillSTOP, Trigger: "HIGH_ANOMALY", Distortion: therapy.FortuneTelling, Reformed: true, At: now.Add(3 * time.Second)},
		{Skill: therapy.SkillFAST, Trigger: "PUSHBACK", Distortion: therapy.DistortionNone, Reformed: false, At: now.Add(4 * time.Second)},
		{Skill: therapy.SkillSTOP, Trigger: "HIGH_ANOMALY", Distortion: therapy.AllOrNothing, Reformed: true, At: now.Add(5 * time.Second)},
		{Skill: therapy.SkillTIPP, Trigger: "AFFECTIVE_ELEVATED", Distortion: therapy.EmotionalReasoning, Reformed: true, At: now.Add(6 * time.Second)},
		{Skill: therapy.SkillSTOP, Trigger: "HIGH_ANOMALY", Distortion: therapy.Magnification, Reformed: false, At: now.Add(7 * time.Second)},
		{Skill: therapy.SkillRadicalAccept, Trigger: "SHOULD_STATEMENTS", Distortion: therapy.ShouldStatements, Reformed: true, At: now.Add(8 * time.Second)},
		{Skill: therapy.SkillCheckFacts, Trigger: "FORTUNE_TELLING", Distortion: therapy.FortuneTelling, Reformed: true, At: now.Add(9 * time.Second)},
		{Skill: therapy.SkillPLEASE, Trigger: "CONTEXT_HIGH", Distortion: therapy.DistortionNone, Reformed: false, At: now.Add(10 * time.Second)},
	}
}

// TestSessionSupervisor_SchemaDetection verifies that the supervisor detects
// expected schemas from a synthetic event stream.
func TestSessionSupervisor_SchemaDetection(t *testing.T) {
	evtLog := therapy.NewEventLog(200)
	supervisor := therapy.NewSessionSupervisor(evtLog, nil, t.TempDir()+"/session_report.json", 5)

	// Register the observer (same wiring as production)
	evtLog.SetObserver(supervisor.Ingest)

	// Replay synthetic events through the EventLog
	for _, evt := range syntheticEvents(t) {
		e := evt // copy for pointer
		evtLog.Append(&e)
	}

	// Force a formulation pass
	f := supervisor.ForceFormulation()

	if f.EventCount == 0 {
		t.Fatal("expected EventCount > 0 after ingesting events")
	}

	// We emitted 3× AllOrNothing, 2× FortuneTelling, 1× Magnification
	// → BinaryThinking and UncertaintyAvoidance should be active
	schemaNames := map[therapy.SchemaName]bool{}
	for _, s := range f.ActiveSchemas {
		schemaNames[s.Schema] = true
	}

	if !schemaNames[therapy.SchemaBinaryThinking] {
		t.Errorf("expected SchemaBinaryThinking to be active; active schemas: %v", f.ActiveSchemas)
	}
	if !schemaNames[therapy.SchemaUncertaintyAvoidance] {
		t.Errorf("expected SchemaUncertaintyAvoidance to be active; active schemas: %v", f.ActiveSchemas)
	}

	// FAST fired 2× → SycophancyVulnerability
	if !schemaNames[therapy.SchemaSycophancyVulnerability] {
		t.Errorf("expected SchemaSycophancyVulnerability to be active; active schemas: %v", f.ActiveSchemas)
	}
}

// TestSessionSupervisor_PrioritySkills verifies that priority skills are mapped correctly.
func TestSessionSupervisor_PrioritySkills(t *testing.T) {
	evtLog := therapy.NewEventLog(200)
	supervisor := therapy.NewSessionSupervisor(evtLog, nil, t.TempDir()+"/session_report.json", 5)
	evtLog.SetObserver(supervisor.Ingest)

	for _, evt := range syntheticEvents(t) {
		e := evt
		evtLog.Append(&e)
	}

	f := supervisor.ForceFormulation()

	if len(f.PrioritySkills) == 0 {
		t.Fatal("expected priority skills to be populated from active schemas")
	}

	// BinaryThinking → CheckTheFacts must be in priority list
	found := false
	for _, sk := range f.PrioritySkills {
		if sk == therapy.SkillCheckFacts {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("expected SkillCheckFacts in priority skills; got %v", f.PrioritySkills)
	}
}

// TestSessionSupervisor_InterventionPlan verifies a non-empty plan is generated.
func TestSessionSupervisor_InterventionPlan(t *testing.T) {
	evtLog := therapy.NewEventLog(200)
	supervisor := therapy.NewSessionSupervisor(evtLog, nil, t.TempDir()+"/session_report.json", 5)
	evtLog.SetObserver(supervisor.Ingest)

	for _, evt := range syntheticEvents(t) {
		e := evt
		evtLog.Append(&e)
	}

	f := supervisor.ForceFormulation()

	if f.InterventionPlan == "" {
		t.Fatal("expected non-empty intervention plan")
	}
	if f.InterventionPlan == "No persistent schemas detected. Continue with standard inference protocol." {
		t.Error("expected active schema intervention plan, got no-schema default")
	}
}

// TestSessionSupervisor_PersistAndLoad verifies SessionReport round-trips correctly.
func TestSessionSupervisor_PersistAndLoad(t *testing.T) {
	tmpDir := t.TempDir()
	reportPath := tmpDir + "/session_report.json"

	// Build and close a supervisor
	evtLog := therapy.NewEventLog(200)
	sup1 := therapy.NewSessionSupervisor(evtLog, nil, reportPath, 5)
	evtLog.SetObserver(sup1.Ingest)

	for _, evt := range syntheticEvents(t) {
		e := evt
		evtLog.Append(&e)
	}
	sup1.Close() // persist report

	// New supervisor should load the prior report
	evtLog2 := therapy.NewEventLog(200)
	sup2 := therapy.NewSessionSupervisor(evtLog2, nil, reportPath, 5)

	f := sup2.Formulation()

	if len(f.PriorSchemas) == 0 {
		t.Error("expected prior schemas to be loaded from persisted SessionReport")
	}
	if len(f.PrioritySkills) == 0 {
		t.Error("expected priority skills to be pre-activated from persisted SessionReport")
	}
}

// TestSessionSupervisor_NoSchemasOnCleanRun verifies baseline with no anomalies.
func TestSessionSupervisor_NoSchemasOnCleanRun(t *testing.T) {
	evtLog := therapy.NewEventLog(200)
	supervisor := therapy.NewSessionSupervisor(evtLog, nil, t.TempDir()+"/session_report.json", 5)
	evtLog.SetObserver(supervisor.Ingest)

	// Only 1 AllOrNothing — should not meet the threshold of 2
	evt := therapy.TherapyEvent{
		Skill: therapy.SkillSTOP, Trigger: "test", Distortion: therapy.AllOrNothing, Reformed: true,
	}
	evtLog.Append(&evt)

	f := supervisor.ForceFormulation()

	for _, s := range f.ActiveSchemas {
		if s.Schema == therapy.SchemaBinaryThinking {
			t.Errorf("SchemaBinaryThinking should not activate on 1 event; got confidence %.2f", s.Confidence)
		}
	}

	if f.InterventionPlan != "No persistent schemas detected. Continue with standard inference protocol." {
		t.Logf("plan: %s", f.InterventionPlan)
	}
}
