// Package swarm implements the Sovereign Peer Protocol (SPP) —
// a zero-broker, WebSocket-mesh swarm communication layer for independent
// Oricli engine instances. Nodes trade Knowledge Fragments and Task Bids
// without exposing raw data or owner identity.
//
// This file: SPP-1 — Node Identity + Constitutional Attestation.
//
// Each engine generates a persistent Ed25519 keypair on first boot.
// Mutual authentication uses a challenge-response handshake plus a
// ConstitutionalAttestation (SHA-256 of active SCAI rules + Hive OS version),
// proving the remote node is running a constitutionally-aligned Hive OS.
//
// Env vars:
//
//	ORICLI_STATE_DIR — state directory (default ".oricli")
package swarm

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/ecdh"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// HiveOSVersion is the canonical Hive OS version string embedded in attestations.
// Bump this when the Constitutional Stack or core Swarm protocol changes.
const HiveOSVersion = "2.1.0"

// identityFile is the filename within ORICLI_STATE_DIR for the persisted keypair.
const identityFile = ".node_identity"

// NodeIdentity holds the persistent cryptographic identity of this Oricli engine.
type NodeIdentity struct {
	// NodeID is the hex-encoded SHA-256 fingerprint of the Ed25519 public key.
	// First 16 chars are used for human-readable display.
	NodeID string `json:"node_id"`

	// PublicKey is the raw Ed25519 public key bytes.
	PublicKey ed25519.PublicKey `json:"public_key"`

	// privateKey is never serialised; loaded from disk only.
	privateKey ed25519.PrivateKey

	mu sync.RWMutex
}

// identityDisk is the on-disk JSON representation (includes private key).
type identityDisk struct {
	NodeID     string `json:"node_id"`
	PublicKey  []byte `json:"public_key"`
	PrivateKey []byte `json:"private_key"`
}

// LoadOrCreateIdentity loads the node identity from stateDir, creating a new
// Ed25519 keypair if none exists.
func LoadOrCreateIdentity(stateDir string) (*NodeIdentity, error) {
	if err := os.MkdirAll(stateDir, 0700); err != nil {
		return nil, fmt.Errorf("swarm/identity: mkdir state dir: %w", err)
	}
	path := filepath.Join(stateDir, identityFile)

	if data, err := os.ReadFile(path); err == nil {
		return deserializeIdentity(data)
	}

	// Generate new keypair.
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return nil, fmt.Errorf("swarm/identity: keygen: %w", err)
	}
	id := &NodeIdentity{
		NodeID:     fingerprintPubKey(pub),
		PublicKey:  pub,
		privateKey: priv,
	}
	if err := id.persist(path); err != nil {
		return nil, err
	}
	return id, nil
}

// ShortID returns the first 16 hex chars of the NodeID for human-readable display.
func (n *NodeIdentity) ShortID() string {
	if len(n.NodeID) >= 16 {
		return n.NodeID[:16]
	}
	return n.NodeID
}

// Sign signs msg with the node's Ed25519 private key.
func (n *NodeIdentity) Sign(msg []byte) []byte {
	n.mu.RLock()
	defer n.mu.RUnlock()
	return ed25519.Sign(n.privateKey, msg)
}

// Verify checks that sig is a valid Ed25519 signature over msg by this node's key.
func (n *NodeIdentity) Verify(msg, sig []byte) bool {
	n.mu.RLock()
	defer n.mu.RUnlock()
	return ed25519.Verify(n.PublicKey, msg, sig)
}

// VerifyPeer checks that sig is a valid Ed25519 signature over msg by peerPubKey.
func VerifyPeer(peerPubKey ed25519.PublicKey, msg, sig []byte) bool {
	return ed25519.Verify(peerPubKey, msg, sig)
}

// persist writes the identity keypair to disk with 0600 permissions.
func (n *NodeIdentity) persist(path string) error {
	d := identityDisk{
		NodeID:     n.NodeID,
		PublicKey:  []byte(n.PublicKey),
		PrivateKey: []byte(n.privateKey),
	}
	data, err := json.Marshal(d)
	if err != nil {
		return fmt.Errorf("swarm/identity: marshal: %w", err)
	}
	return os.WriteFile(path, data, 0600)
}

