package rag

import (
	"fmt"
	"net"
	"net/url"
	"strings"
)

// ValidateFetchURL rejects obviously unsafe fetch targets (local SSRF guard).
// This is not urlscan.io — no API key, pure policy for capsule ingest.
func ValidateFetchURL(raw string) error {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return fmt.Errorf("url required")
	}
	u, err := url.Parse(raw)
	if err != nil {
		return fmt.Errorf("invalid url: %w", err)
	}
	scheme := strings.ToLower(u.Scheme)
	if scheme != "http" && scheme != "https" {
		return fmt.Errorf("scheme %q not allowed (want http/https)", scheme)
	}
	host := strings.ToLower(u.Hostname())
	if host == "" {
		return fmt.Errorf("missing host")
	}
	if host == "localhost" || strings.HasSuffix(host, ".localhost") || host == "metadata.google.internal" {
		return fmt.Errorf("host %q blocked", host)
	}
	if ip := net.ParseIP(host); ip != nil {
		if ip.IsLoopback() || ip.IsPrivate() || ip.IsLinkLocalUnicast() || ip.IsLinkLocalMulticast() || ip.IsUnspecified() {
			return fmt.Errorf("ip %s blocked", ip)
		}
	}
	return nil
}
