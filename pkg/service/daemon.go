package service

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

type JITState struct {
	LastSyncTime  int64  `json:"last_sync_time"`
	LastSyncCount int    `json:"last_sync_count"`
	UpdatedAt     string `json:"updated_at"`
}

type JITDaemon struct {
	RepoRoot        string
	JitFile         string
	CheckpointFile  string
	Threshold       int
	CooldownSeconds int64
	State           JITState
	Orchestrator    *GoOrchestrator
}

func NewJITDaemon(root string, orch *GoOrchestrator) *JITDaemon {
	d := &JITDaemon{
		RepoRoot:        root,
		JitFile:         filepath.Join(root, "oricli_core/data/jit_absorption.jsonl"),
		CheckpointFile:  filepath.Join(root, "jit_last_sync.json"),
		Threshold:       5,
		CooldownSeconds: 7200,
		Orchestrator:    orch,
	}
	d.loadState()
	return d
}

func (d *JITDaemon) loadState() {
	data, err := os.ReadFile(d.CheckpointFile)
	if err == nil {
		json.Unmarshal(data, &d.State)
	}
}

func (d *JITDaemon) saveState() {
	d.State.UpdatedAt = time.Now().Format(time.RFC3339)
	data, _ := json.MarshalIndent(d.State, "", "  ")
	os.WriteFile(d.CheckpointFile, data, 0644)
}

func (d *JITDaemon) getLessonCount() int {
	f, err := os.Open(d.JitFile)
	if err != nil {
		return 0
	}
	defer f.Close()

	count := 0
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		count++
	}
	return count
}

func (d *JITDaemon) Run() {
	log.Println("[JITDaemon] Started.")
	for {
		currentCount := d.getLessonCount()
		newLessons := currentCount - d.State.LastSyncCount

		if newLessons >= d.Threshold {
			now := time.Now()
			isNight := now.Hour() >= 23 || now.Hour() <= 5
			cooldownOver := (now.Unix() - d.State.LastSyncTime) >= d.CooldownSeconds

			if cooldownOver || isNight {
				d.triggerTraining(currentCount)
			}
		}

		time.Sleep(5 * time.Minute)
	}
}

func (d *JITDaemon) triggerTraining(currentCount int) {
	log.Printf("[JITDaemon] Triggering remote JIT knowledge absorption (Count: %d)", currentCount)

	pythonExe := filepath.Join(d.RepoRoot, ".venv/bin/python3")
	bridgeScript := filepath.Join(d.RepoRoot, "scripts/runpod_bridge.py")

	cmd := exec.Command(pythonExe, bridgeScript,
		"--cluster-size", "2",
		"--auto",
		"--min-vram", "40",
		"--max-price", "2.50",
		"--upload-to-s3",
		"--train-jit",
		"--alias", "oricli_jit_absorption",
	)
	cmd.Dir = d.RepoRoot
	cmd.Env = append(os.Environ(), "PYTHONPATH="+d.RepoRoot)

	start := time.Now()
	output, err := cmd.CombinedOutput()
	duration := time.Since(start)

	if err == nil {
		log.Printf("[JITDaemon] JIT Absorption complete in %v", duration)
		d.State.LastSyncTime = time.Now().Unix()
		d.State.LastSyncCount = currentCount
		d.saveState()

		// Update memory graph via orchestrator
		d.Orchestrator.Execute("graph_query", map[string]interface{}{
			"query": "CREATE (n:MetaEvent {id: $id, type: 'meta_event', content: $content, timestamp: $ts, importance: 0.9})",
			"params": map[string]interface{}{
				"id":      fmt.Sprintf("jit_sync_%d", d.State.LastSyncTime),
				"content": fmt.Sprintf("JIT Knowledge Absorption completed for %d lessons.", currentCount),
				"ts":      d.State.LastSyncTime,
			},
		}, 30*time.Second)
	} else {
		log.Printf("[JITDaemon] JIT Training failed: %v\nOutput: %s", err, string(output))
	}
}

type DreamDaemon struct {
	IdleThreshold int64
	CheckInterval int64
	Graph         *GraphService
	Memory        *MemoryBridge
	Gosh          *GoshModule
	Ghost         *GhostClusterService
	Orchestrator  *GoOrchestrator
	GenService    *GenerationService
	MemoryBank    *MemoryBank
	Constitution  *LivingConstitution
	lastActivity  int64
}

