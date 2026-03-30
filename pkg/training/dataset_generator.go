package training

// DatasetGenerator builds Alpaca-format training examples for structured
// output fine-tuning. Two sources:
//  1. Synthetic: template-based expansion of seed examples (programmatic, no LLM)
//  2. Live: real PAD sessions + Forge tool records pulled from PocketBase
//
// Usage:
//
//	gen := NewDatasetGenerator(pbClient) // pbClient may be nil (synthetic only)
//	examples, err := gen.Generate(ctx, 200)
//	jsonl, err := gen.ExportJSONL(examples)

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"strings"
	"time"
)

// ─────────────────────────────────────────────────────────────────────────────
// PocketBase minimal client interface (avoids import cycle with pkg/pb)
// ─────────────────────────────────────────────────────────────────────────────

// PBLister is the minimal PocketBase interface used for dataset pulls.
type PBLister interface {
	ListRecords(ctx context.Context, collection string, page, perPage int, filter string) ([]map[string]interface{}, error)
}

// ─────────────────────────────────────────────────────────────────────────────
// Generator
// ─────────────────────────────────────────────────────────────────────────────

// DatasetGenerator produces AlpacaExamples from schema patterns + live PB data.
type DatasetGenerator struct {
	PB       PBLister // may be nil — disables PB pull
	Patterns []SchemaPattern
	rng      *rand.Rand
}

// NewDatasetGenerator creates a generator.
func NewDatasetGenerator(pb PBLister) *DatasetGenerator {
	return &DatasetGenerator{
		PB:       pb,
		Patterns: AllPatterns(),
		rng:      rand.New(rand.NewSource(time.Now().UnixNano())),
	}
}

// GenerateStats summarises dataset composition.
type GenerateStats struct {
	Total      int            `json:"total"`
	ByPattern  map[string]int `json:"by_pattern"`
	SeedBased  int            `json:"seed_based"`
	PBPulled   int            `json:"pb_pulled"`
}

// Generate builds examples targeting countPerPattern per schema category.
// If PB is wired, also pulls real sessions as additional examples.
func (g *DatasetGenerator) Generate(ctx context.Context, countPerPattern int) ([]AlpacaExample, GenerateStats) {
	stats := GenerateStats{ByPattern: make(map[string]int)}
	var all []AlpacaExample

	for _, p := range g.Patterns {
		examples := g.expandPattern(p, countPerPattern)
		all = append(all, examples...)
		stats.ByPattern[p.Name] = len(examples)
		stats.SeedBased += len(examples)
	}

	// Pull live PB examples if wired
	if g.PB != nil {
		live, n := g.pullLiveSessions(ctx)
		all = append(all, live...)
		stats.PBPulled = n
	}

	// Shuffle so patterns interleave
	g.rng.Shuffle(len(all), func(i, j int) { all[i], all[j] = all[j], all[i] })

	stats.Total = len(all)
	log.Printf("[DatasetGenerator] total=%d seed=%d pb=%d", stats.Total, stats.SeedBased, stats.PBPulled)
	return all, stats
}

// ExportJSONL serialises examples to newline-delimited JSON for Axolotl.
func (g *DatasetGenerator) ExportJSONL(examples []AlpacaExample) (string, error) {
	var sb strings.Builder
	for _, ex := range examples {
		b, err := json.Marshal(ex)
		if err != nil {
			return "", fmt.Errorf("marshal example: %w", err)
		}
		sb.Write(b)
		sb.WriteByte('\n')
	}
	return sb.String(), nil
}

// ─────────────────────────────────────────────────────────────────────────────
// Synthetic expansion
// ─────────────────────────────────────────────────────────────────────────────

// expandPattern generates count examples by cycling through seed examples and
// applying lightweight topic substitution for variety.
func (g *DatasetGenerator) expandPattern(p SchemaPattern, count int) []AlpacaExample {
	out := make([]AlpacaExample, 0, count)
	seeds := p.SeedExamples

	if len(seeds) == 0 {
		return out
	}

	for i := 0; i < count; i++ {
		seed := seeds[i%len(seeds)]

		input := seed.Input
		output := seed.Output

		// For variety beyond the seed count, apply topic substitution
		if i >= len(seeds) {
			input, output = g.varyExample(p.Name, seed, i)
		}

		out = append(out, AlpacaExample{
			Instruction: p.SystemPrompt,
			Input:       buildUserMessage(p.UserTemplate, input),
			Output:      output,
		})
	}

	return out
}

