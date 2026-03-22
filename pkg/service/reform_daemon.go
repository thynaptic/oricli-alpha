package service

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/thynaptic/oricli-go/pkg/gosh"
	"github.com/thynaptic/oricli-go/pkg/reform"
)

// --- Pillar 52: Reform Daemon (The Self-Modifier) ---
// Monitors performance bottlenecks and autonomously proposes — and, for non-sensitive
// paths, deploys — code refactors through a multi-stage Code Constitution pipeline.

// deployGate controls whether auto-deploy is enabled. Set to true to allow hot-swap.
const deployGate = true

// rollbackWatchWindow is how long the rollback watchdog monitors the new binary.
const rollbackWatchWindow = 60 * time.Second

// binaryPath is the production binary that gets hot-swapped.
const binaryPath = "bin/oricli-go-v2"

type ReformProposal struct {
	TraceID        string `json:"trace_id"`
	FilePath       string `json:"file_path"`
	OldCode        string `json:"old_code"`
	NewCode        string `json:"new_code"`
	Benefit        string `json:"benefit"`
	Benchmark      string `json:"benchmark_result"`
	IsSensitive    bool   `json:"is_sensitive"`
	AutoDeployed   bool   `json:"auto_deployed"`
	DeployRejected bool   `json:"deploy_rejected"`
	RejectReason   string `json:"reject_reason,omitempty"`
}

type ReformDaemon struct {
	TraceStore *TraceStore
	Metrics    *CodeMetricsService
	Gen        *GenerationService
	WSHub      interface {
		BroadcastEvent(eventType string, payload interface{})
	}

	constitution *reform.CodeConstitution
	verifier     *reform.CodeVerifier
	mu           sync.Mutex
	active       bool
}

func NewReformDaemon(ts *TraceStore, cm *CodeMetricsService, gen *GenerationService, hub interface {
	BroadcastEvent(eventType string, payload interface{})
}) *ReformDaemon {
	return &ReformDaemon{
		TraceStore:   ts,
		Metrics:      cm,
		Gen:          gen,
		WSHub:        hub,
		constitution: reform.NewCodeConstitution(),
		verifier:     reform.NewCodeVerifier(),
	}
}

func (d *ReformDaemon) InjectWSHub(hub interface {
	BroadcastEvent(eventType string, payload interface{})
}) {
	d.WSHub = hub
}

