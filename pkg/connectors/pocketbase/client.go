package pocketbase

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
	"sync"
	"time"
)

// Client is a lightweight PocketBase REST client with admin token auth.
// Critical: PocketBase v0.23+ requires the raw token in the Authorization
// header — NO "Admin" or "Bearer" prefix.
type Client struct {
	baseURL  string
	email    string
	password string
	authPath string // admin: /api/admins/auth-with-password | user: /api/collections/users/auth-with-password

	mu      sync.RWMutex
	token   string
	tokenAt time.Time

	http *http.Client
}

// NewClientFromEnv creates an admin Client from PB_BASE_URL, PB_ADMIN_EMAIL,
// PB_ADMIN_PASSWORD env vars.
func NewClientFromEnv() *Client {
	return &Client{
		baseURL:  strings.TrimRight(os.Getenv("PB_BASE_URL"), "/"),
		email:    os.Getenv("PB_ADMIN_EMAIL"),
		password: os.Getenv("PB_ADMIN_PASSWORD"),
		authPath: "/api/admins/auth-with-password",
		http:     &http.Client{Timeout: 20 * time.Second},
	}
}

// NewClient creates an admin Client with explicit credentials.
func NewClient(baseURL, email, password string) *Client {
	return &Client{
		baseURL:  strings.TrimRight(baseURL, "/"),
		email:    email,
		password: password,
		authPath: "/api/admins/auth-with-password",
		http:     &http.Client{Timeout: 20 * time.Second},
	}
}

// NewUserClient creates a user-scoped Client (non-admin) for a regular PocketBase
// user account. Uses /api/collections/users/auth-with-password.
// Records written with this client are owned by the authenticated user.
func NewUserClient(baseURL, email, password string) *Client {
	return &Client{
		baseURL:  strings.TrimRight(baseURL, "/"),
		email:    email,
		password: password,
		authPath: "/api/collections/users/auth-with-password",
		http:     &http.Client{Timeout: 20 * time.Second},
	}
}

// IsConfigured returns true if all required env vars are present.
func (c *Client) IsConfigured() bool {
	return c.baseURL != "" && c.email != "" && c.password != ""
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

type authResponse struct {
	Token string `json:"token"`
}

// authenticate fetches a fresh token and caches it.
func (c *Client) authenticate(ctx context.Context) error {
	body, _ := json.Marshal(map[string]string{
		"identity": c.email,
		"password": c.password,
	})
	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		c.baseURL+c.authPath, bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.http.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		b, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("pb auth failed %d: %s", resp.StatusCode, b)
	}

	var ar authResponse
	if err := json.NewDecoder(resp.Body).Decode(&ar); err != nil {
		return err
	}

	c.mu.Lock()
	c.token = ar.Token
	c.tokenAt = time.Now()
	c.mu.Unlock()
	return nil
}

// token returns the cached token, refreshing if needed.
func (c *Client) getToken(ctx context.Context) (string, error) {
	c.mu.RLock()
	tok := c.token
	age := time.Since(c.tokenAt)
	c.mu.RUnlock()

	// Tokens last ~1h in PocketBase; refresh after 50 min to be safe
	if tok == "" || age > 50*time.Minute {
		if err := c.authenticate(ctx); err != nil {
			return "", err
		}
		c.mu.RLock()
		tok = c.token
		c.mu.RUnlock()
	}
	return tok, nil
}

// ─── HTTP helpers ─────────────────────────────────────────────────────────────

func (c *Client) doJSON(ctx context.Context, method, path string, body any, out any) error {
	tok, err := c.getToken(ctx)
	if err != nil {
		return err
	}

	var bodyReader io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			return err
		}
		bodyReader = bytes.NewReader(b)
	}

	req, err := http.NewRequestWithContext(ctx, method, c.baseURL+path, bodyReader)
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", tok) // raw token, NO prefix
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	resp, err := c.http.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	// 401 → refresh token and retry once
	if resp.StatusCode == http.StatusUnauthorized {
		if err := c.authenticate(ctx); err != nil {
			return err
		}
		return c.doJSON(ctx, method, path, body, out)
	}

	respBody, _ := io.ReadAll(resp.Body)
	if resp.StatusCode >= 300 {
		return fmt.Errorf("pb %s %s → %d: %s", method, path, resp.StatusCode, respBody)
	}

	if out != nil && len(respBody) > 0 {
		return json.Unmarshal(respBody, out)
	}
	return nil
}

