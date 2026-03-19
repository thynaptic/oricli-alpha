package main

import (
	"fmt"
	"log"
	"os"

	"github.com/thynaptic/oricli-go/pkg/service"
)

func main() {
	fmt.Println("--- Oricli-Alpha Dream State (Consolidation) Demo ---")

	// 1. Setup Infrastructure
	dbPath := "/tmp/oricli_dream_demo"
	os.RemoveAll(dbPath)
	defer os.RemoveAll(dbPath)

	key := "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=" 
	mb, err := service.NewMemoryBridge(dbPath, key)
	if err != nil {
		log.Fatalf("Failed to init MemoryBridge: %v", err)
	}
	defer mb.Close()

	// Setup Ghost Cluster (Simulated Key)
	apiKey := os.Getenv("OricliAlpha_Key")
	ghost := service.NewGhostClusterService(apiKey)

	// 2. Seed a High-Quality Gosh Trace (The "Experience")
	fmt.Println("\n[Phase 1: Recording Daily Experience]")
	mb.Put(service.Episodic, "exp_001", map[string]interface{}{
		"task": "Fix Memory Leak in Swarm Bus",
		"gosh_trace": "GO_LEAK_FIX_VERIFIED_V1.2",
	}, map[string]interface{}{"quality": 0.98})
	fmt.Println("Gosh Trace recorded: GO_LEAK_FIX_VERIFIED_V1.2")

	// 3. Trigger Dream Daemon
	fmt.Println("\n[Phase 2: Entering Dream State]")
	
	// We'll use a short idle threshold for the demo
	dream := service.NewDreamDaemon(5, 1, nil, mb, nil, ghost, nil)
	
	// Manually trigger consolidation for the demo
	fmt.Println("DreamDaemon: 'Analyzing recent experiences for consolidation...'")
	dream.ConsolidateExperience() 
	
	fmt.Println("\n--- Dream State Demo Complete ---")
}
