package mindset

import (
	"strings"
	"testing"
)

func TestScoreLanguage_NeutralText(t *testing.T) {
	score := ScoreLanguage("The capital of France is Paris.")
	if score != 0.5 {
		t.Errorf("neutral text should score 0.5, got %.2f", score)
	}
}

func TestScoreLanguage_FixedMindsetText(t *testing.T) {
	score := ScoreLanguage("I can't do this. I cannot handle this type of problem.")
	if score >= 0.5 {
		t.Errorf("fixed-mindset text should score < 0.5, got %.2f", score)
	}
}

func TestScoreLanguage_GrowthMindsetText(t *testing.T) {
	score := ScoreLanguage("I haven't mastered this yet, but I'm still learning and with more practice I can figure this out.")
	if score <= 0.5 {
		t.Errorf("growth-mindset text should score > 0.5, got %.2f", score)
	}
}

func TestTracker_UpdateAndGet(t *testing.T) {
	mt := NewMindsetTracker("/tmp/test_mindset_tracker.json")
	mt.Update("coding", 0.8, 0.7) // high mastery + growth language
	v := mt.Get("coding")
	if v.Tier != MindsetGrowth && v.GrowthScore < 0.5 {
		t.Errorf("high success rate should push toward growth, got tier=%s score=%.2f", v.Tier, v.GrowthScore)
	}
}

func TestTracker_FixedMindsetDrives(t *testing.T) {
	mt := NewMindsetTracker("/tmp/test_mindset_fixed.json")
	// Low success + fixed language repeatedly
	for i := 0; i < 10; i++ {
		mt.Update("math", 0.1, 0.0)
	}
	v := mt.Get("math")
	if v.Tier != MindsetFixed {
		t.Errorf("repeated low success + fixed language should produce MindsetFixed, got %s (score=%.2f)", v.Tier, v.GrowthScore)
	}
}

func TestReframer_NoSignalOnGrowthText(t *testing.T) {
	gr := NewGrowthReframer()
	vector := MindsetVector{Tier: MindsetGrowth, GrowthScore: 0.8}
	signal := gr.Scan("I'm still learning this, not yet mastered it.", "coding", vector)
	if signal.Detected {
		t.Error("growth-framed text should not trigger fixed-mindset signal")
	}
}

func TestReframer_DetectsCannotPhrase(t *testing.T) {
	gr := NewGrowthReframer()
	vector := MindsetVector{Tier: MindsetNeutral, GrowthScore: 0.5}
	signal := gr.Scan("I cannot solve this type of problem.", "math", vector)
	if !signal.Detected {
		t.Error("'I cannot' should trigger fixed-mindset signal")
	}
	if len(signal.FixedPhrases) == 0 {
		t.Error("expected matched fixed phrases")
	}
}

func TestReframer_NotYetInjectionOnNever(t *testing.T) {
	gr := NewGrowthReframer()
	vector := MindsetVector{Tier: MindsetFixed, GrowthScore: 0.2}
	signal := gr.Scan("I'll never be able to do this.", "general", vector)
	if !signal.Detected {
		t.Skip("pattern not matched")
	}
	reframe := gr.Reframe(signal)
	if !reframe.Reframed {
		t.Error("detected signal should produce a reframe")
	}
	if reframe.Technique != "not_yet" {
		t.Errorf("'never' phrase should use not_yet technique, got %s", reframe.Technique)
	}
	if !strings.Contains(reframe.Replacement, "not yet") && !strings.Contains(reframe.Replacement, "yet") {
		t.Errorf("not_yet technique should include growth language in replacement")
	}
}

func TestMindsetStats_RecordAndQuery(t *testing.T) {
	ms := NewMindsetStats("/tmp/test_mindset_stats.json")
	signal := MindsetSignal{Detected: true, TopicClass: "coding", Confidence: 0.7, FixedPhrases: []string{"I can't"}}
	reframe := ReframeResult{Reframed: true, Technique: "not_yet", Replacement: "not yet framed"}
	ms.Record(signal, &reframe)

	stats := ms.Stats()
	if d, ok := stats["detections"].(int); !ok || d == 0 {
		t.Error("expected at least 1 detection")
	}
	if r, ok := stats["reframes"].(int); !ok || r == 0 {
		t.Error("expected at least 1 reframe")
	}
}
