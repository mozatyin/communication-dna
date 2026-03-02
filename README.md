# Communication DNA

A system for modeling human communication style as a feature vector. Detects, reproduces, and leverages individual communication fingerprints.

## Quick Start

```bash
pip install -e ".[dev]"
export ANTHROPIC_API_KEY=<your-key>
```

### Detect a speaker's style

```python
from communication_dna.detector import Detector

detector = Detector(api_key="...")
profile = detector.analyze(
    text="<conversation transcript>",
    speaker_id="alice",
    speaker_label="Alice",
)
```

### Mimic a style

```python
from communication_dna.speaker import Speaker

speaker = Speaker(api_key="...")
output = speaker.generate(
    profile=profile,
    content="Explain quantum computing",
)
```

### Guide a deeper conversation

```python
from communication_dna.matcher import StyleMatcher

matcher = StyleMatcher(api_key="...")
result = matcher.respond(
    counterpart=profile,
    conversation=[{"role": "user", "text": "I've been stressed lately."}],
    goal="understand_deeper",
)
```

## Running Tests

```bash
# Unit tests (no API key needed)
pytest tests/test_models.py tests/test_catalog.py tests/test_storage.py -v

# Integration tests (API key required)
ANTHROPIC_API_KEY=<key> pytest tests/ -v --timeout=120
```
