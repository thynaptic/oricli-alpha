package audit

import (
	"context"
	"fmt"
	"log"
	"os"
	"sync"
	"time"
)

// ---------------------------------------------------------------------------
// AuditRun — state of a single audit execution
// ---------------------------------------------------------------------------

// AuditRunStatus represents the lifecycle state of an audit run.
type AuditRunStatus string

const (
	RunStatusPending  AuditRunStatus = "pending"
	RunStatusScanning AuditRunStatus = "scanning"
	RunStatusVerifying AuditRunStatus = "verifying"
	RunStatusRaising  AuditRunStatus = "raising_prs"
	RunStatusDone     AuditRunStatus = "done"
	RunStatusError    AuditRunStatus = "error"
)

// AuditRun tracks a single audit execution from scan to PR creation.
type AuditRun struct {
	ID              string         `json:"id"`
	Status          AuditRunStatus `json:"status"`
	Scope           []string       `json:"scope"`
	StartedAt       time.Time      `json:"started_at"`
	CompletedAt     time.Time      `json:"completed_at,omitempty"`
	TotalFindings   int            `json:"total_findings"`
	VerifiedCount   int            `json:"verified_count"`
	PRsOpened       int            `json:"prs_opened"`
	PRURLs          []string       `json:"pr_urls,omitempty"`
	Error           string         `json:"error,omitempty"`
	Findings        []Finding      `json:"findings,omitempty"`
}

// ---------------------------------------------------------------------------
// AuditDaemon
// ---------------------------------------------------------------------------

// AuditDaemon orchestrates scheduled and on-demand audit runs.
type AuditDaemon struct {
	scanner  *AuditScanner
	verifier *Verifier
	bot      *GitHubBot
	interval time.Duration

	mu      sync.RWMutex
	runs    map[string]*AuditRun
	trigger chan struct{}
}

// NewAuditDaemon creates an AuditDaemon.
func NewAuditDaemon(llm LLMCaller, githubReadToken, botToken string) *AuditDaemon {
	interval := 168 * time.Hour // weekly default
	if v := os.Getenv("ORICLI_AUDIT_INTERVAL"); v != "" {
		if d, err := time.ParseDuration(v); err == nil {
			interval = d
		}
	}
	return &AuditDaemon{
		scanner:  NewAuditScanner(llm, githubReadToken),
		verifier: NewVerifier(llm),
		bot:      NewGitHubBot(botToken),
		interval: interval,
		runs:     make(map[string]*AuditRun),
		trigger:  make(chan struct{}, 1),
	}
}

// StartDaemon launches the background scheduler goroutine.
func (d *AuditDaemon) StartDaemon(ctx context.Context) {
	log.Printf("[Audit] Daemon started — scheduled interval: %s", d.interval)
	go func() {
		ticker := time.NewTicker(d.interval)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				d.runAudit(ctx, []string{"pkg"})
			case <-d.trigger:
				d.runAudit(ctx, []string{"pkg"})
			}
		}
	}()
}

// Trigger queues an on-demand audit run for the given scope.
// Returns the run ID immediately; the run executes asynchronously.
func (d *AuditDaemon) Trigger(ctx context.Context, scope []string) string {
	if len(scope) == 0 {
		scope = []string{"pkg"}
	}
	runID := fmt.Sprintf("audit-%d", time.Now().UnixMilli())
	run := &AuditRun{
		ID:        runID,
		Status:    RunStatusPending,
		Scope:     scope,
		StartedAt: time.Now(),
	}
	d.mu.Lock()
	d.runs[runID] = run
	d.mu.Unlock()

	go d.executeRun(ctx, run)
	return runID
}

// GetRun returns the AuditRun for the given ID, or nil if not found.
func (d *AuditDaemon) GetRun(id string) *AuditRun {
	d.mu.RLock()
	defer d.mu.RUnlock()
	r := d.runs[id]
	if r == nil {
		return nil
	}
	copy := *r
	return &copy
}

