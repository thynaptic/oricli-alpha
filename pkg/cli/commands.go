package cli

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// ── Styles ────────────────────────────────────────────────────────────────────

var (
	stylePrimary  = lipgloss.NewStyle().Foreground(lipgloss.Color("#7C3AED"))       // sovereign purple
	styleAccent   = lipgloss.NewStyle().Foreground(lipgloss.Color("#A78BFA"))       // light purple
	styleSuccess  = lipgloss.NewStyle().Foreground(lipgloss.Color("#10B981"))       // green
	styleWarning  = lipgloss.NewStyle().Foreground(lipgloss.Color("#F59E0B"))       // amber
	styleDanger   = lipgloss.NewStyle().Foreground(lipgloss.Color("#EF4444"))       // red
	styleDim      = lipgloss.NewStyle().Foreground(lipgloss.Color("#6B7280"))       // muted
	styleBold     = lipgloss.NewStyle().Bold(true)
	styleKeyVal   = lipgloss.NewStyle().Foreground(lipgloss.Color("#A78BFA")).Bold(true)
	styleResponse = lipgloss.NewStyle().Foreground(lipgloss.Color("#F3F4F6"))       // near-white
	styleLabel    = lipgloss.NewStyle().Foreground(lipgloss.Color("#7C3AED")).Bold(true)
)

// handleSlashCommand routes /commands in the REPL and returns rendered output.
// Returns (output string, handled bool).
func handleSlashCommand(input string, client *Client, cfg *Config, history *[]map[string]string) (string, bool) {
	parts := strings.Fields(input)
	if len(parts) == 0 || !strings.HasPrefix(parts[0], "/") {
		return "", false
	}

	cmd := strings.ToLower(parts[0])
	args := parts[1:]

	switch cmd {
	case "/help":
		return renderHelp(), true

	case "/health":
		return runHealth(client), true

	case "/models":
		return runModels(client), true

	case "/modules":
		return runModules(client), true

	case "/metrics":
		return runMetrics(client), true

	case "/therapy":
		return runTherapy(client), true

	case "/mastery":
		return runMastery(client), true

	case "/compute":
		return runCompute(client), true

	case "/goals":
		return runGoals(client), true

	case "/goal":
		if len(args) == 0 {
			return styleDanger.Render("Usage: /goal <description>"), true
		}
		return runPostGoal(client, strings.Join(args, " ")), true

	case "/target":
		if len(args) == 0 {
			return styleAccent.Render("Current target: ") + cfg.Target, true
		}
		newTarget := args[0]
		client.SetTarget(newTarget)
		cfg.Target = newTarget
		return styleSuccess.Render("✓ Target switched to: ") + newTarget, true

	case "/clear":
		*history = []map[string]string{}
		return styleSuccess.Render("✓ Conversation history cleared"), true

	case "/model":
		if len(args) == 0 {
			return styleAccent.Render("Current model: ") + cfg.Model, true
		}
		cfg.Model = args[0]
		return styleSuccess.Render("✓ Model set to: ") + cfg.Model, true

	case "/save":
		if err := cfg.Save(); err != nil {
			return styleDanger.Render("Save failed: "+err.Error()), true
		}
		return styleSuccess.Render("✓ Config saved to ~/.oricli/config.yaml"), true

	default:
		return styleDanger.Render("Unknown command: "+cmd+" — type /help for available commands"), true
	}
}

// ── Individual command runners ────────────────────────────────────────────────

func runHealth(c *Client) string {
	data, err := c.GetHealth()
	if err != nil {
		return styleDanger.Render("✗ " + err.Error())
	}
	var sb strings.Builder
	sb.WriteString(styleLabel.Render("● Health") + "\n")
	for k, v := range data {
		sb.WriteString(fmt.Sprintf("  %s  %v\n", styleKeyVal.Render(padRight(k, 18)), v))
	}
	return sb.String()
}

