package forge

import (
	"fmt"
	"regexp"
	"strings"
)

// CodeConstitution enforces safety rules on generated bash tool scripts.
// Every generated tool must pass Check() before sandbox execution.
type CodeConstitution struct {
	Rules []ConstitutionRule
}

// ConstitutionRule is a single enforceable constraint on generated source.
type ConstitutionRule struct {
	Name        string
	Description string
	Pattern     *regexp.Regexp // nil = custom checker only
	check       func(source string) bool
	Fatal       bool // if true, single violation = immediate reject
}

// Violation is a rule breach found during Check().
type Violation struct {
	Rule    string
	Detail  string
	Fatal   bool
}

func (v Violation) Error() string {
	return fmt.Sprintf("[%s] %s", v.Rule, v.Detail)
}

// NewCodeConstitution builds the default Code Constitution for JIT tool scripts.
// All rules govern bash scripts that follow the stdin→JSON stdout contract.
func NewCodeConstitution() *CodeConstitution {
	c := &CodeConstitution{}
	c.Rules = []ConstitutionRule{
		// ── Hard blocks (Fatal = true) ─────────────────────────────────────────
		{
			Name:        "no_destructive_fs",
			Description: "No recursive deletion or forced overwrites of arbitrary paths",
			Pattern:     regexp.MustCompile(`rm\s+-[a-zA-Z]*r[a-zA-Z]*f|rm\s+-[a-zA-Z]*f[a-zA-Z]*r|rm\s+--force`),
			Fatal:       true,
		},
		{
			Name:        "no_etc_access",
			Description: "No access to system config directories",
			Pattern:     regexp.MustCompile(`/etc/|/proc/|/sys/|/boot/|/root/`),
			Fatal:       true,
		},
		{
			Name:        "no_exec_download",
			Description: "No download-and-execute patterns",
			Pattern:     regexp.MustCompile(`curl\s+.*\|\s*(bash|sh)|wget\s+.*\|\s*(bash|sh)|eval\s*\$\(curl|eval\s*\$\(wget`),
			Fatal:       true,
		},
		{
			Name:        "no_background_jobs",
			Description: "No background process spawning",
			Pattern:     regexp.MustCompile(`&\s*$|&\s*#|\bnohup\b|\bdisown\b`),
			Fatal:       true,
		},
		{
			Name:        "no_privileged_ops",
			Description: "No sudo, su, chmod 777, or chown to root",
			Pattern:     regexp.MustCompile(`\bsudo\b|\bsu\s+-|\bchmod\s+777|\bchown\s+root|\bpasswd\b`),
			Fatal:       true,
		},
		{
			Name:        "no_encoded_exec",
			Description: "No base64-decode-and-execute patterns",
			Pattern:     regexp.MustCompile(`base64\s+.*\|\s*(bash|sh|exec)|echo\s+.*base64.*\|\s*(bash|sh)`),
			Fatal:       true,
		},
		{
			Name:        "no_network_to_unknown",
			Description: "curl/wget must use HTTPS and not target internal ranges",
			Pattern:     regexp.MustCompile(`(curl|wget)\s+http://|192\.168\.|10\.\d+\.\d+\.|127\.0\.0\.|localhost`),
			Fatal:       true,
		},
		{
			Name:        "no_oricli_paths",
			Description: "No access to Oricli internal directories",
			Pattern:     regexp.MustCompile(`/home/mike/|\.env|oricli|mavaia`),
			Fatal:       true,
		},

		// ── Non-fatal warnings (accumulated) ──────────────────────────────────
		{
			Name:        "no_sleep_loops",
			Description: "No long sleep or infinite loops",
			Pattern:     regexp.MustCompile(`while\s+true|sleep\s+[0-9]{3,}|for\s*\(.*;`),
			Fatal:       false,
		},
		{
			Name:        "max_lines",
			Description: "Script must not exceed 150 lines",
			check: func(source string) bool {
				lines := strings.Count(source, "\n") + 1
				return lines > 150
			},
			Fatal: false,
		},
		{
			Name:        "must_read_stdin",
			Description: "Tool must read input (stdin or $1) — no-input tools are suspicious",
			check: func(source string) bool {
				hasStdin := strings.Contains(source, "stdin") ||
					strings.Contains(source, "read ") ||
					strings.Contains(source, "cat -") ||
					strings.Contains(source, "cat /dev/stdin") ||
					strings.Contains(source, "$1") ||
					strings.Contains(source, "$@") ||
					strings.Contains(source, `"$1"`)
				return !hasStdin
			},
			Fatal: false,
		},
		{
			Name:        "must_output_json",
			Description: "Tool should produce JSON output (jq or echo with braces)",
			check: func(source string) bool {
				hasJSON := strings.Contains(source, "jq") ||
					strings.Contains(source, `echo "{"`) ||
					strings.Contains(source, `echo '{'`) ||
					strings.Contains(source, `printf '{'`) ||
					strings.Contains(source, `printf "{"`)
				return !hasJSON
			},
			Fatal: false,
		},
	}
	return c
}

// Check evaluates the source against all constitution rules.
// Returns violations found and whether the source passes (no fatal violations,
// and non-fatal violations ≤ 1).
func (c *CodeConstitution) Check(source string) ([]Violation, bool) {
	var violations []Violation
	sourceLower := strings.ToLower(source)

	for _, rule := range c.Rules {
		violated := false
		detail := ""

		if rule.Pattern != nil {
			if loc := rule.Pattern.FindStringIndex(sourceLower); loc != nil {
				violated = true
				snippet := source[loc[0]:min(loc[1]+20, len(source))]
				detail = fmt.Sprintf("matched pattern near: %q", strings.TrimSpace(snippet))
			}
		}

		if !violated && rule.check != nil {
			if rule.check(source) {
				violated = true
				detail = rule.Description
			}
		}

		if violated {
			violations = append(violations, Violation{
				Rule:   rule.Name,
				Detail: detail,
				Fatal:  rule.Fatal,
			})
		}
	}

	// Fail on any fatal violation.
	for _, v := range violations {
		if v.Fatal {
			return violations, false
		}
	}

	// Fail if more than 1 non-fatal violation (too many warnings = suspicious).
	nonFatal := 0
	for _, v := range violations {
		if !v.Fatal {
			nonFatal++
		}
	}
	if nonFatal > 1 {
		return violations, false
	}

	return violations, true
}

// Summary returns a human-readable violation report.
func (c *CodeConstitution) Summary(violations []Violation) string {
	if len(violations) == 0 {
		return "✅ Constitution: PASS (no violations)"
	}
	var sb strings.Builder
	for _, v := range violations {
		severity := "⚠️ warn"
		if v.Fatal {
			severity = "🚫 FATAL"
		}
		fmt.Fprintf(&sb, "%s [%s]: %s\n", severity, v.Rule, v.Detail)
	}
	return strings.TrimSpace(sb.String())
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
