package service

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"os"
	"runtime"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/PowerDNS/lmdb-go/lmdb"
)

type MemoryCategory string

const (
	Semantic      MemoryCategory = "semantic"
	Episodic      MemoryCategory = "episodic"
	Identity      MemoryCategory = "identity"
	Skill         MemoryCategory = "skill"
	LongTermState MemoryCategory = "long_term_state"
	ReflectionLog MemoryCategory = "reflection_log"
	VectorIndex   MemoryCategory = "vector_index"
	TemporalIndex MemoryCategory = "temporal_index"
)

type MemoryRecord struct {
	SchemaVersion int                    `json:"schema_version"`
	Category      string                 `json:"category"`
	ID            string                 `json:"id"`
	Data          map[string]interface{} `json:"data,omitempty"`
	Metadata      map[string]interface{} `json:"metadata"`
	UpdatedAt     float64                `json:"updated_at"`
	Vector        []float32              `json:"vector,omitempty"`
}

type MemoryBridge struct {
	Env           *lmdb.Env
	DBs           map[MemoryCategory]lmdb.DBI
	EncryptionKey []byte
	GCM           cipher.AEAD
	Mu            sync.RWMutex
}

func NewMemoryBridge(path string, encryptionKeyBase64 string) (*MemoryBridge, error) {
	// 1. Setup Encryption
	key, err := decodeKey(encryptionKeyBase64)
	if err != nil {
		return nil, fmt.Errorf("invalid encryption key: %w", err)
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}

	aesgcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}

	// 2. Setup LMDB
	if err := os.MkdirAll(path, 0755); err != nil {
		return nil, err
	}

	env, err := lmdb.NewEnv()
	if err != nil {
		return nil, err
	}

	// 512MB default map size matching Python
	err = env.SetMapSize(512 * 1024 * 1024)
	if err != nil {
		return nil, err
	}

	err = env.SetMaxDBs(16)
	if err != nil {
		return nil, err
	}

	err = env.Open(path, 0, 0644)
	if err != nil {
		return nil, err
	}

	mb := &MemoryBridge{
		Env:           env,
		DBs:           make(map[MemoryCategory]lmdb.DBI),
		EncryptionKey: key,
		GCM:           aesgcm,
	}

	// 3. Open Databases
	categories := []MemoryCategory{Semantic, Episodic, Identity, Skill, LongTermState, ReflectionLog, VectorIndex, TemporalIndex}
	err = env.Update(func(txn *lmdb.Txn) error {
		for _, cat := range categories {
			dbi, err := txn.OpenDBI(string(cat), lmdb.Create)
			if err != nil {
				return err
			}
			mb.DBs[cat] = dbi
		}
		return nil
	})

	if err != nil {
		return nil, err
	}

	return mb, nil
}

func decodeKey(keyStr string) ([]byte, error) {
	// Support both standard and URL-safe base64
	key, err := base64.StdEncoding.DecodeString(keyStr)
	if err != nil {
		key, err = base64.URLEncoding.DecodeString(keyStr)
	}
	if err != nil {
		// Try raw hex if base64 fails
		return base64.URLEncoding.DecodeString(keyStr) // Fallback handled by caller
	}
	if len(key) != 32 {
		return nil, fmt.Errorf("key must be 32 bytes for AES-256")
	}
	return key, nil
}

func (mb *MemoryBridge) Put(category MemoryCategory, id string, data map[string]interface{}, metadata map[string]interface{}) error {
	record := MemoryRecord{
		SchemaVersion: 1,
		Category:      string(category),
		ID:            id,
		Data:          data,
		Metadata:      metadata,
		UpdatedAt:     float64(time.Now().UnixNano()) / 1e9,
	}

	payload, err := json.Marshal(record)
	if err != nil {
		return err
	}

	// Encrypt: [version_byte(1)][nonce(12)][ciphertext]
	nonce := make([]byte, 12)
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return err
	}

	// AAD matching Python: category:id
	aad := []byte(fmt.Sprintf("%s:%s", category, id))
	ciphertext := mb.GCM.Seal(nil, nonce, payload, aad)

	finalValue := append([]byte{1}, nonce...)
	finalValue = append(finalValue, ciphertext...)

	return mb.Env.Update(func(txn *lmdb.Txn) error {
		// 1. Store main record
		dbi := mb.DBs[category]
		if err := txn.Put(dbi, []byte(id), finalValue, 0); err != nil {
			return err
		}

		// 2. Index by time
		timeDbi := mb.DBs[TemporalIndex]
		timeKey := make([]byte, 8)
		binary.BigEndian.PutUint64(timeKey, math.Float64bits(record.UpdatedAt))
		timeVal := []byte(fmt.Sprintf("%s:%s", category, id))

		return txn.Put(timeDbi, timeKey, timeVal, 0)
	})
}

func (mb *MemoryBridge) Get(category MemoryCategory, id string) (*MemoryRecord, error) {
	var record *MemoryRecord
	err := mb.Env.View(func(txn *lmdb.Txn) error {
		var err error
		record, err = mb.getWithTxn(txn, category, id)
		return err
	})
	return record, err
}

