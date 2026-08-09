package safety

import (
	"regexp"
	"strings"
)

// RagContentGuard scans externally-fetched content (web scrapes, SearXNG results,
// ingest payloads) for hidden prompt injection instructions before they enter context.
type RagContentGuard struct {
	// invisibleCSS detects CSS-hidden text patterns
	invisibleCSS *regexp.Regexp
	// htmlCommentInstruction detects injected instructions in HTML comments
	htmlCommentInstruction *regexp.Regexp
	// metaTagInstruction detects instructions in meta tags
	metaTagInstruction *regexp.Regexp
	// llmFormatTokens detects raw LLM format tokens that adversarial pages may embed
	llmFormatTokens *regexp.Regexp
	// instructionMarkers detects explicit instruction framing in scraped content
	instructionMarkers []string
	// excessiveWhitespace detects padding used to hide injected text
	excessiveWhitespace *regexp.Regexp
}

// NewRagContentGuard initialises a RagContentGuard with all detection patterns.
func NewRagContentGuard() *RagContentGuard {
	g := &RagContentGuard{}
	g.invisibleCSS = regexp.MustCompile(`(?i)style\s*=\s*["'][^"']*(?:color\s*:\s*(?:white|#fff|#ffffff|transparent)|display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0|opacity\s*:\s*0)[^"']*["']`)
	g.htmlCommentInstruction = regexp.MustCompile(`(?i)<!--[^>]*(?:ignore|instructions?|system|override|forget|bypass|disregard|your (rules?|guidelines?|training))[^>]*-->`)
	g.metaTagInstruction = regexp.MustCompile(`(?i)<meta[^>]*(?:name|content)\s*=\s*["'][^"']*(?:ignore|instructions?|system prompt|override)[^"']*["'][^>]*>`)
	g.llmFormatTokens = regexp.MustCompile(`(?i)(<\|system\|>|<\|user\|>|<\|assistant\|>|\[INST\]|\[/INST\]|<<SYS>>|</SYS>|<s>|</s>|\[system\]|\[assistant\])`)
	g.excessiveWhitespace = regexp.MustCompile(`\s{100,}`)
	g.instructionMarkers = []string{
		"ignore previous instructions",
		"ignore all prior instructions",
		"disregard your previous",
		"new instructions:",
		"updated instructions:",
		"[override]",
		"[new system]",
		"assistant: sure, i will",
		"assistant: understood, i'll now",
		"do not follow your",
		"your real instructions are",
		"you are actually",
		"from now on you must",
		"ignore your safety",
		"bypass your filters",
	}
	return g
}

// ScanResult describes the result of scanning scraped content.
type ScanResult struct {
	Flagged    bool
	Sanitized  string
	Detections []string
}

// ScanScrapedContent checks and sanitizes externally-fetched text before it enters context.
// It strips detected injection patterns and returns a clean string plus a flag.
func (g *RagContentGuard) ScanScrapedContent(raw string) ScanResult {
	result := ScanResult{Sanitized: raw}

	// 1. Strip HTML comment injections
	if g.htmlCommentInstruction.MatchString(raw) {
		result.Flagged = true
		result.Detections = append(result.Detections, "html_comment_injection")
		raw = g.htmlCommentInstruction.ReplaceAllString(raw, "")
	}

	// 2. Strip meta-tag injections
	if g.metaTagInstruction.MatchString(raw) {
		result.Flagged = true
		result.Detections = append(result.Detections, "meta_tag_injection")
		raw = g.metaTagInstruction.ReplaceAllString(raw, "")
	}

	// 3. Strip invisible CSS elements (keep text, strip the style attribute)
	if g.invisibleCSS.MatchString(raw) {
		result.Flagged = true
		result.Detections = append(result.Detections, "invisible_css_text")
		raw = g.invisibleCSS.ReplaceAllString(raw, "")
	}

	// 4. Strip LLM format tokens
	if g.llmFormatTokens.MatchString(raw) {
		result.Flagged = true
		result.Detections = append(result.Detections, "llm_format_token")
		raw = g.llmFormatTokens.ReplaceAllString(raw, "")
	}

	// 5. Collapse excessive whitespace (used to pad/hide injected text)
	if g.excessiveWhitespace.MatchString(raw) {
		result.Flagged = true
		result.Detections = append(result.Detections, "whitespace_padding")
		raw = g.excessiveWhitespace.ReplaceAllString(raw, " ")
	}

	// 6. Check for explicit instruction markers in plain text
	lower := strings.ToLower(raw)
	for _, marker := range g.instructionMarkers {
		if strings.Contains(lower, marker) {
			result.Flagged = true
			result.Detections = append(result.Detections, "instruction_marker:"+marker)
			// Replace the offending sentence/line
			raw = redactLine(raw, marker)
		}
	}

	result.Sanitized = strings.TrimSpace(raw)
	return result
}

// redactLine replaces the line(s) in text that contain the trigger phrase with a placeholder.
func redactLine(text, trigger string) string {
	lines := strings.Split(text, "\n")
	lowerTrigger := strings.ToLower(trigger)
	var out []string
	for _, line := range lines {
		if strings.Contains(strings.ToLower(line), lowerTrigger) {
			out = append(out, "[content removed: external injection attempt]")
		} else {
			out = append(out, line)
		}
	}
	return strings.Join(out, "\n")
}
