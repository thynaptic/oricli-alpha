// Package sovereign provides the owner-authentication layer for Oricli.
// Two session levels are supported:
//
//	Level 1 (ADMIN)  — elevated chat: full technical detail, no response softening
//	Level 2 (EXEC)   — all of Level 1 plus safe allowlisted system commands
//
// Plain-text keys are loaded from env vars at startup:
//
//	SOVEREIGN_ADMIN_KEY
//	SOVEREIGN_EXEC_KEY
//
// Keys are compared with constant-time equality. Set them in .env — the
// systemd unit loads that file via EnvironmentFile=.
package sovereign

import (
	"context"
	"crypto/rand"
	"crypto/subtle"
	"encoding/hex"
	"fmt"
	"log"
	"os"
	"strings"
	"sync"
	"time"
)

const (
	LevelNone  = 0
	LevelAdmin = 1
	LevelExec  = 2

	sessionTTL      = time.Hour
	lockoutDuration = 5 * time.Minute
	maxFailedAttempts = 3
)

// SovereignSession holds the state for an authenticated owner session.
type SovereignSession struct {
	Level     int
	ExpiresAt time.Time
}

type failRecord struct {
	count     int
	lockedAt  time.Time
}

// SovereignAuth manages owner sessions and rate-limits failed attempts.
type SovereignAuth struct {
	mu       sync.RWMutex
	sessions map[string]*SovereignSession // sessionKey → session
	fails    map[string]*failRecord        // ip → fail record

	adminKey []byte
	execKey  []byte
}

// NewSovereignAuth loads plain-text keys from env and returns a ready auth manager.
// If the env vars are not set, owner auth is effectively disabled (no key matches).
func NewSovereignAuth() *SovereignAuth {
	sa := &SovereignAuth{
		sessions: make(map[string]*SovereignSession),
		fails:    make(map[string]*failRecord),
	}

	if k := strings.TrimSpace(os.Getenv("SOVEREIGN_ADMIN_KEY")); k != "" {
		sa.adminKey = []byte(k)
	}
	if k := strings.TrimSpace(os.Getenv("SOVEREIGN_EXEC_KEY")); k != "" {
		sa.execKey = []byte(k)
	}

	if len(sa.adminKey) == 0 && len(sa.execKey) == 0 {
		log.Println("[SovereignAuth] WARNING: no keys configured — owner auth disabled")
	}

	go sa.gcLoop()
	return sa
}

// Authenticate checks a raw key against stored keys using constant-time comparison.
// Returns the unlocked level (1=admin, 2=exec) or an error.
func (sa *SovereignAuth) Authenticate(rawKey, sessionKey string) (int, error) {
	sa.mu.Lock()
	defer sa.mu.Unlock()

	if sa.isLockedOut(sessionKey) {
		return 0, fmt.Errorf("too many failed attempts — try again in %s", lockoutDuration)
	}

	key := []byte(strings.TrimSpace(rawKey))

	// Check exec first (higher privilege)
	if len(sa.execKey) > 0 && subtle.ConstantTimeCompare(sa.execKey, key) == 1 {
		sa.clearFails(sessionKey)
		sa.sessions[sessionKey] = &SovereignSession{
			Level:     LevelExec,
			ExpiresAt: time.Now().Add(sessionTTL),
		}
		log.Printf("[SovereignAuth] EXEC session established for %s", sessionKey)
		return LevelExec, nil
	}

	// Check admin
	if len(sa.adminKey) > 0 && subtle.ConstantTimeCompare(sa.adminKey, key) == 1 {
		sa.clearFails(sessionKey)
		sa.sessions[sessionKey] = &SovereignSession{
			Level:     LevelAdmin,
			ExpiresAt: time.Now().Add(sessionTTL),
		}
		log.Printf("[SovereignAuth] ADMIN session established for %s", sessionKey)
		return LevelAdmin, nil
	}

	sa.recordFail(sessionKey)
	return 0, fmt.Errorf("invalid key")
}

