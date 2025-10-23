"""
Graceful JSON parsing with fallback handling for Constitutional Reasoning Engine
Never throw away model responses - always save them for manual review
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from enum import Enum


class ParseStatus(Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"  # Some fields extracted
    MANUAL_REVIEW = "manual_review"     # Raw response saved for review
    FAILED = "failed"                   # Complete failure


class GracefulJsonParser:
    """
    Graceful JSON parser that never throws away responses
    """
    
    def __init__(self, fallback_dir: str = "results/manual_review", experiment_id: str = None):
        if experiment_id:
            # Organize manual review by experiment run
            self.fallback_dir = Path(f"results/runs/{experiment_id}/manual_review")
        else:
            self.fallback_dir = Path(fallback_dir)
        self.fallback_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_constitutional_response(self, response: str, test_id: str) -> Tuple[Dict[str, Any], ParseStatus]:
        """
        Parse constitutional response with graceful fallback
        
        Returns:
            Tuple of (parsed_data, status)
            - parsed_data: Best attempt at extracting fields
            - status: ParseStatus indicating level of success
        """
        
        # Method 1: Try robust JSON parsing
        try:
            parsed = self._robust_json_parse(response)
            if self._validate_constitutional_response(parsed):
                return parsed, ParseStatus.SUCCESS
        except:
            pass
        
        # Method 2: Try partial extraction
        try:
            partial = self._extract_partial_fields(response)
            if partial and len(partial) >= 2:  # At least 2 fields
                self._save_raw_response(test_id, response, "partial_extraction")
                return partial, ParseStatus.PARTIAL_SUCCESS
        except:
            pass
        
        # Method 3: Manual review fallback - NEVER lose the response
        self._save_raw_response(test_id, response, "manual_review_needed")
        
        # Return minimal structure with raw response for manual processing
        fallback_data = {
            "reasoning": f"[MANUAL_REVIEW_NEEDED] Raw response saved to {self.fallback_dir}/{test_id}_manual_review.json",
            "recommendation": "[MANUAL_REVIEW_NEEDED]",
            "valuesApplied": ["manual_review_needed"],
            "tradeoffsAcknowledged": "Response requires manual parsing - see raw response file",
            "_raw_response": response,
            "_parse_status": "manual_review",
            "_timestamp": datetime.now().isoformat()
        }
        
        return fallback_data, ParseStatus.MANUAL_REVIEW
    
    def parse_integrity_response(self, response: str, test_id: str) -> Tuple[Dict[str, Any], ParseStatus]:
        """
        Parse integrity evaluation response with graceful fallback
        """
        
        # Method 1: Try robust JSON parsing
        try:
            parsed = self._robust_json_parse(response)
            if self._validate_integrity_response(parsed):
                return parsed, ParseStatus.SUCCESS
        except:
            pass
        
        # Method 2: Try partial extraction
        try:
            partial = self._extract_partial_integrity(response)
            if partial and 'factualAdherence' in partial:
                self._save_raw_response(test_id, response, "partial_integrity")
                return partial, ParseStatus.PARTIAL_SUCCESS
        except:
            pass
        
        # Method 3: Manual review fallback
        self._save_raw_response(test_id, response, "integrity_manual_review")
        
        # Return default scores that indicate manual review needed
        fallback_data = {
            "factualAdherence": {
                "score": -1,  # Special marker for manual review
                "explanation": "[MANUAL_REVIEW_NEEDED] See raw response file",
                "examples": ["Manual review required"]
            },
            "valueTransparency": {
                "score": -1,
                "explanation": "[MANUAL_REVIEW_NEEDED] See raw response file", 
                "examples": ["Manual review required"]
            },
            "logicalCoherence": {
                "score": -1,
                "explanation": "[MANUAL_REVIEW_NEEDED] See raw response file",
                "examples": ["Manual review required"]
            },
            "overallScore": -1,
            "_raw_response": response,
            "_parse_status": "manual_review",
            "_timestamp": datetime.now().isoformat()
        }
        
        return fallback_data, ParseStatus.MANUAL_REVIEW
    
    def _robust_json_parse(self, response: str) -> dict:
        """
        Robust JSON parsing with multiple fallback methods
        """
        # Method 1: Standard cleaning
        try:
            clean = self._clean_json_response(response)
            return json.loads(clean)
        except:
            pass
        
        # Method 2: Remove control characters
        try:
            clean = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', response)
            clean = self._clean_json_response(clean)
            return json.loads(clean)
        except:
            pass
        
        # Method 3: Extract first complete JSON object
        try:
            start = response.find('{')
            if start == -1:
                raise ValueError("No JSON object found")
                
            brace_count = 0
            end = start
            in_string = False
            escape_next = False
            
            for i, char in enumerate(response[start:], start):
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\':
                    escape_next = True
                    continue
                    
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                    
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end = i
                            break
            
            if brace_count == 0:
                json_str = response[start:end+1]
                # Clean any control characters
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                return json.loads(json_str)
                
        except:
            pass
        
        # Method 4: Remove trailing content after last }
        try:
            clean = self._clean_json_response(response)
            last_brace = clean.rfind('}')
            if last_brace != -1:
                clean = clean[:last_brace+1]
            return json.loads(clean)
        except:
            pass
        
        raise ValueError(f"Could not parse JSON from response")
    
    def _clean_json_response(self, response: str) -> str:
        """Clean JSON response by removing markdown code blocks"""
        clean = response.strip()
        if clean.startswith('```json'):
            clean = clean[7:]
        if clean.endswith('```'):
            clean = clean[:-3]
        return clean.strip()
    
    def _extract_partial_fields(self, response: str) -> Dict[str, Any]:
        """
        Extract fields using regex patterns when JSON parsing fails
        """
        partial = {}
        
        # Extract reasoning
        reasoning_patterns = [
            r'"reasoning":\s*"([^"]*(?:\\"[^"]*)*)"',
            r'reasoning["\s]*:[\s]*"([^"]*)"',
            r'Reasoning:\s*([^\\n]+)',
        ]
        
        for pattern in reasoning_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                partial["reasoning"] = match.group(1).replace('\\"', '"')
                break
        
        # Extract recommendation
        rec_patterns = [
            r'"recommendation":\s*"([^"]*(?:\\"[^"]*)*)"',
            r'recommendation["\s]*:[\s]*"([^"]*)"',
            r'Recommendation:\s*([^\\n]+)',
        ]
        
        for pattern in rec_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                partial["recommendation"] = match.group(1).replace('\\"', '"')
                break
        
        # Extract values applied (look for array)
        values_patterns = [
            r'"valuesApplied":\s*(\[[^\]]*\])',
            r'valuesApplied["\s]*:[\s]*(\[[^\]]*\])',
        ]
        
        for pattern in values_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                try:
                    partial["valuesApplied"] = json.loads(match.group(1))
                except:
                    # Fallback: extract quoted strings
                    values = re.findall(r'"([^"]*)"', match.group(1))
                    if values:
                        partial["valuesApplied"] = values
                break
        
        # Extract tradeoffs
        tradeoff_patterns = [
            r'"tradeoffsAcknowledged":\s*"([^"]*(?:\\"[^"]*)*)"',
            r'tradeoffsAcknowledged["\s]*:[\s]*"([^"]*)"',
        ]
        
        for pattern in tradeoff_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                partial["tradeoffsAcknowledged"] = match.group(1).replace('\\"', '"')
                break
        
        return partial
    
    def _extract_partial_integrity(self, response: str) -> Dict[str, Any]:
        """
        Extract integrity scores using regex when JSON parsing fails
        """
        partial = {}
        
        # Look for score patterns
        score_patterns = [
            r'"score":\s*(\d+)',
            r'score["\s]*:[\s]*(\d+)',
            r'Score:\s*(\d+)',
        ]
        
        # Try to extract each dimension
        dimensions = ['factualAdherence', 'valueTransparency', 'logicalCoherence']
        
        for dim in dimensions:
            # Look for this dimension's score
            dim_pattern = rf'{dim}[^{{]*"score":\s*(\d+)'
            match = re.search(dim_pattern, response, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                partial[dim] = {
                    "score": score,
                    "explanation": "[PARTIAL_EXTRACTION] See raw response for full details",
                    "examples": ["Partial extraction from raw response"]
                }
        
        # Calculate overall if we have at least one dimension
        if partial:
            scores = [partial[dim]["score"] for dim in partial if "score" in partial[dim]]
            if scores:
                partial["overallScore"] = sum(scores) // len(scores)
        
        return partial
    
    def _validate_constitutional_response(self, data: dict) -> bool:
        """Validate constitutional response has required fields"""
        required_fields = ["reasoning", "recommendation", "valuesApplied", "tradeoffsAcknowledged"]
        return all(field in data for field in required_fields)
    
    def _validate_integrity_response(self, data: dict) -> bool:
        """Validate integrity response has required structure"""
        required_dims = ["factualAdherence", "valueTransparency", "logicalCoherence"]
        if not all(dim in data for dim in required_dims):
            return False
        
        # Check each dimension has score
        for dim in required_dims:
            if not isinstance(data[dim], dict) or "score" not in data[dim]:
                return False
        
        return True
    
    def _save_raw_response(self, test_id: str, response: str, reason: str) -> None:
        """Save raw response for manual review"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{test_id}_{reason}_{timestamp}.json"
        filepath = self.fallback_dir / filename
        
        save_data = {
            "test_id": test_id,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "raw_response": response,
            "instructions": {
                "manual_parsing": "This response could not be automatically parsed",
                "next_steps": [
                    "1. Review the raw_response field",
                    "2. Manually extract the required fields",
                    "3. Update the test result with correct data",
                    "4. Consider improving the parser for this pattern"
                ]
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(save_data, f, indent=2)
        
        print(f"📁 Saved raw response: {filename}")
    
    def get_manual_review_files(self) -> list:
        """Get list of files that need manual review"""
        return list(self.fallback_dir.glob("*manual_review*.json"))
    
    def get_partial_extraction_files(self) -> list:
        """Get list of files with partial extraction"""
        return list(self.fallback_dir.glob("*partial*.json"))