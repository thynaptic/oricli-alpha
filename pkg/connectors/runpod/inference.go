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
	KoboldCppImage   = "koboldai/koboldcpp:latest"
	A1111Image       = "ashleykleynhans/stable-diffusion-webui:latest"
	VLLMPrimaryImage = "vllm/vllm-openai:latest"
	primaryPort      = 8000
	proxyURLTemplate = "https://%s-%d.proxy.runpod.net"
)

// HFModels is the vLLM/HuggingFace model catalog for the primary inference pod.
// All models are AWQ 4-bit quantized for vLLM — dramatically lower VRAM requirements
// vs native BF16, with minimal quality loss on chat/code/reasoning tasks.
//
// VRAM guide (AWQ 4-bit):
//   Qwen2.5-32B-AWQ  ≈ 20 GB  (fits A40 48GB @ $0.33/hr)
//   Qwen2.5-14B-AWQ  ≈  9 GB  (fits RTX A4000 16GB @ $0.17/hr)
//   Qwen2.5-7B-AWQ   ≈  5 GB  (fits RTX 3080 10GB @ $0.12/hr)
//   Qwen2.5-3B       ≈  3 GB  (fallback for tiny GPUs)
//
// Ordered largest-first; first model whose MinVRAMGB ≤ available VRAM wins.
// Override via RUNPOD_PRIMARY_MODEL env var.
var HFModels = []struct {
	MinVRAMGB int
	ID        string // HuggingFace model ID
	Name      string
	AWQ       bool   // true = pass --quantization awq to vLLM
}{
	{MinVRAMGB: 24, ID: "Qwen/Qwen2.5-32B-Instruct-AWQ",  Name: "Qwen2.5-32B-AWQ",  AWQ: true},
	{MinVRAMGB: 12, ID: "Qwen/Qwen2.5-14B-Instruct-AWQ",  Name: "Qwen2.5-14B-AWQ",  AWQ: true},
	{MinVRAMGB: 6,  ID: "Qwen/Qwen2.5-7B-Instruct-AWQ",   Name: "Qwen2.5-7B-AWQ",   AWQ: true},
	{MinVRAMGB: 3,  ID: "Qwen/Qwen2.5-3B-Instruct",       Name: "Qwen2.5-3B",        AWQ: false},
}

// HFModelForVRAM returns the best HuggingFace model ID for available GPU VRAM.
func HFModelForVRAM(vramGB int, override string) (id, name string, awq bool) {
	if override != "" {
		return override, override, false
	}
	for _, m := range HFModels {
		if vramGB >= m.MinVRAMGB {
			return m.ID, m.Name, m.AWQ
		}
	}
	last := HFModels[len(HFModels)-1]
	return last.ID, last.Name, last.AWQ
}

// PrimaryPod is a live RunPod pod running vLLM with a HuggingFace model.
type PrimaryPod struct {
	PodID       string
	EndpointURL string // https://{id}-8000.proxy.runpod.net/v1
	ModelID     string // HuggingFace model ID loaded
	ModelName   string
	GPUTypeID   string
	HourlyRate  float64
	StartedAt   time.Time
}

// CreatePrimaryPod spins up a vLLM pod on RunPod.
// modelID is a HuggingFace model ID (e.g. "Qwen/Qwen2.5-14B-Instruct-AWQ").
// awq=true adds --quantization awq to the vLLM docker args.
// vLLM exposes an OpenAI-compatible API at /v1/chat/completions.
func (c *Client) CreatePrimaryPod(gpuTypeID, modelID string, awq, community bool) (*PrimaryPod, error) {
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

	dockerArgs := fmt.Sprintf(
		"--model %s --port %d --host 0.0.0.0 --trust-remote-code --max-model-len 8192 --tensor-parallel-size 1",
		modelID, primaryPort,
	)
	if awq {
		dockerArgs += " --quantization awq"
	}

	variables := map[string]interface{}{
		"input": map[string]interface{}{
			"name":              "oricli-primary",
			"gpuTypeId":         gpuTypeID,
			"gpuCount":          1,
			"cloudType":         cloudType,
			"volumeInGb":        30, // HF cache persists across pod restarts
			"containerDiskInGb": 30,
			"volumeMountPath":   "/root/.cache/huggingface",
			"imageName":         VLLMPrimaryImage,
			"ports":             fmt.Sprintf("%d/http", primaryPort),
			"dockerArgs":        dockerArgs,
			"env": []map[string]string{
				{"key": "HF_HUB_ENABLE_HF_TRANSFER", "value": "1"},
			},
		},
	}

	result, err := c.Query(query, variables)
	if err != nil {
		return nil, fmt.Errorf("CreatePrimaryPod: %w", err)
	}

	data, _ := result["data"].(map[string]interface{})
	podData, _ := data["podFindAndDeployOnDemand"].(map[string]interface{})
	if podData == nil {
		return nil, fmt.Errorf("CreatePrimaryPod: empty response — GPU type %s unavailable", gpuTypeID)
	}

	podID, _ := podData["id"].(string)
	endpointURL := fmt.Sprintf(proxyURLTemplate, podID, primaryPort) + "/v1"

	return &PrimaryPod{
		PodID:       podID,
		EndpointURL: endpointURL,
		ModelID:     modelID,
		GPUTypeID:   gpuTypeID,
		StartedAt:   time.Now(),
	}, nil
}