// Run starts the background monitoring loop.
func (d *ReformDaemon) Run(ctx context.Context) {
	d.active = true
	ticker := time.NewTicker(10 * time.Minute)
	defer ticker.Stop()

	log.Println("[ReformDaemon] Self-Modification loop engaged (Code Constitution active).")

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

// PerformAudit scans for bottlenecks and runs the full reform pipeline.
func (d *ReformDaemon) PerformAudit(ctx context.Context) {
	bottlenecks := d.TraceStore.FindBottlenecks(2*time.Second, 0.7)
	if len(bottlenecks) == 0 {
		return
	}
	log.Printf("[ReformDaemon] Detected %d bottlenecks. Running reform pipeline...", len(bottlenecks))

	for _, trace := range bottlenecks {
		targetFile := "pkg/cognition/mcts.go"

		proposal, err := d.GenerateReform(ctx, trace, targetFile)
		if err != nil {
			log.Printf("[ReformDaemon] Reform generation failed for %s: %v", targetFile, err)
			continue
		}

		// Broadcast proposal to UI regardless of deploy outcome
		if d.WSHub != nil {
			d.WSHub.BroadcastEvent("reform_proposal", proposal)
		}

		if proposal.IsSensitive {
			log.Printf("[ReformDaemon] %s is a sensitive path — proposal only, no auto-deploy", targetFile)
			continue
		}

		if !deployGate || proposal.DeployRejected {
			log.Printf("[ReformDaemon] Deploy rejected for %s: %s", targetFile, proposal.RejectReason)
			continue
		}

		if err := d.deploy(ctx, proposal); err != nil {
			log.Printf("[ReformDaemon] Deploy failed for %s: %v", targetFile, err)
		}
	}
}

// GenerateReform drafts, constitutionally validates, and statically verifies a reform proposal.
func (d *ReformDaemon) GenerateReform(ctx context.Context, trace TraceRecord, path string) (*ReformProposal, error) {
	oldCodeBytes, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	oldCode := string(oldCodeBytes)

	// Inject the Code Constitution as the system prompt — governs generation
	constitutionPrompt := d.constitution.GetSystemPrompt()
	prompt := fmt.Sprintf(
		"Analyze this Go file and the following execution trace bottleneck. "+
			"Propose an optimized version following the Code Constitution above.\n\n"+
			"FILE: %s\nBOTTLENECK TRACE:\n%v\n\n"+
			"CURRENT CODE:\n```go\n%s\n```",
		path, trace.TraceGraph, oldCode,
	)

	res, err := d.Gen.Generate(prompt, map[string]interface{}{
		"system": constitutionPrompt,
		"model":  "qwen2.5-coder:3b",
	})
	if err != nil {
		return nil, err
	}
	newCode, _ := res["text"].(string)
	newCode = stripMarkdownFences(newCode)

	proposal := &ReformProposal{
		TraceID:     trace.TraceID,
		FilePath:    path,
		OldCode:     oldCode,
		NewCode:     newCode,
		IsSensitive: reform.IsSensitivePath(path),
	}

	// Four-stage Code Verifier gate
	result := d.verifier.Verify(newCode, path)
	proposal.Benchmark = fmt.Sprintf("Stage: %s | Passed: %v", result.Stage, result.Passed)
	if !result.Passed {
		proposal.DeployRejected = true
		proposal.RejectReason = fmt.Sprintf("verification failed at %s: %s", result.Stage, strings.Join(result.Failures, "; "))
		log.Printf("[ReformDaemon] Code Constitution rejected proposal for %s: %s", path, proposal.RejectReason)
		return proposal, nil
	}

	// Gosh sandbox sanity check (secondary, non-blocking on pass)
	session, _ := gosh.NewOverlaySession(".")
	if sandboxErr := session.RegisterTool("compile_test", newCode); sandboxErr != nil {
		proposal.Benchmark += " | Sandbox: WARN: " + sandboxErr.Error()
	} else {
		proposal.Benchmark += " | Sandbox: OK"
	}

	log.Printf("[ReformDaemon] Proposal for %s passed all verification gates", path)
	return proposal, nil
}

// deploy writes the patched file, rebuilds the binary, restarts the service,
// and watches for regressions with a 60-second rollback window.
func (d *ReformDaemon) deploy(ctx context.Context, proposal *ReformProposal) error {
	log.Printf("[ReformDaemon] Deploying reform to %s", proposal.FilePath)

	// Backup current file
	backupPath := proposal.FilePath + ".reform-backup"
	if err := copyFile(proposal.FilePath, backupPath); err != nil {
		return fmt.Errorf("backup failed: %w", err)
	}

	// Backup current binary
	binaryBackup := binaryPath + ".reform-backup"
	if err := copyFile(binaryPath, binaryBackup); err != nil {
		// Non-fatal — file may not exist yet
		log.Printf("[ReformDaemon] Binary backup skipped: %v", err)
	}

	// Write proposed code
	if err := os.WriteFile(proposal.FilePath, []byte(proposal.NewCode), 0644); err != nil {
		return fmt.Errorf("write failed: %w", err)
	}

	// Candidate build
	candidatePath := binaryPath + ".candidate"
	buildCmd := exec.CommandContext(ctx, "go", "build", "-o", candidatePath, "./cmd/backbone/")
	buildCmd.Dir = repoRoot()
	buildOut, err := buildCmd.CombinedOutput()
	if err != nil {
		// Build failed — restore source file immediately
		_ = copyFile(backupPath, proposal.FilePath)
		return fmt.Errorf("candidate build failed: %s", string(buildOut))
	}

	// Run tests against candidate
	testCmd := exec.CommandContext(ctx, "go", "test", "./pkg/...")
	testCmd.Dir = repoRoot()
	testOut, err := testCmd.CombinedOutput()
	if err != nil {
		_ = copyFile(backupPath, proposal.FilePath)
		_ = os.Remove(candidatePath)
		return fmt.Errorf("tests failed: %s", string(testOut))
	}

	// Atomic promote: rename candidate → production binary
	if err := os.Rename(candidatePath, binaryPath); err != nil {
		_ = copyFile(backupPath, proposal.FilePath)
		return fmt.Errorf("binary promotion failed: %w", err)
	}

	// Restart service
	restartCmd := exec.Command("systemctl", "restart", "oricli-backbone")
	if err := restartCmd.Run(); err != nil {
		return fmt.Errorf("systemctl restart failed: %w", err)
	}

	proposal.AutoDeployed = true
	log.Printf("[ReformDaemon] Reform deployed to %s — rollback watchdog active for %s", proposal.FilePath, rollbackWatchWindow)

	// Rollback watchdog — monitors health after restart
	go d.watchAndRollback(proposal.FilePath, backupPath, binaryBackup)
	return nil
}

// watchAndRollback monitors the service after a hot-swap and restores backups if unhealthy.
func (d *ReformDaemon) watchAndRollback(filePath, backupFile, binaryBackup string) {
	time.Sleep(rollbackWatchWindow)

	// Check service is still running
	out, err := exec.Command("systemctl", "is-active", "oricli-backbone").Output()
	if err != nil || strings.TrimSpace(string(out)) != "active" {
		log.Printf("[ReformDaemon] ROLLBACK triggered — service not active after hot-swap")
		_ = copyFile(backupFile, filePath)
		if binaryBackup != "" {
			_ = copyFile(binaryBackup, binaryPath)
		}
		_ = exec.Command("systemctl", "restart", "oricli-backbone").Run()
		if d.WSHub != nil {
			d.WSHub.BroadcastEvent("reform_rollback", map[string]string{
				"file":   filePath,
				"reason": "service not active after rollback window",
			})
		}
		return
	}
	log.Printf("[ReformDaemon] Hot-swap stable — cleaning up backups for %s", filePath)
	_ = os.Remove(backupFile)
	_ = os.Remove(binaryBackup)
}

// stripMarkdownFences removes ```go ... ``` wrappers from LLM output.
func stripMarkdownFences(s string) string {
	s = strings.TrimSpace(s)
	if strings.HasPrefix(s, "```go") {
		s = strings.TrimPrefix(s, "```go")
	} else if strings.HasPrefix(s, "```") {
		s = strings.TrimPrefix(s, "```")
	}
	s = strings.TrimSuffix(s, "```")
	return strings.TrimSpace(s)
}

func copyFile(src, dst string) error {
	data, err := os.ReadFile(src)
	if err != nil {
		return err
	}
	return os.WriteFile(dst, data, 0755)
}

func repoRoot() string {
	// Walk up from the binary location to find go.mod
	dir, _ := filepath.Abs(".")
	for {
		if _, err := os.Stat(filepath.Join(dir, "go.mod")); err == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return "."
}
