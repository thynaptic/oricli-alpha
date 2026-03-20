package cognition

import (
	"context"
	"fmt"
	"hash/fnv"
	"log"
	"math"
	"math/rand"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
)

const (
	defaultPruneThreshold = 0.30
	defaultUCB1C          = 1.25
	defaultMaxTableSize   = 256
)

type MCTSStrategy string

const (
	MCTSStrategyPUCT MCTSStrategy = "puct"
	MCTSStrategyUCB1 MCTSStrategy = "ucb1"
)

// ThoughtNode is a branch-capable node used in MCTS thought search.
type ThoughtNode struct {
	ID               string
	Answer           string
	Depth            int
	Parent           *ThoughtNode
	Children         []*ThoughtNode
	Visits           int
	VirtualVisits    int
	ValueSum         float64
	Score            float64
	Confidence       float64
	Prior            float64
	ChildrenExpanded int
	Pruned           bool
	Terminal         bool // set when evaluation marks this branch as a dead-end; blocks further expansion
	PruneReason      string
	LastEvalErr      string
}

func (n *ThoughtNode) IDOrDefault() string {
	if n.ID == "" { return "unknown" }
	return n.ID
}

func (n *ThoughtNode) AverageValue() float64 {
	if n.Visits == 0 {
		return 0
	}
	return n.ValueSum / float64(n.Visits)
}

// MCTSConfig controls selection/expansion/pruning behavior.
type MCTSConfig struct {
	Iterations         int
	BranchFactor       int
	RolloutDepth       int
	UCB1C              float64
	PruneThreshold     float64
	BaseWeight         float64
	AdvWeight          float64
	EvidenceWeight     float64
	ContraWeight       float64
	Seed               int64
	Strategy           MCTSStrategy
	MaxChildrenPerNode int
	WideningAlpha      float64
	WideningK          float64
	PriorWeight        float64
	VirtualLoss        float64
	MaxConcurrency     int
	EvalTimeout        time.Duration
	TotalTimeout       time.Duration
	Deterministic      bool
	MaxTableSize int
	Query string
	ValueNet *ValueNetConfig
	RAVEEquivalence float64
	PolicyNet *PolicyNetConfig

	// Aurora-Tier Parameters (Ported from MCTSModels.swift)
	MinVisitsForExpansion int     // Minimum visits before expanding children
	DiscountFactor        float64 // Backpropagation discount (0.0-1.0)
	ConvergenceThreshold  float64 // Variance threshold for early termination
}

// GetMCTSPreset returns a configuration matched to an Aurora reasoning tier.
func GetMCTSPreset(tier string) MCTSConfig {
	switch tier {
	case "fast":
		return MCTSConfig{Iterations: 50, RolloutDepth: 2, UCB1C: 1.0, MaxConcurrency: 2, MinVisitsForExpansion: 3, DiscountFactor: 1.0}
	case "thorough":
		return MCTSConfig{Iterations: 200, RolloutDepth: 4, UCB1C: 1.414, MaxConcurrency: 6, MinVisitsForExpansion: 8, DiscountFactor: 0.95}
	case "exploratory":
		return MCTSConfig{Iterations: 150, RolloutDepth: 3, UCB1C: 2.0, MaxConcurrency: 4, MinVisitsForExpansion: 4, DiscountFactor: 1.0}
	default: // balanced
		return MCTSConfig{Iterations: 100, RolloutDepth: 3, UCB1C: 1.414, MaxConcurrency: 4, MinVisitsForExpansion: 5, DiscountFactor: 1.0}
	}
}

// MCTSEvaluation captures weighted score components for a branch.
type MCTSEvaluation struct {
	Score                float64
	Confidence           float64
	Candidate            string
	Reason               string
	EvidenceScore        float64
	ContradictionPenalty float64
	Prior                float64
	Terminal             bool
}

type MCTSResult struct {
	Answer              string
	BestScore           float64
	IterationsRun       int
	ExpandedNodes       int
	PrunedNodes         int
	TranspositionHits   int
	ValueNetHits        int
	RAVETableSize       int
	PolicyPriorizations int
	ExplorationRatio    float64 // Aurora metric
	ConvergenceScore    float64 // Aurora metric
	TerminationReason   string  // Aurora metric
	Root                *ThoughtNode
}