func deserializeIdentity(data []byte) (*NodeIdentity, error) {
	var d identityDisk
	if err := json.Unmarshal(data, &d); err != nil {
		return nil, fmt.Errorf("swarm/identity: unmarshal: %w", err)
	}
	if len(d.PublicKey) != ed25519.PublicKeySize || len(d.PrivateKey) != ed25519.PrivateKeySize {
		return nil, errors.New("swarm/identity: corrupt keypair on disk")
	}
	return &NodeIdentity{
		NodeID:     d.NodeID,
		PublicKey:  ed25519.PublicKey(d.PublicKey),
		privateKey: ed25519.PrivateKey(d.PrivateKey),
	}, nil
}

func fingerprintPubKey(pub ed25519.PublicKey) string {
	h := sha256.Sum256(pub)
	return hex.EncodeToString(h[:])
}

// ---------------------------------------------------------------------------
// Constitutional Attestation
// ---------------------------------------------------------------------------

// ConstitutionalAttestation proves that a node is running a constitutionally-
// aligned Hive OS. It contains a stable fingerprint of the active SCAI
// constitution rules + the Hive OS version, all signed by the node's Ed25519 key.
//
// This is NOT a zero-knowledge proof — it is a "Constitutional Attestation":
// the peer learns the constitution hash and OS version, not the raw rules.
type ConstitutionalAttestation struct {
	NodeID            string    `json:"node_id"`
	HiveOSVersion     string    `json:"hive_os_version"`
	ConstitutionHash  string    `json:"constitution_hash"` // SHA-256 of canonical rule text
	IssuedAt          time.Time `json:"issued_at"`
	Signature         []byte    `json:"signature"` // Ed25519 sig over the above fields (canonical JSON)
}

// NewAttestation builds and signs a ConstitutionalAttestation for this node.
// constitutionText should be the stable canonical string representation of the
// active SCAI principles (e.g. Constitution.GetSystemPrompt()).
func NewAttestation(identity *NodeIdentity, constitutionText string) *ConstitutionalAttestation {
	h := sha256.Sum256([]byte(constitutionText))
	a := &ConstitutionalAttestation{
		NodeID:           identity.NodeID,
		HiveOSVersion:    HiveOSVersion,
		ConstitutionHash: hex.EncodeToString(h[:]),
		IssuedAt:         time.Now().UTC(),
	}
	a.Signature = identity.Sign(a.sigPayload())
	return a
}

// Verify checks that the attestation signature is valid for the given public key.
// It does NOT enforce a specific ConstitutionHash — callers may enforce policy.
func (a *ConstitutionalAttestation) Verify(peerPubKey ed25519.PublicKey) bool {
	if a == nil {
		return false
	}
	return VerifyPeer(peerPubKey, a.sigPayload(), a.Signature)
}

// sigPayload is the canonical bytes signed/verified — stable JSON without Signature.
func (a *ConstitutionalAttestation) sigPayload() []byte {
	type sigFields struct {
		NodeID           string    `json:"node_id"`
		HiveOSVersion    string    `json:"hive_os_version"`
		ConstitutionHash string    `json:"constitution_hash"`
		IssuedAt         time.Time `json:"issued_at"`
	}
	b, _ := json.Marshal(sigFields{
		NodeID:           a.NodeID,
		HiveOSVersion:    a.HiveOSVersion,
		ConstitutionHash: a.ConstitutionHash,
		IssuedAt:         a.IssuedAt,
	})
	return b
}

// ---------------------------------------------------------------------------
// Challenge-Response Handshake
// ---------------------------------------------------------------------------

// HandshakeChallenge is sent by the initiating node to a peer.
type HandshakeChallenge struct {
	FromNodeID  string    `json:"from_node_id"`
	FromPubKey  []byte    `json:"from_pub_key"` // raw Ed25519 public key bytes
	Nonce       []byte    `json:"nonce"`        // 32 random bytes
	IssuedAt    time.Time `json:"issued_at"`
	Attestation *ConstitutionalAttestation `json:"attestation"`

	// ECDHPublicKey is the ephemeral X25519 public key for session key negotiation.
	ECDHPublicKey []byte `json:"ecdh_pub_key"`
}

