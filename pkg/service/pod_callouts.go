package service

import (
	"fmt"
	"math/rand"
	"time"
)

// podCallouts holds the personality lines shown when Oricli routes to RunPod.
// Tone: honest, direct, a little self-aware — not dry, not chatty-assistant.

var callouts = struct {
	spinning []string // first request, pod being created
	warming  []string // pod exists but model still loading
	fallback []string // had to fall back to local Ollama
}{
	spinning: []string{
		"*Spinning up a dedicated GPU pod — leaving the 3B world behind for this one.*\n\n",
		"*Pulling in dedicated compute. Give it ~2 min while the model downloads.*\n\n",
		"*This one needs more horsepower. Kicking off a GPU pod now — sit tight.*\n\n",
		"*The local model was punching above its weight. Routing to proper inference — back in a moment.*\n\n",
		"*Calling in the big iron. Model download in progress — worth it.*\n\n",
		"*Escalating to dedicated GPU inference. The CPU stack had its limits.*\n\n",
	},
	warming: []string{
		"*Pod's still loading. Model's heavy — almost there.*\n\n",
		"*Inference pod is warming up. Shouldn't be much longer.*\n\n",
		"*GPU pod is live, model's still initializing. Hang tight.*\n\n",
		"*Almost — pod's up, vLLM is loading weights.*\n\n",
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
// kind: "spinning" | "warming" | "fallback"
func podCallout(kind string) string {
	var pool []string
	switch kind {
	case "spinning":
		pool = callouts.spinning
	case "warming":
		pool = callouts.warming
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

// podCalloutWithModel returns a callout that names the model being loaded.
// Used when we know the model tier before pod creation completes.
func podCalloutWithModel(modelName string) string {
	lines := []string{
		fmt.Sprintf("*Spinning up a GPU pod to load %s. Give it a moment.*\n\n", modelName),
		fmt.Sprintf("*Routing to dedicated inference — %s loading now. ~2 min.*\n\n", modelName),
		fmt.Sprintf("*Pulling %s off the shelf. The local stack doesn't cut it for this.*\n\n", modelName),
		fmt.Sprintf("*%s needs real hardware. Pod spinning up — sit tight.*\n\n", modelName),
	}
	return lines[rand.Intn(len(lines))] //nolint:gosec
}
