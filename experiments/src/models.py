"""
LLM API integration using LiteLLM for unified interface
"""
import os
import time
import asyncio
from typing import Optional, Dict, Any, List
from litellm import acompletion
import litellm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure LiteLLM
litellm.set_verbose = False

# Model configurations (focusing on working models)
MODELS = [
    {
        "id": "claude-sonnet-4-5",
        "name": "Claude Sonnet 4.5",
        "provider": "anthropic",
        "api_model": "claude-sonnet-4-5-20250929"
    },
    {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "provider": "openai",
        "api_model": "gpt-4o"
    },
    {
        "id": "llama-3-8b",
        "name": "Llama 3 8B",
        "provider": "replicate",
        "api_model": "replicate/meta/meta-llama-3-8b-instruct"
    },
    {
        "id": "gemini-2-5-flash",
        "name": "Gemini 2.5 Flash",
        "provider": "google",
        "api_model": "gemini/gemini-2.5-flash"
    },
    {
        "id": "grok-3",
        "name": "Grok 3",
        "provider": "xai",
        "api_model": "xai/grok-3"
    },
    {
        "id": "deepseek-chat",
        "name": "DeepSeek Chat",
        "provider": "deepseek",
        "api_model": "deepseek/deepseek-chat"
    }
]

# Additional models to test when available/stable
ADDITIONAL_MODELS = []


async def get_model_response(
    model_id: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    timeout: int = 60,
    max_retries: int = 3
) -> str:
    """
    Unified interface for calling any LLM via LiteLLM with retry logic

    Args:
        model_id: ID from MODELS list
        prompt: User prompt
        system_prompt: Optional system prompt
        temperature: Response randomness (0.0-1.0)
        max_tokens: Maximum response length
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts for rate limits (default: 3)

    Returns:
        Model response as string

    Raises:
        ValueError: If model_id not found
        Exception: If API call fails after all retries
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

    # Retry loop with exponential backoff
    for attempt in range(max_retries):
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
            error_str = str(e).lower()

            # Check if this is a rate limit error
            is_rate_limit = any(phrase in error_str for phrase in [
                'rate limit', 'too many requests', '429', 'quota',
                'rate_limit_exceeded', 'resource_exhausted'
            ])

            # Check if this is a timeout
            is_timeout = 'timeout' in error_str or 'timed out' in error_str

            if (is_rate_limit or is_timeout) and attempt < max_retries - 1:
                # Exponential backoff: 2s, 4s, 8s
                wait_time = 2 ** (attempt + 1)
                print(f"⚠️  {model_id}: {'Rate limit' if is_rate_limit else 'Timeout'} hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
                continue
            else:
                # Not a rate limit/timeout, or out of retries
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