"""
Workflow Configuration for Options Analysis System

This module defines authoritative constants for the analysis workflow,
ensuring consistency across all modules.

**BR-01 Fix**: Unified Progress Total Definition
- All report_progress() calls must use TOTAL_ANALYSIS_STEPS
- This prevents progress inconsistency bugs (e.g., Module 32 using different total)
- Single source of truth for workflow orchestration
"""

# Authoritative progress contract for main analysis workflow
# This constant defines the total number of steps in the complete analysis
# All report_progress() calls MUST use this value for the 'total' parameter
TOTAL_ANALYSIS_STEPS = 30

# Future: If conditional modules are added, this could become a function:
# def get_total_analysis_steps(enable_advanced=False):
#     base_steps = 28
#     if enable_advanced:
#         base_steps += 4  # Additional advanced modules
#     return base_steps