// ListRuns returns all audit runs sorted newest first (max 50).
func (d *AuditDaemon) ListRuns() []AuditRun {
	d.mu.RLock()
	defer d.mu.RUnlock()
	runs := make([]AuditRun, 0, len(d.runs))
	for _, r := range d.runs {
		runs = append(runs, *r)
	}
	// Simple reverse sort by StartedAt
	for i := 0; i < len(runs)-1; i++ {
		for j := i + 1; j < len(runs); j++ {
			if runs[j].StartedAt.After(runs[i].StartedAt) {
				runs[i], runs[j] = runs[j], runs[i]
			}
		}
	}
	if len(runs) > 50 {
		runs = runs[:50]
	}
	return runs
}

// ---------------------------------------------------------------------------
// Internal execution
// ---------------------------------------------------------------------------

func (d *AuditDaemon) runAudit(ctx context.Context, scope []string) {
	runID := fmt.Sprintf("audit-%d", time.Now().UnixMilli())
	run := &AuditRun{
		ID:        runID,
		Status:    RunStatusPending,
		Scope:     scope,
		StartedAt: time.Now(),
	}
	d.mu.Lock()
	d.runs[runID] = run
	d.mu.Unlock()
	d.executeRun(ctx, run)
}

func (d *AuditDaemon) executeRun(ctx context.Context, run *AuditRun) {
	log.Printf("[Audit] Run %s started — scope: %v", run.ID, run.Scope)

	d.setStatus(run, RunStatusScanning)

	// 1. Scan
	findings, err := d.scanner.Scan(ctx, run.ID, run.Scope)
	if err != nil && len(findings) == 0 {
		d.failRun(run, fmt.Sprintf("scan error: %v", err))
		return
	}

	d.mu.Lock()
	run.TotalFindings = len(findings)
	run.Findings = findings
	d.mu.Unlock()
	log.Printf("[Audit] Run %s — %d findings, starting verification", run.ID, len(findings))

	// 2. Verify — only HIGH and CRITICAL
	d.setStatus(run, RunStatusVerifying)
	var verified []struct {
		Finding Finding
		Result  VerifyResult
	}
	for _, f := range findings {
		if f.Severity != SeverityHigh && f.Severity != SeverityCritical {
			continue
		}
		vr := d.verifier.Verify(ctx, f)
		if vr.Verified {
			f.Verified = true
			verified = append(verified, struct {
				Finding Finding
				Result  VerifyResult
			}{f, vr})
		}
	}

	d.mu.Lock()
	run.VerifiedCount = len(verified)
	d.mu.Unlock()
	log.Printf("[Audit] Run %s — %d verified findings, raising PRs", run.ID, len(verified))

	// 3. Raise PRs for verified findings
	d.setStatus(run, RunStatusRaising)
	var prURLs []string
	for _, v := range verified {
		prURL, err := d.bot.RaisePR(ctx, v.Finding, v.Result)
		if err != nil {
			log.Printf("[Audit] RaisePR failed for %s: %v", v.Finding.ID, err)
			continue
		}
		v.Finding.PRUrl = prURL
		prURLs = append(prURLs, prURL)
	}

	d.mu.Lock()
	run.PRsOpened = len(prURLs)
	run.PRURLs = prURLs
	run.Status = RunStatusDone
	run.CompletedAt = time.Now()
	d.mu.Unlock()

	log.Printf("[Audit] Run %s complete — findings=%d verified=%d prs=%d",
		run.ID, run.TotalFindings, run.VerifiedCount, run.PRsOpened)
}

func (d *AuditDaemon) setStatus(run *AuditRun, status AuditRunStatus) {
	d.mu.Lock()
	run.Status = status
	d.mu.Unlock()
}

func (d *AuditDaemon) failRun(run *AuditRun, errMsg string) {
	d.mu.Lock()
	run.Status = RunStatusError
	run.Error = errMsg
	run.CompletedAt = time.Now()
	d.mu.Unlock()
	log.Printf("[Audit] Run %s failed: %s", run.ID, errMsg)
}
