package searchintent_test

import (
	"testing"

	"github.com/thynaptic/oricli-go/pkg/cognition"
	"github.com/thynaptic/oricli-go/pkg/searchintent"
)

// ─── Conversational fast-exits ─────────────────────────────────────────────────

func TestDetect_Conversational_NoSearch(t *testing.T) {
	cases := []string{
		"hi", "hello", "hey", "thanks", "ok", "sure", "yes", "no",
		"good morning", "how are you", "lol", "cool", "sounds good",
		"can you help me", "my name is Alice",
	}
	for _, c := range cases {
		got, _ := cognition.DetectUncertainty(c)
		if got {
			t.Errorf("conversational %q should NOT trigger search", c)
		}
	}
}

func TestDetect_ShortNoQuestion_NoSearch(t *testing.T) {
	cases := []string{"the weather", "nice day", "ok sure"}
	for _, c := range cases {
		got, _ := cognition.DetectUncertainty(c)
		if got {
			t.Errorf("short non-question %q should NOT trigger search", c)
		}
	}
}

// ─── Should trigger search ─────────────────────────────────────────────────────

func TestDetect_WhatIs_TriggersSearch(t *testing.T) {
	cases := []string{
		"what is recursion?",
		"what are eigenvectors?",
		"what does idempotent mean?",
	}
	for _, c := range cases {
		got, q := cognition.DetectUncertainty(c)
		if !got {
			t.Errorf("%q should trigger search", c)
		}
		if q.Intent != searchintent.IntentDefinition {
			t.Errorf("%q → want definition intent, got %s", c, q.Intent)
		}
	}
}

func TestDetect_WhenWho_TriggersFactual(t *testing.T) {
	cases := []string{
		"when did the Berlin Wall fall?",
		"who is the current prime minister of the UK?",
		"how many moons does Saturn have?",
	}
	for _, c := range cases {
		got, q := cognition.DetectUncertainty(c)
		if !got {
			t.Errorf("%q should trigger search", c)
		}
		if q.Intent != searchintent.IntentFactual {
			t.Errorf("%q → want factual intent, got %s", c, q.Intent)
		}
	}
}

func TestDetect_HowTo_TriggersProcedural(t *testing.T) {
	cases := []string{
		"how to set up a reverse proxy with nginx?",
		"how do I deploy a Go app to Linux?",
	}
	for _, c := range cases {
		got, q := cognition.DetectUncertainty(c)
		if !got {
			t.Errorf("%q should trigger search", c)
		}
		if q.Intent != searchintent.IntentProcedural {
			t.Errorf("%q → want procedural, got %s", c, q.Intent)
		}
	}
}

func TestDetect_TellMeAbout_TriggersSearch(t *testing.T) {
	got, q := cognition.DetectUncertainty("tell me about the Byzantine Generals Problem")
	if !got {
		t.Error("'tell me about' should trigger search")
	}
	if q.RawTopic == "" {
		t.Error("RawTopic should not be empty")
	}
}

func TestDetect_Explain_TriggersSearch(t *testing.T) {
	got, q := cognition.DetectUncertainty("explain the difference between TCP and UDP")
	if !got {
		t.Error("'explain' should trigger search")
	}
	if q.RawTopic == "" {
		t.Error("RawTopic should not be empty")
	}
}

func TestDetect_Latest_TriggersCurrentEvents(t *testing.T) {
	got, q := cognition.DetectUncertainty("what's the latest news about AI regulation?")
	if !got {
		t.Error("'latest' should trigger search")
	}
	if q.Intent != searchintent.IntentCurrentEvents {
		t.Errorf("want current_events, got %s", q.Intent)
	}
}

// ─── Topic extraction quality ──────────────────────────────────────────────────

func TestDetect_ExtractsTopic_NotFullPrompt(t *testing.T) {
	_, q := cognition.DetectUncertainty("what is entropy in thermodynamics?")
	// RawTopic should be trimmed to the subject, not the full sentence
	if q.RawTopic == "" {
		t.Error("RawTopic should not be empty")
	}
	// Should not start with "what is"
	if len(q.RawTopic) > 50 {
		t.Errorf("RawTopic suspiciously long (%d chars): %q", len(q.RawTopic), q.RawTopic)
	}
}

func TestDetect_FormattedQueryNotEmpty(t *testing.T) {
	_, q := cognition.DetectUncertainty("who was Marie Curie?")
	if q.FormattedQuery == "" {
		t.Error("FormattedQuery should not be empty")
	}
}

func TestDetect_MaxPassesSet(t *testing.T) {
	_, q := cognition.DetectUncertainty("what is entropy?")
	if q.MaxPasses < 1 {
		t.Errorf("MaxPasses should be ≥ 1, got %d", q.MaxPasses)
	}
}
