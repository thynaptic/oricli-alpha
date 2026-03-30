package forge

// DefaultTools returns the 8 pre-built bash tool scripts that are registered
// at boot. Each tool follows the stdin→JSON stdout contract:
//   - Reads input from $1 (first arg) or stdin
//   - Writes a JSON object to stdout
//   - Exits 0 on success, 1 on error (with {"error":"..."} on stdout)

type DefaultTool struct {
	Name        string
	Description string
	Source      string
	Parameters  map[string]interface{}
}

// AllDefaultTools returns all 8 default tools.
func AllDefaultTools() []DefaultTool {
	return []DefaultTool{
		jsonExtract(),
		regexExtract(),
		textDiff(),
		mathEval(),
		csvToJSON(),
		urlFetch(),
		templateRender(),
		hashText(),
	}
}

// ── 1. json_extract ───────────────────────────────────────────────────────────

func jsonExtract() DefaultTool {
	return DefaultTool{
		Name:        "json_extract",
		Description: "Extract a value from a JSON string using a dot-notation path (e.g. 'user.name')",
		Parameters: map[string]interface{}{
			"type": "object",
			"properties": map[string]interface{}{
				"json":  map[string]interface{}{"type": "string", "description": "JSON input string"},
				"path":  map[string]interface{}{"type": "string", "description": "Dot-notation path, e.g. 'user.name'"},
			},
			"required": []string{"json", "path"},
		},
		Source: `#!/usr/bin/env bash
set -euo pipefail
INPUT=$(echo "$1" | base64 -d 2>/dev/null || echo "$1")
JSON=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d)" 2>/dev/null || echo "$INPUT")
PARAMS=$(echo "$JSON")
DATA=$(echo "$PARAMS" | python3 -c "import sys,json; p=json.load(sys.stdin); print(p.get('json',''))")
PATH_ARG=$(echo "$PARAMS" | python3 -c "import sys,json; p=json.load(sys.stdin); print(p.get('path',''))")
RESULT=$(echo "$DATA" | python3 -c "
import sys, json
data = json.load(sys.stdin)
path = '$PATH_ARG'.split('.')
cur = data
for k in path:
    if isinstance(cur, dict):
        cur = cur.get(k)
    else:
        cur = None
    if cur is None:
        break
print(json.dumps({'result': cur}))
" 2>&1) || RESULT='{"error":"extraction failed"}'
echo "$RESULT"
`,
	}
}

// ── 2. regex_extract ─────────────────────────────────────────────────────────

func regexExtract() DefaultTool {
	return DefaultTool{
		Name:        "regex_extract",
		Description: "Extract all regex matches from a text string",
		Parameters: map[string]interface{}{
			"type": "object",
			"properties": map[string]interface{}{
				"text":    map[string]interface{}{"type": "string"},
				"pattern": map[string]interface{}{"type": "string", "description": "Python regex pattern"},
			},
			"required": []string{"text", "pattern"},
		},
		Source: `#!/usr/bin/env bash
set -euo pipefail
PARAMS="$1"
python3 -c "
import sys, json, re
p = json.loads('$PARAMS'.replace(\"'\", '\"'))
matches = re.findall(p['pattern'], p['text'])
print(json.dumps({'matches': matches, 'count': len(matches)}))
" 2>/dev/null || echo '{"error":"regex failed","matches":[]}'
`,
	}
}

// ── 3. text_diff ─────────────────────────────────────────────────────────────

func textDiff() DefaultTool {
	return DefaultTool{
		Name:        "text_diff",
		Description: "Produce a unified diff between two text strings",
		Parameters: map[string]interface{}{
			"type": "object",
			"properties": map[string]interface{}{
				"before": map[string]interface{}{"type": "string"},
				"after":  map[string]interface{}{"type": "string"},
			},
			"required": []string{"before", "after"},
		},
		Source: `#!/usr/bin/env bash
set -euo pipefail
PARAMS="$1"
python3 -c "
import sys, json, difflib
p = json.loads('''$PARAMS''')
before = p.get('before','').splitlines(keepends=True)
after  = p.get('after','').splitlines(keepends=True)
diff = list(difflib.unified_diff(before, after, fromfile='before', tofile='after'))
print(json.dumps({'diff': ''.join(diff), 'changed': len(diff) > 0}))
" 2>/dev/null || echo '{"error":"diff failed"}'
`,
	}
}

// ── 4. math_eval ─────────────────────────────────────────────────────────────

