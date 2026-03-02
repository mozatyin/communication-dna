"""
End-to-end demo: Analyze a conversation → Build profile → Mimic style → Validate round-trip.

Usage:
    ANTHROPIC_API_KEY=<key> python examples/analyze_and_mimic.py
"""

import os
import sys
from pathlib import Path

# Ensure the package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from communication_dna.detector import Detector
from communication_dna.speaker import Speaker
from communication_dna.matcher import StyleMatcher
from communication_dna.storage import save_profile, load_profile


SAMPLE_CONVERSATION = """
A: So what did you think of the presentation today?
B: ugh honestly? it was kind of a mess lol. like the data was solid but the delivery... yikes. I mean I get it, public speaking is hard, but maybe don't read directly from the slides you know?? 😅
A: Ha, fair point. Any parts you liked?
B: ok yeah actually the market analysis section was fire 🔥 whoever did that research really knew their stuff. like they actually went and talked to real customers instead of just making stuff up. respect.
A: That was Sarah's team.
B: oh wow ok yeah sarah's team is legit. I kinda wish the whole presentation had that energy tbh. like less corporate-speak more actual insights?? idk maybe I'm being too harsh but I just... I really care about us getting this right and sometimes it feels like we're going through the motions
"""


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    detector = Detector(api_key=api_key)
    speaker = Speaker(api_key=api_key)
    matcher = StyleMatcher(api_key=api_key)

    # Step 1: Detect
    print("=" * 60)
    print("STEP 1: Detecting communication style for Speaker B...")
    print("=" * 60)
    profile = detector.analyze(text=SAMPLE_CONVERSATION, speaker_id="speaker_B", speaker_label="B")

    print(f"\nDetected {len(profile.features)} features:")
    for f in sorted(profile.features, key=lambda x: x.confidence, reverse=True)[:10]:
        print(f"  [{f.dimension}] {f.name}: {f.value:.2f} (confidence: {f.confidence:.2f})")

    # Step 2: Save
    output_dir = Path("profiles")
    save_profile(profile, output_dir / "speaker_B.json")
    print(f"\nProfile saved to {output_dir / 'speaker_B.json'}")

    # Step 3: Mimic
    print("\n" + "=" * 60)
    print("STEP 2: Generating text in Speaker B's style...")
    print("=" * 60)
    content = "Give your opinion on remote work vs. office work"
    mimicked = speaker.generate(profile=profile, content=content)
    print(f"\nGenerated (as Speaker B):\n{mimicked}")

    # Step 4: Style Matcher
    print("\n" + "=" * 60)
    print("STEP 3: Style Matcher — guiding a deeper conversation...")
    print("=" * 60)
    conversation = [
        {"role": "user", "text": "I've been thinking about whether I should stay at this company or try something new."},
    ]
    response = matcher.respond(counterpart=profile, conversation=conversation, goal="understand_deeper")
    print(f"\nAssessed depth: L{response.assessed_depth}")
    print(f"Target depth: L{response.target_depth}")
    print(f"Strategy: {response.strategy_used}")
    print(f"Response:\n{response.response_text}")


if __name__ == "__main__":
    main()
