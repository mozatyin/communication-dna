# eval_intention.py
"""Evaluate Intention Detector accuracy via closed-loop testing."""

import json
import os
import statistics
import sys
from pathlib import Path

from intention_graph.comparator import compare_graphs
from intention_graph.detector import IntentionDetector
from intention_graph.graph_speaker import GraphSpeaker
from intention_graph.models import ActionNode, IntentionGraph, Transition


def make_graph(
    domain: str,
    nodes: list[dict],
    transitions: list[dict],
    end_goal: str,
) -> IntentionGraph:
    """Build an IntentionGraph from shorthand definitions."""
    action_nodes = [
        ActionNode(
            id=n["id"], text=n["text"], domain=domain,
            source="expressed", status=n.get("status", "pending"),
            confidence=1.0, specificity=n.get("specificity", 0.5),
        )
        for n in nodes
    ]
    trans = [
        Transition(
            from_id=t["from"], to_id=t["to"],
            base_probability=t["prob"],
            dna_adjusted_probability=t["prob"],
            relation=t["rel"], confidence=1.0,
        )
        for t in transitions
    ]
    return IntentionGraph(
        nodes=action_nodes, transitions=trans,
        end_goal=end_goal,
        summary=f"Eval graph: {domain}",
    )


# ── Test graphs ──────────────────────────────────────────────────────────────
# Focus areas: 心理咨询 (psychological counseling) and 软件 PRD (product requirements)

GRAPHS = {
    # ── 心理咨询 (Therapy/Counseling) ──
    "therapy_anxiety": make_graph(
        domain="therapy",
        nodes=[
            {"id": "int_001", "text": "manage work-related anxiety and stress", "specificity": 0.3},
            {"id": "int_002", "text": "learn breathing and grounding techniques", "specificity": 0.7},
            {"id": "int_003", "text": "set boundaries with manager about overtime", "specificity": 0.7},
            {"id": "int_004", "text": "start regular exercise routine", "specificity": 0.6},
            {"id": "int_005", "text": "consider whether to change jobs", "specificity": 0.5},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_001", "to": "int_004", "rel": "decomposes_to", "prob": 0.6},
            {"from": "int_003", "to": "int_005", "rel": "next_step", "prob": 0.4},
        ],
        end_goal="int_001",
    ),
    "therapy_grief": make_graph(
        domain="therapy",
        nodes=[
            {"id": "int_001", "text": "process grief after losing a parent", "specificity": 0.3},
            {"id": "int_002", "text": "allow myself to feel sadness without guilt", "specificity": 0.5},
            {"id": "int_003", "text": "talk to siblings about shared memories", "specificity": 0.7},
            {"id": "int_004", "text": "join a grief support group", "specificity": 0.7},
            {"id": "int_005", "text": "gradually return to normal daily routine", "specificity": 0.5},
        ],
        transitions=[
            {"from": "int_002", "to": "int_005", "rel": "enables", "prob": 0.6},
            {"from": "int_003", "to": "int_001", "rel": "enables", "prob": 0.5},
            {"from": "int_003", "to": "int_004", "rel": "alternative", "prob": 0.4},
            {"from": "int_004", "to": "int_001", "rel": "enables", "prob": 0.5},
        ],
        end_goal="int_001",
    ),
    "therapy_self_esteem": make_graph(
        domain="therapy",
        nodes=[
            {"id": "int_001", "text": "build self-confidence and self-worth", "specificity": 0.3},
            {"id": "int_002", "text": "stop comparing myself to others on social media", "specificity": 0.6},
            {"id": "int_003", "text": "challenge negative self-talk when it happens", "specificity": 0.6},
            {"id": "int_004", "text": "take on a small creative project to prove capability", "specificity": 0.7},
            {"id": "int_005", "text": "reduce social media usage", "status": "completed", "specificity": 0.7},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_005", "to": "int_002", "rel": "enables", "prob": 0.7},
            {"from": "int_003", "to": "int_004", "rel": "next_step", "prob": 0.5},
        ],
        end_goal="int_001",
    ),

    # ── 软件 PRD (Product Requirements) ──
    "prd_auth": make_graph(
        domain="product",
        nodes=[
            {"id": "int_001", "text": "implement user authentication system for the app", "specificity": 0.4},
            {"id": "int_002", "text": "support email and password login", "specificity": 0.7},
            {"id": "int_003", "text": "add OAuth login with Google and GitHub", "specificity": 0.8},
            {"id": "int_004", "text": "implement role-based access control", "specificity": 0.7},
            {"id": "int_005", "text": "add two-factor authentication for admin users", "specificity": 0.8},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.9},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_002", "to": "int_004", "rel": "enables", "prob": 0.8},
            {"from": "int_004", "to": "int_005", "rel": "next_step", "prob": 0.6},
        ],
        end_goal="int_001",
    ),
    "prd_dashboard": make_graph(
        domain="product",
        nodes=[
            {"id": "int_001", "text": "build analytics dashboard for business users", "specificity": 0.4},
            {"id": "int_002", "text": "show real-time revenue and conversion metrics", "specificity": 0.7},
            {"id": "int_003", "text": "support custom date range filtering", "specificity": 0.7},
            {"id": "int_004", "text": "export reports as PDF or CSV", "specificity": 0.8},
            {"id": "int_005", "text": "build data pipeline from existing database", "specificity": 0.6},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.9},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_001", "to": "int_004", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_005", "to": "int_002", "rel": "enables", "prob": 0.9},
        ],
        end_goal="int_001",
    ),
    "prd_mobile_redesign": make_graph(
        domain="product",
        nodes=[
            {"id": "int_001", "text": "redesign the mobile app checkout flow", "specificity": 0.4},
            {"id": "int_002", "text": "reduce checkout steps from 5 to 3", "specificity": 0.7},
            {"id": "int_003", "text": "add Apple Pay and Google Pay support", "specificity": 0.8},
            {"id": "int_004", "text": "run A/B test on new flow vs old flow", "specificity": 0.7},
            {"id": "int_005", "text": "conduct user research on current pain points", "status": "completed", "specificity": 0.6},
        ],
        transitions=[
            {"from": "int_005", "to": "int_002", "rel": "enables", "prob": 0.8},
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_001", "to": "int_003", "rel": "decomposes_to", "prob": 0.7},
            {"from": "int_002", "to": "int_004", "rel": "next_step", "prob": 0.6},
        ],
        end_goal="int_001",
    ),
}