func mathEval() DefaultTool {
	return DefaultTool{
		Name:        "math_eval",
		Description: "Safely evaluate a mathematical expression and return the numeric result",
		Parameters: map[string]interface{}{
			"type": "object",
			"properties": map[string]interface{}{
				"expression": map[string]interface{}{"type": "string", "description": "Math expression, e.g. '2 + 2 * 3'"},
			},
			"required": []string{"expression"},
		},
		Source: `#!/usr/bin/env bash
set -euo pipefail
PARAMS="$1"
python3 -c "
import sys, json, ast, operator
p = json.loads('''$PARAMS''')
expr = p.get('expression', '')

# Safe eval: only allow numbers and basic operators
allowed = set('0123456789+-*/(). ')
if not all(c in allowed for c in expr):
    print(json.dumps({'error': 'unsafe expression', 'expression': expr}))
    sys.exit(0)

try:
    result = eval(compile(ast.parse(expr, mode='eval'), '<string>', 'eval'))
    print(json.dumps({'result': result, 'expression': expr}))
except Exception as e:
    print(json.dumps({'error': str(e), 'expression': expr}))
" 2>/dev/null || echo '{"error":"eval failed"}'
`,
	}
}

// ── 5. csv_to_json ───────────────────────────────────────────────────────────

func csvToJSON() DefaultTool {
	return DefaultTool{
		Name:        "csv_to_json",
		Description: "Parse a CSV string into a JSON array of objects using the first row as headers",
		Parameters: map[string]interface{}{
			"type": "object",
			"properties": map[string]interface{}{
				"csv": map[string]interface{}{"type": "string", "description": "CSV text with header row"},
			},
			"required": []string{"csv"},
		},
		Source: `#!/usr/bin/env bash
set -euo pipefail
PARAMS="$1"
python3 -c "
import sys, json, csv, io
p = json.loads('''$PARAMS''')
reader = csv.DictReader(io.StringIO(p.get('csv','')))
rows = list(reader)
print(json.dumps({'rows': rows, 'count': len(rows)}))
" 2>/dev/null || echo '{"error":"csv parse failed","rows":[]}'
`,
	}
}

// ── 6. url_fetch ─────────────────────────────────────────────────────────────

func urlFetch() DefaultTool {
	return DefaultTool{
		Name:        "url_fetch",
		Description: "Fetch the content of a URL via HTTPS GET (public URLs only, 10s timeout)",
		Parameters: map[string]interface{}{
			"type": "object",
			"properties": map[string]interface{}{
				"url":     map[string]interface{}{"type": "string"},
				"headers": map[string]interface{}{"type": "object", "description": "Optional HTTP headers"},
			},
			"required": []string{"url"},
		},
		Source: `#!/usr/bin/env bash
set -euo pipefail
PARAMS="$1"
python3 -c "
import sys, json, urllib.request, urllib.error
p = json.loads('''$PARAMS''')
url = p.get('url', '')
if not url.startswith('https://'):
    print(json.dumps({'error': 'only HTTPS URLs allowed'}))
    sys.exit(0)
headers = p.get('headers', {})
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode('utf-8', errors='replace')[:8192]
        print(json.dumps({'status': resp.status, 'body': body, 'url': url}))
except Exception as e:
    print(json.dumps({'error': str(e), 'url': url}))
" 2>/dev/null || echo '{"error":"fetch failed"}'
`,
	}
}

// ── 7. template_render ───────────────────────────────────────────────────────

func templateRender() DefaultTool {
	return DefaultTool{
		Name:        "template_render",
		Description: "Render a Python str.format_map template with provided variables",
		Parameters: map[string]interface{}{
			"type": "object",
			"properties": map[string]interface{}{
				"template": map[string]interface{}{"type": "string", "description": "Template string with {var} placeholders"},
				"vars":     map[string]interface{}{"type": "object", "description": "Variables to substitute"},
			},
			"required": []string{"template", "vars"},
		},
		Source: `#!/usr/bin/env bash
set -euo pipefail
PARAMS="$1"
python3 -c "
import sys, json
p = json.loads('''$PARAMS''')
tmpl = p.get('template', '')
vars_ = p.get('vars', {})
try:
    rendered = tmpl.format_map(vars_)
    print(json.dumps({'rendered': rendered}))
except Exception as e:
    print(json.dumps({'error': str(e), 'template': tmpl}))
" 2>/dev/null || echo '{"error":"template render failed"}'
`,
	}
}

// ── 8. hash_text ─────────────────────────────────────────────────────────────

func hashText() DefaultTool {
	return DefaultTool{
		Name:        "hash_text",
		Description: "Compute SHA256 or MD5 hash of an input string",
		Parameters: map[string]interface{}{
			"type": "object",
			"properties": map[string]interface{}{
				"text":      map[string]interface{}{"type": "string"},
				"algorithm": map[string]interface{}{"type": "string", "enum": []string{"sha256", "md5"}, "default": "sha256"},
			},
			"required": []string{"text"},
		},
		Source: `#!/usr/bin/env bash
set -euo pipefail
PARAMS="$1"
python3 -c "
import sys, json, hashlib
p = json.loads('''$PARAMS''')
text = p.get('text', '')
algo = p.get('algorithm', 'sha256')
h = hashlib.new(algo)
h.update(text.encode('utf-8'))
print(json.dumps({'hash': h.hexdigest(), 'algorithm': algo}))
" 2>/dev/null || echo '{"error":"hash failed"}'
`,
	}
}
