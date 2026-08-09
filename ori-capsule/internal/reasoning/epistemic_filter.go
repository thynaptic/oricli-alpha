package reasoning

import (
	"net/url"
	"regexp"
	"strings"
)

// FilterResult is a local quality gate for retrieved text (BM25 / URL ingest).
type FilterResult struct {
	Pass      bool    `json:"pass"`
	Relevance float64 `json:"relevance"`
	Trust     float64 `json:"trust"`
	Combined  float64 `json:"combined"`
	Reason    string  `json:"reason"`
}

var hardBlockedHosts = map[string]bool{
	"localhost": true, "127.0.0.1": true, "0.0.0.0": true,
}

var lowTrustSuffixes = []string{".xyz", ".top", ".click", ".loan"}

// EpistemicFilter scores retrieved text against a topic (no constitution file, no LLM).
func EpistemicFilter(topic, text, rawURL string) FilterResult {
	host := hostOf(rawURL)
	if hardBlockedHosts[host] {
		return FilterResult{Pass: false, Reason: "hard-blocked host"}
	}
	if strings.TrimSpace(text) == "" || len([]rune(text)) < 40 {
		return FilterResult{Pass: false, Reason: "ingestion rule: too short"}
	}
	rel := scoreRelevance(topic, text)
	trust := scoreTrust(host)
	combined := 0.55*rel + 0.45*trust
	pass := combined >= 0.35
	reason := "PASS — adequate scores"
	if !pass {
		reason = "DROP — weak relevance/trust"
	}
	return FilterResult{Pass: pass, Relevance: rel, Trust: trust, Combined: combined, Reason: reason}
}

func scoreRelevance(topic, text string) float64 {
	qTokens := epistemicTokenize(topic)
	if len(qTokens) == 0 {
		return 0.5
	}
	lead := text
	if len(lead) > 300 {
		lead = lead[:300]
	}
	leadSet := tokenSet(epistemicTokenize(lead))
	bodySet := tokenSet(epistemicTokenize(text))
	var score float64
	for _, qt := range qTokens {
		if leadSet[qt] {
			score += 2
		} else if bodySet[qt] {
			score += 1
		}
	}
	max := float64(len(qTokens)) * 2
	r := score / max
	if r > 1 {
		r = 1
	}
	return r
}

func scoreTrust(host string) float64 {
	if host == "" {
		return 0.40
	}
	for _, s := range lowTrustSuffixes {
		if strings.HasSuffix(host, s) {
			return 0.25
		}
	}
	if strings.HasSuffix(host, ".edu") || strings.HasSuffix(host, ".gov") {
		return 0.85
	}
	if strings.HasSuffix(host, ".org") {
		return 0.65
	}
	return 0.55
}

func hostOf(rawURL string) string {
	if rawURL == "" {
		return ""
	}
	parsed, err := url.Parse(rawURL)
	if err != nil {
		return ""
	}
	return strings.TrimPrefix(strings.ToLower(parsed.Hostname()), "www.")
}

func tokenSet(toks []string) map[string]bool {
	m := make(map[string]bool, len(toks))
	for _, t := range toks {
		m[t] = true
	}
	return m
}

func epistemicTokenize(s string) []string {
	raw := reSplit.Split(strings.ToLower(s), -1)
	seen := make(map[string]bool, len(raw))
	out := make([]string, 0, len(raw))
	for _, t := range raw {
		if len(t) < 3 || epistemicStop[t] || seen[t] {
			continue
		}
		seen[t] = true
		out = append(out, t)
	}
	return out
}

var reSplit = regexp.MustCompile(`[^a-z0-9]+`)

var epistemicStop = map[string]bool{
	"the": true, "and": true, "for": true, "are": true, "but": true,
	"not": true, "you": true, "all": true, "can": true, "has": true,
	"her": true, "was": true, "one": true, "our": true, "out": true,
	"she": true, "get": true, "his": true, "how": true, "its": true,
	"may": true, "now": true, "own": true, "say": true, "too": true,
	"use": true, "way": true, "who": true, "did": true, "had": true,
	"him": true, "let": true, "old": true, "see": true, "two": true,
	"why": true, "ask": true,
}
