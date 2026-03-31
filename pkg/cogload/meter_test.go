package cogload

import (
	"strings"
	"testing"
)

func TestMeter_EmptyMessages(t *testing.T) {
	m := NewLoadMeter()
	profile := m.Measure([]map[string]string{})
	if profile.Tier != LoadNormal {
		t.Errorf("empty messages should be LoadNormal, got %s", profile.Tier)
	}
}

func TestMeter_ShortConversationNormal(t *testing.T) {
	m := NewLoadMeter()
	messages := []map[string]string{
		{"role": "user", "content": "Hello"},
		{"role": "assistant", "content": "Hi there!"},
	}
	profile := m.Measure(messages)
	if profile.Tier != LoadNormal {
		t.Errorf("short conversation should be LoadNormal, got %s (total=%.2f)", profile.Tier, profile.TotalLoad)
	}
}

func TestMeter_LongConversationElevated(t *testing.T) {
	m := NewLoadMeter()
	// Simulate a deep conversation with lots of content
	messages := make([]map[string]string, 20)
	for i := range messages {
		role := "user"
		if i%2 == 1 {
			role = "assistant"
		}
		messages[i] = map[string]string{
			"role":    role,
			"content": strings.Repeat("This is a detailed technical discussion about distributed systems, algorithms, and architecture. ", 8),
		}
	}
	profile := m.Measure(messages)
	if profile.Tier < LoadElevated {
		t.Errorf("long dense conversation should be at least LoadElevated, got %s (total=%.2f)", profile.Tier, profile.TotalLoad)
	}
}

func TestSurgery_NormalNoChange(t *testing.T) {
	m := NewLoadMeter()
	s := NewContextSurgery(m)
	messages := []map[string]string{
		{"role": "user", "content": "Hello"},
		{"role": "assistant", "content": "Hi!"},
	}
	profile := m.Measure(messages)
	trimmed, result := s.Trim(messages, profile)
	if len(trimmed) != len(messages) {
		t.Errorf("normal load should not change message count, got %d (was %d)", len(trimmed), len(messages))
	}
	if result.RemovedMsgs != 0 {
		t.Errorf("expected 0 removed msgs, got %d", result.RemovedMsgs)
	}
}

func TestSurgery_ElevatedRemovesOldAssistant(t *testing.T) {
	m := NewLoadMeter()
	s := NewContextSurgery(m)

	// Build a long conversation that exceeds elevated threshold
	messages := make([]map[string]string, 20)
	for i := range messages {
		role := "user"
		if i%2 == 1 {
			role = "assistant"
		}
		messages[i] = map[string]string{
			"role":    role,
			"content": strings.Repeat("detailed technical architecture discussion with algorithms ", 10),
		}
	}
	profile := m.Measure(messages)
	if profile.Tier < LoadElevated {
		t.Skipf("messages didn't reach elevated load (%.2f) — skip surgery test", profile.TotalLoad)
	}

	trimmed, result := s.Trim(messages, profile)
	if len(trimmed) >= len(messages) {
		t.Errorf("surgery should reduce message count, got %d (was %d)", len(trimmed), len(messages))
	}
	if result.RemovedMsgs == 0 {
		t.Errorf("expected removed msgs > 0, got %d", result.RemovedMsgs)
	}
	// Verify recent messages are preserved
	lastMsg := trimmed[len(trimmed)-1]
	origLastMsg := messages[len(messages)-1]
	if lastMsg["content"] != origLastMsg["content"] {
		t.Error("last message should be preserved after surgery")
	}
}

func TestSurgery_SystemPromptCompressedOnCritical(t *testing.T) {
	m := NewLoadMeter()
	s := NewContextSurgery(m)

	longSystemPrompt := strings.Repeat("You are a sovereign AI with these detailed instructions. ", 60) // ~3000 chars
	messages := []map[string]string{
		{"role": "system", "content": longSystemPrompt},
		{"role": "user", "content": "help"},
	}
	// Force critical tier for test
	profile := LoadProfile{Tier: LoadCritical, TierLabel: "critical", TotalLoad: 2.5}
	trimmed, result := s.Trim(messages, profile)

	systemMsg := trimmed[0]
	if len(systemMsg["content"]) >= len(longSystemPrompt) {
		t.Errorf("system prompt should be compressed on critical load, original=%d new=%d", len(longSystemPrompt), len(systemMsg["content"]))
	}
	if result.CharsRemoved == 0 {
		t.Error("expected chars removed > 0 after system prompt compression")
	}
}

func TestStats_RecordAndQuery(t *testing.T) {
	cs := NewCogLoadStats("/tmp/test_cogload_stats.json")
	m := NewLoadMeter()

	msgs := []map[string]string{{"role": "user", "content": "hello"}}
	profile := m.Measure(msgs)
	cs.Record(profile, nil)

	stats := cs.Stats()
	if measurements, ok := stats["measurements"].(int); !ok || measurements == 0 {
		t.Error("expected at least 1 measurement in stats")
	}
}
