#!/bin/bash
#
# Minimal incremental test: 1 scenario × 1 constitution × 1 model
#
# This creates a clean baseline test to verify the pipeline works
# before scaling up to multiple scenarios/constitutions/models.
#
# Test configuration:
#   - Scenario: vaccine-mandate-religious-exemption
#   - Constitution: harm-minimization
#   - Layer 2 Model: claude-sonnet-4-5
#   - Layer 3 Evaluator: claude-sonnet-4-5 (default)
#

~/.local/bin/poetry run python -m src.runner --new \
  --scenarios vaccine-mandate-religious-exemption \
  --constitutions harm-minimization \
  --layer2-models claude-sonnet-4-5
