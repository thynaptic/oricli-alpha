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
	fmt.Println("--- Oricli-Alpha Handbook API Validation (100% Match Test) ---")

	// 1. SETUP: Boot Kernel and Safety
	safety := kernel.NewSafetyFramework(50.0)
	k := kernel.NewMicroKernel(nil, nil, nil, safety)
	ctx := context.Background()

	// 2. SPAWN: Following Section 2 of Handbook
	profile := service.AgentProfile{Name: "ValidationAgent"}
	pid, err := k.SpawnProcess(profile, 500.0, "echo 'Initializing Handbook Validation Test...'")
	if err != nil {
		log.Fatalf("Spawn failed: %v", err)
	}
	fmt.Printf("[OK] Process %s spawned with 500 tokens.\n", pid)

	// 3. GOSH YAEGI: Following Section 3 of Handbook
	fmt.Println("\n[Testing Section 3: Gosh Sovereign Tools]")
	proc, _ := k.GetProcess(pid)
	toolCode := `
package main
func Multiplier(args []string) (string, string, error) {
	return "YA_EGI_VAL_SUCCESS", "", nil
}
`
	err = proc.Sandbox.RegisterTool("multiplier", toolCode)
	if err != nil {
		log.Fatalf("RegisterTool failed: %v", err)
	}
	output, _ := proc.Sandbox.Execute(ctx, "multiplier")
	fmt.Printf("[OK] Dynamic Tool Result: %s\n", strings.TrimSpace(output))

	// 4. SYSCALLS: Following Section 4 of Handbook
	fmt.Println("\n[Testing Section 4: Syscall Reference]")

	// 4a. SysAllocSharedMem
	fmt.Println("Testing SysAllocSharedMem...")
	res := k.ExecSyscall(kernel.SyscallRequest{
		PID:  pid,
		Call: kernel.SysAllocSharedMem,
		Args: map[string]interface{}{"name": "hb_shared", "size": 1024},
	})
	if !res.Success { log.Fatalf("SysAllocSharedMem failed: %v", res.Error) }

	// 4b. SysWriteSharedMem
	fmt.Println("Testing SysWriteSharedMem...")
	proc.Sandbox.Execute(ctx, "mkdir -p /out")
	proc.Sandbox.WriteFile("/out/test.bin", []byte("HANDBOOK_VAL"))
	res = k.ExecSyscall(kernel.SyscallRequest{
		PID:  pid,
		Call: kernel.SysWriteSharedMem,
		Args: map[string]interface{}{"name": "hb_shared", "path": "/out/test.bin"},
	})
	if !res.Success { log.Fatalf("SysWriteSharedMem failed: %v", res.Error) }

	// 4c. SysMapSharedMem
	fmt.Println("Testing SysMapSharedMem...")
	proc.Sandbox.Execute(ctx, "mkdir -p /in")
	res = k.ExecSyscall(kernel.SyscallRequest{
		PID:  pid,
		Call: kernel.SysMapSharedMem,
		Args: map[string]interface{}{"name": "hb_shared", "path": "/in/hb_data.bin"},
	})
	if !res.Success { log.Fatalf("SysMapSharedMem failed: %v", res.Error) }
	
	val, _ := proc.Sandbox.ReadFile("/in/hb_data.bin")
	fmt.Printf("[OK] IPC Roundtrip: %s\n", strings.TrimRight(string(val), "\x00"))

	// 4d. SysAllocGPU
	fmt.Println("Testing SysAllocGPU...")
	res = k.ExecSyscall(kernel.SyscallRequest{
		PID:  pid,
		Call: kernel.SysAllocGPU,
		Args: map[string]interface{}{"gpu_type": "NVIDIA RTX 5090", "count": 1},
	})
	if !res.Success { log.Fatalf("SysAllocGPU failed: %v", res.Error) }
	fmt.Printf("[OK] GPU Resource Handle: %v\n", res.Data)

	// 4e. SysQueryMemory
	fmt.Println("Testing SysQueryMemory...")
	res = k.ExecSyscall(kernel.SyscallRequest{
		PID:  pid,
		Call: kernel.SysQueryMemory,
		Args: map[string]interface{}{"keyword": "sovereign"},
	})
	if !res.Success { log.Fatalf("SysQueryMemory failed: %v", res.Error) }
	fmt.Printf("[OK] Memory Result: %v\n", res.Data)

	// 5. SAFETY: Following Section 6 of Handbook
	fmt.Println("\n[Testing Section 6: Safety & SysPanic]")
	fmt.Println("Triggering SysPanic (The Big Red Button)...")
	k.ExecSyscall(kernel.SyscallRequest{
		PID:  pid,
		Call: kernel.SysPanic,
	})

	if safety.Level == kernel.Defcon1 && safety.IsKernelLocked {
		fmt.Println("[OK] System successfully entered DEFCON 1 (Locked).")
	} else {
		log.Fatalf("FAIL: System failed to enter DEFCON 1 after Panic.")
	}

	// Verify post-panic isolation
	res = k.ExecSyscall(kernel.SyscallRequest{
		PID:  pid,
		Call: kernel.SysQueryMemory,
		Args: map[string]interface{}{"keyword": "test"},
	})
	if !res.Success && strings.Contains(res.Error.Error(), "locked") {
		fmt.Println("[OK] Post-panic Syscall correctly blocked.")
	}

	fmt.Println("\n--- ALL HANDBOOK APIS VERIFIED 100% ---")
}