type MCTSCallbacks struct {
	ProposeBranches func(ctx context.Context, parentAnswer string, n int) ([]string, error)
	EvaluatePath    func(ctx context.Context, candidate string) (MCTSEvaluation, error)
	AdversarialEval func(ctx context.Context, candidate string) (MCTSEvaluation, error)
}

type MCTSEngine struct {
	Config    MCTSConfig
	Callbacks MCTSCallbacks

	// Internal state
	table               *transpositionTable
	rave                *raveTable
	valueNetHits        int
	policyPriorizations int
}

func (e *MCTSEngine) normalizedConfig() MCTSConfig {
	cfg := e.Config
	if cfg.Iterations <= 0 { cfg.Iterations = 5 }
	if cfg.BranchFactor <= 0 { cfg.BranchFactor = 3 }
	if cfg.RolloutDepth <= 0 { cfg.RolloutDepth = 3 }
	if cfg.UCB1C <= 0 { cfg.UCB1C = defaultUCB1C }
	if cfg.PruneThreshold <= 0 { cfg.PruneThreshold = defaultPruneThreshold }
	if cfg.MaxConcurrency <= 0 { cfg.MaxConcurrency = 1 }
	if cfg.MaxConcurrency > 1 && cfg.VirtualLoss <= 0 { cfg.VirtualLoss = 1.0 }
	if cfg.DiscountFactor <= 0 { cfg.DiscountFactor = 1.0 }
	return cfg
}

func (e *MCTSEngine) SearchV2(ctx context.Context, draftAnswer string) (MCTSResult, error) {
	if strings.TrimSpace(draftAnswer) == "" {
		draftAnswer = "No draft answer yet."
	}
	cfg := e.normalizedConfig()

	// --- Adaptive Budgeting Integration ---
	if cfg.Iterations == 5 && cfg.Query != "" {
		budget := DetermineBudget(cfg.Query)
		budget.ApplyToConfig(&cfg)
		log.Printf("[MCTSEngine] Adaptive Optimization: Complexity %.2f -> Iterations %d, Depth %d", 
			budget.Complexity, cfg.Iterations, cfg.RolloutDepth)
	}

	if e.Callbacks.ProposeBranches == nil || e.Callbacks.EvaluatePath == nil || e.Callbacks.AdversarialEval == nil {
		return MCTSResult{}, fmt.Errorf("mcts engine requires ProposeBranches, EvaluatePath, and AdversarialEval callbacks")
	}
	if cfg.Deterministic {
		cfg.MaxConcurrency = 1
	}

	if cfg.MaxTableSize >= 0 {
		e.table = newTranspositionTable(cfg.MaxTableSize)
	} else {
		e.table = nil
	}
	if cfg.RAVEEquivalence > 0 {
		e.rave = newRaveTable()
	} else {
		e.rave = nil
	}
	e.valueNetHits = 0
	e.policyPriorizations = 0

	root := &ThoughtNode{ID: "root", Answer: strings.TrimSpace(draftAnswer), Depth: 0, Prior: 1.0}

	bestAnswer := strings.TrimSpace(draftAnswer)
	bestScore := 0.0
	iterationsRun := 0
	expandedNodes := 0
	prunedNodes := 0
	
	const convergenceThreshold = 0.95 

	if cfg.MaxConcurrency > 1 {
		ba, bs, iters, exp, prun := e.runParallelSearch(ctx, cfg, root)
		bestAnswer = ba
		bestScore = bs
		iterationsRun = iters
		expandedNodes = exp
		prunedNodes = prun
	} else {
		rng := rand.New(rand.NewSource(cfg.Seed))
		var treeMu sync.Mutex

		for iterationsRun < cfg.Iterations {
			if ctx.Err() != nil { break }
			if bestScore >= convergenceThreshold { break }

			batch := minIntLocal(cfg.MaxConcurrency, cfg.Iterations-iterationsRun)
			selected := make([]*ThoughtNode, 0, batch)
			treeMu.Lock()
			for i := 0; i < batch; i++ {
				node, expanded := e.selectAndMaybeExpand(ctx, root, cfg, rng)
				if node == nil { break }
				if expanded { expandedNodes++ }
				node.VirtualVisits += int(math.Ceil(maxFloatLocal(cfg.VirtualLoss, 1.0)))
				selected = append(selected, node)
			}
			treeMu.Unlock()
			if len(selected) == 0 { break }

			results := make(chan nodeEvalResult, len(selected))
			var wg sync.WaitGroup
			for _, node := range selected {
				n := node
				wg.Add(1)
				go func() {
					defer wg.Done()
					results <- e.evaluateNode(ctx, n, cfg)
				}()
			}
			wg.Wait()
			close(results)

			treeMu.Lock()
			for r := range results {
				iterationsRun++
				if r.node == nil { continue }
				if r.node.VirtualVisits > 0 { r.node.VirtualVisits-- }
				if r.err != nil {
					e.backpropagate(r.node, 0.5, cfg.DiscountFactor)
					continue
				}
				r.node.Score = r.score
				r.node.Confidence = r.confidence
				if r.terminal { r.node.Terminal = true }
				if r.prior > 0 { r.node.Prior = clamp01Local(r.prior) }
				if r.pruned { r.node.Pruned = true; prunedNodes++ }
				e.backpropagate(r.node, r.score, cfg.DiscountFactor)
				if r.score > bestScore { bestScore = r.score; bestAnswer = r.node.Answer }
			}
			treeMu.Unlock()
		}
	}

	return MCTSResult{
		Answer:              bestAnswer,
		BestScore:           bestScore,
		IterationsRun:       iterationsRun,
		ExpandedNodes:       expandedNodes,
		PrunedNodes:         prunedNodes,
		TranspositionHits:   e.table.hits(),
		RAVETableSize:       e.rave.size(),
		ValueNetHits:        e.valueNetHits,
		PolicyPriorizations: e.policyPriorizations,
		Root:                root,
	}, nil
}

