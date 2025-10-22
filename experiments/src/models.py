"""
LLM API integration using LiteLLM for unified interface
"""
import os
import time
import asyncio
from typing import Optional, Dict, Any
from litellm import acompletion
import litellm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure LiteLLM
litellm.set_verbose = False

# Model configurations
MODELS = [
    {
        "id": "claude-sonnet-4-5",
        "name": "Claude Sonnet 4.5",
        "provider": "anthropic",
        "api_model": "claude-3-sonnet-20240229"  # Using available model
    },
    {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "provider": "openai",
        "api_model": "gpt-4o"
    },
    {
        "id": "gemini-2-pro",
        "name": "Gemini 2.0 Pro",
        "provider": "google",
        "api_model": "gemini-pro"  # Using available model
    },
    {
        "id": "grok-2",
        "name": "Grok 2",
        "provider": "xai",
        "api_model": "grok-beta"  # Using available model
    },
    {
        "id": "llama-3-2-3b",
        "name": "Llama 3.2 3B",
        "provider": "replicate",
        "api_model": "meta/llama-2-7b-chat"  # Using available model
    },
    {
        "id": "deepseek-v3",
        "name": "DeepSeek V3",
        "provider": "deepseek",
        "api_model": "deepseek-chat"
    }
]


async def get_model_response(
    model_id: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    timeout: int = 60
) -> str:
    """
    Unified interface for calling any LLM via LiteLLM
    
    Args:
        model_id: ID from MODELS list
        prompt: User prompt
        system_prompt: Optional system prompt
        temperature: Response randomness (0.0-1.0)
        max_tokens: Maximum response length
        timeout: Request timeout in seconds
    
    Returns:
        Model response as string
    
    Raises:
        ValueError: If model_id not found
        Exception: If API call fails
    """
    # Find model config
    model_config = None
    for model in MODELS:
        if model["id"] == model_id:
            model_config = model
            break
    
    if not model_config:
        raise ValueError(f"Model ID '{model_id}' not found in MODELS list")
    
    # Build messages
    messages = []
    
    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt
        })
    
    messages.append({
        "role": "user",
        "content": prompt
    })
    
    # Record timing
    start_time = time.time()
    
    try:
        # Make API call
        response = await acompletion(
            model=model_config["api_model"],
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        content = response.choices[0].message.content
        
        print(f"✓ {model_id}: {response_time_ms}ms")
        
        return content
        
    except Exception as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        print(f"✗ {model_id}: {response_time_ms}ms - Error: {str(e)}")
        raise Exception(f"Error calling {model_id}: {str(e)}")


async def test_model_connectivity(model_id: str) -> Dict[str, Any]:
    """
    Test connectivity to a specific model
    
    Args:
        model_id: Model ID to test
        
    Returns:
        Dict with test results
    """
    test_prompt = "Hello! Please respond with 'Connection successful' if you can read this."
    
    try:
        start_time = time.time()
        response = await get_model_response(
            model_id=model_id,
            prompt=test_prompt,
            temperature=0.1,
            max_tokens=50
        )
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "model_id": model_id,
            "status": "success",
            "response": response,
            "response_time_ms": response_time_ms,
            "error": None
        }
        
    except Exception as e:
        return {
            "model_id": model_id,
            "status": "error",
            "response": None,
            "response_time_ms": None,
            "error": str(e)
        }


async def test_all_models() -> List[Dict[str, Any]]:
    """
    Test connectivity to all configured models
    
    Returns:
        List of test results for each model
    """
    print("Testing connectivity to all models...")
    print("=" * 50)
    
    # Test all models concurrently (with some rate limiting)
    results = []
    
    for model in MODELS:
        print(f"Testing {model['name']} ({model['id']})...")
        result = await test_model_connectivity(model['id'])
        results.append(result)
        
        # Small delay to avoid rate limits
        await asyncio.sleep(1)
    
    print("=" * 50)
    
    # Summary
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] == 'error']
    
    print(f"Summary: {len(successful)}/{len(MODELS)} models accessible")
    
    if failed:
        print("\nFailed models:")
        for result in failed:
            print(f"  - {result['model_id']}: {result['error']}")
    
    if successful:
        print("\nSuccessful models:")
        for result in successful:
            print(f"  - {result['model_id']}: {result['response_time_ms']}ms")
    
    return results


if __name__ == "__main__":
    # Run connectivity test
    asyncio.run(test_all_models())