// TryCreatePrimaryPod iterates GPU candidates in VRAM-per-dollar order,
// trying SECURE cloud first, falling back to COMMUNITY, until one succeeds.
func (c *Client) TryCreatePrimaryPod(minVRAMGB int, maxHourly float64, modelOverride string) (*PrimaryPod, error) {
	gpus, err := c.GetGPUTypes()
	if err != nil {
		return nil, fmt.Errorf("TryCreatePrimaryPod: fetch GPUs: %w", err)
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
		modelID, modelName, awq := HFModelForVRAM(cand.gpu.MemoryInGb, modelOverride)
		pod, err := c.CreatePrimaryPod(cand.gpu.ID, modelID, awq, cand.community)
		if err == nil {
			pod.ModelName = modelName
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

// WaitForPrimaryReady polls /v1/models until vLLM has downloaded and loaded the model.
// vLLM downloads from HuggingFace on first boot — allow up to 12 minutes.
func (c *Client) WaitForPrimaryReady(ctx context.Context, pod *PrimaryPod) error {
	httpClient := &http.Client{Timeout: 12 * time.Second}
	deadline := time.Now().Add(12 * time.Minute)

	for time.Now().Before(deadline) {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}
		resp, err := httpClient.Get(fmt.Sprintf(proxyURLTemplate, pod.PodID, primaryPort) + "/v1/models")
		if err == nil && resp.StatusCode == 200 {
			resp.Body.Close()
			return nil
		}
		if resp != nil {
			resp.Body.Close()
		}
		time.Sleep(15 * time.Second)
	}
	return fmt.Errorf("WaitForPrimaryReady: vLLM pod %s not ready within 12 minutes", pod.PodID)
}

// CatalogEntry maps a VRAM floor to a baked-in GGUF model URL.
type CatalogEntry struct {
	MinVRAMGB int
	Name      string
	URL       string // direct HuggingFace resolve URL
}

// TierModels is the baked-in model catalog. The system auto-selects the best
// model for the available GPU VRAM — no RUNPOD_MODEL_URL config required.
// Entries are ordered largest-first; first entry that fits the GPU wins.
// Override any tier with env RUNPOD_MODEL_URL_CODE, RUNPOD_MODEL_URL_RESEARCH.
var TierModels = map[string][]CatalogEntry{
	"code": {
		{MinVRAMGB: 14, Name: "Qwen2.5-Coder-14B-Q4K", URL: "https://huggingface.co/bartowski/Qwen2.5-Coder-14B-Instruct-GGUF/resolve/main/Qwen2.5-Coder-14B-Instruct-Q4_K_M.gguf"},
		{MinVRAMGB: 6, Name: "Qwen2.5-Coder-7B-Q4K", URL: "https://huggingface.co/bartowski/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf"},
	},
	"research": {
		{MinVRAMGB: 14, Name: "Cogito-16B-Q4K", URL: "https://huggingface.co/cognitivecomputations/cogito-v1-preview-llama-16B-GGUF/resolve/main/cogito-v1-preview-llama-16B.Q4_K_M.gguf"},
		{MinVRAMGB: 10, Name: "Qwen2.5-Coder-14B-Q4K", URL: "https://huggingface.co/bartowski/Qwen2.5-Coder-14B-Instruct-GGUF/resolve/main/Qwen2.5-Coder-14B-Instruct-Q4_K_M.gguf"},
		{MinVRAMGB: 6, Name: "Qwen2.5-Coder-7B-Q4K", URL: "https://huggingface.co/bartowski/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf"},
	},
	"chat": {
		{MinVRAMGB: 4, Name: "Ministral-3B-Q4K", URL: "https://huggingface.co/bartowski/Ministral-3B-Instruct-GGUF/resolve/main/Ministral-3B-Instruct-Q4_K_M.gguf"},
	},
}

// ModelURLForTier returns the best GGUF URL for the given tier and available GPU VRAM.
// override takes precedence when non-empty (for RUNPOD_MODEL_URL_* env vars).
func ModelURLForTier(tier string, vramGB int, override string) string {
	if override != "" {
		return override
	}
	entries, ok := TierModels[tier]
	if !ok {
		entries = TierModels["code"]
	}
	for _, e := range entries {
		if vramGB >= e.MinVRAMGB {
			return e.URL
		}
	}
	// Fallback: smallest model
	return entries[len(entries)-1].URL
}

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

// SelectBestGPUAny is like SelectBestGPU but also considers community-cloud GPUs
// when no secure-cloud GPU is available. Returns the GPU and a bool indicating
// whether it is community-cloud (caller must set cloudType accordingly).
func (c *Client) SelectBestGPUAny(minVRAMGB int, maxHourly float64) (*GPUType, bool, error) {
	gpus, err := c.GetGPUTypes()
	if err != nil {
		return nil, false, fmt.Errorf("SelectBestGPUAny: fetch GPU types: %w", err)
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
		return nil, false, fmt.Errorf("no GPU available with ≥%d GB VRAM under $%.2f/hr", minVRAMGB, maxHourly)
	}
	sort.Slice(pool, func(i, j int) bool { return pool[i].score > pool[j].score })
	best := pool[0]
	return &best.gpu, best.community, nil
}


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

// ImageGenPod is a live RunPod pod running Stable Diffusion WebUI (A1111) in API mode.
type ImageGenPod struct {
	PodID       string
	EndpointURL string // https://{id}-7860.proxy.runpod.net
	GPUTypeID   string
	HourlyRate  float64
	StartedAt   time.Time
}

// CreateImageGenPod spins up an A1111 Stable Diffusion WebUI pod with API enabled.
// The pod exposes /sdapi/v1/txt2img on port 7860.
func (c *Client) CreateImageGenPod(gpuTypeID string) (*ImageGenPod, error) {
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
			"name":              "oricli-imagegen",
			"gpuTypeId":         gpuTypeID,
			"gpuCount":          1,
			"cloudType":         "SECURE",
			"volumeInGb":        30,
			"containerDiskInGb": 30,
			"volumeMountPath":   "/workspace",
			"imageName":         A1111Image,
			"ports":             "7860/http,22/tcp",
			// A1111 container uses COMMANDLINE_ARGS env to pass launch flags
			"env": []map[string]string{
				{"key": "COMMANDLINE_ARGS", "value": "--api --nowebui --skip-torch-cuda-test --no-half-vae --xformers --listen"},
			},
		},
	}

	result, err := c.Query(query, variables)
	if err != nil {
		return nil, fmt.Errorf("CreateImageGenPod: %w", err)
	}

	data, _ := result["data"].(map[string]interface{})
	podData, _ := data["podFindAndDeployOnDemand"].(map[string]interface{})
	if podData == nil {
		return nil, fmt.Errorf("CreateImageGenPod: empty response — GPU type %s may be unavailable", gpuTypeID)
	}

	podID, _ := podData["id"].(string)
	endpointURL := fmt.Sprintf(proxyURLTemplate, podID, 7860)

	return &ImageGenPod{
		PodID:       podID,
		EndpointURL: endpointURL,
		GPUTypeID:   gpuTypeID,
		StartedAt:   time.Now(),
	}, nil
}

// WaitForImageReady polls A1111's /sdapi/v1/options until it responds (model loaded).
// A1111 typically takes 1–3 minutes on first boot.
func (c *Client) WaitForImageReady(ctx context.Context, pod *ImageGenPod) error {
	healthURL := pod.EndpointURL + "/sdapi/v1/options"
	httpClient := &http.Client{Timeout: 15 * time.Second}

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
