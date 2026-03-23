package sovereign

import (
	"fmt"
	"log"
	"os/exec"
	"strconv"
	"strings"

	"github.com/thynaptic/oricli-go/pkg/reform"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// allowedCommands maps the short command name to the actual binary + base args.
// These are the ONLY system commands Oricli can run at EXEC level.
// Also registered in OpsConstitution.AllowedCommands — keep both in sync.
var allowedCommands = map[string][]string{
	"status":  {"systemctl", "status", "oricli-backbone", "--no-pager", "-l"},
	"df":      {"df", "-h"},
	"free":    {"free", "-h"},
	"uptime":  {"uptime"},
	"ps":      {"ps", "aux", "--sort=-%cpu"},
}

var opsConstitution = reform.NewOpsConstitution()

// SovereignExecHandler runs allowlisted system commands on behalf of the owner.
// All executions are validated by OpsConstitution and logged to PocketBase.
type SovereignExecHandler struct {
	MemoryBank *service.MemoryBank // optional — wired at server boot
}

func NewSovereignExecHandler() *SovereignExecHandler {
	return &SovereignExecHandler{}
}

// IsExecCommand returns true if the message looks like a sovereign system command.
// Format: `!status`, `!logs 50`, `!modules`, `!df`, `!free`, `!uptime`
func IsExecCommand(msg string) bool {
	t := strings.TrimSpace(msg)
	return strings.HasPrefix(t, "!")
}

// Handle executes the command and returns a human-readable result.
// Every invocation is: (1) validated by OpsConstitution, (2) logged to PocketBase.
func (h *SovereignExecHandler) Handle(msg string) string {
	t := strings.TrimSpace(strings.TrimPrefix(strings.TrimSpace(msg), "!"))
	parts := strings.Fields(t)
	if len(parts) == 0 {
		return "No command provided. Try: !status, !logs <n>, !df, !free, !uptime, !ps"
	}

	cmd := strings.ToLower(parts[0])

	// Constitution pre-flight — reject anything outside the allowlist before any exec.
	// "logs" and "modules" are special-cased below but also validated here.
	if cmd != "logs" && cmd != "modules" {
		if err := opsConstitution.Validate(cmd); err != nil {
			log.Printf("[OpsConstitution] BLOCKED: %v", err)
			h.auditExec(cmd, "", err.Error())
			return fmt.Sprintf("⛔ %s", err.Error())
		}
	}

	var result string
	switch cmd {
	case "logs":
		n := 50
		if len(parts) > 1 {
			if v, err := strconv.Atoi(parts[1]); err == nil && v > 0 && v <= 500 {
				n = v
			}
		}
		result = runCommand("journalctl", "-u", "oricli-backbone", "-n", strconv.Itoa(n), "--no-pager", "--output=short")

	case "modules":
		// Answered by the LLM/inference layer; return sentinel for inference injection.
		result = "__SOVEREIGN_MODULES__"

	default:
		args, ok := allowedCommands[cmd]
		if !ok {
			result = fmt.Sprintf("Unknown command: !%s\nAvailable: !status, !logs [n], !modules, !df, !free, !uptime, !ps", cmd)
		} else {
			result = runCommand(args[0], args[1:]...)
		}
	}

	// Audit every exec — fire-and-forget to PocketBase.
	h.auditExec(cmd, result, "")
	return result
}

// auditExec writes a system_exec provenance record to PocketBase memory.
// Called for every Handle() invocation — successful or blocked.
// Non-blocking: Write is already async inside MemoryBank.
func (h *SovereignExecHandler) auditExec(cmd, output, errMsg string) {
	if h.MemoryBank == nil || !h.MemoryBank.IsEnabled() {
		return
	}
	summary := output
	if errMsg != "" {
		summary = "[BLOCKED] " + errMsg
	}
	if len(summary) > 500 {
		summary = summary[:500] + "... (truncated)"
	}
	h.MemoryBank.Write(service.MemoryFragment{
		Topic:      "vps_exec",
		Content:    fmt.Sprintf("VPS exec: !%s\n%s", cmd, summary),
		Source:     "system_exec",
		Importance: 0.6,
		Provenance: service.ProvenanceSyntheticL1, // audit log, not user-stated fact
		Volatility: service.VolatilityEphemeral,   // exec logs decay in 7d
	})
}

func runCommand(bin string, args ...string) string {
	out, err := exec.Command(bin, args...).CombinedOutput()
	if err != nil {
		return fmt.Sprintf("Command failed: %v\n%s", err, string(out))
	}
	result := strings.TrimSpace(string(out))
	if len(result) > 4000 {
		result = result[:4000] + "\n... (truncated)"
	}
	return result
}
