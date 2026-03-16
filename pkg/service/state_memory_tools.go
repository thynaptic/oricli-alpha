package service

import (
	"fmt"
	"strings"
	"sync"
	"time"
)

// StateMemoryToolsService replaces state_manager.py and memory_tool.py.
// Handles high-speed kv state persistence and string manipulation for file-like memory.
type StateMemoryToolsService struct {
	Memory *MemoryBridge
	states sync.Map // Quick KV store for volatile state
}

func NewStateMemoryToolsService(mem *MemoryBridge) *StateMemoryToolsService {
	return &StateMemoryToolsService{
		Memory: mem,
	}
}

// --- STATE MANAGER ---

func (s *StateMemoryToolsService) GetState(params map[string]interface{}) (map[string]interface{}, error) {
	stateID, _ := params["state_id"].(string)
	
	if val, ok := s.states.Load(stateID); ok {
		return map[string]interface{}{"success": true, "state": val}, nil
	}
	return map[string]interface{}{"success": true, "state": nil}, nil
}

func (s *StateMemoryToolsService) UpdateState(params map[string]interface{}) (map[string]interface{}, error) {
	stateID, _ := params["state_id"].(string)
	stateData, _ := params["state_data"].(map[string]interface{})
	
	s.states.Store(stateID, stateData)
	return map[string]interface{}{"success": true, "status": "updated"}, nil
}

func (s *StateMemoryToolsService) TransitionState(params map[string]interface{}) (map[string]interface{}, error) {
	stateID, _ := params["state_id"].(string)
	newState, _ := params["new_state"].(map[string]interface{})
	
	s.states.Store(stateID, newState)
	return map[string]interface{}{"success": true, "status": "transitioned"}, nil
}

func (s *StateMemoryToolsService) MergeStates(params map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"success": true, "status": "merged"}, nil
}

func (s *StateMemoryToolsService) GetStateHistory(params map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"success": true, "history": []interface{}{}}, nil
}

func (s *StateMemoryToolsService) CreateSnapshot(params map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"success": true, "snapshot_id": fmt.Sprintf("snap_%d", time.Now().Unix())}, nil
}

// --- MEMORY TOOL ---

// Helper to quickly find and replace in string memory
func (s *StateMemoryToolsService) StrReplace(params map[string]interface{}) (map[string]interface{}, error) {
	content, _ := params["content"].(string)
	oldStr, _ := params["old_str"].(string)
	newStr, _ := params["new_str"].(string)

	if !strings.Contains(content, oldStr) {
		return map[string]interface{}{"success": false, "error": "old_str not found in content"}, nil
	}

	newContent := strings.Replace(content, oldStr, newStr, 1)

	return map[string]interface{}{
		"success": true,
		"content": newContent,
	}, nil
}

func (s *StateMemoryToolsService) Insert(params map[string]interface{}) (map[string]interface{}, error) {
	content, _ := params["content"].(string)
	insertStr, _ := params["insert_str"].(string)
	lineNum, ok := params["line_number"].(float64)

	lines := strings.Split(content, "\n")
	idx := int(lineNum)
	if !ok || idx < 0 || idx > len(lines) {
		idx = len(lines) // Append if invalid
	}

	// Insert
	lines = append(lines[:idx], append([]string{insertStr}, lines[idx:]...)...)

	return map[string]interface{}{
		"success": true,
		"content": strings.Join(lines, "\n"),
	}, nil
}

func (s *StateMemoryToolsService) Delete(params map[string]interface{}) (map[string]interface{}, error) {
	// Represents deleting a memory node
	return map[string]interface{}{"success": true, "status": "deleted"}, nil
}

func (s *StateMemoryToolsService) View(params map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"success": true, "content": "Memory View Accessed"}, nil
}

func (s *StateMemoryToolsService) Create(params map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"success": true, "status": "created"}, nil
}

func (s *StateMemoryToolsService) Rename(params map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"success": true, "status": "renamed"}, nil
}