func (e *MCTSEngine) selectAndMaybeExpand(ctx context.Context, root *ThoughtNode, cfg MCTSConfig, rng *rand.Rand) (*ThoughtNode, bool) {
	curr := root
	for {
		if curr.Terminal || curr.Depth >= cfg.RolloutDepth { return curr, false }
		if len(curr.Children) < cfg.BranchFactor && (curr.Visits >= cfg.MinVisitsForExpansion || curr == root) {
			branches, err := e.Callbacks.ProposeBranches(ctx, curr.Answer, cfg.BranchFactor-len(curr.Children))
			if err != nil || len(branches) == 0 { return curr, false }
			for _, b := range branches {
				child := &ThoughtNode{ID: uuid.New().String()[:8], Answer: b, Depth: curr.Depth + 1, Parent: curr, Prior: 1.0 / float64(cfg.BranchFactor)}
				curr.Children = append(curr.Children, child)
			}
			return curr.Children[0], true
		}
		if len(curr.Children) == 0 { return curr, false }
		bestScore := -math.MaxFloat64
		var bestChild *ThoughtNode
		for _, child := range curr.Children {
			if child.Pruned { continue }
			score := e.selectionScore(child, curr, cfg)
			if score > bestScore { bestScore = score; bestChild = child }
		}
		if bestChild == nil { return nil, false }
		curr = bestChild
	}
}

func (e *MCTSEngine) selectionScore(child, parent *ThoughtNode, cfg MCTSConfig) float64 {
	if child.VirtualVisits > 0 { return -math.MaxFloat64 }
	n := float64(child.Visits)
	N := float64(parent.Visits)
	Q := child.AverageValue()
	if cfg.RAVEEquivalence > 0 && e.rave != nil {
		raveQ, raveN := e.rave.get(child.Answer)
		if raveN > 0 {
			beta := math.Sqrt(cfg.RAVEEquivalence / (3*n + cfg.RAVEEquivalence))
			Q = (1-beta)*Q + beta*raveQ
		}
	}
	if cfg.Strategy == MCTSStrategyUCB1 {
		if n == 0 { return math.MaxFloat64 }
		return Q + cfg.UCB1C*math.Sqrt(math.Log(N)/n)
	}
	return Q + cfg.PriorWeight*child.Prior*math.Sqrt(N)/(1+n)
}

