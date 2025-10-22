"""
Test script to verify API connectivity for all models
"""
import asyncio
import sys
import os

# Add the experiments/src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'experiments', 'src'))

from models import test_all_models


async def main():
    """Main test function"""
    print("Constitutional Reasoning Engine - API Connectivity Test")
    print("=" * 60)
    
    # Check if .env file exists
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_file):
        print("⚠️  .env file not found!")
        print("Please copy .env.example to .env and add your API keys")
        print()
        return
    
    # Test all models
    results = await test_all_models()
    
    # Exit with error code if any tests failed
    failed_count = len([r for r in results if r['status'] == 'error'])
    if failed_count > 0:
        print(f"\n❌ {failed_count} models failed connectivity test")
        sys.exit(1)
    else:
        print(f"\n✅ All {len(results)} models passed connectivity test")
        print("Ready to run experiments!")


if __name__ == "__main__":
    asyncio.run(main())