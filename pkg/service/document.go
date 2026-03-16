package service

import (
	"context"
	"fmt"
	"sort"
	"strings"
)

// DocumentAnalysisResult represents the structured analysis of a document
type DocumentAnalysisResult struct {
	FileName       string   `json:"file_name"`
	Summary        string   `json:"summary"`
	KeyPoints      []string `json:"key_points"`
	ActionItems    []string `json:"action_items"`
	CharacterCount int      `json:"character_count"`
}

// DocumentService handles document analysis, summarization, and ranking natively.
type DocumentService struct {
	GenService *GenerationService
}

func NewDocumentService(gen *GenerationService) *DocumentService {
	return &DocumentService{
		GenService: gen,
	}
}

// AnalyzeDocument performs deep analysis of document text
func (s *DocumentService) AnalyzeDocument(ctx context.Context, text string, fileName string) (*DocumentAnalysisResult, error) {
	prompt := fmt.Sprintf("Analyze the following document: %s\n\nContent:\n%s\n\nProvide a summary, key points, and action items.", fileName, text)
	
	result, err := s.GenService.Generate(prompt, map[string]interface{}{
		"system": "You are a professional document analyst.",
	})
	if err != nil {
		return nil, err
	}

	analysisText, _ := result["text"].(string)
	
	return &DocumentAnalysisResult{
		FileName:       fileName,
		Summary:        s.extractSection(analysisText, "Summary:"),
		KeyPoints:      s.extractList(analysisText, "Key Points:"),
		ActionItems:    s.extractList(analysisText, "Action Items:"),
		CharacterCount: len(text),
	}, nil
}

// SummarizeDocument generates a concise summary of text
func (s *DocumentService) SummarizeDocument(ctx context.Context, text string, maxSentences int) (string, error) {
	prompt := fmt.Sprintf("Summarize the following text in exactly %d sentences:\n\n%s", maxSentences, text)
	result, err := s.GenService.Generate(prompt, map[string]interface{}{
		"system": "You are a concise summarizer.",
	})
	if err != nil {
		return "", err
	}
	return result["text"].(string), nil
}

// RankDocuments ranks documents by relevance to a query
func (s *DocumentService) RankDocuments(query string, documents []map[string]interface{}) []map[string]interface{} {
	// Simple BM25-like ranking logic natively in Go
	queryWords := strings.Fields(strings.ToLower(query))
	
	type scoredDoc struct {
		doc   map[string]interface{}
		score float64
	}
	
	scored := make([]scoredDoc, len(documents))
	for i, doc := range documents {
		content, _ := doc["content"].(string)
		title, _ := doc["title"].(string)
		lowerContent := strings.ToLower(content + " " + title)
		
		score := 0.0
		for _, qw := range queryWords {
			count := strings.Count(lowerContent, qw)
			score += float64(count)
		}
		
		// Factor in original relevance score if present
		if origScore, ok := doc["relevanceScore"].(float64); ok {
			score += origScore * 10.0
		}
		
		scored[i] = scoredDoc{doc: doc, score: score}
	}
	
	sort.Slice(scored, func(i, j int) bool {
		return scored[i].score > scored[j].score
	})
	
	res := make([]map[string]interface{}, len(scored))
	for i, sd := range scored {
		sd.doc["rank_score"] = sd.score
		res[i] = sd.doc
	}
	
	return res
}

func (s *DocumentService) extractSection(text string, sectionName string) string {
	idx := strings.Index(text, sectionName)
	if idx == -1 { return "" }
	res := text[idx+len(sectionName):]
	if end := strings.Index(res, "\n\n"); end != -1 {
		res = res[:end]
	}
	return strings.TrimSpace(res)
}

func (s *DocumentService) extractList(text string, sectionName string) []string {
	section := s.extractSection(text, sectionName)
	lines := strings.Split(section, "\n")
	var res []string
	for _, l := range lines {
		l = strings.TrimSpace(l)
		if strings.HasPrefix(l, "-") || strings.HasPrefix(l, "*") || (len(l) > 2 && l[1] == '.') {
			res = append(res, strings.TrimSpace(l[1:]))
		}
	}
	return res
}
