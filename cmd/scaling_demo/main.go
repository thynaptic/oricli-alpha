package main

import (
	"fmt"
	"time"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/kernel"
)

func main() {
	fmt.Println("--- Oricli-Alpha Autonomous Scaling Demo ---")

	// 1. Setup Swarm Bus and Kernel
	swarmBus := bus.NewSwarmBus(1000)
	k := kernel.NewMicroKernel(nil, nil, nil)
	
	// Ensure the Kernel has a dummy process for the "KERNEL" PID to avoid "invalid PID" errors
	// (In a real OS, the Kernel is a reserved PID)
	// We'll skip the PID check for the KERNEL PID in this demo.

	// 2. Setup Scaling Service
	scaler := kernel.NewScalingService(swarmBus, k)
	scaler.LatencyLimit = 100.0 // Lowered to 100ms for demo speed
	
	fmt.Println("[System] Kernel and Scaling Monitor online.")

	// 3. Simulate Pressure: Flood the bus with "slow" messages
	fmt.Println("\n[Phase 1: Simulating System Pressure]")
	fmt.Println("Flooding SwarmBus with 500ms latency events...")
	
	go func() {
		for i := 0; i < 20; i++ {
			// Simulate a message that was created 500ms ago
			ts := time.Now().Add(-500 * time.Millisecond).UnixNano()
			swarmBus.Publish(bus.Message{
				Topic:     "system.load",
				Timestamp: ts,
				Payload:   map[string]interface{}{"load": 0.95},
			})
			time.Sleep(50 * time.Millisecond)
		}
	}()

	// 4. Run the monitor
	fmt.Println("\n[Phase 2: Autonomic Reaction]")
	
	// We'll call monitorPressure manually for the demo instead of Run() to keep it synchronous
	for i := 0; i < 5; i++ {
		time.Sleep(1 * time.Second)
		fmt.Printf("Tick %d: Current Bus Latency: %.2fms\n", i+1, swarmBus.GetLatency())
		
		if swarmBus.GetLatency() > scaler.LatencyLimit {
			scaler.TriggerScaleOut()
			break
		}
	}

	fmt.Println("\n--- Autonomous Scaling Demo Complete ---")
}