func runModels(c *Client) string {
	data, err := c.GetModels()
	if err != nil {
		return styleDanger.Render("✗ " + err.Error())
	}
	var sb strings.Builder
	sb.WriteString(styleLabel.Render("● Models") + "\n")
	if models, ok := data["data"].([]interface{}); ok {
		for _, m := range models {
			if model, ok := m.(map[string]interface{}); ok {
				id := fmt.Sprintf("%v", model["id"])
				sb.WriteString("  " + styleAccent.Render("▸ ") + id + "\n")
			}
		}
	} else {
		sb.WriteString(prettyJSON(data))
	}
	return sb.String()
}

func runModules(c *Client) string {
	data, err := c.GetModules()
	if err != nil {
		return styleDanger.Render("✗ " + err.Error())
	}
	var sb strings.Builder
	sb.WriteString(styleLabel.Render("● Modules") + "\n")
	if modules, ok := data["modules"].([]interface{}); ok {
		sb.WriteString(fmt.Sprintf("  %s %d\n", styleDim.Render("total:"), len(modules)))
		for _, m := range modules {
			if mod, ok := m.(map[string]interface{}); ok {
				name := fmt.Sprintf("%v", mod["name"])
				status := fmt.Sprintf("%v", mod["status"])
				statusStyle := styleSuccess
				if status != "active" && status != "healthy" {
					statusStyle = styleWarning
				}
				sb.WriteString(fmt.Sprintf("  %s %s\n", styleAccent.Render(padRight(name, 32)), statusStyle.Render(status)))
			}
		}
	} else {
		sb.WriteString(prettyJSON(data))
	}
	return sb.String()
}

func runMetrics(c *Client) string {
	data, err := c.GetMetrics()
	if err != nil {
		return styleDanger.Render("✗ " + err.Error())
	}
	var sb strings.Builder
	sb.WriteString(styleLabel.Render("● Metrics") + "\n")
	sb.WriteString(prettyKV(data, 2))
	return sb.String()
}

func runTherapy(c *Client) string {
	stats, err := c.GetTherapyStats()
	if err != nil {
		return styleDanger.Render("✗ " + err.Error())
	}
	form, _ := c.GetFormulation()

	var sb strings.Builder
	sb.WriteString(styleLabel.Render("● Therapy / Cognitive State") + "\n")
	sb.WriteString("\n" + styleBold.Render("  Stats") + "\n")
	sb.WriteString(prettyKV(stats, 2))

	if form != nil {
		sb.WriteString("\n" + styleBold.Render("  Formulation") + "\n")
		if schemas, ok := form["active_schemas"]; ok {
			sb.WriteString(fmt.Sprintf("  %s  %v\n", styleKeyVal.Render(padRight("active_schemas", 18)), schemas))
		}
		if plan, ok := form["intervention_plan"].(string); ok && plan != "" {
			sb.WriteString("\n" + styleDim.Render("  Intervention Plan:") + "\n")
			for _, line := range strings.Split(plan, "\n") {
				sb.WriteString("    " + line + "\n")
			}
		}
	}
	return sb.String()
}

func runMastery(c *Client) string {
	data, err := c.GetMastery()
	if err != nil {
		return styleDanger.Render("✗ " + err.Error())
	}
	var sb strings.Builder
	sb.WriteString(styleLabel.Render("● Mastery Log — Topic Class Success Rates") + "\n")
	if stats, ok := data["stats"].(map[string]interface{}); ok {
		if len(stats) == 0 {
			sb.WriteString(styleDim.Render("  No mastery data yet — starts building after first completions\n"))
		}
		for class, rate := range stats {
			rateStr := fmt.Sprintf("%.0f%%", rate.(float64)*100)
			rateStyle := styleSuccess
			if r, ok := rate.(float64); ok && r < 0.5 {
				rateStyle = styleWarning
			}
			sb.WriteString(fmt.Sprintf("  %s  %s\n", styleKeyVal.Render(padRight(class, 20)), rateStyle.Render(rateStr)))
		}
	} else {
		sb.WriteString(prettyJSON(data))
	}
	return sb.String()
}

