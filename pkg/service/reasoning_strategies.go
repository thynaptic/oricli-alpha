package service

import (
	"context"
	"fmt"
	"strings"
)

// StrategyResult represents the outcome of a reasoning strategy
type StrategyResult struct {
	Reasoning     string   `json:"reasoning"`
	Conclusion    string   `json:"conclusion"`
	Confidence    float64  `json:"confidence"`
	Steps         []string `json:"reasoning_steps"`
	ReasoningType string   `json:"reasoning_type"`
}

// ReasoningStrategyService provides various specialized reasoning patterns
type ReasoningStrategyService struct {
	genService *GenerationService
}

// NewReasoningStrategyService creates a new reasoning strategy service
func NewReasoningStrategyService(genService *GenerationService) *ReasoningStrategyService {
	return &ReasoningStrategyService{
		genService: genService,
	}
}

// AnalogicalReasoning performs reasoning by analogy
func (s *ReasoningStrategyService) AnalogicalReasoning(ctx context.Context, query string, context string) (*StrategyResult, error) {
	prompt := fmt.Sprintf(`Perform analogical reasoning for the following target.
Target: %s
Context: %s

Please follow these steps:
1. Identify Source Domain
2. Map Relationships
3. Transfer Knowledge
4. Validate Analogy

Provide full reasoning and a conclusion.`, query, context)
	return s.runStrategy(ctx, prompt, "analogical_reasoning", 0.4)
}

// LogicalDeduction applies formal logic
func (s *ReasoningStrategyService) LogicalDeduction(ctx context.Context, query string, context string) (*StrategyResult, error) {
	prompt := fmt.Sprintf(`Apply logical deduction to the following premise.
Premise: %s
Context: %s

Follow these steps:
1. Identify Premises
2. Apply Logical Rules
3. Derive Conclusions
4. Validate Deduction

Provide full reasoning and a conclusion.`, query, context)
	return s.runStrategy(ctx, prompt, "logical_deduction", 0.2)
}

// Decomposition breaks a complex problem into sub-problems
func (s *ReasoningStrategyService) Decomposition(ctx context.Context, query string, context string) (*StrategyResult, error) {
	prompt := fmt.Sprintf(`Decompose the following complex problem.
Problem: %s
Context: %s

Steps:
1. Core Question Identification
2. Context Analysis
3. Solution Approach for each sub-problem
4. Validation strategy

Provide full reasoning and a conclusion.`, query, context)
	return s.runStrategy(ctx, prompt, "decomposition", 0.3)
}

// CriticalThinking evaluates assumptions and biases
func (s *ReasoningStrategyService) CriticalThinking(ctx context.Context, query string, context string) (*StrategyResult, error) {
	prompt := fmt.Sprintf(`Apply critical thinking to the following query.
Query: %s
Context: %s

Steps:
1. Assumption Evaluation
2. Bias Identification
3. Evidence Assessment
4. Logical Consistency

Provide full reasoning and a conclusion.`, query, context)
	return s.runStrategy(ctx, prompt, "critical_thinking", 0.3)
}

// HypothesisGeneration generates multiple explanations
func (s *ReasoningStrategyService) HypothesisGeneration(ctx context.Context, query string, context string) (*StrategyResult, error) {
	prompt := fmt.Sprintf(`Generate and evaluate hypotheses for the following problem.
Problem: %s
Context: %s

Steps:
1. Generate Multiple Hypotheses
2. Evidence Mapping
3. Falsification Attempt
4. Likelihood Assessment

Provide full reasoning and a conclusion.`, query, context)
	return s.runStrategy(ctx, prompt, "hypothesis_generation", 0.5)
}

