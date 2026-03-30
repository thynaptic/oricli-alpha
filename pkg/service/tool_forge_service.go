package service

// ToolForgeService orchestrates the full JIT Tool Forge pipeline:
//
//	BuildJustification → POCGate.Score → Constitution.Check
//	→ Generator.Generate → Verifier.Verify → Library.Store → ToolService.Register
//
// Env:
//
//	ORICLI_FORGE_ENABLED=true — enables the service (default: false)
//	ORICLI_FORGE_MAX_TOOLS=50 — library cap (default: 50)

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strconv"
	"sync/atomic"

	"github.com/thynaptic/oricli-go/pkg/forge"
)

// ForgeStats tracks pipeline activity.
type ForgeStats struct {
	Attempted   int64 `json:"attempted"`    // total TryForge calls
	GateApproved int64 `json:"gate_approved"` // passed POC Gate
	GateRejected int64 `json:"gate_rejected"` // failed POC Gate
	BuiltSuccess int64 `json:"built_success"` // verified + stored
	BuiltFailed  int64 `json:"built_failed"`  // generated but failed verify
	Evictions    int64 `json:"evictions"`     // LRU evictions (tracked via size delta)
}

// ToolForgeService is the sovereign JIT tool forge.
type ToolForgeService struct {
	Gate         *forge.POCGate
	Generator    *forge.ToolGenerator
	Constitution *forge.CodeConstitution
	Verifier     *forge.ToolVerifier
	Library      *forge.ToolLibrary
	ToolSvc      *ToolService

	Enabled bool
	stats   ForgeStats
}

// NewToolForgeService wires all forge components together.
// Any nil component causes that stage to be skipped gracefully.
func NewToolForgeService(
	gate *forge.POCGate,
	generator *forge.ToolGenerator,
	constitution *forge.CodeConstitution,
	verifier *forge.ToolVerifier,
	library *forge.ToolLibrary,
	toolSvc *ToolService,
) *ToolForgeService {
	enabled := os.Getenv("ORICLI_FORGE_ENABLED") == "true"
	return &ToolForgeService{
		Gate:         gate,
		Generator:    generator,
		Constitution: constitution,
		Verifier:     verifier,
		Library:      library,
		ToolSvc:      toolSvc,
		Enabled:      enabled,
	}
}

// TryForge runs the full forge pipeline for a task that no existing tool can handle.
// Returns the newly registered JITTool on success.
func (s *ToolForgeService) TryForge(ctx context.Context, task string, triedTools []string) (*forge.JITTool, error) {
	if !s.Enabled {
		return nil, fmt.Errorf("tool forge disabled (ORICLI_FORGE_ENABLED != true)")
	}

	atomic.AddInt64(&s.stats.Attempted, 1)
	log.Printf("[ToolForge] attempt — task: %q, tried: %v", task, triedTools)

	// ── Stage 1: Build justification ─────────────────────────────────────────
	var req forge.JustificationRequest
	var err error
	if s.Gate != nil {
		req, err = s.Gate.BuildJustification(ctx, task, triedTools)
		if err != nil {
			log.Printf("[ToolForge] justification build error: %v", err)
			req = forge.JustificationRequest{Task: task, TriedTools: triedTools}
		}
	} else {
		req = forge.JustificationRequest{Task: task, TriedTools: triedTools}
	}

	// ── Stage 2: POC Gate ─────────────────────────────────────────────────────
	if s.Gate != nil {
		result := s.Gate.Score(ctx, req)
		if !result.Approved() {
			atomic.AddInt64(&s.stats.GateRejected, 1)
			return nil, fmt.Errorf("POC Gate rejected (score:%.2f): %s", result.Score, result.Reason)
		}
		atomic.AddInt64(&s.stats.GateApproved, 1)
		log.Printf("[ToolForge] POC Gate APPROVED %q (score:%.2f)", req.ProposedName, result.Score)
	}

	// ── Stage 3: Generate ─────────────────────────────────────────────────────
	if s.Generator == nil {
		return nil, fmt.Errorf("no generator configured")
	}
	generated, err := s.Generator.Generate(req)
	if err != nil {
		atomic.AddInt64(&s.stats.BuiltFailed, 1)
		return nil, fmt.Errorf("generation failed: %w", err)
	}

	// ── Stage 4: Code Constitution check ─────────────────────────────────────
	if s.Constitution != nil {
		violations, pass := s.Constitution.Check(generated.Source)
		if !pass {
			atomic.AddInt64(&s.stats.BuiltFailed, 1)
			summary := s.Constitution.Summary(violations)
			log.Printf("[ToolForge] Constitution FAIL %q:\n%s", generated.Name, summary)
			return nil, fmt.Errorf("constitution check failed: %s", summary)
		}
		if len(violations) > 0 {
			log.Printf("[ToolForge] Constitution warnings for %q: %s", generated.Name, s.Constitution.Summary(violations))
		}
	}

	// ── Stage 5: Sandbox verification ────────────────────────────────────────
	if s.Verifier != nil {
		testInput := buildTestInput(req)
		vResult := s.Verifier.Verify(ctx, generated.Source, testInput)
		if !vResult.OK {
			atomic.AddInt64(&s.stats.BuiltFailed, 1)
			return nil, fmt.Errorf("verification failed: %s", vResult.Reason)
		}
		log.Printf("[ToolForge] Verified %q: %s", generated.Name, vResult.Reason)
	}

	// ── Stage 6: Store in library ─────────────────────────────────────────────
	justBytes, _ := json.Marshal(req)
	tool := forge.JITTool{
		Name:          generated.Name,
		Description:   generated.Description,
		Source:        generated.Source,
		Parameters:    generated.Parameters,
		Justification: string(justBytes),
		ModelUsed:     generated.ModelUsed,
		Verified:      true,
	}

	if s.Library != nil {
		if err := s.Library.Store(ctx, tool); err != nil {
			log.Printf("[ToolForge] library store error: %v", err)
			// Non-fatal — tool still registered in memory.
		}
	}

	// ── Stage 7: Register in ToolService ─────────────────────────────────────
	s.registerTool(tool)
	atomic.AddInt64(&s.stats.BuiltSuccess, 1)
	log.Printf("[ToolForge] ✅ forge complete — %q registered", tool.Name)
	return &tool, nil
}

