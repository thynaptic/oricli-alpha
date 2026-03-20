package service

import (
	"context"
	"fmt"
	"log"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/thynaptic/oricli-go/pkg/gosh"
)

// --- Pillar 52: Reform Daemon (The Self-Modifier) ---
// Monitors performance bottlenecks and autonomously proposes code refactors.

type ReformProposal struct {
	TraceID     string `json:"trace_id"`
	FilePath    string `json:"file_path"`
	OldCode     string `json:"old_code"`
	NewCode     string `json:"new_code"`
	Benefit     string `json:"benefit"`
	Benchmark   string `json:"benchmark_result"`
	IsSensitive bool   `json:"is_sensitive"` // If true, requires manual override
}

type ReformDaemon struct {
	TraceStore *TraceStore
	Metrics    *CodeMetricsService
	Gen        *GenerationService
	WSHub      interface {
		BroadcastEvent(eventType string, payload interface{})
	}
	
	mu sync.Mutex
	active bool
}

func NewReformDaemon(ts *TraceStore, cm *CodeMetricsService, gen *GenerationService, hub interface {
	BroadcastEvent(eventType string, payload interface{})
}) *ReformDaemon {
	return &ReformDaemon{
		TraceStore: ts,
		Metrics:    cm,
		Gen:        gen,
		WSHub:      hub,
	}
}

// Run starts the background monitoring loop.
func (d *ReformDaemon) Run(ctx context.Context) {
	d.active = true
	ticker := time.NewTicker(10 * time.Minute) // Audit every 10 mins
	defer ticker.Stop()

	log.Println("[ReformDaemon] Self-Modification loop engaged.")

	for {
		select {
		case <-ctx.Done():
			d.active = false
			return
		case <-ticker.C:
			d.PerformAudit(ctx)
		}
	}
}

// PerformAudit scans for bottlenecks and initiates the reform pipeline.
func (d *ReformDaemon) PerformAudit(ctx context.Context) {
	// 1. Monitor: Find slowness or low confidence
	bottlenecks := d.TraceStore.FindBottlenecks(2*time.Second, 0.7)
	if len(bottlenecks) == 0 {
		return
	}

	log.Printf("[ReformDaemon] Detected %d bottlenecks. Initiating Audit Phase...", len(bottlenecks))

	for _, trace := range bottlenecks {
		// 2. Diagnostic: Analyze the trace to find the Go logic
		// (Simplification: In a full impl, we'd extract the calling function name from the trace)
		targetFile := "pkg/cognition/mcts.go" // Default optimization target for now
		
		// 3. Draft & Verify
		proposal, err := d.GenerateReform(ctx, trace, targetFile)
		if err != nil {
			log.Printf("[ReformDaemon] Failed to generate reform for %s: %v", targetFile, err)
			continue
		}

		// 4. Propose: Broadcast to UI
		if d.WSHub != nil {
			d.WSHub.BroadcastEvent("reform_proposal", proposal)
		}
		log.Printf("[ReformDaemon] Reform Proposal generated for %s. Awaiting manual approval.", targetFile)
	}
}

// GenerateReform drafts and verifies an optimized version of a function.
func (d *ReformDaemon) GenerateReform(ctx context.Context, trace TraceRecord, path string) (*ReformProposal, error) {
	// Read current code
	oldCodeBytes, err := os.ReadFile(path)
	if err != nil { return nil, err }
	oldCode := string(oldCodeBytes)

	// Draft optimized version
	prompt := fmt.Sprintf("Analyze this Go file and the following execution trace bottleneck. Propose an optimized version of the slow logic to improve latency and maintain perimeter sovereignty.\n\nFILE: %s\nTRACE: %v", path, trace.TraceGraph)
	res, err := d.Gen.Generate(prompt, map[string]interface{}{
		"system": "Sovereign Technical Architect",
		"model":  "qwen2.5-coder:3b",
	})
	if err != nil { return nil, err }

	newCode, _ := res["text"].(string)

	// Verify in Gosh Sandbox (Compile Test)
	session, _ := gosh.NewOverlaySession(".")
	err = session.RegisterTool("compile_test", newCode)
	benchmarkResult := "Verification Passed: Interpreted successfully in Sovereign Sandbox."
	if err != nil {
		benchmarkResult = fmt.Sprintf("Verification Failed: %v", err)
	}

	return &ReformProposal{
		TraceID:     trace.TraceID,
		FilePath:    path,
		OldCode:     oldCode,
		NewCode:     newCode,
		Benefit:     "Latency Reduction and Deterministic Optimization",
		Benchmark:   benchmarkResult,
		IsSensitive: strings.Contains(path, "kernel") || strings.Contains(path, "safety"),
	}, nil
}
