package service

import (
	"strings"
)

// InstructionFollowingDetector analyzes inputs for strict task execution commands
type InstructionFollowingDetector struct{}

func NewInstructionFollowingDetector() *InstructionFollowingDetector {
	return &InstructionFollowingDetector{}
}

func (d *InstructionFollowingDetector) IsTaskExecution(input string) bool {
	inputLower := strings.ToLower(input)
	
	keywords := []string{
		"convert", "format", "jsonl", "csv", "table", 
		"output only", "strictly", "no conversational",
	}
	
	for _, kw := range keywords {
		if strings.Contains(inputLower, kw) {
			return true
		}
	}
	return false
}

func (d *InstructionFollowingDetector) GetTaskSystemPrompt() string {
	return "You are a Precise Data Engineer. DO NOT include conversational filler. DO NOT acknowledge the instruction. ONLY output the requested format."
}
