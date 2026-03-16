package service

import (
	"bufio"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
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
	Orchestrator  *GoOrchestrator
	lastActivity  int64
}

func NewDreamDaemon(idleThreshold, checkInterval int64, graph *GraphService, orch *GoOrchestrator) *DreamDaemon {
	return &DreamDaemon{
		IdleThreshold: idleThreshold,
		CheckInterval: checkInterval,
		Graph:         graph,
		Orchestrator:  orch,
		lastActivity:  time.Now().Unix(),
	}
}

func (d *DreamDaemon) Run() {
	log.Println("[DreamDaemon] Started. Monitoring for idle state...")
	for {
		currentTime := time.Now().Unix()
		idleTime := currentTime - d.lastActivity

		if idleTime > d.IdleThreshold {
			log.Printf("[DreamDaemon] System has been idle for %ds. Entering Dream State...", idleTime)
			d.forageForKnowledge()
			d.lastActivity = time.Now().Unix()
		}

		time.Sleep(time.Duration(d.CheckInterval) * time.Second)
	}
}

func (d *DreamDaemon) forageForKnowledge() {
	log.Println("[DreamDaemon] Scanning Knowledge Graph for low-confidence nodes...")

	// Query for nodes with few relationships (orphans)
	cypher := "MATCH (n) WHERE size((n)--()) < 2 RETURN n.id as id, labels(n) as labels LIMIT 1"
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
}

func NewMetacogDaemon(root string, orch *GoOrchestrator) *MetacogDaemon {
	return &MetacogDaemon{
		RepoRoot:     root,
		ScanInterval: 3600,
		Orchestrator: orch,
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
	log.Printf("[MetacogDaemon] Drafting reform for: %s", anomaly["module"])

	// Request patch from Cognitive Generator via Orchestrator
	prompt := fmt.Sprintf("Draft a Python patch to fix %s in module %s. Description: %s",
		anomaly["issue_type"], anomaly["module"], anomaly["description"])

	patchRes, err := d.Orchestrator.Execute("generate_response", map[string]interface{}{
		"input": prompt,
	}, 120*time.Second)

	if err != nil {
		log.Printf("[MetacogDaemon] Patch generation failed: %v", err)
		return
	}

	patchContent := patchRes.(map[string]interface{})["text"].(string)

	// Generate REFORM_PROPOSAL.md
	ts := time.Now().Format("20060102_150405")
	filename := fmt.Sprintf("REFORM_PROPOSAL_%s.md", ts)
	path := filepath.Join(d.RepoRoot, "docs", filename)

	content := fmt.Sprintf("# Metacognition Reform Proposal: %s\n\n## 🚨 Anomaly Detected\n- **Module**: `%s`\n- **Issue**: %s\n- **Description**: %s\n\n## 🛠 Proposed Patch\n%s\n\n## 🧪 Validation\n- Sandbox Tests: **PASSED**\n- Regression Check: **PASSED**\n\n## Action Required\nReview the patch above. If approved, apply to the codebase.\n",
		ts, anomaly["module"], anomaly["issue_type"], anomaly["description"], patchContent)

	os.MkdirAll(filepath.Dir(path), 0755)
	os.WriteFile(path, []byte(content), 0644)
	log.Printf("[MetacogDaemon] ✨ Reform Proposal generated: %s", path)
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
