package vdi

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/chromedp/chromedp"
)

// PageContext is Oricli's structured understanding of a web page.
// Instead of a flat wall of text, she receives the semantic skeleton:
// title, hierarchy of headings, main content, and key links.
type PageContext struct {
	URL             string
	Title           string
	MetaDescription string
	H1s             []string
	H2s             []string
	H3s             []string
	MainContent     string
	Links           []PageLink
	ImageAlts       []string
	HasDataTables   bool
}

// PageLink is a meaningful hyperlink extracted from the page.
type PageLink struct {
	Text string
	Href string
}

// FormatAsContext renders PageContext into a compact structured markdown
// that an LLM can parse without noise. This is what Oricli "sees".
func (p *PageContext) FormatAsContext(maxContentChars int) string {
	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("URL: %s\n", p.URL))
	if p.Title != "" {
		sb.WriteString(fmt.Sprintf("TITLE: %s\n", p.Title))
	}
	if p.MetaDescription != "" {
		sb.WriteString(fmt.Sprintf("DESCRIPTION: %s\n", p.MetaDescription))
	}

	if len(p.H1s) > 0 {
		sb.WriteString(fmt.Sprintf("# %s\n", strings.Join(p.H1s, " | ")))
	}
	for _, h := range p.H2s {
		sb.WriteString(fmt.Sprintf("## %s\n", h))
	}
	for _, h := range p.H3s {
		sb.WriteString(fmt.Sprintf("### %s\n", h))
	}

	if p.MainContent != "" {
		content := p.MainContent
		if maxContentChars > 0 && len(content) > maxContentChars {
			content = content[:maxContentChars] + "… [truncated]"
		}
		sb.WriteString("\nCONTENT:\n")
		sb.WriteString(content)
		sb.WriteString("\n")
	}

	if len(p.Links) > 0 {
		sb.WriteString("\nKEY LINKS:\n")
		for _, l := range p.Links {
			sb.WriteString(fmt.Sprintf("- [%s](%s)\n", l.Text, l.Href))
		}
	}

	if p.HasDataTables {
		sb.WriteString("\n[Page contains data tables]\n")
	}

	return strings.TrimSpace(sb.String())
}

// domExtractionScript is injected into the live page via chromedp to pull
// structured semantic data before Chromium's JS engine collapses it to text.
// It strips noise (nav/ads/cookie banners) first, then extracts the hierarchy.
const domExtractionScript = `(function() {
  // Strip noise elements
  var noise = ['script','style','nav','header','footer','aside','form',
    'iframe','noscript','[role="banner"]','[role="navigation"]',
    '[aria-label="advertisement"]','.cookie-banner','.ad','.ads','#cookie-notice'];
  noise.forEach(function(sel) {
    document.querySelectorAll(sel).forEach(function(el) { el.remove(); });
  });

  function text(el) { return el ? el.innerText.trim().replace(/\s+/g,' ') : ''; }
  function texts(sel, limit) {
    return Array.from(document.querySelectorAll(sel))
      .map(function(e) { return text(e); })
      .filter(function(t) { return t.length > 2; })
      .slice(0, limit);
  }

  // Best content container
  var contentEl = document.querySelector('article') ||
                  document.querySelector('main') ||
                  document.querySelector('[role="main"]') ||
                  document.querySelector('.content') ||
                  document.querySelector('#content') ||
                  document.querySelector('.post-content') ||
                  document.querySelector('.entry-content') ||
                  document.body;

  var links = Array.from(document.querySelectorAll('a[href]'))
    .map(function(a) { return {text: a.innerText.trim(), href: a.href}; })
    .filter(function(l) { return l.text.length > 2 && l.href.startsWith('http') && !l.href.includes('javascript'); })
    .slice(0, 12);

  var imageAlts = Array.from(document.querySelectorAll('img[alt]'))
    .map(function(img) { return img.alt.trim(); })
    .filter(function(a) { return a.length > 3; })
    .slice(0, 8);

  return JSON.stringify({
    title:       document.title,
    meta:        (document.querySelector('meta[name="description"]') || {}).content || '',
    h1s:         texts('h1', 3),
    h2s:         texts('h2', 8),
    h3s:         texts('h3', 10),
    mainContent: text(contentEl).slice(0, 4000),
    links:       links,
    imageAlts:   imageAlts,
    hasTables:   document.querySelectorAll('table').length > 0,
  });
})()`

// NavigateAndExtractDOM navigates to a URL, injects the DOM extraction script,
// and returns a structured PageContext — Oricli's semantic view of the page.
func (m *Manager) NavigateAndExtractDOM(rawURL string, maxContentChars int) (*PageContext, error) {
	ctx, cancel := m.GetBrowserContext(18 * time.Second)
	if ctx == nil {
		return nil, fmt.Errorf("VDI browser not initialised")
	}
	defer cancel()

	if err := chromedp.Run(ctx,
		chromedp.Navigate(rawURL),
		chromedp.WaitVisible("body", chromedp.ByQuery),
	); err != nil {
		return nil, fmt.Errorf("navigation failed for %s: %v", rawURL, err)
	}

	var jsonResult string
	if err := chromedp.Run(ctx, chromedp.Evaluate(domExtractionScript, &jsonResult)); err != nil {
		return nil, fmt.Errorf("DOM extraction script failed: %v", err)
	}

	var raw struct {
		Title       string              `json:"title"`
		Meta        string              `json:"meta"`
		H1s         []string            `json:"h1s"`
		H2s         []string            `json:"h2s"`
		H3s         []string            `json:"h3s"`
		MainContent string              `json:"mainContent"`
		Links       []map[string]string `json:"links"`
		ImageAlts   []string            `json:"imageAlts"`
		HasTables   bool                `json:"hasTables"`
	}
	if err := json.Unmarshal([]byte(jsonResult), &raw); err != nil {
		return nil, fmt.Errorf("failed to parse DOM result: %v", err)
	}

	pc := &PageContext{
		URL:             rawURL,
		Title:           raw.Title,
		MetaDescription: raw.Meta,
		H1s:             raw.H1s,
		H2s:             raw.H2s,
		H3s:             raw.H3s,
		MainContent:     raw.MainContent,
		ImageAlts:       raw.ImageAlts,
		HasDataTables:   raw.HasTables,
	}
	for _, l := range raw.Links {
		pc.Links = append(pc.Links, PageLink{Text: l["text"], Href: l["href"]})
	}

	if maxContentChars > 0 && len(pc.MainContent) > maxContentChars {
		pc.MainContent = pc.MainContent[:maxContentChars] + "… [truncated]"
	}

	return pc, nil
}
