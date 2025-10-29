"""
Shared Layer 3 Evaluation Logic

Centralizes integrity evaluation logic used by:
- src/runner.py (during full trial execution)
- src/tools/re_evaluate_layer3.py (re-evaluating existing Layer 2 outputs)
"""
import time
from typing import Dict, Any, Optional
from datetime import datetime

from src.core.models import get_model_response
from src.core.graceful_parser import GracefulJsonParser, ParseStatus
from src.core.truncation_detector import TruncationDetector
from src.core.experiment_state import ExperimentManager


async def evaluate_layer3(
    trial_id: str,
    eval_prompt: str,
    evaluator_id: str,
    is_primary: bool,
    experiment_manager: ExperimentManager,
    parser: GracefulJsonParser,
    save_result: bool = True
) -> Dict[str, Any]:
    """
    Run Layer 3 integrity evaluation on a trial

    Args:
        trial_id: Unique trial identifier
        eval_prompt: Evaluation prompt (from build_integrity_evaluation_prompt_likert/binary/ternary)
        evaluator_id: Model ID of the evaluator
        is_primary: If True, saves to layer3/raw/ and layer3/parsed/
                   If False, saves to layer3/{evaluator_id}/raw/ and layer3/{evaluator_id}/parsed/
        experiment_manager: ExperimentManager instance
        parser: GracefulJsonParser instance
        save_result: If True, saves result immediately. If False, returns layer3_data for caller to save

    Returns:
        {
            "success": bool,
            "integrity_data": dict or None,
            "layer3_data": dict (full evaluation data, only if save_result=False),
            "error": str or None,
            "elapsed_ms": int,
            "max_tokens_used": int
        }
    """
    try:
        # Create evaluator-specific audit callback
        def layer3_audit_callback(request_params, response, error, http_status, retry_attempt):
            experiment_manager.save_api_audit_log(
                trial_id=trial_id,
                layer=3,
                model_id=evaluator_id,
                request_params=request_params,
                response=response,
                error=error,
                http_status=http_status,
                retry_attempt=retry_attempt
            )

        # Try with increasing max_tokens if truncated
        truncation_detector = TruncationDetector()
        max_tokens_integrity = 4000  # Start with baseline (evaluations are verbose)
        max_retries = 3

        # Capture Layer 3 timing
        layer3_start = time.time()

        integrity_response = None  # Initialize for error handling
        for attempt in range(max_retries):
            integrity_response = await get_model_response(
                model_id=evaluator_id,
                prompt=eval_prompt,
                temperature=0.3,
                max_tokens=max_tokens_integrity,
                audit_callback=layer3_audit_callback
            )

            # Parse integrity response with graceful fallback
            integrity_data, integrity_status = parser.parse_integrity_response(
                integrity_response,
                f"{trial_id}_integrity_{evaluator_id}"
            )

            # Check if truncated
            is_truncated, trunc_reason = truncation_detector.is_truncated(
                integrity_response,
                parse_success=(integrity_status == ParseStatus.SUCCESS)
            )

            if not is_truncated or integrity_status == ParseStatus.SUCCESS:
                # Success or not truncated - keep the result
                break

            # Truncated - retry with higher limit
            if attempt < max_retries - 1:
                new_limit = truncation_detector.get_next_token_limit(max_tokens_integrity)
                print(f"⚠️  Layer 3 ({evaluator_id}) response truncated ({trunc_reason}), retrying with max_tokens={new_limit}")
                max_tokens_integrity = new_limit
            else:
                print(f"⚠️  Max retries reached for Layer 3 ({evaluator_id}), using partial response")

        if integrity_status == ParseStatus.MANUAL_REVIEW:
            print(f"⚠️  Integrity response parsing needs manual review for {trial_id} ({evaluator_id})")
        elif integrity_status == ParseStatus.PARTIAL_SUCCESS:
            print(f"⚠️  Partial integrity response extraction for {trial_id} ({evaluator_id})")

        # Calculate evaluator timing
        elapsed_ms = int((time.time() - layer3_start) * 1000)

        # Log token usage if needed
        if max_tokens_integrity > 4000:
            print(f"📊 Layer 3 ({evaluator_id}) required {max_tokens_integrity} tokens for complete response")

        # Calculate overall score (V2.0 - 2D format with backward compatibility)
        if integrity_status == ParseStatus.MANUAL_REVIEW:
            overall_score = -1
        else:
            # Try new 2D format first
            if 'epistemicIntegrity' in integrity_data and 'valueTransparency' in integrity_data:
                overall_score = (
                    integrity_data['epistemicIntegrity']['score'] +
                    integrity_data['valueTransparency']['score']
                ) / 2
            # Fall back to old 3D format for backward compatibility
            elif 'factualAdherence' in integrity_data and 'valueTransparency' in integrity_data and 'logicalCoherence' in integrity_data:
                overall_score = (
                    integrity_data['factualAdherence']['score'] +
                    integrity_data['valueTransparency']['score'] +
                    integrity_data['logicalCoherence']['score']
                ) / 3
            else:
                # If neither format is complete, use -1 to indicate error
                overall_score = -1
            integrity_data['overallScore'] = round(overall_score)

        # Save Layer 3 output - aligned with data schema
        layer3_data = {
            "trial_id": trial_id,
            "timestamp": datetime.now().isoformat(),
            "evaluationModel": evaluator_id,

            # Prompt and response
            "prompt_sent": eval_prompt,
            "response_raw": integrity_response,
            "response_parsed": integrity_data,

            # Parsing metadata
            "parsing": {
                "success": integrity_status == ParseStatus.SUCCESS,
                "method": "standard_json" if integrity_status == ParseStatus.SUCCESS else "manual_review",
                "fallback_attempts": 0,
                "error": None if integrity_status == ParseStatus.SUCCESS else integrity_status.value,
                "manual_review_path": None
            },

            # Performance metrics
            "tokens_used": max_tokens_integrity,
            "latency_ms": elapsed_ms,

            # Legacy compatibility
            "integrityEvaluation": integrity_data  # Keep for backward compatibility
        }

        # Save if requested (default behavior for backward compatibility)
        if save_result:
            experiment_manager.save_evaluator_response(
                trial_id=trial_id,
                evaluator_id=evaluator_id,
                is_primary=is_primary,
                raw_content=integrity_response,
                parsed_data=layer3_data
            )

            # Only update trial status for primary evaluator
            if is_primary:
                experiment_manager.update_layer_status(trial_id, 3, "completed", evaluator_id)

        return {
            "success": True,
            "integrity_data": integrity_data,
            "layer3_data": layer3_data,  # Include full data for caller to use
            "error": None,
            "elapsed_ms": elapsed_ms,
            "max_tokens_used": max_tokens_integrity
        }

    except Exception as e:
        error_msg = f"Layer 3 (integrity evaluation with {evaluator_id}) failed: {str(e)}"

        # Extract detailed error information
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.now().isoformat(),
            "layer": 3,
            "model_id": evaluator_id
        }

        # If exception has attached error_details from models.py, include them
        if hasattr(e, 'error_details'):
            error_details.update(e.error_details)

        # Save error if requested
        if save_result:
            experiment_manager.save_evaluator_error(
                trial_id=trial_id,
                evaluator_id=evaluator_id,
                is_primary=is_primary,
                error_details=error_details
            )

            # Only update trial status for primary evaluator
            if is_primary:
                experiment_manager.update_layer_status(trial_id, 3, "failed", evaluator_id, error_msg)

        print(f"❌ {trial_id} - Evaluator {evaluator_id} failed: {error_msg}")

        return {
            "success": False,
            "integrity_data": None,
            "layer3_data": None,
            "error": error_msg,
            "elapsed_ms": 0,
            "max_tokens_used": 0
        }
