package safety

import (
	"regexp"
	"strings"
)

// --- Web & SSI Injection Guard ---
//
// Covers both sides of the inference pipeline:
//
//   Input  side: intercept prompts that attempt to weaponise Oricli as a
//                payload generator or that carry active injection markers.
//
//   Output side: strip or block injection payloads from generated responses
//                OUTSIDE of fenced code blocks (legitimate code examples in
//                ```-blocks are allowed through; they are shown, not executed).
//
// Attack families covered:
//   SSI        — <!--#exec -->, <!--#include -->, <!--#printenv -->
//   XSS        — <script>, javascript:, event handlers (on*=), data URIs
//   HTML       — meta refresh, iframe with srcdoc, object/embed with data
//   SSTI       — Jinja2/Twig {{…}}, Freemarker ${…}, ERB <%=…%>, Thymeleaf
//   SQL/NoSQL  — classic UNION/OR-based SQLi, MongoDB $where/$ne, ...
//   LDAP       — )(uid=*))(|(uid=* patterns
//   XPATH      — ' or 1=1 variants
//   XXE/XML    — <!ENTITY, SYSTEM "file://..."
//   CRLF       — \r\n header injection
//   SSRF       — requests to internal metadata / localhost URLs
//   Path Trav  — ../../ sequences targeting sensitive paths
//   Log Inject — log forgery via \n injection

// InjectionCategory labels a detected vector for logging.
type InjectionCategory string

const (
	CatSSI       InjectionCategory = "ssi"
	CatXSS       InjectionCategory = "xss"
	CatSSTI      InjectionCategory = "ssti"
	CatSQLi      InjectionCategory = "sqli"
	CatNoSQLi    InjectionCategory = "nosqli"
	CatLDAP      InjectionCategory = "ldap_injection"
	CatXPath     InjectionCategory = "xpath_injection"
	CatXXE       InjectionCategory = "xxe"
	CatCRLF      InjectionCategory = "crlf"
	CatSSRF      InjectionCategory = "ssrf"
	CatPathTrav  InjectionCategory = "path_traversal"
	CatLogInject InjectionCategory = "log_injection"
	CatHTMLInj   InjectionCategory = "html_injection"
)

// WebInjectionResult is returned by both input and output scanning.
type WebInjectionResult struct {
	Detected  bool
	Category  InjectionCategory
	Severity  DisclosureSeverity // reuse the tier type from disclosure.go
	Matches   []string
	Sanitized string // cleaned output text (output-side only)
	Refusal   string // human-readable message (input-side only)
}

// WebInjectionGuard is the main engine.
type WebInjectionGuard struct {
	// --- Input-side: prompt patterns that signal weaponisation intent ---
	inputWeaponPatterns []string // "generate an XSS payload that..."
	inputSSRFPatterns   []string // "fetch http://169.254.169.254/..."
	inputSSTIPatterns   []string // {{7*7}} / ${7*7} directly in message

	// --- Compiled output-side regexes ---
	reSSI        *regexp.Regexp
	reXSS        *regexp.Regexp
	reHTMLInj    *regexp.Regexp
	reSSTI       *regexp.Regexp
	reSQLi       *regexp.Regexp
	reNoSQLi     *regexp.Regexp
	reLDAP       *regexp.Regexp
	reXPath      *regexp.Regexp
	reXXE        *regexp.Regexp
	reCRLF       *regexp.Regexp
	reSSRF       *regexp.Regexp
	rePathTrav   *regexp.Regexp
	reLogInject  *regexp.Regexp
}

// NewWebInjectionGuard constructs the guard with all patterns compiled.
func NewWebInjectionGuard() *WebInjectionGuard {
	g := &WebInjectionGuard{}
	g.loadInputPatterns()
	g.compileOutputPatterns()
	return g
}

// ---------------------------------------------------------------------------
// Input-side patterns
// ---------------------------------------------------------------------------

