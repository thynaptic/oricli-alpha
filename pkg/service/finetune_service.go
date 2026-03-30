package service

// FineTuneService wraps the FineTuneOrchestrator for async job management.
// A single job runs at a time — concurrent fine-tune runs are rejected.
//
// Env:
//   ORICLI_FINETUNE_ENABLED=true  — enables the service (default: false)

import (
	"context"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/thynaptic/oricli-go/pkg/finetune"
	"github.com/thynaptic/oricli-go/pkg/training"
)

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

// JobState is the lifecycle state of a fine-tune job.
type JobState string

const (
	JobQueued    JobState = "queued"
	JobRunning   JobState = "running"
	JobDone      JobState = "done"
	JobFailed    JobState = "failed"
)

// FineTuneStatus is the full status of a job returned by GetStatus.
type FineTuneStatus struct {
	JobID      string              `json:"job_id"`
	State      JobState            `json:"state"`
	Step       finetune.StepName   `json:"step"`
	Progress   int                 `json:"progress"`
	Message    string              `json:"message"`
	GGUFPath   string              `json:"gguf_path,omitempty"`
	PodID      string              `json:"pod_id,omitempty"`
	DurationMs int64               `json:"duration_ms,omitempty"`
	Error      string              `json:"error,omitempty"`
	StartedAt  time.Time           `json:"started_at"`
	UpdatedAt  time.Time           `json:"updated_at"`
}

// ─────────────────────────────────────────────────────────────────────────────
// FineTuneService
// ─────────────────────────────────────────────────────────────────────────────

// FineTuneService manages async fine-tuning jobs.
type FineTuneService struct {
	Orchestrator *finetune.FineTuneOrchestrator
	Enabled      bool

	mu      sync.RWMutex
	jobs    map[string]*FineTuneStatus
	current string // job ID of running job, "" if idle
}

// NewFineTuneService wires all components together.
func NewFineTuneService(repoRoot string) *FineTuneService {
	enabled := os.Getenv("ORICLI_FINETUNE_ENABLED") == "true"

	pods := finetune.NewPodClient("")
	dataGen := training.NewDatasetGenerator(nil)
	orch := finetune.NewOrchestrator(pods, dataGen, repoRoot)

	return &FineTuneService{
		Orchestrator: orch,
		Enabled:      enabled,
		jobs:         make(map[string]*FineTuneStatus),
	}
}

// RunAsync starts a fine-tuning job in the background and returns the job ID.
// Returns error if another job is already running or service is disabled.
func (s *FineTuneService) RunAsync(cfg finetune.RunConfig) (string, error) {
	if !s.Enabled {
		return "", fmt.Errorf("fine-tuning disabled — set ORICLI_FINETUNE_ENABLED=true")
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if s.current != "" {
		return "", fmt.Errorf("a fine-tune job is already running: %s", s.current)
	}

	jobID := uuid.New().String()
	status := &FineTuneStatus{
		JobID:     jobID,
		State:     JobQueued,
		StartedAt: time.Now().UTC(),
		UpdatedAt: time.Now().UTC(),
	}
	s.jobs[jobID] = status
	s.current = jobID

	go s.runJob(jobID, cfg)

	log.Printf("[FineTune] job %s queued", jobID[:8])
	return jobID, nil
}

// GetStatus returns the current status of a job.
func (s *FineTuneService) GetStatus(jobID string) (*FineTuneStatus, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	status, ok := s.jobs[jobID]
	if !ok {
		return nil, false
	}
	// Return a copy
	cp := *status
	return &cp, true
}

// ListJobs returns all jobs (most recent first, capped at 20).
func (s *FineTuneService) ListJobs() []*FineTuneStatus {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]*FineTuneStatus, 0, len(s.jobs))
	for _, j := range s.jobs {
		cp := *j
		out = append(out, &cp)
	}
	return out
}

// ─────────────────────────────────────────────────────────────────────────────
// Internal
// ─────────────────────────────────────────────────────────────────────────────

func (s *FineTuneService) runJob(jobID string, cfg finetune.RunConfig) {
	defer func() {
		s.mu.Lock()
		s.current = ""
		s.mu.Unlock()
	}()

	s.updateStatus(jobID, func(st *FineTuneStatus) {
		st.State = JobRunning
	})

	ctx := context.Background()
	progress, results := s.Orchestrator.Run(ctx, cfg)

	// Drain progress events — update status for each
	go func() {
		for ev := range progress {
			s.updateStatus(jobID, func(st *FineTuneStatus) {
				st.Step = ev.Step
				st.Progress = ev.PctDone
				st.Message = ev.Message
				if ev.Error != nil {
					st.Message = ev.Error.Error()
				}
			})
		}
	}()

	// Wait for final result
	result := <-results

	s.updateStatus(jobID, func(st *FineTuneStatus) {
		st.DurationMs = result.DurationMs
		st.PodID = result.PodID
		if result.Error != nil {
			st.State = JobFailed
			st.Error = result.Error.Error()
			st.Step = "failed"
			log.Printf("[FineTune] job %s FAILED: %v", jobID[:8], result.Error)
		} else {
			st.State = JobDone
			st.GGUFPath = result.GGUFPath
			st.Progress = 100
			st.Step = finetune.StepDone
			log.Printf("[FineTune] job %s DONE — GGUF: %s (%dms)", jobID[:8], result.GGUFPath, result.DurationMs)
			s.signalRestart(result.GGUFPath)
		}
	})
}

func (s *FineTuneService) updateStatus(jobID string, fn func(*FineTuneStatus)) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if st, ok := s.jobs[jobID]; ok {
		fn(st)
		st.UpdatedAt = time.Now().UTC()
	}
}

// signalRestart logs the new model path — the swap_ollama_model.sh was already
// called by the orchestrator. We just need to restart the server.
func (s *FineTuneService) signalRestart(ggufPath string) {
	log.Printf("[FineTune] new model at %s — server restart required to activate", filepath.Base(ggufPath))
	// Write a restart-needed sentinel file — the server operator / systemd watchdog picks it up
	sentinel := filepath.Join(filepath.Dir(ggufPath), ".finetune_restart_needed")
	_ = os.WriteFile(sentinel, []byte(ggufPath+"\n"), 0644)
}
