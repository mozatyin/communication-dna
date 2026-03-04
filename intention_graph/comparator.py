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
    edge_f1_relaxed: float = 0.0  # ignoring relation type
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
            "edge_f1_relaxed": round(self.edge_f1_relaxed, 3),
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

    edge_f1, prob_mae, edge_f1_relaxed = _compare_edges(predicted, truth, node_matches)

    end_goal_correct = False
    if truth.end_goal and predicted.end_goal:
        # Primary: check if predicted end_goal maps to truth end_goal via node matching
        mapped_pred_goal = node_matches.get(predicted.end_goal)
        if mapped_pred_goal == truth.end_goal:
            end_goal_correct = True
        else:
            # Fallback: text similarity for cases where node IDs differ
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
        edge_f1_relaxed=edge_f1_relaxed,
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
) -> tuple[float, float, float]:
    """Compare edges and return (edge_f1, probability_mae, edge_f1_relaxed)."""
    pred_edges = set()
    pred_edges_relaxed = set()
    pred_probs: dict[tuple, float] = {}
    for t in predicted.transitions:
        mapped_from = node_matches.get(t.from_id)
        mapped_to = node_matches.get(t.to_id)
        if mapped_from and mapped_to:
            key = (mapped_from, mapped_to, t.relation)
            pred_edges.add(key)
            pred_edges_relaxed.add((mapped_from, mapped_to))
            pred_probs[key] = t.base_probability

    truth_edges = set()
    truth_edges_relaxed = set()
    truth_probs: dict[tuple, float] = {}
    for t in truth.transitions:
        key = (t.from_id, t.to_id, t.relation)
        truth_edges.add(key)
        truth_edges_relaxed.add((t.from_id, t.to_id))
        truth_probs[key] = t.base_probability

    if not truth_edges and not pred_edges:
        return 1.0, 0.0, 1.0

    # Strict F1 (includes relation type)
    tp = len(pred_edges & truth_edges)
    precision = tp / len(pred_edges) if pred_edges else 0.0
    recall = tp / len(truth_edges) if truth_edges else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # Relaxed F1 (ignores relation type)
    tp_relaxed = len(pred_edges_relaxed & truth_edges_relaxed)
    prec_relaxed = tp_relaxed / len(pred_edges_relaxed) if pred_edges_relaxed else 0.0
    rec_relaxed = tp_relaxed / len(truth_edges_relaxed) if truth_edges_relaxed else 0.0
    f1_relaxed = (
        2 * prec_relaxed * rec_relaxed / (prec_relaxed + rec_relaxed)
        if (prec_relaxed + rec_relaxed) > 0
        else 0.0
    )

    matched_edges = pred_edges & truth_edges
    if matched_edges:
        mae = sum(
            abs(pred_probs[e] - truth_probs[e]) for e in matched_edges
        ) / len(matched_edges)
    else:
        mae = 0.0

    return f1, mae, f1_relaxed


def _text_similarity(a: str, b: str) -> float:
    """Compute text similarity using character-level + fuzzy word matching."""
    if not a or not b:
        return 0.0
    a_lower, b_lower = a.lower(), b.lower()
    # Character-level similarity
    char_sim = SequenceMatcher(None, a_lower, b_lower).ratio()
    # Fuzzy word matching: words match if they share a 4+ char prefix
    # (handles deliver/delivered/delivery, restaurant/restaurants, etc.)
    words_a = set(a_lower.split())
    words_b = set(b_lower.split())
    # Remove stop words for better signal
    stop = {"a", "an", "the", "to", "of", "in", "on", "at", "for", "and", "or", "is", "it", "my", "i", "with"}
    content_a = words_a - stop
    content_b = words_b - stop
    if not content_a or not content_b:
        return char_sim
    # Count fuzzy matches (prefix-based)
    matched = 0
    used_b: set[str] = set()
    for wa in content_a:
        for wb in content_b:
            if wb in used_b:
                continue
            if wa == wb or (len(wa) >= 4 and len(wb) >= 4 and
                           (wa[:4] == wb[:4])):
                matched += 1
                used_b.add(wb)
                break
    fuzzy_sim = matched / max(len(content_a), len(content_b))
    return max(char_sim, fuzzy_sim)
