package cognition

import (
	"hash/fnv"
	"math"
	"strings"
	"sync"
)

// raveEntry holds the cumulative score for an answer text seen anywhere
// in the search tree during a single SearchV2 call.
type raveEntry struct {
	Visits   int
	ValueSum float64
}

// raveTable is a global RAVE (Rapid Action Value Estimation) table.
//
// Every time an answer text is evaluated and backpropagated, its score is
// recorded here regardless of tree position. When a new node with the same
// (or previously seen) answer text is selected, its cold-start Q estimate is
// seeded from the RAVE average instead of 0.
//
// The table is reset at the start of every SearchV2 call.
type raveTable struct {
	mu      sync.Mutex
	entries map[uint64]raveEntry
}

func newRaveTable() *raveTable {
	return &raveTable{entries: make(map[uint64]raveEntry, 64)}
}

func (r *raveTable) key(answer string) uint64 {
	h := fnv.New64a()
	_, _ = h.Write([]byte(strings.ToLower(strings.TrimSpace(answer))))
	return h.Sum64()
}

// update records that the given answer text received the given score in a rollout.
func (r *raveTable) update(answer string, score float64) {
	k := r.key(answer)
	r.mu.Lock()
	e := r.entries[k]
	e.Visits++
	e.ValueSum += score
	r.entries[k] = e
	r.mu.Unlock()
}

// estimate returns the RAVE average value for the answer text, if any rollout
// has recorded it. Returns (0, false) when no data exists.
func (r *raveTable) estimate(answer string) (float64, bool) {
	k := r.key(answer)
	r.mu.Lock()
	e, ok := r.entries[k]
	r.mu.Unlock()
	if !ok || e.Visits == 0 {
		return 0, false
	}
	return e.ValueSum / float64(e.Visits), true
}

// size returns the number of unique answer texts recorded.
func (r *raveTable) size() int {
	r.mu.Lock()
	n := len(r.entries)
	r.mu.Unlock()
	return n
}

// raveBlend returns β — the weight to give the RAVE estimate when blending
// with the standard MCTS Q value.
//
//	β = sqrt(k / (3·N + k))
//
// At N=0:   β = 1.0 → trust RAVE fully (cold start)
// At N=k/3: β ≈ 0.5 → equal blend
// As N→∞:   β → 0   → trust real visits only
//
// k is RAVEEquivalence from MCTSConfig (default 300). Higher k keeps RAVE
// influence longer; lower k lets real data take over faster.
func raveBlend(nodeVisits int, k float64) float64 {
	if k <= 0 || nodeVisits < 0 {
		return 0
	}
	return math.Sqrt(k / (3*float64(nodeVisits) + k))
}
