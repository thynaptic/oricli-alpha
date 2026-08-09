package safety

import (
	"encoding/base64"
	"html"
	"regexp"
	"strings"
	"unicode"
)

// NormalizeInput pre-processes raw input before any safety gate.
// It strips/decodes obfuscation techniques (unicode confusables, zero-width chars,
// HTML entities, base64, ROT13, leetspeak) so downstream pattern matchers work correctly.
func NormalizeInput(raw string) string {
	s := raw

	// 1. Strip zero-width and invisible Unicode characters
	s = stripInvisibleChars(s)

	// 2. Decode HTML entities (&amp; &#105; etc.)
	s = html.UnescapeString(s)

	// 3. Replace Unicode confusables (Cyrillic/Greek lookalikes → ASCII)
	s = applyConfusables(s)

	// 4. Normalize leetspeak
	s = normalizeLeet(s)

	// 5. Base64 detection — decode any segments that look like base64 and
	//    substitute the decoded text so pattern matchers see the real content.
	s = expandBase64Segments(s)

	// 6. ROT13 heuristic — if the ROT13 form has higher threat density, use it.
	s = maybeROT13(s)

	return s
}

// stripInvisibleChars removes zero-width and soft-hyphen Unicode code points.
func stripInvisibleChars(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		switch r {
		case '\u200B', // zero width space
			'\u200C', // zero width non-joiner
			'\u200D', // zero width joiner
			'\u200E', // left-to-right mark
			'\u200F', // right-to-left mark
			'\uFEFF', // byte order mark / zero width no-break space
			'\u00AD', // soft hyphen
			'\u2060', // word joiner
			'\u2061', // function application
			'\u2062', // invisible times
			'\u2063', // invisible separator
			'\u2064': // invisible plus
			// skip
		default:
			b.WriteRune(r)
		}
	}
	return b.String()
}

// confusableMap maps commonly abused Unicode lookalikes to their ASCII equivalents.
// Covers the most exploited Cyrillic, Greek, and fullwidth code points.
var confusableMap = map[rune]rune{
	// Cyrillic → Latin
	'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x',
	'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O',
	'Р': 'P', 'С': 'C', 'Т': 'T', 'Х': 'X', 'і': 'i', 'І': 'I',
	// Greek → Latin
	'ο': 'o', 'Ο': 'O', 'ρ': 'p', 'Α': 'A', 'Β': 'B', 'Ε': 'E', 'Ζ': 'Z',
	'Η': 'H', 'Ι': 'I', 'Κ': 'K', 'Μ': 'M', 'Ν': 'N', 'Τ': 'T', 'Υ': 'Y',
	'Χ': 'X', 'ν': 'v', 'χ': 'x',
	// Fullwidth ASCII → standard ASCII
	'ａ': 'a', 'ｂ': 'b', 'ｃ': 'c', 'ｄ': 'd', 'ｅ': 'e', 'ｆ': 'f',
	'ｇ': 'g', 'ｈ': 'h', 'ｉ': 'i', 'ｊ': 'j', 'ｋ': 'k', 'ｌ': 'l',
	'ｍ': 'm', 'ｎ': 'n', 'ｏ': 'o', 'ｐ': 'p', 'ｑ': 'q', 'ｒ': 'r',
	'ｓ': 's', 'ｔ': 't', 'ｕ': 'u', 'ｖ': 'v', 'ｗ': 'w', 'ｘ': 'x',
	'ｙ': 'y', 'ｚ': 'z',
	'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'Ｅ': 'E', 'Ｆ': 'F',
	'Ｇ': 'G', 'Ｈ': 'H', 'Ｉ': 'I', 'Ｊ': 'J', 'Ｋ': 'K', 'Ｌ': 'L',
	'Ｍ': 'M', 'Ｎ': 'N', 'Ｏ': 'O', 'Ｐ': 'P', 'Ｑ': 'Q', 'Ｒ': 'R',
	'Ｓ': 'S', 'Ｔ': 'T', 'Ｕ': 'U', 'Ｖ': 'V', 'Ｗ': 'W', 'Ｘ': 'X',
	'Ｙ': 'Y', 'Ｚ': 'Z',
}

