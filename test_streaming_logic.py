import json
import asyncio
from typing import Any, Dict
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.api.openai_compatible import OpenAICompatibleAPI
from mavaia_core.types.models import ChatCompletionRequest, ChatMessage

async def test_streaming_logic():
    # 1. Initialize Registry
    print("Discovering modules...")
    ModuleRegistry.discover_modules()
    
    # 2. Get API instance
    api = OpenAICompatibleAPI()
    
    # 3. Create a mock request
    request = ChatCompletionRequest(
        model="mavaia-cognitive",
        messages=[ChatMessage(role="user", content="Test complex reasoning")],
        stream=True
    )
    
    print("\nStarting stream...")
    # 4. Call _stream_chat_completion
    response = await api._stream_chat_completion(request)
    
    thought_count = 0
    content_received = False
    
    # 5. Consume the generator
    async for chunk in response.body_iterator:
        if isinstance(chunk, bytes):
            chunk = chunk.decode('utf-8')
            
        for line in chunk.split('\n'):
            line = line.strip()
            if line.startswith("data: "):
                data_str = line[6:].strip()
                if not data_str or data_str == "[DONE]":
                    if data_str == "[DONE]":
                        print("\n[DONE]")
                    continue
                
                try:
                    data = json.loads(data_str)
                    if "choices" in data:
                        delta = data["choices"][0]["delta"]
                        if "thought" in delta:
                            thought_count += 1
                            print(f"Thought: {delta['thought']}")
                        if "content" in delta:
                            content_received = True
                            print(delta["content"], end="", flush=True)
                    elif "error" in data:
                        print(f"\nError in stream: {data['error']}")
                except Exception as e:
                    print(f"\nError parsing JSON: {e} from line: {line}")

    print("\n\nLogic Test Summary:")
    print(f"Thoughts received: {thought_count}")
    print(f"Content received: {content_received}")
    
    return thought_count > 0 and content_received

if __name__ == "__main__":
    success = asyncio.run(test_streaming_logic())
    if not success:
        sys.exit(1)
