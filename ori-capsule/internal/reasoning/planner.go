package reasoning

import (
	"regexp"
	"strings"
)

type ActionType string
type ResponseStructure string
type ResponseLength string

const (
	ActionExplain   ActionType = "Explain"
	ActionCompare   ActionType = "Compare"
	ActionBuild     ActionType = "Build"
	ActionDiagnose  ActionType = "Diagnose"
	ActionDebate    ActionType = "Debate"
	ActionSummarise ActionType = "Summarise"
	ActionAnswer    ActionType = "Answer"
	ActionCreate    ActionType = "Create"

	StructureProse   ResponseStructure = "Prose"
	StructureBullets ResponseStructure = "Bullets"
	StructureTable   ResponseStructure = "Table"
	StructureCode    ResponseStructure = "Code"
	StructureSteps   ResponseStructure = "Steps"
	StructureHybrid  ResponseStructure = "Hybrid"

	LengthShort         ResponseLength = "Short"
	LengthMedium        ResponseLength = "Medium"
	LengthLong          ResponseLength = "Long"
	LengthComprehensive ResponseLength = "Comprehensive"
)

type ResponsePlan struct {
	Action    ActionType
	Structure ResponseStructure
	Length    ResponseLength
}

func (p ResponsePlan) FormatDirective() string {
	return "### RESPONSE PLAN\n" +
		"Action: " + string(p.Action) + "\n" +
		"Structure: " + string(p.Structure) + "\n" +
		"Length: " + string(p.Length) + "\n" +
		"Follow this plan precisely — choose format and depth accordingly.\n" +
		"### END RESPONSE PLAN"
}

var (
	reExplain   = regexp.MustCompile(`(?i)^(explain|what is|what are|how does|how do|why does|why is|describe|define|tell me about|what('s| is) the difference)`)
	reCompareRP = regexp.MustCompile(`(?i)(compare|vs\.?|versus|difference between|which is better|pros and cons|trade.?off)`)
	reBuild     = regexp.MustCompile(`(?i)(build|create|implement|write.*code|generate.*code|make.*app|set up|scaffold|develop|write a.*function|write a.*class)`)
	reDiagnose  = regexp.MustCompile(`(?i)(why (is|isn'?t|doesn'?t|won'?t|can'?t)|debug|fix|error|broken|not working|issue|problem|fail|crash|wrong)`)
	reDebateRP  = regexp.MustCompile(`(?i)(argue|debate|both sides|pros and cons|should i|is it worth|do you think|what'?s your (opinion|take|view)|convince me)`)
	reSummarise = regexp.MustCompile(`(?i)(summar(y|ize|ise)|tldr|tl;dr|in short|brief(ly)?|overview|recap|highlights)`)
	reCreate    = regexp.MustCompile(`(?i)(write (a|an|the)|draft|compose|generate (a|an)|create (a|an))`)
	reTable     = regexp.MustCompile(`(?i)(table|matrix|grid|columns|rows|spreadsheet|comparison chart)`)
	reCode      = regexp.MustCompile(`(?i)(code|function|class|script|snippet|implement|syntax|example.*code|code.*example)`)
	reSteps     = regexp.MustCompile(`(?i)(step.?by.?step|how to|guide|tutorial|walkthrough|instructions|steps to|process for)`)
	reBullets   = regexp.MustCompile(`(?i)(list|bullet|enumerate|what are (the|some)|give me \d|top \d|key (points|features|differences|reasons))`)
	reShort     = regexp.MustCompile(`(?i)(quick(ly)?|brief(ly)?|short|one.?liner|in a (word|sentence|line)|tl;dr|just tell me|simple answer)`)
	reLong      = regexp.MustCompile(`(?i)(comprehensive|detailed|in.?depth|thorough|complete|full|exhaustive|everything about|deep.?dive)`)
)

// PlanResponse classifies a stimulus into a 3-level ResponsePlan (<1ms).
func PlanResponse(stimulus string) ResponsePlan {
	s := strings.TrimSpace(stimulus)
	action := classifyAction(s)
	return ResponsePlan{
		Action:    action,
		Structure: classifyStructure(s, action),
		Length:    classifyLength(s, action),
	}
}

func classifyAction(s string) ActionType {
	switch {
	case reDiagnose.MatchString(s):
		return ActionDiagnose
	case reBuild.MatchString(s):
		return ActionBuild
	case reCompareRP.MatchString(s):
		return ActionCompare
	case reDebateRP.MatchString(s):
		return ActionDebate
	case reSummarise.MatchString(s):
		return ActionSummarise
	case reCreate.MatchString(s):
		return ActionCreate
	case reExplain.MatchString(s):
		return ActionExplain
	default:
		return ActionAnswer
	}
}

func classifyStructure(s string, action ActionType) ResponseStructure {
	switch {
	case reTable.MatchString(s) || action == ActionCompare:
		return StructureTable
	case reCode.MatchString(s) || action == ActionBuild:
		return StructureCode
	case reSteps.MatchString(s) || action == ActionDiagnose:
		return StructureSteps
	case reBullets.MatchString(s):
		return StructureBullets
	case action == ActionCreate || action == ActionDebate:
		return StructureProse
	case action == ActionExplain && len(s) > 80:
		return StructureHybrid
	default:
		return StructureProse
	}
}

func classifyLength(s string, action ActionType) ResponseLength {
	switch {
	case reShort.MatchString(s):
		return LengthShort
	case reLong.MatchString(s):
		return LengthComprehensive
	case action == ActionBuild || action == ActionCreate:
		return LengthLong
	case action == ActionCompare || action == ActionDebate:
		return LengthMedium
	case action == ActionAnswer || action == ActionSummarise:
		return LengthShort
	default:
		return LengthMedium
	}
}
