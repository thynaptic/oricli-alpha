package audit

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// repoFile is a file entry from the GitHub Trees/Contents API.
type repoFile struct {
	Name        string `json:"name"`
	Path        string `json:"path"`
	DownloadURL string `json:"download_url"`
	Type        string `json:"type"` // "file" | "dir"
	URL         string `json:"url"`  // API URL (for dirs)
}

// githubFileClient fetches file listings and content from the GitHub API.
type githubFileClient struct {
	token  string
	client *http.Client
}

func newGitHubFileClient(token string) *githubFileClient {
	return &githubFileClient{
		token:  token,
		client: &http.Client{Timeout: 30 * time.Second},
	}
}

const ghAPIBase = "https://api.github.com"
const auditRepo = "thynaptic/oricli-alpha"

// fetchFileList recursively lists all files under path in the repo.
func (c *githubFileClient) fetchFileList(ctx context.Context, path string) ([]repoFile, error) {
	url := fmt.Sprintf("%s/repos/%s/contents/%s", ghAPIBase, auditRepo, path)
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}
	if c.token != "" {
		req.Header.Set("Authorization", "Bearer "+c.token)
	}
	req.Header.Set("Accept", "application/vnd.github+json")

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var entries []repoFile
	if err := json.Unmarshal(body, &entries); err != nil {
		return nil, fmt.Errorf("fetchFileList parse: %w (status %d)", err, resp.StatusCode)
	}

	// Recurse into subdirectories
	var all []repoFile
	for _, entry := range entries {
		if entry.Type == "dir" {
			sub, err := c.fetchFileList(ctx, entry.Path)
			if err != nil {
				continue
			}
			all = append(all, sub...)
		} else {
			all = append(all, entry)
		}
	}
	return all, nil
}

// fetchFileContent downloads raw file content from download_url.
func (c *githubFileClient) fetchFileContent(ctx context.Context, downloadURL string) (string, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, downloadURL, nil)
	if err != nil {
		return "", err
	}
	if c.token != "" {
		req.Header.Set("Authorization", "Bearer "+c.token)
	}
	resp, err := c.client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	return string(body), err
}

// ---------------------------------------------------------------------------
// getDefaultBranchSHA returns the SHA of the tip of the default branch (main).
// Used by GitHubBot to create new branches from.
// ---------------------------------------------------------------------------

func (c *githubFileClient) getDefaultBranchSHA(ctx context.Context) (string, error) {
	url := fmt.Sprintf("%s/repos/%s/git/refs/heads/main", ghAPIBase, auditRepo)
	req, _ := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if c.token != "" {
		req.Header.Set("Authorization", "Bearer "+c.token)
	}
	req.Header.Set("Accept", "application/vnd.github+json")
	resp, err := c.client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	var result struct {
		Object struct {
			SHA string `json:"sha"`
		} `json:"object"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", err
	}
	return result.Object.SHA, nil
}

// ---------------------------------------------------------------------------
// createBranch creates a new branch from baseSHA.
// ---------------------------------------------------------------------------

func (c *githubFileClient) createBranch(ctx context.Context, branch, baseSHA string) error {
	payload := map[string]string{"ref": "refs/heads/" + branch, "sha": baseSHA}
	body, _ := json.Marshal(payload)
	url := fmt.Sprintf("%s/repos/%s/git/refs", ghAPIBase, auditRepo)
	req, _ := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	req.Header.Set("Authorization", "Bearer "+c.token)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/vnd.github+json")
	resp, err := c.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		b, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("createBranch: HTTP %d — %s", resp.StatusCode, string(b))
	}
	return nil
}

// commitFile creates or updates a single file on the given branch.
// content should be the raw file content (not base64 — this function encodes it).
func (c *githubFileClient) commitFile(ctx context.Context, branch, path, message, content string) error {
	import64 := encodeBase64(content)
	payload := map[string]interface{}{
		"message": message,
		"content": import64,
		"branch":  branch,
	}
	body, _ := json.Marshal(payload)
	url := fmt.Sprintf("%s/repos/%s/contents/%s", ghAPIBase, auditRepo, path)
	req, _ := http.NewRequestWithContext(ctx, http.MethodPut, url, bytes.NewReader(body))
	req.Header.Set("Authorization", "Bearer "+c.token)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/vnd.github+json")
	resp, err := c.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		b, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("commitFile(%s): HTTP %d — %s", path, resp.StatusCode, string(b))
	}
	return nil
}

// openPR creates a pull request from branch into main.
// Returns the PR HTML URL.
func (c *githubFileClient) openPR(ctx context.Context, branch, title, body string) (string, error) {
	payload := map[string]interface{}{
		"title": title,
		"head":  branch,
		"base":  "main",
		"body":  body,
	}
	data, _ := json.Marshal(payload)
	url := fmt.Sprintf("%s/repos/%s/pulls", ghAPIBase, auditRepo)
	req, _ := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(data))
	req.Header.Set("Authorization", "Bearer "+c.token)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/vnd.github+json")
	resp, err := c.client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	var result struct {
		HTMLURL string `json:"html_url"`
		Number  int    `json:"number"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", err
	}
	if result.HTMLURL == "" {
		return "", fmt.Errorf("openPR: empty html_url in response")
	}
	return result.HTMLURL, nil
}

// encodeBase64 base64-encodes content for the GitHub Contents API.
func encodeBase64(s string) string {
	return base64.StdEncoding.EncodeToString([]byte(s))
}