func runCompute(c *Client) string {
	stats, err := c.GetComputeBidStats()
	if err != nil {
		return styleDanger.Render("✗ " + err.Error())
	}
	decisions, err2 := c.GetComputeGovernor(10)
	var sb strings.Builder
	sb.WriteString(styleLabel.Render("● Sovereign Compute Bidding") + "\n")
	sb.WriteString(styleAccent.Render("  Tier Confidence Scores:") + "\n")
	if conf, ok := stats["confidence"].(map[string]interface{}); ok {
		for k, v := range conf {
			sb.WriteString(fmt.Sprintf("  %s  %.2f\n", styleKeyVal.Render(padRight(k, 26)), v))
		}
	} else {
		sb.WriteString(prettyJSON(stats))
	}
	sb.WriteString("\n" + styleAccent.Render("  Recent Decisions:") + "\n")
	if err2 == nil {
		if decs, ok := decisions["recent_decisions"].([]interface{}); ok {
			if len(decs) == 0 {
				sb.WriteString(styleDim.Render("  No decisions yet\n"))
			}
			for _, d := range decs {
				if dm, ok := d.(map[string]interface{}); ok {
					tier := fmt.Sprintf("%v", dm["winner_tier"])
					rationale := fmt.Sprintf("%v", dm["rationale"])
					tierColor := styleSuccess
					if tier == "remote" {
						tierColor = styleWarning
					}
					sb.WriteString(fmt.Sprintf("  %s  %s\n", tierColor.Render(padRight(tier, 10)), styleDim.Render(rationale)))
				}
			}
		}
	}
	return sb.String()
}

func runGoals(c *Client) string {
	data, err := c.GetGoals()
	if err != nil {
		return styleDanger.Render("✗ " + err.Error())
	}
	var sb strings.Builder
	sb.WriteString(styleLabel.Render("● Sovereign Goals") + "\n")
	sb.WriteString(prettyJSON(data))
	return sb.String()
}

func runPostGoal(c *Client, desc string) string {
	data, err := c.PostGoal(desc)
	if err != nil {
		return styleDanger.Render("✗ " + err.Error())
	}
	return styleSuccess.Render("✓ Goal created\n") + prettyJSON(data)
}

func renderHelp() string {
	commands := [][2]string{
		{"/help", "Show this help"},
		{"/health", "Backbone health check"},
		{"/models", "List available models"},
		{"/modules", "List all brain modules + status"},
		{"/metrics", "Runtime metrics"},
		{"/therapy", "Therapy stats + session formulation"},
		{"/mastery", "Mastery log — topic class success rates"},
		{"/compute", "Compute bid stats + recent governor decisions"},
		{"/goals", "List sovereign goals"},
		{"/goal <desc>", "Create a new sovereign goal"},
		{"/target <url>", "Switch API target (e.g. http://localhost:8089)"},
		{"/model <name>", "Switch model"},
		{"/clear", "Clear conversation history"},
		{"/save", "Save current config to ~/.oricli/config.yaml"},
	}
	var sb strings.Builder
	sb.WriteString(styleLabel.Render("● Oricli CLI — Commands") + "\n\n")
	for _, c := range commands {
		sb.WriteString(fmt.Sprintf("  %s  %s\n",
			styleKeyVal.Render(padRight(c[0], 20)),
			styleDim.Render(c[1]),
		))
	}
	sb.WriteString("\n" + styleDim.Render("  Tip: type anything without / to chat — Ctrl+C to exit") + "\n")
	return sb.String()
}

// ── Formatting helpers ────────────────────────────────────────────────────────

func prettyKV(data map[string]interface{}, indent int) string {
	pad := strings.Repeat(" ", indent)
	var sb strings.Builder
	for k, v := range data {
		switch val := v.(type) {
		case map[string]interface{}:
			sb.WriteString(fmt.Sprintf("%s%s\n", pad, styleKeyVal.Render(k+":")))
			sb.WriteString(prettyKV(val, indent+2))
		default:
			sb.WriteString(fmt.Sprintf("%s%s  %v\n", pad, styleKeyVal.Render(padRight(k, 20)), val))
		}
	}
	return sb.String()
}

func prettyJSON(data interface{}) string {
	b, err := json.MarshalIndent(data, "  ", "  ")
	if err != nil {
		return fmt.Sprintf("  %v\n", data)
	}
	return styleDim.Render(string(b)) + "\n"
}

func padRight(s string, n int) string {
	if len(s) >= n {
		return s
	}
	return s + strings.Repeat(" ", n-len(s))
}
