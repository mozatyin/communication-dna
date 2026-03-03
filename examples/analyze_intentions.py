# examples/analyze_intentions.py
"""Example: Extract an intention graph from a conversation."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from intention_graph.detector import IntentionDetector
from intention_graph.storage import save_graph

api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("Error: set ANTHROPIC_API_KEY environment variable")
    sys.exit(1)

SAMPLE_CONVERSATION = """\
User: I've been really stressed out about work lately. I think I need a complete change.
Coach: What kind of change are you thinking about?
User: Well, I've always been passionate about cooking. I took a pastry course last year \
and everyone said I was really talented. I'm thinking about opening a small bakery.
Coach: That's a big step. Have you thought about the practical side?
User: Kind of. I know I need to save up at least $50,000. Right now I have about $20,000. \
I also need to find a good location — maybe somewhere near the university district where \
there's lots of foot traffic.
Coach: What about the business side — permits, suppliers?
User: That's what scares me honestly. I don't know anything about running a business. \
Maybe I should take a small business course first, or find a mentor who's done it before.
"""

# Create detector
detector = IntentionDetector(api_key=api_key)

# Analyze conversation
print("Analyzing conversation for intentions...\n")
graph = detector.analyze(
    text=SAMPLE_CONVERSATION,
    speaker_id="aspiring_baker",
    speaker_label="User",
)

# Display results
print(f"Summary: {graph.summary}\n")
print(f"End Goal: {graph.end_goal}\n")

print("=== Intention Nodes ===")
for node in graph.nodes:
    status = " [DONE]" if node.status == "completed" else ""
    source_tag = f" ({node.source})" if node.source == "inferred" else ""
    print(f"  [{node.id}] {node.text}{status}{source_tag}")
    print(f"         confidence={node.confidence:.2f}  specificity={node.specificity:.2f}")

print(f"\n=== Transitions ===")
node_map = {n.id: n.text for n in graph.nodes}
for t in graph.transitions:
    print(f"  {node_map.get(t.from_id, t.from_id)}")
    print(f"    --[{t.relation}, p={t.base_probability:.2f}]-->")
    print(f"    {node_map.get(t.to_id, t.to_id)}")

if graph.ambiguities:
    print(f"\n=== Ambiguities ({len(graph.ambiguities)}) ===")
    for amb in graph.ambiguities:
        print(f"  Node: {node_map.get(amb.node_id, amb.node_id)}")
        print(f"  Question: {amb.incisive_question}")
        print(f"  Info Gain: {amb.information_gain:.2f}")
        print()

# Save
output_dir = Path("output")
save_graph(graph, output_dir / "bakery_intentions.json")
print(f"\nGraph saved to {output_dir / 'bakery_intentions.json'}")
