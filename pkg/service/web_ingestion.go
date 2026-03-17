package service

import (
	"fmt"
	"log"
)

type WebIngestionService struct {
	Fetcher *WebFetchService
	Rag     *RagService
}

func NewWebIngestionService(fetcher *WebFetchService, rag *RagService) *WebIngestionService {
	return &WebIngestionService{
		Fetcher: fetcher,
		Rag:     rag,
	}
}

func (s *WebIngestionService) CrawlAndIngest(seedURL string, maxPages int, maxDepth int, metadata map[string]interface{}) (map[string]interface{}, error) {
	log.Printf("[WebIngest] Starting crawl for %s (max_pages=%d, max_depth=%d)", seedURL, maxPages, maxDepth)
	
	visited := make(map[string]bool)
	queue := []string{seedURL}
	ingestedURLs := []string{}

	for len(queue) > 0 && len(ingestedURLs) < maxPages {
		currentURL := queue[0]
		queue = queue[1:]

		if visited[currentURL] {
			continue
		}
		visited[currentURL] = true

		// 1. Fetch
		res := s.Fetcher.FetchURL(currentURL)
		if !res.Success {
			log.Printf("[WebIngest] Failed to fetch %s: %s", currentURL, res.Error)
			continue
		}

		// 2. Ingest into RAG
		meta := make(map[string]string)
		for k, v := range metadata {
			meta[k] = fmt.Sprintf("%v", v)
		}
		meta["source"] = currentURL
		meta["title"] = res.Title
		
		err := s.Rag.IngestText(res.Content, currentURL, meta)
		if err != nil {
			log.Printf("[WebIngest] Failed to ingest %s: %v", currentURL, err)
			continue
		}

		ingestedURLs = append(ingestedURLs, currentURL)
		log.Printf("[WebIngest] Ingested %s (%d/%d)", currentURL, len(ingestedURLs), maxPages)
	}

	return map[string]interface{}{
		"success":        true,
		"seed_url":       seedURL,
		"pages_ingested": len(ingestedURLs),
		"urls":           ingestedURLs,
	}, nil
}
