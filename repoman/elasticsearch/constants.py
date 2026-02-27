"""Elasticsearch constants."""

from __future__ import annotations

REPOSITORIES_INDEX = "repoman-repositories"
ISSUES_INDEX = "repoman-issues"

# Kept as a data stream to support ILM delete (90d) semantics.
ANALYSIS_DATA_STREAM = "repoman-analysis"

ANALYSIS_ILM_POLICY = "repoman-analysis-ilm"
ANALYSIS_INDEX_TEMPLATE = "repoman-analysis-template"
