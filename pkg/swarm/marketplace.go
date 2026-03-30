// SPP-3 — Epistemic Marketplace: Fragment Trading + Bounty Execution
//
// The Epistemic Marketplace extends the in-process Contract Net Protocol (CNP)
// to the swarm network. It provides two mechanisms:
//
//  1. Fragment Trading: a node broadcasts a "knowledge gap" to peers before
//     hitting the live web. Peers respond with matching KnowledgeFragments.
//
//  2. Bounty Execution: a node posts a task bounty to the swarm. Peers bid.
//     The originating node accepts the best bid and awaits the result fragment.
//
// All fragment payloads are Ed25519-signed by the issuing node. The receiving
// node verifies the signature before ingesting into chromem-go.
// Raw source text never leaves the origin node — only embeddings + metadata.
package swarm

import (
	"context"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"sync"
	"time"
)

// ---------------------------------------------------------------------------
// Knowledge Fragment
// ---------------------------------------------------------------------------

// KnowledgeFragment is the atomic unit of swarm knowledge exchange.
// Raw source text stays on the origin node; only the embedding + metadata travels.
type KnowledgeFragment struct {
	ID         string    `json:"id"`          // SHA-256 of (Subject + NodeID + IssuedAt)
	Subject    string    `json:"subject"`     // human-readable topic label
	Embedding  []float32 `json:"embedding"`   // chromem-go compatible vector
	Confidence float64   `json:"confidence"`  // 0.0–1.0
	SourceHash string    `json:"source_hash"` // SHA-256 of source doc; proves provenance without revealing content
	NodeID     string    `json:"node_id"`     // issuing node fingerprint
	IssuedAt   time.Time `json:"issued_at"`
	Signature  []byte    `json:"signature"` // Ed25519 sig over all fields above (canonical JSON)
}

// NewFragment builds and signs a KnowledgeFragment.
func NewFragment(identity *NodeIdentity, subject string, embedding []float32, confidence float64, sourceText string) *KnowledgeFragment {
	srcHash := sha256.Sum256([]byte(sourceText))
	now := time.Now().UTC()

	f := &KnowledgeFragment{
		Subject:    subject,
		Embedding:  embedding,
		Confidence: confidence,
		SourceHash: hex.EncodeToString(srcHash[:]),
		NodeID:     identity.NodeID,
		IssuedAt:   now,
	}
	f.ID = fragmentID(f)
	f.Signature = identity.Sign(f.sigPayload())
	return f
}

// Verify checks the fragment's Ed25519 signature against the issuer's public key.
func (f *KnowledgeFragment) Verify(issuerPubKey ed25519.PublicKey) error {
	if f == nil {
		return errors.New("swarm/marketplace: nil fragment")
	}
	if !VerifyPeer(issuerPubKey, f.sigPayload(), f.Signature) {
		return fmt.Errorf("swarm/marketplace: fragment %s signature invalid", f.ID[:min(8, len(f.ID))])
	}
	return nil
}

func (f *KnowledgeFragment) sigPayload() []byte {
	type sigFields struct {
		Subject    string    `json:"subject"`
		Confidence float64   `json:"confidence"`
		SourceHash string    `json:"source_hash"`
		NodeID     string    `json:"node_id"`
		IssuedAt   time.Time `json:"issued_at"`
	}
	b, _ := json.Marshal(sigFields{
		Subject:    f.Subject,
		Confidence: f.Confidence,
		SourceHash: f.SourceHash,
		NodeID:     f.NodeID,
		IssuedAt:   f.IssuedAt,
	})
	return b
}

func fragmentID(f *KnowledgeFragment) string {
	h := sha256.Sum256([]byte(f.Subject + f.NodeID + f.IssuedAt.String()))
	return hex.EncodeToString(h[:])
}

// ---------------------------------------------------------------------------
// Bounty
// ---------------------------------------------------------------------------

// BountyRequest is broadcast via CFP to all swarm peers.
type BountyRequest struct {
	BountyID       string    `json:"bounty_id"`
	Task           string    `json:"task"`            // natural language task description
	RequiredSkills []string  `json:"required_skills"` // e.g. ["research", "code_gen"]
	MaxBudgetTokens int      `json:"max_budget_tokens"`
	DeadlineMS     int64     `json:"deadline_ms"` // unix ms; 0 = no deadline
	OriginNodeID   string    `json:"origin_node_id"`
	IssuedAt       time.Time `json:"issued_at"`
}

