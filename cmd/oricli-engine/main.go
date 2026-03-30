// cmd/oricli-engine — Oricli Headless Engine
//
// A standalone, local-first deployment of the Sovereign Engine designed to run
// on a customer's own VPS. It boots the full Sovereign cognition stack and
// OpenAI-compatible API Gateway, but excludes Studio-only services (VDI browser,
// WorldTraveler benchmark foraging, DreamDaemon, MetacogDaemon) to minimise
// resource usage on modest hardware.
//
// Key characteristics vs the main backbone:
//   - No PocketBase dependency — uses LMDB for all persistent state
//   - No ORI Studio UI proxy (pure API, no HTML/JS served)
//   - Remote-control config sync via THYNAPTIC_CONFIG_URL (opt-in; offline by default)
//   - Single binary — deploy with: scp bin/oricli-engine user@vps:~/ && ./oricli-engine
//
// Environment variables:
//
//	ORICLI_SEED_API_KEY        — owner Bearer token (auto-generated if absent, written to .oricli/api_key)
//	ORICLI_ENGINE_PORT         — API port (default: 8089)
//	ORICLI_STATE_DIR           — state directory (default: .oricli)
//	OLLAMA_MODEL               — default chat model (default: qwen3:1.7b)
//	OLLAMA_URL                 — Ollama base URL (default: http://127.0.0.1:11434)
//	THYNAPTIC_CONFIG_URL       — remote config endpoint (empty = fully offline)
//	THYNAPTIC_CONFIG_INTERVAL  — how often to poll for config updates (default: 1h)
//	THYNAPTIC_ENGINE_ID        — stable ID for this deployment (auto-generated)
//	MAVAIA_REQUIRE_AUTH        — "true" to enforce Bearer token on all API calls (default: false)
package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/joho/godotenv"
	"github.com/thynaptic/oricli-go/pkg/api"
	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/cognition"
	"github.com/thynaptic/oricli-go/pkg/core/auth"
	"github.com/thynaptic/oricli-go/pkg/core/config"
	"github.com/thynaptic/oricli-go/pkg/core/store/memory"
	"github.com/thynaptic/oricli-go/pkg/engine"
	pb "github.com/thynaptic/oricli-go/pkg/connectors/pocketbase"
	"github.com/thynaptic/oricli-go/pkg/service"
	"github.com/thynaptic/oricli-go/pkg/sovereign"
	"github.com/thynaptic/oricli-go/pkg/swarm"
)

const (
	defaultPort     = 8089
	defaultStateDir = ".oricli"
)

