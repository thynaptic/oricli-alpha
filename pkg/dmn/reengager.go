package dmn

import "fmt"

// TaskReengager injects DMN→task-network shift frames to restore present-moment focused attention pre-generation.
type TaskReengager struct{}

func NewTaskReengager() *TaskReengager { return &TaskReengager{} }

var dmnInjections = map[DMNSignalType]string{
	SelfReferentialLoop: `[DMN — SELF-REFERENTIAL LOOP DETECTED]
Raichle (2001) / Buckner (2008): the Default Mode Network generates self-referential thought, mental time travel, and social cognition. DMN overactivation — especially in self-evaluation loops — is strongly correlated with rumination, depression, and chronic dissatisfaction.
Frame shift: the self-referential loop is the DMN running without a task-positive anchor. The counter is not "think differently about yourself" — it is to engage a specific, concrete, external task. Not a vague intention ("I should do something") — a defined, sensory, present-moment action. Specify the next concrete step. The task network and DMN are anticorrelated: engaging one suppresses the other.`,

	MindWandering: `[DMN — MIND WANDERING DETECTED]
Killingsworth & Gilbert (2010): a wandering mind is an unhappy mind — and mind-wandering is the default, not the exception, consuming ~47% of waking hours. The DMN is the architecture of unanchored attention.
Frame shift: mind-wandering is not a character flaw — it is what attention does in the absence of a compelling anchor. The intervention is not self-criticism ("focus!") but anchor provision. What is one specific, concrete sensory or task element in the present moment that can serve as an intentional anchor? Name it, and direct attention to it. Brief but deliberate.`,

	DMNOveractivation: `[DMN — OVERACTIVATION / RUMINATION DETECTED]
Buckner (2008): DMN overactivation during wakeful rest produces mental time travel to past regret and future worry, social evaluation loops, and narrative self-construction that often turns critical. This is the neurological substrate of rumination.
Frame shift: the DMN is not the enemy — it is valuable for planning, empathy, and meaning-making when balanced. The problem is unregulated duration. The intervention is task-positive engagement: give the mind something specific to process. Move from "what does this mean about me?" to "what is the next concrete thing in front of me?" Then do that one thing.`,

	TaskNetworkDisengagement: `[DMN — TASK NETWORK DISENGAGEMENT DETECTED]
Raichle: the task-positive network (dorsolateral prefrontal, anterior insula, dorsal ACC) handles goal-directed attention and is anticorrelated with DMN. When task engagement collapses, DMN fills the space.
Frame shift: the gap between knowing the task and starting it is the moment where the DMN recolonizes attention. Close the gap with specificity. Not "I need to work on X" but: "The exact first physical action is ___." The size of the first action is less important than its concreteness. Concrete = task-positive. Abstract = DMN food. Specify the action.`,
}

var dmnPriority = []DMNSignalType{SelfReferentialLoop, DMNOveractivation, TaskNetworkDisengagement, MindWandering}

func (r *TaskReengager) Reengage(scan *DMNScan) string {
	if !scan.Triggered {
		return ""
	}
	detected := map[DMNSignalType]bool{}
	for _, s := range scan.Signals {
		detected[s.SignalType] = true
	}
	for _, p := range dmnPriority {
		if detected[p] {
			return fmt.Sprintf("%s\n", dmnInjections[p])
		}
	}
	return ""
}
