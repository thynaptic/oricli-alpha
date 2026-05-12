package service

import "testing"

func TestSkillManagerMatchSkillsDeterministicAndSpecific(t *testing.T) {
	sm := &SkillManager{skills: map[string]AgentSkill{}}
	sm.RegisterSkill(AgentSkill{
		Name:     "generic_planner",
		Triggers: []string{"plan"},
	})
	sm.RegisterSkill(AgentSkill{
		Name:     "task_patch_planner",
		Triggers: []string{"make this simpler", "plan"},
	})

	matches := sm.MatchSkills("Can you make this simpler in the plan?")
	if len(matches) < 2 {
		t.Fatalf("expected at least two matches, got %+v", matches)
	}
	if matches[0].Name != "task_patch_planner" {
		t.Fatalf("expected specific multi-word trigger first, got %+v", matches)
	}
}

func TestSkillManagerListSkillsSorted(t *testing.T) {
	sm := &SkillManager{skills: map[string]AgentSkill{}}
	sm.RegisterSkill(AgentSkill{Name: "zeta"})
	sm.RegisterSkill(AgentSkill{Name: "alpha"})

	list := sm.ListSkills()
	if len(list) != 2 {
		t.Fatalf("expected two skills, got %+v", list)
	}
	if list[0].Name != "alpha" || list[1].Name != "zeta" {
		t.Fatalf("expected sorted skills, got %+v", list)
	}
}
