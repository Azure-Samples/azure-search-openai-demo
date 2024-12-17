"""Utility functions for JSON handling and metrics dashboard data calculation."""
from pathlib import Path
from typing import Dict, Any, Union, List
import json
from datetime import datetime
from statistics import mean, stdev


def calculate_metrics_averages(results: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate comprehensive statistics for each metric across all test cases.
    Example:
        {
            "Contextual Precision": MetricStats(
                average=0.85,
                std_dev=0.12,
                success_rate=0.90,
                total_samples=50
            ),
            "AVG_SCORE (excl. custom metrics)": MetricStats(
                average=0.75,
                std_dev=0.15,
                success_rate=0.85,
                total_samples=250
            )
        }
    """
    base_metrics = {
        "Contextual Precision",
        "Contextual Recall",
        "Contextual Relevancy",
        "Answer Relevancy",
        "Faithfulness"
    }
    
    metrics_data: Dict[str, List[float]] = {}
    metrics_success: Dict[str, List[bool]] = {}
    
    for test_case in results.get("test_results", []):
        for metric in test_case.get("metrics_data", []):
            name = metric["name"]
            score = metric.get("score")
            threshold = metric.get("threshold", 0.5)
            
            if score is not None:
                metrics_data.setdefault(name, []).append(score)
                metrics_success.setdefault(name, []).append(score >= threshold)
    
    stats = {}
    base_metric_scores = []
    base_metric_successes = []
    
    for name in metrics_data:
        scores = metrics_data[name]
        successes = metrics_success[name]
        
        # Convert MetricStats to dictionary
        stats[name] = {
            "average": mean(scores),
            "std_dev": stdev(scores) if len(scores) > 1 else None,
            "success_rate": sum(successes) / len(successes),
            "total_samples": len(scores)
        }
        
        if name in base_metrics:
            base_metric_scores.extend(scores)
            base_metric_successes.extend(successes)
    
    if base_metric_scores:
        stats["AVG_SCORE (excl. custom metrics)"] = {
            "average": mean(base_metric_scores),
            "std_dev": stdev(base_metric_scores) if len(base_metric_scores) > 1 else None,
            "success_rate": sum(base_metric_successes)/len(base_metric_successes),
            "total_samples": len(metrics_data["Contextual Precision"])
        }
    
    return {"avg_scores": stats}

def read_json(filepath: Union[str, Path]) -> Dict[str, Any]:
    """
    Read a JSON file and return its contents.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {filepath}: {str(e)}") from e
    except IOError as e:
        raise IOError(f"Error reading file {filepath}: {str(e)}") from e

def save_results(results: Dict[str, Any], filepath: Union[str, Path]) -> None:
    """
    Save evaluation results to a JSON file with metadata and RAGAS scores.
    """
    results_dict = results.model_dump()
    metrics_averages = calculate_metrics_averages(results_dict)

    results_dict["metadata"] = {
        "timestamp": datetime.now().isoformat(),
        "num_test_cases": len(results_dict["test_results"]),
        "avg_scores": metrics_averages
    }
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, indent=2, ensure_ascii=False)
    except IOError as e:
        raise IOError(f"Error saving results to {filepath}: {str(e)}") 