// HandshakeResponse is returned by the peer being challenged.
type HandshakeResponse struct {
	FromNodeID    string    `json:"from_node_id"`
	FromPubKey    []byte    `json:"from_pub_key"`
	Nonce         []byte    `json:"nonce"`         // echo of challenge nonce
	ResponseNonce []byte    `json:"response_nonce"` // 32 new random bytes for reverse proof
	NonceSig      []byte    `json:"nonce_sig"`     // Ed25519 sig over challenge nonce
	IssuedAt      time.Time `json:"issued_at"`
	Attestation   *ConstitutionalAttestation `json:"attestation"`
	ECDHPublicKey []byte    `json:"ecdh_pub_key"` // peer's ephemeral X25519 key
}

// HandshakeFinalise is sent by the initiator to complete mutual auth.
type HandshakeFinalise struct {
	FromNodeID    string `json:"from_node_id"`
	ResponseNonce []byte `json:"response_nonce"` // echo of response nonce
	NonceSig      []byte `json:"nonce_sig"`      // Ed25519 sig over response nonce
}

// NewChallenge creates a HandshakeChallenge from the local identity.
func NewChallenge(identity *NodeIdentity, constitutionText string) (*HandshakeChallenge, *ecdh.PrivateKey, error) {
	nonce := make([]byte, 32)
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, nil, fmt.Errorf("swarm/identity: challenge nonce: %w", err)
	}

	ecdhPriv, ecdhPub, err := generateECDHPair()
	if err != nil {
		return nil, nil, err
	}

	return &HandshakeChallenge{
		FromNodeID:    identity.NodeID,
		FromPubKey:    []byte(identity.PublicKey),
		Nonce:         nonce,
		IssuedAt:      time.Now().UTC(),
		Attestation:   NewAttestation(identity, constitutionText),
		ECDHPublicKey: ecdhPub,
	}, ecdhPriv, nil
}

// RespondToChallenge validates the challenge and builds a HandshakeResponse.
// Returns the derived AES-256-GCM session key and the response message.
func RespondToChallenge(
	identity *NodeIdentity,
	constitutionText string,
	ch *HandshakeChallenge,
) (*HandshakeResponse, []byte, error) {
	// Verify challenger's attestation signature.
	challengerPub := ed25519.PublicKey(ch.FromPubKey)
	if !ch.Attestation.Verify(challengerPub) {
		return nil, nil, errors.New("swarm/identity: challenger attestation invalid")
	}
	if ch.Attestation.NodeID != ch.FromNodeID {
		return nil, nil, errors.New("swarm/identity: attestation node_id mismatch")
	}

	// Derive session key via ECDH.
	sessionKey, ecdhPub, err := deriveSessionKey(ch.ECDHPublicKey)
	if err != nil {
		return nil, nil, err
	}

	respNonce := make([]byte, 32)
	if _, err := io.ReadFull(rand.Reader, respNonce); err != nil {
		return nil, nil, fmt.Errorf("swarm/identity: response nonce: %w", err)
	}

	resp := &HandshakeResponse{
		FromNodeID:    identity.NodeID,
		FromPubKey:    []byte(identity.PublicKey),
		Nonce:         ch.Nonce,
		ResponseNonce: respNonce,
		NonceSig:      identity.Sign(ch.Nonce),
		IssuedAt:      time.Now().UTC(),
		Attestation:   NewAttestation(identity, constitutionText),
		ECDHPublicKey: ecdhPub,
	}
	return resp, sessionKey, nil
}

