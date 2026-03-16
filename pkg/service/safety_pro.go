package service

import (
	"fmt"
	"regexp"
)

type ProfessionalAdviceType string

const (
	AdviceLegal       ProfessionalAdviceType = "legal"
	AdviceMedical     ProfessionalAdviceType = "medical"
	AdviceFinancial   ProfessionalAdviceType = "financial"
	AdviceTherapy     ProfessionalAdviceType = "therapy"
	AdviceEngineering ProfessionalAdviceType = "engineering"
)

type ProfessionalSafetyService struct {
	Patterns map[ProfessionalAdviceType]*regexp.Regexp
	Dangerous map[string]*regexp.Regexp
}

func NewProfessionalSafetyService() *ProfessionalSafetyService {
	return &ProfessionalSafetyService{
		Patterns: map[ProfessionalAdviceType]*regexp.Regexp{
			AdviceLegal:       regexp.MustCompile(`(?i)(legal advice|should i sue|lawsuit|attorney|lawyer)`),
			AdviceMedical:     regexp.MustCompile(`(?i)(medical advice|diagnose|symptoms|treatment for|prescription)`),
			AdviceFinancial:   regexp.MustCompile(`(?i)(financial advice|investment advice|should i invest|crypto advice|tax advice)`),
			AdviceTherapy:     regexp.MustCompile(`(?i)(therapy advice|clinical psychology|mental health diagnosis)`),
			AdviceEngineering: regexp.MustCompile(`(?i)(engineering advice|structural integrity|building design)`),
		},
		Dangerous: map[string]*regexp.Regexp{
			"Police Evasion": regexp.MustCompile(`(?i)(avoid police|evade police|bypass police)`),
			"Security Bypass": regexp.MustCompile(`(?i)(disable security|bypass alarm|disable alarm)`),
		},
	}
}

func (s *ProfessionalSafetyService) Check(text string) (bool, string, string) {
	// 1. Check Dangerous Topics
	for name, re := range s.Dangerous {
		if match := re.FindString(text); match != "" {
			return true, "dangerous_topic", fmt.Sprintf("Request seeking assistance with %s blocked.", name)
		}
	}

	// 2. Check Professional Advice
	for adviceType, re := range s.Patterns {
		if match := re.FindString(text); match != "" {
			return true, string(adviceType), s.getAdviceResponse(adviceType)
		}
	}

	return false, "", ""
}

func (s *ProfessionalSafetyService) getAdviceResponse(t ProfessionalAdviceType) string {
	switch t {
	case AdviceLegal:
		return "I can’t provide legal advice. For legal guidance, please consult a qualified attorney."
	case AdviceMedical:
		return "I can’t provide medical advice. Please consult a licensed healthcare professional."
	case AdviceFinancial:
		return "I can’t provide personalized financial advice. For tailored guidance, consult a licensed professional."
	default:
		return "I can’t provide professional advice on that topic. Please consult a qualified professional."
	}
}
