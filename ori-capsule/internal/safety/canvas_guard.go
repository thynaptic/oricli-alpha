package safety

import (
	"regexp"
	"strings"
)

// CanvasGuard applies stricter output scanning for canvas/artifact rendering requests.
// Canvas mode produces HTML, JSX, or rich code outputs that may be rendered directly
// in the UI — a much higher-risk surface than prose responses.
type CanvasGuard struct {
	// Dangerous JS patterns even when inside code
	dangerousJSPatterns []*regexp.Regexp
	// Script tag patterns
	scriptTagRe *regexp.Regexp
	// Event handler attributes
	eventHandlerRe *regexp.Regexp
	// External resource patterns (non-allowlisted)
	externalResourceRe *regexp.Regexp
	// Dangerous HTML meta/base patterns
	dangerousHTMLRe *regexp.Regexp
	// Allowed CDN domains for external resources
	allowedDomains []string
}

// NewCanvasGuard initialises the CanvasGuard with all patterns.
func NewCanvasGuard() *CanvasGuard {
	g := &CanvasGuard{
		allowedDomains: []string{
			"cdn.jsdelivr.net",
			"unpkg.com",
			"cdnjs.cloudflare.com",
			"fonts.googleapis.com",
			"fonts.gstatic.com",
		},
	}

	g.scriptTagRe = regexp.MustCompile(`(?i)<script[^>]*>[\s\S]*?</script>`)
	g.eventHandlerRe = regexp.MustCompile(`(?i)\s+on\w+\s*=\s*["'][^"']*["']`)
	g.externalResourceRe = regexp.MustCompile(`(?i)(?:src|href|action|data|formaction)\s*=\s*["'](https?://[^"']+)["']`)
	g.dangerousHTMLRe = regexp.MustCompile(`(?i)<(?:meta\s+http-equiv\s*=\s*["']refresh["']|base\s+href)`)

	g.dangerousJSPatterns = []*regexp.Regexp{
		regexp.MustCompile(`(?i)document\.cookie`),
		regexp.MustCompile(`(?i)localStorage\s*[\[.]`),
		regexp.MustCompile(`(?i)sessionStorage\s*[\[.]`),
		regexp.MustCompile(`(?i)window\.location\s*=`),
		regexp.MustCompile(`(?i)window\.location\.(?:href|replace|assign)\s*=`),
		regexp.MustCompile(`(?i)eval\s*\(`),
		regexp.MustCompile(`(?i)Function\s*\(\s*["']`),
		regexp.MustCompile(`(?i)XMLHttpRequest`),
		regexp.MustCompile(`(?i)fetch\s*\(\s*["']https?://`),
		regexp.MustCompile(`(?i)navigator\.sendBeacon`),
		regexp.MustCompile(`(?i)new\s+WebSocket\s*\(`),
		regexp.MustCompile(`(?i)import\s*\(\s*["']https?://`),
		regexp.MustCompile(`(?i)__proto__\s*\[`),
		regexp.MustCompile(`(?i)prototype\s*\[`),
	}

	return g
}

// CanvasResult is the result of a canvas output scan.
type CanvasResult struct {
	Blocked      bool
	Sanitized    string
	Violations   []string
	CSPHeader    string
}

// ScanOutput runs canvas-mode output hardening on the generated content.
// It sanitizes or blocks depending on severity of violations found.
func (g *CanvasGuard) ScanOutput(output string) CanvasResult {
	result := CanvasResult{Sanitized: output}
	sanitized := output

	// 1. Strip <script> blocks entirely — canvas should not need inline scripts
	if g.scriptTagRe.MatchString(sanitized) {
		result.Violations = append(result.Violations, "inline_script_tag")
		sanitized = g.scriptTagRe.ReplaceAllString(sanitized, "<!-- [script removed by CanvasGuard] -->")
	}

	// 2. Strip event handler attributes (onclick, onload, onerror, etc.)
	if g.eventHandlerRe.MatchString(sanitized) {
		result.Violations = append(result.Violations, "event_handler_attr")
		sanitized = g.eventHandlerRe.ReplaceAllString(sanitized, "")
	}

	// 3. Check external resource URLs against allowlist
	sanitized = g.externalResourceRe.ReplaceAllStringFunc(sanitized, func(match string) string {
		urlMatch := g.externalResourceRe.FindStringSubmatch(match)
		if len(urlMatch) < 2 {
			return match
		}
		url := urlMatch[1]
		if g.isAllowedDomain(url) {
			return match
		}
		result.Violations = append(result.Violations, "external_resource:"+url)
		return strings.Replace(match, urlMatch[1], "#[blocked-external-resource]", 1)
	})

	// 4. Block dangerous HTML (meta refresh, base href redirect)
	if g.dangerousHTMLRe.MatchString(sanitized) {
		result.Violations = append(result.Violations, "dangerous_html_redirect")
		sanitized = g.dangerousHTMLRe.ReplaceAllString(sanitized, "<!-- [dangerous HTML removed] -->")
	}

	// 5. Scan for dangerous JS patterns in the full output (prose + code)
	// Canvas guard is intentionally stricter — we DO check inside code blocks here
	// because canvas output may be rendered directly.
	for _, re := range g.dangerousJSPatterns {
		if re.MatchString(sanitized) {
			patternName := extractPatternName(re.String())
			result.Violations = append(result.Violations, "dangerous_js:"+patternName)
			// For JS violations we block rather than sanitize — too risky to partial-fix
			result.Blocked = true
		}
	}

	if result.Blocked {
		result.Sanitized = "[Canvas output blocked: dangerous JavaScript pattern detected. Please rephrase without DOM manipulation, cookie access, or external network calls.]"
	} else {
		result.Sanitized = sanitized
	}

	// 6. Suggest CSP header for the UI to apply when rendering
	result.CSPHeader = "default-src 'self'; script-src 'none'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'none';"

	return result
}

// isAllowedDomain checks whether a URL's host is in the allowed CDN list.
func (g *CanvasGuard) isAllowedDomain(url string) bool {
	for _, domain := range g.allowedDomains {
		if strings.Contains(url, domain) {
			return true
		}
	}
	return false
}

// extractPatternName pulls a readable name from a regex string for violation logging.
func extractPatternName(pattern string) string {
	clean := regexp.MustCompile(`[()\\s?.+*\[\]{}|^$]`).ReplaceAllString(pattern, "")
	clean = strings.TrimPrefix(clean, "(?i)")
	if len(clean) > 30 {
		return clean[:30]
	}
	return clean
}
