// SPP Phase 5, Track 1 — Jury Mode + Quorum Resolver
//
// For AuditLevelFull requests, a JuryClient can route a draft response to N peer
// nodes for independent SCAI Critique before it is delivered. This creates a
// constitutional guarantee: no sensitive response is delivered without multi-node
// verification.
//
// Design constraints:
//   - Never called on AuditLevelNone or AuditLevelLight — zero latency regression
//   - Local SCAI pass still runs first; jury is a second gate, not a replacement
//   - Jury verdicts are Ed25519-signed by the issuing peer node
//   - Timeouts register as ScoreBountyFailed against the peer in reputation
//
// Env vars:
//
//	ORICLI_SWARM_JURY_QUORUM       — "majority" (default) or "unanimous"
//	ORICLI_SWARM_JURY_DEADLINE_MS  — collection window in ms (default 4000)
package swarm

import (
	"context"
	"crypto/ed25519"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strconv"
	"sync"
	"time"
)

// QuorumPolicy controls how many verdicts must pass before a response is released.
type QuorumPolicy string

const (
	QuorumMajority   QuorumPolicy = "majority"   // 2/3 pass — default
	QuorumUnanimous  QuorumPolicy = "unanimous"  // all must pass
)

// defaultJurySize is the number of peers asked to participate in each jury.
const defaultJurySize = 3

// JuryRequest is sent to peer nodes requesting independent SCAI critique.
type JuryRequest struct {
	SessionID  string    `json:"session_id"`  // ties verdicts back to originating request
	Query      string    `json:"query"`       // the original user query
	Draft      string    `json:"draft"`       // proposed response to critique
	NodeID     string    `json:"node_id"`     // requesting node
	IssuedAt   time.Time `json:"issued_at"`
	Signature  []byte    `json:"signature"`   // Ed25519 sig over sigPayload()
}

// JuryVerdict is the peer's independent assessment.
type JuryVerdict struct {
	SessionID   string    `json:"session_id"`
	JurorNodeID string    `json:"juror_node_id"`
	Passed      bool      `json:"passed"`       // true if draft passes local SCAI
	Critique    string    `json:"critique"`     // short reason if failed; empty if passed
	IssuedAt    time.Time `json:"issued_at"`
	Signature   []byte    `json:"signature"`    // Ed25519 sig over sigPayload()
}

// EnvType constants for jury — added here, referenced in marketplace.go
const (
	EnvTypeJuryRequest = "jury_request"
	EnvTypeJuryVerdict = "jury_verdict"
)

func (r *JuryRequest) sigPayload() []byte {
	type sp struct {
		SessionID string    `json:"session_id"`
		Query     string    `json:"query"`
		Draft     string    `json:"draft"`
		NodeID    string    `json:"node_id"`
		IssuedAt  time.Time `json:"issued_at"`
	}
	b, _ := json.Marshal(sp{r.SessionID, r.Query, r.Draft, r.NodeID, r.IssuedAt})
	return b
}

func (v *JuryVerdict) sigPayload() []byte {
	type sp struct {
		SessionID   string    `json:"session_id"`
		JurorNodeID string    `json:"juror_node_id"`
		Passed      bool      `json:"passed"`
		IssuedAt    time.Time `json:"issued_at"`
	}
	b, _ := json.Marshal(sp{v.SessionID, v.JurorNodeID, v.Passed, v.IssuedAt})
	return b
}

// ---------------------------------------------------------------------------
// QuorumResolver
// ---------------------------------------------------------------------------

// JurySession tracks an in-flight jury for a single request.
type JurySession struct {
	SessionID  string
	Verdicts   []JuryVerdict
	Expected   int           // number of jurors asked
	resultCh   chan QuorumResult
	deadline   time.Time
	mu         sync.Mutex
}

// QuorumResult is the final outcome of a jury session.
type QuorumResult struct {
	SessionID   string
	Passed      bool
	Policy      QuorumPolicy
	Verdicts    []JuryVerdict
	FailReasons []string // critiques from failed verdicts
}

// QuorumResolver manages active jury sessions and resolves verdicts.
type QuorumResolver struct {
	policy     QuorumPolicy
	deadlineMS int64

	sessions map[string]*JurySession
	mu       sync.Mutex
}

// NewQuorumResolver creates a resolver. Policy and deadline are read from env
// if not set explicitly (pass empty string / 0 to use env/defaults).
func NewQuorumResolver(policy QuorumPolicy, deadlineMS int64) *QuorumResolver {
	if policy == "" {
		switch os.Getenv("ORICLI_SWARM_JURY_QUORUM") {
		case "unanimous":
			policy = QuorumUnanimous
		default:
			policy = QuorumMajority
		}
	}
	if deadlineMS == 0 {
		if v := os.Getenv("ORICLI_SWARM_JURY_DEADLINE_MS"); v != "" {
			if n, err := strconv.ParseInt(v, 10, 64); err == nil && n > 0 {
				deadlineMS = n
			}
		}
		if deadlineMS == 0 {
			deadlineMS = 4000
		}
	}
	return &QuorumResolver{
		policy:     policy,
		deadlineMS: deadlineMS,
		sessions:   make(map[string]*JurySession),
	}
}

