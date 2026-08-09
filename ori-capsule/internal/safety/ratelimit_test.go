package safety

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
)

func init() {
	gin.SetMode(gin.TestMode)
}

// ─── Normal requests allowed ──────────────────────────────────────────────────

func TestRateLimiter_NormalRequests_Allowed(t *testing.T) {
	rl := NewRateLimiter()
	for i := 0; i < 10; i++ {
		allowed, _ := rl.Allow("192.168.1.1")
		if !allowed {
			t.Errorf("request %d should be allowed, was blocked", i+1)
		}
	}
}

// ─── Rate exceeded after burst ────────────────────────────────────────────────

func TestRateLimiter_RateExceeded_Blocked(t *testing.T) {
	rl := NewRateLimiter()
	ip := "10.0.0.1"
	// Drain the entire bucket
	for i := 0; i < int(normalBurstLimit); i++ {
		rl.Allow(ip)
	}
	// Next request should be blocked
	allowed, retryAfter := rl.Allow(ip)
	if allowed {
		t.Error("request after limit exhaustion should be blocked")
	}
	if retryAfter <= 0 {
		t.Error("retryAfter should be positive when blocked")
	}
}

// ─── Blocked session drops to reduced limit ───────────────────────────────────

func TestRateLimiter_AfterBlock_LimitDrops(t *testing.T) {
	rl := NewRateLimiter()
	ip := "10.0.0.2"
	// Record a safety block — drops limit to blockedBurstLimit
	rl.RecordBlock(ip, "injection")
	// New limit should be blockedBurstLimit (10)
	st := rl.getState(ip)
	st.mu.Lock()
	limit := st.limit
	st.mu.Unlock()
	if limit != blockedBurstLimit {
		t.Errorf("expected limit to drop to %d after block, got %f", blockedBurstLimit, limit)
	}
}

// ─── Probe trip-wire activation ───────────────────────────────────────────────

func TestRateLimiter_ProbeTripWire_HardBlocks(t *testing.T) {
	rl := NewRateLimiter()
	ip := "10.0.0.3"
	// Hit 3 distinct safety categories within probe window
	rl.RecordBlock(ip, "injection")
	rl.RecordBlock(ip, "disclosure")
	rl.RecordBlock(ip, "web_injection")
	// Should now be hard-blocked
	allowed, _ := rl.Allow(ip)
	if allowed {
		t.Error("IP hitting 3 distinct safety categories should be hard-blocked")
	}
}

func TestRateLimiter_TwoCategories_NotHardBlocked(t *testing.T) {
	rl := NewRateLimiter()
	ip := "10.0.0.4"
	// Only 2 distinct categories — not enough for trip-wire
	rl.RecordBlock(ip, "injection")
	rl.RecordBlock(ip, "disclosure")
	// Should not be hard-blocked (only 2 categories, need 3)
	allowed, _ := rl.Allow(ip)
	if !allowed {
		t.Error("IP with only 2 categories should not be hard-blocked")
	}
}

// ─── IP isolation ─────────────────────────────────────────────────────────────

func TestRateLimiter_DifferentIPs_Independent(t *testing.T) {
	rl := NewRateLimiter()
	// Exhaust ip-A
	for i := 0; i < int(normalBurstLimit); i++ {
		rl.Allow("10.1.1.1")
	}
	// ip-B should be unaffected
	allowed, _ := rl.Allow("10.1.1.2")
	if !allowed {
		t.Error("different IP should not be rate-limited by another IP's exhaustion")
	}
}

// ─── Hard block retry-after header ───────────────────────────────────────────

func TestRateLimiter_HardBlock_ReturnsRetryAfter(t *testing.T) {
	rl := NewRateLimiter()
	ip := "10.0.0.5"
	rl.RecordBlock(ip, "injection")
	rl.RecordBlock(ip, "disclosure")
	rl.RecordBlock(ip, "web_injection")

	_, retryAfter := rl.Allow(ip)
	if retryAfter <= 0 {
		t.Error("hard-blocked IP should return positive retryAfter")
	}
	if retryAfter > hardBlockDuration+time.Second {
		t.Errorf("retryAfter exceeds hard block duration: %v", retryAfter)
	}
}

// ─── Gin middleware integration ───────────────────────────────────────────────

func TestRateLimiter_GinMiddleware_AllowsNormal(t *testing.T) {
	rl := NewRateLimiter()
	router := gin.New()
	router.Use(rl.GinMiddleware())
	router.GET("/test", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	req, _ := http.NewRequest(http.MethodGet, "/test", nil)
	req.Header.Set("X-Real-IP", "192.168.100.1")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", w.Code)
	}
}

func TestRateLimiter_GinMiddleware_BlocksExhausted(t *testing.T) {
	rl := NewRateLimiter()
	ip := "192.168.200.1"
	// Drain bucket via Allow calls
	for i := 0; i < int(normalBurstLimit); i++ {
		rl.Allow(ip)
	}

	router := gin.New()
	router.Use(rl.GinMiddleware())
	router.GET("/test", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	req, _ := http.NewRequest(http.MethodGet, "/test", nil)
	req.Header.Set("X-Real-IP", ip)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusTooManyRequests {
		t.Errorf("expected 429, got %d", w.Code)
	}
}

// ─── extractIP helper ─────────────────────────────────────────────────────────

func TestExtractIP_XRealIP(t *testing.T) {
	gin.SetMode(gin.TestMode)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("GET", "/", nil)
	c.Request.Header.Set("X-Real-IP", "203.0.113.1")
	ip := extractIP(c)
	if ip != "203.0.113.1" {
		t.Errorf("expected 203.0.113.1, got %q", ip)
	}
}

func TestExtractIP_XForwardedFor(t *testing.T) {
	gin.SetMode(gin.TestMode)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request, _ = http.NewRequest("GET", "/", nil)
	c.Request.Header.Set("X-Forwarded-For", "203.0.113.2, 10.0.0.1")
	ip := extractIP(c)
	if ip != "203.0.113.2" {
		t.Errorf("expected first IP from X-Forwarded-For (203.0.113.2), got %q", ip)
	}
}
