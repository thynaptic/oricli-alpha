package memory

import (
	"regexp"
	"strings"
)

// --- Pillar 30: Autonomous Knowledge Extraction ---
// Ported from Aurora's COGSEntityExtractor and COGSRelationshipExtractor.
// Implements heuristic NLP for self-building session graphs.

type ExtractedEntity struct {
	Label      string
	Type       EntityType
	Confidence float64
}

type ExtractedLink struct {
	Source     string
	Target     string
	Type       string
	Confidence float64
}

type ExtractorEngine struct {
	EntityRegex map[EntityType]*regexp.Regexp
	LinkRegex   []*regexp.Regexp
}

func NewExtractorEngine() *ExtractorEngine {
	e := &ExtractorEngine{
		EntityRegex: make(map[EntityType]*regexp.Regexp),
	}
	e.loadPatterns()
	return e
}

func (e *ExtractorEngine) loadPatterns() {
	// Entity Patterns (Ported from Swift)
	e.EntityRegex[TypePerson] = regexp.MustCompile(`\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b`)
	e.EntityRegex[TypePlace] = regexp.MustCompile(`\b(in|at|from|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b`)
	e.EntityRegex[TypeConcept] = regexp.MustCompile(`\b(concept|idea|theory|principle)\s+of\s+([a-z]+(?:\s+[a-z]+)*)\b`)
	e.EntityRegex[TypeAction] = regexp.MustCompile(`\b(want|need|intend|plan|goal)\s+to\s+([a-z]+(?:\s+[a-z]+)*)\b`)

	// Link Patterns (Ported from Swift)
	e.LinkRegex = append(e.LinkRegex, regexp.MustCompile(`\b([A-Za-z]+)\s+is\s+(related|connected|linked)\s+to\s+([A-Za-z]+)\b`))
	e.LinkRegex = append(e.LinkRegex, regexp.MustCompile(`\b([A-Za-z]+)\s+(causes|leads to|results in)\s+([A-Za-z]+)\b`))
	e.LinkRegex = append(e.LinkRegex, regexp.MustCompile(`\b([A-Za-z]+)\s+is\s+part\s+of\s+([A-Za-z]+)\b`))
}

// ExtractEntities finds potential context objects in text.
func (e *ExtractorEngine) ExtractEntities(text string) []ExtractedEntity {
	var results []ExtractedEntity
	for eType, re := range e.EntityRegex {
		matches := re.FindAllStringSubmatch(text, -1)
		for _, m := range matches {
			label := m[0]
			if eType == TypePlace || eType == TypeConcept || eType == TypeAction {
				if len(m) > 2 {
					label = m[2]
				}
			}
			
			if isCommonWord(label) {
				continue
			}

			results = append(results, ExtractedEntity{
				Label:      label,
				Type:       eType,
				Confidence: 0.6,
			})
		}
	}
	return results
}

// ExtractLinks finds potential relationships between entities.
func (e *ExtractorEngine) ExtractLinks(text string) []ExtractedLink {
	var results []ExtractedLink
	for _, re := range e.LinkRegex {
		matches := re.FindAllStringSubmatch(text, -1)
		for _, m := range matches {
			if len(m) >= 4 {
				results = append(results, ExtractedLink{
					Source:     m[1],
					Target:     m[3],
					Type:       m[2],
					Confidence: 0.7,
				})
			}
		}
	}
	return results
}

// HydrateGraph runs extraction and populates the provided working memory graph.
func (e *ExtractorEngine) HydrateGraph(text string, g *WorkingMemoryGraph, valence, arousal, eri float32) {
	entities := e.ExtractEntities(text)
	labelToID := make(map[string]string)

	for _, ent := range entities {
		entity := g.AddEntity(ent.Label, ent.Type, "Extracted from session stream", valence, arousal, eri)
		labelToID[strings.ToLower(ent.Label)] = entity.ID
	}

	links := e.ExtractLinks(text)
	for _, l := range links {
		sourceID, ok1 := labelToID[strings.ToLower(l.Source)]
		targetID, ok2 := labelToID[strings.ToLower(l.Target)]
		if ok1 && ok2 {
			g.AddRelationship(sourceID, targetID, l.Type, l.Confidence, valence, arousal, eri)
		}
	}
}

func isCommonWord(word string) bool {
	common := map[string]bool{
		"the": true, "a": true, "an": true, "and": true, "but": true, "or": true,
		"in": true, "on": true, "at": true, "to": true, "for": true, "of": true,
		"with": true, "by": true, "from": true, "is": true, "was": true, "are": true,
	}
	return common[strings.ToLower(word)]
}