func main() {
	// --gen-keys flag: generate sovereign key pair and exit.
	for _, arg := range os.Args[1:] {
		if arg == "--gen-keys" {
			runGenKeys()
			return
		}
		if arg == "--version" || arg == "-v" {
			fmt.Println("oricli-engine v1.0.0 (headless, local-first)")
			return
		}
	}

	log.Println("--- BOOTING ORICLI-ENGINE (HEADLESS, LOCAL-FIRST) ---")

	// ── 1. Environment ────────────────────────────────────────────────────────
	godotenv.Load(".env")

	stateDir := envOr("ORICLI_STATE_DIR", defaultStateDir)
	port := defaultPort
	if v := os.Getenv("ORICLI_ENGINE_PORT"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			port = n
		}
	}

	encKey := envOr("ORICLI_ENCRYPTION_KEY", "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=")

	// ── 2. Core Infrastructure ────────────────────────────────────────────────
	swarmBus := bus.NewSwarmBus(5000)

	// ── 3. Local-first Storage (LMDB — no cloud, no PocketBase required) ─────
	log.Println("[Engine] Opening local LMDB memory store...")
	memPath := stateDir + "/lmdb"
	mb, err := service.NewMemoryBridge(memPath, encKey)
	if err != nil {
		log.Fatalf("[Engine] FATAL: Failed to open LMDB at %s: %v", memPath, err)
	}
	log.Printf("[Engine] LMDB memory store ready at: %s", memPath)

	// ── 4. Auth Store (in-memory; key persisted to .oricli/api_key) ───────────
	st := memory.New()
	apiKey := bootstrapAPIKey(st, stateDir)
	log.Printf("[Engine] API key active (first 20 chars): %s...", apiKey[:min(20, len(apiKey))])

	// ── 5. Generation + Sovereign Engine ─────────────────────────────────────
	log.Println("[Engine] Initializing Sovereign Engine...")
	genService := service.NewGenerationService()

	// CostGovernor — gates RunPod complexity escalation on daily budget.
	costGovernor := service.NewCostGovernor(nil)
	genService.Governor = costGovernor

	sovEngine := cognition.NewSovereignEngine(genService, swarmBus)

	// ── 6. DAG Goal System ────────────────────────────────────────────────────
	goalDataPath := stateDir + "/objectives.jsonl"
	goalService := service.NewGoalService(goalDataPath)
	goalService.PBClient = pb.NewClientFromEnv() // nil-safe: returns noop client when env absent
	goalExecutor := service.NewGoalExecutor(goalService, nil, 30*time.Second)
	log.Println("[Engine] DAG GoalService ready.")

	// ── 7. Orchestrator + Module Registry ────────────────────────────────────
	registry := service.NewModuleRegistry("")
	orch := service.NewGoOrchestrator(swarmBus, registry)

	// ── 8. Curiosity Daemon (Epistemic Foraging — lightweight, optional) ──────
	curiosity := service.NewCuriosityDaemon(sovEngine.Graph, sovEngine.VDI, genService, nil)
	curiosity.Governor = costGovernor
	sovEngine.Curiosity = curiosity
	if os.Getenv("ORICLI_ENGINE_CURIOSITY") == "true" {
		go curiosity.Run(context.Background())
		log.Println("[Engine] Curiosity Daemon enabled (ORICLI_ENGINE_CURIOSITY=true).")
	} else {
		log.Println("[Engine] Curiosity Daemon disabled (set ORICLI_ENGINE_CURIOSITY=true to enable).")
	}

	// ── 9. MCP Bridge (async, non-blocking) ───────────────────────────────────
	if os.Getenv("ORICLI_ENGINE_MCP") == "true" {
		go func() {
			if err := sovEngine.MCP.StartAll(context.Background()); err != nil {
				log.Printf("[Engine] MCP start warning: %v", err)
			}
		}()
		log.Println("[Engine] MCP bridge starting (ORICLI_ENGINE_MCP=true).")
	}

	// ── 10. API Gateway ───────────────────────────────────────────────────────
	personaPath := stateDir + "/agent_profiles.json"
	personaService, _ := service.NewPersonaService(personaPath)
	agentService := service.NewGoAgentService(orch, genService, personaService, sovEngine)
	monitor := service.NewModuleMonitorService(registry)
	traceStore := service.NewTraceStore(genService)

	apiServer := api.NewServerV2(config.Load(), st, orch, agentService, monitor, port)
	apiServer.Traces = traceStore
	apiServer.GoalService = goalService

	sovEngine.SetWSHub(apiServer.WSHub)

	goalExecutor.Router = apiServer.ActionRouter
	apiServer.GoalExecutor = goalExecutor
	go goalExecutor.Start(context.Background())

	docIngestor := &service.DocumentIngestor{
		MemoryBank:      apiServer.MemoryBank,
		CuriosityDaemon: curiosity,
	}
	apiServer.DocumentIngestor = docIngestor

	// ── 11. Remote Config Sync (Thynaptic dashboard → hot-reload) ────────────
	// Disabled by default (THYNAPTIC_CONFIG_URL is empty) → fully offline mode.
	remoteSync := engine.NewRemoteConfigSync(apiServer)
	if remoteSync != nil {
		go remoteSync.Run(context.Background())
		log.Println("[Engine] Remote config sync active.")
	}

	// ── 12. Identity Seed ────────────────────────────────────────────────────
	go service.SeedIdentity(apiServer.MemoryBank)

	// ── 13. SPP: Sovereign Peer Protocol (opt-in) ─────────────────────────────
	if os.Getenv("ORICLI_SWARM_ENABLED") == "true" {
		nodeIdentity, err := swarm.LoadOrCreateIdentity(stateDir)
		if err != nil {
			log.Printf("[Swarm] identity load error: %v — swarm disabled", err)
		} else {
			constitutionText := apiServer.Constitution.Inject()
			reputation := swarm.NewReputationStore(nil, nil)
			swarmMonitor := swarm.NewSwarmMonitor(nodeIdentity, reputation, nil)
			marketplace := swarm.NewMarketplace(nodeIdentity, nil, nil, nil)

			combinedHandler := swarm.MessageHandler(func(peer *swarm.PeerConn, env swarm.SwarmEnvelope) {
				switch env.Type {
				case swarm.EnvTypeHealthBeacon:
					var beacon swarm.SwarmHealthBeacon
					if ok, err := env.UnmarshalPayload(&beacon); ok && err == nil {
						swarmMonitor.IngestBeacon(beacon)
					}
				default:
					marketplace.HandleEnvelope(peer, env)
				}
			})

			registry := swarm.NewPeerRegistry(nodeIdentity, constitutionText, combinedHandler)
			marketplace.SetRegistry(registry)
			apiServer.SwarmRegistry = registry
			apiServer.SwarmMonitor = swarmMonitor

			swarmCtx, _ := context.WithCancel(context.Background())
			if seedURL := os.Getenv("THYNAPTIC_PEER_REGISTRY_URL"); seedURL != "" {
				go registry.Bootstrap(swarmCtx, seedURL)
			}
			go swarmMonitor.RunBeaconPublisher(swarmCtx, registry, func() int { return 0 })
			log.Printf("[Swarm] Node %s online — SPP active", nodeIdentity.ShortID())
		}
	}

	// ── 14. Start API ─────────────────────────────────────────────────────────
	go apiServer.Start()
	log.Printf("[Engine] Sovereign API Gateway live on :%d", port)
	log.Printf("[Engine] OpenAI-compatible: POST http://localhost:%d/v1/chat/completions", port)
	log.Println("--- ORICLI-ENGINE READY. SOVEREIGNTY ENGAGED. ---")

	// Graceful shutdown
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	log.Println("[Engine] Shutting down gracefully...")
	sovEngine.MCP.StopAll()
	mb.Close()
	swarmBus.Stop()
	log.Println("[Engine] Offline.")
}

