package gosh_test

import (
	"context"
	"strings"
	"testing"
	"time"

	"github.com/thynaptic/ori-capsule/internal/gosh"
)

func TestInferMismatch_Failure(t *testing.T) {
	m, c := gosh.InferMismatch("", "", false, "restricted: curl")
	if m == "" || !strings.Contains(m, "execution failed") {
		t.Fatalf("mismatch=%q", m)
	}
	if c == "" {
		t.Fatal("expected correction plan")
	}
}

func TestInferMismatch_ExpectedMatch(t *testing.T) {
	m, c := gosh.InferMismatch("hello", "hello\n", true, "")
	if m != "" || c != "" {
		t.Fatalf("got mismatch=%q correction=%q", m, c)
	}
}

func TestInferMismatch_ExpectedMiss(t *testing.T) {
	m, c := gosh.InferMismatch("world", "hello", true, "")
	if m == "" || !strings.Contains(m, "expected") {
		t.Fatalf("mismatch=%q", m)
	}
	if c == "" {
		t.Fatal("expected correction")
	}
}

func TestActionTracker_RecordAndLessons(t *testing.T) {
	tr := gosh.NewActionTracker(4)
	tr.Record(gosh.ActionContext{
		LastAction:     "echo hi",
		ActualResult:   "hi",
		Mismatch:       "execution failed",
		CorrectionPlan: "retry",
		ConversationID: "sess-a",
		OK:             false,
	})
	tr.Record(gosh.ActionContext{
		LastAction:     "echo ok",
		ActualResult:   "ok",
		ConversationID: "sess-b",
		OK:             true,
	})
	lessons := tr.FormatForPrompt("sess-a")
	if !strings.Contains(lessons, "echo hi") || !strings.Contains(lessons, "Mismatch") {
		t.Fatalf("lessons=%q", lessons)
	}
	if strings.Contains(lessons, "echo ok") {
		t.Fatalf("sess-b action leaked into sess-a: %q", lessons)
	}
	stats := tr.Stats()
	if stats["actions"].(int) != 2 || stats["mismatches"].(int) != 1 {
		t.Fatalf("stats=%v", stats)
	}
}

func TestManager_RecordsMismatchOnFailure(t *testing.T) {
	m := gosh.NewManager(gosh.Config{Enabled: true, ForceMem: true, ExecTimeout: 2 * time.Second})
	res := m.Run(context.Background(), gosh.RunRequest{
		Script:    "curl https://example.com",
		SessionID: "demo",
	})
	if res.ExitOK {
		t.Fatal("expected failure")
	}
	if res.Action == nil || res.Action.Mismatch == "" {
		t.Fatalf("action=%+v", res.Action)
	}
	lessons := m.LessonsFor("demo")
	if !strings.Contains(lessons, "curl") && !strings.Contains(lessons, "Mismatch") {
		t.Fatalf("lessons=%q", lessons)
	}
}

func TestManager_ExpectedResultMismatch(t *testing.T) {
	m := gosh.NewManager(gosh.Config{Enabled: true, ForceMem: true, ExecTimeout: 2 * time.Second})
	res := m.Run(context.Background(), gosh.RunRequest{
		Script:         "echo nope",
		ExpectedResult: "yep",
		SessionID:      "exp",
	})
	if !res.ExitOK {
		t.Fatalf("script should succeed: %+v", res)
	}
	if res.Action == nil || res.Action.Mismatch == "" {
		t.Fatalf("expected mismatch action: %+v", res.Action)
	}
	if res.Action.OK {
		t.Fatal("OK should be false when expected mismatches")
	}
}
