// Package auth provides tenant-aware context enrichment for the Sovereign API.
// It runs after the core auth.Service validates the Bearer token and injects
// the tenant's CognitivePolicy + Quota into the Gin request context so
// downstream handlers can enforce per-tenant limits without hitting the store again.
package auth

import (
	"context"
	"log"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	coreauth "github.com/thynaptic/oricli-go/pkg/core/auth"
	"github.com/thynaptic/oricli-go/pkg/core/model"
	"github.com/thynaptic/oricli-go/pkg/core/store"
)

type contextKey string

const (
	ctxCognitivePolicy contextKey = "cognitive_policy"
	ctxQuota           contextKey = "quota"
)

// TenantEnricher returns a Gin middleware that looks up the authenticated
// tenant's CognitivePolicy and Quota from the store and injects them into
// the request context. Designed to run immediately after authMiddleware.
// Soft failure: if the policy or quota is not found, the request proceeds
// with nil values — callers must treat nil as "unrestricted".
func TenantEnricher(st store.Store) gin.HandlerFunc {
	return func(c *gin.Context) {
		tenantID := coreauth.TenantID(c.Request.Context())
		if tenantID == "" {
			c.Next()
			return
		}

		ctx, cancel := context.WithTimeout(c.Request.Context(), 3*time.Second)
		defer cancel()

		// Fetch CognitivePolicy — gates reasoning mode access + tool allowlist.
		policy, err := st.GetCognitivePolicy(ctx, tenantID)
		if err != nil {
			log.Printf("[TenantEnricher] CognitivePolicy lookup for %q: %v", tenantID, err)
		} else {
			ctx = context.WithValue(ctx, ctxCognitivePolicy, &policy)
		}

		// Fetch Quota — gates RPM/TPM limits per tenant.
		quota, err := st.GetQuota(ctx, tenantID)
		if err != nil {
			log.Printf("[TenantEnricher] Quota lookup for %q: %v", tenantID, err)
		} else {
			ctx = context.WithValue(ctx, ctxQuota, &quota)
		}

		c.Request = c.Request.WithContext(ctx)
		c.Next()
	}
}

// CognitivePolicy returns the tenant's CognitivePolicy from context, or nil.
func CognitivePolicy(ctx context.Context) *model.CognitivePolicy {
	v, _ := ctx.Value(ctxCognitivePolicy).(*model.CognitivePolicy)
	return v
}

// Quota returns the tenant's Quota from context, or nil.
func Quota(ctx context.Context) *model.Quota {
	v, _ := ctx.Value(ctxQuota).(*model.Quota)
	return v
}

// ReasoningModeAllowed checks whether the given mode string is permitted by the
// tenant's CognitivePolicy. Returns true if:
//   - Policy is nil (no restriction configured)
//   - AllowedReasoningModes is empty (allow all)
//   - The mode string appears in AllowedReasoningModes
func ReasoningModeAllowed(ctx context.Context, mode string) bool {
	policy := CognitivePolicy(ctx)
	if policy == nil || len(policy.AllowedReasoningModes) == 0 {
		return true
	}
	for _, m := range policy.AllowedReasoningModes {
		if m == mode || m == "*" {
			return true
		}
	}
	return false
}

// TenantID re-exports the core auth.TenantID helper so callers only need
// to import this package.
func TenantID(ctx context.Context) string {
	return coreauth.TenantID(ctx)
}

// AdminOnly is a Gin middleware that restricts a route to keys with the "admin" scope.
// The owner seed key is registered with this scope; per-tenant keys are not.
// Returns 403 for any key missing the "admin" scope.
func AdminOnly() gin.HandlerFunc {
	return func(c *gin.Context) {
		if err := coreauth.RequireScope(c.Request.Context(), "admin"); err != nil {
			c.AbortWithStatusJSON(http.StatusForbidden, gin.H{
				"error": "admin routes require a key with 'admin' scope",
			})
			return
		}
		c.Next()
	}
}