func (g *WebInjectionGuard) loadInputPatterns() {
	// Weaponisation intent — user is asking Oricli to *generate* payloads
	g.inputWeaponPatterns = []string{
		// XSS generation requests
		"generate an xss payload", "create an xss payload", "write an xss attack",
		"give me a cross-site scripting payload", "xss payload for",
		"bypass xss filter", "xss that bypasses", "blind xss",

		// SQL injection generation
		"generate a sql injection", "create a sql injection payload", "write sql injection",
		"sqli payload for", "sql injection that bypasses", "union select attack",
		"give me a sqlmap command", "sqlmap -u",

		// SSTI generation
		"generate a ssti payload", "server side template injection payload",
		"template injection for jinja", "template injection for freemarker",
		"ssti that achieves rce", "{{7*7}} payload",

		// SSI generation
		"generate a ssi injection", "server side include injection",
		"ssi payload to execute", "<!--#exec payload",

		// General web attack generation
		"write a web shell", "generate a webshell", "php web shell",
		"generate a csrf token bypass", "csrf attack payload",
		"generate a path traversal payload", "directory traversal payload",
		"xxe payload to read", "xml external entity payload",
		"ldap injection payload", "nosql injection payload",
		"generate a crlf injection", "http header injection payload",

		// Log injection / forgery
		"inject into logs", "log injection payload", "forge a log entry",
		"newline injection to forge",

		// SSTI exploit generation (not just payload — full attack assist)
		"create a ssti exploit", "write a ssti exploit", "craft a ssti exploit",
		"ssti exploit for", "flask ssti exploit", "jinja2 exploit",
		"generate a server-side template injection exploit",
		"server-side template injection exploit",

		// Stored/reflected XSS assist
		"give me a stored xss payload", "give me a reflected xss payload",
		"stored xss payload", "reflected xss payload",
		"how do i craft a reflected xss", "how to craft a reflected xss",
		"how do i craft an xss attack", "how to craft an xss attack",

		// SSRF payload generation
		"write an ssrf payload", "create an ssrf payload", "craft an ssrf payload",
		"ssrf payload targeting", "ssrf payload for aws", "ssrf payload for gcp",
		"write a ssrf payload", "generate ssrf payload",
	}

	// SSRF — trying to make Oricli fetch internal infrastructure URLs
	g.inputSSRFPatterns = []string{
		"fetch http://169.254.169.254",     // AWS metadata
		"fetch http://metadata.google",     // GCP metadata
		"fetch http://100.100.100.200",     // Alibaba metadata
		"curl http://169.254.169.254",
		"make a request to localhost",
		"make a request to 127.0.0.1",
		"make a request to 192.168.",
		"make a request to 10.",
		"make a request to 172.16.",
		"access internal api at",
		"make a request to the internal",
		"fetch the internal endpoint",
		"access http://localhost",
		"request to http://localhost",

		// Verb-first SSRF patterns
		"access http://169.254.169.254", "access http://metadata.",
		"access http://127.0.0.1", "access http://10.",
		"retrieve http://169.254.169.254", "retrieve http://metadata.",
		"retrieve http://localhost", "retrieve http://127.0.0.1",
		"read from http://127.0.0.1", "read from http://localhost",
		"read from http://169.254.169.254", "read from http://metadata.",
		"get http://169.254.169.254", "get http://metadata.",
		"get http://127.0.0.1", "get http://localhost",
	}

	// Direct SSTI markers IN the prompt itself (not asking to generate, just firing)
	g.inputSSTIPatterns = []string{
		"{{7*7}}", "{{config}}", "{{self.__dict__}}",
		"${7*7}", "${system('", "#{7*7}",
		"<%= 7*7 %>", "<%= system(", "{% debug %}",
		"{{request.application.__globals__",
		"{{''.__class__.__mro__",
	}
}

// ---------------------------------------------------------------------------
// Output-side compiled patterns
// ---------------------------------------------------------------------------

