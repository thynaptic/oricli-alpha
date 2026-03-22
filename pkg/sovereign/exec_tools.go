package sovereign

import (
	"fmt"
	"os/exec"
	"strconv"
	"strings"
)

// allowedCommands maps the short command name to the actual binary + base args.
// These are the ONLY system commands Oricli can run at EXEC level.
var allowedCommands = map[string][]string{
	"status":  {"systemctl", "status", "oricli-backbone", "--no-pager", "-l"},
	"df":      {"df", "-h"},
	"free":    {"free", "-h"},
	"uptime":  {"uptime"},
	"ps":      {"ps", "aux", "--sort=-%cpu"},
}

// SovereignExecHandler runs allowlisted system commands on behalf of the owner.
type SovereignExecHandler struct{}

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
func (h *SovereignExecHandler) Handle(msg string) string {
	t := strings.TrimSpace(strings.TrimPrefix(strings.TrimSpace(msg), "!"))
	parts := strings.Fields(t)
	if len(parts) == 0 {
		return "No command provided. Try: !status, !logs <n>, !df, !free, !uptime, !ps"
	}

	cmd := strings.ToLower(parts[0])

	switch cmd {
	case "logs":
		n := 50
		if len(parts) > 1 {
			if v, err := strconv.Atoi(parts[1]); err == nil && v > 0 && v <= 500 {
				n = v
			}
		}
		return runCommand("journalctl", "-u", "oricli-backbone", "-n", strconv.Itoa(n), "--no-pager", "--output=short")

	case "modules":
		// This is answered by the LLM/inference layer; we return a sentinel so
		// the inference step can inject module registry data.
		return "__SOVEREIGN_MODULES__"

	default:
		args, ok := allowedCommands[cmd]
		if !ok {
			return fmt.Sprintf("Unknown command: !%s\nAvailable: !status, !logs [n], !modules, !df, !free, !uptime, !ps", cmd)
		}
		return runCommand(args[0], args[1:]...)
	}
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