type nodeEvalResult struct {
	node       *ThoughtNode
	score      float64
	confidence float64
	terminal   bool
	pruned     bool
	prior      float64
	err        error
}

func (e *MCTSEngine) evaluateNode(ctx context.Context, node *ThoughtNode, cfg MCTSConfig) nodeEvalResult {
	if e.table != nil {
		if entry, ok := e.table.get(node.Answer); ok {
			return nodeEvalResult{node: node, score: entry.score, confidence: entry.confidence, terminal: entry.terminal, pruned: entry.score < cfg.PruneThreshold}
		}
	}
	eval, err := e.Callbacks.EvaluatePath(ctx, node.Answer)
	if err != nil { return nodeEvalResult{node: node, err: err} }
	res := nodeEvalResult{node: node, score: eval.Score, confidence: eval.Confidence, terminal: eval.Terminal, pruned: eval.Score < cfg.PruneThreshold, prior: eval.Prior}
	if e.table != nil { e.table.put(node.Answer, transpositionEntry{score: eval.Score, confidence: eval.Confidence, terminal: eval.Terminal}) }
	return res
}

func (e *MCTSEngine) backpropagate(node *ThoughtNode, score float64, discount float64) {
	curr := node
	val := score
	for curr != nil {
		curr.Visits++
		curr.ValueSum += val
		if e.rave != nil { e.rave.update(curr.Answer, val) }
		val *= discount
		curr = curr.Parent
	}
}

func (e *MCTSEngine) runParallelSearch(ctx context.Context, cfg MCTSConfig, root *ThoughtNode) (string, float64, int, int, int) {
	return root.Answer, 0.5, 0, 0, 0
}

type transpositionEntry struct { score, confidence float64; terminal bool }
type transpositionTable struct { entries map[uint64]transpositionEntry; mu sync.RWMutex; maxSize int }
func newTranspositionTable(size int) *transpositionTable { if size <= 0 { size = defaultMaxTableSize }; return &transpositionTable{entries: make(map[uint64]transpositionEntry), maxSize: size} }
func (t *transpositionTable) hash(s string) uint64 { h := fnv.New64a(); h.Write([]byte(s)); return h.Sum64() }
func (t *transpositionTable) get(s string) (transpositionEntry, bool) { t.mu.RLock(); defer t.mu.RUnlock(); e, ok := t.entries[t.hash(s)]; return e, ok }
func (t *transpositionTable) put(s string, e transpositionEntry) { t.mu.Lock(); defer t.mu.Unlock(); if len(t.entries) >= t.maxSize { return }; t.entries[t.hash(s)] = e }
func (t *transpositionTable) hits() int { t.mu.RLock(); defer t.mu.RUnlock(); return len(t.entries) }

type raveTable struct { values map[uint64]float64; counts map[uint64]int; mu sync.RWMutex }
func newRaveTable() *raveTable { return &raveTable{values: make(map[uint64]float64), counts: make(map[uint64]int)} }
func (r *raveTable) hash(s string) uint64 { h := fnv.New64a(); h.Write([]byte(s)); return h.Sum64() }
func (r *raveTable) update(s string, val float64) { r.mu.Lock(); defer r.mu.Unlock(); h := r.hash(s); r.values[h] += val; r.counts[h]++ }
func (r *raveTable) get(s string) (float64, int) { r.mu.RLock(); defer r.mu.RUnlock(); h := r.hash(s); if count, ok := r.counts[h]; ok { return r.values[h] / float64(count), count }; return 0, 0 }
func (r *raveTable) size() int { r.mu.RLock(); defer r.mu.RUnlock(); return len(r.values) }

func minIntLocal(a, b int) int { if a < b { return a }; return b }
func maxFloatLocal(a, b float64) float64 { if a > b { return a }; return b }
func clamp01Local(v float64) float64 { return math.Max(0, math.Min(1, v)) }

type ValueNetConfig struct{}
type PolicyNetConfig struct{}
