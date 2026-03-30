// Package audit implements the Self-Audit Loop — Oricli's ability to read her
// own source code, identify issues via LLM analysis, verify them with Gosh
// (Yaegi interpreter), and raise GitHub PRs as oricli-bot for confirmed findings.
//
// Flow:
//  1. AuditScanner reads .go files from thynaptic/oricli-go via GitHub API
//  2. Each file is chunked and sent to the LLM with a structured audit prompt
//  3. Findings are parsed: {file, line, description, severity}
//  4. Verifier writes a minimal Gosh snippet and runs it in a sandboxed session
//  5. Only verified HIGH/CRITICAL findings proceed to GitHubBot
//  6. GitHubBot creates branch + commits repro test + markdown report + opens PR
package audit

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"time"
)

// ---------------------------------------------------------------------------
// Finding — a single issue discovered during an audit scan
// ---------------------------------------------------------------------------

// Severity represents how critical a finding is.
type Severity string

const (
	SeverityLow      Severity = "LOW"
	SeverityMedium   Severity = "MEDIUM"
	SeverityHigh     Severity = "HIGH"
	SeverityCritical Severity = "CRITICAL"
)

// Finding represents a potential issue identified by the LLM auditor.
type Finding struct {
	ID          string    `json:"id"`
	AuditRunID  string    `json:"audit_run_id"`
	File        string    `json:"file"`        // e.g. "pkg/goal/executor.go"
	LineHint    int       `json:"line_hint"`   // approximate line (LLM best guess)
	Description string    `json:"description"` // human-readable issue summary
	Category    string    `json:"category"`    // bug | security | logic | performance | dead_code
	Severity    Severity  `json:"severity"`
	CodeSnippet string    `json:"code_snippet"` // relevant excerpt from the file
	Verified    bool      `json:"verified"`
	PRUrl       string    `json:"pr_url,omitempty"`
	FoundAt     time.Time `json:"found_at"`
}

// Slug returns a URL-safe identifier for a finding.
func (f *Finding) Slug() string {
	desc := strings.ToLower(f.Description)
	// Keep only alphanum and spaces, truncate, replace spaces with dashes
	var b strings.Builder
	for _, r := range desc {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == ' ' {
			b.WriteRune(r)
		}
	}
	words := strings.Fields(b.String())
	if len(words) > 5 {
		words = words[:5]
	}
	return strings.Join(words, "-")
}

// ---------------------------------------------------------------------------
// LLM caller interface — avoids import cycle with service package
// ---------------------------------------------------------------------------

// LLMCaller is a function that makes a single blocking LLM call.
// Matches service.GenerationService.DirectOllamaSingle signature.
type LLMCaller func(ctx context.Context, messages []map[string]string) (string, error)

// ---------------------------------------------------------------------------
// AuditScanner
// ---------------------------------------------------------------------------

// AuditScanner reads source files from the oricli-go repo and uses the LLM
// to identify potential issues in each file.
type AuditScanner struct {
	llm        LLMCaller
	httpClient interface {
		fetchFileList(ctx context.Context, path string) ([]repoFile, error)
		fetchFileContent(ctx context.Context, downloadURL string) (string, error)
	}
	repoOwner string
	repoName  string
	token     string
}

// NewAuditScanner creates an AuditScanner targeting thynaptic/oricli-go.
func NewAuditScanner(llm LLMCaller, token string) *AuditScanner {
	return &AuditScanner{
		llm:       llm,
		repoOwner: "thynaptic",
		repoName:  "oricli-go",
		token:     token,
		httpClient: newGitHubFileClient(token),
	}
}

// Scan audits the given package paths (e.g. ["pkg/goal", "pkg/pad"]).
// If scope is empty, scans the full pkg/ directory tree.
func (s *AuditScanner) Scan(ctx context.Context, runID string, scope []string) ([]Finding, error) {
	if len(scope) == 0 {
		scope = []string{"pkg"}
	}

	var allFiles []repoFile
	for _, dir := range scope {
		files, err := s.httpClient.fetchFileList(ctx, dir)
		if err != nil {
			log.Printf("[Audit] fetchFileList(%s): %v", dir, err)
			continue
		}
		allFiles = append(allFiles, files...)
	}

	// Filter to .go files only, skip test files and generated files
	var goFiles []repoFile
	for _, f := range allFiles {
		if strings.HasSuffix(f.Name, ".go") &&
			!strings.HasSuffix(f.Name, "_test.go") &&
			!strings.Contains(f.Path, "vendor/") {
			goFiles = append(goFiles, f)
		}
	}
	log.Printf("[Audit] %s — scanning %d Go source files", runID, len(goFiles))

	var findings []Finding
	for i, f := range goFiles {
		select {
		case <-ctx.Done():
			return findings, ctx.Err()
		default:
		}

		content, err := s.httpClient.fetchFileContent(ctx, f.DownloadURL)
		if err != nil {
			log.Printf("[Audit] fetchFileContent(%s): %v", f.Path, err)
			continue
		}

		// Chunk large files — LLM context limit
		chunks := chunkSource(content, 3000)
		for ci, chunk := range chunks {
			chunkFindings, err := s.analyzeChunk(ctx, runID, f.Path, chunk, ci+1, len(chunks))
			if err != nil {
				log.Printf("[Audit] analyzeChunk(%s chunk %d): %v", f.Path, ci+1, err)
				continue
			}
			findings = append(findings, chunkFindings...)
		}

		if (i+1)%10 == 0 {
			log.Printf("[Audit] %s — progress: %d/%d files", runID, i+1, len(goFiles))
		}
	}

	log.Printf("[Audit] %s — scan complete: %d findings", runID, len(findings))
	return findings, nil
}

