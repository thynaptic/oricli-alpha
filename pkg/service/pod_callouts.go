package service

import (
	"fmt"
	"math/rand"
	"time"
)

// podCallouts holds the personality lines shown when Oricli routes to RunPod.
// Tone: honest, direct, a little self-aware — not dry, not chatty-assistant.

var callouts = struct {
	spinning   []string // first request, pod being created — matter-of-fact
	escalation []string // first request, pod being created — punchy/dramatic variant
	warming    []string // pod exists but model still loading
	handoff    []string // pod just became ready — transition into the real response
	fallback   []string // had to fall back to local Ollama
}{
	spinning: []string{
		"*Spinning up a dedicated GPU pod — leaving the 3B world behind for this one.*\n\n",
		"*Pulling in dedicated compute. Give it ~2 min while the model downloads.*\n\n",
		"*This one needs more horsepower. Kicking off a GPU pod now — sit tight.*\n\n",
		"*The local model was punching above its weight. Routing to proper inference — back in a moment.*\n\n",
		"*Calling in the big iron. Model download in progress — worth it.*\n\n",
		"*Escalating to dedicated GPU inference. The CPU stack had its limits.*\n\n",
	},
	escalation: []string{
		"*Alright — this one gets the full stack. Spinning up GPU inference now.*\n\n",
		"*Not a 3B problem. Pulling real compute — give it a moment.*\n\n",
		"*We're going heavier. GPU pod incoming, model loading shortly.*\n\n",
		"*Time to stop pretending the local model was enough. Escalating.*\n\n",
		"*This deserves proper hardware. Spinning up — won't be long.*\n\n",
		"*Routing up the chain. Dedicated inference pod launching now.*\n\n",
		"*The CPU was a placeholder. Bringing in the actual firepower.*\n\n",
	},
	warming: []string{
		"*Pod's still loading. Model's heavy — almost there.*\n\n",
		"*Inference pod is warming up. Shouldn't be much longer.*\n\n",
		"*GPU pod is live, model's still initializing. Hang tight.*\n\n",
		"*Almost — pod's up, vLLM is loading weights.*\n\n",
	},
	handoff: []string{
		"*Alright — we're live. Let's do this properly.*\n\n",
		"*GPU's ready. Handing off to the real model now.*\n\n",
		"*Pod's warm. Switching over — here we go.*\n\n",
		"*We're in business. Full inference online.*\n\n",
		"*That's a live pod. Let's get into it.*\n\n",
		"*GPU is up. No more holding back.*\n\n",
		"*Dedicated inference ready. You've got the full model now.*\n\n",
	},
	fallback: []string{
		"*GPU pod isn't ready yet — local model covering for now. Next message hits the real thing.*\n\n",
		"*Running on local inference while the pod spins up. Quality may vary.*\n\n",
		"*Pod's still warming — falling back to local for this one.*\n\n",
	},
}

func init() {
	rand.New(rand.NewSource(time.Now().UnixNano())) //nolint:gosec
}

// podCallout returns a callout line for the given situation.
// kind: "spinning" | "escalation" | "warming" | "handoff" | "fallback"
func podCallout(kind string) string {
	var pool []string
	switch kind {
	case "spinning":
		pool = callouts.spinning
	case "escalation":
		pool = callouts.escalation
	case "warming":
		pool = callouts.warming
	case "handoff":
		pool = callouts.handoff
	case "fallback":
		pool = callouts.fallback
	default:
		return ""
	}
	if len(pool) == 0 {
		return ""
	}
	return pool[rand.Intn(len(pool))] //nolint:gosec
}

// podCalloutWithModel returns an escalation callout that names the model being loaded.
func podCalloutWithModel(modelName string) string {
	lines := []string{
		fmt.Sprintf("*Escalating to %s. GPU pod spinning up — give it a moment.*\n\n", modelName),
		fmt.Sprintf("*Routing to dedicated inference — %s loading now.*\n\n", modelName),
		fmt.Sprintf("*The local stack doesn't cut it for this. Pulling %s off the shelf.*\n\n", modelName),
		fmt.Sprintf("*%s needs real hardware. Pod incoming — sit tight.*\n\n", modelName),
		fmt.Sprintf("*Going heavier: %s on GPU. Won't be long.*\n\n", modelName),
	}
	return lines[rand.Intn(len(lines))] //nolint:gosec
}

// podHandoff returns a success handoff line, optionally naming the model.
func podHandoff(modelName string) string {
	if modelName == "" {
		return podCallout("handoff")
	}
	lines := []string{
		fmt.Sprintf("*Alright — %s is live. Let's do this properly.*\n\n", modelName),
		fmt.Sprintf("*%s is ready. Handing off — here we go.*\n\n", modelName),
		fmt.Sprintf("*We're in business. %s online.*\n\n", modelName),
		fmt.Sprintf("*That's a live %s pod. Full inference from here.*\n\n", modelName),
		fmt.Sprintf("*%s warm and ready. No more holding back.*\n\n", modelName),
	}
	return lines[rand.Intn(len(lines))] //nolint:gosec
}