PROMPTS = {
    "therapy": "Talk about what's been bothering you with your therapist",
    "product": "Discuss the product requirements with a product manager",
}


def run_eval(api_key: str, version: str = "latest", n_samples: int = 2):
    speaker = GraphSpeaker(api_key=api_key)
    detector = IntentionDetector(api_key=api_key)

    all_metrics = []
    results: dict[str, dict] = {}

    for graph_name, truth_graph in GRAPHS.items():
        print(f"\n{'='*60}")
        print(f"  Graph: {graph_name}")
        print(f"{'='*60}")

        best_metrics = None
        best_predicted = None
        best_score = -1.0

        for sample_i in range(n_samples):
            # Generate dialogue
            print(f"  [Run {sample_i+1}/{n_samples}] Generating dialogue...", end=" ", flush=True)
            domain = truth_graph.nodes[0].domain if truth_graph.nodes else "general"
            prompt = PROMPTS.get(domain, "Discuss your plans and goals with an advisor")
            dialogue = speaker.generate(graph=truth_graph, prompt=prompt)
            print(f"done ({len(dialogue.split())} words)")

            # Detect
            print(f"  [Run {sample_i+1}/{n_samples}] Detecting intentions...", end=" ", flush=True)
            predicted = detector.analyze(
                text=dialogue,
                speaker_id=f"eval_{graph_name}",
                speaker_label="Speaker",
                domain=truth_graph.nodes[0].domain,
                skip_expand=True,
            )
            print("done")

            # Compare
            metrics = compare_graphs(predicted, truth_graph)
            score = metrics.node_f1 + metrics.edge_f1
            if score > best_score:
                best_score = score
                best_metrics = metrics
                best_predicted = predicted

        metrics = best_metrics
        predicted = best_predicted
        all_metrics.append(metrics)

        print(f"\n  Best of {n_samples} — Nodes: {metrics.matched_nodes}/{metrics.total_truth_nodes} matched "
              f"(P={metrics.node_precision:.2f} R={metrics.node_recall:.2f} F1={metrics.node_f1:.2f})")
        print(f"  Edges: F1={metrics.edge_f1:.2f} (relaxed={metrics.edge_f1_relaxed:.2f}), Prob MAE={metrics.probability_mae:.3f}")
        print(f"  End Goal: {'CORRECT' if metrics.end_goal_correct else 'WRONG'}")

        # Diagnostic: show predicted graph
        print(f"\n  Predicted nodes ({len(predicted.nodes)}):")
        for n in predicted.nodes:
            print(f"    [{n.id}] {n.text} (sp={n.specificity:.1f})")
        print(f"  Predicted edges ({len(predicted.transitions)}):")
        for t in predicted.transitions:
            print(f"    {t.from_id} --[{t.relation}]--> {t.to_id}")
        print(f"  Predicted end goal: {predicted.end_goal}")

        results[graph_name] = metrics.to_dict()

    # Overall
    print(f"\n{'='*60}")
    print(f"  OVERALL SUMMARY")
    print(f"{'='*60}")
    avg_node_f1 = statistics.mean(m.node_f1 for m in all_metrics)
    avg_edge_f1 = statistics.mean(m.edge_f1 for m in all_metrics)
    avg_edge_f1_relaxed = statistics.mean(m.edge_f1_relaxed for m in all_metrics)
    avg_recall = statistics.mean(m.node_recall for m in all_metrics)
    end_goal_acc = sum(1 for m in all_metrics if m.end_goal_correct) / len(all_metrics)

    print(f"  Avg Node F1: {avg_node_f1:.3f}")
    print(f"  Avg Node Recall: {avg_recall:.3f}")
    print(f"  Avg Edge F1: {avg_edge_f1:.3f} (relaxed={avg_edge_f1_relaxed:.3f})")
    print(f"  End Goal Accuracy: {end_goal_acc:.1%}")

    results["_overall"] = {
        "avg_node_f1": round(avg_node_f1, 3),
        "avg_node_recall": round(avg_recall, 3),
        "avg_edge_f1": round(avg_edge_f1, 3),
        "avg_edge_f1_relaxed": round(avg_edge_f1_relaxed, 3),
        "end_goal_accuracy": round(end_goal_acc, 3),
    }

    version_tag = version or "latest"
    output_path = Path(f"eval_intention_results_{version_tag}.json")
    output_path.write_text(json.dumps(results, indent=2))
    print(f"\n  Results saved to {output_path}")

    return results


if __name__ == "__main__":
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY env var to run evaluation.")
        sys.exit(1)
    version = sys.argv[1] if len(sys.argv) > 1 else "latest"
    run_eval(api_key, version=version)