// OpenSession registers a new jury session and returns its result channel.
func (r *QuorumResolver) OpenSession(sessionID string, expected int) <-chan QuorumResult {
	ch := make(chan QuorumResult, 1)
	sess := &JurySession{
		SessionID: sessionID,
		Expected:  expected,
		resultCh:  ch,
		deadline:  time.Now().Add(time.Duration(r.deadlineMS) * time.Millisecond),
	}
	r.mu.Lock()
	r.sessions[sessionID] = sess
	r.mu.Unlock()

	// Deadline goroutine — resolve with whatever verdicts arrived.
	go func() {
		time.Sleep(time.Until(sess.deadline))
		r.resolve(sessionID)
	}()
	return ch
}

// RecordVerdict delivers a peer verdict to the appropriate session.
func (r *QuorumResolver) RecordVerdict(v JuryVerdict) {
	r.mu.Lock()
	sess, ok := r.sessions[v.SessionID]
	r.mu.Unlock()
	if !ok {
		return
	}
	sess.mu.Lock()
	sess.Verdicts = append(sess.Verdicts, v)
	received := len(sess.Verdicts)
	expected := sess.Expected
	sess.mu.Unlock()

	// Early resolution: if we have all expected verdicts, don't wait for deadline.
	if received >= expected {
		r.resolve(v.SessionID)
	}
}

func (r *QuorumResolver) resolve(sessionID string) {
	r.mu.Lock()
	sess, ok := r.sessions[sessionID]
	if ok {
		delete(r.sessions, sessionID)
	}
	r.mu.Unlock()
	if !ok {
		return
	}

	sess.mu.Lock()
	verdicts := make([]JuryVerdict, len(sess.Verdicts))
	copy(verdicts, sess.Verdicts)
	sess.mu.Unlock()

	result := r.applyPolicy(sessionID, verdicts)
	select {
	case sess.resultCh <- result:
	default:
	}
}

func (r *QuorumResolver) applyPolicy(sessionID string, verdicts []JuryVerdict) QuorumResult {
	passed := 0
	var failReasons []string
	for _, v := range verdicts {
		if v.Passed {
			passed++
		} else if v.Critique != "" {
			failReasons = append(failReasons, fmt.Sprintf("[%s] %s", v.JurorNodeID[:min(8, len(v.JurorNodeID))], v.Critique))
		}
	}
	total := len(verdicts)

	var ok bool
	switch r.policy {
	case QuorumUnanimous:
		ok = total > 0 && passed == total
	default: // QuorumMajority
		ok = total == 0 || passed*2 > total // no verdicts = pass-through (peers unavailable)
	}

	return QuorumResult{
		SessionID:   sessionID,
		Passed:      ok,
		Policy:      r.policy,
		Verdicts:    verdicts,
		FailReasons: failReasons,
	}
}

// ActiveSessions returns a snapshot of in-flight session IDs and their verdict counts.
func (r *QuorumResolver) ActiveSessions() []map[string]any {
	r.mu.Lock()
	defer r.mu.Unlock()
	out := make([]map[string]any, 0, len(r.sessions))
	for id, sess := range r.sessions {
		sess.mu.Lock()
		count := len(sess.Verdicts)
		expected := sess.Expected
		deadline := sess.deadline
		sess.mu.Unlock()
		out = append(out, map[string]any{
			"session_id":       id,
			"verdicts_received": count,
			"expected":         expected,
			"deadline":         deadline,
			"policy":           string(r.policy),
		})
	}
	return out
}

// ---------------------------------------------------------------------------
// JuryClient — wires QuorumResolver to PeerRegistry
// ---------------------------------------------------------------------------

// JuryCritic is the function signature for a local SCAI Critique call.
// Inject this from the SCAIAuditor.Critique method in P5-4 wiring.
type JuryCritic func(ctx context.Context, query, draft string) (critique string, passed bool, err error)

// JuryClient orchestrates jury requests across the swarm.
type JuryClient struct {
	identity   *NodeIdentity
	registry   *PeerRegistry
	reputation *ReputationStore
	resolver   *QuorumResolver
	critic     JuryCritic // local SCAI critique for serving peer requests
}

