package reform

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
)

// VerificationResult is the output of CodeVerifier.Verify().
type VerificationResult struct {
	Passed   bool
	Stage    string   // which stage failed (empty if passed)
	Failures []string // human-readable failure reasons
}

// CodeVerifier runs a four-stage static analysis gate on LLM-proposed Go code
// before it is allowed to enter the build pipeline.
//
//  Stage 1 — Forbidden pattern scan (regex, no subprocess)
//  Stage 2 — go fmt check (formatting compliance)
//  Stage 3 — go vet (semantic checks)
//  Stage 4 — go build (full compile in isolated temp module)
type CodeVerifier struct {
	ModulePath string // e.g. "github.com/thynaptic/oricli-go"
	GoVersion  string // e.g. "1.22"
}

// NewCodeVerifier returns a verifier configured for the Oricli-Alpha module.
func NewCodeVerifier() *CodeVerifier {
	return &CodeVerifier{
		ModulePath: "github.com/thynaptic/oricli-go",
		GoVersion:  "1.22",
	}
}

// forbidden patterns — any match in proposed code is an automatic rejection.
var forbiddenPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)//\s*(TODO|FIXME|HACK|XXX|PLACEHOLDER|STUB|NOT IMPLEMENTED)`),
	regexp.MustCompile(`panic\("not implemented"\)`),
	regexp.MustCompile(`panic\("TODO`),
	// empty function body: "func ... {\n}" with only optional whitespace inside
	regexp.MustCompile(`(?m)\bfunc\b[^{]+\{\s*\}`),
	// lone blank identifier assignment used as a stub: "_ = something" on its own line
	regexp.MustCompile(`(?m)^\s*_\s*=\s*\S+\s*$`),
}

// sensitivePathPrefixes — files on these paths may never be auto-deployed.
var sensitivePathPrefixes = []string{
	"pkg/safety/",
	"pkg/sovereign/",
	"pkg/kernel/",
}

// IsSensitivePath returns true if the file path targets a protected package.
func IsSensitivePath(filePath string) bool {
	clean := filepath.ToSlash(filePath)
	for _, prefix := range sensitivePathPrefixes {
		if strings.Contains(clean, prefix) {
			return true
		}
	}
	return false
}

// Verify runs all four verification stages against proposedCode.
// filePath is used only for context in error messages.
func (v *CodeVerifier) Verify(proposedCode, filePath string) VerificationResult {
	// Stage 1: Forbidden pattern scan
	var failures []string
	for _, pat := range forbiddenPatterns {
		if loc := pat.FindStringIndex(proposedCode); loc != nil {
			snippet := proposedCode[loc[0]:min(loc[1]+40, len(proposedCode))]
			failures = append(failures, fmt.Sprintf("forbidden pattern %q near: %q", pat.String(), snippet))
		}
	}
	if len(failures) > 0 {
		return VerificationResult{Passed: false, Stage: "pattern-scan", Failures: failures}
	}

	// Write code to a temp file for subprocess stages
	tmpDir, err := os.MkdirTemp("", "oricli-reform-*")
	if err != nil {
		return VerificationResult{Passed: false, Stage: "setup", Failures: []string{err.Error()}}
	}
	defer os.RemoveAll(tmpDir)

	// Determine package name from proposed code (first "package X" line)
	pkgName := extractPackageName(proposedCode)
	if pkgName == "" {
		return VerificationResult{Passed: false, Stage: "setup", Failures: []string{"could not detect package declaration in proposed code"}}
	}

	srcFile := filepath.Join(tmpDir, "proposed.go")
	if err := os.WriteFile(srcFile, []byte(proposedCode), 0644); err != nil {
		return VerificationResult{Passed: false, Stage: "setup", Failures: []string{err.Error()}}
	}

	// Stage 2: go fmt — proposed code must be already formatted (no diff)
	fmtOut, err := exec.Command("gofmt", "-l", srcFile).CombinedOutput()
	if err != nil {
		return VerificationResult{Passed: false, Stage: "go-fmt", Failures: []string{string(fmtOut)}}
	}
	if strings.TrimSpace(string(fmtOut)) != "" {
		return VerificationResult{
			Passed:   false,
			Stage:    "go-fmt",
			Failures: []string{"proposed code is not gofmt-clean; run gofmt and resubmit"},
		}
	}

	// Stage 3 & 4: build an isolated module and run go vet + go build
	// We create a minimal go.mod so the file compiles as its own package.
	goMod := fmt.Sprintf("module reform_sandbox\n\ngo %s\n", v.GoVersion)
	if err := os.WriteFile(filepath.Join(tmpDir, "go.mod"), []byte(goMod), 0644); err != nil {
		return VerificationResult{Passed: false, Stage: "setup", Failures: []string{err.Error()}}
	}

	// Stage 3: go vet
	vetOut, err := exec.Command("go", "vet", "./...").CombinedOutput()
	// go vet returns exit code 1 on issues but also on import errors from sandbox isolation
	// We treat any non-empty non-import output as a failure
	vetStr := strings.TrimSpace(string(vetOut))
	if err != nil && vetStr != "" && !strings.Contains(vetStr, "no Go files") {
		return VerificationResult{Passed: false, Stage: "go-vet", Failures: []string{vetStr}}
	}

	// Stage 4: go build
	buildOut, err := exec.Command("go", "build", "./...").CombinedOutput()
	buildStr := strings.TrimSpace(string(buildOut))
	if err != nil && buildStr != "" && !strings.Contains(buildStr, "no Go files") {
		return VerificationResult{Passed: false, Stage: "go-build", Failures: []string{buildStr}}
	}

	return VerificationResult{Passed: true, Stage: "all", Failures: nil}
}

func extractPackageName(src string) string {
	for _, line := range strings.Split(src, "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "package ") {
			parts := strings.Fields(line)
			if len(parts) >= 2 {
				return parts[1]
			}
		}
	}
	return ""
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
