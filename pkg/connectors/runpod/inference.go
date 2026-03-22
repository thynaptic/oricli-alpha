package runpod

import (
	"context"
	"fmt"
	"math"
	"net/http"
	"sort"
	"time"
)

const (
	KoboldCppImage = "koboldai/koboldcpp:latest"
	// RunPod proxy URL pattern: https://{podId}-{port}.proxy.runpod.net
	proxyURLTemplate = "https://%s-%d.proxy.runpod.net"
)

// InferencePod is a live RunPod pod running KoboldCpp.
type InferencePod struct {
	PodID       string
	EndpointURL string // https://{id}-5001.proxy.runpod.net/v1
	GPUTypeID   string
	HourlyRate  float64
	StartedAt   time.Time
}

type scoredGPU struct {
	gpu   GPUType
	score float64
}

// SelectBestGPU picks the best GPU within budget using the VRAM-per-dollar
// scoring algorithm ported from scripts/runpod_bridge.py::_select_candidate_gpus.
//
// Score = vram^1.5 / effectivePrice — maximises VRAM headroom per dollar.
func (c *Client) SelectBestGPU(minVRAMGB int, maxHourly float64) (*GPUType, error) {
	gpus, err := c.GetGPUTypes()
	if err != nil {
		return nil, fmt.Errorf("SelectBestGPU: fetch GPU types: %w", err)
	}

	const storageOverhead = 0.02 // ~$0.01/10 GB/hr for a 20 GB volume

	var candidates []scoredGPU
	for _, g := range gpus {
		effective := g.SecurePrice + storageOverhead
		if g.MemoryInGb < minVRAMGB || effective > maxHourly || g.SecurePrice <= 0 {
			continue
		}
		vram := float64(g.MemoryInGb)
		score := math.Pow(vram, 1.5) / effective
		candidates = append(candidates, scoredGPU{g, score})
	}
	if len(candidates) == 0 {
		return nil, fmt.Errorf("no GPU available with ≥%d GB VRAM under $%.2f/hr", minVRAMGB, maxHourly)
	}
	sort.Slice(candidates, func(i, j int) bool { return candidates[i].score > candidates[j].score })
	best := candidates[0].gpu
	return &best, nil
}

// CreateInferencePod spins up a KoboldCpp pod on RunPod.
// modelURL must be a direct GGUF download URL (HuggingFace resolve URL works).
func (c *Client) CreateInferencePod(gpuTypeID, modelURL string) (*InferencePod, error) {
	query := `
	mutation CreatePod($input: PodFindAndDeployOnDemandInput!) {
		podFindAndDeployOnDemand(input: $input) {
			id
			name
			runtime {
				ports { ip isIpPublic privatePort publicPort type }
			}
		}
	}`

	dockerArgs := fmt.Sprintf(
		"python /koboldcpp.py --model %s --port 5001 --host 0.0.0.0 --usecublas --threads 8 --contextsize 8192 --gpulayers 999",
		modelURL,
	)
	variables := map[string]interface{}{
		"input": map[string]interface{}{
			"name":              "oricli-inference",
			"gpuTypeId":         gpuTypeID,
			"gpuCount":          1,
			"cloudType":         "SECURE",
			"volumeInGb":        20,
			"containerDiskInGb": 20,
			"volumeMountPath":   "/workspace",
			"imageName":         KoboldCppImage,
			"ports":             "5001/http,22/tcp",
			"dockerArgs":        dockerArgs,
		},
	}

	result, err := c.Query(query, variables)
	if err != nil {
		return nil, fmt.Errorf("CreateInferencePod: %w", err)
	}

	data, _ := result["data"].(map[string]interface{})
	podData, _ := data["podFindAndDeployOnDemand"].(map[string]interface{})
	if podData == nil {
		return nil, fmt.Errorf("CreateInferencePod: empty response — GPU type %s may be unavailable", gpuTypeID)
	}

	podID, _ := podData["id"].(string)
	endpointURL := fmt.Sprintf(proxyURLTemplate, podID, 5001) + "/v1"

	return &InferencePod{
		PodID:       podID,
		EndpointURL: endpointURL,
		GPUTypeID:   gpuTypeID,
		StartedAt:   time.Now(),
	}, nil
}

// WaitForReady polls the pod's /health endpoint until KoboldCpp responds or
// the context is cancelled. Returns the endpoint base URL on success.
func (c *Client) WaitForReady(ctx context.Context, pod *InferencePod) error {
	healthURL := fmt.Sprintf(proxyURLTemplate, pod.PodID, 5001) + "/health"
	httpClient := &http.Client{Timeout: 10 * time.Second}

	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			resp, err := httpClient.Get(healthURL)
			if err == nil && resp.StatusCode < 400 {
				resp.Body.Close()
				return nil
			}
			if resp != nil {
				resp.Body.Close()
			}
		}
	}
}

// GetPodHourlyRate queries the GPU type's current secure price.
func (c *Client) GetPodHourlyRate(gpuTypeID string) (float64, error) {
	gpus, err := c.GetGPUTypes()
	if err != nil {
		return 0, err
	}
	for _, g := range gpus {
		if g.ID == gpuTypeID {
			return g.SecurePrice, nil
		}
	}
	return 0, fmt.Errorf("GPU type %s not found", gpuTypeID)
}
