package service

// BenchmarkGapDetector reads ARC / LiveBench result JSON files, extracts topic
// entities from failed questions, and injects them as high-priority seeds into
// the CuriosityDaemon so ORI actively studies its own weaknesses.
//
// Priority 2.0 seeds preempt the standard knowledge-gap (priority 1.0) and
// curiosity-burst (priority 0.5) seeds, ensuring benchmark failures get
// targeted study before the next evaluation run.
//
// Usage:
//
//	detector := service.NewBenchmarkGapDetector(curiosityDaemon)
//	n, err := detector.IngestResultFile(ctx, "arc_results/run1/results.json")
//
// The detector is also wired into the WorldTraveler run cadence so that the
// most recent benchmark result (if present) is re-seeded on each world-travel
// tick.

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"unicode"
)

const benchmarkGapPriority = 2.0

// BenchmarkGapDetector extracts failing questions and injects study seeds.
type BenchmarkGapDetector struct {
	Curiosity *CuriosityDaemon
}

func NewBenchmarkGapDetector(c *CuriosityDaemon) *BenchmarkGapDetector {
	return &BenchmarkGapDetector{Curiosity: c}
}

// ── Result file schemas ───────────────────────────────────────────────────────

// arcResultFile matches the JSON written by scripts/run_arc_bench.py
type arcResultFile struct {
	RunID     string          `json:"run_id"`
	Timestamp string          `json:"timestamp"`
	Results   []arcSuiteBlock `json:"results"`
}

type arcSuiteBlock struct {
	Suite   string           `json:"suite"`
	Label   string           `json:"label"`
	Model   string           `json:"model"`
	Total   int              `json:"total"`
	Correct int              `json:"correct"`
	Results []arcItemResult  `json:"results"`
}

type arcItemResult struct {
	ID        string `json:"id"`
	Config    string `json:"config"` // e.g. "ARC-Easy", "ARC-Challenge"
	Question  string `json:"question"`
	Correct   bool   `json:"correct"`
	Predicted string `json:"predicted"`
	Expected  string `json:"expected"`
}

// ── Ingestion ─────────────────────────────────────────────────────────────────

// IngestResultFile reads an ARC/LiveBench results.json, extracts topic entities
// from failed questions, and injects priority-2 seeds into CuriosityDaemon.
// Returns the number of seeds injected.
func (d *BenchmarkGapDetector) IngestResultFile(ctx context.Context, path string) (int, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return 0, fmt.Errorf("BenchmarkGapDetector: read %s: %w", path, err)
	}

	var rf arcResultFile
	if err := json.Unmarshal(data, &rf); err != nil {
		return 0, fmt.Errorf("BenchmarkGapDetector: parse %s: %w", path, err)
	}

	topics := d.extractFailingTopics(rf)
	if len(topics) == 0 {
		log.Printf("[BenchmarkGap] %s — no failures found, nothing to seed", filepath.Base(path))
		return 0, nil
	}

	injected := 0
	label := fmt.Sprintf("benchmark_gap:%s", filepath.Base(filepath.Dir(path)))
	for topic := range topics {
		if ctx.Err() != nil {
			break
		}
		// AddSeedForce bypasses the seenKeys dedup filter so benchmark failures
		// are always re-studied, even if previously forged during normal operation.
		d.Curiosity.AddSeedForce(topic, label)
		injected++
	}

	log.Printf("[BenchmarkGap] %s — injected %d priority seeds from %d unique gap topics",
		filepath.Base(path), injected, len(topics))
	return injected, nil
}

