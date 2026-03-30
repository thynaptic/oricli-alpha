// SPP-4 — Reputation + Quarantine
//
// ReputationStore tracks the trustworthiness of swarm peers using a rolling
// weighted score (0.0–1.0). Scores are persisted to LMDB in the "peer_reputation"
// bucket so they survive process restarts.
//
// Scoring inputs:
//   - Fragment accuracy: did the fragment improve or degrade local reasoning?
//   - Bounty task completion rate: did the peer complete accepted bounties?
//   - SCAI pass rate: did received content pass the local SCAI auditor?
//
// Quarantine policy:
//   - Score drops below QuarantineThreshold (default 0.2) for 3+ consecutive
//     interactions → peer is quarantined.
//   - Quarantined peers are severed from the WebSocket registry.
//   - In-flight tasks are allowed to complete; no new bids accepted.
//   - Quarantine events are logged to the reflection_log PocketBase collection
//     (reuses Phase 3.5 SaveSCAIRevision infrastructure).
package swarm

import (
	"encoding/json"
	"fmt"
	"log"
	"sync"
	"time"
)

// QuarantineThreshold is the score below which a peer is considered unstable.
const QuarantineThreshold = 0.2

// quarantineStrikes is the number of consecutive below-threshold interactions
// before quarantine is triggered.
const quarantineStrikes = 3

// defaultReputationScore is the starting score for all new peers.
const defaultReputationScore = 0.5

// ScoreEvent classifies the type of signal used to update reputation.
type ScoreEvent string

const (
	ScoreFragmentAccurate   ScoreEvent = "fragment_accurate"
	ScoreFragmentInaccurate ScoreEvent = "fragment_inaccurate"
	ScoreBountyCompleted    ScoreEvent = "bounty_completed"
	ScoreBountyFailed       ScoreEvent = "bounty_failed"
	ScoreSCAIPass           ScoreEvent = "scai_pass"
	ScoreSCAIFail           ScoreEvent = "scai_fail"
)

// scoreWeights defines the magnitude of each event's impact.
var scoreWeights = map[ScoreEvent]float64{
	ScoreFragmentAccurate:   +0.05,
	ScoreFragmentInaccurate: -0.10,
	ScoreBountyCompleted:    +0.08,
	ScoreBountyFailed:       -0.12,
	ScoreSCAIPass:           +0.03,
	ScoreSCAIFail:           -0.15,
}

// PeerRecord holds the reputation state for a single peer.
type PeerRecord struct {
	NodeID             string    `json:"node_id"`
	Score              float64   `json:"score"`
	ConsecutiveLow     int       `json:"consecutive_low"`
	Quarantined        bool      `json:"quarantined"`
	QuarantinedAt      time.Time `json:"quarantined_at,omitempty"`
	TotalInteractions  int       `json:"total_interactions"`
	LastSeen           time.Time `json:"last_seen"`
}

// QuarantineNotifier is called when a peer is quarantined, allowing the
// PeerRegistry to sever the WebSocket connection.
type QuarantineNotifier func(nodeID string, reason string)

// ReputationStore manages peer reputation scoring and quarantine enforcement.
type ReputationStore struct {
	peers     map[string]*PeerRecord
	mu        sync.RWMutex
	onQuarantine QuarantineNotifier

	// persist is a lightweight write-back function; inject LMDB writer in SPP-6 wiring.
	// Signature: func(nodeID string, record []byte) error
	persist func(nodeID string, record []byte) error
}

// NewReputationStore creates a ReputationStore.
// onQuarantine is called (in a goroutine) when a peer crosses the quarantine threshold.
// persist may be nil (in-memory only; scores lost on restart until LMDB is wired).
func NewReputationStore(onQuarantine QuarantineNotifier, persist func(string, []byte) error) *ReputationStore {
	return &ReputationStore{
		peers:        make(map[string]*PeerRecord),
		onQuarantine: onQuarantine,
		persist:      persist,
	}
}