func (g *WebInjectionGuard) compileOutputPatterns() {
	// SSI directives
	g.reSSI = regexp.MustCompile(
		`(?i)<!--#(exec|include|printenv|echo|set|if|elif|else|endif|flastmod|fsize|config)\s`,
	)

	// XSS — active vectors: script tags, javascript: URIs, DOM event handlers, data: URIs with scripts
	g.reXSS = regexp.MustCompile(
		`(?i)(` +
			`<script[\s>]` + // opening script tag
			`|</script>` + // closing script tag
			`|javascript\s*:` + // javascript: URI
			`|vbscript\s*:` + // vbscript: URI
			`|on(load|error|click|mouseover|focus|blur|submit|change|keyup|keydown|keypress|input|drag|drop|paste|copy|cut|scroll|resize|unload|beforeunload|message|storage|hashchange|popstate|animationend|transitionend)\s*=` +
			`|<\s*img[^>]+src\s*=\s*["\']?javascript:` + // img src=javascript:
			`|<\s*iframe[^>]+srcdoc\s*=` + // iframe srcdoc (scriptable)
			`|<\s*object[^>]+data\s*=` + // object data
			`|<\s*embed[^>]+src\s*=` + // embed src
			`|data:text/html` + // data URI HTML
			`|data:application/javascript` + // data URI JS
			`)`,
	)

	// Dangerous HTML injection (meta refresh, form action to external, base href override)
	g.reHTMLInj = regexp.MustCompile(
		`(?i)(` +
			`<meta[^>]+http-equiv\s*=\s*["\']?refresh` + // meta refresh
			`|<base[^>]+href\s*=` + // base href override
			`|<link[^>]+rel\s*=\s*["\']?import` + // HTML imports
			`|<form[^>]+action\s*=\s*["\']?https?://` + // form exfil to external
			`)`,
	)

	// SSTI markers (template engine syntax that should never appear in plain prose)
	g.reSSTI = regexp.MustCompile(
		`(` +
			`\{\{[^}]{0,200}\}\}` + // Jinja2/Twig/Handlebars {{...}}
			`|\$\{[^}]{0,200}\}` + // Freemarker/EL ${...}
			`|#\{[^}]{0,200}\}` + // Ruby ERB #{...}
			`|<%=[^%]{0,200}%>` + // ERB/ASP <%= ... %>
			`|\[%=[^\]]{0,200}%\]` + // some template engines
			`)`,
	)

	// SQL injection signatures in output (model accidentally completing an attack)
	g.reSQLi = regexp.MustCompile(
		`(?i)(` +
			`'\s*OR\s*'?\s*1\s*=\s*1` + // ' OR '1'='1
			`|'\s*OR\s+\d+\s*=\s*\d+` + // ' OR 1=1
			`|UNION\s+(ALL\s+)?SELECT\s+` + // UNION SELECT
			`|INSERT\s+INTO\s+\w+\s*\(` + // INSERT INTO injection
			`|DROP\s+TABLE\s+` + // DROP TABLE
			`|;\s*DROP\s+` + // ; DROP
			`|EXEC\s*\(\s*xp_cmdshell` + // xp_cmdshell
			`|WAITFOR\s+DELAY\s+'` + // time-based blind
			`|BENCHMARK\s*\(\d+,` + // MySQL time-based
			`)`,
	)

	// NoSQL injection markers
	g.reNoSQLi = regexp.MustCompile(
		`(?i)(` +
			`\$where\s*:` + // MongoDB $where operator
			`|\$ne\s*:\s*(null|true|false|0|"")` + // $ne bypass
			`|\$gt\s*:\s*""` + // $gt bypass
			`|\$regex\s*:` + // $regex injection
			`|\$or\s*:\s*\[` + // $or injection
			`|\{\s*"\$` + // generic $operator injection
			`)`,
	)

	// LDAP injection
	g.reLDAP = regexp.MustCompile(
		`(?i)(` +
			`\*\)\s*\(uid=\*\)` + // classic LDAP escape
			`|\)\s*\(\|\s*\(uid=\*` + // OR bypass
			`|\*\)\)\s*%00` + // null byte bypass
			`|cn=\*,dc=` + // wildcard CN
			`)`,
	)

	// XPath injection
	g.reXPath = regexp.MustCompile(
		`(?i)(` +
			`'\s*or\s*'?\s*'?\s*=\s*'` + // ' or ''='
			`|'\s*or\s+1\s*=\s*1` + // ' or 1=1
			`|\bcount\s*\(\s*/\s*\*\s*\)` + // count(/*) XPath
			`)`,
	)

	// XXE / XML injection
	g.reXXE = regexp.MustCompile(
		`(?i)(` +
			`<!ENTITY\s+\w+\s+SYSTEM\s+` + // <!ENTITY x SYSTEM "...">
			`|<!DOCTYPE[^>]+SYSTEM\s+["']` + // DOCTYPE SYSTEM
			`|<!DOCTYPE[^>]+\[` + // DOCTYPE with internal subset
			`|SYSTEM\s+["']file://` + // SYSTEM file:// URI
			`|SYSTEM\s+["']http://` + // SYSTEM http:// (blind XXE)
			`)`,
	)

	// CRLF injection — URL-encoded \r\n sequences that could split HTTP headers.
	// We only flag URL-encoded variants (%0d%0a) because plain \r\n in model output
	// is legitimately used in formatted prose and is safely escaped by JSON transport.
	// Matching plain "\nWord: " patterns causes false positives on formatted responses.
	g.reCRLF = regexp.MustCompile(`(%0[dD]%0[aA]|%0[aA]%0[dD])`)

	// SSRF — internal metadata and loopback URLs appearing in generated output
	g.reSSRF = regexp.MustCompile(
		`(?i)(` +
			`http://169\.254\.169\.254` + // AWS/GCP/Azure IMDS
			`|http://metadata\.google\.internal` +
			`|http://100\.100\.100\.200` + // Alibaba IMDS
			`|http://localhost` + // generic localhost
			`|http://127\.\d+\.\d+\.\d+` + // loopback
			`|http://0\.0\.0\.0` +
			`|http://\[::1\]` + // IPv6 loopback
			`)`,
	)

	// Path traversal sequences
	g.rePathTrav = regexp.MustCompile(
		`(\.\.[\\/]){2,}` + // ../../ or ..\ sequences (2+ hops)
		`|(%2[eE]%2[eE][\\/]){2,}` + // URL-encoded ../
		`|(%2[eE]%2[eE]%2[fF]){2,}`, // double-URL-encoded
	)

	// Log injection — newline followed by log-like prefixes
	g.reLogInject = regexp.MustCompile(
		`(?m)(\r?\n|\r)(` +
			`\[?(INFO|WARN|ERROR|DEBUG|CRITICAL|FATAL)\]?` +
			`|\d{4}[-/]\d{2}[-/]\d{2}` + // ISO date
			`|\w+\s+\w+\s+\d+\s+\d+:\d+:\d+` + // syslog date
			`)\s+`, // followed by space (looks like a forged log line)
	)
}

