#!/usr/bin/env python
"""Simple script to validate Anthropic API connectivity."""

import os
import sys

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def validate_anthropic_api() -> bool:
    """Test Anthropic API connectivity with a simple call."""
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found in environment")
        return False

    if api_key == "your-api-key-here":
        print("ERROR: Please replace placeholder with actual API key in .env")
        return False

    print("API key found in environment")

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        # Simple test message
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[{"role": "user", "content": "Reply with just: API OK"}],
        )

        response_text = message.content[0].text  # type: ignore[union-attr]
        print(f"API Response: {response_text}")
        print("SUCCESS: Anthropic API connection validated!")
        return True

    except anthropic.AuthenticationError:
        print("ERROR: Invalid API key")
        return False
    except anthropic.RateLimitError:
        print("ERROR: Rate limited - but API key is valid")
        return True  # Key works, just rate limited
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    success = validate_anthropic_api()
    sys.exit(0 if success else 1)
