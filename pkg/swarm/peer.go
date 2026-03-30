// SPP-2 — Peer Registry + WebSocket Transport
//
// PeerRegistry maintains connected peers, handles bootstrap from a Thynaptic-hosted
// seed list, and manages encrypted WebSocket connections using the AES-256-GCM
// session keys negotiated during the SPP-1 handshake.
//
// Each peer connection runs two goroutines: a reader and a writer.
// All messages are encrypted on the wire using EncryptGCM/DecryptGCM from identity.go.
//
// Env vars:
//
//	THYNAPTIC_PEER_REGISTRY_URL — JSON seed list URL (empty = no bootstrap)
//	ORICLI_SWARM_ENABLED        — must be "true" for swarm to activate
package swarm

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"net/url"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// SeedEntry is one record in the Thynaptic peer registry JSON.
type SeedEntry struct {
	NodeID    string `json:"node_id"`
	WSAddress string `json:"ws_address"` // e.g. "wss://node.example.com/v1/swarm/connect"
	PubKey    []byte `json:"pub_key"`    // raw Ed25519 public key bytes
}

// PeerConn represents an authenticated, encrypted connection to a peer.
type PeerConn struct {
	NodeID     string
	ShortID    string
	sessionKey []byte // 32-byte AES-256-GCM key derived during handshake
	conn       *websocket.Conn
	sendCh     chan []byte // plaintext envelopes; encrypted before write
	closeCh    chan struct{}
	once       sync.Once
}

// SwarmEnvelope is the wire format for all swarm messages (after decryption).
type SwarmEnvelope struct {
	Type    string          `json:"type"`    // "fragment", "bounty_cfp", "bounty_bid", "health_beacon", etc.
	From    string          `json:"from"`    // sender NodeID
	To      string          `json:"to"`      // recipient NodeID or "" for broadcast
	Payload json.RawMessage `json:"payload"` // type-specific payload
}

// UnmarshalPayload decodes the envelope payload into v. Returns (true, nil) on success.
func (e *SwarmEnvelope) UnmarshalPayload(v any) (bool, error) {
	if e.Payload == nil {
		return false, nil
	}
	return true, json.Unmarshal(e.Payload, v)
}


// MessageHandler is called for every decrypted inbound envelope.
type MessageHandler func(peer *PeerConn, env SwarmEnvelope)
type PeerRegistry struct {
	identity         *NodeIdentity
	constitutionText string
	handler          MessageHandler
	auxHandlers      map[string]MessageHandler // P5: per-type auxiliary handlers

	peers   map[string]*PeerConn // keyed by NodeID
	mu      sync.RWMutex

	upgrader websocket.Upgrader
}

// NewPeerRegistry creates a PeerRegistry. constitutionText should be
// Constitution.GetSystemPrompt() — used for attestation during handshakes.
func NewPeerRegistry(identity *NodeIdentity, constitutionText string, handler MessageHandler) *PeerRegistry {
	return &PeerRegistry{
		identity:         identity,
		constitutionText: constitutionText,
		handler:          handler,
		auxHandlers:      make(map[string]MessageHandler),
		peers:            make(map[string]*PeerConn),
		upgrader: websocket.Upgrader{
			HandshakeTimeout: 15 * time.Second,
			CheckOrigin:      func(r *http.Request) bool { return true },
		},
	}
}

// RegisterAuxHandler registers a per-envelope-type handler for P5 subsystems
// (jury, ESI) without requiring modification of the primary Marketplace handler.
func (r *PeerRegistry) RegisterAuxHandler(envType string, h MessageHandler) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.auxHandlers[envType] = h
}

// ---------------------------------------------------------------------------
// Bootstrap from seed registry
// ---------------------------------------------------------------------------

// Bootstrap fetches the Thynaptic peer seed list and dials each listed peer.
// Non-fatal: errors are logged, not returned.
func (r *PeerRegistry) Bootstrap(ctx context.Context, registryURL string) {
	if registryURL == "" {
		return
	}
	seeds, err := fetchSeedList(ctx, registryURL)
	if err != nil {
		log.Printf("[swarm] bootstrap fetch error: %v", err)
		return
	}
	for _, s := range seeds {
		if s.NodeID == r.identity.NodeID {
			continue // skip self
		}
		go r.DialPeer(ctx, s.WSAddress)
	}
}

