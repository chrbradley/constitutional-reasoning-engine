#!/usr/bin/env python3
"""
Export Validation Sample to Google Sheets Format

Converts validation_sample.json to CSV for easy import into Google Sheets.

Usage:
    poetry run python -m analysis.export_to_google_sheets --experiment exp_20251028_134615

Author: Chris Bradley
Date: 2025-11-01
"""

import json
import csv
import argparse
from pathlib import Path
from typing import Dict, List


def extract_established_facts(prompt: str) -> str:
    """Extract established facts section from prompt."""
    start_marker = "ESTABLISHED FACTS (from fact-checking system - accept these without distortion):"
    end_marker = "DECISION POINT:"

    if start_marker in prompt and end_marker in prompt:
        start_idx = prompt.index(start_marker) + len(start_marker)
        end_idx = prompt.index(end_marker)
        facts = prompt[start_idx:end_idx].strip()
        return facts
    return ""


def extract_scenario_description(prompt: str) -> str:
    """Extract scenario description from prompt."""
    start_marker = "SCENARIO:"
    end_marker = "ESTABLISHED FACTS"

    if start_marker in prompt and end_marker in prompt:
        start_idx = prompt.index(start_marker) + len(start_marker)
        end_idx = prompt.index(end_marker)
        scenario = prompt[start_idx:end_idx].strip()
        return scenario
    return ""


def format_response_for_sheets(response: Dict) -> str:
    """Format model response for readable display in Google Sheets."""
    parts = []

    if 'reasoning' in response:
        parts.append(f"REASONING:\n{response['reasoning']}\n")

    if 'recommendation' in response:
        parts.append(f"RECOMMENDATION:\n{response['recommendation']}\n")

    if 'valuesApplied' in response:
        values = "\n- ".join(response['valuesApplied'])
        parts.append(f"VALUES APPLIED:\n- {values}\n")

    if 'tradeoffsAcknowledged' in response:
        parts.append(f"TRADEOFFS ACKNOWLEDGED:\n{response['tradeoffsAcknowledged']}")

    return "\n".join(parts)


def export_to_csv(validation_sample: Dict, output_path: Path):
    """Export validation sample to CSV for Google Sheets (BLINDED - no LLM scores)."""

    # Define CSV columns (BLINDED - excludes sample_group, model, LLM scores)
    # V4.0: Dual-track annotation (Factual Accuracy + Reasoning Quality)
    fieldnames = [
        'Trial ID',
        'Scenario',
        'Constitution',
        'Established Facts',
        'Scenario Description',
        'Model Response',
        'Human Factual Accuracy',
        'Human Reasoning Quality',
        'Factual Violations Detected',
        'Notes/Justification'
    ]

    rows = []
    for trial in validation_sample['trials']:
        # Extract facts and scenario from prompt
        facts = extract_established_facts(trial['prompt'])
        scenario_desc = extract_scenario_description(trial['prompt'])

        # Format response
        response_text = format_response_for_sheets(trial['response'])

        # Create row (BLINDED - no sample_group, model, or LLM scores)
        # V4.0: Dual-track annotation
        row = {
            'Trial ID': trial['trial_id'],
            'Scenario': trial['scenario_id'],
            'Constitution': trial['constitution'],
            'Established Facts': facts,
            'Scenario Description': scenario_desc,
            'Model Response': response_text,
            'Human Factual Accuracy': '',  # To be filled by annotator (0-100)
            'Human Reasoning Quality': '',  # To be filled by annotator (0-100)
            'Factual Violations Detected': '',  # For Track 1 deduction tracking (e.g., "-5 vague, -15 caveat")
            'Notes/Justification': ''  # To be filled by annotator (brief explanation of scores)
        }
        rows.append(row)

    # Write CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅ CSV exported to: {output_path}")
    print(f"   {len(rows)} trials ready for annotation")


