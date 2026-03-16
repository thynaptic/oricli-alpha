package service

import (
	"fmt"
	"strings"
)

type GameTheoryService struct{}

func NewGameTheoryService() *GameTheoryService {
	return &GameTheoryService{}
}

// NormalFormGame represents the parsed game structure
type NormalFormGame struct {
	Players         []string
	Strategies      map[string][]string
	StrategyIndices []int // Number of strategies per player
	PayoffTensor    []interface{}
}

func (s *GameTheoryService) SolveGame(params map[string]interface{}) (map[string]interface{}, error) {
	game, err := s.normalizeGame(params)
	if err != nil {
		return nil, err
	}

	totalProfiles := 1
	for _, count := range game.StrategyIndices {
		totalProfiles *= count
	}

	if totalProfiles > 10000 {
		return nil, fmt.Errorf("game too large: %d profiles (max 10,000)", totalProfiles)
	}

	var equilibria []map[string]interface{}
	
	// Enumerate all possible strategy profiles
	profiles := s.generateProfiles(game.StrategyIndices)
	
	for _, profile := range profiles {
		if s.isNashEquilibrium(game, profile) {
			eqProfile := make(map[string]string)
			for i, pIdx := range profile {
				eqProfile[game.Players[i]] = game.Strategies[game.Players[i]][pIdx]
			}
			
			payoffs, _ := s.getPayoffProfile(game.PayoffTensor, profile, len(game.Players))
			payoffMap := make(map[string]float64)
			for i, p := range game.Players {
				payoffMap[p] = payoffs[i]
			}
			
			equilibria = append(equilibria, map[string]interface{}{
				"profile": eqProfile,
				"payoffs": payoffMap,
			})
		}
	}

	if equilibria == nil {
		equilibria = make([]map[string]interface{}, 0)
	}

	return map[string]interface{}{
		"success":    true,
		"equilibria": equilibria,
		"metadata": map[string]interface{}{
			"players":                game.Players,
			"total_profiles_checked": totalProfiles,
			"equilibrium_type":       "nash",
		},
	}, nil
}

func (s *GameTheoryService) BestResponse(params map[string]interface{}) (map[string]interface{}, error) {
	targetPlayer, ok := params["player"].(string)
	if !ok {
		return nil, fmt.Errorf("player is required and must be a string")
	}

	profileMap, ok := params["profile"].(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("profile is required and must be an object")
	}

	game, err := s.normalizeGame(params)
	if err != nil {
		return nil, err
	}

	targetIdx := -1
	for i, p := range game.Players {
		if p == targetPlayer {
			targetIdx = i
			break
		}
	}
	if targetIdx == -1 {
		return nil, fmt.Errorf("player %s not in game", targetPlayer)
	}

	// Build the fixed profile (excluding target player)
	baseProfile := make([]int, len(game.Players))
	for i, p := range game.Players {
		if i == targetIdx {
			continue
		}
		stratRaw, exists := profileMap[p]
		if !exists {
			return nil, fmt.Errorf("missing strategy for player %s", p)
		}
		stratStr, _ := stratRaw.(string)
		
		found := false
		for j, sName := range game.Strategies[p] {
			if sName == stratStr {
				baseProfile[i] = j
				found = true
				break
			}
		}
		if !found {
			return nil, fmt.Errorf("strategy %s not valid for player %s", stratStr, p)
		}
	}

	// Find best response
	var bestResponses []string
	payoffsMap := make(map[string]float64)
	bestPayoff := -mathMaxFloat()

	for j, strat := range game.Strategies[targetPlayer] {
		testProfile := make([]int, len(game.Players))
		copy(testProfile, baseProfile)
		testProfile[targetIdx] = j
		
		payoffs, err := s.getPayoffProfile(game.PayoffTensor, testProfile, len(game.Players))
		if err != nil {
			return nil, err
		}
		
		pVal := payoffs[targetIdx]
		payoffsMap[strat] = pVal
		
		if pVal > bestPayoff {
			bestPayoff = pVal
			bestResponses = []string{strat}
		} else if pVal == bestPayoff {
			bestResponses = append(bestResponses, strat)
		}
	}

	if bestResponses == nil {
		bestResponses = make([]string, 0)
	}

	return map[string]interface{}{
		"success":        true,
		"best_responses": bestResponses,
		"payoffs":        payoffsMap,
		"metadata": map[string]interface{}{
			"player": targetPlayer,
		},
	}, nil
}

func (s *GameTheoryService) AnalyzeScenario(params map[string]interface{}) (map[string]interface{}, error) {
	scenario, ok := params["scenario"].(string)
	if !ok {
		return nil, fmt.Errorf("scenario parameter required")
	}

	var gameParams map[string]interface{}

	switch strings.ToLower(scenario) {
	case "prisoners_dilemma":
		gameParams = map[string]interface{}{
			"players": []string{"P1", "P2"},
			"strategies": map[string][]string{
				"P1": {"Cooperate", "Defect"},
				"P2": {"Cooperate", "Defect"},
			},
			"payoffs": []interface{}{
				[]interface{}{[]interface{}{-1.0, -1.0}, []interface{}{-3.0, 0.0}},
				[]interface{}{[]interface{}{0.0, -3.0}, []interface{}{-2.0, -2.0}},
			},
		}
	case "chicken":
		gameParams = map[string]interface{}{
			"players": []string{"P1", "P2"},
			"strategies": map[string][]string{
				"P1": {"Swerve", "Straight"},
				"P2": {"Swerve", "Straight"},
			},
			"payoffs": []interface{}{
				[]interface{}{[]interface{}{0.0, 0.0}, []interface{}{-1.0, 1.0}},
				[]interface{}{[]interface{}{1.0, -1.0}, []interface{}{-10.0, -10.0}},
			},
		}
	case "stag_hunt":
		gameParams = map[string]interface{}{
			"players": []string{"P1", "P2"},
			"strategies": map[string][]string{
				"P1": {"Stag", "Hare"},
				"P2": {"Stag", "Hare"},
			},
			"payoffs": []interface{}{
				[]interface{}{[]interface{}{2.0, 2.0}, []interface{}{0.0, 1.0}},
				[]interface{}{[]interface{}{1.0, 0.0}, []interface{}{1.0, 1.0}},
			},
		}
	case "matching_pennies":
		gameParams = map[string]interface{}{
			"players": []string{"P1", "P2"},
			"strategies": map[string][]string{
				"P1": {"Heads", "Tails"},
				"P2": {"Heads", "Tails"},
			},
			"payoffs": []interface{}{
				[]interface{}{[]interface{}{1.0, -1.0}, []interface{}{-1.0, 1.0}},
				[]interface{}{[]interface{}{-1.0, 1.0}, []interface{}{1.0, -1.0}},
			},
		}
	default:
		return nil, fmt.Errorf("unknown scenario: %s", scenario)
	}

	res, err := s.SolveGame(gameParams)
	if err != nil {
		return nil, err
	}
	
	res["scenario"] = scenario
	res["game"] = gameParams
	return res, nil
}