func NewDreamDaemon(idleThreshold, checkInterval int64, graph *GraphService, memory *MemoryBridge, gosh *GoshModule, ghost *GhostClusterService, orch *GoOrchestrator) *DreamDaemon {
	return &DreamDaemon{
		IdleThreshold: idleThreshold,
		CheckInterval: checkInterval,
		Graph:         graph,
		Memory:        memory,
		Gosh:          gosh,
		Ghost:         ghost,
		Orchestrator:  orch,
		lastActivity:  time.Now().Unix(),
	}
}

func (d *DreamDaemon) Run() {
	log.Println("[DreamDaemon] Started. Monitoring for offline consolidation...")
	for {
		currentTime := time.Now().Unix()
		idleTime := currentTime - d.lastActivity

		if idleTime > d.IdleThreshold {
			log.Printf("[DreamDaemon] System has been idle for %ds. Entering Dream State...", idleTime)
			d.ConsolidateExperience()
			d.lastActivity = time.Now().Unix()
		}

		time.Sleep(time.Duration(d.CheckInterval) * time.Second)
	}
}

func (d *DreamDaemon) ConsolidateExperience() {
	log.Println("[DreamDaemon] Offline Consolidation Initiated.")

	if d.MemoryBank == nil || !d.MemoryBank.IsEnabled() {
		log.Println("[DreamDaemon] MemoryBank unavailable — skipping consolidation.")
		d.forageForKnowledge()
		return
	}

	// Pull feedback + correction + teach signals from the last 24 hours.
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	feedbackFrags, err := d.MemoryBank.QueryBySource(ctx, []string{"feedback", "correction", "teach", "contrastive"}, 30)
	if err != nil || len(feedbackFrags) == 0 {
		log.Println("[DreamDaemon] No Imprint signals found. Foraging for knowledge instead.")
		d.forageForKnowledge()
		return
	}

	log.Printf("[DreamDaemon] Consolidating %d Imprint signals into behavioral lessons.", len(feedbackFrags))

	// Build a compact signal digest for the SLM — keep it short to stay within 512 token budget.
	var sigLines []string
	for i, f := range feedbackFrags {
		if i >= 15 { // cap at 15 signals to stay within num_predict budget
			break
		}
		preview := f.Content
		if len(preview) > 120 {
			preview = preview[:120] + "…"
		}
		sigLines = append(sigLines, fmt.Sprintf("- [%s] %s", f.Source, preview))
	}
	digest := strings.Join(sigLines, "\n")

	if d.GenService == nil {
		log.Println("[DreamDaemon] No GenService — cannot distill lessons.")
		return
	}

	prompt := fmt.Sprintf(
		"You are a behavioral analyst. Based on these user interaction signals, extract 3-5 concise behavioral rules or preferences. "+
			"Each rule must be ≤15 words and actionable (e.g., 'Prefer direct answers over long explanations'). "+
			"Return only a numbered list.\n\nSignals:\n%s\n\nRules:", digest)

	result, err := d.GenService.Generate(prompt, map[string]interface{}{
		"num_ctx":     4096,
		"num_predict": 256,
		"temperature": 0.3,
	})
	if err != nil {
		log.Printf("[DreamDaemon] SLM distillation failed: %v", err)
		return
	}

	responseText, _ := result["response"].(string)
	if responseText == "" {
		log.Println("[DreamDaemon] Empty distillation response.")
		return
	}

	// Parse numbered list into individual lessons.
	lessons := parseLessonList(responseText)
	if len(lessons) == 0 {
		log.Println("[DreamDaemon] Could not parse lessons from response.")
		return
	}

	log.Printf("[DreamDaemon] Distilled %d behavioral lessons.", len(lessons))

	// Write each lesson to MemoryBank as a durable ProvenanceUserStated fragment.
	for _, lesson := range lessons {
		d.MemoryBank.Write(MemoryFragment{
			Content:    "Learned preference: " + lesson,
			Source:     "dream_consolidation",
			Topic:      "behavioral_lesson",
			Importance: 0.85,
			Provenance: ProvenanceUserStated,
			Volatility: VolatilityStable,
		})
	}

	// Update the Living Constitution with the new lessons.
	if d.Constitution != nil {
		d.Constitution.MergeLessons(lessons, nil, nil)
		if err := d.Constitution.Save(); err != nil {
			log.Printf("[DreamDaemon] Failed to save Living Constitution: %v", err)
		} else {
			log.Println("[DreamDaemon] Living Constitution updated.")
		}
	}

	log.Println("[DreamDaemon] Consolidation complete. ORI's behavioral model evolved.")
}