// ─── Collection Management ───────────────────────────────────────────────────

type FieldSchema struct {
	Name     string         `json:"name"`
	Type     string         `json:"type"`
	Required bool           `json:"required,omitempty"`
	Options  map[string]any `json:"options,omitempty"`
}

type CollectionSchema struct {
	Name   string        `json:"name"`
	Type   string        `json:"type"`
	Schema []FieldSchema `json:"schema"`
}

type collectionListResponse struct {
	Items []struct {
		Name string `json:"name"`
	} `json:"items"`
}

// CollectionExists checks if a named collection exists.
func (c *Client) CollectionExists(ctx context.Context, name string) (bool, error) {
	var list collectionListResponse
	err := c.doJSON(ctx, http.MethodGet, "/api/collections?perPage=200", nil, &list)
	if err != nil {
		return false, err
	}
	for _, item := range list.Items {
		if item.Name == name {
			return true, nil
		}
	}
	return false, nil
}

// CreateCollection creates a collection with the given schema.
func (c *Client) CreateCollection(ctx context.Context, schema CollectionSchema) error {
	return c.doJSON(ctx, http.MethodPost, "/api/collections", schema, nil)
}

// ─── Record Operations ───────────────────────────────────────────────────────

type RecordID struct {
	ID string `json:"id"`
}

// CreateRecord inserts a new record and returns the created ID.
func (c *Client) CreateRecord(ctx context.Context, collection string, data map[string]any) (string, error) {
	var result RecordID
	if err := c.doJSON(ctx, http.MethodPost,
		"/api/collections/"+collection+"/records", data, &result); err != nil {
		return "", err
	}
	return result.ID, nil
}

// UpdateRecord updates an existing record by ID.
func (c *Client) UpdateRecord(ctx context.Context, collection, id string, data map[string]any) error {
	return c.doJSON(ctx, http.MethodPatch,
		"/api/collections/"+collection+"/records/"+id, data, nil)
}

// DeleteRecord deletes a record by ID.
func (c *Client) DeleteRecord(ctx context.Context, collection, id string) error {
	return c.doJSON(ctx, http.MethodDelete,
		"/api/collections/"+collection+"/records/"+id, nil, nil)
}

// ListRecordsResponse is the PocketBase list response envelope.
type ListRecordsResponse struct {
	Page       int              `json:"page"`
	PerPage    int              `json:"perPage"`
	TotalItems int              `json:"totalItems"`
	TotalPages int              `json:"totalPages"`
	Items      []map[string]any `json:"items"`
}

// QueryRecords fetches records from a collection with optional filter/sort.
// filter uses PocketBase filter syntax, e.g. `topic = "golang"`.
func (c *Client) QueryRecords(ctx context.Context, collection string, filter, sort string, perPage int) (*ListRecordsResponse, error) {
	params := url.Values{}
	params.Set("perPage", fmt.Sprintf("%d", perPage))
	if filter != "" {
		params.Set("filter", filter)
	}
	if sort != "" {
		params.Set("sort", sort)
	}
	var result ListRecordsResponse
	path := "/api/collections/" + collection + "/records?" + params.Encode()
	if err := c.doJSON(ctx, http.MethodGet, path, nil, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// CountRecords returns the total record count for a collection.
func (c *Client) CountRecords(ctx context.Context, collection string) (int, error) {
	result, err := c.QueryRecords(ctx, collection, "", "", 1)
	if err != nil {
		return 0, err
	}
	return result.TotalItems, nil
}
