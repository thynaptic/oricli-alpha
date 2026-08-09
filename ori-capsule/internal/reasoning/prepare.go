// Package reasoning is the capsule's zero-extra-LLM cognition pack:
// precompute, trap checks, response plan, S1/S2 classify, load trim,
// epistemic filter, planning helpers, and single-inject reframes.
// No multi-gen engines, no therapy product, no chat-path retries.
package reasoning

import "strings"

// ChatMessage is a minimal role/content pair for prepare.
type ChatMessage struct {
	Role    string
	Content string
}

// PrepareResult is the output of Prepare (no LLM calls).
type PrepareResult struct {
	Messages   []ChatMessage
	SystemExtra string
	Meta       map[string]any
}

// Prepare runs all zero-latency reasoning helpers before BYOK chat.
// May trim messages under elevated load (fewer tokens — not more latency).
func Prepare(msgs []ChatMessage, lastUser string) PrepareResult {
	maps := toMaps(msgs)
	load := MeasureLoad(maps)
	var surgery SurgeryResult
	if load.Tier != LoadNormal {
		maps, surgery = TrimLoad(maps, load)
	}

	var blocks []string
	pre := Compute(lastUser)
	if facts := FormatPrecomputeInjection(pre); facts != "" {
		blocks = append(blocks, facts)
	}
	traps := Detect(lastUser)
	if trapBlock := FormatTrapInjection(traps); trapBlock != "" {
		blocks = append(blocks, trapBlock)
	}
	plan := PlanResponse(lastUser)
	blocks = append(blocks, plan.FormatDirective())

	demand := ClassifyProcess(lastUser, taskClassFor(plan.Action))
	if h := FormatProcessHint(demand); h != "" {
		blocks = append(blocks, h)
	}
	hint := ClassifyHint(lastUser)
	if h := FormatHintDirective(hint); h != "" {
		blocks = append(blocks, h)
	}
	if r := CollectReframes(lastUser); r != "" {
		blocks = append(blocks, r)
	}
	if r := CollectRuminationInject(maps); r != "" {
		blocks = append(blocks, r)
	}

	meta := map[string]any{
		"response_plan": map[string]string{
			"action": string(plan.Action), "structure": string(plan.Structure), "length": string(plan.Length),
		},
		"process_tier":    demand.Tier.String(),
		"process_score":   demand.Score,
		"reasoning_hint":  string(hint),
		"load_tier":       load.TierLabel,
		"load_total":      load.TotalLoad,
		"surgery_removed": surgery.RemovedMsgs,
		"precompute":      len(pre),
		"traps":           len(traps),
	}

	return PrepareResult{
		Messages:    fromMaps(maps),
		SystemExtra: strings.Join(blocks, "\n\n"),
		Meta:        meta,
	}
}

func taskClassFor(a ActionType) string {
	switch a {
	case ActionBuild, ActionDiagnose:
		return "technical"
	case ActionCompare:
		return "comparative"
	case ActionCreate:
		return "procedural"
	default:
		return "general"
	}
}

func toMaps(msgs []ChatMessage) []map[string]string {
	out := make([]map[string]string, len(msgs))
	for i, m := range msgs {
		out[i] = map[string]string{"role": m.Role, "content": m.Content}
	}
	return out
}

func fromMaps(msgs []map[string]string) []ChatMessage {
	out := make([]ChatMessage, len(msgs))
	for i, m := range msgs {
		out[i] = ChatMessage{Role: m["role"], Content: m["content"]}
	}
	return out
}
