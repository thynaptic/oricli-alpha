package service

import (
	"github.com/thynaptic/oricli-go/pkg/memory"
	"github.com/thynaptic/oricli-go/pkg/rag"
)

type RagService struct {
	MemoryManager *memory.MemoryManager
}

func NewRagService() (*RagService, error) {
	mm, err := memory.NewMemoryManager()
	if err != nil {
		return nil, err
	}
	return &RagService{MemoryManager: mm}, nil
}

func (s *RagService) IngestText(text string, source string, metadata map[string]string) error {
	// Directly use the memory manager from P-LMv1
	return s.MemoryManager.AddKnowledge(text, metadata)
}

func (s *RagService) IngestFile(filePath string, opts rag.IndexOptions) (rag.IndexStats, error) {
	// For now, support single file by using a temp directory or direct read
	// P-LMv1 IndexDirectory is robust, we can leverage it
	return rag.IndexDirectory(s.MemoryManager, filePath, opts)
}
