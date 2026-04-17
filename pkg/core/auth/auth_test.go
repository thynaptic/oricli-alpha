package auth

import (
	"context"
	"strings"
	"testing"
	"time"

	"github.com/thynaptic/oricli-go/pkg/core/store/memory"
)

func TestGenerateAndAuthenticateAPIKey(t *testing.T) {
	st := memory.New()
	a := NewService(st)
	tenant, err := st.CreateTenant(context.Background(), "acme")
	if err != nil {
		t.Fatal(err)
	}
	raw, _, err := a.GenerateAPIKey(context.Background(), tenant.ID, []string{"runtime:chat"}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.HasPrefix(raw, "ori.") {
		t.Fatalf("expected generated key prefix ori., got %q", raw)
	}
	ctx, err := a.Authenticate(context.Background(), "Bearer "+raw)
	if err != nil {
		t.Fatalf("expected auth success, got %v", err)
	}
	if got := TenantID(ctx); got != tenant.ID {
		t.Fatalf("expected tenant %s, got %s", tenant.ID, got)
	}
}

func TestExpiredKeyRejected(t *testing.T) {
	st := memory.New()
	a := NewService(st)
	tenant, _ := st.CreateTenant(context.Background(), "acme")
	expired := time.Now().UTC().Add(-1 * time.Minute)
	raw, _, err := a.GenerateAPIKey(context.Background(), tenant.ID, []string{"runtime:chat"}, &expired)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := a.Authenticate(context.Background(), "Bearer "+raw); err == nil {
		t.Fatal("expected key to be rejected")
	}
}

func TestRegisterAndAuthenticateLegacyGLMKey(t *testing.T) {
	st := memory.New()
	a := NewService(st)
	tenant, err := st.CreateTenant(context.Background(), "acme")
	if err != nil {
		t.Fatal(err)
	}

	legacyRaw := "glm.legacyPrefix.legacySecretKeyForCompat"
	if _, err := a.RegisterAPIKey(context.Background(), legacyRaw, tenant.ID, []string{"runtime:chat"}, nil); err != nil {
		t.Fatalf("expected legacy glm key registration to succeed, got %v", err)
	}
	if _, err := a.Authenticate(context.Background(), "Bearer "+legacyRaw); err != nil {
		t.Fatalf("expected legacy glm key authentication to succeed, got %v", err)
	}
}
