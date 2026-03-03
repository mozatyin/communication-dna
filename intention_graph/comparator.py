"""Compare two IntentionGraphs and compute evaluation metrics."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from intention_graph.models import IntentionGraph


@dataclass
class GraphMetrics:
    """Evaluation metrics for comparing predicted vs ground truth graphs."""
    node_recall: float = 0.0
    node_precision: float = 0.0
    node_f1: float = 0.0
    edge_f1: float = 0.0
    probability_mae: float = 0.0
    end_goal_correct: bool = False
    matched_nodes: int = 0
    total_predicted_nodes: int = 0
    total_truth_nodes: int = 0

    def to_dict(self) -> dict:
        return {
            "node_recall": round(self.node_recall, 3),
            "node_precision": round(self.node_precision, 3),
            "node_f1": round(self.node_f1, 3),
            "edge_f1": round(self.edge_f1, 3),
            "probability_mae": round(self.probability_mae, 3),
            "end_goal_correct": self.end_goal_correct,
            "matched_nodes": self.matched_nodes,
            "total_predicted_nodes": self.total_predicted_nodes,
            "total_truth_nodes": self.total_truth_nodes,
        }


def compare_graphs(predicted: IntentionGraph, truth: IntentionGraph) -> GraphMetrics:
    """Compare a predicted graph against ground truth and compute metrics."""
    node_matches = _match_nodes(predicted, truth)
    matched = len(node_matches)
    total_pred = len(predicted.nodes)
    total_truth = len(truth.nodes)

    node_recall = matched / total_truth if total_truth > 0 else 1.0
    node_precision = matched / total_pred if total_pred > 0 else 1.0
    node_f1 = (
        2 * node_precision * node_recall / (node_precision + node_recall)
        if (node_precision + node_recall) > 0
        else 0.0
    )

    edge_f1, prob_mae = _compare_edges(predicted, truth, node_matches)

    end_goal_correct = False
    if truth.end_goal and predicted.end_goal:
        truth_goal_text = next(
            (n.text for n in truth.nodes if n.id == truth.end_goal), ""
        )
        pred_goal_text = next(
            (n.text for n in predicted.nodes if n.id == predicted.end_goal), ""
        )
        end_goal_correct = _text_similarity(pred_goal_text, truth_goal_text) > 0.5

    return GraphMetrics(
        node_recall=node_recall,
        node_precision=node_precision,
        node_f1=node_f1,
        edge_f1=edge_f1,
        probability_mae=prob_mae,
        end_goal_correct=end_goal_correct,
        matched_nodes=matched,
        total_predicted_nodes=total_pred,
        total_truth_nodes=total_truth,
    )


def _match_nodes(
    predicted: IntentionGraph, truth: IntentionGraph, threshold: float = 0.4
) -> dict[str, str]:
    """Match predicted nodes to truth nodes by text similarity."""
    matches: dict[str, str] = {}
    used_truth: set[str] = set()

    pairs = []
    for p in predicted.nodes:
        for t in truth.nodes:
            sim = _text_similarity(p.text, t.text)
            pairs.append((sim, p.id, t.id))
    pairs.sort(reverse=True)

    for sim, pred_id, truth_id in pairs:
        if sim < threshold:
            break
        if pred_id in matches or truth_id in used_truth:
            continue
        matches[pred_id] = truth_id
        used_truth.add(truth_id)

    return matches


def _compare_edges(
    predicted: IntentionGraph,
    truth: IntentionGraph,
    node_matches: dict[str, str],
) -> tuple[float, float]:
    """Compare edges and return (edge_f1, probability_mae)."""
    pred_edges = set()
    pred_probs: dict[tuple, float] = {}
    for t in predicted.transitions:
        mapped_from = node_matches.get(t.from_id)
        mapped_to = node_matches.get(t.to_id)
        if mapped_from and mapped_to:
            key = (mapped_from, mapped_to, t.relation)
            pred_edges.add(key)
            pred_probs[key] = t.base_probability

    truth_edges = set()
    truth_probs: dict[tuple, float] = {}
    for t in truth.transitions:
        key = (t.from_id, t.to_id, t.relation)
        truth_edges.add(key)
        truth_probs[key] = t.base_probability

    if not truth_edges and not pred_edges:
        return 1.0, 0.0

    tp = len(pred_edges & truth_edges)
    precision = tp / len(pred_edges) if pred_edges else 0.0
    recall = tp / len(truth_edges) if truth_edges else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    matched_edges = pred_edges & truth_edges
    if matched_edges:
        mae = sum(
            abs(pred_probs[e] - truth_probs[e]) for e in matched_edges
        ) / len(matched_edges)
    else:
        mae = 0.0

    return f1, mae


def _text_similarity(a: str, b: str) -> float:
    """Compute text similarity between two strings (0.0-1.0)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()