// parseLessonList extracts numbered or bulleted lines from SLM output.
func parseLessonList(text string) []string {
	var lessons []string
	for _, line := range strings.Split(text, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		// Strip leading number/bullet: "1. ", "- ", "• "
		for _, prefix := range []string{"1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "-", "•", "*"} {
			if strings.HasPrefix(line, prefix) {
				line = strings.TrimSpace(line[len(prefix):])
				break
			}
		}
		if len(line) > 10 && len(line) < 200 {
			lessons = append(lessons, line)
		}
		if len(lessons) >= 5 {
			break
		}
	}
	return lessons
}

func (d *DreamDaemon) forageForKnowledge() {
	log.Println("[DreamDaemon] Scanning Knowledge Graph for low-confidence nodes...")

	// Query for nodes with few relationships (orphans)
	cypher := "MATCH (n) WHERE COUNT { (n)--() } < 2 RETURN n.id as id, labels(n) as labels LIMIT 1"
	results, err := d.Graph.ExecuteQuery(cypher, nil)
	if err != nil {
		log.Printf("[DreamDaemon] Neo4j query failed: %v", err)
		return
	}

	if len(results) > 0 {
		target := results[0]
		entityID := target["id"].(string)
		log.Printf("[DreamDaemon] Found low-context node: '%s'. Triggering research...", entityID)

		// Formulate research question via Swarm Orchestrator
		query := fmt.Sprintf("Research the context and latest news for '%s' and update the knowledge graph.", entityID)
		go d.Orchestrator.Execute("swarm_run", map[string]interface{}{
			"query":            query,
			"max_rounds":       2,
			"consensus_policy": "merge_top",
		}, 300*time.Second)
	} else {
		log.Println("[DreamDaemon] Knowledge Graph looks healthy. No immediate research needed.")
	}
}

type MetacogDaemon struct {
	RepoRoot     string
	ScanInterval int64
	Orchestrator *GoOrchestrator
	Gosh         *GoshModule // Required for sandbox pre-flights
}

func NewMetacogDaemon(root string, orch *GoOrchestrator, gosh *GoshModule) *MetacogDaemon {
	return &MetacogDaemon{
		RepoRoot:     root,
		ScanInterval: 3600,
		Orchestrator: orch,
		Gosh:         gosh,
	}
}

func (d *MetacogDaemon) Run() {
	log.Println("[MetacogDaemon] Started.")
	for {
		d.runCycle()
		time.Sleep(time.Duration(d.ScanInterval) * time.Second)
	}
}

func (d *MetacogDaemon) runCycle() {
	log.Println("[MetacogDaemon] Metacognition Cycle Started.")

	// 1. Scan Traces for anomalies
	res, err := d.Orchestrator.Execute("analyze_traces", map[string]interface{}{
		"limit": 100,
		"focus": "errors_and_latency",
	}, 60*time.Second)

	if err != nil {
		log.Printf("[MetacogDaemon] Trace scan failed: %v", err)
		return
	}

	findings, ok := res.(map[string]interface{})["findings"].([]interface{})
	if !ok || len(findings) == 0 {
		log.Println("[MetacogDaemon] No actionable anomalies found.")
		return
	}

	anomaly := findings[0].(map[string]interface{})
	issueType := anomaly["issue_type"].(string)

	if issueType == "architecture_bottleneck" {
		d.triggerNAS(anomaly)
	} else {
		d.proposeReform(anomaly)
	}
}

func (d *MetacogDaemon) triggerNAS(anomaly map[string]interface{}) {
	log.Printf("[MetacogDaemon] 🧠 Triggering NAS for bottleneck: %s", anomaly["description"])
	// Implementation would involve complex Swarm/GPU orchestration
}

func (d *MetacogDaemon) proposeReform(anomaly map[string]interface{}) {
	// ... (rest of the method logic)
}

