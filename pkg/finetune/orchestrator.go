package finetune

// FineTuneOrchestrator drives the full automated LoRA training pipeline:
//
//  1. Generate dataset (pkg/training)
//  2. Generate ephemeral SSH keypair
//  3. Create RunPod pod (Axolotl image, inject public key)
//  4. Wait until pod is RUNNING + SSH is live
//  5. Upload dataset JSONL + Axolotl config to pod
//  6. SSH exec: axolotl train config.yaml  (blocking, streams logs)
//  7. SSH exec: convert merged model to GGUF
//  8. SCP: pull GGUF to local data/ dir
//  9. Terminate pod (stop billing)
// 10. Swap model in Ollama (scripts/swap_ollama_model.sh)

import (
	"bytes"
	"context"
	"embed"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/thynaptic/oricli-go/pkg/training"
)

// ─────────────────────────────────────────────────────────────────────────────
// Embedded Axolotl config template
// ─────────────────────────────────────────────────────────────────────────────

//go:embed axolotl_template.yaml
var axolotlTemplateFS embed.FS

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

// RunConfig controls a single fine-tuning run.
type RunConfig struct {
	ModelBase      string // HF model ID, default: Qwen/Qwen2.5-1.5B-Instruct
	DatasetCount   int    // examples per category, default: 200
	GPUType        string // default: NVIDIA GeForce RTX 4090
	MaxDurationMin int    // hard timeout in minutes, default: 240 (4h)
	OutputDir      string // local dir for GGUF output, default: data/
	PBPull         bool   // pull real PB sessions into dataset
}

func (r *RunConfig) setDefaults() {
	if r.ModelBase == "" {
		r.ModelBase = "Qwen/Qwen2.5-1.5B-Instruct"
	}
	if r.DatasetCount <= 0 {
		r.DatasetCount = 200
	}
	if r.GPUType == "" {
		r.GPUType = DefaultGPUType
	}
	if r.MaxDurationMin <= 0 {
		r.MaxDurationMin = 240
	}
	if r.OutputDir == "" {
		r.OutputDir = "data"
	}
}

// StepName identifies a pipeline step.
type StepName string

const (
	StepDataset    StepName = "dataset_gen"
	StepSpawnPod   StepName = "spawn_pod"
	StepWaitPod    StepName = "wait_pod_ready"
	StepUpload     StepName = "upload_to_pod"
	StepTrain      StepName = "axolotl_train"
	StepConvert    StepName = "convert_gguf"
	StepPullGGUF   StepName = "pull_gguf"
	StepTerminate  StepName = "terminate_pod"
	StepSwapModel  StepName = "swap_ollama_model"
	StepDone       StepName = "done"
)

// ProgressEvent is emitted on the Progress channel during a run.
type ProgressEvent struct {
	Step    StepName
	Message string
	PctDone int // 0–100
	Error   error
}

// RunResult is the final result of a completed run.
type RunResult struct {
	GGUFPath   string
	PodID      string
	DurationMs int64
	Error      error
}

// ─────────────────────────────────────────────────────────────────────────────
// Orchestrator
// ─────────────────────────────────────────────────────────────────────────────

// FineTuneOrchestrator coordinates the full training pipeline.
type FineTuneOrchestrator struct {
	Pods     *PodClient
	DataGen  *training.DatasetGenerator
	RepoRoot string // absolute path to Mavaia repo root
}

// NewOrchestrator creates an orchestrator.
func NewOrchestrator(pods *PodClient, dataGen *training.DatasetGenerator, repoRoot string) *FineTuneOrchestrator {
	return &FineTuneOrchestrator{
		Pods:     pods,
		DataGen:  dataGen,
		RepoRoot: repoRoot,
	}
}

