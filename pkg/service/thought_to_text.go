package service

import (
	"log"
	"strings"
	"time"
)

type ThoughtToTextResult struct {
	Text       string                 `json:"text"`
	Confidence float64                `json:"confidence"`
	Method     string                 `json:"method"`
	Metadata   map[string]interface{} `json:"metadata"`
}

type ThoughtToTextService struct {
	Orchestrator *GoOrchestrator
}

func NewThoughtToTextService(orch *GoOrchestrator) *ThoughtToTextService {
	return &ThoughtToTextService{Orchestrator: orch}
}

func (s *ThoughtToTextService) ConvertThoughtGraph(nodes []interface{}, context string) (*ThoughtToTextResult, error) {
	startTime := time.Now()
	log.Printf("[ThoughtToText] Converting MCTS graph to text (%d nodes)", len(nodes))

	var thoughts []string
	for _, rawNode := range nodes {
		if nodeMap, ok := rawNode.(map[string]interface{}); ok {
			if thought, ok := nodeMap["thought"].(string); ok {
				thoughts = append(thoughts, thought)
			} else if content, ok := nodeMap["content"].(string); ok {
				thoughts = append(thoughts, content)
			} else if totNode, ok := nodeMap["totNode"].(map[string]interface{}); ok {
				if tThought, ok := totNode["thought"].(string); ok {
					thoughts = append(thoughts, tThought)
				}
			}
		}
	}

	text := s.generateSentences(thoughts)

	// Optionally apply grammar/style via Orchestrator
	grammarRes, err := s.Orchestrator.Execute("neural_grammar.apply_grammar", map[string]interface{}{"text": text}, 10*time.Second)
	if err == nil {
		if t, ok := grammarRes.(map[string]interface{})["text"].(string); ok && t != "" {
			text = t
		}
	}

	return &ThoughtToTextResult{
		Text:       text,
		Confidence: 0.85, // Heuristic confidence
		Method:     "graph_flattening",
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
			"node_count":     len(nodes),
		},
	}, nil
}

func (s *ThoughtToTextService) ConvertReasoningTree(tree map[string]interface{}, context string) (*ThoughtToTextResult, error) {
	startTime := time.Now()
	log.Printf("[ThoughtToText] Converting reasoning tree to text")

	var thoughts []string
	s.extractThoughtsFromTree(tree, &thoughts)
	text := s.generateSentences(thoughts)

	return &ThoughtToTextResult{
		Text:       text,
		Confidence: 0.80,
		Method:     "tree_flattening",
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
		},
	}, nil
}

func (s *ThoughtToTextService) extractThoughtsFromTree(node interface{}, thoughts *[]string) {
	switch v := node.(type) {
	case map[string]interface{}:
		if thought, ok := v["thought"].(string); ok && thought != "" {
			*thoughts = append(*thoughts, thought)
		}
		if children, ok := v["children"].([]interface{}); ok {
			for _, child := range children {
				s.extractThoughtsFromTree(child, thoughts)
			}
		}
	case []interface{}:
		for _, item := range v {
			s.extractThoughtsFromTree(item, thoughts)
		}
	}
}

func (s *ThoughtToTextService) generateSentences(thoughts []string) string {
	if len(thoughts) == 0 {
		return ""
	}

	var sb strings.Builder
	for i, thought := range thoughts {
		t := strings.TrimSpace(thought)
		if t == "" {
			continue
		}
		
		// Capitalize first letter
		if len(t) > 0 {
			t = strings.ToUpper(string(t[0])) + t[1:]
		}

		// Ensure it ends with punctuation
		if !strings.HasSuffix(t, ".") && !strings.HasSuffix(t, "!") && !strings.HasSuffix(t, "?") {
			t += "."
		}

		// Add transition words for flow
		if i > 0 && len(thoughts) > 2 {
			if i == len(thoughts)-1 {
				sb.WriteString("Finally, ")
			} else if i == 1 {
				sb.WriteString("Next, ")
			} else {
				sb.WriteString("Then, ")
			}
		}

		sb.WriteString(t)
		sb.WriteString(" ")
	}

	return strings.TrimSpace(sb.String())
}
