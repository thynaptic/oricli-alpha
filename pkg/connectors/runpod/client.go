package runpod

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

const (
	GraphQLEndpoint = "https://api.runpod.io/graphql"
)

// GPUType represents a RunPod GPU type.
type GPUType struct {
	ID             string  `json:"id"`
	DisplayName    string  `json:"displayName"`
	MemoryInGb     int     `json:"memoryInGb"`
	SecurePrice    float64 `json:"securePrice"`
	CommunityPrice float64 `json:"communityPrice"`
}

// Pod represents a RunPod pod.
type Pod struct {
	ID            string `json:"id"`
	Name          string `json:"name"`
	DesiredStatus string `json:"desiredStatus"`
}

// Client handles communication with the RunPod API.
type Client struct {
	APIKey     string
	HTTPClient *http.Client
}

// NewClient creates a new RunPod API client.
func NewClient(apiKey string) *Client {
	return &Client{
		APIKey: apiKey,
		HTTPClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// Query performs a GraphQL query against the RunPod API.
func (c *Client) Query(query string, variables map[string]interface{}) (map[string]interface{}, error) {
	reqBody, err := json.Marshal(map[string]interface{}{
		"query":     query,
		"variables": variables,
	})
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequest("POST", GraphQLEndpoint, bytes.NewBuffer(reqBody))
	if err != nil {
		return nil, err
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.APIKey))

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("HTTP error: %d %s", resp.StatusCode, resp.Status)
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	if errors, ok := result["errors"].([]interface{}); ok && len(errors) > 0 {
		return nil, fmt.Errorf("GraphQL error: %v", errors[0])
	}

	return result, nil
}

// GetGPUTypes retrieves the available GPU types from RunPod.
func (c *Client) GetGPUTypes() ([]GPUType, error) {
	query := `query { gpuTypes { id displayName memoryInGb securePrice communityPrice } }`
	result, err := c.Query(query, nil)
	if err != nil {
		return nil, err
	}

	data, ok := result["data"].(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("unexpected response format")
	}

	gpuTypesData, ok := data["gpuTypes"].([]interface{})
	if !ok {
		return nil, fmt.Errorf("unexpected response format")
	}

	var gpuTypes []GPUType
	for _, g := range gpuTypesData {
		gMap := g.(map[string]interface{})
		gpuTypes = append(gpuTypes, GPUType{
			ID:             gMap["id"].(string),
			DisplayName:    gMap["displayName"].(string),
			MemoryInGb:     int(gMap["memoryInGb"].(float64)),
			SecurePrice:    gMap["securePrice"].(float64),
			CommunityPrice: gMap["communityPrice"].(float64),
		})
	}

	return gpuTypes, nil
}

// GetPods retrieves the user's active pods from RunPod.
func (c *Client) GetPods() ([]Pod, error) {
	query := `query { myself { pods { id name desiredStatus } } }`
	result, err := c.Query(query, nil)
	if err != nil {
		return nil, err
	}

	data, ok := result["data"].(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("unexpected response format")
	}

	myself, ok := data["myself"].(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("unexpected response format")
	}

	podsData, ok := myself["pods"].([]interface{})
	if !ok {
		return nil, fmt.Errorf("unexpected response format")
	}

	var pods []Pod
	for _, p := range podsData {
		pMap := p.(map[string]interface{})
		pods = append(pods, Pod{
			ID:            pMap["id"].(string),
			Name:          pMap["name"].(string),
			DesiredStatus: pMap["desiredStatus"].(string),
		})
	}

	return pods, nil
}

// CreatePod creates a new on-demand pod.
func (c *Client) CreatePod(name, gpuTypeId, imageName string) (*Pod, error) {
	query := `
	mutation CreatePod($input: PodFindAndDeployOnDemandInput!) {
		podFindAndDeployOnDemand(input: $input) {
			id
			name
		}
	}`

	variables := map[string]interface{}{
		"input": map[string]interface{}{
			"name":              name,
			"gpuTypeId":         gpuTypeId,
			"gpuCount":          1,
			"cloudType":         "SECURE",
			"volumeInGb":        50,
			"containerDiskInGb": 50,
			"volumeMountPath":   "/workspace",
			"imageName":         imageName,
			"ports":             "22/tcp",
			"dockerArgs":        "",
		},
	}

	result, err := c.Query(query, variables)
	if err != nil {
		return nil, err
	}

	data, ok := result["data"].(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("unexpected response format")
	}

	podData, ok := data["podFindAndDeployOnDemand"].(map[string]interface{})
	if !ok || podData == nil {
		return nil, fmt.Errorf("failed to create pod, response may be empty")
	}

	return &Pod{
		ID:   podData["id"].(string),
		Name: podData["name"].(string),
	}, nil
}

// TerminatePod terminates an existing pod by its ID.
func (c *Client) TerminatePod(podId string) error {
	query := `
	mutation TerminatePod($input: PodTerminateInput!) {
		podTerminate(input: $input)
	}`

	variables := map[string]interface{}{
		"input": map[string]interface{}{
			"podId": podId,
		},
	}

	_, err := c.Query(query, variables)
	return err
}
