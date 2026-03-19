package service

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/thynaptic/oricli-go/pkg/connectors/runpod"
)

// GhostClusterService manages the autonomous lifecycle of temporary GPU clusters.
type GhostClusterService struct {
	RunPodClient *runpod.Client
	ActivePods   map[string]*runpod.Pod
	mu           sync.Mutex
}

// NewGhostClusterService initializes the orchestrator for ephemeral hardware.
func NewGhostClusterService(apiKey string) *GhostClusterService {
	return &GhostClusterService{
		RunPodClient: runpod.NewClient(apiKey),
		ActivePods:   make(map[string]*runpod.Pod),
	}
}

// GhostSession represents a temporary allocation of GPU hardware.
type GhostSession struct {
	PodIDs    []string
	GPUType   string
	StartTime time.Time
}

// Provision spins up the requested hardware and waits for it to be ready.
func (s *GhostClusterService) Provision(ctx context.Context, name string, gpuType string, count int) (*GhostSession, error) {
	log.Printf("[GhostCluster] Provisioning %d x %s for '%s'...", count, gpuType, name)
	
	session := &GhostSession{
		GPUType:   gpuType,
		StartTime: time.Now(),
	}

	var wg sync.WaitGroup
	var errMu sync.Mutex
	var firstErr error

	for i := 0; i < count; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			podName := fmt.Sprintf("ghost-%s-%d", name, idx)
			// Using a standard PyTorch image for ML tasks
			image := "runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04"
			
			pod, err := s.RunPodClient.CreatePod(podName, gpuType, image)
			if err != nil {
				errMu.Lock()
				if firstErr == nil {
					firstErr = fmt.Errorf("failed to create pod %s: %w", podName, err)
				}
				errMu.Unlock()
				return
			}
			
			s.mu.Lock()
			s.ActivePods[pod.ID] = pod
			session.PodIDs = append(session.PodIDs, pod.ID)
			s.mu.Unlock()
			
			log.Printf("[GhostCluster] Pod %s (%s) initialized.", pod.ID, podName)
		}(i)
	}

	wg.Wait()

	if firstErr != nil {
		// Rollback any successfully created pods if the full cluster failed
		s.Vanish(session)
		return nil, firstErr
	}

	log.Printf("[GhostCluster] Cluster '%s' provisioned successfully in %v.", name, time.Since(session.StartTime))
	return session, nil
}

// Vanish destroys the temporary cluster, leaving no trace.
func (s *GhostClusterService) Vanish(session *GhostSession) {
	log.Printf("[GhostCluster] Initiating 'Vanish' protocol for %d pods...", len(session.PodIDs))
	var wg sync.WaitGroup

	for _, podID := range session.PodIDs {
		wg.Add(1)
		go func(id string) {
			defer wg.Done()
			err := s.RunPodClient.TerminatePod(id)
			if err != nil {
				log.Printf("[GhostCluster] Failed to terminate pod %s: %v", id, err)
			} else {
				log.Printf("[GhostCluster] Pod %s terminated. Traces erased.", id)
				s.mu.Lock()
				delete(s.ActivePods, id)
				s.mu.Unlock()
			}
		}(podID)
	}

	wg.Wait()
	log.Printf("[GhostCluster] 'Vanish' complete. Hardware reclaimed.")
}