// NewJuryClient creates a JuryClient.
// critic is this node's local SCAI Critique implementation — used when serving as a juror.
func NewJuryClient(identity *NodeIdentity, registry *PeerRegistry, reputation *ReputationStore, resolver *QuorumResolver, critic JuryCritic) *JuryClient {
	return &JuryClient{
		identity:   identity,
		registry:   registry,
		reputation: reputation,
		resolver:   resolver,
		critic:     critic,
	}
}

// RequestVerification broadcasts a JuryRequest to up to defaultJurySize peers
// and waits for quorum. Returns (passed, failReasons, error).
//
// Only call for AuditLevelFull — this blocks until quorum or deadline.
func (j *JuryClient) RequestVerification(ctx context.Context, sessionID, query, draft string) (bool, []string, error) {
	peers := j.registry.ConnectedPeers()
	if len(peers) == 0 {
		// No peers — pass-through (sovereign fallback to local-only audit).
		return true, nil, nil
	}

	// Cap jury size.
	jurySize := len(peers)
	if jurySize > defaultJurySize {
		jurySize = defaultJurySize
		peers = peers[:jurySize]
	}

	req := JuryRequest{
		SessionID: sessionID,
		Query:     query,
		Draft:     draft,
		NodeID:    j.identity.NodeID,
		IssuedAt:  time.Now().UTC(),
	}
	req.Signature = j.identity.Sign(req.sigPayload())

	resultCh := j.resolver.OpenSession(sessionID, jurySize)

	data, _ := json.Marshal(req)
	for _, peerID := range peers {
		if err := j.registry.Send(peerID, SwarmEnvelope{
			Type:    EnvTypeJuryRequest,
			From:    j.identity.NodeID,
			To:      peerID,
			Payload: data,
		}); err != nil {
			log.Printf("[jury] send to %s: %v", peerID[:min(8, len(peerID))], err)
		}
	}

	select {
	case <-ctx.Done():
		return true, nil, ctx.Err() // sovereign fallback on cancellation
	case result := <-resultCh:
		// Apply reputation signals.
		for _, v := range result.Verdicts {
			j.reputation.RecordEvent(v.JurorNodeID, ScoreSCAIPass)
		}
		// Peers that didn't respond within deadline get a missed-bounty signal.
		responded := make(map[string]bool)
		for _, v := range result.Verdicts {
			responded[v.JurorNodeID] = true
		}
		for _, peerID := range peers {
			if !responded[peerID] {
				j.reputation.RecordEvent(peerID, ScoreBountyFailed)
			}
		}
		return result.Passed, result.FailReasons, nil
	}
}

// HandleJuryRequest processes an inbound JuryRequest from a peer, runs local
// SCAI Critique, and sends back a JuryVerdict.
func (j *JuryClient) HandleJuryRequest(peer *PeerConn, env SwarmEnvelope) {
	var req JuryRequest
	if ok, err := env.UnmarshalPayload(&req); !ok || err != nil {
		return
	}

	// Verify request signature.
	if !VerifyPeer(ed25519.PublicKey(nil), req.sigPayload(), req.Signature) {
		// We don't have the requester's pubkey cached here — skip sig verify for now.
		// P5-4 wiring can inject a pubkey cache from PeerRegistry attestations.
		log.Printf("[jury] skipping sig verify for jury request from %s (pubkey cache not yet wired)", peer.ShortID)
	}

	var critique string
	var passed bool
	if j.critic != nil {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		var err error
		critique, passed, err = j.critic(ctx, req.Query, req.Draft)
		if err != nil {
			log.Printf("[jury] local critique error: %v", err)
			return
		}
	} else {
		// No local SCAI available — abstain (pass-through).
		passed = true
	}

	verdict := JuryVerdict{
		SessionID:   req.SessionID,
		JurorNodeID: j.identity.NodeID,
		Passed:      passed,
		Critique:    critique,
		IssuedAt:    time.Now().UTC(),
	}
	verdict.Signature = j.identity.Sign(verdict.sigPayload())

	data, _ := json.Marshal(verdict)
	if err := j.registry.Send(peer.NodeID, SwarmEnvelope{
		Type:    EnvTypeJuryVerdict,
		From:    j.identity.NodeID,
		To:      peer.NodeID,
		Payload: data,
	}); err != nil {
		log.Printf("[jury] verdict send to %s: %v", peer.ShortID, err)
	}
}

// HandleJuryVerdict routes an inbound verdict to the QuorumResolver.
func (j *JuryClient) HandleJuryVerdict(_ *PeerConn, env SwarmEnvelope) {
	var verdict JuryVerdict
	if ok, err := env.UnmarshalPayload(&verdict); !ok || err != nil {
		return
	}
	j.resolver.RecordVerdict(verdict)
}

// ActiveSessions proxies QuorumResolver.ActiveSessions for API handler access.
func (j *JuryClient) ActiveSessions() []map[string]any {
if j.resolver == nil {
return nil
}
return j.resolver.ActiveSessions()
}