// ---------------------------------------------------------------------------
// ScanInput: check user message for injection weaponisation intent / direct payloads
// ---------------------------------------------------------------------------

// ScanInput checks the user message for web/SSI injection attack patterns.
// Returns a WebInjectionResult. Call alongside CheckInputSafety.
func (g *WebInjectionGuard) ScanInput(input string) WebInjectionResult {
	lower := strings.ToLower(input)

	// 1. Weaponisation intent (asking Oricli to generate attack payloads)
	for _, p := range g.inputWeaponPatterns {
		if strings.Contains(lower, p) {
			return WebInjectionResult{
				Detected: true,
				Category: CatXSS, // generic — actual category varies but XSS is most common
				Severity: DisclosureCritical,
				Matches:  []string{p},
				Refusal:  "Generating attack payloads — XSS, SQLi, SSTI, or otherwise — isn't something I'll do. I'm not your red-team toolkit. If you have a legitimate security question, ask it straight.",
			}
		}
	}

	// 2. SSRF — trying to make Oricli fetch internal infrastructure
	for _, p := range g.inputSSRFPatterns {
		if strings.Contains(lower, p) {
			return WebInjectionResult{
				Detected: true,
				Category: CatSSRF,
				Severity: DisclosureCritical,
				Matches:  []string{p},
				Refusal:  "I won't make requests to internal infrastructure or metadata endpoints. That's a hard boundary.",
			}
		}
	}

	// 3. Direct SSTI markers injected into the prompt
	for _, p := range g.inputSSTIPatterns {
		if strings.Contains(input, p) { // case-sensitive for SSTI
			return WebInjectionResult{
				Detected: true,
				Category: CatSSTI,
				Severity: DisclosureCritical,
				Matches:  []string{p},
				Refusal:  "Template injection syntax detected in your message. If you have a legitimate question about template engines, ask without the live payload.",
			}
		}
	}

	// 4. Direct SSI directives in the prompt
	if g.reSSI.MatchString(input) {
		return WebInjectionResult{
			Detected: true,
			Category: CatSSI,
			Severity: DisclosureCritical,
			Matches:  []string{"ssi_directive"},
			Refusal:  "SSI directives in your message aren't going to execute here. What's the actual question?",
		}
	}

	// 5. XSS payloads directly in the prompt (not asking to generate — embedding them)
	if g.reXSS.MatchString(input) {
		return WebInjectionResult{
			Detected: true,
			Category: CatXSS,
			Severity: DisclosureHigh,
			Matches:  []string{"xss_payload"},
			Refusal:  "Active script injection markers detected in your message. Those don't execute here. What's the real question?",
		}
	}

	// 6. XXE / XML injection in prompt
	if g.reXXE.MatchString(input) {
		return WebInjectionResult{
			Detected: true,
			Category: CatXXE,
			Severity: DisclosureCritical,
			Matches:  []string{"xxe_entity"},
			Refusal:  "XML external entity injection detected. Internal file access via XXE isn't going to work here.",
		}
	}

	return WebInjectionResult{Detected: false}
}

// ---------------------------------------------------------------------------
// ScanOutput: strip active injection payloads from generated responses.
// Skips content inside fenced code blocks (```...```) — those are shown,
// not rendered or executed.
// ---------------------------------------------------------------------------

