#!/usr/bin/env python3
"""
Validation Sample Selector

Creates a stratified sample of trials for human validation using hybrid approach:
- High-disagreement trials (LLM evaluators disagreed)
- High-agreement trials (LLM evaluators agreed)
- Stratified random (constitution/model/scenario diversity)

Usage:
    poetry run python -m analysis.select_validation_sample --experiment exp_20251028_134615 --n 30

Author: Chris Bradley
Date: 2025-11-01
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter
import argparse


def load_consensus_scores(experiment_dir: Path) -> List[Dict]:
    """Load consensus scores with disagreement metrics."""
    consensus_path = experiment_dir / "analysis" / "consensus_scores.json"
    with open(consensus_path, 'r') as f:
        data = json.load(f)
    return data['consensus_scores']


def load_trial_metadata(experiment_dir: Path, trial_id: str) -> Dict:
    """Load full trial metadata from layer2 file."""
    trial_path = experiment_dir / "data" / "layer2" / f"{trial_id}.json"
    with open(trial_path, 'r') as f:
        return json.load(f)


def classify_by_disagreement(consensus_scores: List[Dict],
                             high_threshold: float = 10.0,
                             low_threshold: float = 3.0) -> Dict[str, List[str]]:
    """
    Classify trials by evaluator disagreement level.

    Args:
        consensus_scores: List of consensus score objects
        high_threshold: Disagreement > this = high disagreement
        low_threshold: Disagreement < this = high agreement

    Returns:
        Dict with keys 'high_disagreement', 'medium_disagreement', 'high_agreement'
    """
    classification = {
        'high_disagreement': [],
        'medium_disagreement': [],
        'high_agreement': []
    }

    for trial in consensus_scores:
        disagreement = trial['max_disagreement']
        trial_id = trial['trial_id']

        if disagreement > high_threshold:
            classification['high_disagreement'].append(trial_id)
        elif disagreement < low_threshold:
            classification['high_agreement'].append(trial_id)
        else:
            classification['medium_disagreement'].append(trial_id)

    return classification


def stratified_random_sample(experiment_dir: Path,
                             consensus_scores: List[Dict],
                             n: int,
                             exclude_trials: List[str]) -> List[str]:
    """
    Select n trials ensuring constitution/model/scenario diversity.

    Strategy: Maximize coverage of all experimental factors
    """
    # Get all trials not already selected
    available_trials = [t['trial_id'] for t in consensus_scores
                       if t['trial_id'] not in exclude_trials]

    # Load metadata for available trials
    trials_with_metadata = []
    for trial_id in available_trials:
        metadata = load_trial_metadata(experiment_dir, trial_id)
        trials_with_metadata.append({
            'trial_id': trial_id,
            'constitution': metadata['constitution'],
            'model': metadata['model'],
            'scenario_id': metadata['scenario_id']
        })

    # Count existing representation in excluded trials (already selected)
    selected_metadata = []
    for trial_id in exclude_trials:
        metadata = load_trial_metadata(experiment_dir, trial_id)
        selected_metadata.append({
            'constitution': metadata['constitution'],
            'model': metadata['model'],
            'scenario_id': metadata['scenario_id']
        })

    constitution_counts = Counter(t['constitution'] for t in selected_metadata)
    model_counts = Counter(t['model'] for t in selected_metadata)
    scenario_counts = Counter(t['scenario_id'] for t in selected_metadata)

    # Greedy selection to maximize diversity
    selected = []
    remaining = trials_with_metadata.copy()

    for _ in range(min(n, len(remaining))):
        # Score each trial by how much it improves diversity
        scores = []
        for trial in remaining:
            # Lower counts = higher priority (underrepresented factors)
            score = (
                1.0 / (constitution_counts[trial['constitution']] + 1) +
                1.0 / (model_counts[trial['model']] + 1) +
                1.0 / (scenario_counts[trial['scenario_id']] + 1)
            )
            scores.append((score, trial))

        # Select trial with highest diversity score
        best_trial = max(scores, key=lambda x: x[0])[1]
        selected.append(best_trial['trial_id'])
        remaining.remove(best_trial)

        # Update counts
        constitution_counts[best_trial['constitution']] += 1
        model_counts[best_trial['model']] += 1
        scenario_counts[best_trial['scenario_id']] += 1

    return selected


def select_validation_sample(experiment_dir: Path,
                             n_total: int = 30,
                             n_high_disagreement: int = 15,
                             n_high_agreement: int = 10,
                             high_threshold: float = 10.0,
                             low_threshold: float = 3.0,
                             seed: Optional[int] = 42) -> Dict:
    """
    Select validation sample using hybrid stratified approach.

    Args:
        experiment_dir: Path to experiment directory
        n_total: Total sample size
        n_high_disagreement: Number of high-disagreement trials
        n_high_agreement: Number of high-agreement trials
        high_threshold: Disagreement threshold for "high"
        low_threshold: Disagreement threshold for "low"
        seed: Random seed for reproducibility

    Returns:
        Dict with selected trials and metadata
    """
    if seed is not None:
        random.seed(seed)

    # Load consensus scores
    consensus_scores = load_consensus_scores(experiment_dir)

    # Classify trials by disagreement
    classification = classify_by_disagreement(
        consensus_scores,
        high_threshold=high_threshold,
        low_threshold=low_threshold
    )

    print(f"\nDisagreement classification:")
    print(f"  High disagreement (>{high_threshold}): {len(classification['high_disagreement'])} trials")
    print(f"  Medium disagreement: {len(classification['medium_disagreement'])} trials")
    print(f"  High agreement (<{low_threshold}): {len(classification['high_agreement'])} trials")

    # Select high-disagreement trials
    high_dis_sample = random.sample(
        classification['high_disagreement'],
        min(n_high_disagreement, len(classification['high_disagreement']))
    )

    # Select high-agreement trials
    high_agr_sample = random.sample(
        classification['high_agreement'],
        min(n_high_agreement, len(classification['high_agreement']))
    )

    # Calculate how many stratified random needed
    n_stratified = n_total - len(high_dis_sample) - len(high_agr_sample)

    # Select stratified random sample (excluding already selected)
    exclude_trials = high_dis_sample + high_agr_sample
    stratified_sample = stratified_random_sample(
        experiment_dir,
        consensus_scores,
        n_stratified,
        exclude_trials
    )

    # Combine all selected trials
    all_selected = high_dis_sample + high_agr_sample + stratified_sample

    print(f"\nSample composition:")
    print(f"  High disagreement: {len(high_dis_sample)} trials")
    print(f"  High agreement: {len(high_agr_sample)} trials")
    print(f"  Stratified random: {len(stratified_sample)} trials")
    print(f"  Total: {len(all_selected)} trials")

    # Load full metadata for selected trials
    validation_sample = []
    for trial_id in all_selected:
        # Get layer2 metadata
        layer2_data = load_trial_metadata(experiment_dir, trial_id)

        # Get consensus scores
        consensus = next(t for t in consensus_scores if t['trial_id'] == trial_id)

        # Determine sample group
        if trial_id in high_dis_sample:
            sample_group = 'high_disagreement'
        elif trial_id in high_agr_sample:
            sample_group = 'high_agreement'
        else:
            sample_group = 'stratified_random'

        validation_sample.append({
            'trial_id': trial_id,
            'sample_group': sample_group,
            'scenario_id': layer2_data['scenario_id'],
            'constitution': layer2_data['constitution'],
            'model': layer2_data['model'],
            'llm_consensus': {
                'epistemic_integrity': consensus['mean_all']['epistemic_integrity'],
                'value_transparency': consensus['mean_all']['value_transparency'],
                'overall_score': consensus['mean_all']['overall_score']
            },
            'llm_disagreement': consensus['max_disagreement'],
            'prompt': layer2_data['prompt_sent'],
            'response': layer2_data['response_parsed']
        })

    # Randomize order (so annotator doesn't see grouped by disagreement level)
    random.shuffle(validation_sample)

    # Print diversity statistics
    print("\nDiversity statistics:")
    constitutions = Counter(t['constitution'] for t in validation_sample)
    models = Counter(t['model'] for t in validation_sample)
    scenarios = Counter(t['scenario_id'] for t in validation_sample)

    print(f"  Constitutions: {dict(constitutions)}")
    print(f"  Models: {dict(models)}")
    print(f"  Scenarios (top 5): {dict(scenarios.most_common(5))}")

    return {
        'experiment_id': experiment_dir.name,
        'selection_strategy': 'hybrid_stratified',
        'n_total': len(all_selected),
        'n_high_disagreement': len(high_dis_sample),
        'n_high_agreement': len(high_agr_sample),
        'n_stratified_random': len(stratified_sample),
        'high_disagreement_threshold': high_threshold,
        'low_agreement_threshold': low_threshold,
        'random_seed': seed,
        'trials': validation_sample
    }


def main():
    parser = argparse.ArgumentParser(
        description='Select validation sample for human annotation'
    )
    parser.add_argument(
        '--experiment',
        type=str,
        required=True,
        help='Experiment ID (e.g., exp_20251028_134615)'
    )
    parser.add_argument(
        '--n-total',
        type=int,
        default=30,
        help='Total sample size (default: 30)'
    )
    parser.add_argument(
        '--n-high-disagreement',
        type=int,
        default=15,
        help='Number of high-disagreement trials (default: 15)'
    )
    parser.add_argument(
        '--n-high-agreement',
        type=int,
        default=10,
        help='Number of high-agreement trials (default: 10)'
    )
    parser.add_argument(
        '--high-threshold',
        type=float,
        default=10.0,
        help='Disagreement threshold for high-disagreement (default: 10.0)'
    )
    parser.add_argument(
        '--low-threshold',
        type=float,
        default=3.0,
        help='Disagreement threshold for high-agreement (default: 3.0)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output file path (default: {experiment}/analysis/validation_sample.json)'
    )

    args = parser.parse_args()

    # Get experiment directory
    experiment_dir = Path('results/experiments') / args.experiment
    if not experiment_dir.exists():
        print(f"Error: Experiment directory not found: {experiment_dir}")
        return

    # Select validation sample
    print(f"\nSelecting validation sample from {args.experiment}...")
    print(f"Target: {args.n_total} trials ({args.n_high_disagreement} high-disagreement, "
          f"{args.n_high_agreement} high-agreement, "
          f"{args.n_total - args.n_high_disagreement - args.n_high_agreement} stratified random)")

    validation_sample = select_validation_sample(
        experiment_dir=experiment_dir,
        n_total=args.n_total,
        n_high_disagreement=args.n_high_disagreement,
        n_high_agreement=args.n_high_agreement,
        high_threshold=args.high_threshold,
        low_threshold=args.low_threshold,
        seed=args.seed
    )

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = experiment_dir / "analysis" / "validation_sample.json"

    # Save to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(validation_sample, f, indent=2)

    print(f"\n✅ Validation sample saved to: {output_path}")
    print(f"   Total trials: {validation_sample['n_total']}")
    print(f"   Ready for human annotation!")


if __name__ == '__main__':
    main()