// CausalInference identifies cause-and-effect
func (s *ReasoningStrategyService) CausalInference(ctx context.Context, query string, context string) (*StrategyResult, error) {
	prompt := fmt.Sprintf(`Perform causal inference for the following situation.
Query: %s
Context: %s

Steps:
1. Identify Candidate Causes
2. Analyze Temporal Precedence
3. Evaluate Mechanisms
4. Rule out Confounders

Provide full reasoning and a conclusion.`, query, context)
	return s.runStrategy(ctx, prompt, "causal_inference", 0.3)
}

// CounterfactualAnalysis considers alternative scenarios
func (s *ReasoningStrategyService) CounterfactualAnalysis(ctx context.Context, query string, context string) (*StrategyResult, error) {
	prompt := fmt.Sprintf(`Perform counterfactual analysis for the following scenario.
Scenario: %s
Context: %s

Steps:
1. Identify Key Antecedents
2. Construct "What-If" Scenarios
3. Trace Downstream Effects
4. Extract Lessons

Provide full reasoning and a conclusion.`, query, context)
	return s.runStrategy(ctx, prompt, "counterfactual_analysis", 0.5)
}

// StepByStepReasoning breaks reasoning into explicit sequential steps
func (s *ReasoningStrategyService) StepByStepReasoning(ctx context.Context, query string, context string) (*StrategyResult, error) {
	prompt := fmt.Sprintf(`Break down the reasoning for the following query into explicit sequential steps.
Query: %s
Context: %s

Format each step clearly as "Step X: [Reasoning]". Provide a final conclusion.`, query, context)
	return s.runStrategy(ctx, prompt, "step_by_step", 0.4)
}

// VerifyConclusion validates reasoning steps and conclusion
func (s *ReasoningStrategyService) VerifyConclusion(ctx context.Context, reasoningToVerify string, context string) (*StrategyResult, error) {
	prompt := fmt.Sprintf(`Verify and validate the following reasoning and conclusion.
Reasoning to Verify: %s
Context: %s

Identify any logical gaps, jumps in reasoning, or unstated assumptions. Provide a final validation status.`, reasoningToVerify, context)
	return s.runStrategy(ctx, prompt, "verification", 0.2)
}

// ReflectOnReasoning reviews reasoning steps and generates corrections
func (s *ReasoningStrategyService) ReflectOnReasoning(ctx context.Context, reasoningToReflect string) (*StrategyResult, error) {
	prompt := fmt.Sprintf(`Reflect on the following reasoning. Identify any potential improvements, inconsistencies, or better approaches.
Reasoning: %s

Provide a self-reflection analysis and suggested improvements.`, reasoningToReflect)
	return s.runStrategy(ctx, prompt, "reflection", 0.3)
}

func (s *ReasoningStrategyService) runStrategy(ctx context.Context, prompt string, strategyType string, temp float64) (*StrategyResult, error) {
	resp, err := s.genService.Generate(prompt, map[string]interface{}{"temperature": temp})
	if err != nil {
		return nil, err
	}

	reasoning, _ := resp["text"].(string)
	return &StrategyResult{
		Reasoning:     reasoning,
		Conclusion:    s.extractConclusion(reasoning),
		Confidence:    0.8,
		Steps:         s.extractSteps(reasoning),
		ReasoningType: strategyType,
	}, nil
}

func (s *ReasoningStrategyService) extractConclusion(reasoning string) string {
	if idx := strings.LastIndex(reasoning, "Conclusion:"); idx != -1 {
		return strings.TrimSpace(reasoning[idx+len("Conclusion:"):])
	}
	paras := strings.Split(reasoning, "\n\n")
	return strings.TrimSpace(paras[len(paras)-1])
}

func (s *ReasoningStrategyService) extractSteps(reasoning string) []string {
	var steps []string
	lines := strings.Split(reasoning, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if len(line) > 2 && (line[0] >= '1' && line[0] <= '9') && (line[1] == '.' || line[1] == ')') {
			steps = append(steps, line)
		} else if strings.HasPrefix(line, "Step ") {
			steps = append(steps, line)
		}
	}
	return steps
}
