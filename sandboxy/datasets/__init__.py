"""Dataset support for multi-case benchmarking."""

from sandboxy.datasets.loader import Dataset, TestCase, load_dataset, load_multiple_datasets
from sandboxy.datasets.runner import (
    CaseResult,
    DatasetResult,
    run_dataset,
    run_dataset_parallel,
)

__all__ = [
    "Dataset",
    "TestCase",
    "load_dataset",
    "load_multiple_datasets",
    "CaseResult",
    "DatasetResult",
    "run_dataset",
    "run_dataset_parallel",
]