// analyzeChunk sends one source chunk to the LLM and parses the JSON response.
func (s *AuditScanner) analyzeChunk(ctx context.Context, runID, filePath, source string, chunkN, totalChunks int) ([]Finding, error) {
	prompt := buildAuditPrompt(filePath, source, chunkN, totalChunks)
	messages := []map[string]string{
		{"role": "system", "content": auditSystemPrompt},
		{"role": "user", "content": prompt},
	}

	raw, err := s.llm(ctx, messages)
	if err != nil {
		return nil, err
	}

	return parseFindings(raw, runID, filePath)
}

// ---------------------------------------------------------------------------
// Parsing
// ---------------------------------------------------------------------------

func parseFindings(raw, runID, filePath string) ([]Finding, error) {
	// Strip markdown fences
	clean := raw
	if idx := strings.Index(clean, "```json"); idx >= 0 {
		clean = clean[idx+7:]
		if end := strings.Index(clean, "```"); end >= 0 {
			clean = clean[:end]
		}
	} else if idx := strings.Index(clean, "```"); idx >= 0 {
		clean = clean[idx+3:]
		if end := strings.Index(clean, "```"); end >= 0 {
			clean = clean[:end]
		}
	}
	clean = strings.TrimSpace(clean)

	// Expect a JSON array
	var raw_findings []struct {
		LineHint    int    `json:"line_hint"`
		Description string `json:"description"`
		Category    string `json:"category"`
		Severity    string `json:"severity"`
		CodeSnippet string `json:"code_snippet"`
	}
	if err := json.Unmarshal([]byte(clean), &raw_findings); err != nil {
		// No findings or parse error — treat as clean file
		return nil, nil
	}

	var findings []Finding
	for i, rf := range raw_findings {
		sev := normalizeSeverity(rf.Severity)
		findings = append(findings, Finding{
			ID:          fmt.Sprintf("%s-c%d-f%d", sanitizeID(filePath), 0, i),
			AuditRunID:  runID,
			File:        filePath,
			LineHint:    rf.LineHint,
			Description: rf.Description,
			Category:    rf.Category,
			Severity:    sev,
			CodeSnippet: rf.CodeSnippet,
			FoundAt:     time.Now(),
		})
	}
	return findings, nil
}

func normalizeSeverity(s string) Severity {
	switch strings.ToUpper(strings.TrimSpace(s)) {
	case "CRITICAL":
		return SeverityCritical
	case "HIGH":
		return SeverityHigh
	case "MEDIUM":
		return SeverityMedium
	default:
		return SeverityLow
	}
}

func sanitizeID(path string) string {
	r := strings.NewReplacer("/", "-", ".", "-", "_", "-")
	return r.Replace(path)
}

// chunkSource splits source code into chunks of approximately maxChars characters,
// splitting on newlines to avoid cutting mid-line.
func chunkSource(source string, maxChars int) []string {
	if len(source) <= maxChars {
		return []string{source}
	}
	var chunks []string
	lines := strings.Split(source, "\n")
	var current strings.Builder
	for _, line := range lines {
		if current.Len()+len(line)+1 > maxChars && current.Len() > 0 {
			chunks = append(chunks, current.String())
			current.Reset()
		}
		current.WriteString(line)
		current.WriteByte('\n')
	}
	if current.Len() > 0 {
		chunks = append(chunks, current.String())
	}
	return chunks
}

// ---------------------------------------------------------------------------
// Prompts
// ---------------------------------------------------------------------------

const auditSystemPrompt = `You are a senior Go security and correctness auditor for the Oricli-Alpha codebase.
Analyze the provided Go source code for real, verifiable issues only.

Return a JSON array of findings. Each finding must have:
- "line_hint": approximate line number (integer)
- "description": concise one-sentence description of the issue
- "category": one of "bug" | "security" | "logic" | "performance" | "dead_code"
- "severity": one of "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
- "code_snippet": the specific 1-5 lines that contain the issue

Rules:
- ONLY include findings you are highly confident about
- Do NOT flag style issues, formatting, or naming conventions
- Do NOT flag things that are intentional patterns (e.g. fail-open sentinel)
- Return [] if no real issues found
- Return raw JSON only — no prose, no markdown fences`

func buildAuditPrompt(filePath, source string, chunkN, totalChunks int) string {
	header := fmt.Sprintf("File: %s", filePath)
	if totalChunks > 1 {
		header += fmt.Sprintf(" (chunk %d of %d)", chunkN, totalChunks)
	}
	return header + "\n\n```go\n" + source + "\n```"
}
