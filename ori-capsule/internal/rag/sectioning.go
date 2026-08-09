// Package rag is the consumer capsule RAG stack: structural helpers + BM25-only
// local retrieval. No chromem, PocketBase, or sync embeds on the chat path.
package rag

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

var markdownHeadingPattern = regexp.MustCompile(`^(#{1,6})\s+(.+?)\s*$`)

// SectionMeta describes the heading context for a text chunk.
type SectionMeta struct {
	ID       string
	Title    string
	Level    int
	Inferred bool
}

// InferChunkSections assigns section titles/ids from markdown headings.
func InferChunkSections(chunks []string, sourceRef string) []SectionMeta {
	out := make([]SectionMeta, 0, len(chunks))
	currentTitle := "General"
	currentLevel := 0
	ordinal := 1
	for i, chunk := range chunks {
		foundTitle, foundLevel, explicit := headingFromChunk(chunk)
		if explicit {
			if i > 0 {
				ordinal++
			}
			currentTitle = foundTitle
			currentLevel = foundLevel
		}
		id := fmt.Sprintf("%s::section-%d", strings.TrimSpace(sourceRef), ordinal)
		out = append(out, SectionMeta{
			ID:       id,
			Title:    truncateSectionMeta(currentTitle, 120),
			Level:    currentLevel,
			Inferred: !explicit,
		})
	}
	return out
}

func headingFromChunk(chunk string) (string, int, bool) {
	lines := strings.Split(strings.TrimSpace(chunk), "\n")
	for _, line := range lines {
		clean := strings.TrimSpace(line)
		if clean == "" {
			continue
		}
		if m := markdownHeadingPattern.FindStringSubmatch(clean); len(m) == 3 {
			return truncateSectionMeta(strings.TrimSpace(m[2]), 120), len(m[1]), true
		}
		lower := strings.ToLower(clean)
		if strings.HasPrefix(lower, "section:") {
			title := strings.TrimSpace(clean[len("section:"):])
			if title != "" {
				return truncateSectionMeta(title, 120), 1, true
			}
		}
		break
	}
	return "", 0, false
}

// SectionMetaStrings returns string fields for storage/metadata maps.
func SectionMetaStrings(m SectionMeta) (id, title, level, inferred string) {
	id = strings.TrimSpace(m.ID)
	title = strings.TrimSpace(m.Title)
	if title == "" {
		title = "General"
	}
	level = strconv.Itoa(m.Level)
	inferred = "true"
	if !m.Inferred {
		inferred = "false"
	}
	return id, title, level, inferred
}

func truncateSectionMeta(s string, n int) string {
	s = strings.TrimSpace(s)
	if len(s) <= n {
		return s
	}
	if n < 4 {
		return s[:n]
	}
	return s[:n-3] + "..."
}

// ChunkText splits text into overlapping character windows.
func ChunkText(text string, maxChars, overlap int) []string {
	text = strings.TrimSpace(text)
	if text == "" {
		return nil
	}
	if maxChars <= 0 {
		maxChars = 1200
	}
	if overlap < 0 {
		overlap = 0
	}
	if overlap >= maxChars {
		overlap = maxChars / 4
	}
	runes := []rune(text)
	if len(runes) <= maxChars {
		return []string{string(runes)}
	}
	var out []string
	step := maxChars - overlap
	for i := 0; i < len(runes); i += step {
		end := i + maxChars
		if end > len(runes) {
			end = len(runes)
		}
		out = append(out, strings.TrimSpace(string(runes[i:end])))
		if end == len(runes) {
			break
		}
	}
	return out
}
