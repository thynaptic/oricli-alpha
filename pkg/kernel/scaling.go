package kernel

import (
	"log"
	"time"

	"github.com/thynaptic/oricli-go/pkg/bus"
)

// ScalingService is an autonomic Kernel daemon that monitors system pressure and scales out.
type ScalingService struct {
	Bus           *bus.SwarmBus
	Kernel        *MicroKernel
	LatencyLimit  float64       // MS threshold to trigger scaling
	CheckInterval time.Duration
	stopCh        chan struct{}
}

// NewScalingService initializes the autonomic growth daemon.
func NewScalingService(b *bus.SwarmBus, k *MicroKernel) *ScalingService {
	return &ScalingService{
		Bus:           b,
		Kernel:        k,
		LatencyLimit:  500.0, // 500ms latency trigger
		CheckInterval: 10 * time.Second,
		stopCh:        make(chan struct{}),
	}
}

// Run starts the autonomic monitoring loop.
func (s *ScalingService) Run() {
	log.Println("[ScalingService] Autonomic scaling monitor started.")
	ticker := time.NewTicker(s.CheckInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			s.monitorPressure()
		case <-s.stopCh:
			return
		}
	}
}

func (s *ScalingService) monitorPressure() {
	latency := s.Bus.GetLatency()
	
	if latency > s.LatencyLimit {
		log.Printf("[ScalingService] CRITICAL PRESSURE: Avg Latency %.2fms exceeds limit %.2fms.", latency, s.LatencyLimit)
		s.TriggerScaleOut()
	}
}

// TriggerScaleOut autonomously requests more hardware from the Kernel.
func (s *ScalingService) TriggerScaleOut() {
	log.Println("[ScalingService] Autonomously initiating 'Growth' protocol...")

	// Internal Kernel Syscall (Kernel-to-Kernel)
	req := SyscallRequest{
		PID:  "KERNEL", // Direct Ring 0 request
		Call: SysAllocGPU,
		Args: map[string]interface{}{
			"gpu_type": "NVIDIA RTX 5090",
			"count":    1,
			"reason":   "SwarmBus Latency Pressure",
		},
	}

	res := s.Kernel.ExecSyscall(req)
	if res.Success {
		log.Printf("[ScalingService] GROWTH SUCCESS: New worker node provisioned. Data: %v", res.Data)
	} else {
		log.Printf("[ScalingService] GROWTH FAILED: %v", res.Error)
	}
}

func (s *ScalingService) Stop() {
	close(s.stopCh)
}
