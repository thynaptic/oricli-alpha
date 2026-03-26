package runpod

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

const (
	OllamaImage      = "ollama/ollama:latest"
	VisionModel      = "moondream:latest"
	visionPort       = 11434
	pullTimeout      = 8 * time.Minute  // model download on GPU pod: fast but non-trivial
	visionReadyDelay = 10 * time.Second // poll interval while waiting for Ollama / pull
)

// VisionPod represents a RunPod pod running Ollama for GPU-accelerated image analysis.
type VisionPod struct {
	PodID      string
	OllamaURL  string // https://{id}-11434.proxy.runpod.net
	GPUTypeID  string
	HourlyRate float64
	StartedAt  time.Time
}

// CreateVisionPod spins up an Ollama GPU pod on RunPod.
// The pod uses the official ollama/ollama image on port 11434.
// After creation, call WaitForVisionReady to ensure the model is pulled and ready.
func (c *Client) CreateVisionPod(gpuTypeID string) (*VisionPod, error) {
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

	variables := map[string]interface{}{
		"input": map[string]interface{}{
			"name":              "oricli-vision",
			"gpuTypeId":         gpuTypeID,
			"gpuCount":          1,
			"cloudType":         "SECURE",
			"volumeInGb":        10,
			"containerDiskInGb": 15,
			"volumeMountPath":   "/root/.ollama",
			"imageName":         OllamaImage,
			"ports":             fmt.Sprintf("%d/http,22/tcp", visionPort),
			// No dockerArgs — ollama/ollama default entrypoint is `ollama serve`
		},
	}

	result, err := c.Query(query, variables)
	if err != nil {
		return nil, fmt.Errorf("CreateVisionPod: %w", err)
	}

	data, _ := result["data"].(map[string]interface{})
	podData, _ := data["podFindAndDeployOnDemand"].(map[string]interface{})
	if podData == nil {
		return nil, fmt.Errorf("CreateVisionPod: empty response — GPU type %s may be unavailable", gpuTypeID)
	}

	podID, _ := podData["id"].(string)
	ollamaURL := fmt.Sprintf(proxyURLTemplate, podID, visionPort)

	return &VisionPod{
		PodID:     podID,
		OllamaURL: ollamaURL,
		GPUTypeID: gpuTypeID,
		StartedAt: time.Now(),
	}, nil
}

// WaitForVisionReady waits until the Ollama server is up, then triggers a model pull
// and waits for it to complete. Returns when moondream:latest is ready to serve.
func (c *Client) WaitForVisionReady(ctx context.Context, pod *VisionPod) error {
	httpClient := &http.Client{Timeout: 10 * time.Second}

	// Phase 1: wait for Ollama HTTP server to respond
	deadline := time.Now().Add(5 * time.Minute)
	for time.Now().Before(deadline) {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}
		resp, err := httpClient.Get(pod.OllamaURL + "/api/tags")
		if err == nil && resp.StatusCode == http.StatusOK {
			resp.Body.Close()
			break
		}
		if resp != nil {
			resp.Body.Close()
		}
		time.Sleep(visionReadyDelay)
	}
	if time.Now().After(deadline) {
		return fmt.Errorf("WaitForVisionReady: Ollama server did not come up within 5 minutes")
	}

	// Phase 2: pull the vision model (streaming response)
	pullCtx, cancel := context.WithTimeout(ctx, pullTimeout)
	defer cancel()

	body, _ := json.Marshal(map[string]string{"model": VisionModel})
	req, _ := http.NewRequestWithContext(pullCtx, http.MethodPost,
		pod.OllamaURL+"/api/pull", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")

	pullClient := &http.Client{Timeout: pullTimeout}
	resp, err := pullClient.Do(req)
	if err != nil {
		return fmt.Errorf("WaitForVisionReady: pull request failed: %w", err)
	}
	defer resp.Body.Close()

	// Ollama streams pull progress as newline-delimited JSON.
	// Wait for {"status":"success"} to confirm the model is ready.
	scanner := bufio.NewScanner(resp.Body)
	for scanner.Scan() {
		var line struct {
			Status string `json:"status"`
			Error  string `json:"error"`
		}
		if err := json.Unmarshal(scanner.Bytes(), &line); err != nil {
			continue
		}
		if line.Error != "" {
			return fmt.Errorf("WaitForVisionReady: pull error: %s", line.Error)
		}
		if strings.Contains(line.Status, "success") {
			return nil
		}
	}

	return fmt.Errorf("WaitForVisionReady: pull stream ended without success confirmation")
}

// CallOllamaVision sends a vision inference request to the pod's Ollama API.
// imageB64 is a raw base64-encoded image (no data: URI prefix).
func CallOllamaVision(ctx context.Context, ollamaURL, imageB64, prompt string) (string, error) {
	payload, _ := json.Marshal(map[string]any{
		"model":       VisionModel,
		"prompt":      prompt,
		"images":      []string{imageB64},
		"stream":      false,
		"num_predict": 256,
		"options": map[string]any{
			"temperature": 0.1,
			"num_ctx":     2048,
		},
	})

	reqCtx, cancel := context.WithTimeout(ctx, 90*time.Second)
	defer cancel()

	req, _ := http.NewRequestWithContext(reqCtx, http.MethodPost,
		ollamaURL+"/api/generate", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("vision inference: %w", err)
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("vision read response: %w", err)
	}

	var ollamaResp struct {
		Response string `json:"response"`
		Error    string `json:"error"`
	}
	if err := json.Unmarshal(raw, &ollamaResp); err != nil {
		return "", fmt.Errorf("vision decode response: %w", err)
	}
	if ollamaResp.Error != "" {
		return "", fmt.Errorf("vision model error: %s", ollamaResp.Error)
	}

	return strings.TrimSpace(ollamaResp.Response), nil
}
