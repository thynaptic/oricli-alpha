#!/bin/bash
MODELS=("qwen2.5-coder:3b" "qwen3:1.7b" "phi3.5:latest" "llama3.2:latest" "gemma3:1b" "qwen2.5:1.5b" "qwen2:1.5b")
SYSTEM="You are ORI — a direct, confident, warm AI. You speak like a knowledgeable friend: no corporate fluff, no excessive disclaimers. Concise but never cold. You're proud of being sovereign and local."
declare -a PROMPTS=("Hey, how are you doing?" "What makes you different from ChatGPT? 2-3 sentences." "I'm stressed about a big project. What do I do?" "Explain neural networks simply.")
declare -a LABELS=("casual" "identity" "emotional" "technical")

echo "===== ORI PROSE BENCHMARK ====="
for model in "${MODELS[@]}"; do
  echo -e "\n\n##### $model #####"
  for i in "${!PROMPTS[@]}"; do
    echo -e "\n[${LABELS[$i]}] ${PROMPTS[$i]}"
    start=$SECONDS
    curl -s --max-time 180 -X POST http://localhost:11434/api/chat \
      -H "Content-Type: application/json" \
      -d "{\"model\":\"$model\",\"stream\":false,\"think\":false,\"messages\":[{\"role\":\"system\",\"content\":$(echo "$SYSTEM" | python3 -c 'import sys,json;print(json.dumps(sys.stdin.read().strip()))')},{\"role\":\"user\",\"content\":$(echo "${PROMPTS[$i]}" | python3 -c 'import sys,json;print(json.dumps(sys.stdin.read().strip()))')}],\"options\":{\"num_predict\":150,\"num_ctx\":1024,\"temperature\":0.7}}" \
      | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['message']['content'])" 2>/dev/null
    echo -e "($(($SECONDS - start))s)"
  done
done
echo -e "\n===== DONE ====="
