package memory_test

import (
	"path/filepath"
	"testing"
	"time"

	"github.com/thynaptic/ori-capsule/internal/memory"
)

func TestBridgeRoundTrip(t *testing.T) {
	dir := t.TempDir()
	b, err := memory.OpenBridge(dir, "")
	if err != nil {
		t.Fatal(err)
	}
	defer b.Close()
	if err := b.Put(memory.CatEpisodic, "e1", map[string]any{"text": "hello"}, nil); err != nil {
		t.Fatal(err)
	}
	rec, err := b.Get(memory.CatEpisodic, "e1")
	if err != nil || rec == nil {
		t.Fatalf("get: %v %#v", err, rec)
	}
	if rec.Data["text"] != "hello" {
		t.Fatalf("data=%v", rec.Data)
	}
}

func TestSessionAppendAndMerge(t *testing.T) {
	dir := t.TempDir()
	b, err := memory.OpenBridge(dir, "")
	if err != nil {
		t.Fatal(err)
	}
	defer b.Close()
	ss := memory.NewSessionStore(b, 10)
	if err := ss.Append("s1",
		memory.Turn{Role: "user", Content: "hi"},
		memory.Turn{Role: "assistant", Content: "hello"},
	); err != nil {
		t.Fatal(err)
	}
	turns, err := ss.Load("s1")
	if err != nil || len(turns) != 2 {
		t.Fatalf("load=%v n=%d", err, len(turns))
	}
	incoming := []struct{ Role, Content string }{{"user", "again"}}
	merged := memory.MergeForRequest(turns, incoming, 24)
	if len(merged) != 3 {
		t.Fatalf("merged len=%d", len(merged))
	}
	// Fat history from client should not double
	fat := []struct{ Role, Content string }{
		{"user", "a"}, {"assistant", "b"}, {"user", "c"},
	}
	if n := len(memory.MergeForRequest(turns, fat, 24)); n != 3 {
		t.Fatalf("fat merge=%d", n)
	}
}

func TestRuntimePrepareAndAfter(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "mem")
	rt, err := memory.Open(memory.OpenOptions{Dir: dir, MaxSessionTurns: 12})
	if err != nil {
		t.Fatal(err)
	}
	defer rt.Close()

	expanded, extras, hit := rt.PrepareChat("sess-1", []memory.ChatMessage{
		{Role: "user", Content: "I want to build a golang api"},
	})
	if len(expanded) != 1 {
		t.Fatalf("expanded=%d", len(expanded))
	}
	if hit != "" {
		t.Fatal("unexpected cache hit")
	}
	if extras == "" {
		t.Fatal("expected belief/temporal extras")
	}
	rt.AfterReply("sess-1", "I want to build a golang api", "Sure — let's sketch routes.")
	deadline := time.Now().Add(2 * time.Second)
	for {
		turns, _ := rt.Sessions.Load("sess-1")
		if len(turns) >= 2 && rt.Chronos.Len() > 0 {
			break
		}
		if time.Now().After(deadline) {
			t.Fatalf("session/chronos not persisted (turns=%d chronos=%d)", len(turns), rt.Chronos.Len())
		}
		time.Sleep(10 * time.Millisecond)
	}
	if rt.Graph.NodeCount() == 0 {
		t.Fatal("graph empty")
	}
}

func TestTasksAndSpaces(t *testing.T) {
	dir := t.TempDir()
	rt, err := memory.Open(memory.OpenOptions{Dir: dir})
	if err != nil {
		t.Fatal(err)
	}
	defer rt.Close()
	sp := rt.Spaces.Upsert("home", "Home")
	if sp.ID != "home" {
		t.Fatal(sp)
	}
	task, err := rt.Tasks.Add("buy milk")
	if err != nil || task.Title != "buy milk" {
		t.Fatalf("%v %#v", err, task)
	}
	if err := rt.Tasks.SetDone(task.ID, true); err != nil {
		t.Fatal(err)
	}
}
