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

GRAPHS = {
    "career_change": make_graph(
        domain="career",
        nodes=[
            {"id": "int_001", "text": "change career to product design", "specificity": 0.5},
            {"id": "int_002", "text": "save 6 months of living expenses", "specificity": 0.7},
            {"id": "int_003", "text": "build a design portfolio", "specificity": 0.6},
            {"id": "int_004", "text": "take online design courses", "status": "completed", "specificity": 0.8},
            {"id": "int_005", "text": "apply to design jobs at startups", "specificity": 0.6},
        ],
        transitions=[
            {"from": "int_002", "to": "int_005", "rel": "enables", "prob": 0.8},
            {"from": "int_003", "to": "int_005", "rel": "enables", "prob": 0.9},
            {"from": "int_004", "to": "int_003", "rel": "next_step", "prob": 0.7},
        ],
        end_goal="int_001",
    ),
    "food_delivery": make_graph(
        domain="food",
        nodes=[
            {"id": "int_001", "text": "eat steak dinner at home", "specificity": 0.6},
            {"id": "int_002", "text": "order steak delivery via app", "specificity": 0.7},
            {"id": "int_003", "text": "find a good steak restaurant on delivery app", "specificity": 0.6},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_002", "to": "int_003", "rel": "decomposes_to", "prob": 0.7},
        ],
        end_goal="int_001",
    ),
    "relationship": make_graph(
        domain="relationship",
        nodes=[
            {"id": "int_001", "text": "repair relationship with partner after argument", "specificity": 0.4},
            {"id": "int_002", "text": "have an honest conversation about feelings", "specificity": 0.6},
            {"id": "int_003", "text": "give each other some space first", "specificity": 0.5},
            {"id": "int_004", "text": "plan a meaningful date together", "specificity": 0.6},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "alternative", "prob": 0.5},
            {"from": "int_001", "to": "int_003", "rel": "alternative", "prob": 0.4},
            {"from": "int_002", "to": "int_004", "rel": "next_step", "prob": 0.6},
        ],
        end_goal="int_001",
    ),
    "laptop_purchase": make_graph(
        domain="shopping",
        nodes=[
            {"id": "int_001", "text": "buy a new programming laptop within $1500 budget", "specificity": 0.6},
            {"id": "int_002", "text": "compare MacBook Pro vs ThinkPad X1", "specificity": 0.7},
            {"id": "int_003", "text": "check RAM and keyboard reviews", "specificity": 0.7},
            {"id": "int_004", "text": "visit store to try keyboards", "specificity": 0.8},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_002", "to": "int_003", "rel": "next_step", "prob": 0.7},
            {"from": "int_003", "to": "int_004", "rel": "next_step", "prob": 0.5},
        ],
        end_goal="int_001",
    ),
}

PROMPTS = [
    "Discuss your plans and goals with an advisor",
    "Talk about what you've been thinking about lately",
    "Explain your current situation and what you want to achieve",
]


def run_eval(api_key: str, version: str = "latest"):
    speaker = GraphSpeaker(api_key=api_key)
    detector = IntentionDetector(api_key=api_key)

    all_metrics = []
    results: dict[str, dict] = {}

    for graph_name, truth_graph in GRAPHS.items():
        print(f"\n{'='*60}")
        print(f"  Graph: {graph_name}")
        print(f"{'='*60}")

        # Generate dialogue
        print("  Generating dialogue...", end=" ", flush=True)
        prompt = PROMPTS[0]
        dialogue = speaker.generate(graph=truth_graph, prompt=prompt)
        print(f"done ({len(dialogue.split())} words)")

        # Detect
        print("  Detecting intentions...", end=" ", flush=True)
        predicted = detector.analyze(
            text=dialogue,
            speaker_id=f"eval_{graph_name}",
            speaker_label="Speaker",
            domain=truth_graph.nodes[0].domain,
            skip_expand=True,  # Compare Connect output directly against truth
        )
        print("done")

        # Compare
        metrics = compare_graphs(predicted, truth_graph)
        all_metrics.append(metrics)

        print(f"\n  Nodes: {metrics.matched_nodes}/{metrics.total_truth_nodes} matched "
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