// --- Helpers ---

func (s *GameTheoryService) normalizeGame(params map[string]interface{}) (*NormalFormGame, error) {
	// Parse Players
	var players []string
	if pRaw, ok := params["players"].([]interface{}); ok {
		for _, p := range pRaw {
			if pStr, ok := p.(string); ok {
				players = append(players, pStr)
			}
		}
	} else if _, ok := params["players"].(int); ok || (params["players"] != nil && fmt.Sprintf("%T", params["players"]) == "float64") {
		var count int
		if f, isFloat := params["players"].(float64); isFloat {
			count = int(f)
		} else {
			count = params["players"].(int)
		}
		for i := 0; i < count; i++ {
			players = append(players, fmt.Sprintf("player_%d", i))
		}
	}
	
	if len(players) < 1 {
		return nil, fmt.Errorf("at least one player required")
	}

	// Parse Strategies
	strategies := make(map[string][]string)
	strategyIndices := make([]int, len(players))
	
	if sRaw, ok := params["strategies"].(map[string]interface{}); ok {
		for i, p := range players {
			if sListRaw, exists := sRaw[p]; exists {
				if sList, isList := sListRaw.([]interface{}); isList {
					var strats []string
					for _, st := range sList {
						if stStr, ok := st.(string); ok {
							strats = append(strats, stStr)
						}
					}
					strategies[p] = strats
					strategyIndices[i] = len(strats)
				}
			}
		}
	}

	for _, p := range players {
		if len(strategies[p]) == 0 {
			return nil, fmt.Errorf("missing or empty strategies for player %s", p)
		}
	}

	// Payoffs
	payoffs, ok := params["payoffs"].([]interface{})
	if !ok {
		return nil, fmt.Errorf("payoffs tensor is required and must be an array")
	}

	return &NormalFormGame{
		Players:         players,
		Strategies:      strategies,
		StrategyIndices: strategyIndices,
		PayoffTensor:    payoffs,
	}, nil
}

func (s *GameTheoryService) generateProfiles(counts []int) [][]int {
	if len(counts) == 0 {
		return [][]int{{}}
	}
	
	head := counts[0]
	tailProfiles := s.generateProfiles(counts[1:])
	
	var res [][]int
	for i := 0; i < head; i++ {
		for _, t := range tailProfiles {
			profile := append([]int{i}, t...)
			res = append(res, profile)
		}
	}
	return res
}

func (s *GameTheoryService) getPayoffProfile(tensor []interface{}, profile []int, numPlayers int) ([]float64, error) {
	var current interface{} = tensor
	for _, idx := range profile {
		arr, ok := current.([]interface{})
		if !ok || idx >= len(arr) {
			return nil, fmt.Errorf("payoff tensor shape mismatch")
		}
		current = arr[idx]
	}
	
	finalArr, ok := current.([]interface{})
	if !ok || len(finalArr) != numPlayers {
		return nil, fmt.Errorf("payoff tensor leaf must contain exactly %d float values", numPlayers)
	}
	
	payoffs := make([]float64, numPlayers)
	for i, val := range finalArr {
		switch v := val.(type) {
		case float64:
			payoffs[i] = v
		case int:
			payoffs[i] = float64(v)
		default:
			return nil, fmt.Errorf("invalid payoff value type at leaf")
		}
	}
	return payoffs, nil
}

func (s *GameTheoryService) isNashEquilibrium(game *NormalFormGame, profile []int) bool {
	// For each player, check if they can strictly improve by unilaterally deviating
	currentPayoffs, err := s.getPayoffProfile(game.PayoffTensor, profile, len(game.Players))
	if err != nil {
		return false
	}

	for pIdx := 0; pIdx < len(game.Players); pIdx++ {
		currentVal := currentPayoffs[pIdx]
		
		// Check all other strategies for this player
		for altStrat := 0; altStrat < game.StrategyIndices[pIdx]; altStrat++ {
			if altStrat == profile[pIdx] {
				continue
			}
			
			devProfile := make([]int, len(profile))
			copy(devProfile, profile)
			devProfile[pIdx] = altStrat
			
			altPayoffs, err := s.getPayoffProfile(game.PayoffTensor, devProfile, len(game.Players))
			if err != nil {
				continue
			}
			
			if altPayoffs[pIdx] > currentVal {
				return false // Strictly better deviation exists
			}
		}
	}
	return true
}

func mathMaxFloat() float64 {
	return 1e308 // close enough to math.MaxFloat64 for pure constants
}
