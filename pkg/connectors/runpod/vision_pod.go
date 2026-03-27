package runpod

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"net/http"
	"sort"
	"strings"
	"time"
)

const (
	// vLLM OpenAI-compatible server — native CUDA, no GGUF wrapper, proper multimodal.
	VLLMImage   = "vllm/vllm-openai:latest"
	VisionModel = "llava-hf/llava-1.5-7b-hf" // 4GB, HuggingFace public, vLLM first-class
	visionPort  = 8000

	visionReadyDelay = 15 * time.Second
	visionReadyMax   = 10 * time.Minute // vLLM + HF model download can take a few minutes
)

// VisionPod represents a RunPod pod running vLLM for GPU-accelerated image analysis.
type VisionPod struct {
	PodID      string
	BaseURL    string // https://{id}-8000.proxy.runpod.net
	GPUTypeID  string
	HourlyRate float64
	StartedAt  time.Time
}

// TryCreateVisionPod attempts GPU candidates in descending VRAM-per-dollar order
// until one is available. Prefers SECURE cloud, falls back to COMMUNITY.
func (c *Client) TryCreateVisionPod(minVRAMGB int, maxHourly float64) (*VisionPod, error) {
	gpus, err := c.GetGPUTypes()
	if err != nil {
		return nil, fmt.Errorf("TryCreateVisionPod: fetch GPUs: %w", err)
	}

	const storageOverhead = 0.02

	type candidate struct {
		gpu       GPUType
		score     float64
		community bool
	}
	var pool []candidate

	for _, g := range gpus {
		if g.MemoryInGb < minVRAMGB {
			continue
		}
		if g.SecurePrice > 0 && g.SecurePrice+storageOverhead <= maxHourly {
			score := math.Pow(float64(g.MemoryInGb), 1.5) / (g.SecurePrice + storageOverhead)
			pool = append(pool, candidate{g, score, false})
		} else if g.CommunityPrice > 0 && g.CommunityPrice+storageOverhead <= maxHourly {
			score := math.Pow(float64(g.MemoryInGb), 1.5) / (g.CommunityPrice + storageOverhead)
			pool = append(pool, candidate{g, score, true})
		}
	}
	if len(pool) == 0 {
		return nil, fmt.Errorf("no GPU available with ≥%d GB VRAM under $%.2f/hr", minVRAMGB, maxHourly)
	}
	sort.Slice(pool, func(i, j int) bool { return pool[i].score > pool[j].score })

	var lastErr error
	for _, cand := range pool {
		pod, err := c.createVisionPod(cand.gpu.ID, cand.community)
		if err == nil {
			if cand.community {
				pod.HourlyRate = cand.gpu.CommunityPrice
			} else {
				pod.HourlyRate = cand.gpu.SecurePrice
			}
			return pod, nil
		}
		lastErr = err
	}
	return nil, fmt.Errorf("all %d GPU candidates exhausted; last error: %w", len(pool), lastErr)
}