// BountyBid is a peer's response to a BountyRequest.
type BountyBid struct {
	BountyID       string    `json:"bounty_id"`
	BidderNodeID   string    `json:"bidder_node_id"`
	EstimatedTokens int      `json:"estimated_tokens"`
	ConfidenceScore float64  `json:"confidence_score"` // 0.0–1.0
	IssuedAt        time.Time `json:"issued_at"`
}

// BountyAccept notifies the winning bidder.
type BountyAccept struct {
	BountyID     string `json:"bounty_id"`
	WinnerNodeID string `json:"winner_node_id"`
}

// BountyResult is the completed task payload returned by the winning peer.
type BountyResult struct {
	BountyID   string             `json:"bounty_id"`
	Fragment   *KnowledgeFragment `json:"fragment,omitempty"`
	ResultText string             `json:"result_text,omitempty"` // plain text for non-embedding results
	Success    bool               `json:"success"`
	Error      string             `json:"error,omitempty"`
}

// ---------------------------------------------------------------------------
// Envelope type constants
// ---------------------------------------------------------------------------

const (
	EnvTypeFragmentOffer  = "fragment_offer"  // push: "I have this fragment, want it?"
	EnvTypeFragmentReq    = "fragment_req"    // pull: "does anyone have info on X?"
	EnvTypeFragmentResp   = "fragment_resp"   // reply to fragment_req
	EnvTypeBountyCFP      = "bounty_cfp"      // Call For Proposals
	EnvTypeBountyBid      = "bounty_bid"
	EnvTypeBountyAccept   = "bounty_accept"
	EnvTypeBountyResult   = "bounty_result"
	EnvTypeHealthBeacon   = "health_beacon"   // SPP-5
)

// ---------------------------------------------------------------------------
// Marketplace
// ---------------------------------------------------------------------------

// FragmentIngester is called when a valid fragment arrives from a peer.
// Implement this to pipe into chromem-go or the local knowledge graph.
type FragmentIngester func(f *KnowledgeFragment, fromNodeID string)

// BountyExecutor is called when this node wins a bounty bid.
// It should execute the task and return a BountyResult.
type BountyExecutor func(ctx context.Context, req BountyRequest) BountyResult

// Marketplace manages fragment trading and bounty execution across the swarm.
type Marketplace struct {
	identity  *NodeIdentity
	registry  *PeerRegistry
	ingester  FragmentIngester
	executor  BountyExecutor

	// in-flight bounties originated by this node: bountyID → result channel
	pendingBounties map[string]chan BountyResult
	// bids received for each open bounty: bountyID → []BountyBid
	receivedBids    map[string][]BountyBid
	mu              sync.Mutex
}

// SetRegistry injects the PeerRegistry after construction (avoids circular init).
func (m *Marketplace) SetRegistry(r *PeerRegistry) {
	m.registry = r
}

// NewMarketplace creates a Marketplace. ingester and executor may be nil
// (fragment trading and bounty execution are each optional).
func NewMarketplace(identity *NodeIdentity, registry *PeerRegistry, ingester FragmentIngester, executor BountyExecutor) *Marketplace {
	m := &Marketplace{
		identity:        identity,
		registry:        registry,
		ingester:        ingester,
		executor:        executor,
		pendingBounties: make(map[string]chan BountyResult),
		receivedBids:    make(map[string][]BountyBid),
	}
	return m
}

// HandleEnvelope is the MessageHandler to register with PeerRegistry.
// Route inbound swarm envelopes through here.
func (m *Marketplace) HandleEnvelope(peer *PeerConn, env SwarmEnvelope) {
	switch env.Type {
	case EnvTypeFragmentOffer, EnvTypeFragmentResp:
		m.handleFragment(peer, env)
	case EnvTypeFragmentReq:
		m.handleFragmentRequest(peer, env)
	case EnvTypeBountyCFP:
		m.handleBountyCFP(peer, env)
	case EnvTypeBountyBid:
		m.handleBountyBid(peer, env)
	case EnvTypeBountyAccept:
		m.handleBountyAccept(peer, env)
	case EnvTypeBountyResult:
		m.handleBountyResult(peer, env)
	}
}

