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

	case "/process":
		return runProcess(client), true

	case "/cogload":
		return runCogLoad(client), true

	case "/ruminate":
		return runRumination(client), true

	case "/mindset":
		return runMindset(client), true

	case "/hope":
		return runHope(client), true

	case "/defeat":
		return runDefeat(client), true

	case "/conformity":
		return runConformity(client), true

	case "/ideocapture":
		return runIdeoCapture(client), true

	case "/coalition":
		return runCoalition(client), true

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

func runCogLoad(c *Client) string {
	data, err := c.GetCogLoadStats()
	if err != nil {
		return styleDanger.Render("✗ " + err.Error())
	}
	var sb strings.Builder
	sb.WriteString(styleLabel.Render("● Cognitive Load Manager (Sweller CLT)") + "\n")
	if m, ok := data["measurements"].(float64); ok && m == 0 {
		sb.WriteString(styleDim.Render("  No load data yet — accumulates after first requests\n"))
		return sb.String()
	}
	fields := []struct{ key, label string }{
		{"avg_intrinsic", "Avg Intrinsic"},
		{"avg_extraneous", "Avg Extraneous"},
		{"avg_germane", "Avg Germane"},
		{"avg_total_load", "Avg Total Load"},
	}
	for _, f := range fields {
		if v, ok := data[f.key].(float64); ok {
			bar := loadBar(v)
			color := styleSuccess
			if v > 0.6 {
				color = styleWarning
			}
			if v > 0.9 {
				color = styleDanger
			}
			sb.WriteString(fmt.Sprintf("  %s  %s %s\n",
				styleKeyVal.Render(padRight(f.label, 18)),
				color.Render(bar),
				styleDim.Render(fmt.Sprintf("%.2f", v))))
		}
	}
	if sr, ok := data["surgery_rate"].(float64); ok {
		sb.WriteString(fmt.Sprintf("  %s  %s\n",
			styleKeyVal.Render(padRight("Surgery Rate", 18)),
			styleAccent.Render(fmt.Sprintf("%.0f%%", sr*100))))
	}
	if m, ok := data["measurements"].(float64); ok {
		sb.WriteString(fmt.Sprintf("  %s  %s\n",
			styleKeyVal.Render(padRight("Measurements", 18)),
			styleDim.Render(fmt.Sprintf("%.0f", m))))
	}
	return sb.String()
}

// loadBar renders a mini ASCII bar for a [0-1] load score.
func loadBar(v float64) string {
	total := 10
	filled := int(v * float64(total))
	if filled > total {
		filled = total
	}
	bar := ""
	for i := 0; i < total; i++ {
		if i < filled {
			bar += "█"
		} else {
			bar += "░"
		}
	}
	return bar
}

