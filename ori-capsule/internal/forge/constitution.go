package forge

import (
	"fmt"
	"regexp"
	"strings"
)

// ConstitutionRule is a single enforceable constraint on script/source.
type ConstitutionRule struct {
	Name        string
	Description string
	Pattern     *regexp.Regexp // nil = custom checker only
	check       func(source string) bool
	Fatal       bool
}

// Violation is a rule breach found during Check().
type Violation struct {
	Rule   string `json:"rule"`
	Detail string `json:"detail"`
	Fatal  bool   `json:"fatal"`
}

func (v Violation) Error() string {
	return fmt.Sprintf("[%s] %s", v.Rule, v.Detail)
}

// ScriptConstitution enforces safety rules on GOSH shell scripts.
// Ported from pkg/forge CodeConstitution — fatal security rules always apply.
// ToolMode adds JIT-tool contract warnings (stdin/JSON/line limits).
type ScriptConstitution struct {
	Rules []ConstitutionRule
}

// NewScriptConstitution builds the sandbox gate used before every GOSH script run.
// Fatal-only by default so normal capsule scripts (echo/cat) still pass.
func NewScriptConstitution() *ScriptConstitution {
	return &ScriptConstitution{Rules: sandboxFatalRules()}
}

// NewToolConstitution builds the stricter JIT-tool gate (pkg/forge full set, capsule-tuned).
func NewToolConstitution() *ScriptConstitution {
	rules := sandboxFatalRules()
	rules = append(rules, toolContractRules()...)
	return &ScriptConstitution{Rules: rules}
}

func sandboxFatalRules() []ConstitutionRule {
	return []ConstitutionRule{
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
			Name:        "no_secret_paths",
			Description: "No access to env/secret or host-home paths",
			Pattern:     regexp.MustCompile(`/home/mike/|\.env\b|/root/`),
			Fatal:       true,
		},
		{
			Name:        "no_restricted_binaries",
			Description: "No binaries outside the GOSH allowlist",
			Pattern:     regexp.MustCompile(`(?m)^\s*(curl|wget|bash|sh|python3?|perl|ruby|node|npm|pip|nc|ncat|ssh|scp)\b`),
			Fatal:       true,
		},
	}
}

func toolContractRules() []ConstitutionRule {
	return []ConstitutionRule{
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
				return strings.Count(source, "\n")+1 > 150
			},
			Fatal: false,
		},
		{
			Name:        "must_read_stdin",
			Description: "Tool must read input (stdin or $1)",
			check: func(source string) bool {
				hasStdin := strings.Contains(source, "stdin") ||
					strings.Contains(source, "read ") ||
					strings.Contains(source, "cat -") ||
					strings.Contains(source, "cat /dev/stdin") ||
					strings.Contains(source, "$1") ||
					strings.Contains(source, "$@")
				return !hasStdin
			},
			Fatal: false,
		},
		{
			Name:        "must_output_json",
			Description: "Tool should produce JSON output",
			check: func(source string) bool {
				hasJSON := strings.Contains(source, "jq") ||
					strings.Contains(source, `echo "{`) ||
					strings.Contains(source, `echo '{`) ||
					strings.Contains(source, `printf '{`) ||
					strings.Contains(source, `printf "{`)
				return !hasJSON
			},
			Fatal: false,
		},
	}
}

// Check evaluates source against all rules.
// Pass = no fatals and ≤1 non-fatal warning.
func (c *ScriptConstitution) Check(source string) ([]Violation, bool) {
	if c == nil || strings.TrimSpace(source) == "" {
		return nil, true
	}
	var violations []Violation
	sourceLower := strings.ToLower(source)

	for _, rule := range c.Rules {
		violated := false
		detail := ""

		if rule.Pattern != nil {
			if loc := rule.Pattern.FindStringIndex(sourceLower); loc != nil {
				violated = true
				end := loc[1] + 20
				if end > len(source) {
					end = len(source)
				}
				// Pattern matched on lowercased view — index into original carefully.
				snippet := source
				if loc[0] < len(source) {
					snippet = source[loc[0]:end]
				}
				detail = fmt.Sprintf("matched pattern near: %q", strings.TrimSpace(snippet))
			}
		}
		if !violated && rule.check != nil && rule.check(source) {
			violated = true
			detail = rule.Description
		}
		if violated {
			violations = append(violations, Violation{
				Rule:   rule.Name,
				Detail: detail,
				Fatal:  rule.Fatal,
			})
		}
	}

	for _, v := range violations {
		if v.Fatal {
			return violations, false
		}
	}
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
func (c *ScriptConstitution) Summary(violations []Violation) string {
	if len(violations) == 0 {
		return "Constitution: PASS (no violations)"
	}
	var sb strings.Builder
	for _, v := range violations {
		severity := "warn"
		if v.Fatal {
			severity = "FATAL"
		}
		fmt.Fprintf(&sb, "%s [%s]: %s\n", severity, v.Rule, v.Detail)
	}
	return strings.TrimSpace(sb.String())
}