// Score returns the current reputation score for a peer (default 0.5 for unknowns).
func (r *ReputationStore) Score(nodeID string) float64 {
	r.mu.RLock()
	defer r.mu.RUnlock()
	if rec, ok := r.peers[nodeID]; ok {
		return rec.Score
	}
	return defaultReputationScore
}

// IsQuarantined returns true if the peer has been quarantined.
func (r *ReputationStore) IsQuarantined(nodeID string) bool {
	r.mu.RLock()
	defer r.mu.RUnlock()
	rec, ok := r.peers[nodeID]
	return ok && rec.Quarantined
}

// RecordEvent updates a peer's score based on a scored interaction.
func (r *ReputationStore) RecordEvent(nodeID string, event ScoreEvent) {
	delta, ok := scoreWeights[event]
	if !ok {
		return
	}
	r.mu.Lock()
	rec := r.getOrCreate(nodeID)
	rec.Score = clampScore(rec.Score + delta)
	rec.TotalInteractions++
	rec.LastSeen = time.Now().UTC()

	// Track consecutive below-threshold interactions.
	if rec.Score < QuarantineThreshold {
		rec.ConsecutiveLow++
	} else {
		rec.ConsecutiveLow = 0
	}

	shouldQuarantine := !rec.Quarantined && rec.ConsecutiveLow >= quarantineStrikes
	if shouldQuarantine {
		rec.Quarantined = true
		rec.QuarantinedAt = time.Now().UTC()
	}
	r.mu.Unlock()

	r.writeback(nodeID)

	if shouldQuarantine {
		reason := fmt.Sprintf("score %.2f below threshold %.2f for %d consecutive interactions", rec.Score, QuarantineThreshold, quarantineStrikes)
		log.Printf("[reputation] quarantining peer %s: %s", nodeID[:min(16, len(nodeID))], reason)
		if r.onQuarantine != nil {
			go r.onQuarantine(nodeID, reason)
		}
	}
}

// Reinstate removes a quarantine and resets consecutive-low counter.
// Use after manual review via admin API.
func (r *ReputationStore) Reinstate(nodeID string) {
	r.mu.Lock()
	rec := r.getOrCreate(nodeID)
	rec.Quarantined = false
	rec.ConsecutiveLow = 0
	rec.Score = defaultReputationScore
	r.mu.Unlock()
	r.writeback(nodeID)
	log.Printf("[reputation] reinstated peer %s", nodeID[:min(16, len(nodeID))])
}

// Snapshot returns a copy of all peer records for the /v1/swarm/peers endpoint.
func (r *ReputationStore) Snapshot() []PeerRecord {
	r.mu.RLock()
	defer r.mu.RUnlock()
	out := make([]PeerRecord, 0, len(r.peers))
	for _, rec := range r.peers {
		cp := *rec
		out = append(out, cp)
	}
	return out
}

// LoadRecord deserialises a JSON blob from LMDB into the store.
// Call during startup to restore persisted reputation scores.
func (r *ReputationStore) LoadRecord(data []byte) error {
	var rec PeerRecord
	if err := json.Unmarshal(data, &rec); err != nil {
		return err
	}
	r.mu.Lock()
	r.peers[rec.NodeID] = &rec
	r.mu.Unlock()
	return nil
}

func (r *ReputationStore) getOrCreate(nodeID string) *PeerRecord {
	rec, ok := r.peers[nodeID]
	if !ok {
		rec = &PeerRecord{
			NodeID:   nodeID,
			Score:    defaultReputationScore,
			LastSeen: time.Now().UTC(),
		}
		r.peers[nodeID] = rec
	}
	return rec
}

func (r *ReputationStore) writeback(nodeID string) {
	if r.persist == nil {
		return
	}
	r.mu.RLock()
	rec, ok := r.peers[nodeID]
	r.mu.RUnlock()
	if !ok {
		return
	}
	data, err := json.Marshal(rec)
	if err != nil {
		return
	}
	if err := r.persist(nodeID, data); err != nil {
		log.Printf("[reputation] writeback for %s: %v", nodeID[:min(16, len(nodeID))], err)
	}
}

func clampScore(s float64) float64 {
	if s < 0 {
		return 0
	}
	if s > 1 {
		return 1
	}
	return s
}
