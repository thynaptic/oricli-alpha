package main

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/thynaptic/oricli-go/pkg/kernel"
	"github.com/thynaptic/oricli-go/pkg/service"
)

func main() {
	fmt.Println("--- Oricli-Alpha Kernel IPC (Shared Memory) Demo ---")

	// 1. Boot Kernel
	k := kernel.NewMicroKernel(nil, nil)
	fmt.Println("[System] Kernel online.")

	// 2. Spawn Agents
	pidA, _ := k.SpawnProcess(service.AgentProfile{Name: "Generator"}, 100.0)
	pidB, _ := k.SpawnProcess(service.AgentProfile{Name: "Consumer"}, 100.0)

	ctx := context.Background()

	fmt.Println("\n[Phase 1: Shared Memory Allocation]")
	res := k.ExecSyscall(kernel.SyscallRequest{
		PID:  pidA,
		Call: kernel.SysAllocSharedMem,
		Args: map[string]interface{}{"name": "hft_signals", "size": 1024},
	})
	if !res.Success {
		log.Fatalf("Alloc failed: %v", res.Error)
	}

	fmt.Println("\n[Phase 2: Agent A Writing to IPC]")
	procA, _ := k.GetProcess(pidA)
	msg := "SIGNAL:BUY_BLACKWELL_GPUS_AT_3AM"
	
	// Ensure the directory exists in the sandbox
	_, err := procA.Sandbox.Execute(ctx, "mkdir -p /out")
	if err != nil {
		log.Fatalf("Agent A mkdir failed: %v", err)
	}
	
	err = procA.Sandbox.WriteFile("/out/signal.bin", []byte(msg))
	if err != nil {
		log.Fatalf("Agent A WriteFile failed: %v", err)
	}
	fmt.Printf("Agent A (Generator) wrote to its local sandbox: %s\n", msg)

	res = k.ExecSyscall(kernel.SyscallRequest{
		PID:  pidA,
		Call: kernel.SysWriteSharedMem,
		Args: map[string]interface{}{"name": "hft_signals", "path": "/out/signal.bin"},
	})
	if !res.Success {
		log.Fatalf("Write failed: %v", res.Error)
	}
	fmt.Println("[Kernel] Data flushed from Agent A's sandbox to shared buffer.")

	fmt.Println("\n[Phase 3: Agent B Reading from IPC]")
	procB, _ := k.GetProcess(pidB)
	// Ensure the directory exists in B's sandbox
	_, err = procB.Sandbox.Execute(ctx, "mkdir -p /in")
	if err != nil {
		log.Fatalf("Agent B mkdir failed: %v", err)
	}

	res = k.ExecSyscall(kernel.SyscallRequest{
		PID:  pidB,
		Call: kernel.SysMapSharedMem,
		Args: map[string]interface{}{"name": "hft_signals", "path": "/in/market_signal.bin"},
	})
	if !res.Success {
		log.Fatalf("Map failed: %v", res.Error)
	}
	fmt.Println("[Kernel] Shared region mapped to Agent B's sandbox at /in/market_signal.bin")

	// Verify Agent B can see the data
	data, err := procB.Sandbox.ReadFile("/in/market_signal.bin")
	if err != nil {
		log.Fatalf("Read failed: %v", err)
	}
	
	cleanData := strings.TrimRight(string(data), "\x00")
	fmt.Printf("Agent B (Consumer) read from its local sandbox: %s\n", cleanData)

	if cleanData == msg {
		fmt.Println("\n--- IPC Demo SUCCESS: Zero-Copy (Simulated) Memory Sharing Verified ---")
	} else {
		fmt.Printf("\n--- IPC Demo FAILED: Data mismatch. Length expected: %d, got: %d ---\n", len(msg), len(cleanData))
	}
}