func runProcess(c *Client) string {
	data, err := c.GetProcessStats()
	if err != nil {
		return styleDanger.Render("✗ " + err.Error())
	}
	var sb strings.Builder
	sb.WriteString(styleLabel.Render("● Dual Process Engine — S1/S2 Mismatch Rates") + "\n")
	if stats, ok := data["stats"].([]interface{}); ok {
		if len(stats) == 0 {
			sb.WriteString(styleDim.Render("  No process data yet — accumulates after first audited responses\n"))
		}
		for _, s := range stats {
			if sm, ok := s.(map[string]interface{}); ok {
				class := fmt.Sprintf("%v", sm["task_class"])
				total := fmt.Sprintf("%.0f", sm["total"])
				rate := 0.0
				if r, ok := sm["mismatch_rate"].(float64); ok {
					rate = r
				}
				rateStr := fmt.Sprintf("%.0f%%", rate*100)
				rateStyle := styleSuccess
				if rate > 0.3 {
					rateStyle = styleDanger
				} else if rate > 0.15 {
					rateStyle = styleWarning
				}
				sb.WriteString(fmt.Sprintf("  %s  %s mismatches  %s\n",
					styleKeyVal.Render(padRight(class, 20)),
					styleDim.Render(total+" total,"),
					rateStyle.Render(rateStr)))
			}
		}
	} else {
		sb.WriteString(prettyJSON(data))
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
		{"/process", "Dual Process stats — S1/S2 mismatch rates per topic class"},
		{"/cogload", "Cognitive Load stats — avg load components + surgery rate"},
		{"/ruminate", "Rumination Detector stats — loop detection rate + interrupt rate"},
		{"/mindset", "Growth Mindset stats — per-topic mindset vectors (Dweck)"},
		{"/hope", "Hope Circuit stats — agency activation rate + controllability evidence"},
		{"/defeat", "Social Defeat Recovery stats — correction pressure + withdrawal detection"},
		{"/conformity", "Agency & Conformity Shield stats — authority/consensus pressure + shield rate"},
		{"/ideocapture", "Ideological Capture Detector stats — frame density + blank screen resets"},
		{"/coalition", "Coalition Bias Detector stats — competitive/adversarial framing + anchor rate (Robbers Cave)"},
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

func runRumination(c *Client) string {
	data, err := c.GetRuminationStats()
	if err != nil {
		return styleDanger.Render("✗ " + err.Error())
	}
	var sb strings.Builder
	sb.WriteString(styleLabel.Render("● Rumination Detector (ACT / Temporal Interruption)") + "\n")
	if total, _ := data["total_scans"].(float64); total == 0 {
		sb.WriteString(styleDim.Render("  No data yet\n"))
		return sb.String()
	}
	fields := []struct{ key, label string }{
		{"total_scans", "Total Scans"},
		{"detections", "Detections"},
		{"interruptions", "Interruptions"},
	}
	for _, f := range fields {
		if v, ok := data[f.key].(float64); ok {
			sb.WriteString(fmt.Sprintf("  %s  %s\n",
				styleKeyVal.Render(padRight(f.label, 18)),
				styleDim.Render(fmt.Sprintf("%.0f", v))))
		}
	}
	if dr, ok := data["detection_rate"].(float64); ok {
		sb.WriteString(fmt.Sprintf("  %s  %s\n",
			styleKeyVal.Render(padRight("Detection Rate", 18)),
			styleAccent.Render(fmt.Sprintf("%.0f%%", dr*100))))
	}
	if ir, ok := data["interrupt_rate"].(float64); ok {
		sb.WriteString(fmt.Sprintf("  %s  %s\n",
			styleKeyVal.Render(padRight("Interrupt Rate", 18)),
			styleSuccess.Render(fmt.Sprintf("%.0f%%", ir*100))))
	}
	return sb.String()
}

func runMindset(c *Client) string {
	data, err := c.GetMindsetStats()
	if err != nil {
		return styleDanger.Render("✗ " + err.Error())
	}
	var sb strings.Builder
	sb.WriteString(styleLabel.Render("● Growth Mindset Tracker (Dweck)") + "\n")
	if total, _ := data["total_scans"].(float64); total == 0 {
		sb.WriteString(styleDim.Render("  No data yet\n"))
		// Still try to show vectors
	}
	fields := []struct{ key, label string }{
		{"total_scans", "Total Scans"},
		{"detections", "Fixed Signals"},
		{"reframes", "Reframes"},
		{"detection_rate", "Detection Rate"},
		{"reframe_rate", "Reframe Rate"},
	}
	for _, f := range fields {
		switch v := data[f.key].(type) {
		case float64:
			var s string
			if f.key == "detection_rate" || f.key == "reframe_rate" {
				s = fmt.Sprintf("%.0f%%", v*100)
			} else {
				s = fmt.Sprintf("%.0f", v)
			}
			sb.WriteString(fmt.Sprintf("  %s  %s\n", styleKeyVal.Render(padRight(f.label, 18)), styleDim.Render(s)))
		}
	}
	// Show vectors
	vdata, verr := c.GetMindsetVectors()
	if verr == nil {
		if vecs, ok := vdata["vectors"].([]interface{}); ok && len(vecs) > 0 {
			sb.WriteString(styleLabel.Render("\n  Topic Vectors:") + "\n")
			for _, vi := range vecs {
				if vm, ok := vi.(map[string]interface{}); ok {
					topic, _ := vm["topic_class"].(string)
					tier, _ := vm["tier"].(string)
					score, _ := vm["growth_score"].(float64)
					color := styleDim
					if tier == "growth" { color = styleSuccess }
					if tier == "fixed" { color = styleDanger }
					sb.WriteString(fmt.Sprintf("    %s  %s  %s\n",
						styleDim.Render(padRight(topic, 20)),
						color.Render(padRight(tier, 8)),
						styleDim.Render(fmt.Sprintf("%.2f", score))))
				}
			}
		}
	}
	return sb.String()
}

func runHope(c *Client) string {
	data, err := c.GetHopeStats()
	if err != nil {
		return styleDanger.Render("✗ " + err.Error())
	}
	var sb strings.Builder
	sb.WriteString(styleLabel.Render("● Hope Circuit (Learned Controllability — Maier & Seligman)") + "\n")
	if total, _ := data["total_checks"].(float64); total == 0 {
		sb.WriteString(styleDim.Render("  No data yet — accumulates after first requests\n"))
		return sb.String()
	}
	fields := []struct{ key, label string }{
		{"total_checks", "Total Checks"},
		{"activations", "Activations"},
	}
	for _, f := range fields {
		if v, ok := data[f.key].(float64); ok {
			sb.WriteString(fmt.Sprintf("  %s  %s\n",
				styleKeyVal.Render(padRight(f.label, 20)),
				styleDim.Render(fmt.Sprintf("%.0f", v))))
		}
	}
	if ar, ok := data["activation_rate"].(float64); ok {
		color := styleDim
		if ar > 0.3 { color = styleSuccess }
		sb.WriteString(fmt.Sprintf("  %s  %s\n",
			styleKeyVal.Render(padRight("Activation Rate", 20)),
			color.Render(fmt.Sprintf("%.0f%%", ar*100))))
	}
	return sb.String()
}

func runDefeat(c *Client) string {
	data, err := c.GetDefeatStats()
	if err != nil {
		return styleDanger.Render("✗ " + err.Error())
	}
	var sb strings.Builder
	sb.WriteString(styleLabel.Render("● Social Defeat Recovery (Social Defeat Model + Monster Study)") + "\n")
	if total, _ := data["total_scans"].(float64); total == 0 {
		sb.WriteString(styleDim.Render("  No data yet\n"))
		return sb.String()
	}
	fields := []struct{ key, label string }{
		{"total_scans", "Total Scans"},
		{"detections", "Defeat Signals"},
		{"recoveries", "Recoveries"},
		{"detection_rate", "Detection Rate"},
		{"recovery_rate", "Recovery Rate"},
	}
	for _, f := range fields {
		switch v := data[f.key].(type) {
		case float64:
			var s string
			if f.key == "detection_rate" || f.key == "recovery_rate" {
				s = fmt.Sprintf("%.0f%%", v*100)
			} else {
				s = fmt.Sprintf("%.0f", v)
			}
			color := styleDim
			if (f.key == "detection_rate" && v > 0.1) { color = styleWarning }
			if (f.key == "recovery_rate" && v > 0.5) { color = styleSuccess }
			sb.WriteString(fmt.Sprintf("  %s  %s\n", styleKeyVal.Render(padRight(f.label, 18)), color.Render(s)))
		}
	}
	return sb.String()
}

func runConformity(c *Client) string {
	data, err := c.GetConformityStats()
	if err != nil {
		return styleDanger.Render("✗ " + err.Error())
	}
	var sb strings.Builder
	sb.WriteString(styleLabel.Render("● Agency & Conformity Shield (Milgram + Asch)") + "\n")
	if total, _ := data["total_scans"].(float64); total == 0 {
		sb.WriteString(styleDim.Render("  No data yet\n"))
		return sb.String()
	}
	fields := []struct{ key, label string }{
		{"total_scans", "Total Scans"},
		{"authority_detections", "Authority Signals (Milgram)"},
		{"consensus_detections", "Consensus Signals (Asch)"},
		{"shields_fired", "Shields Fired"},
		{"shield_rate", "Shield Rate"},
	}
	for _, f := range fields {
		switch v := data[f.key].(type) {
		case float64:
			var s string
			if f.key == "shield_rate" {
				s = fmt.Sprintf("%.0f%%", v*100)
			} else {
				s = fmt.Sprintf("%.0f", v)
			}
			color := styleDim
			if f.key == "shields_fired" && v > 0 { color = styleWarning }
			if f.key == "shield_rate" && v > 0.05 { color = styleSuccess }
			sb.WriteString(fmt.Sprintf("  %s  %s\n", styleKeyVal.Render(padRight(f.label, 26)), color.Render(s)))
		}
	}
	return sb.String()
}

func runIdeoCapture(c *Client) string {
	data, err := c.GetIdeoCaptureStats()
	if err != nil {
		return styleDanger.Render("✗ " + err.Error())
	}
	var sb strings.Builder
	sb.WriteString(styleLabel.Render("● Ideological Capture Detector (The Third Wave)") + "\n")
	if total, _ := data["total_scans"].(float64); total == 0 {
		sb.WriteString(styleDim.Render("  No data yet\n"))
		return sb.String()
	}
	fields := []struct{ key, label string }{
		{"total_scans", "Total Scans"},
		{"detections", "Capture Signals"},
		{"resets_fired", "Blank Screen Resets"},
		{"reset_rate", "Reset Rate"},
	}
	for _, f := range fields {
		switch v := data[f.key].(type) {
		case float64:
			var s string
			if f.key == "reset_rate" {
				s = fmt.Sprintf("%.0f%%", v*100)
			} else {
				s = fmt.Sprintf("%.0f", v)
			}
			color := styleDim
			if f.key == "resets_fired" && v > 0 { color = styleWarning }
			if f.key == "reset_rate" && v > 0.05 { color = styleSuccess }
			sb.WriteString(fmt.Sprintf("  %s  %s\n", styleKeyVal.Render(padRight(f.label, 22)), color.Render(s)))
		}
	}
	if cats, ok := data["by_category"].(map[string]interface{}); ok && len(cats) > 0 {
		sb.WriteString("  " + styleDim.Render("by category:") + "\n")
		for cat, v := range cats {
			if count, ok := v.(float64); ok && count > 0 {
				sb.WriteString(fmt.Sprintf("    %s  %s\n", styleKeyVal.Render(padRight(cat, 16)), styleDim.Render(fmt.Sprintf("%.0f", count))))
			}
		}
	}
	return sb.String()
}

func runCoalition(c *Client) string {
	data, err := c.GetCoalitionStats()
	if err != nil {
		return styleDanger.Render("✗ " + err.Error())
	}
	var sb strings.Builder
	sb.WriteString(styleLabel.Render("● Coalition Bias Detector (Robbers Cave)") + "\n")
	if total, _ := data["total_scans"].(float64); total == 0 {
		sb.WriteString(styleDim.Render("  No data yet\n"))
		return sb.String()
	}
	fields := []struct{ key, label string }{
		{"total_scans", "Total Scans"},
		{"detections", "Coalition Frames"},
		{"anchors_fired", "Anchors Fired"},
		{"anchor_rate", "Anchor Rate"},
	}
	for _, f := range fields {
		switch v := data[f.key].(type) {
		case float64:
			var s string
			if f.key == "anchor_rate" {
				s = fmt.Sprintf("%.0f%%", v*100)
			} else {
				s = fmt.Sprintf("%.0f", v)
			}
			color := styleDim
			if f.key == "anchors_fired" && v > 0 { color = styleWarning }
			if f.key == "anchor_rate" && v > 0.05 { color = styleSuccess }
			sb.WriteString(fmt.Sprintf("  %s  %s\n", styleKeyVal.Render(padRight(f.label, 18)), color.Render(s)))
		}
	}
	if types, ok := data["by_frame_type"].(map[string]interface{}); ok && len(types) > 0 {
		sb.WriteString("  " + styleDim.Render("by frame type:") + "\n")
		for ft, v := range types {
			if count, ok := v.(float64); ok && count > 0 {
				sb.WriteString(fmt.Sprintf("    %s  %s\n", styleKeyVal.Render(padRight(ft, 16)), styleDim.Render(fmt.Sprintf("%.0f", count))))
			}
		}
	}
	return sb.String()
}
