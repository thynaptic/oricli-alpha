// SPP Phase 5, Track 3 — Epistemic Skill Inheritance (ESI)
//
// ESI enables nodes to share high-quality reasoning traces with peers — without
// LoRA, without model mutation, and without raw user data ever leaving the node.
//
// Instead of fine-tuning weights, receiving nodes ingest peer skill traces into
// their RAG context. For procedural tasks (code patterns, refactoring, debugging)
// this achieves equivalent lift to LoRA with full reversibility.
//
// Two mechanisms:
//  1. PeerSkillTrace — anonymised reasoning trace broadcast after high-quality tasks
//  2. SkillManifest  — compact .ori expert system-prompt section shared across swarm
//
// Opt-in: ORICLI_SWARM_LESSON_SHARE=true required for any outbound broadcast.
// Quality gate: QualityScore > 0.85 before broadcast.
//
// Env vars:
//
//	ORICLI_SWARM_LESSON_SHARE — "true" to enable outbound skill trace broadcasts
package swarm

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"log"
	"os"
	"regexp"
	"strings"
	"sync"
	"time"
)

// EnvType constants for ESI — add alongside marketplace constants.
const (
	EnvTypeSkillTrace    = "skill_trace"
	EnvTypeSkillManifest = "skill_manifest"
)

// MinQualityScore is the minimum quality score required before a trace is broadcast.
const MinQualityScore = 0.85

// ---------------------------------------------------------------------------
// PeerSkillTrace
// ---------------------------------------------------------------------------

// PeerSkillTrace is the atomic unit of Epistemic Skill Inheritance.
// Raw source text, session IDs, and user context are never included.
type PeerSkillTrace struct {
	ID             string    `json:"id"`              // SHA-256 of (Skill+NodeID+IssuedAt)
	Skill          string    `json:"skill"`           // e.g. "python_refactor", "go_engineer"
	ReasoningTrace string    `json:"reasoning_trace"` // scrubbed reasoning pattern
	QualityScore   float64   `json:"quality_score"`
	NodeID         string    `json:"node_id"`
	IssuedAt       time.Time `json:"issued_at"`
	Signature      []byte    `json:"signature"`
}

// SkillManifest is a compact expert system-prompt addendum for a named skill.
// Loadable via X-ORI-Manifest: peer:<node_short_id>:<skill>
type SkillManifest struct {
	Skill         string    `json:"skill"`
	SystemAddendum string   `json:"system_addendum"` // expert prompt section only
	NodeID        string    `json:"node_id"`
	IssuedAt      time.Time `json:"issued_at"`
	Signature     []byte    `json:"signature"`
}

// ---------------------------------------------------------------------------
// Scrub pipeline
// ---------------------------------------------------------------------------

var scrubPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)session[_-]?id\s*[:=]\s*\S+`),
	regexp.MustCompile(`(?i)user[_-]?id\s*[:=]\s*\S+`),
	regexp.MustCompile(`(?i)api[_-]?key\s*[:=]\s*\S+`),
	regexp.MustCompile(`\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b`), // email
	regexp.MustCompile(`\b(?:\d{1,3}\.){3}\d{1,3}\b`),                           // IPv4
	regexp.MustCompile(`/(?:home|root|Users|var|etc|tmp)/[^\s"']+`),              // file paths
	regexp.MustCompile(`(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*`),                    // bearer tokens
	regexp.MustCompile(`glm\.[A-Za-z0-9]+\.[A-Za-z0-9\-_]+`),                    // seed key pattern
}

// ScrubTrace removes all identifiable user/session/path data from a reasoning trace.
// The scrubbed output retains structural reasoning and code patterns.
func ScrubTrace(raw string) string {
	result := raw
	for _, re := range scrubPatterns {
		result = re.ReplaceAllString(result, "[REDACTED]")
	}
	return strings.TrimSpace(result)
}

// ---------------------------------------------------------------------------
// ESI Federation
// ---------------------------------------------------------------------------

// SkillTraceIngester persists incoming peer skill traces into local RAG storage.
// Uses plain function signatures to avoid import cycles with pkg/service.
type SkillTraceIngester interface {
	StoreSkillTrace(ctx context.Context, skill, reasoning string, quality float64, nodeID string) error
	PurgeSkillTraces(ctx context.Context, nodeID string) error
}

// SkillManifestCache caches incoming peer skill manifests for X-ORI-Manifest loading.
// Implemented by SkillManager in P5-4 wiring.
type SkillManifestCache interface {
	CachePeerManifest(skill, nodeShortID, systemAddendum string)
	GetPeerManifest(skill, nodeShortID string) (string, bool)
}

// ESIFederation manages Epistemic Skill Inheritance across the swarm.
type ESIFederation struct {
	identity  *NodeIdentity
	registry  *PeerRegistry
	ingester  SkillTraceIngester  // nil until wired
	manifests SkillManifestCache  // nil until wired

	// cache of locally broadcasted trace IDs to avoid re-broadcast
	sentTraces map[string]time.Time
	mu         sync.Mutex
}

// NewESIFederation creates an ESIFederation.
func NewESIFederation(identity *NodeIdentity, registry *PeerRegistry) *ESIFederation {
	return &ESIFederation{
		identity:   identity,
		registry:   registry,
		sentTraces: make(map[string]time.Time),
	}
}

// SetIngester injects the SkillTraceIngester after construction.
func (e *ESIFederation) SetIngester(i SkillTraceIngester) {
	e.mu.Lock()
	e.ingester = i
	e.mu.Unlock()
}

// SetManifestCache injects the SkillManifestCache after construction.
func (e *ESIFederation) SetManifestCache(c SkillManifestCache) {
	e.mu.Lock()
	e.manifests = c
	e.mu.Unlock()
}