// buildUserMessage substitutes {{.Input}} in the template with the actual input.
// For patterns with multi-field templates, the input is used verbatim.
func buildUserMessage(template, input string) string {
	return strings.ReplaceAll(template, "{{.Input}}", input)
}

// varyExample produces a variant of a seed by substituting topic keywords.
// This gives the model exposure to diverse phrasing without requiring LLM generation.
func (g *DatasetGenerator) varyExample(pattern string, seed SeedExample, idx int) (string, string) {
	switch pattern {
	case "pad_decompose":
		return g.varyDecompose(seed, idx)
	case "critic_score":
		return seed.Input, seed.Output // critic examples are dense — repeat is fine
	case "goal_plan":
		return g.varyGoalPlan(seed, idx)
	default:
		return seed.Input, seed.Output
	}
}

// Topic pools for decompose variety
var decomposeTopics = []struct {
	query    string
	strategy string
	output   string
}{
	{
		"How does the Bitcoin Lightning Network work and what are its limitations?",
		"parallel",
		`{"strategy":"parallel","tasks":[{"id":"t1","goal":"Explain Lightning Network payment channel mechanism and HTLC"},{"id":"t2","goal":"Analyse Lightning Network scalability: throughput, routing complexity"},{"id":"t3","goal":"Identify current limitations: liquidity, channel management, and attack vectors"}],"rationale":"Three independent technical angles covering mechanics, scalability, and limitations"}`,
	},
	{
		"What is 2 + 2?",
		"single",
		`{"strategy":"single","tasks":[{"id":"t1","goal":"What is 2 + 2?"}],"rationale":"Simple arithmetic with a single direct answer"}`,
	},
	{
		"Research open-source LLM alternatives to GPT-4 including Llama, Mistral, and Qwen models, comparing benchmarks, licensing, and hardware requirements.",
		"parallel",
		`{"strategy":"parallel","tasks":[{"id":"t1","goal":"Survey Llama model family: versions, benchmarks, and Meta licensing terms"},{"id":"t2","goal":"Survey Mistral model family: Mistral-7B, Mixtral, licensing, and benchmark performance"},{"id":"t3","goal":"Survey Qwen model family: sizes, multilingual capabilities, and Alibaba licensing"},{"id":"t4","goal":"Compare hardware requirements across all three families for inference and fine-tuning"}],"rationale":"Each model family and hardware comparison is an independent research track"}`,
	},
	{
		"How do I write a for loop in JavaScript?",
		"single",
		`{"strategy":"single","tasks":[{"id":"t1","goal":"How do I write a for loop in JavaScript?"}],"rationale":"Simple direct programming question"}`,
	},
	{
		"Analyse the impact of containerisation on DevOps workflows covering Docker, Kubernetes, security implications, and cost management in cloud environments.",
		"parallel",
		`{"strategy":"parallel","tasks":[{"id":"t1","goal":"Explain how Docker and container images changed development and deployment workflows"},{"id":"t2","goal":"Describe Kubernetes orchestration: deployments, services, and operational complexity"},{"id":"t3","goal":"Identify container security concerns: image vulnerabilities, runtime isolation, and CVE management"},{"id":"t4","goal":"Analyse cloud container cost management: sizing, spot instances, and cluster autoscaling"}],"rationale":"Four non-overlapping dimensions: tooling, orchestration, security, and cost"}`,
	},
}

func (g *DatasetGenerator) varyDecompose(seed SeedExample, idx int) (string, string) {
	topic := decomposeTopics[idx%len(decomposeTopics)]
	return topic.query, topic.output
}