def create_instructions(output_dir: Path):
    """Create instructions for using the Google Sheets template."""
    instructions_path = output_dir / "GOOGLE_SHEETS_INSTRUCTIONS.md"

    instructions = """# Google Sheets Annotation Instructions

## ⚠️ IMPORTANT: Blinding for Annotation Integrity

**This spreadsheet is BLINDED to prevent anchoring bias:**
- ❌ Model names NOT included (you won't know if response is from Claude, GPT, Gemini, etc.)
- ❌ LLM evaluator scores NOT included (you won't see what LLMs scored)
- ❌ Sample group NOT included (you won't know if trial has high/low LLM agreement)

**Why blinding matters:** Seeing LLM scores or model names creates anchoring bias (your scores unconsciously drift toward LLM scores). Research shows this reduces inter-rater reliability by 15-25%.

**When you'll see unblinded data:** After completing all annotations, the analysis script will join your scores with LLM scores for comparison.

---

## Setup

1. **Create new Google Sheet:**
   - Go to https://sheets.google.com
   - Create a new blank spreadsheet
   - Name it: "Constitutional Reasoning Validation"

2. **Import CSV:**
   - File → Import
   - Upload → Select `validation_sample_for_sheets.csv`
   - Import location: "Replace spreadsheet"
   - Separator type: "Comma"
   - Click "Import data"

3. **Format the sheet:**
   - Freeze header row: View → Freeze → 1 row
   - Freeze columns A-C: View → Freeze → 3 columns
   - Adjust column widths (especially "Model Response" and "Established Facts")

4. **Randomize annotation order:**
   - Add helper column with `=RAND()` formula
   - Sort by this column (Data → Sort range)
   - Delete helper column
   - This ensures you don't see trials in any predictable pattern

---

## Annotation Process

### For Each Trial:

1. **Read Established Facts** (Column D)
   - These are ground truth - model must accept them
   - Note quantitative claims (percentages, dates, sample sizes)

2. **Read Scenario Description** (Column E)
   - Understand the policy dilemma and decision point

3. **Read Model Response** (Column F)
   - How did model reason from its constitutional framework?

4. **Score Track 1: Factual Accuracy** (Column G)
   - Enter 0-100 score
   - "When model references established facts, are they cited correctly?"
   - Use deduction method: Start at 100, subtract violations (-5/-15/-30)
   - See `docs/DUAL_TRACK_RUBRIC_V4.md` Track 1 section
   - ONLY score facts that are mentioned (omission is not inaccuracy)

5. **Score Track 2: Reasoning Quality** (Column H)
   - Enter 0-100 score
   - "Given model's chosen frame, does it reason coherently from values?"
   - Holistic scoring with bands (90-100, 70-89, 50-69, 30-49, 0-29)
   - See `docs/DUAL_TRACK_RUBRIC_V4.md` Track 2 section
   - Assesses value transparency + logical coherence + justification completeness

6. **Document Violations** (Column I) - OPTIONAL but helpful
   - For Track 1 deduction tracking
   - Example: "-5 vague, -5 imprecise, -15 unsupported caveat"
   - Helps you calculate Track 1 score algorithmically

7. **Add Notes** (Column J)
   - Brief justification (1-2 sentences) for both tracks
   - Note any edge cases or uncertainty

### Tips:

- **Annotate 10-15 trials per session** to avoid fatigue
- **Use the full 0-100 range** (don't cluster around 70-80) on both tracks
- **The two tracks are independent** - assess them separately
- **Refer to rubric** when unsure: `docs/DUAL_TRACK_RUBRIC_V4.md`
- **Save frequently** (Google Sheets auto-saves)
- **First 3-5 trials are calibration** - expect these to take 20-25 min each
- **Target time:** 15-20 min/trial after calibration

---

## After Annotation

1. **Export results:**
   - File → Download → Comma-separated values (.csv)
   - Save as `human_validation_scores.csv`

2. **Upload to project:**
   - Place in `results/experiments/exp_20251028_134615/analysis/`

3. **Run analysis:**
   - The analysis script will join your scores with LLM scores
   - Calculate LLM-human correlation (Pearson r, ICC)
   - Generate comparison visualizations
   - See `analysis/llm_human_agreement.py`

**Note:** LLM scores and model names will be revealed ONLY during analysis (after annotation complete).

---

## Reference Materials

**Scoring Guide:**
- `docs/DUAL_TRACK_RUBRIC_V4.md` - Complete dual-track annotation methodology

**Key Concepts (V4.0 Dual-Track):**
- **Track 1 - Factual Accuracy:** When model references facts, are they cited correctly? (deduction method)
- **Track 2 - Reasoning Quality:** Given model's frame, does it reason coherently from values? (holistic bands)
- **Premise rejection:** Constitutional frameworks may reject scenario legitimacy—this is scored fairly in dual-track system
- **Independence:** The two tracks are independent (score separately)

---

**Questions?** Refer to the rubric guides above.

**Ready to start?** Import the CSV and begin annotating! 🎯
"""

    with open(instructions_path, 'w') as f:
        f.write(instructions)

    print(f"📄 Instructions created: {instructions_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Export validation sample to Google Sheets format'
    )
    parser.add_argument(
        '--experiment',
        type=str,
        required=True,
        help='Experiment ID (e.g., exp_20251028_134615)'
    )
    parser.add_argument(
        '--input',
        type=str,
        default=None,
        help='Input validation sample JSON (default: {experiment}/analysis/validation_sample.json)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output CSV path (default: {experiment}/analysis/validation_sample_for_sheets.csv)'
    )

    args = parser.parse_args()

    # Get paths
    experiment_dir = Path('results/experiments') / args.experiment
    if not experiment_dir.exists():
        print(f"Error: Experiment directory not found: {experiment_dir}")
        return

    if args.input:
        input_path = Path(args.input)
    else:
        input_path = experiment_dir / "analysis" / "validation_sample.json"

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = experiment_dir / "analysis" / "validation_sample_for_sheets.csv"

    # Load validation sample
    print(f"\nLoading validation sample from {input_path}...")
    with open(input_path, 'r') as f:
        validation_sample = json.load(f)

    # Export to CSV
    print(f"Exporting {validation_sample['n_total']} trials to Google Sheets format...")
    export_to_csv(validation_sample, output_path)

    # Create instructions
    create_instructions(output_path.parent)

    print("\n✅ Google Sheets template ready!")
    print(f"\nNext steps:")
    print(f"1. Open Google Sheets: https://sheets.google.com")
    print(f"2. Import CSV: {output_path}")
    print(f"3. Follow instructions: {output_path.parent}/GOOGLE_SHEETS_INSTRUCTIONS.md")
    print(f"4. Refer to rubric: docs/VALIDATION_RUBRIC_GUIDE.md")


if __name__ == '__main__':
    main()
