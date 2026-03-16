package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

type VoiceEngineModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.VoiceEngineService
}

func NewVoiceEngineModule(swarmBus *bus.SwarmBus, svc *service.VoiceEngineService) *VoiceEngineModule {
	return &VoiceEngineModule{
		ID:         "go_native_voice_engine",
		ModuleName: "universal_voice_engine",
		Operations: []string{
			"detect_tone_cues",
			"adapt_voice",
			"get_voice_profile",
			"update_voice_profile",
			"apply_voice_style",
			"analyze_conversation_topic",
			"generate",
			"generate_variations",
			"detect_emotion",
			"transition_emotion",
			"select_emotion_response",
			"get_emotion_graph",
			"get_emotion_intensity",
			"get_emotion_valence_arousal",
		},
		Bus:     swarmBus,
		Service: svc,
	}
}

func (m *VoiceEngineModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[VoiceEngineModule] %s started. Native persona formatting active.", m.ModuleName)
}

func (m *VoiceEngineModule) onCFP(msg bus.Message) {
	operation, ok := msg.Payload["operation"].(string)
	if !ok {
		return
	}

	supported := false
	for _, op := range m.Operations {
		if op == operation {
			supported = true
			break
		}
	}
	if !supported {
		return
	}

	taskID, _ := msg.Payload["task_id"].(string)

	m.Bus.Publish(bus.Message{
		Protocol:    bus.BID,
		Topic:       fmt.Sprintf("tasks.bid.%s", taskID),
		SenderID:    m.ID,
		RecipientID: msg.SenderID,
		Payload: map[string]interface{}{
			"task_id":      taskID,
			"operation":    operation,
			"confidence":   1.0,
			"compute_cost": 1, // High speed string ops
			"node_id":      m.ID,
			"module_name":  m.ModuleName,
		},
	})
}

func (m *VoiceEngineModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result map[string]interface{}
	var err error

	switch operation {
	case "detect_tone_cues":
		result, err = m.Service.DetectToneCues(params)
	case "adapt_voice":
		result, err = m.Service.AdaptVoice(params)
	case "get_voice_profile":
		result, err = m.Service.GetVoiceProfile(params)
	case "update_voice_profile":
		result, err = m.Service.UpdateVoiceProfile(params)
	case "apply_voice_style":
		result, err = m.Service.ApplyVoiceStyle(params)
	case "analyze_conversation_topic":
		result, err = m.Service.AnalyzeConversationTopic(params)
	case "generate":
		result, err = m.Service.GenerateResponse(params)
	case "generate_variations":
		result, err = m.Service.GenerateVariations(params)
	case "detect_emotion":
		result, err = m.Service.DetectEmotion(params)
	case "transition_emotion":
		result, err = m.Service.TransitionEmotion(params)
	case "select_emotion_response":
		result, err = m.Service.SelectEmotionResponse(params)
	case "get_emotion_graph":
		result, err = m.Service.GetEmotionGraph(params)
	case "get_emotion_intensity":
		result, err = m.Service.GetEmotionIntensity(params)
	case "get_emotion_valence_arousal":
		result, err = m.Service.GetEmotionValenceArousal(params)
	default:
		err = fmt.Errorf("unknown operation %s", operation)
	}

	if err != nil {
		m.Bus.Publish(bus.Message{Protocol: bus.ERROR, Topic: fmt.Sprintf("tasks.error.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"error": err.Error(), "task_id": taskID}})
		return
	}

	m.Bus.Publish(bus.Message{Protocol: bus.RESULT, Topic: fmt.Sprintf("tasks.result.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"result": result, "task_id": taskID}})
}