// GetSessionLevel returns the current sovereign level for a session (0 if none/expired).
func (sa *SovereignAuth) GetSessionLevel(sessionKey string) int {
	sa.mu.RLock()
	defer sa.mu.RUnlock()

	sess, ok := sa.sessions[sessionKey]
	if !ok || time.Now().After(sess.ExpiresAt) {
		return LevelNone
	}
	return sess.Level
}

// InvalidateSession ends an owner session.
func (sa *SovereignAuth) InvalidateSession(sessionKey string) {
	sa.mu.Lock()
	defer sa.mu.Unlock()
	delete(sa.sessions, sessionKey)
	log.Printf("[SovereignAuth] Session invalidated for %s", sessionKey)
}

// ScrubKey replaces the key argument in an auth command with [REDACTED].
// Covers /admin, /exec, and the legacy /auth prefix.
func ScrubKey(message string) string {
	lower := strings.ToLower(strings.TrimSpace(message))
	if strings.HasPrefix(lower, "/admin ") {
		return "/admin [REDACTED]"
	}
	if strings.HasPrefix(lower, "/exec ") {
		return "/exec [REDACTED]"
	}
	if strings.HasPrefix(lower, "/auth ") {
		return "/auth [REDACTED]"
	}
	return message
}

// --- internal helpers ---

func (sa *SovereignAuth) isLockedOut(key string) bool {
	r, ok := sa.fails[key]
	if !ok {
		return false
	}
	if r.count >= maxFailedAttempts {
		if time.Since(r.lockedAt) < lockoutDuration {
			return true
		}
		// Lockout expired — reset
		delete(sa.fails, key)
	}
	return false
}

func (sa *SovereignAuth) recordFail(key string) {
	r, ok := sa.fails[key]
	if !ok {
		r = &failRecord{}
		sa.fails[key] = r
	}
	r.count++
	if r.count >= maxFailedAttempts {
		r.lockedAt = time.Now()
		log.Printf("[SovereignAuth] IP %s locked out after %d failed attempts", key, r.count)
	}
}

func (sa *SovereignAuth) clearFails(key string) {
	delete(sa.fails, key)
}

// gcLoop evicts expired sessions every 10 minutes.
func (sa *SovereignAuth) gcLoop() {
	ticker := time.NewTicker(10 * time.Minute)
	defer ticker.Stop()
	for range ticker.C {
		sa.mu.Lock()
		now := time.Now()
		for k, s := range sa.sessions {
			if now.After(s.ExpiresAt) {
				delete(sa.sessions, k)
			}
		}
		sa.mu.Unlock()
	}
}

// --- Context helpers ---

type sovereignContextKey struct{}

// WithSovereignLevel returns a context with the sovereign level attached.
func WithSovereignLevel(ctx context.Context, level int) context.Context {
	return context.WithValue(ctx, sovereignContextKey{}, level)
}

// GetSovereignLevel extracts the sovereign level from a context (0 if not set).
func GetSovereignLevel(ctx context.Context) int {
	if v, ok := ctx.Value(sovereignContextKey{}).(int); ok {
		return v
	}
	return LevelNone
}

// --- Key generation (called by --gen-keys CLI flag) ---

// GenerateKeyPair generates two 32-byte hex keys for SOVEREIGN_ADMIN_KEY and SOVEREIGN_EXEC_KEY.
// Returns (adminKey, execKey) — set these directly in .env.
func GenerateKeyPair() (adminKey, execKey string, err error) {
	aRaw := make([]byte, 32)
	eRaw := make([]byte, 32)

	if _, err = rand.Read(aRaw); err != nil {
		return
	}
	if _, err = rand.Read(eRaw); err != nil {
		return
	}

	adminKey = hex.EncodeToString(aRaw)
	execKey = hex.EncodeToString(eRaw)
	return
}