// MaybeShareTrace checks the quality gate and opt-in flag, then broadcasts
// a scrubbed skill trace to all swarm peers.
// Call from LearningSystem after record_lesson in P5-4 wiring.
func (e *ESIFederation) MaybeShareTrace(ctx context.Context, skill, rawTrace string, qualityScore float64) {
	if os.Getenv("ORICLI_SWARM_LESSON_SHARE") != "true" {
		return
	}
	if qualityScore < MinQualityScore {
		return
	}
	if e.registry == nil || len(e.registry.ConnectedPeers()) == 0 {
		return
	}

	scrubbed := ScrubTrace(rawTrace)
	if len(scrubbed) < 20 {
		return // nothing useful left after scrubbing
	}

	now := time.Now().UTC()
	trace := PeerSkillTrace{
		Skill:          skill,
		ReasoningTrace: scrubbed,
		QualityScore:   qualityScore,
		NodeID:         e.identity.NodeID,
		IssuedAt:       now,
	}
	h := sha256.Sum256([]byte(skill + e.identity.NodeID + now.String()))
	trace.ID = hex.EncodeToString(h[:])
	trace.Signature = e.identity.Sign(e.tracePayload(trace))

	e.mu.Lock()
	if _, sent := e.sentTraces[trace.ID]; sent {
		e.mu.Unlock()
		return
	}
	e.sentTraces[trace.ID] = now
	e.mu.Unlock()

	data, _ := json.Marshal(trace)
	e.registry.Broadcast(SwarmEnvelope{
		Type:    EnvTypeSkillTrace,
		From:    e.identity.NodeID,
		Payload: data,
	})
	log.Printf("[esi] broadcast skill trace: skill=%s quality=%.2f", skill, qualityScore)
}

// BroadcastManifest shares a SkillManifest with all connected peers.
// systemAddendum is the expert system-prompt section (not the full .ori file).
func (e *ESIFederation) BroadcastManifest(skill, systemAddendum string) {
	if os.Getenv("ORICLI_SWARM_LESSON_SHARE") != "true" {
		return
	}
	manifest := SkillManifest{
		Skill:          skill,
		SystemAddendum: systemAddendum,
		NodeID:         e.identity.NodeID,
		IssuedAt:       time.Now().UTC(),
	}
	manifest.Signature = e.identity.Sign(e.manifestPayload(manifest))

	data, _ := json.Marshal(manifest)
	e.registry.Broadcast(SwarmEnvelope{
		Type:    EnvTypeSkillManifest,
		From:    e.identity.NodeID,
		Payload: data,
	})
}

// HandleSkillTrace processes an inbound PeerSkillTrace from a peer.
func (e *ESIFederation) HandleSkillTrace(ctx context.Context, peer *PeerConn, env SwarmEnvelope) {
	var trace PeerSkillTrace
	if ok, err := env.UnmarshalPayload(&trace); !ok || err != nil {
		return
	}
	if trace.QualityScore < MinQualityScore {
		log.Printf("[esi] dropping low-quality trace from %s (%.2f)", peer.ShortID, trace.QualityScore)
		return
	}

	e.mu.Lock()
	ing := e.ingester
	e.mu.Unlock()

	if ing == nil {
		return
	}
	if err := ing.StoreSkillTrace(ctx, trace.Skill, trace.ReasoningTrace, trace.QualityScore, trace.NodeID); err != nil {
		log.Printf("[esi] store trace from %s: %v", peer.ShortID, err)
	}
}

// HandleSkillManifest processes an inbound SkillManifest from a peer.
func (e *ESIFederation) HandleSkillManifest(peer *PeerConn, env SwarmEnvelope) {
	var manifest SkillManifest
	if ok, err := env.UnmarshalPayload(&manifest); !ok || err != nil {
		return
	}

	e.mu.Lock()
	cache := e.manifests
	e.mu.Unlock()

	if cache == nil {
		return
	}
	shortID := manifest.NodeID
	if len(shortID) > 16 {
		shortID = shortID[:16]
	}
	cache.CachePeerManifest(manifest.Skill, shortID, manifest.SystemAddendum)
	log.Printf("[esi] cached skill manifest from %s: skill=%s", peer.ShortID, manifest.Skill)
}

// PurgeNodeTraces removes all skill traces from a specific peer node.
// Called from DELETE /v1/swarm/skills/traces/:node_id admin endpoint.
func (e *ESIFederation) PurgeNodeTraces(ctx context.Context, nodeID string) error {
	e.mu.Lock()
	ing := e.ingester
	e.mu.Unlock()
	if ing == nil {
		return nil
	}
	return ing.PurgeSkillTraces(ctx, nodeID)
}

// ---------------------------------------------------------------------------
// Signature helpers
// ---------------------------------------------------------------------------

func (e *ESIFederation) tracePayload(t PeerSkillTrace) []byte {
	type sp struct {
		Skill        string    `json:"skill"`
		QualityScore float64   `json:"quality_score"`
		NodeID       string    `json:"node_id"`
		IssuedAt     time.Time `json:"issued_at"`
	}
	b, _ := json.Marshal(sp{t.Skill, t.QualityScore, t.NodeID, t.IssuedAt})
	return b
}

func (e *ESIFederation) manifestPayload(m SkillManifest) []byte {
	type sp struct {
		Skill    string    `json:"skill"`
		NodeID   string    `json:"node_id"`
		IssuedAt time.Time `json:"issued_at"`
	}
	b, _ := json.Marshal(sp{m.Skill, m.NodeID, m.IssuedAt})
	return b
}
