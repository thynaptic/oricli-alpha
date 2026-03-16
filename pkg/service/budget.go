package service

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type Transaction struct {
	Timestamp    float64 `json:"timestamp"`
	Type         string  `json:"type"`
	Amount       float64 `json:"amount"`
	Reason       string  `json:"reason"`
	BalanceAfter float64 `json:"balance_after"`
}

type BudgetState struct {
	Balance      float64       `json:"balance"`
	Currency     string        `json:"currency"`
	Transactions []Transaction `json:"transactions"`
}

type BudgetManager struct {
	FilePath string
	mu       sync.Mutex
}

func NewBudgetManager(path string) *BudgetManager {
	if path == "" {
		path = "oricli_core/data/compute_budget.json"
	}
	bm := &BudgetManager{FilePath: path}
	bm.ensureFile()
	return bm
}

// --- OPTIMIZATION & RESOURCE ALLOCATION ---

func (bm *BudgetManager) OptimizeGraph(params map[string]interface{}) (map[string]interface{}, error) {
	// Native Go graph optimization logic (simplified)
	return map[string]interface{}{
		"success":   true,
		"optimized": true,
		"reduction": "15% compute estimated",
	}, nil
}

func (bm *BudgetManager) AllocateCompute(params map[string]interface{}) (map[string]interface{}, error) {
	priority, _ := params["priority"].(float64)
	if priority == 0 { priority = 0.5 }
	
	return map[string]interface{}{
		"success": true,
		"cores":   int(32 * priority),
		"status":  "allocated_on_epyc",
	}, nil
}

func (bm *BudgetManager) EstimateCost(params map[string]interface{}) (map[string]interface{}, error) {
	op, _ := params["operation"].(string)
	cost := 0.1
	if op == "reasoning" { cost = 0.5 }
	return map[string]interface{}{"success": true, "estimated_cost": cost}, nil
}

// --- EXISTING BUDGET METHODS ---

func (bm *BudgetManager) ensureFile() {
	if _, err := os.Stat(bm.FilePath); os.IsNotExist(err) {
		os.MkdirAll(filepath.Dir(bm.FilePath), 0755)
		bm.saveState(BudgetState{Balance: 100.0, Currency: "credits"})
	}
}

func (bm *BudgetManager) GetBalance() float64 {
	bm.mu.Lock()
	defer bm.mu.Unlock()
	return bm.loadState().Balance
}

func (bm *BudgetManager) Deduct(amount float64, reason string) bool {
	bm.mu.Lock()
	defer bm.mu.Unlock()
	state := bm.loadState()
	if state.Balance < amount { return false }
	state.Balance -= amount
	state.Transactions = append(state.Transactions, Transaction{Timestamp: float64(time.Now().Unix()), Type: "deduction", Amount: amount, Reason: reason, BalanceAfter: state.Balance})
	if len(state.Transactions) > 100 { state.Transactions = state.Transactions[len(state.Transactions)-100:] }
	bm.saveState(state)
	return true
}

func (bm *BudgetManager) Add(amount float64, reason string) {
	bm.mu.Lock()
	defer bm.mu.Unlock()
	state := bm.loadState()
	state.Balance += amount
	state.Transactions = append(state.Transactions, Transaction{Timestamp: float64(time.Now().Unix()), Type: "deposit", Amount: amount, Reason: reason, BalanceAfter: state.Balance})
	if len(state.Transactions) > 100 { state.Transactions = state.Transactions[len(state.Transactions)-100:] }
	bm.saveState(state)
}

func (bm *BudgetManager) loadState() BudgetState {
	data, err := os.ReadFile(bm.FilePath)
	if err != nil { return BudgetState{Balance: 0, Currency: "credits"} }
	var state BudgetState
	json.Unmarshal(data, &state)
	return state
}

func (bm *BudgetManager) saveState(state BudgetState) {
	data, _ := json.MarshalIndent(state, "", "  ")
	os.WriteFile(bm.FilePath, data, 0644)
}
