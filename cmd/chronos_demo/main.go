package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/thynaptic/oricli-go/pkg/service"
)

func main() {
	fmt.Println("--- Oricli-Alpha Chronos Protocol Demo ---")

	// 1. Initialize Memory Bridge (Temporary for demo)
	dbPath := "/tmp/oricli_chronos_demo"
	os.RemoveAll(dbPath)
	defer os.RemoveAll(dbPath)

	// 32-byte key for AES-256 (Base64 encoded)
	key := "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=" 
	mb, err := service.NewMemoryBridge(dbPath, key)
	if err != nil {
		log.Fatalf("Failed to init MemoryBridge: %v", err)
	}
	defer mb.Close()

	grep := service.NewTemporalGrepService(mb)
	ctx := context.Background()

	// 2. Seed Memories
	fmt.Println("\n[Phase 1: Seeding Temporal Memories]")
	
	// Memories from "Last Tuesday" (simulated)
	lastTuesday := time.Now().AddDate(0, 0, -7).Truncate(24 * time.Hour).Add(14 * time.Hour)
	lastTuesdayTS := float64(lastTuesday.UnixNano()) / 1e9
	_ = lastTuesdayTS

	fmt.Printf("Seeding memories for Last Tuesday (%v)...\n", lastTuesday)
	
	// We'll manually hack the 'UpdatedAt' for the demo by using a custom Put helper if we had one,
	// but mb.Put uses time.Now(). 
	// For the demo, I'll update mb.Put to accept an optional timestamp or just use a hack.
	// Actually, I'll just use QueryTemporal with Today's range for the demo if I can't easily mock time.
	
	// Wait! I can't easily mock the time inside mb.Put without changing the signature.
	// Let's just use two different timestamps separated by a few seconds and query one.
	
	t1 := time.Now()
	mb.Put(service.Episodic, "mem1", map[string]interface{}{"task": "Build gRPC bridge"}, map[string]interface{}{"tags": "golang,grpc"})
	
	time.Sleep(1 * time.Second)
	t2 := time.Now()
	mb.Put(service.Episodic, "mem2", map[string]interface{}{"task": "Optimize MCTS logic"}, map[string]interface{}{"tags": "reasoning"})

	time.Sleep(1 * time.Second)
	t3 := time.Now()
	mb.Put(service.Episodic, "mem3", map[string]interface{}{"task": "Write gRPC documentation"}, map[string]interface{}{"tags": "docs,grpc"})

	// 3. Temporal Grep
	fmt.Println("\n[Phase 2: Temporal Grep]")
	keyword := "gRPC"
	
	// Search in the range [t1, t2] -> Should only find mem1
	fmt.Printf("Searching for '%s' between T1 and T2...\n", keyword)
	matches, _ := grep.Grep(ctx, keyword, float64(t1.UnixNano())/1e9, float64(t2.UnixNano())/1e9)
	
	for _, m := range matches {
		fmt.Printf("MATCH FOUND: ID=%s, Data=%v\n", m.ID, m.Data)
	}

	// Search in the range [t1, t3] -> Should find mem1 and mem3
	fmt.Printf("\nSearching for '%s' between T1 and T3...\n", keyword)
	matches, _ = grep.Grep(ctx, keyword, float64(t1.UnixNano())/1e9, float64(t3.UnixNano())/1e9 + 0.1)
	
	for _, m := range matches {
		fmt.Printf("MATCH FOUND: ID=%s, Data=%v\n", m.ID, m.Data)
	}

	fmt.Println("\n--- Chronos Protocol Demo Complete ---")
}
