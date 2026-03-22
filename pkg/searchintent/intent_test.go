package searchintent_test

import (
	"strings"
	"testing"

	"github.com/thynaptic/oricli-go/pkg/searchintent"
)

// ─── ClassifySearchIntent ─────────────────────────────────────────────────────

func TestClassify_Definition_SingleWord(t *testing.T) {
	cases := []string{"ephemeral", "ontology", "heuristic", "entropy", "paradigm"}
	for _, c := range cases {
		got := searchintent.ClassifySearchIntent(c)
		if got != searchintent.IntentDefinition {
			t.Errorf("single word %q → want definition, got %s", c, got)
		}
	}
}

func TestClassify_Definition_WhatIs(t *testing.T) {
	cases := []string{
		"what is recursion",
		"what are eigenvectors",
		"what does idempotent mean",
		"define entropy",
		"definition of Byzantine fault tolerance",
	}
	for _, c := range cases {
		got := searchintent.ClassifySearchIntent(c)
		if got != searchintent.IntentDefinition {
			t.Errorf("%q → want definition, got %s", c, got)
		}
	}
}

func TestClassify_Factual(t *testing.T) {
	cases := []string{
		"when did World War 2 end",
		"who is the president of France",
		"how many planets are in the solar system",
		"what year was the Eiffel Tower built",
		"where is the Great Barrier Reef",
	}
	for _, c := range cases {
		got := searchintent.ClassifySearchIntent(c)
		if got != searchintent.IntentFactual {
			t.Errorf("%q → want factual, got %s", c, got)
		}
	}
}

func TestClassify_Entity_ProperNoun(t *testing.T) {
	cases := []string{
		"Elon Musk",
		"OpenAI",
		"Albert Einstein",
		"European Central Bank",
	}
	for _, c := range cases {
		got := searchintent.ClassifySearchIntent(c)
		if got != searchintent.IntentEntity {
			t.Errorf("proper noun %q → want entity, got %s", c, got)
		}
	}
}

func TestClassify_Technical(t *testing.T) {
	cases := []string{
		"PostgreSQL v16",
		"gRPC documentation",
		"React hooks",
		"Kubernetes ingress controller",
		"LMDB performance",
		"FastAPI vs Flask",
	}
	for _, c := range cases {
		got := searchintent.ClassifySearchIntent(c)
		if got != searchintent.IntentTechnical && got != searchintent.IntentComparative {
			t.Errorf("technical %q → want technical or comparative, got %s", c, got)
		}
	}
}

func TestClassify_CurrentEvents(t *testing.T) {
	cases := []string{
		"latest news about AI regulation",
		"recent developments in quantum computing",
		"what's happening with the Fed rate 2025",
	}
	for _, c := range cases {
		got := searchintent.ClassifySearchIntent(c)
		if got != searchintent.IntentCurrentEvents {
			t.Errorf("%q → want current_events, got %s", c, got)
		}
	}
}

func TestClassify_Comparative(t *testing.T) {
	cases := []string{
		"Rust vs Go",
		"difference between TCP and UDP",
		"PostgreSQL vs MySQL",
	}
	for _, c := range cases {
		got := searchintent.ClassifySearchIntent(c)
		if got != searchintent.IntentComparative {
			t.Errorf("%q → want comparative, got %s", c, got)
		}
	}
}

func TestClassify_Procedural(t *testing.T) {
	cases := []string{
		"how to deploy a Go binary to a VPS",
		"steps to set up Caddy with HTTPS",
		"how do I configure nginx reverse proxy",
		"tutorial for Kubernetes ingress",
	}
	for _, c := range cases {
		got := searchintent.ClassifySearchIntent(c)
		if got != searchintent.IntentProcedural {
			t.Errorf("%q → want procedural, got %s", c, got)
		}
	}
}

func TestClassify_Topic_Default(t *testing.T) {
	cases := []string{
		"climate change impact on agriculture",
		"history of the Roman Empire",
		"machine learning in healthcare",
	}
	for _, c := range cases {
		got := searchintent.ClassifySearchIntent(c)
		if got != searchintent.IntentTopic {
			t.Errorf("broad topic %q → want topic, got %s", c, got)
		}
	}
}

// ─── BuildSearchQuery ─────────────────────────────────────────────────────────

func TestBuildQuery_Definition_FormatsCorrectly(t *testing.T) {
	q := searchintent.BuildSearchQuery("entropy", searchintent.IntentDefinition)
	if !strings.Contains(q.FormattedQuery, "define") || !strings.Contains(q.FormattedQuery, "entropy") {
		t.Errorf("definition query should contain 'define' and topic, got %q", q.FormattedQuery)
	}
	if q.MaxPasses != 1 {
		t.Errorf("definition should be single-pass, got %d", q.MaxPasses)
	}
	if q.Category != searchintent.CategoryGeneral {
		t.Errorf("definition should use general category, got %s", q.Category)
	}
}

func TestBuildQuery_CurrentEvents_SetsTimeRange(t *testing.T) {
	q := searchintent.BuildSearchQuery("AI regulation news", searchintent.IntentCurrentEvents)
	if q.TimeRange != searchintent.TimeRangeWeek {
		t.Errorf("current_events should set time_range=week, got %q", q.TimeRange)
	}
	if q.Category != searchintent.CategoryNews {
		t.Errorf("current_events should use news category, got %s", q.Category)
	}
}

func TestBuildQuery_Technical_UsesITCategory(t *testing.T) {
	q := searchintent.BuildSearchQuery("gRPC", searchintent.IntentTechnical)
	if q.Category != searchintent.CategoryIT {
		t.Errorf("technical should use IT category, got %s", q.Category)
	}
	if q.MaxPasses < 2 {
		t.Errorf("technical should use multi-pass, got %d", q.MaxPasses)
	}
}

func TestBuildQuery_Procedural_StripsDuplicateHowTo(t *testing.T) {
	q := searchintent.BuildSearchQuery("how to deploy nginx", searchintent.IntentProcedural)
	lq := strings.ToLower(q.FormattedQuery)
	// Should not produce "how to how to deploy nginx"
	if strings.Contains(lq, "how to how to") {
		t.Errorf("procedural query doubled 'how to': %q", q.FormattedQuery)
	}
	if !strings.Contains(lq, "guide") && !strings.Contains(lq, "step") {
		t.Errorf("procedural query should mention guide/step: %q", q.FormattedQuery)
	}
}

func TestBuildQuery_Entity_AppendsWikipedia(t *testing.T) {
	q := searchintent.BuildSearchQuery("Marie Curie", searchintent.IntentEntity)
	if !strings.Contains(q.FormattedQuery, "Wikipedia") {
		t.Errorf("entity query should append Wikipedia, got %q", q.FormattedQuery)
	}
}

func TestBuildQuery_SourceHints_NotEmpty(t *testing.T) {
	intents := []searchintent.SearchIntent{
		searchintent.IntentDefinition,
		searchintent.IntentTechnical,
		searchintent.IntentCurrentEvents,
	}
	for _, intent := range intents {
		q := searchintent.BuildSearchQuery("test", intent)
		if len(q.SourceHints) == 0 {
			t.Errorf("intent %s should have source hints", intent)
		}
	}
}

func TestBuildQuery_RawTopicPreserved(t *testing.T) {
	topic := "Byzantine fault tolerance"
	q := searchintent.BuildSearchQuery(topic, searchintent.IntentTopic)
	if q.RawTopic != topic {
		t.Errorf("RawTopic should be preserved, got %q", q.RawTopic)
	}
}
