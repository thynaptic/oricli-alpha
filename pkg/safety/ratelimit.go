package safety

import (
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
)

const (
	normalBurstLimit  = 60              // requests per minute under normal conditions
	blockedBurstLimit = 10              // requests per minute after first blocked attempt
	probeWindow       = 5 * time.Minute // window for probe detection
	probeCategoryHits = 3               // distinct categories in probeWindow = adversarial probe
	hardBlockDuration = 30 * time.Minute
)

// ipState tracks per-IP request and probe state.
type ipState struct {
	mu sync.Mutex

	// Token bucket
	tokens    float64
	limit     float64 // current req/min cap
	lastFill  time.Time
	wasBlocked bool

	// Probe detection: category hits within probeWindow
	probeHits map[string][]time.Time // category → timestamps

	// Hard block
	hardBlockUntil time.Time
}

func newIPState() *ipState {
	return &ipState{
		tokens:    normalBurstLimit,
		limit:     normalBurstLimit,
		lastFill:  time.Now(),
		probeHits: make(map[string][]time.Time),
	}
}

// refill adds tokens based on elapsed time (token bucket).
func (st *ipState) refill() {
	now := time.Now()
	elapsed := now.Sub(st.lastFill).Minutes()
	st.tokens += elapsed * st.limit
	if st.tokens > st.limit {
		st.tokens = st.limit
	}
	st.lastFill = now
}

// RateLimiter is a per-IP token-bucket rate limiter with probe trip-wire.
type RateLimiter struct {
	mu     sync.RWMutex
	states map[string]*ipState
}

// NewRateLimiter creates a RateLimiter and starts a background cleanup goroutine.
func NewRateLimiter() *RateLimiter {
	rl := &RateLimiter{states: make(map[string]*ipState)}
	go rl.cleanupLoop()
	return rl
}

func (rl *RateLimiter) getState(ip string) *ipState {
	rl.mu.RLock()
	st, ok := rl.states[ip]
	rl.mu.RUnlock()
	if ok {
		return st
	}
	rl.mu.Lock()
	defer rl.mu.Unlock()
	// Double-check after write lock
	if st, ok = rl.states[ip]; ok {
		return st
	}
	st = newIPState()
	rl.states[ip] = st
	return st
}

// Allow checks whether the request from ip is permitted.
// Returns (allowed bool, retryAfter duration).
func (rl *RateLimiter) Allow(ip string) (bool, time.Duration) {
	st := rl.getState(ip)
	st.mu.Lock()
	defer st.mu.Unlock()

	// Hard-block check
	if time.Now().Before(st.hardBlockUntil) {
		return false, time.Until(st.hardBlockUntil)
	}

	st.refill()
	if st.tokens < 1 {
		retryAfter := time.Duration((1-st.tokens)/st.limit*60) * time.Second
		return false, retryAfter
	}
	st.tokens--
	return true, 0
}

// RecordBlock is called when a safety gate blocks a request for ip with category.
// It drops the rate limit and accumulates probe detection state.
func (rl *RateLimiter) RecordBlock(ip, category string) {
	st := rl.getState(ip)
	st.mu.Lock()
	defer st.mu.Unlock()

	// Drop to reduced limit on first block
	if !st.wasBlocked {
		st.wasBlocked = true
		st.limit = blockedBurstLimit
		if st.tokens > blockedBurstLimit {
			st.tokens = blockedBurstLimit
		}
	}

	// Record probe hit for this category
	now := time.Now()
	st.probeHits[category] = append(st.probeHits[category], now)

	// Prune old hits outside the probe window
	cutoff := now.Add(-probeWindow)
	activeCategories := 0
	for cat, times := range st.probeHits {
		var fresh []time.Time
		for _, t := range times {
			if t.After(cutoff) {
				fresh = append(fresh, t)
			}
		}
		if len(fresh) > 0 {
			st.probeHits[cat] = fresh
			activeCategories++
		} else {
			delete(st.probeHits, cat)
		}
	}

	// Trip-wire: 3+ distinct categories within window = adversarial probe
	if activeCategories >= probeCategoryHits {
		st.hardBlockUntil = now.Add(hardBlockDuration)
	}
}

// cleanupLoop removes expired IP state entries every 10 minutes to prevent memory growth.
func (rl *RateLimiter) cleanupLoop() {
	ticker := time.NewTicker(10 * time.Minute)
	defer ticker.Stop()
	for range ticker.C {
		rl.mu.Lock()
		now := time.Now()
		for ip, st := range rl.states {
			st.mu.Lock()
			idle := now.Sub(st.lastFill) > 30*time.Minute
			hardExpired := st.hardBlockUntil.IsZero() || now.After(st.hardBlockUntil)
			if idle && hardExpired {
				delete(rl.states, ip)
			}
			st.mu.Unlock()
		}
		rl.mu.Unlock()
	}
}

// extractIP pulls the real client IP, preferring X-Real-IP and X-Forwarded-For
// since the backbone runs behind Caddy.
func extractIP(c *gin.Context) string {
	if ip := c.GetHeader("X-Real-IP"); ip != "" {
		return strings.TrimSpace(ip)
	}
	if fwd := c.GetHeader("X-Forwarded-For"); fwd != "" {
		parts := strings.SplitN(fwd, ",", 2)
		return strings.TrimSpace(parts[0])
	}
	return c.ClientIP()
}

// GinMiddleware returns a Gin handler that enforces rate limiting.
// Call RecordBlock(ip, category) from safety handlers to tighten limits.
func (rl *RateLimiter) GinMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		ip := extractIP(c)
		allowed, retryAfter := rl.Allow(ip)
		if !allowed {
			c.Header("Retry-After", retryAfter.String())
			c.AbortWithStatusJSON(http.StatusTooManyRequests, gin.H{
				"error":       "rate limit exceeded",
				"retry_after": retryAfter.Seconds(),
			})
			return
		}
		// Store IP in context so safety handlers can call RecordBlock without re-extracting
		c.Set("client_ip", ip)
		c.Next()
	}
}