// AssessPlan performs static and sandbox analysis on an agent's intended plan.
// Returns a RiskScore (0.0 - 1.0) where > 0.7 triggers a Kernel Reject.
func (d *MetacogDaemon) AssessPlan(ctx context.Context, plan string) (float64, string) {
	log.Printf("[Precog] Assessing risk for incoming agent plan...")

	// 1. Static Analysis for common "Hallucination" or malicious patterns
	risk := 0.0
	reason := "Plan looks stable."

	if strings.Contains(plan, "while true") || strings.Contains(plan, "fork bomb") {
		risk = 1.0
		reason = "Malicious or infinite loop pattern detected."
		return risk, reason
	}

	// 2. Sandbox Pre-flight
	if d.Gosh != nil {
		resInterface, err := d.Gosh.Execute(ctx, "execute", map[string]interface{}{
			"script": plan,
		})
		
		if err != nil {
			risk = 0.8
			reason = fmt.Sprintf("Sandbox execution error: %v", err)
			return risk, reason
		}

		res := resInterface.(ExecutionResult)
		if !res.Success {
			risk = 0.5 
			reason = "Plan failed self-validation in sandbox."
		}
	}

	return risk, reason
}

type ToolDaemon struct {
	RepoRoot        string
	CorrectionsFile string
	CheckpointFile  string
	Threshold       int
	CooldownSeconds int64
	State           struct {
		LastSyncTime  int64  `json:"last_sync_time"`
		LastSyncCount int    `json:"last_sync_count"`
		UpdatedAt     string `json:"updated_at"`
	}
}

func NewToolDaemon(root string) *ToolDaemon {
	d := &ToolDaemon{
		RepoRoot:        root,
		CorrectionsFile: filepath.Join(root, "oricli_core/data/tool_corrections.jsonl"),
		CheckpointFile:  filepath.Join(root, "tool_last_sync.json"),
		Threshold:       10,
		CooldownSeconds: 14400,
	}
	d.loadState()
	return d
}

func (d *ToolDaemon) loadState() {
	data, err := os.ReadFile(d.CheckpointFile)
	if err == nil {
		json.Unmarshal(data, &d.State)
	}
}

func (d *ToolDaemon) saveState() {
	d.State.UpdatedAt = time.Now().Format(time.RFC3339)
	data, _ := json.MarshalIndent(d.State, "", "  ")
	os.WriteFile(d.CheckpointFile, data, 0644)
}

func (d *ToolDaemon) getCorrectionCount() int {
	f, err := os.Open(d.CorrectionsFile)
	if err != nil {
		return 0
	}
	defer f.Close()

	count := 0
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		count++
	}
	return count
}

func (d *ToolDaemon) Run() {
	log.Println("[ToolDaemon] Started.")
	for {
		currentCount := d.getCorrectionCount()
		newCorrections := currentCount - d.State.LastSyncCount

		if newCorrections >= d.Threshold {
			if (time.Now().Unix() - d.State.LastSyncTime) >= d.CooldownSeconds {
				d.triggerTraining(currentCount)
			}
		}

		time.Sleep(10 * time.Minute)
	}
}

func (d *ToolDaemon) triggerTraining(currentCount int) {
	log.Printf("[ToolDaemon] Triggering remote Tool-Efficacy training (Corrections: %d)", currentCount)

	pythonExe := filepath.Join(d.RepoRoot, ".venv/bin/python3")
	bridgeScript := filepath.Join(d.RepoRoot, "scripts/runpod_bridge.py")

	cmd := exec.Command(pythonExe, bridgeScript,
		"--cluster-size", "2",
		"--auto",
		"--min-vram", "40",
		"--max-price", "2.50",
		"--upload-to-s3",
		"--train-tool-bench",
		"--alias", "oricli_tool_tuning",
	)
	cmd.Dir = d.RepoRoot
	cmd.Env = append(os.Environ(), "PYTHONPATH="+d.RepoRoot)

	start := time.Now()
	output, err := cmd.CombinedOutput()
	duration := time.Since(start)

	if err == nil {
		log.Printf("[ToolDaemon] Tool-Efficacy training complete in %v", duration)
		d.State.LastSyncTime = time.Now().Unix()
		d.State.LastSyncCount = currentCount
		d.saveState()
	} else {
		log.Printf("[ToolDaemon] Tool training failed: %v\nOutput: %s", err, string(output))
	}
}
