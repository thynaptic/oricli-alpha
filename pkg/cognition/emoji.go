package cognition

import (
	"math"
	"strings"
	"time"
)

// --- Pillar 27: Emoji Emotion Detection ---
// Ported from Aurora's EmojiEmotionDetector.swift.
// Extracts affective signals from non-verbal Unicode symbols.

type EmojiEmotion string

const (
	EmojiHappy      EmojiEmotion = "happy"
	EmojiSad        EmojiEmotion = "sad"
	EmojiAngry      EmojiEmotion = "angry"
	EmojiExcited    EmojiEmotion = "excited"
	EmojiAnxious    EmojiEmotion = "anxious"
	EmojiLove       EmojiEmotion = "love"
	EmojiCrying     EmojiEmotion = "crying"
	EmojiDespair    EmojiEmotion = "despair"
	EmojiFrustrated EmojiEmotion = "frustrated"
	EmojiConfused   EmojiEmotion = "confused"
	EmojiSurprised  EmojiEmotion = "surprised"
	EmojiTired      EmojiEmotion = "tired"
	EmojiSick       EmojiEmotion = "sick"
	EmojiNeutral    EmojiEmotion = "neutral"
	EmojiNone       EmojiEmotion = "none"
)

type EmojiState struct {
	DominantEmotion  EmojiEmotion `json:"dominant_emotion"`
	DetectedEmojis   []string     `json:"detected_emojis"`
	IsEmojiOnly      bool         `json:"is_emoji_only"`
	Intensity        float64      `json:"intensity"`
	DistressSeverity float64      `json:"distress_severity"`
	Confidence       float64      `json:"confidence"`
	Timestamp        time.Time    `json:"timestamp"`
}

type EmojiEngine struct {
	EmojiMap map[string]EmojiEmotion
}

func NewEmojiEngine() *EmojiEngine {
	e := &EmojiEngine{
		EmojiMap: make(map[string]EmojiEmotion),
	}
	e.loadEmojiMappings()
	return e
}

func (e *EmojiEngine) loadEmojiMappings() {
	// Ported from Swift emojiEmotionMap
	happy := []string{"😊", "😄", "😃", "😁", "😆", "😂", "🤣", "😉", "😎", "🥳", "😋", "😌", "🙂", "😀", "😇", "🤗", "🤩", "😏"}
	for _, s := range happy { e.EmojiMap[s] = EmojiHappy }

	sad := []string{"😢", "😔", "😞", "😟", "😕", "🙁", "☹️", "😓", "😥", "😪"}
	for _, s := range sad { e.EmojiMap[s] = EmojiSad }

	crying := []string{"😭", "🥺"}
	for _, s := range crying { e.EmojiMap[s] = EmojiCrying }

	despair := []string{"💔"}
	for _, s := range despair { e.EmojiMap[s] = EmojiDespair }

	anxious := []string{"😰", "😨", "😱", "😖", "😣", "😧", "😦"}
	for _, s := range anxious { e.EmojiMap[s] = EmojiAnxious }

	angry := []string{"😠", "😡", "🤬", "💢", "👿", "😾"}
	for _, s := range angry { e.EmojiMap[s] = EmojiAngry }

	love := []string{"❤️", "💕", "💖", "💗", "💓", "💞", "💝", "💘", "💟", "😍", "🥰", "😘"}
	for _, s := range love { e.EmojiMap[s] = EmojiLove }

	excited := []string{"🎉", "🎊", "🎈", "🚀", "⚡", "🔥", "✨", "🌟"}
	for _, s := range excited { e.EmojiMap[s] = EmojiExcited }

	confused := []string{"😵", "😵‍💫", "🤷", "🤷‍♀️", "🤷‍♂️"}
	for _, s := range confused { e.EmojiMap[s] = EmojiConfused }
}

// Detect analyzes the text for emoji-based emotional signals.
func (e *EmojiEngine) Detect(text string) EmojiState {
	detected := e.extractEmojis(text)
	if len(detected) == 0 {
		return EmojiState{DominantEmotion: EmojiNone, Timestamp: time.Now()}
	}

	// 1. Check if Emoji-Only
	trimmed := strings.TrimSpace(text)
	for _, emoji := range detected {
		trimmed = strings.ReplaceAll(trimmed, emoji, "")
	}
	isEmojiOnly := strings.TrimSpace(trimmed) == ""

	// 2. Map to Emotions & Determine Dominant
	counts := make(map[EmojiEmotion]int)
	uniqueEmotions := 0
	for _, emoji := range detected {
		if emo, ok := e.EmojiMap[emoji]; ok {
			if counts[emo] == 0 {
				uniqueEmotions++
			}
			counts[emo]++
		}
	}

	dominant := EmojiNone
	maxCount := 0
	for emo, count := range counts {
		if count > maxCount {
			maxCount = count
			dominant = emo
		}
	}

	// 3. Intensity & Severity (Ported heuristics)
	intensity := math.Min(1.0, (float64(len(detected))/5.0)*0.5+(float64(uniqueEmotions)/3.0)*0.5)
	
	severity := 0.0
	switch dominant {
	case EmojiDespair, EmojiSick:
		severity = 0.8
	case EmojiCrying:
		severity = 0.7
	case EmojiAngry:
		severity = 0.6
	case EmojiAnxious, EmojiFrustrated:
		severity = 0.5
	case EmojiSad, EmojiTired:
		severity = 0.3
	}
	severity = severity * intensity

	return EmojiState{
		DominantEmotion:  dominant,
		DetectedEmojis:   detected,
		IsEmojiOnly:      isEmojiOnly,
		Intensity:        intensity,
		DistressSeverity: severity,
		Confidence:       math.Min(1.0, float64(len(detected))*0.2+intensity*0.6),
		Timestamp:        time.Now(),
	}
}

func (e *EmojiEngine) extractEmojis(text string) []string {
	var detected []string
	for _, r := range text {
		if isEmoji(r) {
			detected = append(detected, string(r))
		}
	}
	return detected
}

func isEmoji(r rune) bool {
	// Simple range check for common emojis
	return (r >= 0x1F300 && r <= 0x1F6FF) || (r >= 0x1F900 && r <= 0x1FAFF) || (r >= 0x2600 && r <= 0x27BF)
}