// IngestLatestResults scans resultsDir for the most recent results.json
// and ingests it. Safe to call repeatedly — CuriosityDaemon deduplicates.
func (d *BenchmarkGapDetector) IngestLatestResults(ctx context.Context, resultsDir string) (int, error) {
	entries, err := os.ReadDir(resultsDir)
	if err != nil {
		if os.IsNotExist(err) {
			return 0, nil // no results yet — not an error
		}
		return 0, err
	}

	// Find most recent run directory (they're timestamped, lexicographic sort works)
	var latest string
	for _, e := range entries {
		if e.IsDir() {
			latest = e.Name()
		}
	}
	if latest == "" {
		return 0, nil
	}

	resultPath := filepath.Join(resultsDir, latest, "results.json")
	if _, err := os.Stat(resultPath); os.IsNotExist(err) {
		return 0, nil
	}
	return d.IngestResultFile(ctx, resultPath)
}

// ── Topic extraction ──────────────────────────────────────────────────────────

// extractFailingTopics scans all failed questions across suites and returns a
// map of topic → frequency, where topics are noun-phrase-style entities
// extracted from the question text.
func (d *BenchmarkGapDetector) extractFailingTopics(rf arcResultFile) map[string]int {
	topicFreq := map[string]int{}

	for _, suite := range rf.Results {
		for _, item := range suite.Results {
			if item.Correct {
				continue
			}
			// Skip parse failures — those are infrastructure errors, not knowledge gaps
			if strings.HasPrefix(item.Predicted, "PARSE_FAIL") {
				continue
			}

			topics := extractTopicsFromQuestion(item.Question, item.Config)
			for _, t := range topics {
				topicFreq[t]++
			}
		}
	}
	return topicFreq
}

// extractTopicsFromQuestion applies lightweight NLP to extract study-worthy
// topics from a benchmark question.
//
// Strategy (no LLM required):
//  1. Strip MCQ option lines ("A. ...", "B. ...")
//  2. Extract capitalized noun phrases (≥2 words starting with capital)
//  3. Extract domain keywords from a curated science/tech vocabulary
//  4. Use ARC config label as a topic hint ("ARC-Challenge" → harder material)
func extractTopicsFromQuestion(question, config string) []string {
	var topics []string

	// Strip option lines
	lines := strings.Split(question, "\n")
	var contentLines []string
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if len(trimmed) > 2 && trimmed[1] == '.' && trimmed[0] >= 'A' && trimmed[0] <= 'E' {
			continue
		}
		contentLines = append(contentLines, trimmed)
	}
	text := strings.Join(contentLines, " ")

	// Extract capitalized noun phrases (2-4 consecutive capitalized words)
	words := strings.Fields(text)
	for i, w := range words {
		if !startsWithUpper(w) {
			continue
		}
		// Build multi-word phrase
		phrase := []string{cleanWord(w)}
		for j := i + 1; j < len(words) && j < i+4; j++ {
			if startsWithUpper(words[j]) {
				phrase = append(phrase, cleanWord(words[j]))
			} else {
				break
			}
		}
		if len(phrase) >= 2 {
			t := strings.Join(phrase, " ")
			if len(t) > 5 {
				topics = append(topics, t)
			}
		}
	}

	// Extract domain keywords that signal specific study areas
	domainKeywords := extractDomainKeywords(text)
	topics = append(topics, domainKeywords...)

	// Deduplicate
	seen := map[string]struct{}{}
	unique := topics[:0]
	for _, t := range topics {
		lt := strings.ToLower(t)
		if _, ok := seen[lt]; ok {
			continue
		}
		seen[lt] = struct{}{}
		unique = append(unique, t)
	}
	topics = unique

	// Cap at 5 topics per question to avoid dilution
	if len(topics) > 5 {
		topics = topics[:5]
	}

	return topics
}

func startsWithUpper(s string) bool {
	if s == "" {
		return false
	}
	return unicode.IsUpper(rune(s[0]))
}

func cleanWord(w string) string {
	return strings.Trim(w, ".,;:?!()")
}

