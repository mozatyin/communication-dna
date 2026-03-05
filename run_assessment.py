"""Launch the Recursive Thinking Assessment server."""

import os
import sys


def main():
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn not installed. Run: pip install -e '.[assessment]'")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("Warning: ANTHROPIC_API_KEY not set. Scenario scoring will be disabled.")

    port = int(os.environ.get("PORT", "8000"))
    print(f"\n  Recursive Thinking Assessment")
    print(f"  http://localhost:{port}\n")

    uvicorn.run("assessment.app:app", host="0.0.0.0", port=port, reload=True)


if __name__ == "__main__":
    main()