func (mb *MemoryBridge) getWithTxn(txn *lmdb.Txn, category MemoryCategory, id string) (*MemoryRecord, error) {
	dbi := mb.DBs[category]
	val, err := txn.Get(dbi, []byte(id))
	if lmdb.IsNotFound(err) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	if len(val) < 13 {
		return nil, fmt.Errorf("invalid memory blob")
	}

	// Decrypt
	nonce := val[1:13]
	ciphertext := val[13:]
	aad := []byte(fmt.Sprintf("%s:%s", category, id))

	plaintext, err := mb.GCM.Open(nil, nonce, ciphertext, aad)
	if err != nil {
		return nil, fmt.Errorf("decryption failed: %w", err)
	}

	var record MemoryRecord
	if err := json.Unmarshal(plaintext, &record); err != nil {
		return nil, err
	}

	return &record, nil
}

// QueryTemporal retrieves records within a specific time range [startTime, endTime].
func (mb *MemoryBridge) QueryTemporal(startTime, endTime float64) ([]MemoryRecord, error) {
	var records []MemoryRecord

	err := mb.Env.View(func(txn *lmdb.Txn) error {
		dbi := mb.DBs[TemporalIndex]
		cur, err := txn.OpenCursor(dbi)
		if err != nil {
			return err
		}
		defer cur.Close()

		startKey := make([]byte, 8)
		binary.BigEndian.PutUint64(startKey, math.Float64bits(startTime))

		k, v, err := cur.Get(startKey, nil, lmdb.SetRange)
		if lmdb.IsNotFound(err) {
			return nil
		}
		if err != nil {
			return err
		}

		for {
			ts := math.Float64frombits(binary.BigEndian.Uint64(k))
			if ts > endTime {
				break
			}

			parts := strings.Split(string(v), ":")
			if len(parts) == 2 {
				cat := MemoryCategory(parts[0])
				id := parts[1]
				rec, err := mb.getWithTxn(txn, cat, id)
				if err == nil && rec != nil {
					records = append(records, *rec)
				}
			}

			k, v, err = cur.Get(nil, nil, lmdb.Next)
			if lmdb.IsNotFound(err) {
				break
			}
			if err != nil {
				return err
			}
		}
		return nil
	})

	return records, err
}

type VectorResult struct {
	ID       string                 `json:"id"`
	Score    float32                `json:"score"`
	Metadata map[string]interface{} `json:"metadata"`
}

// VectorSearch performs parallel brute-force cosine similarity search
func (mb *MemoryBridge) VectorSearch(queryVector []float32, topK int, minScore float32) ([]VectorResult, error) {
	var records []MemoryRecord

	// 1. Fetch all vectors from LMDB (This is the I/O part)
	err := mb.Env.View(func(txn *lmdb.Txn) error {
		dbi := mb.DBs[VectorIndex]
		cur, err := txn.OpenCursor(dbi)
		if err != nil {
			return err
		}
		defer cur.Close()

		for {
			k, v, err := cur.Get(nil, nil, lmdb.Next)
			if lmdb.IsNotFound(err) {
				break
			}
			if err != nil {
				return err
			}

			// Decrypt each record
			id := string(k)
			nonce := v[1:13]
			ciphertext := v[13:]
			aad := []byte(fmt.Sprintf("%s:%s", VectorIndex, id))

			plaintext, err := mb.GCM.Open(nil, nonce, ciphertext, aad)
			if err != nil {
				continue // Skip corrupt records
			}

			var rec MemoryRecord
			if err := json.Unmarshal(plaintext, &rec); err == nil {
				records = append(records, rec)
			}
		}
		return nil
	})

	if err != nil {
		return nil, err
	}

	// 2. Parallel Similarity Search
	numCPU := runtime.NumCPU()
	chunkSize := (len(records) + numCPU - 1) / numCPU
	resultsChan := make(chan []VectorResult, numCPU)
	var wg sync.WaitGroup

	for i := 0; i < len(records); i += chunkSize {
		end := i + chunkSize
		if end > len(records) {
			end = len(records)
		}

		wg.Add(1)
		go func(subset []MemoryRecord) {
			defer wg.Done()
			var localResults []VectorResult
			for _, rec := range subset {
				if len(rec.Vector) != len(queryVector) {
					continue
				}
				score := cosineSimilarity(queryVector, rec.Vector)
				if score >= minScore {
					localResults = append(localResults, VectorResult{
						ID:       rec.ID,
						Score:    score,
						Metadata: rec.Metadata,
					})
				}
			}
			resultsChan <- localResults
		}(records[i:end])
	}

	go func() {
		wg.Wait()
		close(resultsChan)
	}()

	var allResults []VectorResult
	for res := range resultsChan {
		allResults = append(allResults, res...)
	}

	// 3. Sort and limit
	sort.Slice(allResults, func(i, j int) bool {
		return allResults[i].Score > allResults[j].Score
	})

	if len(allResults) > topK {
		allResults = allResults[:topK]
	}

	return allResults, nil
}

func cosineSimilarity(v1, v2 []float32) float32 {
	var dot, norm1, norm2 float32
	for i := range v1 {
		dot += v1[i] * v2[i]
		norm1 += v1[i] * v1[i]
		norm2 += v2[i] * v2[i]
	}
	if norm1 == 0 || norm2 == 0 {
		return 0
	}
	return dot / (float32(math.Sqrt(float64(norm1))) * float32(math.Sqrt(float64(norm2))))
}

func (mb *MemoryBridge) Close() {
	if mb.Env != nil {
		mb.Env.Close()
	}
}