// createVisionPod spins up a vLLM pod on RunPod.
// vLLM serves an OpenAI-compatible API at /v1/chat/completions with full vision support.
func (c *Client) createVisionPod(gpuTypeID string, community bool) (*VisionPod, error) {
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

	cloudType := "SECURE"
	if community {
		cloudType = "COMMUNITY"
	}

	// vLLM args: model from HF, tensor parallel 1 GPU, enforce eager for compat,
	// trust remote code for llava tokenizer.
	dockerArgs := fmt.Sprintf(
		"--model %s --port %d --host 0.0.0.0 --tensor-parallel-size 1 --enforce-eager --trust-remote-code --max-model-len 4096",
		VisionModel, visionPort,
	)

	variables := map[string]interface{}{
		"input": map[string]interface{}{
			"name":              "oricli-vision",
			"gpuTypeId":         gpuTypeID,
			"gpuCount":          1,
			"cloudType":         cloudType,
			"volumeInGb":        20,
			"containerDiskInGb": 30, // vLLM image (~8GB) + model (~4GB) + headroom
			"volumeMountPath":   "/root/.cache/huggingface",
			"imageName":         VLLMImage,
			"ports":             fmt.Sprintf("%d/http", visionPort),
			"dockerArgs":        dockerArgs,
			"env": []map[string]string{
				{"key": "HF_HUB_ENABLE_HF_TRANSFER", "value": "1"}, // fast HF downloads
			},
		},
	}

	result, err := c.Query(query, variables)
	if err != nil {
		return nil, fmt.Errorf("createVisionPod: %w", err)
	}

	data, _ := result["data"].(map[string]interface{})
	podData, _ := data["podFindAndDeployOnDemand"].(map[string]interface{})
	if podData == nil {
		return nil, fmt.Errorf("createVisionPod: empty response — GPU type %s unavailable", gpuTypeID)
	}

	podID, _ := podData["id"].(string)
	baseURL := fmt.Sprintf(proxyURLTemplate, podID, visionPort)

	return &VisionPod{
		PodID:     podID,
		BaseURL:   baseURL,
		GPUTypeID: gpuTypeID,
		StartedAt: time.Now(),
	}, nil
}

// WaitForVisionReady polls /v1/models until vLLM has loaded the model and is serving.
// vLLM downloads the model from HuggingFace on first boot — allow up to visionReadyMax.
func (c *Client) WaitForVisionReady(ctx context.Context, pod *VisionPod) error {
	httpClient := &http.Client{Timeout: 12 * time.Second}
	deadline := time.Now().Add(visionReadyMax)

	for time.Now().Before(deadline) {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		resp, err := httpClient.Get(pod.BaseURL + "/v1/models")
		if err == nil && resp.StatusCode == http.StatusOK {
			// Verify the model is actually listed (not just server up)
			var body struct {
				Data []struct{ ID string `json:"id"` } `json:"data"`
			}
			if jsonErr := json.NewDecoder(resp.Body).Decode(&body); jsonErr == nil {
				resp.Body.Close()
				for _, m := range body.Data {
					if strings.Contains(m.ID, "llava") || strings.Contains(m.ID, "vision") || m.ID == VisionModel {
						return nil // model loaded and ready
					}
				}
			} else {
				resp.Body.Close()
			}
		} else if resp != nil {
			resp.Body.Close()
		}

		time.Sleep(visionReadyDelay)
	}
	return fmt.Errorf("WaitForVisionReady: vLLM did not load model within %s", visionReadyMax)
}

// CallVisionInference sends a vision request to the vLLM pod via the OpenAI
// chat completions endpoint. imageB64 is raw base64 (no data: URI prefix).
func CallVisionInference(ctx context.Context, baseURL, imageB64, prompt string) (string, error) {
	payload, _ := json.Marshal(map[string]any{
		"model": VisionModel,
		"messages": []map[string]any{
			{
				"role": "user",
				"content": []map[string]any{
					{
						"type": "image_url",
						"image_url": map[string]string{
							// vLLM accepts base64 data URIs directly
							"url": "data:image/jpeg;base64," + imageB64,
						},
					},
					{
						"type": "text",
						"text": prompt,
					},
				},
			},
		},
		"max_tokens":  300,
		"temperature": 0.1,
	})

	reqCtx, cancel := context.WithTimeout(ctx, 90*time.Second)
	defer cancel()

	req, _ := http.NewRequestWithContext(reqCtx, http.MethodPost,
		baseURL+"/v1/chat/completions", bytes.NewReader(payload))
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

	var completion struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
		Error *struct {
			Message string `json:"message"`
		} `json:"error"`
	}
	if err := json.Unmarshal(raw, &completion); err != nil {
		return "", fmt.Errorf("vision decode response: %w", err)
	}
	if completion.Error != nil {
		return "", fmt.Errorf("vision model error: %s", completion.Error.Message)
	}
	if len(completion.Choices) == 0 {
		return "", fmt.Errorf("vision: empty response from model")
	}

	return strings.TrimSpace(completion.Choices[0].Message.Content), nil
}