func applyConfusables(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		if mapped, ok := confusableMap[r]; ok {
			b.WriteRune(mapped)
		} else {
			b.WriteRune(r)
		}
	}
	return b.String()
}

// leetMap replaces common leet-speak substitutions with their ASCII equivalents.
var leetMap = map[rune]rune{
	'0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '6': 'g',
	'7': 't', '8': 'b', '9': 'g', '@': 'a', '$': 's', '!': 'i', '+': 't',
}

func normalizeLeet(s string) string {
	// Only apply leet normalization to runs that look like leet (mix of digits/symbols
	// embedded within word characters) — prevents mangling real numbers.
	leetWordRe := regexp.MustCompile(`\b[a-zA-Z0-9@$!+]{3,}\b`)
	return leetWordRe.ReplaceAllStringFunc(s, func(word string) string {
		digitCount := 0
		letterCount := 0
		for _, r := range word {
			if unicode.IsLetter(r) {
				letterCount++
			} else if _, ok := leetMap[r]; ok {
				digitCount++
			}
		}
		// Only normalize if at least 30% leet substitutions among word chars
		total := letterCount + digitCount
		if total == 0 || float64(digitCount)/float64(total) < 0.3 {
			return word
		}
		var b strings.Builder
		for _, r := range word {
			if mapped, ok := leetMap[r]; ok {
				b.WriteRune(mapped)
			} else {
				b.WriteRune(r)
			}
		}
		return b.String()
	})
}

// base64TokenRe matches plausible base64 segments (min 20 chars, proper alphabet).
var base64TokenRe = regexp.MustCompile(`[A-Za-z0-9+/]{20,}={0,2}`)

// expandBase64Segments finds base64-looking substrings, decodes them, and appends
// the decoded text so downstream scanners see both forms.
func expandBase64Segments(s string) string {
	expanded := base64TokenRe.ReplaceAllStringFunc(s, func(token string) string {
		decoded, err := base64.StdEncoding.DecodeString(token)
		if err != nil {
			// Try URL-safe variant
			decoded, err = base64.URLEncoding.DecodeString(token)
			if err != nil {
				return token
			}
		}
		// Only substitute if decoded text is printable ASCII
		if !isPrintableASCII(decoded) {
			return token
		}
		return token + " " + string(decoded)
	})
	return expanded
}

func isPrintableASCII(b []byte) bool {
	for _, c := range b {
		if c < 0x20 || c > 0x7E {
			return false
		}
	}
	return true
}

// rot13 applies ROT13 transformation.
func rot13(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		switch {
		case r >= 'a' && r <= 'z':
			b.WriteRune('a' + (r-'a'+13)%26)
		case r >= 'A' && r <= 'Z':
			b.WriteRune('A' + (r-'A'+13)%26)
		default:
			b.WriteRune(r)
		}
	}
	return b.String()
}

// injectionKeywords is a lightweight threat-density set used only for ROT13 heuristic.
var injectionKeywords = []string{
	"ignore", "instructions", "system", "prompt", "override", "jailbreak",
	"bypass", "dan", "unrestricted", "no restrictions", "forget",
}

func threatDensity(s string) int {
	lower := strings.ToLower(s)
	score := 0
	for _, kw := range injectionKeywords {
		if strings.Contains(lower, kw) {
			score++
		}
	}
	return score
}

// maybeROT13 applies ROT13 if the rotated form has a higher threat score.
// Catches "vtagber cerihbhf vafgehpgvbaf" style attacks.
func maybeROT13(s string) string {
	rotated := rot13(s)
	if threatDensity(rotated) > threatDensity(s) {
		return rotated
	}
	return s
}