// bootstrapAPIKey loads the owner API key from the state dir or generates a new one.
// The key is written to <stateDir>/api_key on first run and reloaded on every restart.
func bootstrapAPIKey(st *memory.MemoryStore, stateDir string) string {
	os.MkdirAll(stateDir, 0700)
	keyFile := stateDir + "/api_key"

	// Prefer ORICLI_SEED_API_KEY env (systemd service / container env).
	if raw := os.Getenv("ORICLI_SEED_API_KEY"); raw != "" {
		authSvc := auth.NewService(st)
		if _, err := authSvc.RegisterAPIKey(context.Background(), raw, "default", []string{"chat", "read", "write", "admin"}, nil); err != nil {
			log.Printf("[Engine] Warning: could not register seed key: %v", err)
		} else {
			log.Println("[Engine] Seed API key registered from ORICLI_SEED_API_KEY.")
			return raw
		}
	}

	// Try key file from prior run.
	if data, err := os.ReadFile(keyFile); err == nil {
		raw := strings.TrimSpace(string(data))
		if len(raw) > 4 {
			authSvc := auth.NewService(st)
			if _, err := authSvc.RegisterAPIKey(context.Background(), raw, "default", []string{"chat", "read", "write", "admin"}, nil); err == nil {
				log.Printf("[Engine] Loaded API key from %s", keyFile)
				return raw
			}
		}
	}

	// Generate fresh key.
	authSvc := auth.NewService(st)
	raw, _, err := authSvc.GenerateAPIKey(context.Background(), "default", []string{"chat", "read", "write", "admin"}, nil)
	if err != nil {
		log.Fatalf("[Engine] FATAL: could not generate API key: %v", err)
	}
	if err := os.WriteFile(keyFile, []byte(raw), 0600); err != nil {
		log.Printf("[Engine] Warning: could not save API key to %s: %v", keyFile, err)
	}
	log.Printf("[Engine] Generated new owner API key — saved to %s", keyFile)
	return raw
}

// runGenKeys generates a sovereign key pair for .env and exits.
func runGenKeys() {
	adminKey, execKey, err := sovereign.GenerateKeyPair()
	if err != nil {
		fmt.Fprintf(os.Stderr, "keygen failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Println("=== SOVEREIGN KEY PAIR ===")
	fmt.Printf("SOVEREIGN_ADMIN_KEY=%s\n", adminKey)
	fmt.Printf("SOVEREIGN_EXEC_KEY=%s\n", execKey)
	fmt.Println("\nAdd these to your .env and restart.")
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
