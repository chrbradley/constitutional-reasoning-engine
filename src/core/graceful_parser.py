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
    
    def __init__(self, fallback_dir: str = "results/raw", experiment_id: str = None):
        if experiment_id:
            # Save raw API responses for complete data preservation
            self.fallback_dir = Path(f"results/experiments/{experiment_id}/data/raw")
        else:
            self.fallback_dir = Path(fallback_dir)
        self.fallback_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_constitutional_response(self, response: str, trial_id: str) -> Tuple[Dict[str, Any], ParseStatus]:
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
                self._save_raw_response(trial_id, response, "partial_extraction")
                return partial, ParseStatus.PARTIAL_SUCCESS
        except:
            pass
        
        # Method 3: Manual review fallback - NEVER lose the response
        self._save_raw_response(trial_id, response, "constitutional_manual_review_needed")

        # Return minimal structure with raw response for manual processing
        fallback_data = {
            "reasoning": f"[PARSING FAILED] Raw response saved to data/raw/{trial_id}.constitutional.json",
            "recommendation": "[PARSING FAILED]",
            "valuesApplied": ["parsing_failed"],
            "tradeoffsAcknowledged": "Response requires manual parsing - see raw response file",
            "_raw_response": response,
            "_parse_status": "manual_review",
            "_timestamp": datetime.now().isoformat()
        }

        return fallback_data, ParseStatus.MANUAL_REVIEW
    
    def parse_integrity_response(self, response: str, trial_id: str) -> Tuple[Dict[str, Any], ParseStatus]:
        """
        Parse integrity evaluation response with graceful fallback (Version 2.0 - 2D Rubric)
        Supports both new 2D format (epistemicIntegrity + valueTransparency) and old 3D format
        """

        # Method 1: Try robust JSON parsing
        try:
            parsed = self._robust_json_parse(response)
            # Try new 2D format first
            if self._validate_integrity_response_v2(parsed):
                return parsed, ParseStatus.SUCCESS
            # Fall back to old 3D format for backward compatibility
            elif self._validate_integrity_response_v1(parsed):
                # Convert old format to new format for unified data structure
                converted = self._convert_v1_to_v2(parsed)
                return converted, ParseStatus.SUCCESS
        except:
            pass

        # Method 2: Try partial extraction (2D format)
        try:
            partial = self._extract_partial_integrity(response)
            if partial and ('epistemicIntegrity' in partial or 'factualAdherence' in partial):
                self._save_raw_response(trial_id, response, "partial_integrity")
                # Convert old format if needed
                if 'factualAdherence' in partial and 'epistemicIntegrity' not in partial:
                    partial = self._convert_v1_to_v2(partial)
                return partial, ParseStatus.PARTIAL_SUCCESS
        except:
            pass

        # Method 3: Manual review fallback (use new 2D format)
        self._save_raw_response(trial_id, response, "integrity_manual_review_needed")

        # Return default scores that indicate parsing failed (new 2D format)
        fallback_data = {
            "epistemicIntegrity": {
                "score": -1,  # Special marker for parsing failure
                "explanation": f"[PARSING FAILED] See data/raw/{trial_id}.integrity.json",
                "examples": ["Parsing failed - see raw response"]
            },
            "valueTransparency": {
                "score": -1,
                "explanation": f"[PARSING FAILED] See data/raw/{trial_id}.integrity.json",
                "examples": ["Parsing failed - see raw response"]
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
        Extract integrity scores using regex when JSON parsing fails (V2.0 - 2D format)
        Also handles old V1.0 3D format for backward compatibility
        """
        partial = {}

        # Look for score patterns
        score_patterns = [
            r'"score":\s*(\d+)',
            r'score["\s]*:[\s]*(\d+)',
            r'Score:\s*(\d+)',
        ]

        # Try to extract new 2D dimensions first
        dimensions_v2 = ['epistemicIntegrity', 'valueTransparency']
        # Also try old 3D dimensions for backward compatibility
        dimensions_v1 = ['factualAdherence', 'valueTransparency', 'logicalCoherence']

        # Try new format first
        for dim in dimensions_v2:
            dim_pattern = rf'{dim}[^{{]*"score":\s*(\d+)'
            match = re.search(dim_pattern, response, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                partial[dim] = {
                    "score": score,
                    "explanation": "[PARTIAL_EXTRACTION] See raw response for full details",
                    "examples": ["Partial extraction from raw response"]
                }

        # If no new format found, try old format
        if not partial:
            for dim in dimensions_v1:
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

    def _validate_integrity_response_v2(self, data: dict) -> bool:
        """Validate integrity response has required structure (V2.0 - 2D format)"""
        required_dims = ["epistemicIntegrity", "valueTransparency"]
        if not all(dim in data for dim in required_dims):
            return False

        # Check each dimension has score
        for dim in required_dims:
            if not isinstance(data[dim], dict) or "score" not in data[dim]:
                return False

        return True

    def _validate_integrity_response_v1(self, data: dict) -> bool:
        """Validate integrity response has required structure (V1.0 - 3D format, legacy)"""
        required_dims = ["factualAdherence", "valueTransparency", "logicalCoherence"]
        if not all(dim in data for dim in required_dims):
            return False

        # Check each dimension has score
        for dim in required_dims:
            if not isinstance(data[dim], dict) or "score" not in data[dim]:
                return False

        return True

    def _convert_v1_to_v2(self, v1_data: dict) -> dict:
        """
        Convert old 3D format to new 2D format for backward compatibility
        Combines factualAdherence + logicalCoherence → epistemicIntegrity
        """
        v2_data = {}

        # Calculate epistemicIntegrity as average of factualAdherence + logicalCoherence
        if 'factualAdherence' in v1_data and 'logicalCoherence' in v1_data:
            fact_score = v1_data['factualAdherence'].get('score', 0)
            logic_score = v1_data['logicalCoherence'].get('score', 0)
            combined_score = (fact_score + logic_score) // 2

            v2_data['epistemicIntegrity'] = {
                "score": combined_score,
                "explanation": f"[CONVERTED FROM V1.0] Combined factualAdherence ({fact_score}) + logicalCoherence ({logic_score})",
                "examples": v1_data['factualAdherence'].get('examples', []) + v1_data['logicalCoherence'].get('examples', [])
            }
        elif 'factualAdherence' in v1_data:
            # If only factualAdherence available, use it directly
            v2_data['epistemicIntegrity'] = v1_data['factualAdherence'].copy()
            v2_data['epistemicIntegrity']['explanation'] = f"[CONVERTED FROM V1.0] {v2_data['epistemicIntegrity'].get('explanation', '')}"

        # Keep valueTransparency as-is
        if 'valueTransparency' in v1_data:
            v2_data['valueTransparency'] = v1_data['valueTransparency'].copy()

        # Recalculate overall score for 2D format
        if 'epistemicIntegrity' in v2_data and 'valueTransparency' in v2_data:
            v2_data['overallScore'] = (
                v2_data['epistemicIntegrity']['score'] +
                v2_data['valueTransparency']['score']
            ) // 2
        elif 'overallScore' in v1_data:
            v2_data['overallScore'] = v1_data['overallScore']

        # Preserve any metadata fields
        for key in v1_data:
            if key.startswith('_'):
                v2_data[key] = v1_data[key]

        return v2_data
    
    def _save_raw_response(self, trial_id: str, response: str, reason: str) -> None:
        """Save raw API response for data preservation"""
        # Extract layer type from reason (e.g., "facts_manual_review_needed" -> "facts")
        layer = reason.split('_')[0] if '_' in reason else reason

        # Simple filename without timestamp: trial_id.layer.json
        filename = f"{trial_id}.{layer}.json"
        filepath = self.fallback_dir / filename

        save_data = {
            "trial_id": trial_id,
            "layer": layer,
            "parse_status": reason,
            "timestamp": datetime.now().isoformat(),
            "raw_response": response
        }

        with open(filepath, 'w') as f:
            json.dump(save_data, f, indent=2)
    
    def get_raw_response_files(self) -> list:
        """Get list of all raw response files"""
        return list(self.fallback_dir.glob("*.json"))

    def get_files_needing_review(self) -> list:
        """Get list of files where parsing failed (indicated by parse_status)"""
        files_needing_review = []
        for filepath in self.fallback_dir.glob("*.json"):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    if 'manual_review' in data.get('parse_status', '') or 'partial' in data.get('parse_status', ''):
                        files_needing_review.append(filepath)
            except:
                pass
        return files_needing_review