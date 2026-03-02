"""
Complete feature catalog across 13 dimensions.

Each entry defines a feature that an LLM can detect from conversation text
and reproduce in generation. The catalog is the source of truth for the
feature vector space.
"""

ALL_DIMENSIONS: dict[str, str] = {
    "LEX": "Lexical — Word choice patterns",
    "SYN": "Syntactic — Sentence structure",
    "DIS": "Discourse — Paragraph and conversation organization",
    "PRA": "Pragmatic — Using language to achieve goals",
    "AFF": "Affective — Emotional expression",
    "INT": "Interactional — Conversational dynamics",
    "IDN": "Identity — Identity markers in language",
    "MET": "Metalingual — Language-about-language habits",
    "TMP": "Temporal — Style dynamics over time",
    "ERR": "Error Patterns — Characteristic deviations",
    "CSW": "Code-switching — Register and language shifting",
    "PTX": "Para-textual — Non-verbal text signals",
    "DSC": "Disclosure — Self-revelation patterns",
}

FEATURE_CATALOG: list[dict] = [
    # === LEX: Lexical ===
    {
        "dimension": "LEX",
        "name": "formality",
        "description": "Degree of formal vs. informal word choice",
        "detection_hint": "Look for formal markers (furthermore, nevertheless, regarding) vs. informal (gonna, kinda, stuff)",
        "value_anchors": {"0.0": "Extremely casual/slang-heavy", "1.0": "Extremely formal/academic"},
    },
    {
        "dimension": "LEX",
        "name": "vocabulary_richness",
        "description": "Diversity and sophistication of vocabulary (type-token ratio, rare word usage)",
        "detection_hint": "Count unique words vs. total words; note unusual or sophisticated word choices",
        "value_anchors": {"0.0": "Very limited/repetitive vocabulary", "1.0": "Highly diverse/sophisticated vocabulary"},
    },
    {
        "dimension": "LEX",
        "name": "jargon_density",
        "description": "Frequency of domain-specific or technical terminology",
        "detection_hint": "Identify words that require specialized knowledge to understand",
        "value_anchors": {"0.0": "No jargon, plain language only", "1.0": "Heavily jargon-laden"},
    },
    {
        "dimension": "LEX",
        "name": "colloquialism",
        "description": "Use of informal expressions, slang, and spoken-language patterns in text",
        "detection_hint": "Look for contractions, filler words (like, you know), slang terms",
        "value_anchors": {"0.0": "No colloquial language", "1.0": "Predominantly colloquial"},
    },
    {
        "dimension": "LEX",
        "name": "hedging_frequency",
        "description": "Use of hedge words that soften assertions (maybe, perhaps, sort of, I think)",
        "detection_hint": "Count hedging markers: maybe, perhaps, sort of, kind of, I think, probably, might",
        "value_anchors": {"0.0": "No hedging, all assertions definitive", "1.0": "Nearly every statement hedged"},
    },

    # === SYN: Syntactic ===
    {
        "dimension": "SYN",
        "name": "sentence_length",
        "description": "Average sentence length in words",
        "detection_hint": "Measure average words per sentence across the sample",
        "value_anchors": {"0.0": "Very short (avg <8 words)", "1.0": "Very long (avg >30 words)"},
    },
    {
        "dimension": "SYN",
        "name": "sentence_complexity",
        "description": "Syntactic complexity — subordinate clauses, nested structures",
        "detection_hint": "Count subordinate clauses, relative clauses, and nesting depth per sentence",
        "value_anchors": {"0.0": "Simple sentences only", "1.0": "Multi-layered complex sentences"},
    },
    {
        "dimension": "SYN",
        "name": "passive_voice_preference",
        "description": "Tendency toward passive vs. active voice constructions",
        "detection_hint": "Identify passive constructions (was done, has been shown, is considered)",
        "value_anchors": {"0.0": "Exclusively active voice", "1.0": "Predominantly passive voice"},
    },
    {
        "dimension": "SYN",
        "name": "ellipsis_frequency",
        "description": "How often sentences omit grammatically expected elements",
        "detection_hint": "Look for sentence fragments, dropped subjects, implied verbs",
        "value_anchors": {"0.0": "All sentences grammatically complete", "1.0": "Frequent elliptical constructions"},
    },

    # === DIS: Discourse ===
    {
        "dimension": "DIS",
        "name": "argumentation_style",
        "description": "Inductive (examples → conclusion) vs. deductive (principle → examples) reasoning",
        "detection_hint": "Does the speaker lead with a conclusion then support it, or build from examples to a point?",
        "value_anchors": {"0.0": "Purely inductive", "1.0": "Purely deductive"},
    },
    {
        "dimension": "DIS",
        "name": "example_frequency",
        "description": "How often concrete examples or anecdotes are used to support points",
        "detection_hint": "Count instances of 'for example', 'like when', anecdotes, specific cases",
        "value_anchors": {"0.0": "Never uses examples", "1.0": "Every point backed by examples"},
    },
    {
        "dimension": "DIS",
        "name": "topic_transition_style",
        "description": "How abruptly or smoothly the speaker shifts between topics",
        "detection_hint": "Look for explicit transitions (speaking of, anyway, by the way) vs. abrupt jumps",
        "value_anchors": {"0.0": "Abrupt jumps, no transitions", "1.0": "Always smooth, explicit transitions"},
    },
    {
        "dimension": "DIS",
        "name": "repetition_for_emphasis",
        "description": "Tendency to repeat key phrases or ideas for emphasis",
        "detection_hint": "Identify repeated phrases, restated ideas, callback references to earlier points",
        "value_anchors": {"0.0": "Never repeats", "1.0": "Frequently restates key ideas"},
    },

    # === PRA: Pragmatic ===
    {
        "dimension": "PRA",
        "name": "directness",
        "description": "How directly requests, opinions, and disagreements are expressed",
        "detection_hint": "Direct: 'I disagree', 'Do X'. Indirect: 'I wonder if maybe...', 'Have you considered...'",
        "value_anchors": {"0.0": "Extremely indirect/circuitous", "1.0": "Extremely blunt/direct"},
    },
    {
        "dimension": "PRA",
        "name": "politeness_strategy",
        "description": "Use of face-saving strategies (softeners, apologies, honorifics)",
        "detection_hint": "Look for please, sorry, would you mind, I appreciate, with respect",
        "value_anchors": {"0.0": "No politeness markers", "1.0": "Heavy politeness marking"},
    },
    {
        "dimension": "PRA",
        "name": "humor_frequency",
        "description": "How often humor, wit, or playfulness appears in communication",
        "detection_hint": "Identify jokes, wordplay, ironic observations, playful exaggeration",
        "value_anchors": {"0.0": "Never uses humor", "1.0": "Humor in nearly every exchange"},
    },
    {
        "dimension": "PRA",
        "name": "irony_frequency",
        "description": "Use of irony, sarcasm, or saying the opposite of what is meant",
        "detection_hint": "Look for statements where intended meaning contradicts literal meaning",
        "value_anchors": {"0.0": "Always literal", "1.0": "Frequently ironic/sarcastic"},
    },
    {
        "dimension": "PRA",
        "name": "rhetorical_question_usage",
        "description": "Frequency of questions asked for effect rather than information",
        "detection_hint": "Identify questions where the speaker doesn't expect/want an answer",
        "value_anchors": {"0.0": "Never uses rhetorical questions", "1.0": "Frequent rhetorical questions"},
    },

    # === AFF: Affective ===
    {
        "dimension": "AFF",
        "name": "emotion_word_density",
        "description": "Frequency of explicit emotion words (happy, frustrated, excited, worried)",
        "detection_hint": "Count emotion-laden words and expressions per unit of text",
        "value_anchors": {"0.0": "No emotion words used", "1.0": "Densely emotional language"},
    },
    {
        "dimension": "AFF",
        "name": "emotional_polarity_balance",
        "description": "Ratio of positive to negative emotional expressions",
        "detection_hint": "Classify emotion words as positive or negative, compute ratio",
        "value_anchors": {"0.0": "Overwhelmingly negative", "1.0": "Overwhelmingly positive"},
    },
    {
        "dimension": "AFF",
        "name": "emotional_volatility",
        "description": "How rapidly emotional tone shifts within a conversation",
        "detection_hint": "Track emotional tone per turn/paragraph, measure variance",
        "value_anchors": {"0.0": "Completely stable emotional tone", "1.0": "Rapid emotional swings"},
    },
    {
        "dimension": "AFF",
        "name": "empathy_expression",
        "description": "Frequency and depth of empathetic responses to others' emotions",
        "detection_hint": "Look for validation, perspective-taking, emotional mirroring phrases",
        "value_anchors": {"0.0": "No empathy expression", "1.0": "Consistently deep empathy"},
    },

    # === INT: Interactional ===
    {
        "dimension": "INT",
        "name": "question_frequency",
        "description": "How often the speaker asks questions in conversation",
        "detection_hint": "Count questions (explicit ? and implicit question forms) per turn",
        "value_anchors": {"0.0": "Never asks questions", "1.0": "Primarily asks questions"},
    },
    {
        "dimension": "INT",
        "name": "turn_length",
        "description": "Typical length of a single conversational turn",
        "detection_hint": "Measure average words/sentences per turn",
        "value_anchors": {"0.0": "Very brief (1-2 sentences)", "1.0": "Very long (multi-paragraph monologue)"},
    },
    {
        "dimension": "INT",
        "name": "feedback_signal_frequency",
        "description": "Use of backchannel responses (yeah, mm, right, I see, got it)",
        "detection_hint": "Count minimal response tokens that signal listening/acknowledgment",
        "value_anchors": {"0.0": "Never uses feedback signals", "1.0": "Very frequent backchanneling"},
    },
    {
        "dimension": "INT",
        "name": "response_elaboration",
        "description": "Tendency to elaborate beyond what was asked vs. minimal responses",
        "detection_hint": "Compare response length/content to what the question required",
        "value_anchors": {"0.0": "Minimal/exact answers only", "1.0": "Always elaborates extensively"},
    },

    # === IDN: Identity ===
    {
        "dimension": "IDN",
        "name": "dialect_markers",
        "description": "Presence of regional or social dialect features in text",
        "detection_hint": "Look for non-standard spellings, regional expressions, dialectal grammar",
        "value_anchors": {"0.0": "Standard/neutral language", "1.0": "Strong dialect presence"},
    },
    {
        "dimension": "IDN",
        "name": "generational_vocabulary",
        "description": "Use of age/generation-specific terms and references",
        "detection_hint": "Identify slang, cultural references, or expressions tied to a generation",
        "value_anchors": {"0.0": "Age-neutral vocabulary", "1.0": "Strongly generation-marked"},
    },
    {
        "dimension": "IDN",
        "name": "cultural_reference_density",
        "description": "Frequency of references to cultural artifacts (media, memes, historical events, literature)",
        "detection_hint": "Count references to movies, books, memes, public figures, events",
        "value_anchors": {"0.0": "No cultural references", "1.0": "Densely referential"},
    },

    # === MET: Metalingual ===
    {
        "dimension": "MET",
        "name": "self_correction_frequency",
        "description": "How often the speaker corrects or amends their own statements",
        "detection_hint": "Look for 'I mean', 'actually', 'well, let me rephrase', corrections",
        "value_anchors": {"0.0": "Never self-corrects", "1.0": "Frequently revises statements"},
    },
    {
        "dimension": "MET",
        "name": "definition_tendency",
        "description": "Tendency to define terms or explain concepts proactively",
        "detection_hint": "Look for 'by X I mean', 'that is to say', 'in other words', definitional clauses",
        "value_anchors": {"0.0": "Assumes shared understanding", "1.0": "Defines everything explicitly"},
    },
    {
        "dimension": "MET",
        "name": "metacommentary",
        "description": "Commenting on the conversation itself or one's own communication",
        "detection_hint": "Look for 'I'm going on a tangent', 'to get back to the point', 'I realize I'm being vague'",
        "value_anchors": {"0.0": "No metacommentary", "1.0": "Frequent self-aware commentary"},
    },

    # === TMP: Temporal ===
    {
        "dimension": "TMP",
        "name": "warmup_pattern",
        "description": "How communication style shifts from start to middle of a conversation",
        "detection_hint": "Compare style features in first 3 turns vs. turns 10+. Measure the delta.",
        "value_anchors": {"0.0": "No warmup, immediately at full expression", "1.0": "Long warmup, style shifts dramatically"},
    },
    {
        "dimension": "TMP",
        "name": "style_consistency",
        "description": "How stable the communication style remains across a conversation",
        "detection_hint": "Measure variance of key features (formality, sentence length) across turns",
        "value_anchors": {"0.0": "Highly variable style", "1.0": "Extremely consistent"},
    },
    {
        "dimension": "TMP",
        "name": "adaptation_speed",
        "description": "How quickly the speaker adjusts style to match conversation partner or context",
        "detection_hint": "Measure how many turns it takes for style features to shift when context changes",
        "value_anchors": {"0.0": "Does not adapt", "1.0": "Adapts almost immediately"},
    },

    # === ERR: Error Patterns ===
    {
        "dimension": "ERR",
        "name": "typo_frequency",
        "description": "Rate of typographical errors in text",
        "detection_hint": "Count obvious typos, misspellings, transposed letters",
        "value_anchors": {"0.0": "Zero typos", "1.0": "Frequent typos"},
    },
    {
        "dimension": "ERR",
        "name": "grammar_deviation",
        "description": "Frequency of non-standard grammar (intentional or habitual)",
        "detection_hint": "Identify subject-verb disagreement, run-ons, fragments used as style",
        "value_anchors": {"0.0": "Textbook grammar", "1.0": "Frequent grammatical deviations"},
    },
    {
        "dimension": "ERR",
        "name": "punctuation_irregularity",
        "description": "Non-standard punctuation usage (multiple exclamation marks, no periods, etc.)",
        "detection_hint": "Look for !!! or ???, comma splices, missing periods, excessive ellipses...",
        "value_anchors": {"0.0": "Standard punctuation", "1.0": "Highly irregular punctuation"},
    },

    # === CSW: Code-switching ===
    {
        "dimension": "CSW",
        "name": "register_shift_frequency",
        "description": "How often the speaker shifts between formal and informal registers",
        "detection_hint": "Track formality level per sentence and count transitions above threshold",
        "value_anchors": {"0.0": "Maintains single register", "1.0": "Constantly shifting registers"},
    },
    {
        "dimension": "CSW",
        "name": "language_mixing",
        "description": "Mixing words or phrases from other languages into primary language",
        "detection_hint": "Identify foreign words, phrases, or code-switching between languages",
        "value_anchors": {"0.0": "Monolingual", "1.0": "Heavy multilingual mixing"},
    },
    {
        "dimension": "CSW",
        "name": "context_sensitivity",
        "description": "How strongly style shifts based on audience/context",
        "detection_hint": "Compare style across different conversation contexts for same speaker",
        "value_anchors": {"0.0": "Same style regardless of context", "1.0": "Dramatically different per context"},
    },

    # === PTX: Para-textual ===
    {
        "dimension": "PTX",
        "name": "emoji_usage",
        "description": "Frequency and diversity of emoji in text communication",
        "detection_hint": "Count emoji per message, note variety vs. repetition of specific emoji",
        "value_anchors": {"0.0": "Never uses emoji", "1.0": "Emoji in nearly every message"},
    },
    {
        "dimension": "PTX",
        "name": "formatting_habits",
        "description": "Use of bold, italics, lists, headers, code blocks, etc.",
        "detection_hint": "Identify markdown/formatting markers, structured layouts, visual organization",
        "value_anchors": {"0.0": "Plain text only", "1.0": "Heavy formatting/structure"},
    },
    {
        "dimension": "PTX",
        "name": "expressive_punctuation",
        "description": "Using punctuation for emotional expression (... for trailing off, !! for excitement)",
        "detection_hint": "Count ellipses, multiple exclamation/question marks, em-dashes for dramatic pause",
        "value_anchors": {"0.0": "Punctuation purely grammatical", "1.0": "Punctuation heavily expressive"},
    },

    # === DSC: Disclosure ===
    {
        "dimension": "DSC",
        "name": "disclosure_depth",
        "description": "How deep self-revelations go (facts → opinions → feelings → beliefs → insights)",
        "detection_hint": "Classify statements: L0 pleasantry, L1 fact, L2 opinion, L3 emotion, L4 belief, L5 insight",
        "value_anchors": {"0.0": "Only surface pleasantries", "1.0": "Reaches deep self-insight"},
    },
    {
        "dimension": "DSC",
        "name": "vulnerability_willingness",
        "description": "Willingness to express uncertainty, weakness, or emotional vulnerability",
        "detection_hint": "Look for admissions of not knowing, expressions of fear/doubt, asking for help",
        "value_anchors": {"0.0": "Never shows vulnerability", "1.0": "Openly vulnerable"},
    },
    {
        "dimension": "DSC",
        "name": "reciprocity_sensitivity",
        "description": "How much disclosure increases when the other party also discloses",
        "detection_hint": "Compare disclosure depth before and after the partner shares something personal",
        "value_anchors": {"0.0": "Disclosure unaffected by partner", "1.0": "Strongly reciprocal"},
    },
]


def get_features_for_dimension(dimension_code: str) -> list[dict]:
    """Return all catalog features for a given dimension code."""
    return [f for f in FEATURE_CATALOG if f["dimension"] == dimension_code]
