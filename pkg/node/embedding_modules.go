package node

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// --- EMBEDDINGS MODULE ---

type EmbeddingsModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.EmbeddingEngineService
}

func NewEmbeddingsModule(swarmBus *bus.SwarmBus, svc *service.EmbeddingEngineService) *EmbeddingsModule {
	return &EmbeddingsModule{
		ID:         "go_native_embeddings",
		ModuleName: "embeddings",
		Operations: []string{"generate", "similarity", "batch_generate"},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *EmbeddingsModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[EmbeddingsModule] %s started.", m.ModuleName)
}

func (m *EmbeddingsModule) onCFP(msg bus.Message) {
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
			"compute_cost": 1, // Replacing expensive PyTorch
			"node_id":      m.ID,
			"module_name":  m.ModuleName,
		},
	})
}

func (m *EmbeddingsModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result map[string]interface{}
	var err error

	switch operation {
	case "generate", "batch_generate":
		result, err = m.Service.GenerateEmbeddings(params)
	case "similarity":
		result, err = m.Service.Similarity(params)
	default:
		err = fmt.Errorf("unknown operation %s", operation)
	}

	if err != nil {
		m.Bus.Publish(bus.Message{Protocol: bus.ERROR, Topic: fmt.Sprintf("tasks.error.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"error": err.Error(), "task_id": taskID}})
		return
	}

	m.Bus.Publish(bus.Message{Protocol: bus.RESULT, Topic: fmt.Sprintf("tasks.result.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"result": result, "task_id": taskID}})
}

// --- CONCEPT EMBEDDINGS MODULE ---

type ConceptEmbeddingsModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.EmbeddingEngineService
}

func NewConceptEmbeddingsModule(swarmBus *bus.SwarmBus, svc *service.EmbeddingEngineService) *ConceptEmbeddingsModule {
	return &ConceptEmbeddingsModule{
		ID:         "go_native_concept_embeddings",
		ModuleName: "concept_embeddings",
		Operations: []string{"embed_concept", "find_related", "build_hierarchy", "semantic_similarity", "get_concept_neighbors", "find_hyponyms"},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *ConceptEmbeddingsModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[ConceptEmbeddingsModule] %s started.", m.ModuleName)
}

func (m *ConceptEmbeddingsModule) onCFP(msg bus.Message) {
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
			"compute_cost": 1,
			"node_id":      m.ID,
			"module_name":  m.ModuleName,
		},
	})
}

func (m *ConceptEmbeddingsModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result map[string]interface{}
	var err error

	switch operation {
	case "embed_concept", "get_concept_neighbors", "find_hyponyms":
		result, err = m.Service.EmbedConcept(params)
	case "find_related":
		result, err = m.Service.FindRelatedConcepts(params)
	case "build_hierarchy":
		result, err = m.Service.BuildHierarchy(params)
	case "semantic_similarity":
		result, err = m.Service.SemanticSimilarity(params)
	default:
		err = fmt.Errorf("unknown operation %s", operation)
	}

	if err != nil {
		m.Bus.Publish(bus.Message{Protocol: bus.ERROR, Topic: fmt.Sprintf("tasks.error.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"error": err.Error(), "task_id": taskID}})
		return
	}

	m.Bus.Publish(bus.Message{Protocol: bus.RESULT, Topic: fmt.Sprintf("tasks.result.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"result": result, "task_id": taskID}})
}

// --- PHRASE EMBEDDINGS MODULE ---

type PhraseEmbeddingsModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Service    *service.EmbeddingEngineService
}

func NewPhraseEmbeddingsModule(swarmBus *bus.SwarmBus, svc *service.EmbeddingEngineService) *PhraseEmbeddingsModule {
	return &PhraseEmbeddingsModule{
		ID:         "go_native_phrase_embeddings",
		ModuleName: "phrase_embeddings",
		Operations: []string{"embed_words", "embed_phrases", "embed_sentence", "find_similar_phrases", "rank_candidates", "batch_embed_words"},
		Bus:        swarmBus,
		Service:    svc,
	}
}

func (m *PhraseEmbeddingsModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[PhraseEmbeddingsModule] %s started.", m.ModuleName)
}

func (m *PhraseEmbeddingsModule) onCFP(msg bus.Message) {
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
			"compute_cost": 1,
			"node_id":      m.ID,
			"module_name":  m.ModuleName,
		},
	})
}

func (m *PhraseEmbeddingsModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	var result map[string]interface{}
	var err error

	switch operation {
	case "embed_words", "embed_phrases", "embed_sentence", "batch_embed_words":
		result, err = m.Service.EmbedWords(params)
	case "find_similar_phrases":
		result, err = m.Service.FindSimilarPhrases(params)
	case "rank_candidates":
		result, err = m.Service.RankCandidates(params)
	default:
		err = fmt.Errorf("unknown operation %s", operation)
	}

	if err != nil {
		m.Bus.Publish(bus.Message{Protocol: bus.ERROR, Topic: fmt.Sprintf("tasks.error.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"error": err.Error(), "task_id": taskID}})
		return
	}

	m.Bus.Publish(bus.Message{Protocol: bus.RESULT, Topic: fmt.Sprintf("tasks.result.%s", taskID), SenderID: m.ID, RecipientID: msg.SenderID, Payload: map[string]interface{}{"result": result, "task_id": taskID}})
}
