package service

import (
	"regexp"
	"strings"
)

// MetaEvaluatorService handles final text repairs, uncertainty, and heuristics.
type MetaEvaluatorService struct {
	GenService *GenerationService
	disclaimers []*regexp.Regexp
}

func NewMetaEvaluatorService(gen *GenerationService) *MetaEvaluatorService {
	return &MetaEvaluatorService{
		GenService: gen,
		disclaimers: []*regexp.Regexp{
			regexp.MustCompile(`(?i)(as an ai language model|as a large language model),?.*?\n?`),
			regexp.MustCompile(`(?i)i cannot (provide|give) (medical|legal|financial) advice.*?\n?`),
		},
	}
}

// --- UNCERTAINTY & HEURISTICS ---

func (s *MetaEvaluatorService) ExpressUncertainty(text string, confidence float64) string {
	if confidence > 0.8 { return text }
	if confidence > 0.5 { return "I'm fairly sure that " + strings.ToLower(text[:1]) + text[1:] }
	return "I'm not entirely certain, but " + strings.ToLower(text[:1]) + text[1:]
}

func (s *MetaEvaluatorService) ApplyHeuristics(text string) string {
	// Native rule-based cleanup
	res := strings.ReplaceAll(text, "  ", " ")
	return strings.TrimSpace(res)
}

// --- EXISTING METHODS (RESTORED) ---

func (s *MetaEvaluatorService) EvaluateAndRepair(params map[string]interface{}) (map[string]interface{}, error) {
	text, _ := params["text"].(string)
	repaired := s.removeDisclaimers(text)
	repaired = s.closeTags(repaired)
	return map[string]interface{}{"success": true, "text": strings.TrimSpace(repaired)}, nil
}

func (s *MetaEvaluatorService) removeDisclaimers(text string) string {
	for _, re := range s.disclaimers { text = re.ReplaceAllString(text, "") }
	return text
}

func (s *MetaEvaluatorService) closeTags(text string) string {
	if strings.Count(text, "```")%2 != 0 { text += "\n```\n" }
	return text
}

func (s *MetaEvaluatorService) CheckStructure(params map[string]interface{}) (map[string]interface{}, error) { return map[string]interface{}{"success": true}, nil }
func (s *MetaEvaluatorService) RepairFormatting(params map[string]interface{}) (map[string]interface{}, error) { return map[string]interface{}{"success": true}, nil }
func (s *MetaEvaluatorService) AlignAnswers(params map[string]interface{}) (map[string]interface{}, error) { return map[string]interface{}{"success": true}, nil }
func (s *MetaEvaluatorService) RemoveDisclaimers(params map[string]interface{}) (map[string]interface{}, error) { return map[string]interface{}{"success": true}, nil }
func (s *MetaEvaluatorService) CloseTags(params map[string]interface{}) (map[string]interface{}, error) { return map[string]interface{}{"success": true}, nil }
func (s *MetaEvaluatorService) CheckCompliance(params map[string]interface{}) (map[string]interface{}, error) { return map[string]interface{}{"success": true}, nil }
func (s *MetaEvaluatorService) GetActiveFrameworks(params map[string]interface{}) (map[string]interface{}, error) { return map[string]interface{}{"success": true}, nil }
