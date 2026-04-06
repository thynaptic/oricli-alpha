package service

import (
	"testing"

	"github.com/thynaptic/oricli-go/pkg/core/config"
)

func TestBrowserServiceAllowsConfiguredDomains(t *testing.T) {
	svc := NewBrowserService(config.Config{
		BrowserAutomationEnabled:     true,
		BrowserServiceBaseURL:        "http://127.0.0.1:7791",
		BrowserAllowedDomains:        []string{"example.com", "localhost"},
		BrowserRequestTimeoutSeconds: 5,
	})

	if err := svc.validateURL("https://app.example.com/dashboard"); err != nil {
		t.Fatalf("expected subdomain to be allowed, got %v", err)
	}
	if err := svc.validateURL("http://localhost:3000"); err != nil {
		t.Fatalf("expected localhost to be allowed, got %v", err)
	}
}

func TestBrowserServiceRejectsDisallowedDomains(t *testing.T) {
	svc := NewBrowserService(config.Config{
		BrowserAutomationEnabled: true,
		BrowserServiceBaseURL:    "http://127.0.0.1:7791",
		BrowserAllowedDomains:    []string{"example.com"},
	})

	if err := svc.validateURL("https://evil.test"); err == nil {
		t.Fatalf("expected disallowed domain to fail validation")
	}
}