func fetchSeedList(ctx context.Context, rawURL string) ([]SeedEntry, error) {
	if _, err := url.ParseRequestURI(rawURL); err != nil {
		return nil, fmt.Errorf("swarm/peer: invalid registry URL: %w", err)
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, rawURL, nil)
	if err != nil {
		return nil, err
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	var seeds []SeedEntry
	if err := json.NewDecoder(resp.Body).Decode(&seeds); err != nil {
		return nil, fmt.Errorf("swarm/peer: decode seed list: %w", err)
	}
	return seeds, nil
}

// ---------------------------------------------------------------------------
// Outbound dial
// ---------------------------------------------------------------------------

// DialPeer connects to a peer WebSocket endpoint and runs the SPP handshake.
// Reconnects with exponential backoff (max 5 min) until ctx is cancelled.
func (r *PeerRegistry) DialPeer(ctx context.Context, addr string) {
	backoff := 2 * time.Second
	const maxBackoff = 5 * time.Minute

	for {
		select {
		case <-ctx.Done():
			return
		default:
		}

		if err := r.dialOnce(ctx, addr); err != nil {
			log.Printf("[swarm] dial %s failed: %v — retry in %s", addr, err, backoff)
			jitter := time.Duration(rand.Int63n(int64(backoff / 4)))
			select {
			case <-ctx.Done():
				return
			case <-time.After(backoff + jitter):
			}
			backoff *= 2
			if backoff > maxBackoff {
				backoff = maxBackoff
			}
			continue
		}
		// Successful connection closed cleanly — reset backoff and reconnect.
		backoff = 2 * time.Second
	}
}

func (r *PeerRegistry) dialOnce(ctx context.Context, addr string) error {
	dialer := websocket.Dialer{HandshakeTimeout: 15 * time.Second}
	conn, _, err := dialer.DialContext(ctx, addr, nil)
	if err != nil {
		return fmt.Errorf("ws dial: %w", err)
	}

	// Initiator sends challenge.
	challenge, ecdhPriv, err := NewChallenge(r.identity, r.constitutionText)
	if err != nil {
		conn.Close()
		return err
	}
	if err := writeJSON(conn, challenge); err != nil {
		conn.Close()
		return fmt.Errorf("send challenge: %w", err)
	}

	// Read response.
	var resp HandshakeResponse
	if err := readJSON(conn, &resp); err != nil {
		conn.Close()
		return fmt.Errorf("read response: %w", err)
	}

	// Verify + derive session key.
	fin, sessionKey, err := VerifyResponse(r.identity, challenge, ecdhPriv, &resp)
	if err != nil {
		conn.Close()
		return err
	}

	// Send finalise.
	if err := writeJSON(conn, fin); err != nil {
		conn.Close()
		return fmt.Errorf("send finalise: %w", err)
	}

	peer := r.registerPeer(resp.FromNodeID, sessionKey, conn)
	log.Printf("[swarm] connected to peer %s", peer.ShortID)
	r.runPeer(ctx, peer)
	r.removePeer(peer.NodeID)
	return nil
}

// ---------------------------------------------------------------------------
// Inbound upgrade (HTTP handler — mount at GET /v1/swarm/connect)
// ---------------------------------------------------------------------------

// HandleUpgrade upgrades an HTTP request to a WebSocket peer connection.
// Mount this on the API router: GET /v1/swarm/connect
func (r *PeerRegistry) HandleUpgrade(w http.ResponseWriter, req *http.Request) {
	conn, err := r.upgrader.Upgrade(w, req, nil)
	if err != nil {
		log.Printf("[swarm] upgrade error: %v", err)
		return
	}

	// Responder: read challenge.
	var challenge HandshakeChallenge
	if err := readJSON(conn, &challenge); err != nil {
		log.Printf("[swarm] read challenge: %v", err)
		conn.Close()
		return
	}

	resp, sessionKey, err := RespondToChallenge(r.identity, r.constitutionText, &challenge)
	if err != nil {
		log.Printf("[swarm] respond to challenge: %v", err)
		conn.Close()
		return
	}
	if err := writeJSON(conn, resp); err != nil {
		conn.Close()
		return
	}

	// Read finalise.
	var fin HandshakeFinalise
	if err := readJSON(conn, &fin); err != nil {
		log.Printf("[swarm] read finalise: %v", err)
		conn.Close()
		return
	}
	if err := VerifyFinalise(challenge.FromPubKey, resp.ResponseNonce, &fin); err != nil {
		log.Printf("[swarm] finalise verify: %v", err)
		conn.Close()
		return
	}

	peer := r.registerPeer(challenge.FromNodeID, sessionKey, conn)
	log.Printf("[swarm] peer connected: %s", peer.ShortID)
	r.runPeer(req.Context(), peer)
	r.removePeer(peer.NodeID)
}

// ---------------------------------------------------------------------------
// Send
// ---------------------------------------------------------------------------

// Send encrypts and delivers an envelope to a specific peer.
func (r *PeerRegistry) Send(toNodeID string, env SwarmEnvelope) error {
	r.mu.RLock()
	peer, ok := r.peers[toNodeID]
	r.mu.RUnlock()
	if !ok {
		return fmt.Errorf("swarm/peer: no connection to %s", toNodeID[:16])
	}
	return peer.send(env)
}

// Broadcast sends an envelope to all connected peers.
func (r *PeerRegistry) Broadcast(env SwarmEnvelope) {
	r.mu.RLock()
	peers := make([]*PeerConn, 0, len(r.peers))
	for _, p := range r.peers {
		peers = append(peers, p)
	}
	r.mu.RUnlock()
	for _, p := range peers {
		if err := p.send(env); err != nil {
			log.Printf("[swarm] broadcast to %s: %v", p.ShortID, err)
		}
	}
}

// ConnectedPeers returns a snapshot of all connected peer NodeIDs.
func (r *PeerRegistry) ConnectedPeers() []string {
	r.mu.RLock()
	defer r.mu.RUnlock()
	ids := make([]string, 0, len(r.peers))
	for id := range r.peers {
		ids = append(ids, id)
	}
	return ids
}

func (p *PeerConn) send(env SwarmEnvelope) error {
	plain, err := json.Marshal(env)
	if err != nil {
		return err
	}
	ct, err := EncryptGCM(p.sessionKey, plain)
	if err != nil {
		return err
	}
	select {
	case p.sendCh <- ct:
		return nil
	default:
		return fmt.Errorf("swarm/peer: send buffer full for %s", p.ShortID)
	}
}

// ---------------------------------------------------------------------------
// Peer lifecycle
// ---------------------------------------------------------------------------

func (r *PeerRegistry) registerPeer(nodeID string, sessionKey []byte, conn *websocket.Conn) *PeerConn {
	peer := &PeerConn{
		NodeID:     nodeID,
		ShortID:    nodeID[:min(16, len(nodeID))],
		sessionKey: sessionKey,
		conn:       conn,
		sendCh:     make(chan []byte, 64),
		closeCh:    make(chan struct{}),
	}
	r.mu.Lock()
	r.peers[nodeID] = peer
	r.mu.Unlock()
	return peer
}

func (r *PeerRegistry) removePeer(nodeID string) {
	r.mu.Lock()
	delete(r.peers, nodeID)
	r.mu.Unlock()
}

func (r *PeerRegistry) runPeer(ctx context.Context, peer *PeerConn) {
	var wg sync.WaitGroup
	wg.Add(2)

	// Writer goroutine.
	go func() {
		defer wg.Done()
		for {
			select {
			case <-ctx.Done():
				peer.closeOnce()
				return
			case <-peer.closeCh:
				return
			case ct := <-peer.sendCh:
				if err := peer.conn.WriteMessage(websocket.BinaryMessage, ct); err != nil {
					log.Printf("[swarm] write to %s: %v", peer.ShortID, err)
					peer.closeOnce()
					return
				}
			}
		}
	}()

	// Reader goroutine.
	go func() {
		defer wg.Done()
		for {
			_, msg, err := peer.conn.ReadMessage()
			if err != nil {
				log.Printf("[swarm] read from %s: %v", peer.ShortID, err)
				peer.closeOnce()
				return
			}
			plain, err := DecryptGCM(peer.sessionKey, msg)
			if err != nil {
				log.Printf("[swarm] decrypt from %s: %v", peer.ShortID, err)
				continue
			}
			var env SwarmEnvelope
			if err := json.Unmarshal(plain, &env); err != nil {
				log.Printf("[swarm] unmarshal from %s: %v", peer.ShortID, err)
				continue
			}
			if r.handler != nil {
				r.handler(peer, env)
			}
			// Dispatch to per-type auxiliary handlers registered by P5 subsystems.
			r.mu.RLock()
			aux := r.auxHandlers[env.Type]
			r.mu.RUnlock()
			if aux != nil {
				aux(peer, env)
			}
		}
	}()

	wg.Wait()
	peer.conn.Close()
}

func (p *PeerConn) closeOnce() {
	p.once.Do(func() { close(p.closeCh) })
}

// ---------------------------------------------------------------------------
// JSON helpers
// ---------------------------------------------------------------------------

func writeJSON(conn *websocket.Conn, v any) error {
	data, err := json.Marshal(v)
	if err != nil {
		return err
	}
	return conn.WriteMessage(websocket.TextMessage, data)
}

func readJSON(conn *websocket.Conn, v any) error {
	_, data, err := conn.ReadMessage()
	if err != nil {
		return err
	}
	return json.Unmarshal(data, v)
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