// scienceKeywords maps domain signal words to their study topic.
// Organized by ARC subject area.
var scienceKeywordMap = map[string]string{
	// Life science
	"photosynthesis": "photosynthesis and plant biology",
	"mitosis":        "cell division and mitosis",
	"meiosis":        "meiosis and reproduction",
	"chromosome":     "genetics and chromosomes",
	"dna":            "DNA and molecular genetics",
	"evolution":      "natural selection and evolution",
	"ecosystem":      "ecosystems and ecology",
	"habitat":        "ecosystems and ecology",
	"organism":       "biology and organisms",
	"cell":           "cell biology",
	"nutrient":       "nutrition and biology",

	// Physical science
	"atom":         "atomic structure and chemistry",
	"molecule":     "molecules and chemical bonding",
	"electron":     "electrons and atomic physics",
	"proton":       "atomic structure",
	"neutron":      "atomic structure",
	"energy":       "energy transfer and physics",
	"gravity":      "gravitational physics",
	"friction":     "forces and motion",
	"velocity":     "kinematics and motion",
	"acceleration": "kinematics and motion",
	"wave":         "wave properties and physics",
	"frequency":    "wave physics and sound",
	"magnet":       "magnetism and electromagnetism",
	"current":      "electricity and circuits",
	"circuit":      "electrical circuits",
	"voltage":      "electricity and circuits",
	"conductor":    "electrical conductors and insulators",

	// Earth science
	"erosion":      "erosion and geology",
	"sediment":     "sedimentation and geology",
	"tectonic":     "plate tectonics",
	"volcano":      "volcanoes and geology",
	"earthquake":   "earthquakes and seismology",
	"atmosphere":   "atmosphere and meteorology",
	"weather":      "meteorology and climate",
	"climate":      "climate science",
	"precipitation": "water cycle and precipitation",
	"evaporation":  "water cycle",
	"solar":        "solar system and astronomy",
	"orbit":        "orbital mechanics and astronomy",
	"planet":       "planetary science",
	"asteroid":     "asteroids and solar system",

	// Technology / CS
	"algorithm":   "algorithms and computer science",
	"neural":      "neural networks and machine learning",
	"quantum":     "quantum computing and physics",
	"genome":      "genomics and bioinformatics",
	"protein":     "protein structure and biochemistry",
}

func extractDomainKeywords(text string) []string {
	lower := strings.ToLower(text)
	seen := map[string]struct{}{}
	var topics []string
	for keyword, topic := range scienceKeywordMap {
		if strings.Contains(lower, keyword) {
			if _, ok := seen[topic]; !ok {
				seen[topic] = struct{}{}
				topics = append(topics, topic)
			}
		}
	}
	return topics
}

// ── Summary report ────────────────────────────────────────────────────────────

// GapSummary returns a human-readable summary of the most frequent gap topics
// found in the given result file.
func (d *BenchmarkGapDetector) GapSummary(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	var rf arcResultFile
	if err := json.Unmarshal(data, &rf); err != nil {
		return "", err
	}

	topics := d.extractFailingTopics(rf)
	if len(topics) == 0 {
		return "No knowledge gaps detected (all questions answered correctly).", nil
	}

	// Sort by frequency
	type kv struct{ k string; v int }
	var sorted []kv
	for k, v := range topics {
		sorted = append(sorted, kv{k, v})
	}
	// Simple bubble sort for small list
	for i := 0; i < len(sorted); i++ {
		for j := i + 1; j < len(sorted); j++ {
			if sorted[j].v > sorted[i].v {
				sorted[i], sorted[j] = sorted[j], sorted[i]
			}
		}
	}

	var sb strings.Builder
	totalFailed := 0
	for _, suite := range rf.Results {
		for _, item := range suite.Results {
			if !item.Correct && !strings.HasPrefix(item.Predicted, "PARSE_FAIL") {
				totalFailed++
			}
		}
	}

	sb.WriteString(fmt.Sprintf("Knowledge gap analysis — %d failed questions:\n", totalFailed))
	limit := 10
	if len(sorted) < limit {
		limit = len(sorted)
	}
	for _, kv := range sorted[:limit] {
		sb.WriteString(fmt.Sprintf("  • %s (appears in %d questions)\n", kv.k, kv.v))
	}
	return sb.String(), nil
}