// ScanOutput scans a generated response for active injection payloads.
// Content inside ``` fenced code blocks is intentionally left untouched.
func (g *WebInjectionGuard) ScanOutput(output string) WebInjectionResult {
	// Split output into prose and code-block segments.
	// We only sanitise prose; code blocks are educational content.
	prose, codeBlocks := splitProseAndCode(output)

	// Build a working copy of the prose to sanitise
	sanitizedProse := prose
	var matches []string
	anyDetected := false
	highestSeverity := DisclosureModerate

	type check struct {
		re       *regexp.Regexp
		cat      InjectionCategory
		severity DisclosureSeverity
		tag      string
	}

	checks := []check{
		{g.reSSI, CatSSI, DisclosureCritical, "SSI_DIRECTIVE"},
		{g.reXSS, CatXSS, DisclosureCritical, "XSS_PAYLOAD"},
		{g.reHTMLInj, CatHTMLInj, DisclosureHigh, "HTML_INJECTION"},
		{g.reSSTI, CatSSTI, DisclosureCritical, "SSTI_PAYLOAD"},
		{g.reSQLi, CatSQLi, DisclosureHigh, "SQLI_PAYLOAD"},
		{g.reNoSQLi, CatNoSQLi, DisclosureHigh, "NOSQLI_PAYLOAD"},
		{g.reLDAP, CatLDAP, DisclosureHigh, "LDAP_INJECTION"},
		{g.reXPath, CatXPath, DisclosureHigh, "XPATH_INJECTION"},
		{g.reXXE, CatXXE, DisclosureCritical, "XXE_ENTITY"},
		{g.reCRLF, CatCRLF, DisclosureHigh, "CRLF_INJECTION"},
		{g.reSSRF, CatSSRF, DisclosureCritical, "SSRF_URL"},
		{g.rePathTrav, CatPathTrav, DisclosureHigh, "PATH_TRAVERSAL"},
		{g.reLogInject, CatLogInject, DisclosureModerate, "LOG_INJECTION"},
	}

	for _, c := range checks {
		found := c.re.FindAllString(sanitizedProse, -1)
		if len(found) > 0 {
			anyDetected = true
			matches = append(matches, found...)
			sanitizedProse = c.re.ReplaceAllString(sanitizedProse, "[SANITIZED:"+c.tag+"]")
			if c.severity == DisclosureCritical {
				highestSeverity = DisclosureCritical
			} else if c.severity == DisclosureHigh && highestSeverity != DisclosureCritical {
				highestSeverity = DisclosureHigh
			}
		}
	}

	if !anyDetected {
		return WebInjectionResult{Detected: false, Sanitized: output}
	}

	// Reassemble prose + code blocks
	reassembled := reassembleOutput(sanitizedProse, codeBlocks)

	return WebInjectionResult{
		Detected:  true,
		Category:  CatXSS, // dominant category (logging only)
		Severity:  highestSeverity,
		Matches:   matches,
		Sanitized: reassembled,
	}
}

// ---------------------------------------------------------------------------
// Helpers: split output into prose vs fenced code blocks
// ---------------------------------------------------------------------------

// splitProseAndCode separates plain prose from fenced code blocks.
// Returns (prose with <<<CODEBLOCK_N>>> placeholders, slice of original blocks).
func splitProseAndCode(text string) (string, []string) {
	var blocks []string
	result := strings.Builder{}
	lines := strings.Split(text, "\n")
	inBlock := false
	blockBuf := strings.Builder{}
	blockIdx := 0

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if !inBlock && strings.HasPrefix(trimmed, "```") {
			inBlock = true
			blockBuf.WriteString(line + "\n")
			continue
		}
		if inBlock {
			blockBuf.WriteString(line + "\n")
			if trimmed == "```" {
				inBlock = false
				blocks = append(blocks, blockBuf.String())
				blockBuf.Reset()
				result.WriteString("<<<CODEBLOCK_" + itoa(blockIdx) + ">>>\n")
				blockIdx++
			}
			continue
		}
		result.WriteString(line + "\n")
	}
	// Unclosed block — treat as code too
	if blockBuf.Len() > 0 {
		blocks = append(blocks, blockBuf.String())
		result.WriteString("<<<CODEBLOCK_" + itoa(blockIdx) + ">>>\n")
	}

	return result.String(), blocks
}

// reassembleOutput restores code block placeholders.
func reassembleOutput(prose string, blocks []string) string {
	for i, block := range blocks {
		prose = strings.ReplaceAll(prose, "<<<CODEBLOCK_"+itoa(i)+">>>", strings.TrimRight(block, "\n"))
	}
	return strings.TrimRight(prose, "\n")
}

// itoa is a minimal int-to-string helper to avoid importing strconv.
func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	digits := ""
	for n > 0 {
		digits = string(rune('0'+n%10)) + digits
		n /= 10
	}
	return digits
}
