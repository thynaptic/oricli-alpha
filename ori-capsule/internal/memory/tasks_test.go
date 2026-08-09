package memory_test

import (
	"testing"

	"github.com/thynaptic/ori-capsule/internal/memory"
)

func TestTaskDAG_ReadySteps(t *testing.T) {
	store, err := memory.OpenTaskStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	defer store.Close()

	task, err := store.AddFull("ship", "demo", 1, []memory.StepInput{
		{ID: "a", Title: "prep", OrderNum: 1},
		{ID: "b", Title: "build", OrderNum: 2, DependsOn: []string{"a"}},
		{ID: "c", Title: "ship", OrderNum: 3, DependsOn: []string{"b"}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(task.Steps) != 3 || task.Status != memory.StatusPending {
		t.Fatalf("%+v", task)
	}
	ready, err := store.ReadySteps(task.ID)
	if err != nil || len(ready) != 1 || ready[0].ID != "a" {
		t.Fatalf("ready=%+v err=%v", ready, err)
	}
	if _, err := store.SetStepStatus(task.ID, "a", memory.StatusDone, "ok"); err != nil {
		t.Fatal(err)
	}
	ready, _ = store.ReadySteps(task.ID)
	if len(ready) != 1 || ready[0].ID != "b" {
		t.Fatalf("ready after a=%+v", ready)
	}
	_, _ = store.SetStepStatus(task.ID, "b", memory.StatusDone, "")
	_, _ = store.SetStepStatus(task.ID, "c", memory.StatusDone, "")
	got, _ := store.Get(task.ID, true)
	if got.Status != memory.StatusDone || !got.Done {
		t.Fatalf("rollup=%+v", got)
	}
}