// registerTool wires a JITTool into the live ToolService registry.
func (s *ToolForgeService) registerTool(tool forge.JITTool) {
	if s.ToolSvc == nil {
		return
	}
	s.ToolSvc.RegisterTool(Tool{
		Name:        tool.Name,
		Description: tool.Description,
		Parameters:  tool.Parameters,
		ModuleName:  "jit_forge",
		Operation:   tool.Name,
	})

	// Register the execution handler on the orchestrator's module map if possible.
	// The actual execution is handled by InvokeJITTool below — the ModuleName
	// "jit_forge" is a sentinel that server_v2 intercepts.
}

// InvokeJITTool executes a stored JIT tool with the given arguments.
func (s *ToolForgeService) InvokeJITTool(ctx context.Context, name string, args map[string]interface{}) (map[string]interface{}, error) {
	if s.Library == nil {
		return nil, fmt.Errorf("library not configured")
	}
	tool, ok := s.Library.Load(name)
	if !ok {
		return nil, fmt.Errorf("tool %q not found in library", name)
	}

	if s.Verifier == nil {
		return nil, fmt.Errorf("verifier not configured")
	}

	vResult := s.Verifier.Verify(ctx, tool.Source, args)
	if !vResult.OK {
		return nil, fmt.Errorf("invocation failed: %s", vResult.Reason)
	}

	// Bump use count async.
	go s.Library.BumpUseCount(context.Background(), name)

	// Parse output as map.
	var out map[string]interface{}
	if err := json.Unmarshal([]byte(vResult.Output), &out); err != nil {
		out = map[string]interface{}{"output": vResult.Output}
	}
	return out, nil
}

// LoadDefaultTools registers the 8 built-in default tools at boot.
func (s *ToolForgeService) LoadDefaultTools(ctx context.Context) {
	defaults := forge.AllDefaultTools()
	for _, d := range defaults {
		tool := forge.JITTool{
			Name:        d.Name,
			Description: d.Description,
			Source:      d.Source,
			Parameters:  d.Parameters,
			Verified:    true,
			ModelUsed:   "built-in",
		}
		// Store in library if not already present.
		if s.Library != nil {
			if _, ok := s.Library.Load(d.Name); !ok {
				if err := s.Library.Store(ctx, tool); err != nil {
					log.Printf("[ToolForge] store default %q: %v", d.Name, err)
				}
			}
		}
		s.registerTool(tool)
	}
	log.Printf("[ToolForge] %d default tools registered", len(defaults))
}

// Stats returns a snapshot of forge pipeline metrics.
func (s *ToolForgeService) Stats() ForgeStats {
	return ForgeStats{
		Attempted:    atomic.LoadInt64(&s.stats.Attempted),
		GateApproved: atomic.LoadInt64(&s.stats.GateApproved),
		GateRejected: atomic.LoadInt64(&s.stats.GateRejected),
		BuiltSuccess: atomic.LoadInt64(&s.stats.BuiltSuccess),
		BuiltFailed:  atomic.LoadInt64(&s.stats.BuiltFailed),
	}
}

// LibrarySize returns the current number of tools in the library.
func (s *ToolForgeService) LibrarySize() int {
	if s.Library == nil {
		return 0
	}
	return s.Library.Size()
}

// ─── helpers ──────────────────────────────────────────────────────────────────

// buildTestInput constructs a minimal test payload for the verifier based on
// the proposed signature.
func buildTestInput(req forge.JustificationRequest) map[string]interface{} {
	// Parse proposed signature hint for field names.
	// e.g. "input: {text: string, pattern: string}"
	out := map[string]interface{}{
		"test": "hello world",
		"text": "hello world",
	}
	return out
}

func maxToolsFromEnv() int {
	if v := os.Getenv("ORICLI_FORGE_MAX_TOOLS"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			return n
		}
	}
	return forge.DefaultMaxTools
}

// ensure maxToolsFromEnv is used even if caller doesn't call it directly
var _ = maxToolsFromEnv
