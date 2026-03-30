// SPP Phase 5, Track 2 — Fragment Vote Log + Universal Truth Promotion
//
// FragmentVoteLog tracks how many independent nodes have emitted a KnowledgeFragment
// on the same subject. When a subject reaches UniversalThreshold (default 3) distinct
// NodeIDs, it qualifies as a "Universal Truth" and is promoted to maximum importance
// in the PocketBase knowledge_fragments collection — giving it priority in all RAG
// retrieval queries.
//
// This is entirely passive — no new network calls. It runs on fragments already
// arriving via SPP-3 Fragment trading. The DreamDaemon calls SweepPromotion()
// during idle consolidation cycles to batch-promote qualifying subjects.
//
// Env vars:
//
//	ORICLI_SWARM_UNIVERSAL_THRESHOLD — distinct node votes required (default 3)
package swarm

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"log"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)

// universalImportance is the importance score written to PB when promoting a fragment.
// Set to 1.0 — the maximum — so universal truths always sort first in RAG queries.
const universalImportance = 1.0

// universalAuthor tags promoted fragments so they can be identified.
const universalAuthor = "swarm:universal"

// UniversalThreshold returns the configured vote count required for promotion.
func UniversalThreshold() int {
	if v := os.Getenv("ORICLI_SWARM_UNIVERSAL_THRESHOLD"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			return n
		}
	}
	return 3
}

// VoteEntry tracks which distinct nodes have attested to a subject.
type VoteEntry struct {
	SubjectHash string
	Subject     string    // canonical subject label (first seen)
	Voters      map[string]time.Time // NodeID → vote timestamp
	Promoted    bool
	PromotedAt  time.Time
}

// FragmentPromoter is the interface for promoting a subject to universal tier.
// Implemented by MemoryBank in P5-4 wiring.
type FragmentPromoter interface {
	PromoteToUniversal(ctx context.Context, subject string) error
}

// FragmentVoteLog records per-subject vote counts and triggers Universal Truth promotion.
type FragmentVoteLog struct {
	entries   map[string]*VoteEntry // keyed by SubjectHash
	mu        sync.RWMutex
	promoter  FragmentPromoter // nil until wired in P5-4
	threshold int
}

// NewFragmentVoteLog creates a FragmentVoteLog.
// promoter may be nil — promotion is silently skipped until wired.
func NewFragmentVoteLog(promoter FragmentPromoter) *FragmentVoteLog {
	return &FragmentVoteLog{
		entries:   make(map[string]*VoteEntry),
		promoter:  promoter,
		threshold: UniversalThreshold(),
	}
}

// SetPromoter injects the MemoryBank promoter after construction.
func (v *FragmentVoteLog) SetPromoter(p FragmentPromoter) {
	v.mu.Lock()
	v.promoter = p
	v.mu.Unlock()
}

// Record registers a new vote from the fragment's issuing node.
// Returns true if this vote crosses the UniversalThreshold (promotion queued).
func (v *FragmentVoteLog) Record(f *KnowledgeFragment) bool {
	if f == nil || f.Subject == "" || f.NodeID == "" {
		return false
	}
	h := subjectHash(f.Subject)

	v.mu.Lock()
	entry, ok := v.entries[h]
	if !ok {
		entry = &VoteEntry{
			SubjectHash: h,
			Subject:     canonicalSubject(f.Subject),
			Voters:      make(map[string]time.Time),
		}
		v.entries[h] = entry
	}
	entry.Voters[f.NodeID] = time.Now().UTC()
	crossedThreshold := !entry.Promoted && len(entry.Voters) >= v.threshold
	v.mu.Unlock()

	return crossedThreshold
}

// SweepPromotion iterates all entries that have crossed the threshold but not yet
// been promoted, and calls the FragmentPromoter for each. Call from DreamDaemon.
func (v *FragmentVoteLog) SweepPromotion(ctx context.Context) {
	v.mu.RLock()
	var toPromote []*VoteEntry
	for _, e := range v.entries {
		if !e.Promoted && len(e.Voters) >= v.threshold {
			toPromote = append(toPromote, e)
		}
	}
	v.mu.RUnlock()

	if len(toPromote) == 0 {
		return
	}
	log.Printf("[consensus] promoting %d subjects to universal tier", len(toPromote))

	for _, e := range toPromote {
		if v.promoter == nil {
			break
		}
		if err := v.promoter.PromoteToUniversal(ctx, e.Subject); err != nil {
			log.Printf("[consensus] promote %q: %v", e.Subject, err)
			continue
		}
		v.mu.Lock()
		e.Promoted = true
		e.PromotedAt = time.Now().UTC()
		v.mu.Unlock()
		log.Printf("[consensus] universal truth promoted: %q (%d voters)", e.Subject, len(e.Voters))
	}
}

// Snapshot returns all vote entries for the /v1/swarm/consensus/fragments endpoint.
func (v *FragmentVoteLog) Snapshot() []VoteEntry {
	v.mu.RLock()
	defer v.mu.RUnlock()
	out := make([]VoteEntry, 0, len(v.entries))
	for _, e := range v.entries {
		cp := VoteEntry{
			SubjectHash: e.SubjectHash,
			Subject:     e.Subject,
			Voters:      make(map[string]time.Time, len(e.Voters)),
			Promoted:    e.Promoted,
			PromotedAt:  e.PromotedAt,
		}
		for k, t := range e.Voters {
			cp.Voters[k] = t
		}
		out = append(out, cp)
	}
	return out
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func subjectHash(subject string) string {
	h := sha256.Sum256([]byte(canonicalSubject(subject)))
	return hex.EncodeToString(h[:])
}

func canonicalSubject(s string) string {
	return strings.ToLower(strings.TrimSpace(s))
}