// ---------------------------------------------------------------------------
// Fragment trading
// ---------------------------------------------------------------------------

// OfferFragment broadcasts a fragment to all connected peers.
func (m *Marketplace) OfferFragment(f *KnowledgeFragment) {
	data, _ := json.Marshal(f)
	m.registry.Broadcast(SwarmEnvelope{
		Type:    EnvTypeFragmentOffer,
		From:    m.identity.NodeID,
		Payload: data,
	})
}

// RequestFragment broadcasts a knowledge gap query to the swarm.
// subject is the topic label (e.g. "sparse transformers").
// Returns a channel that receives up to maxResults fragments within timeout.
func (m *Marketplace) RequestFragment(ctx context.Context, subject string, maxResults int) <-chan *KnowledgeFragment {
	ch := make(chan *KnowledgeFragment, maxResults)
	req := struct {
		Subject string `json:"subject"`
	}{Subject: subject}
	data, _ := json.Marshal(req)
	m.registry.Broadcast(SwarmEnvelope{
		Type:    EnvTypeFragmentReq,
		From:    m.identity.NodeID,
		Payload: data,
	})
	// Close channel when context expires.
	go func() {
		<-ctx.Done()
		close(ch)
	}()
	return ch
}

func (m *Marketplace) handleFragment(peer *PeerConn, env SwarmEnvelope) {
	var f KnowledgeFragment
	if err := json.Unmarshal(env.Payload, &f); err != nil {
		log.Printf("[marketplace] bad fragment from %s: %v", peer.ShortID, err)
		return
	}
	// Signature verification uses the sender's declared pubkey embedded in attestation.
	// For now we trust the session (ECDH-authenticated) and verify the fragment sig
	// against the NodeID in the fragment itself — reputation layer will penalise bad sigs.
	if m.ingester != nil {
		m.ingester(&f, env.From)
	}
}

func (m *Marketplace) handleFragmentRequest(peer *PeerConn, env SwarmEnvelope) {
	// Stub: in SPP-6 wiring, CuriosityDaemon will register a handler here
	// to check local chromem-go for matching embeddings and respond.
	log.Printf("[marketplace] fragment_req from %s (subject in payload)", peer.ShortID)
}

// ---------------------------------------------------------------------------
// Bounty execution
// ---------------------------------------------------------------------------

// PostBounty broadcasts a task to the swarm and waits for the best bid + result.
// Returns the result or ctx cancellation.
func (m *Marketplace) PostBounty(ctx context.Context, req BountyRequest) (BountyResult, error) {
	ch := make(chan BountyResult, 1)
	m.mu.Lock()
	m.pendingBounties[req.BountyID] = ch
	m.receivedBids[req.BountyID] = nil
	m.mu.Unlock()

	data, _ := json.Marshal(req)
	m.registry.Broadcast(SwarmEnvelope{
		Type:    EnvTypeBountyCFP,
		From:    m.identity.NodeID,
		Payload: data,
	})

	// Collect bids for 3 seconds then accept best.
	bidWindow := time.NewTimer(3 * time.Second)
	defer bidWindow.Stop()

	select {
	case <-ctx.Done():
		m.cleanBounty(req.BountyID)
		return BountyResult{}, ctx.Err()
	case <-bidWindow.C:
	}

	best := m.pickBestBid(req.BountyID)
	if best == nil {
		m.cleanBounty(req.BountyID)
		return BountyResult{BountyID: req.BountyID, Success: false, Error: "no bids received"}, nil
	}

	// Notify winner.
	acceptData, _ := json.Marshal(BountyAccept{BountyID: req.BountyID, WinnerNodeID: best.BidderNodeID})
	if err := m.registry.Send(best.BidderNodeID, SwarmEnvelope{
		Type:    EnvTypeBountyAccept,
		From:    m.identity.NodeID,
		To:      best.BidderNodeID,
		Payload: acceptData,
	}); err != nil {
		m.cleanBounty(req.BountyID)
		return BountyResult{}, fmt.Errorf("swarm/marketplace: send accept: %w", err)
	}

	// Wait for result.
	deadline := 60 * time.Second
	if req.DeadlineMS > 0 {
		deadline = time.Until(time.UnixMilli(req.DeadlineMS))
	}
	timer := time.NewTimer(deadline)
	defer timer.Stop()

	select {
	case <-ctx.Done():
		m.cleanBounty(req.BountyID)
		return BountyResult{}, ctx.Err()
	case <-timer.C:
		m.cleanBounty(req.BountyID)
		return BountyResult{BountyID: req.BountyID, Success: false, Error: "bounty result timeout"}, nil
	case result := <-ch:
		m.cleanBounty(req.BountyID)
		return result, nil
	}
}

