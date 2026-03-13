# RFAL (Conversational Reinforced Award Learning)

RFAL is Oricli-Alpha's **autonomous alignment engine**. It allows the system to learn from user interactions in real-time by detecting conflicts, calculating multi-factor rewards, and generating Direct Preference Optimization (DPO) pairs for future fine-tuning.

## Core Concept

Instead of relying solely on static datasets, RFAL treats every user interaction as a potential training signal. If the user corrects the model, rejects an answer, or shows frustration, RFAL captures that negative signal and converts it into a "lesson" (a structured DPO pair).

## The RFAL Loop

1.  **Conflict Detection**: Analyzes user input for signs of rejection or dissatisfaction.
2.  **Reward Calculation**: Computes a scalar reward score based on multiple factors.
3.  **DPO Pair Generation**: If the reward is negative, creates a `(prompt, rejected, chosen)` triplet.
4.  **Persistence**: Saves lessons to a local buffer for later batch training (JIT LoRA).

## Conflict Detection Signals

RFAL monitors three primary signals to detect "bad" responses:

1.  **Keyword Rejection**: Matches user input against a list of explicit rejection terms (e.g., "no", "wrong", "hallucination", "stop", "fix").
2.  **Negative Sentiment**: Uses the `emotional_inference` brain module to detect high-confidence negative emotions (anger, frustration, disappointment).
3.  **Task Repetition**: Detects if the user re-prompts with high similarity to the previous turn, implying the first response was ignored or incorrect.

## Multi-Factor Reward Function

The final reward score is a weighted sum of three components:

$$ \text{Reward} = (S_{\text{HITL}} \times 0.6) + (S_{\text{Fact}} \times 0.3) + (S_{\text{Tone}} \times 0.1) $$

| Component | Weight | Description |
| :--- | :--- | :--- |
| **HITL (Human-in-the-Loop)** | **0.6** | **-1.0** if any conflict signal is detected, **+1.0** otherwise. This is the strongest signal. |
| **Factual Accuracy** | **0.3** | Queries the `world_knowledge` module to validate specific claims. **-1.0** if invalid, **+1.0** if valid. |
| **Tone Alignment** | **0.1** | Queries the `adapter_router` module to see if the response style matched the intended persona/intent. |

## Data Artifacts

RFAL persists its findings to a JSONL file, typically located at:

```
oricli_core/data/rfal_lessons.jsonl
```

### Lesson Structure
Each entry contains:
- `prompt`: The original context/question.
- `rejected`: The model's response that caused the conflict.
- `chosen`: The user's follow-up (correction) or an improved version.
- `reward`: The calculated negative reward score.
- `signals`: List of detected conflict types (e.g., `["keyword_rejection", "negative_sentiment"]`).
- `timestamp`: Unix epoch time.

## Integration

RFAL is implemented as a **Brain Module** (`rfal_engine`). It operates asynchronously to avoid blocking the main chat loop.

- **Module Name**: `rfal_engine`
- **Primary Operation**: `process_feedback`
- **Dependencies**: `emotional_inference`, `world_knowledge`, `adapter_router` (optional but recommended for full scoring).
