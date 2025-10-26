"""
LLM API integration using LiteLLM for unified interface
"""
import os
import json
import time
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from litellm import acompletion
import litellm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure LiteLLM
litellm.set_verbose = False
# Enable client-side JSON validation for models without native response_format support
litellm.enable_json_schema_validation = True


def load_models() -> Dict[str, List[Dict[str, Any]]]:
    """
    Load models from JSON file and filter by capability

    Returns:
        Dict with keys:
            'all': All models
            'layer2': Models that can do Layer 2 reasoning
            'layer3': Models that can do Layer 3 evaluation

    Raises:
        FileNotFoundError: If models.json not found
        ValueError: If JSON is malformed
    """
    json_path = Path(__file__).parent.parent / "data" / "models.json"

    with open(json_path, 'r') as f:
        data = json.load(f)

    all_models = data['models']

    # Filter by capability
    layer2_models = [m for m in all_models if m.get('can_layer2', False)]
    layer3_models = [m for m in all_models if m.get('can_layer3', False)]

    return {
        'all': all_models,
        'layer2': layer2_models,
        'layer3': layer3_models
    }


def get_default_layer3_evaluator(models: List[Dict[str, Any]] = None) -> str:
    """
    Get the default Layer 3 evaluator model ID

    Args:
        models: Optional list of models to search. If None, loads from JSON.

    Returns:
        Model ID marked with is_default_layer3=True

    Raises:
        ValueError: If no default is configured
    """
    if models is None:
        models_data = load_models()
        models = models_data['all']

    for model in models:
        if model.get('is_default_layer3', False):
            return model['id']

    raise ValueError("No default Layer 3 evaluator configured in models.json")


async def get_model_response(
    model_id: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    timeout: int = 60,
    max_retries: int = 3,
    use_response_format: bool = False
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
        use_response_format: Enable JSON mode via response_format parameter (default: False)

    Returns:
        Model response as string

    Raises:
        ValueError: If model_id not found
        Exception: If API call fails after all retries
    """
    # Load and find model config
    models_data = load_models()
    all_models = models_data['all']

    model_config = None
    for model in all_models:
        if model["id"] == model_id:
            model_config = model
            break

    if not model_config:
        raise ValueError(f"Model ID '{model_id}' not found in models list")

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
            # Build API call parameters
            api_params = {
                "model": model_config["api_model"],
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timeout": timeout
            }

            # Only add response_format if explicitly requested
            if use_response_format:
                api_params["response_format"] = {"type": "json_object"}

            # Make API call
            response = await acompletion(**api_params)

            response_time_ms = int((time.time() - start_time) * 1000)

            content = response.choices[0].message.content

            # Suppress verbose per-API-call logging (runner shows trial summaries)
            # print(f"✓ {model_id}: {response_time_ms}ms")

            return content

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            error_str = str(e).lower()

            # Check if this is a rate limit error
            is_rate_limit = any(phrase in error_str for phrase in [
                'rate limit', 'too many requests', '429', 'quota',
                'rate_limit_exceeded', 'resource_exhausted', 'overloaded'
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

    # Load models
    models_data = load_models()
    all_models = models_data['all']

    # Test all models concurrently (with some rate limiting)
    results = []

    for model in all_models:
        print(f"Testing {model['name']} ({model['id']})...")
        result = await test_model_connectivity(model['id'])
        results.append(result)

        # Small delay to avoid rate limits
        await asyncio.sleep(1)

    print("=" * 50)

    # Summary
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] == 'error']

    print(f"Summary: {len(successful)}/{len(all_models)} models accessible")
    
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