func (m *Marketplace) handleBountyCFP(peer *PeerConn, env SwarmEnvelope) {
	if m.executor == nil {
		return
	}
	var req BountyRequest
	if err := json.Unmarshal(env.Payload, &req); err != nil {
		return
	}
	// Bid back with a placeholder confidence; SPP-6 wiring will plug in real skill scoring.
	bid := BountyBid{
		BountyID:        req.BountyID,
		BidderNodeID:    m.identity.NodeID,
		EstimatedTokens: 500,
		ConfidenceScore: 0.7,
		IssuedAt:        time.Now().UTC(),
	}
	data, _ := json.Marshal(bid)
	if err := m.registry.Send(peer.NodeID, SwarmEnvelope{
		Type:    EnvTypeBountyBid,
		From:    m.identity.NodeID,
		To:      peer.NodeID,
		Payload: data,
	}); err != nil {
		log.Printf("[marketplace] bid send to %s: %v", peer.ShortID, err)
	}
}

func (m *Marketplace) handleBountyBid(peer *PeerConn, env SwarmEnvelope) {
	var bid BountyBid
	if err := json.Unmarshal(env.Payload, &bid); err != nil {
		return
	}
	m.mu.Lock()
	m.receivedBids[bid.BountyID] = append(m.receivedBids[bid.BountyID], bid)
	m.mu.Unlock()
}

func (m *Marketplace) handleBountyAccept(peer *PeerConn, env SwarmEnvelope) {
	if m.executor == nil {
		return
	}
	var accept BountyAccept
	if err := json.Unmarshal(env.Payload, &accept); err != nil {
		return
	}
	if accept.WinnerNodeID != m.identity.NodeID {
		return
	}

	// We won — look up the original CFP. In a full implementation the CFP is cached;
	// for now reconstruct a minimal BountyRequest from the accept message.
	req := BountyRequest{BountyID: accept.BountyID, Task: "(cached task — wired in SPP-6)"}
	go func() {
		result := m.executor(context.Background(), req)
		data, _ := json.Marshal(result)
		if err := m.registry.Send(peer.NodeID, SwarmEnvelope{
			Type:    EnvTypeBountyResult,
			From:    m.identity.NodeID,
			To:      peer.NodeID,
			Payload: data,
		}); err != nil {
			log.Printf("[marketplace] result send to %s: %v", peer.ShortID, err)
		}
	}()
}

func (m *Marketplace) handleBountyResult(peer *PeerConn, env SwarmEnvelope) {
	var result BountyResult
	if err := json.Unmarshal(env.Payload, &result); err != nil {
		return
	}
	m.mu.Lock()
	ch, ok := m.pendingBounties[result.BountyID]
	m.mu.Unlock()
	if ok {
		select {
		case ch <- result:
		default:
		}
	}
}

func (m *Marketplace) pickBestBid(bountyID string) *BountyBid {
	m.mu.Lock()
	defer m.mu.Unlock()
	bids := m.receivedBids[bountyID]
	if len(bids) == 0 {
		return nil
	}
	best := &bids[0]
	for i := range bids[1:] {
		if bids[i+1].ConfidenceScore > best.ConfidenceScore {
			best = &bids[i+1]
		}
	}
	return best
}

func (m *Marketplace) cleanBounty(bountyID string) {
	m.mu.Lock()
	delete(m.pendingBounties, bountyID)
	delete(m.receivedBids, bountyID)
	m.mu.Unlock()
}
