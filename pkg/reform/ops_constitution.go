package reform

import (
	"fmt"
	"strings"
)

// OpsConstitution enforces sovereign principles for autonomous VPS/system operations.
// Unlike the Code/Canvas constitutions (which are LLM system prompt injections),
// OpsConstitution is enforced at the execution layer — Validate() is called before
// every exec.Command() in SovereignExecHandler. Violations hard-block execution.
//
// Also exposes GetSystemPrompt() so it can be injected as LLM context, giving Oricli
// self-awareness of her own operational boundaries.
type OpsConstitution struct {
	Principles []CodePrinciple
	// AllowedCommands is the canonical allowlist — any command not in this map is
	// automatically rejected by Validate() regardless of the principle checks.
	AllowedCommands map[string]bool
}

// NewOpsConstitution returns the canonical Sovereign Ops Constitution.
func NewOpsConstitution() *OpsConstitution {
	return &OpsConstitution{
		AllowedCommands: map[string]bool{
			"status":  true,
			"logs":    true,
			"modules": true,
			"df":      true,
			"free":    true,
			"uptime":  true,
			"ps":      true,
		},
		Principles: []CodePrinciple{
			{
				Name:        "Full Audit Trail",
				Description: "Every system command execution must be recorded before it runs.",
				Guideline:   "No command executes silently. Every invocation — including failed attempts — must be timestamped, logged to the service log, and written to the PocketBase memory bank with provenance=system_exec. The audit record is written before the command runs, not after, so a crash cannot erase the record of what was attempted.",
			},
			{
				Name:        "Minimal Footprint",
				Description: "Prefer read-only diagnostics. Mutations require an explicit owner request.",
				Guideline:   "The canonical allowlist contains only observability commands: status, logs, df, free, uptime, ps. No command that writes, moves, deletes, or modifies system state may be added to the allowlist without an explicit code change reviewed by the owner. Commands are never constructed dynamically from user input — they are mapped from a fixed allowlist to fixed binary arguments.",
			},
			{
				Name:        "No Self-Modification",
				Description: "Oricli cannot modify her own service binary, systemd unit, or configuration files via exec.",
				Guideline:   "Commands that would affect oricli-backbone.service, /etc/systemd/, the oricli binary itself, go.mod, or any file under the Mavaia project root are permanently prohibited. Self-restart via systemctl is also prohibited via exec — it must be requested from the owner explicitly and performed by the owner. This prevents recursive self-modification loops.",
			},
			{
				Name:        "Blast Radius Containment",
				Description: "No exec command may affect services or processes outside the oricli service boundary.",
				Guideline:   "The exec surface is scoped to Oricli's own service and read-only host diagnostics. Commands that enumerate, modify, or interact with other services (nginx, caddy, postgresql, etc.) are prohibited. Network configuration, firewall rules, and user account management are permanently out of scope for autonomous exec.",
			},
			{
				Name:        "Allowlist Sovereignty",
				Description: "Only commands in the static allowlist may execute — no exceptions, no dynamic construction.",
				Guideline:   "The allowedCommands map is the ground truth. If a command name does not appear in that map, execution is rejected with a clear error before any subprocess is spawned. User input is never interpolated directly into command arguments — arguments are pre-defined per command in the allowlist, with the only variable being bounded numeric parameters (e.g., log line count capped at 500).",
			},
			{
				Name:        "Owner Primacy",
				Description: "Autonomous exec is a diagnostic capability, not an action capability. Actions require owner intent.",
				Guideline:   "The exec surface exists so Oricli can answer operational questions (\"how is memory?\", \"is the service up?\"). It is not an autonomous action surface. Oricli does not initiate exec commands on her own — she only responds to explicit `!command` owner messages. Daemons and background goroutines must never call SovereignExecHandler directly without an owner-scoped context.",
			},
		},
	}
}

// Validate checks whether the given command name is constitutionally permitted.
// Returns nil if the command is allowed; returns a descriptive error if rejected.
// This must be called before any exec.Command() in SovereignExecHandler.
func (c *OpsConstitution) Validate(cmd string) error {
	normalized := strings.ToLower(strings.TrimSpace(cmd))
	if normalized == "" {
		return fmt.Errorf("ops_constitution: empty command rejected — no silent exec permitted (Audit Trail principle)")
	}
	if !c.AllowedCommands[normalized] {
		return fmt.Errorf("ops_constitution: command %q is not in the sovereign allowlist — execution blocked (Allowlist Sovereignty principle). Allowed: %s",
			normalized, c.allowedList())
	}
	return nil
}

// GetSystemPrompt formats the Ops Constitution as an LLM system prompt addendum.
// Injected so Oricli understands her own operational boundaries and can inform
// the owner accurately when asked about what she can do autonomously.
func (c *OpsConstitution) GetSystemPrompt() string {
	var sb strings.Builder
	sb.WriteString("### SOVEREIGN OPS CONSTITUTION (VPS Execution Boundaries)\n")
	sb.WriteString("You have limited, read-only diagnostic access to the host system via !commands.\n")
	sb.WriteString("You MUST adhere to every principle below when reasoning about or describing system operations.\n\n")
	sb.WriteString("Available commands: !status, !logs [n], !df, !free, !uptime, !ps, !modules\n\n")
	for i, p := range c.Principles {
		sb.WriteString(fmt.Sprintf("%d. **%s** — %s\n   Mandate: %s\n\n", i+1, p.Name, p.Description, p.Guideline))
	}
	sb.WriteString("You cannot modify, restart, or reconfigure any system service autonomously. If the owner requests a system change, describe what they should do — do not attempt it via exec.\n")
	sb.WriteString("### END SOVEREIGN OPS CONSTITUTION\n")
	return sb.String()
}

func (c *OpsConstitution) allowedList() string {
	keys := make([]string, 0, len(c.AllowedCommands))
	for k := range c.AllowedCommands {
		keys = append(keys, "!"+k)
	}
	return strings.Join(keys, ", ")
}
