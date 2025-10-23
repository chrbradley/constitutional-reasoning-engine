"""
Truncation detection and automatic retry logic
"""
import json
import re
from typing import Dict, Any, Tuple


class TruncationDetector:
    """
    Detect if a model response was truncated and needs retry with higher max_tokens
    """

    def __init__(self):
        self.max_token_ladder = [8000, 12000, 16000, 20000]

    def is_truncated(self, response: str, parse_success: bool) -> Tuple[bool, str]:
        """
        Detect if response was likely truncated

        Args:
            response: Raw model response
            parse_success: Whether JSON parsing succeeded

        Returns:
            Tuple of (is_truncated, reason)
        """
        if not response:
            return False, "empty_response"

        # Check 1: JSON parsing failed
        if not parse_success:
            # Try to determine if it's truncation vs other parsing issues
            if self._looks_like_truncated_json(response):
                return True, "incomplete_json"

        # Check 2: String ends abruptly (no proper ending punctuation)
        if self._ends_abruptly(response):
            return True, "abrupt_ending"

        # Check 3: Missing closing braces
        if self._missing_closing_braces(response):
            return True, "missing_closing_braces"

        return False, "not_truncated"

    def _looks_like_truncated_json(self, response: str) -> bool:
        """Check if JSON structure looks incomplete"""
        # Remove markdown code blocks
        clean = response.strip()
        if clean.startswith('```json'):
            clean = clean[7:]
        if clean.startswith('```'):
            clean = clean[3:]
        if clean.endswith('```'):
            clean = clean[:-3]
        clean = clean.strip()

        # Count braces
        open_braces = clean.count('{')
        close_braces = clean.count('}')

        # If we have opening braces but fewer closing braces, likely truncated
        if open_braces > close_braces:
            return True

        # Check if ends with incomplete string (quote without closing)
        if clean.endswith('"') and not clean.endswith('"}'):
            # Count quotes to see if we have unmatched quotes
            quotes = clean.count('"')
            if quotes % 2 != 0:
                return True

        return False

    def _ends_abruptly(self, response: str) -> bool:
        """Check if response ends mid-sentence without proper punctuation"""
        clean = response.strip()

        # Remove markdown code blocks for checking
        if clean.endswith('```'):
            clean = clean[:-3].strip()

        # If it doesn't end with proper punctuation or closing brace, might be truncated
        proper_endings = ['.', '!', '?', '}', ']', '"']

        if not any(clean.endswith(end) for end in proper_endings):
            return True

        # Check if last field value seems incomplete (ends with lowercase letter or comma)
        if re.search(r'[a-z,]$', clean):
            return True

        return False

    def _missing_closing_braces(self, response: str) -> bool:
        """Check if JSON has unmatched opening braces"""
        # Remove markdown
        clean = response.strip()
        for marker in ['```json', '```']:
            clean = clean.replace(marker, '')
        clean = clean.strip()

        # Count all types of brackets
        open_curly = clean.count('{')
        close_curly = clean.count('}')
        open_square = clean.count('[')
        close_square = clean.count(']')

        return (open_curly > close_curly) or (open_square > close_square)

    def get_next_token_limit(self, current_limit: int) -> int:
        """
        Get next higher token limit from ladder

        Args:
            current_limit: Current max_tokens value

        Returns:
            Next higher limit, or current limit if at max
        """
        for limit in self.max_token_ladder:
            if limit > current_limit:
                return limit

        # Already at max, return a very high limit as last resort
        return 30000

    def should_retry(self, current_limit: int) -> bool:
        """Check if we should attempt retry (haven't hit max limit yet)"""
        return current_limit < max(self.max_token_ladder)


def test_truncation_detector():
    """Test the truncation detector with known cases"""
    detector = TruncationDetector()

    # Test case 1: Incomplete JSON (missing closing brace)
    truncated_json = '''```json
{
  "reasoning": "This is a test",
  "recommendation": "Do something"'''

    is_trunc, reason = detector.is_truncated(truncated_json, parse_success=False)
    assert is_trunc, f"Should detect truncation, got: {reason}"
    print(f"✓ Test 1 passed: {reason}")

    # Test case 2: Complete JSON
    complete_json = '''```json
{
  "reasoning": "This is a test",
  "recommendation": "Do something"
}
```'''

    is_trunc, reason = detector.is_truncated(complete_json, parse_success=True)
    assert not is_trunc, f"Should not detect truncation for complete JSON"
    print(f"✓ Test 2 passed: {reason}")

    # Test case 3: Ends abruptly
    abrupt_ending = '''```json
{
  "reasoning": "This is a test and it ends here without proper'''

    is_trunc, reason = detector.is_truncated(abrupt_ending, parse_success=False)
    assert is_trunc, f"Should detect abrupt ending"
    print(f"✓ Test 3 passed: {reason}")

    # Test case 4: Token ladder
    assert detector.get_next_token_limit(8000) == 12000
    assert detector.get_next_token_limit(12000) == 16000
    assert detector.get_next_token_limit(16000) == 20000
    assert detector.get_next_token_limit(20000) == 30000
    print("✓ Test 4 passed: Token ladder works")

    print("\n✅ All truncation detector tests passed!")


if __name__ == "__main__":
    test_truncation_detector()
