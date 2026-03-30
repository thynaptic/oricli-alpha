// SPP-5 — Global ERI + Swarm Homeostasis
//
// SwarmMonitor aggregates health beacons published by all connected peers and
// detects unstable nodes before they can corrupt local reasoning.
//
// Each node publishes a SwarmHealthBeacon every 60 seconds on the "health_beacon"
// envelope type. The monitor tracks a rolling window of beacons per peer.
//
// Anomaly detection:
//   - ERI score < ERILowThreshold  (default 0.3) for AnomalyWindowSize consecutive beacons
//   - Volatility > VolatilityHighThreshold (default 0.8) for AnomalyWindowSize consecutive beacons
//
// When either condition is met:
//   - The peer's reputation score is penalised (ScoreFragmentInaccurate × 2).
//   - No new bounty bids are accepted from the flagged node.
//   - An alert is logged.
//
// GET /v1/swarm/health returns a SwarmHealthReport aggregating all live peers.
package swarm

import (
	"encoding/json"
	"log"
	"sync"
	"time"
)

// Homeostasis tuning constants.
const (
	ERILowThreshold        = 0.3
	VolatilityHighThreshold = 0.8
	AnomalyWindowSize      = 3  // consecutive bad beacons before flagging
	BeaconPublishInterval  = 60 * time.Second
)

// SwarmHealthBeacon is published by each node on the swarm bus every 60s.
type SwarmHealthBeacon struct {
	NodeID      string    `json:"node_id"`
	ERIScore    float64   `json:"eri_score"`    // 0.0–1.0; higher = more resonant
	Volatility  float64   `json:"volatility"`   // 0.0–1.0; higher = more erratic
	Coherence   float64   `json:"coherence"`    // 0.0–1.0
	ActiveTasks int       `json:"active_tasks"`
	UptimeSecs  int64     `json:"uptime_secs"`
	PublishedAt time.Time `json:"published_at"`
}

// PeerHealthState tracks the rolling beacon window for a single peer.
type PeerHealthState struct {
	NodeID        string
	ShortID       string
	LatestBeacon  SwarmHealthBeacon
	BeaconHistory []SwarmHealthBeacon // last AnomalyWindowSize beacons
	Flagged       bool
	FlaggedAt     time.Time
	FlagReason    string
}

// SwarmHealthReport is returned by the /v1/swarm/health endpoint.
type SwarmHealthReport struct {
	LocalNodeID    string             `json:"local_node_id"`
	ConnectedPeers int                `json:"connected_peers"`
	FlaggedPeers   int                `json:"flagged_peers"`
	Peers          []PeerHealthState  `json:"peers"`
	GeneratedAt    time.Time          `json:"generated_at"`
}

// ERIProvider is implemented by whatever maintains the local ERI score
// (e.g. the SovereignEngine or ERI service). Used to populate the local
// node's own beacon fields.
type ERIProvider interface {
	CurrentERI() float64
	CurrentVolatility() float64
	CurrentCoherence() float64
}

// SwarmMonitor aggregates health beacons from all peers and detects anomalies.
type SwarmMonitor struct {
	identity   *NodeIdentity
	reputation *ReputationStore
	eri        ERIProvider // may be nil; local beacon will use placeholder values

	states  map[string]*PeerHealthState
	mu      sync.RWMutex

	startTime time.Time
}

// NewSwarmMonitor creates a SwarmMonitor.
func NewSwarmMonitor(identity *NodeIdentity, reputation *ReputationStore, eri ERIProvider) *SwarmMonitor {
	return &SwarmMonitor{
		identity:   identity,
		reputation: reputation,
		eri:        eri,
		states:     make(map[string]*PeerHealthState),
		startTime:  time.Now(),
	}
}

// IngestBeacon processes an inbound SwarmHealthBeacon from a peer.
// Call this from the Marketplace.HandleEnvelope for EnvTypeHealthBeacon.
func (m *SwarmMonitor) IngestBeacon(beacon SwarmHealthBeacon) {
	m.mu.Lock()
	state, ok := m.states[beacon.NodeID]
	if !ok {
		state = &PeerHealthState{
			NodeID:  beacon.NodeID,
			ShortID: beacon.NodeID[:min(16, len(beacon.NodeID))],
		}
		m.states[beacon.NodeID] = state
	}
	state.LatestBeacon = beacon

	// Maintain rolling window.
	state.BeaconHistory = append(state.BeaconHistory, beacon)
	if len(state.BeaconHistory) > AnomalyWindowSize {
		state.BeaconHistory = state.BeaconHistory[len(state.BeaconHistory)-AnomalyWindowSize:]
	}

	shouldFlag := !state.Flagged && len(state.BeaconHistory) >= AnomalyWindowSize && isAnomalous(state.BeaconHistory)
	if shouldFlag {
		state.Flagged = true
		state.FlaggedAt = time.Now().UTC()
		state.FlagReason = anomalyReason(beacon)
	}
	m.mu.Unlock()

	if shouldFlag {
		log.Printf("[homeostasis] peer %s flagged as unstable: %s", beacon.NodeID[:min(16, len(beacon.NodeID))], anomalyReason(beacon))
		// Apply double reputation penalty.
		if m.reputation != nil {
			m.reputation.RecordEvent(beacon.NodeID, ScoreFragmentInaccurate)
			m.reputation.RecordEvent(beacon.NodeID, ScoreFragmentInaccurate)
		}
	}
}