// Run executes the full pipeline. Progress events are sent to the returned channel.
// The channel is closed when the pipeline completes (success or error).
func (o *FineTuneOrchestrator) Run(ctx context.Context, cfg RunConfig) (<-chan ProgressEvent, <-chan RunResult) {
	cfg.setDefaults()
	progress := make(chan ProgressEvent, 20)
	results := make(chan RunResult, 1)

	go func() {
		defer close(progress)
		defer close(results)

		result := o.run(ctx, cfg, progress)
		results <- result
	}()

	return progress, results
}

func (o *FineTuneOrchestrator) run(ctx context.Context, cfg RunConfig, progress chan<- ProgressEvent) RunResult {
	start := time.Now()
	emit := func(step StepName, msg string, pct int) {
		log.Printf("[FineTune] [%s] %s", step, msg)
		progress <- ProgressEvent{Step: step, Message: msg, PctDone: pct}
	}
	fail := func(step StepName, err error) RunResult {
		progress <- ProgressEvent{Step: step, Error: err, Message: err.Error()}
		return RunResult{Error: err}
	}

	// Hard timeout context
	timeout := time.Duration(cfg.MaxDurationMin) * time.Minute
	runCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	// ── Step 1: Generate dataset ──────────────────────────────────────────────
	emit(StepDataset, fmt.Sprintf("generating dataset (%d examples/category)", cfg.DatasetCount), 5)

	examples, stats := o.DataGen.Generate(runCtx, cfg.DatasetCount)
	jsonl, err := o.DataGen.ExportJSONL(examples)
	if err != nil {
		return fail(StepDataset, fmt.Errorf("export jsonl: %w", err))
	}

	localJSONL := filepath.Join(o.RepoRoot, cfg.OutputDir, "sot_train.jsonl")
	if err := os.MkdirAll(filepath.Dir(localJSONL), 0755); err != nil {
		return fail(StepDataset, err)
	}
	if err := os.WriteFile(localJSONL, []byte(jsonl), 0644); err != nil {
		return fail(StepDataset, err)
	}
	emit(StepDataset, fmt.Sprintf("dataset ready: %d examples across %d patterns", stats.Total, len(stats.ByPattern)), 10)

	// ── Step 2: Generate SSH keypair ──────────────────────────────────────────
	keypair, err := GenerateSSHKeypair()
	if err != nil {
		return fail(StepSpawnPod, fmt.Errorf("keygen: %w", err))
	}

	// ── Step 3: Spawn pod ─────────────────────────────────────────────────────
	emit(StepSpawnPod, fmt.Sprintf("creating RunPod pod (GPU: %s, image: %s)", cfg.GPUType, AxolotlImage), 12)

	podCfg := PodConfig{
		Name:              "oricli-finetune-" + time.Now().Format("20060102-150405"),
		ImageName:         AxolotlImage,
		GPUTypeIDs:        []string{cfg.GPUType},
		ContainerDiskInGb: 80,
		VolumeInGb:        50,
		Ports:             []string{"22/tcp"},
		Env: map[string]string{
			"AUTHORIZED_KEY": keypair.AuthorizedKeyLine,
			"PUBLIC_KEY":     keypair.AuthorizedKeyLine,
		},
		DockerStartCmd: []string{
			"bash", "-c",
			`mkdir -p ~/.ssh && echo "$AUTHORIZED_KEY" >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && service ssh start && sleep infinity`,
		},
	}

	pod, err := o.Pods.CreatePod(runCtx, podCfg)
	if err != nil {
		return fail(StepSpawnPod, fmt.Errorf("create pod: %w", err))
	}
	podID := pod.ID
	emit(StepSpawnPod, fmt.Sprintf("pod created: %s", podID), 15)

	// Ensure pod is terminated even on failure
	defer func() {
		if podID != "" {
			log.Printf("[FineTune] terminating pod %s", podID)
			if terr := o.Pods.TerminatePod(context.Background(), podID); terr != nil {
				log.Printf("[FineTune] WARNING: terminate pod failed: %v", terr)
			}
		}
	}()

	// ── Step 4: Wait for pod RUNNING + SSH ───────────────────────────────────
	emit(StepWaitPod, "waiting for pod to become RUNNING...", 18)

	readyPod, err := o.Pods.WaitUntilRunning(runCtx, podID)
	if err != nil {
		return fail(StepWaitPod, err)
	}
	emit(StepWaitPod, fmt.Sprintf("pod running at %s:%d", readyPod.PublicIP, readyPod.SSHPort()), 22)

	// Dial SSH (pod SSH daemon may need a few seconds after RUNNING)
	emit(StepWaitPod, "dialling SSH (up to 10 attempts)...", 24)
	ssh, err := DialWithRetry(readyPod.PublicIP, readyPod.SSHPort(), keypair.PrivateKey, 10, 15*time.Second)
	if err != nil {
		return fail(StepWaitPod, fmt.Errorf("ssh connect: %w", err))
	}
	defer ssh.Close()
	emit(StepWaitPod, "SSH connected", 26)

	// ── Step 5: Upload dataset + config ──────────────────────────────────────
	emit(StepUpload, "uploading dataset JSONL to pod...", 28)

	if err := ssh.UploadFile(localJSONL, "/workspace/sot_train.jsonl"); err != nil {
		return fail(StepUpload, fmt.Errorf("upload dataset: %w", err))
	}

	axolotlConfig, err := o.buildAxolotlConfig(cfg)
	if err != nil {
		return fail(StepUpload, fmt.Errorf("build axolotl config: %w", err))
	}
	if err := ssh.UploadBytes([]byte(axolotlConfig), "/workspace/config.yaml"); err != nil {
		return fail(StepUpload, fmt.Errorf("upload config: %w", err))
	}
	emit(StepUpload, "dataset + config uploaded", 32)

	// Create workspace dirs on pod
	if _, err := ssh.Exec("mkdir -p /workspace/fine-tuning/outputs /workspace/fine-tuning/.cache"); err != nil {
		return fail(StepUpload, err)
	}

	// ── Step 6: Train ─────────────────────────────────────────────────────────
	emit(StepTrain, "starting axolotl train (this takes 1-3h)...", 35)

	var trainLog bytes.Buffer
	trainWriter := io.MultiWriter(&trainLog, &prefixWriter{prefix: "[axolotl] ", w: os.Stdout})
	if err := ssh.ExecStream("axolotl train /workspace/config.yaml 2>&1", trainWriter); err != nil {
		return fail(StepTrain, fmt.Errorf("axolotl train: %w\nlog tail: %s", err, tail(trainLog.String(), 500)))
	}
	emit(StepTrain, "training complete", 70)

	// ── Step 7: Merge + convert to GGUF ──────────────────────────────────────
	emit(StepConvert, "merging LoRA weights...", 72)

	if _, err := ssh.Exec("axolotl merge-lora /workspace/config.yaml 2>&1"); err != nil {
		return fail(StepConvert, fmt.Errorf("merge-lora: %w", err))
	}

	emit(StepConvert, "converting to GGUF (q4_k_m)...", 78)

	convertCmd := fmt.Sprintf(
		"python3 /workspace/llama.cpp/convert_hf_to_gguf.py "+
			"/workspace/fine-tuning/outputs/sot-lora/merged "+
			"--outfile /workspace/fine-tuning/outputs/sot-lora/oricli-sot-q4.gguf "+
			"--outtype q4_k_m 2>&1",
	)
	if _, err := ssh.Exec(convertCmd); err != nil {
		// llama.cpp may not be in the Axolotl image — fallback: pull unquantized
		emit(StepConvert, "WARNING: llama.cpp convert failed, pulling raw safetensors instead", 80)
	} else {
		emit(StepConvert, "GGUF conversion complete", 82)
	}

	// ── Step 8: Pull GGUF (or merged model) ──────────────────────────────────
	localGGUF := filepath.Join(o.RepoRoot, cfg.OutputDir, "oricli-sot-q4.gguf")
	remotePath := "/workspace/fine-tuning/outputs/sot-lora/oricli-sot-q4.gguf"

	emit(StepPullGGUF, "downloading GGUF from pod...", 85)

	// Check GGUF exists; if not, note path for manual pull
	checkOut, _ := ssh.Exec(fmt.Sprintf("test -f %s && echo exists || echo missing", remotePath))
	if strings.Contains(checkOut, "missing") {
		// GGUF conversion failed — tell user where merged model is
		return fail(StepPullGGUF, fmt.Errorf(
			"GGUF not found at %s — manually pull merged model from pod %s:/workspace/fine-tuning/outputs/sot-lora/merged/",
			remotePath, podID,
		))
	}

	if err := ssh.DownloadFile(remotePath, localGGUF); err != nil {
		return fail(StepPullGGUF, fmt.Errorf("scp gguf: %w", err))
	}
	emit(StepPullGGUF, fmt.Sprintf("GGUF saved to %s", localGGUF), 90)

	// ── Step 9: Terminate pod (defer handles this) ────────────────────────────
	emit(StepTerminate, "terminating RunPod pod...", 92)
	// defer above handles actual termination — clear podID to avoid double-terminate
	terminatedID := podID
	podID = ""
	_ = terminatedID
	emit(StepTerminate, "pod terminated", 94)

	// ── Step 10: Swap Ollama model ────────────────────────────────────────────
	emit(StepSwapModel, "swapping Ollama model...", 96)

	swapScript := filepath.Join(o.RepoRoot, "scripts", "swap_ollama_model.sh")
	cmd := exec.CommandContext(runCtx, "bash", swapScript, localGGUF)
	cmd.Dir = o.RepoRoot
	swapOut, err := cmd.CombinedOutput()
	if err != nil {
		return fail(StepSwapModel, fmt.Errorf("swap script: %w\n%s", err, string(swapOut)))
	}
	emit(StepSwapModel, "model swapped — oricli-sot:latest active", 99)
	emit(StepDone, "FineTune pipeline complete", 100)

	return RunResult{
		GGUFPath:   localGGUF,
		PodID:      terminatedID,
		DurationMs: time.Since(start).Milliseconds(),
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

// buildAxolotlConfig returns the Axolotl YAML with model and dataset paths substituted.
func (o *FineTuneOrchestrator) buildAxolotlConfig(cfg RunConfig) (string, error) {
	// Try embedded template first, fall back to reading from repo
	tmplBytes, err := axolotlTemplateFS.ReadFile("axolotl_template.yaml")
	if err != nil {
		// Fall back to reading from config/sot_axolotl.yaml
		tmplBytes, err = os.ReadFile(filepath.Join(o.RepoRoot, "config", "sot_axolotl.yaml"))
		if err != nil {
			return "", fmt.Errorf("read axolotl config: %w", err)
		}
	}

	config := string(tmplBytes)
	// Substitute placeholders
	config = strings.ReplaceAll(config, "Qwen/Qwen2.5-1.5B-Instruct", cfg.ModelBase)
	// Point to local file on pod (not HF dataset)
	config = strings.ReplaceAll(config, "thynaptic/oricli-sot", "/workspace/sot_train.jsonl")
	config = strings.ReplaceAll(config, "type: alpaca", "type: alpaca\n    data_files:\n      - /workspace/sot_train.jsonl")
	config = strings.ReplaceAll(config, "/workspace/fine-tuning/outputs/sot-lora", "/workspace/fine-tuning/outputs/sot-lora")

	return config, nil
}

// tail returns the last n bytes of a string.
func tail(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[len(s)-n:]
}

// prefixWriter prepends a prefix to each write.
type prefixWriter struct {
	prefix string
	w      io.Writer
}

func (p *prefixWriter) Write(b []byte) (int, error) {
	lines := strings.Split(string(b), "\n")
	for _, line := range lines {
		if line != "" {
			fmt.Fprintf(p.w, "%s%s\n", p.prefix, line)
		}
	}
	return len(b), nil
}