var goalTopics = []struct {
	objective string
	output    string
}{
	{
		"Produce a technical deep-dive on WebAssembly for server-side workloads",
		`{"nodes":[{"id":"sg1","description":"Survey WebAssembly runtime environments for server-side: Wasmtime, WasmEdge, WAMR","depends_on":[]},{"id":"sg2","description":"Benchmark WASM server-side performance vs native Go/Rust for CPU-bound tasks","depends_on":["sg1"]},{"id":"sg3","description":"Identify use cases: plugin systems, sandboxing, and edge compute","depends_on":["sg1"]},{"id":"sg4","description":"Write technical summary with adoption recommendations","depends_on":["sg2","sg3"]}]}`,
	},
	{
		"Develop a security audit checklist for a sovereign AI deployment",
		`{"nodes":[{"id":"sg1","description":"Identify attack surface: API endpoints, model inputs, tool execution, and network exposure","depends_on":[]},{"id":"sg2","description":"Research AI-specific threats: prompt injection, model extraction, and jailbreaks","depends_on":["sg1"]},{"id":"sg3","description":"Compile infrastructure hardening checklist: TLS, auth, secrets management","depends_on":[]},{"id":"sg4","description":"Combine findings into a prioritised audit checklist with severity ratings","depends_on":["sg2","sg3"]}]}`,
	},
}

func (g *DatasetGenerator) varyGoalPlan(seed SeedExample, idx int) (string, string) {
	topic := goalTopics[idx%len(goalTopics)]
	return topic.objective, topic.output
}

// ─────────────────────────────────────────────────────────────────────────────
// PocketBase pull
// ─────────────────────────────────────────────────────────────────────────────

// pullLiveSessions pulls real PAD sessions and Forge tool records and converts
// them to AlpacaExamples. Returns examples and count.
func (g *DatasetGenerator) pullLiveSessions(ctx context.Context) ([]AlpacaExample, int) {
	var out []AlpacaExample

	// PAD sessions → decompose examples
	padRecords, err := g.PB.ListRecords(ctx, "pad_sessions", 1, 50, "")
	if err != nil {
		log.Printf("[DatasetGenerator] PB pad_sessions error: %v", err)
	} else {
		for _, rec := range padRecords {
			ex := g.padSessionToExample(rec)
			if ex != nil {
				out = append(out, *ex)
			}
		}
	}

	// Forge tools → generate examples
	forgeRecords, err := g.PB.ListRecords(ctx, "forge_tools", 1, 50, "")
	if err != nil {
		log.Printf("[DatasetGenerator] PB forge_tools error: %v", err)
	} else {
		for _, rec := range forgeRecords {
			ex := g.forgeToolToExample(rec)
			if ex != nil {
				out = append(out, *ex)
			}
		}
	}

	return out, len(out)
}

func (g *DatasetGenerator) padSessionToExample(rec map[string]interface{}) *AlpacaExample {
	query, _ := rec["query"].(string)
	strategy, _ := rec["strategy"].(string)
	tasksRaw, _ := rec["tasks"].(string)

	if query == "" || strategy == "" || tasksRaw == "" {
		return nil
	}

	// Reconstruct minimal decomposition JSON from stored fields
	output := fmt.Sprintf(`{"strategy":%q,"tasks":%s,"rationale":"extracted from live session"}`,
		strategy, tasksRaw)

	p := padDecompose()
	return &AlpacaExample{
		Instruction: p.SystemPrompt,
		Input:       buildUserMessage(p.UserTemplate, query),
		Output:      output,
	}
}

func (g *DatasetGenerator) forgeToolToExample(rec map[string]interface{}) *AlpacaExample {
	name, _ := rec["name"].(string)
	description, _ := rec["description"].(string)
	source, _ := rec["source"].(string)
	params, _ := rec["parameters"].(string)

	if name == "" || source == "" {
		return nil
	}

	output := fmt.Sprintf(`{"description":%q,"parameters":%s,"source":%q}`,
		description, params, source)

	p := forgeGenerate()
	input := fmt.Sprintf("NAME: %s\nTASK: %s\nIO SPEC: see parameters", name, description)
	return &AlpacaExample{
		Instruction: p.SystemPrompt,
		Input:       buildUserMessage(p.UserTemplate, input),
		Output:      output,
	}
}
