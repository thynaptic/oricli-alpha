package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"sync"
	"time"
)

const (
	baseURL = "http://localhost:8089/v1"
)

type BenchResult struct {
	Operation string
	Latency   time.Duration
	Success   bool
	Error     string
}

func main() {
	fmt.Println("🚀 Starting Oricli-Alpha Native Swarm Benchmark")
	fmt.Println("Target: 32-Core EPYC VPS | Backbone: Go Native")
	fmt.Println("--------------------------------------------------")

	// 1. Warmup Latency (Single Request)
	fmt.Print("Phase 1: Warmup Latency...")
	warmupStart := time.Now()
	testHealth()
	fmt.Printf(" Done (%v)\n", time.Since(warmupStart))

	// 2. Concurrency Stress (The Scream Test)
	concurrency := 5
	fmt.Printf("Phase 2: Concurrency Stress (%d parallel CFPs)...\n", concurrency)
	
	results := make([]BenchResult, concurrency)
	var wg sync.WaitGroup
	stressStart := time.Now()

	for i := 0; i < concurrency; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			start := time.Now()
			success, err := runSwarmQuery("What is the benefit of Go concurrency?")
			results[idx] = BenchResult{
				Operation: "swarm_run",
				Latency:   time.Since(start),
				Success:   success,
			}
			if err != nil {
				results[idx].Error = err.Error()
			}
		}(i)
	}
	wg.Wait()
	stressDuration := time.Since(stressStart)

	// 3. RAG Recall Latency
	fmt.Print("Phase 3: RAG Recall Latency...")
	ragStart := time.Now()
	runRecallQuery("The secret code is BLAZE-2026")
	fmt.Printf(" Done (%v)\n", time.Since(ragStart))

	// Analysis
	printAnalysis(results, stressDuration)
}

func testHealth() bool {
	resp, err := http.Get(baseURL + "/health")
	if err != nil { return false }
	defer resp.Body.Close()
	return resp.StatusCode == 200
}

func runSwarmQuery(query string) (bool, error) {
	payload := map[string]interface{}{
		"operation": "reason",
		"params": map[string]interface{}{
			"query": query,
		},
	}
	data, _ := json.Marshal(payload)
	resp, err := http.Post(baseURL+"/swarm/run", "application/json", bytes.NewReader(data))
	if err != nil { return false, err }
	defer resp.Body.Close()
	
	var res map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&res)
	return res["success"] == true, nil
}

func runRecallQuery(query string) (bool, error) {
	resp, err := http.Get(baseURL + "/knowledge/world/query?query=" + query)
	if err != nil { return false, err }
	defer resp.Body.Close()
	return resp.StatusCode == 200, nil
}

func printAnalysis(results []BenchResult, totalTime time.Duration) {
	successCount := 0
	var totalLatency time.Duration
	maxLatency := time.Duration(0)
	minLatency := totalTime

	for _, r := range results {
		if r.Success {
			successCount++
			totalLatency += r.Latency
			if r.Latency > maxLatency { maxLatency = r.Latency }
			if r.Latency < minLatency { minLatency = r.Latency }
		}
	}

	avgLatency := time.Duration(0)
	if successCount > 0 {
		avgLatency = totalLatency / time.Duration(successCount)
	}

	fmt.Println("--------------------------------------------------")
	fmt.Printf("STRESS TEST COMPLETE in %v\n", totalTime)
	fmt.Printf("Total Requests: %d\n", len(results))
	fmt.Printf("Success Rate:   %.1f%%\n", float64(successCount)/float64(len(results))*100)
	fmt.Printf("Avg Latency:    %v\n", avgLatency)
	fmt.Printf("Min Latency:    %v\n", minLatency)
	fmt.Printf("Max Latency:    %v\n", maxLatency)
	fmt.Printf("Throughput:     %.2f req/s\n", float64(len(results))/totalTime.Seconds())
	fmt.Println("--------------------------------------------------")
}
