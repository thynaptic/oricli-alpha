package finetune

// PodClient wraps the RunPod REST API (rest.runpod.io/v1/pods).
// The existing pkg/connectors/runpod/client.go uses GraphQL — this uses the
// newer REST API which exposes SSH port mappings needed for exec.

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"
)

const (
	restBase        = "https://rest.runpod.io/v1"
	DefaultGPUType  = "NVIDIA GeForce RTX 4090"
	AxolotlImage    = "winglian/axolotl:main-latest"
	podPollInterval = 15 * time.Second
	podReadyTimeout = 10 * time.Minute
)

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

// PodConfig is the payload for POST /v1/pods.
type PodConfig struct {
	Name              string            `json:"name"`
	ImageName         string            `json:"imageName"`
	GPUTypeIDs        []string          `json:"gpuTypeIds"`
	GPUCount          int               `json:"gpuCount"`
	ContainerDiskInGb int               `json:"containerDiskInGb"`
	VolumeInGb        int               `json:"volumeInGb"`
	Ports             []string          `json:"ports"`
	Env               map[string]string `json:"env,omitempty"`
	DockerStartCmd    []string          `json:"dockerStartCmd,omitempty"`
}

// PodResponse is the pod object returned by the RunPod REST API.
type PodResponse struct {
	ID            string            `json:"id"`
	Name          string            `json:"name"`
	DesiredStatus string            `json:"desiredStatus"`
	PublicIP      string            `json:"publicIp"`
	PortMappings  map[string]int    `json:"portMappings"` // e.g. {"22": 10341}
	ContainerDisk int               `json:"containerDiskInGb"`
	CostPerHr     float64           `json:"costPerHr"`
}

// SSHPort returns the external SSH port for the pod (0 if not available yet).
func (p *PodResponse) SSHPort() int {
	return p.PortMappings["22"]
}

// IsRunning returns true if the pod is in RUNNING state with SSH available.
func (p *PodResponse) IsRunning() bool {
	return p.DesiredStatus == "RUNNING" && p.PublicIP != "" && p.SSHPort() > 0
}

// ─────────────────────────────────────────────────────────────────────────────
// PodClient
// ─────────────────────────────────────────────────────────────────────────────

// PodClient manages RunPod pods via the REST API.
type PodClient struct {
	apiKey string
	http   *http.Client
}

// NewPodClient creates a PodClient. Reads RUNPOD_API_KEY from env if apiKey is empty.
func NewPodClient(apiKey string) *PodClient {
	if apiKey == "" {
		apiKey = os.Getenv("RUNPOD_API_KEY")
	}
	return &PodClient{
		apiKey: apiKey,
		http:   &http.Client{Timeout: 30 * time.Second},
	}
}

// CreatePod creates a new on-demand pod and returns it.
func (c *PodClient) CreatePod(ctx context.Context, cfg PodConfig) (*PodResponse, error) {
	if cfg.GPUCount == 0 {
		cfg.GPUCount = 1
	}
	if cfg.ContainerDiskInGb == 0 {
		cfg.ContainerDiskInGb = 80
	}
	if cfg.VolumeInGb == 0 {
		cfg.VolumeInGb = 50
	}
	if len(cfg.Ports) == 0 {
		cfg.Ports = []string{"22/tcp"}
	}
	if len(cfg.GPUTypeIDs) == 0 {
		cfg.GPUTypeIDs = []string{DefaultGPUType}
	}

	return c.doJSON(ctx, "POST", restBase+"/pods", cfg, &PodResponse{})
}

// GetPod fetches a pod by ID.
func (c *PodClient) GetPod(ctx context.Context, podID string) (*PodResponse, error) {
	return c.doJSON(ctx, "GET", fmt.Sprintf("%s/pods/%s", restBase, podID), nil, &PodResponse{})
}

// TerminatePod terminates a pod by ID. Stops billing immediately.
func (c *PodClient) TerminatePod(ctx context.Context, podID string) error {
	_, err := c.doJSON(ctx, "DELETE", fmt.Sprintf("%s/pods/%s", restBase, podID), nil, nil)
	return err
}

// WaitUntilRunning polls GetPod until IsRunning() or timeout. Returns the ready pod.
func (c *PodClient) WaitUntilRunning(ctx context.Context, podID string) (*PodResponse, error) {
	deadline := time.Now().Add(podReadyTimeout)
	for {
		if time.Now().After(deadline) {
			return nil, fmt.Errorf("pod %s did not become RUNNING within %s", podID, podReadyTimeout)
		}

		pod, err := c.GetPod(ctx, podID)
		if err != nil {
			return nil, fmt.Errorf("poll pod: %w", err)
		}
		if pod.IsRunning() {
			return pod, nil
		}

		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(podPollInterval):
		}
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Internal HTTP helper
// ─────────────────────────────────────────────────────────────────────────────

func (c *PodClient) doJSON(ctx context.Context, method, url string, body interface{}, out interface{}) (*PodResponse, error) {
	var bodyReader io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			return nil, err
		}
		bodyReader = bytes.NewReader(b)
	}

	req, err := http.NewRequestWithContext(ctx, method, url, bodyReader)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+c.apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.http.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("RunPod API %s %s → %d: %s", method, url, resp.StatusCode, string(respBody))
	}

	if out == nil {
		return nil, nil
	}

	pod, ok := out.(*PodResponse)
	if !ok {
		return nil, fmt.Errorf("unexpected out type")
	}
	if err := json.Unmarshal(respBody, pod); err != nil {
		return nil, fmt.Errorf("decode pod response: %w", err)
	}
	return pod, nil
}