// BuildLocalBeacon constructs this node's own SwarmHealthBeacon for broadcast.
func (m *SwarmMonitor) BuildLocalBeacon(activeTasks int) SwarmHealthBeacon {
	eri, vol, coh := 0.75, 0.1, 0.8 // healthy defaults when no ERIProvider wired
	if m.eri != nil {
		eri = m.eri.CurrentERI()
		vol = m.eri.CurrentVolatility()
		coh = m.eri.CurrentCoherence()
	}
	return SwarmHealthBeacon{
		NodeID:      m.identity.NodeID,
		ERIScore:    eri,
		Volatility:  vol,
		Coherence:   coh,
		ActiveTasks: activeTasks,
		UptimeSecs:  int64(time.Since(m.startTime).Seconds()),
		PublishedAt: time.Now().UTC(),
	}
}

// IsFlagged returns true if the peer has been detected as anomalous.
func (m *SwarmMonitor) IsFlagged(nodeID string) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	s, ok := m.states[nodeID]
	return ok && s.Flagged
}

// ClearFlag manually clears a peer's anomaly flag (e.g. after it recovers).
func (m *SwarmMonitor) ClearFlag(nodeID string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if s, ok := m.states[nodeID]; ok {
		s.Flagged = false
		s.FlagReason = ""
		s.BeaconHistory = nil
	}
}

// Report returns a SwarmHealthReport for the /v1/swarm/health endpoint.
func (m *SwarmMonitor) Report(connectedPeerIDs []string) SwarmHealthReport {
	m.mu.RLock()
	defer m.mu.RUnlock()

	peers := make([]PeerHealthState, 0, len(m.states))
	flagged := 0
	for _, s := range m.states {
		cp := *s
		peers = append(peers, cp)
		if s.Flagged {
			flagged++
		}
	}
	return SwarmHealthReport{
		LocalNodeID:    m.identity.NodeID,
		ConnectedPeers: len(connectedPeerIDs),
		FlaggedPeers:   flagged,
		Peers:          peers,
		GeneratedAt:    time.Now().UTC(),
	}
}

// ---------------------------------------------------------------------------
// Anomaly detection helpers
// ---------------------------------------------------------------------------

func isAnomalous(history []SwarmHealthBeacon) bool {
	lowERI := 0
	highVol := 0
	for _, b := range history {
		if b.ERIScore < ERILowThreshold {
			lowERI++
		}
		if b.Volatility > VolatilityHighThreshold {
			highVol++
		}
	}
	return lowERI >= AnomalyWindowSize || highVol >= AnomalyWindowSize
}

func anomalyReason(b SwarmHealthBeacon) string {
	if b.ERIScore < ERILowThreshold {
		return "low ERI score"
	}
	if b.Volatility > VolatilityHighThreshold {
		return "high volatility"
	}
	return "anomalous beacon pattern"
}

// ---------------------------------------------------------------------------
// Beacon publisher (runs as a goroutine from SPP-6 wiring)
// ---------------------------------------------------------------------------

// RunBeaconPublisher periodically broadcasts this node's health beacon to all peers.
// Call as go monitor.RunBeaconPublisher(ctx, registry, activeTasksFn).
func (m *SwarmMonitor) RunBeaconPublisher(
	ctx interface{ Done() <-chan struct{} },
	registry *PeerRegistry,
	activeTasksFn func() int,
) {
	ticker := time.NewTicker(BeaconPublishInterval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			beacon := m.BuildLocalBeacon(activeTasksFn())
			data, _ := jsonMarshal(beacon)
			registry.Broadcast(SwarmEnvelope{
				Type:    EnvTypeHealthBeacon,
				From:    m.identity.NodeID,
				Payload: data,
			})
		}
	}
}

// jsonMarshal is a package-level alias for json.Marshal used by RunBeaconPublisher.
func jsonMarshal(v any) ([]byte, error) {
	return json.Marshal(v)
}
