// Package memory is the consumer memory stack for ori-capsule.
//
// Durable warm store: bbolt (pure Go stand-in for monorepo LMDB MemoryBridge —
// keeps CGO_ENABLED=0 / distroless). No PocketBase, Neo4j, chromem, or sync
// embeds on the chat hot path.
package memory

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sync"
	"time"

	bolt "go.etcd.io/bbolt"
)

// Categories mirror monorepo MemoryBridge buckets.
const (
	CatSemantic      = "semantic"
	CatEpisodic      = "episodic"
	CatIdentity      = "identity"
	CatSkill         = "skill"
	CatLongTermState = "long_term_state"
	CatReflectionLog = "reflection_log"
	CatSessions      = "sessions"
	CatMeta          = "meta"
)

var bridgeBuckets = []string{
	CatSemantic, CatEpisodic, CatIdentity, CatSkill,
	CatLongTermState, CatReflectionLog, CatSessions, CatMeta,
}

// Record is one encrypted KV payload.
type Record struct {
	SchemaVersion int            `json:"schema_version"`
	Category      string         `json:"category"`
	ID            string         `json:"id"`
	Data          map[string]any `json:"data,omitempty"`
	Metadata      map[string]any `json:"metadata,omitempty"`
	UpdatedAt     float64        `json:"updated_at"`
}

// Bridge is an encrypted multi-bucket warm store (LMDB-equivalent for capsule).
type Bridge struct {
	db  *bolt.DB
	gcm cipher.AEAD
	mu  sync.RWMutex
}

// OpenBridge opens (or creates) the warm store under dir/bridge.bbolt.
// encryptionKeyBase64 must decode to 32 bytes, or pass empty to derive a
// disposable key from dir (dev-only; set ORI_MEMORY_ENCRYPTION_KEY in real use).
func OpenBridge(dir, encryptionKeyBase64 string) (*Bridge, error) {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, err
	}
	key, err := resolveKey(encryptionKeyBase64, dir)
	if err != nil {
		return nil, err
	}
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	path := filepath.Join(dir, "bridge.bbolt")
	db, err := bolt.Open(path, 0o600, &bolt.Options{Timeout: 2 * time.Second})
	if err != nil {
		return nil, err
	}
	b := &Bridge{db: db, gcm: gcm}
	err = db.Update(func(tx *bolt.Tx) error {
		for _, name := range bridgeBuckets {
			if _, e := tx.CreateBucketIfNotExists([]byte(name)); e != nil {
				return e
			}
		}
		return nil
	})
	if err != nil {
		_ = db.Close()
		return nil, err
	}
	return b, nil
}

func resolveKey(b64, dir string) ([]byte, error) {
	if b64 == "" {
		sum := sha256.Sum256([]byte("ori-capsule-dev:" + dir))
		return sum[:], nil
	}
	key, err := base64.StdEncoding.DecodeString(b64)
	if err != nil {
		key, err = base64.URLEncoding.DecodeString(b64)
	}
	if err != nil {
		return nil, fmt.Errorf("ORI_MEMORY_ENCRYPTION_KEY: %w", err)
	}
	if len(key) != 32 {
		return nil, fmt.Errorf("ORI_MEMORY_ENCRYPTION_KEY must decode to 32 bytes")
	}
	return key, nil
}

func (b *Bridge) Close() error {
	if b == nil || b.db == nil {
		return nil
	}
	return b.db.Close()
}

func (b *Bridge) Put(category, id string, data, metadata map[string]any) error {
	rec := Record{
		SchemaVersion: 1,
		Category:      category,
		ID:            id,
		Data:          data,
		Metadata:      metadata,
		UpdatedAt:     float64(time.Now().UnixNano()) / 1e9,
	}
	payload, err := json.Marshal(rec)
	if err != nil {
		return err
	}
	nonce := make([]byte, b.gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return err
	}
	aad := []byte(category + ":" + id)
	ct := b.gcm.Seal(nil, nonce, payload, aad)
	blob := append([]byte{1}, nonce...)
	blob = append(blob, ct...)
	return b.db.Update(func(tx *bolt.Tx) error {
		bucket := tx.Bucket([]byte(category))
		if bucket == nil {
			return fmt.Errorf("unknown category %q", category)
		}
		return bucket.Put([]byte(id), blob)
	})
}

func (b *Bridge) Get(category, id string) (*Record, error) {
	var out *Record
	err := b.db.View(func(tx *bolt.Tx) error {
		bucket := tx.Bucket([]byte(category))
		if bucket == nil {
			return fmt.Errorf("unknown category %q", category)
		}
		val := bucket.Get([]byte(id))
		if val == nil {
			return nil
		}
		rec, err := b.decrypt(category, id, val)
		if err != nil {
			return err
		}
		out = rec
		return nil
	})
	return out, err
}

func (b *Bridge) decrypt(category, id string, val []byte) (*Record, error) {
	ns := b.gcm.NonceSize()
	if len(val) < 1+ns {
		return nil, fmt.Errorf("invalid memory blob")
	}
	nonce := val[1 : 1+ns]
	ct := val[1+ns:]
	aad := []byte(category + ":" + id)
	pt, err := b.gcm.Open(nil, nonce, ct, aad)
	if err != nil {
		return nil, fmt.Errorf("decryption failed: %w", err)
	}
	var rec Record
	if err := json.Unmarshal(pt, &rec); err != nil {
		return nil, err
	}
	return &rec, nil
}