// VerifyResponse validates a HandshakeResponse against the original challenge.
// Returns the derived session key and a HandshakeFinalise message to send.
func VerifyResponse(
	identity *NodeIdentity,
	ch *HandshakeChallenge,
	ecdhPriv *ecdh.PrivateKey,
	resp *HandshakeResponse,
) (*HandshakeFinalise, []byte, error) {
	peerPub := ed25519.PublicKey(resp.FromPubKey)

	// Peer must have signed our challenge nonce.
	if !VerifyPeer(peerPub, ch.Nonce, resp.NonceSig) {
		return nil, nil, errors.New("swarm/identity: response nonce signature invalid")
	}
	// Attestation must be self-consistent.
	if !resp.Attestation.Verify(peerPub) {
		return nil, nil, errors.New("swarm/identity: peer attestation invalid")
	}
	if resp.Attestation.NodeID != resp.FromNodeID {
		return nil, nil, errors.New("swarm/identity: peer attestation node_id mismatch")
	}

	// Derive session key from peer's ECDH public key + our private key.
	sharedSecret, err := ecdhPriv.ECDH(mustParseX25519(resp.ECDHPublicKey))
	if err != nil {
		return nil, nil, fmt.Errorf("swarm/identity: ECDH finalise: %w", err)
	}
	key := deriveAESKey(sharedSecret)

	fin := &HandshakeFinalise{
		FromNodeID:    identity.NodeID,
		ResponseNonce: resp.ResponseNonce,
		NonceSig:      identity.Sign(resp.ResponseNonce),
	}
	return fin, key, nil
}

// VerifyFinalise completes the mutual auth on the responder side.
// Must be called with the original challenger's public key.
func VerifyFinalise(challengerPubKey ed25519.PublicKey, responseNonce []byte, fin *HandshakeFinalise) error {
	if !VerifyPeer(challengerPubKey, responseNonce, fin.NonceSig) {
		return errors.New("swarm/identity: finalise nonce signature invalid")
	}
	return nil
}

// ---------------------------------------------------------------------------
// AES-256-GCM helpers (used by peer.go for message encryption)
// ---------------------------------------------------------------------------

// EncryptGCM encrypts plaintext with the given 32-byte AES-256-GCM key.
// Returns nonce+ciphertext (nonce prepended, 12 bytes).
func EncryptGCM(key, plaintext []byte) ([]byte, error) {
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, err
	}
	ct := gcm.Seal(nonce, nonce, plaintext, nil)
	return ct, nil
}

// DecryptGCM decrypts a nonce+ciphertext blob produced by EncryptGCM.
func DecryptGCM(key, data []byte) ([]byte, error) {
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	ns := gcm.NonceSize()
	if len(data) < ns {
		return nil, errors.New("swarm/identity: ciphertext too short")
	}
	return gcm.Open(nil, data[:ns], data[ns:], nil)
}

// ---------------------------------------------------------------------------
// ECDH / session key internals
// ---------------------------------------------------------------------------

func generateECDHPair() (priv *ecdh.PrivateKey, pubBytes []byte, err error) {
	curve := ecdh.X25519()
	priv, err = curve.GenerateKey(rand.Reader)
	if err != nil {
		return nil, nil, fmt.Errorf("swarm/identity: ECDH keygen: %w", err)
	}
	return priv, priv.PublicKey().Bytes(), nil
}

func deriveSessionKey(peerECDHPubBytes []byte) (sessionKey []byte, localPubBytes []byte, err error) {
	curve := ecdh.X25519()
	priv, localPub, err := generateECDHPair()
	if err != nil {
		return nil, nil, err
	}
	peerPub, err := curve.NewPublicKey(peerECDHPubBytes)
	if err != nil {
		return nil, nil, fmt.Errorf("swarm/identity: parse peer ECDH key: %w", err)
	}
	shared, err := priv.ECDH(peerPub)
	if err != nil {
		return nil, nil, fmt.Errorf("swarm/identity: ECDH derive: %w", err)
	}
	return deriveAESKey(shared), localPub, nil
}

// deriveAESKey hashes the raw ECDH shared secret into a 32-byte AES key.
func deriveAESKey(sharedSecret []byte) []byte {
	h := sha256.Sum256(sharedSecret)
	return h[:]
}

func mustParseX25519(b []byte) *ecdh.PublicKey {
	k, err := ecdh.X25519().NewPublicKey(b)
	if err != nil {
		panic(fmt.Sprintf("swarm/identity: mustParseX25519: %v", err))
	}
	return k
}
