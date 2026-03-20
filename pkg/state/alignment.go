package state

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// --- Pillar 39: Alignment Lesson Logger ---
// Captures (prompt, rejected, chosen) triplets for RFAL fine-tuning.

const defaultAlignmentLessonPath = ".memory/alignment_lessons.jsonl"

type AlignmentLesson struct {
	Prompt    string    `json:"prompt"`
	Rejected  string    `json:"rejected"`
	Chosen    string    `json:"chosen"`
	Score     float64   `json:"score"`
	Timestamp time.Time `json:"timestamp"`
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
}

type AlignmentLogger struct {
	Path string
	mu   sync.Mutex
}

func NewAlignmentLogger(path string) *AlignmentLogger {
	if path == "" {
		path = defaultAlignmentLessonPath
	}
	return &AlignmentLogger{Path: path}
}

// LogLesson appends a new DPO pair to the jsonl lesson buffer.
func (l *AlignmentLogger) LogLesson(lesson AlignmentLesson) error {
	l.mu.Lock()
	defer l.mu.Unlock()

	lesson.Timestamp = time.Now().UTC()

	if err := os.MkdirAll(filepath.Dir(l.Path), 0755); err != nil {
		return err
	}

	f, err := os.OpenFile(l.Path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	defer f.Close()

	data, err := json.Marshal(lesson)
	if err != nil {
		return err
	}

	if _, err := f.Write(append(data, '\n')); err != nil {
		return err
	}

	return nil
}
