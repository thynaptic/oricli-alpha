package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/joho/godotenv"
	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/kernel"
	"github.com/thynaptic/oricli-go/pkg/service"
)

func main() {
	log.Println("--- BOOTING ORICLI-ALPHA HIVE OS (RING 0) ---")

	// 1. Load Environment (Keys and Config)
	godotenv.Load(".env")
	apiKey := os.Getenv("OricliAlpha_Key")
	encKey := os.Getenv("ORICLI_ENCRYPTION_KEY")
	if encKey == "" {
		encKey = "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=" // Fallback for demo
	}

	// 2. Initialize Bus & Hardware Abstraction Layer (HAL)
	swarmBus := bus.NewSwarmBus(5000)
	ghost := service.NewGhostClusterService(apiKey)
	log.Println("[Boot] HAL and SwarmBus initialized.")

	// 3. Initialize Storage Ring (MemoryBridge + Chronos)
	memPath := "/home/mike/Mavaia/.memory/lmdb"
	mb, err := service.NewMemoryBridge(memPath, encKey)
	if err != nil {
		log.Fatalf("[Kernel Panic] Failed to init MemoryBridge: %v", err)
	}
	log.Println("[Boot] Storage Ring (Encrypted LMDB) secured.")

	// 4. Initialize Safety & Precog
	safety := kernel.NewSafetyFramework(50.0) // $50.00 daily spend cap
	goshMod, _ := service.NewGoshModule("precog_sandbox", "/home/mike/Mavaia")
	orch := service.NewGoOrchestrator(swarmBus, service.NewModuleRegistry(""))
	precog := service.NewMetacogDaemon("/home/mike/Mavaia", orch, goshMod)
	log.Println("[Boot] Safety Framework & Precog online.")

	// 5. BOOT CORE KERNEL
	k := kernel.NewMicroKernel(mb, ghost, precog, safety)
	log.Println("[System] Kernel Ring 0 is ACTIVE.")

	// 6. Spawn System Services as Kernel Processes
	log.Println("[System] Spawning core Hive services...")
	
	// Coordinator Process
	coordProfile := service.AgentProfile{Name: "Coordinator_Kernel"}
	k.SpawnProcess(coordProfile, 1000000.0, "echo 'Booting swarm coordinator...'")

	// 7. Start User-Space API Gateway
	// (Simulating the API start for the MBR demo)
	apiPort := 8089
	log.Printf("[System] User-Space API Gateway active on port %d", apiPort)

	// 8. Start Background Consolidation (DreamDaemon)
	graphSvc, _ := service.NewGraphService()
	dream := service.NewDreamDaemon(3600, 60, graphSvc, mb, goshMod, ghost, orch)
	go dream.Run()
	log.Println("[System] DreamDaemon consolidation loop started.")

	// --- RUNTIME ---
	log.Println("--- HIVE OS BOOT COMPLETE. SOVEREIGNTY ENGAGED. ---")

	// Wait for termination signal
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	log.Println("[System] Initiating graceful shutdown...")
	mb.Close()
	swarmBus.Stop()
	log.Println("[System] Oricli-Alpha Hive OS Offline.")
}
