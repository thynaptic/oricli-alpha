package arc

// ARCResult represents the result of an ARC solve attempt
type ARCResult struct {
	Prediction Grid    `json:"prediction"`
	Confidence float64 `json:"confidence"`
	Method     string  `json:"method"`
	Program    string  `json:"program,omitempty"`
}
