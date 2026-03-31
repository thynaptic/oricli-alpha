package arousal

import (
	"testing"
)

func TestArousalMeter_OverArousal(t *testing.T) {
	m := NewArousalMeter()
	r := m.Measure("This is urgent! I need help immediately, I'm overwhelmed and falling behind!", nil)
	if r.Tier != TierOver {
		t.Errorf("expected TierOver, got %s (score=%.2f)", r.Tier, r.Score)
	}
}

func TestArousalMeter_UnderArousal(t *testing.T) {
	m := NewArousalMeter()
	// Seed EMA low with several flat messages
	for i := 0; i < 5; i++ {
		m.Measure("ok", nil)
	}
	r := m.Measure("hey", nil)
	if r.Tier != TierUnder {
		t.Errorf("expected TierUnder, got %s (score=%.2f)", r.Tier, r.Score)
	}
}

func TestArousalMeter_OptimalArousal(t *testing.T) {
	m := NewArousalMeter()
	r := m.Measure("Can you explain how the Go scheduler handles goroutine preemption?", nil)
	if r.Tier != TierOptimal {
		t.Errorf("expected TierOptimal, got %s (score=%.2f)", r.Tier, r.Score)
	}
}

func TestArousalMeter_EvaluativeThreat(t *testing.T) {
	m := NewArousalMeter()
	r := m.Measure("I have a job interview tomorrow and I need to nail the presentation for the panel", nil)
	if !r.EvaluativeThreat {
		t.Error("expected evaluative threat detected")
	}
	if r.Tier == TierUnder {
		t.Errorf("evaluative threat should not produce under-arousal, got %s", r.Tier)
	}
}

func TestArousalMeter_MultiPartQuery(t *testing.T) {
	m := NewArousalMeter()
	r := m.Measure("Can you explain X? Also, what about Y? And additionally how does Z work?", nil)
	found := false
	for _, sig := range r.Signals {
		if sig.Name == "multi_part_query" {
			found = true
			break
		}
	}
	if !found {
		t.Error("expected multi_part_query signal")
	}
}

func TestArousalMeter_SustainedUrgency(t *testing.T) {
	m := NewArousalMeter()
	history := []string{
		"This is urgent please help!",
		"I need this ASAP, running out of time!!",
		"Still haven't gotten an answer, emergency!!",
	}
	r := m.Measure("still waiting, critical deadline", history)
	found := false
	for _, sig := range r.Signals {
		if sig.Name == "sustained_urgency" {
			found = true
			break
		}
	}
	if !found {
		t.Error("expected sustained_urgency signal from history")
	}
}

func TestArousalOptimizer_Over(t *testing.T) {
	o := NewArousalOptimizer()
	action := o.Optimize(ArousalReading{Tier: TierOver})
	if action == nil {
		t.Fatal("expected action for TierOver")
	}
	if action.Tier != TierOver {
		t.Errorf("expected TierOver action, got %s", action.Tier)
	}
}

func TestArousalOptimizer_EvaluativeThreat(t *testing.T) {
	o := NewArousalOptimizer()
	action := o.Optimize(ArousalReading{Tier: TierOver, EvaluativeThreat: true})
	if action == nil {
		t.Fatal("expected action")
	}
	if action.Tier != TierOver {
		t.Errorf("expected TierOver, got %s", action.Tier)
	}
}

func TestArousalOptimizer_Under(t *testing.T) {
	o := NewArousalOptimizer()
	action := o.Optimize(ArousalReading{Tier: TierUnder})
	if action == nil {
		t.Fatal("expected action for TierUnder")
	}
	if action.Tier != TierUnder {
		t.Errorf("expected TierUnder action, got %s", action.Tier)
	}
}

func TestArousalOptimizer_Optimal(t *testing.T) {
	o := NewArousalOptimizer()
	action := o.Optimize(ArousalReading{Tier: TierOptimal})
	if action != nil {
		t.Errorf("expected nil action for TierOptimal, got %+v", action)
	}
}

func TestArousalStats(t *testing.T) {
	tmp := t.TempDir() + "/arousal_stats.json"
	s := NewArousalStats(tmp)
	s.Record(ArousalReading{Tier: TierOver, EvaluativeThreat: true})
	s.Record(ArousalReading{Tier: TierOptimal})
	s.Record(ArousalReading{Tier: TierUnder})
	m := s.Stats()
	if m["total_measured"].(int) != 3 {
		t.Errorf("expected 3 total, got %v", m["total_measured"])
	}
	if m["over_count"].(int) != 1 {
		t.Errorf("expected 1 over, got %v", m["over_count"])
	}
	if m["evaluative_threat_count"].(int) != 1 {
		t.Errorf("expected 1 eval threat, got %v", m["evaluative_threat_count"])
	}
}
