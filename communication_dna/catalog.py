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
        "detection_hint": (
            "Count formal markers (furthermore, nevertheless, regarding, consequently, henceforth) "
            "vs. informal markers (gonna, kinda, stuff, cool, lol, yeah). "
            "Also note contractions (don't vs do not) and register of address."
        ),
        "value_anchors": {
            "0.0": "Extremely casual/slang-heavy; contractions everywhere, slang dominant",
            "0.25": "Mostly informal; frequent contractions and casual words, rare formal terms",
            "0.50": "Mixed register; some contractions and casual words alongside standard vocabulary",
            "0.75": "Mostly formal; rare contractions, professional vocabulary, few casual terms",
            "1.0": "Extremely formal/academic; no contractions, Latinate vocabulary, elevated register",
        },
        "correlation_hints": "Negatively correlated with colloquialism; positively correlated with sentence_complexity and passive_voice_preference",
    },
    {
        "dimension": "LEX",
        "name": "vocabulary_richness",
        "description": "Diversity and sophistication of vocabulary (type-token ratio, rare word usage)",
        "detection_hint": "Count unique words vs. total words; note unusual or sophisticated word choices",
        "value_anchors": {
            "0.0": "Very limited/repetitive vocabulary; same common words reused",
            "0.25": "Below average; mostly common words with occasional variety",
            "0.50": "Average diversity; standard vocabulary with some less-common terms",
            "0.75": "Rich vocabulary; frequent use of precise, less-common words",
            "1.0": "Highly diverse/sophisticated vocabulary; rare words, precise terminology throughout",
        },
        "correlation_hints": "Positively correlated with formality and sentence_complexity",
    },
    {
        "dimension": "LEX",
        "name": "jargon_density",
        "description": "Frequency of domain-specific or technical terminology",
        "detection_hint": "Identify words that require specialized knowledge to understand",
        "value_anchors": {
            "0.0": "No jargon, plain language only",
            "0.25": "Occasional technical term, mostly explained inline",
            "0.50": "Regular use of domain terms; assumes some background knowledge",
            "0.75": "Heavy technical vocabulary; most sentences contain specialized terms",
            "1.0": "Heavily jargon-laden; impenetrable without domain expertise",
        },
        "correlation_hints": "Positively correlated with definition_tendency and formality",
    },
    {
        "dimension": "LEX",
        "name": "colloquialism",
        "description": "Use of informal expressions, slang, and spoken-language patterns in text",
        "detection_hint": "Look for contractions, filler words (like, you know), slang terms",
        "value_anchors": {
            "0.0": "No colloquial language; fully standard written English",
            "0.25": "Light colloquial touches; a few contractions or casual phrases",
            "0.50": "Moderate; mix of standard and informal expressions",
            "0.75": "Predominantly informal; frequent slang and spoken-language patterns",
            "1.0": "Pervasively colloquial; reads like transcribed casual speech",
        },
        "correlation_hints": "Negatively correlated with formality; positively correlated with ellipsis_frequency and emoji_usage",
    },
    {
        "dimension": "LEX",
        "name": "hedging_frequency",
        "description": "Use of hedge words that soften assertions (maybe, perhaps, sort of, I think)",
        "detection_hint": "Count hedging markers: maybe, perhaps, sort of, kind of, I think, probably, might, I guess, arguably, in a way",
        "value_anchors": {
            "0.0": "No hedging, all assertions definitive",
            "0.25": "Rare hedging; one or two hedge words across the whole text",
            "0.50": "Moderate; hedges appear in roughly half of opinionated statements",
            "0.75": "Frequent; most opinions prefaced or softened with hedges",
            "1.0": "Nearly every statement hedged; very few definitive assertions",
        },
        "correlation_hints": "Negatively correlated with directness; positively correlated with politeness_strategy",
    },

    # === SYN: Syntactic ===
    {
        "dimension": "SYN",
        "name": "sentence_length",
        "description": "Average sentence length in words",
        "detection_hint": "Measure average words per sentence across the sample",
        "value_anchors": {
            "0.0": "Very short (avg <8 words); fragments and terse statements",
            "0.25": "Short (avg 8-14 words); concise, punchy sentences",
            "0.50": "Medium (avg 15-20 words); standard conversational length",
            "0.75": "Long (avg 21-30 words); elaborate, detailed sentences",
            "1.0": "Very long (avg >30 words); complex multi-clause constructions",
        },
        "correlation_hints": "Positively correlated with sentence_complexity and formality; negatively correlated with ellipsis_frequency",
    },
    {
        "dimension": "SYN",
        "name": "sentence_complexity",
        "description": "Syntactic complexity — subordinate clauses, nested structures",
        "detection_hint": "Count subordinate clauses, relative clauses, and nesting depth per sentence",
        "value_anchors": {
            "0.0": "Simple sentences only; no subordination",
            "0.25": "Mostly simple; occasional compound sentence",
            "0.50": "Mix of simple and complex; some subordinate clauses",
            "0.75": "Frequently complex; multiple clauses per sentence common",
            "1.0": "Multi-layered complex sentences; deep nesting throughout",
        },
        "correlation_hints": "Positively correlated with sentence_length and formality",
    },
    {
        "dimension": "SYN",
        "name": "passive_voice_preference",
        "description": "Tendency toward passive vs. active voice constructions",
        "detection_hint": "Identify passive constructions (was done, has been shown, is considered)",
        "value_anchors": {
            "0.0": "Exclusively active voice",
            "0.25": "Mostly active; occasional passive for variety",
            "0.50": "Balanced mix of active and passive",
            "0.75": "Frequently passive; passive is the default construction",
            "1.0": "Predominantly passive voice throughout",
        },
        "correlation_hints": "Positively correlated with formality",
    },
    {
        "dimension": "SYN",
        "name": "ellipsis_frequency",
        "description": "How often sentences omit grammatically expected elements",
        "detection_hint": "Look for sentence fragments, dropped subjects, implied verbs",
        "value_anchors": {
            "0.0": "All sentences grammatically complete",
            "0.25": "Rare fragments; almost always complete sentences",
            "0.50": "Moderate; some fragments mixed with complete sentences",
            "0.75": "Frequent fragments; many sentences lack subject or verb",
            "1.0": "Pervasive ellipsis; most utterances are fragments",
        },
        "correlation_hints": "Negatively correlated with sentence_length and formality; positively correlated with colloquialism",
    },

    # === DIS: Discourse ===
    {
        "dimension": "DIS",
        "name": "argumentation_style",
        "description": "Inductive (examples → conclusion) vs. deductive (principle → examples) reasoning",
        "detection_hint": "Does the speaker lead with a conclusion then support it, or build from examples to a point?",
        "value_anchors": {
            "0.0": "Purely inductive; always examples first, conclusion last",
            "0.25": "Mostly inductive; typically leads with examples",
            "0.50": "Mixed; uses both inductive and deductive approaches",
            "0.75": "Mostly deductive; states thesis first, then evidence",
            "1.0": "Purely deductive; always principle first, examples follow",
        },
        "correlation_hints": "Positively correlated with formality when deductive",
    },
    {
        "dimension": "DIS",
        "name": "example_frequency",
        "description": "How often concrete examples or anecdotes are used to support points",
        "detection_hint": "Count instances of 'for example', 'like when', anecdotes, specific cases",
        "value_anchors": {
            "0.0": "Never uses examples; all abstract claims",
            "0.25": "Rare; one example across many paragraphs",
            "0.50": "Moderate; roughly half of points include an example",
            "0.75": "Frequent; most points illustrated with examples or stories",
            "1.0": "Every point backed by concrete examples or anecdotes",
        },
        "correlation_hints": "Positively correlated with response_elaboration and turn_length",
    },
    {
        "dimension": "DIS",
        "name": "topic_transition_style",
        "description": "How abruptly or smoothly the speaker shifts between topics",
        "detection_hint": "Look for explicit transitions (speaking of, anyway, by the way) vs. abrupt jumps",
        "value_anchors": {
            "0.0": "Abrupt jumps, no transitions",
            "0.25": "Mostly abrupt; occasional implicit bridge",
            "0.50": "Mixed; some transitions explicit, some abrupt",
            "0.75": "Mostly smooth; explicit transition phrases common",
            "1.0": "Always smooth, explicit transitions between every topic",
        },
        "correlation_hints": "Positively correlated with formality and sentence_complexity",
    },
    {
        "dimension": "DIS",
        "name": "repetition_for_emphasis",
        "description": "Tendency to repeat key phrases or ideas for emphasis",
        "detection_hint": "Identify repeated phrases, restated ideas, callback references to earlier points",
        "value_anchors": {
            "0.0": "Never repeats; each idea stated once",
            "0.25": "Rare; occasional restatement of a key point",
            "0.50": "Moderate; important ideas restated in different words",
            "0.75": "Frequent; key phrases repeated, callbacks common",
            "1.0": "Pervasive; major points restated multiple times for emphasis",
        },
        "correlation_hints": "Positively correlated with turn_length and response_elaboration",
    },

    # === PRA: Pragmatic ===
    {
        "dimension": "PRA",
        "name": "directness",
        "description": "How directly requests, opinions, and disagreements are expressed",
        "detection_hint": "Direct: 'I disagree', 'Do X'. Indirect: 'I wonder if maybe...', 'Have you considered...'",
        "value_anchors": {
            "0.0": "Extremely indirect/circuitous; meaning always implied",
            "0.25": "Mostly indirect; softened with qualifiers and suggestions",
            "0.50": "Balanced; direct on some topics, indirect on others",
            "0.75": "Mostly direct; states views and requests clearly",
            "1.0": "Extremely blunt/direct; no softening of opinions or requests",
        },
        "correlation_hints": "Negatively correlated with hedging_frequency and politeness_strategy",
    },
    {
        "dimension": "PRA",
        "name": "politeness_strategy",
        "description": "Use of face-saving strategies (softeners, apologies, honorifics)",
        "detection_hint": "Look for please, sorry, would you mind, I appreciate, with respect",
        "value_anchors": {
            "0.0": "No politeness markers; blunt and unmitigated",
            "0.25": "Minimal politeness; occasional 'please' or 'thanks'",
            "0.50": "Moderate; standard social niceties present",
            "0.75": "Polite; frequent softeners, apologies, and face-saving phrases",
            "1.0": "Heavy politeness marking; every request softened and hedged",
        },
        "correlation_hints": "Positively correlated with hedging_frequency; negatively correlated with directness",
    },
    {
        "dimension": "PRA",
        "name": "humor_frequency",
        "description": "How often humor, wit, or playfulness appears in communication",
        "detection_hint": (
            "Count jokes, wordplay, ironic observations, self-deprecating comments, "
            "haha/lol markers. Distinguish intentional humor from mere friendliness."
        ),
        "value_anchors": {
            "0.0": "Never uses humor; entirely serious tone",
            "0.25": "Rare humor; perhaps one light comment across several paragraphs",
            "0.50": "Moderate; roughly one humorous moment per response",
            "0.75": "Frequent; most exchanges contain a joke or quip",
            "1.0": "Pervasive; nearly every sentence has a humorous element",
        },
        "correlation_hints": "Negatively correlated with formality and passive_voice_preference; positively correlated with colloquialism",
    },
    {
        "dimension": "PRA",
        "name": "irony_frequency",
        "description": "Use of irony, sarcasm, or saying the opposite of what is meant",
        "detection_hint": "Look for statements where intended meaning contradicts literal meaning",
        "value_anchors": {
            "0.0": "Always literal; no irony or sarcasm",
            "0.25": "Rare; occasional sarcastic aside",
            "0.50": "Moderate; irony used periodically for effect",
            "0.75": "Frequent; sarcasm is a regular communication tool",
            "1.0": "Pervasive irony/sarcasm; default mode of expression",
        },
        "correlation_hints": "Positively correlated with humor_frequency",
    },
    {
        "dimension": "PRA",
        "name": "rhetorical_question_usage",
        "description": "Frequency of questions asked for effect rather than information",
        "detection_hint": "Identify questions where the speaker doesn't expect/want an answer",
        "value_anchors": {
            "0.0": "Never uses rhetorical questions",
            "0.25": "Rare; one rhetorical question in a long passage",
            "0.50": "Moderate; rhetorical questions appear occasionally",
            "0.75": "Frequent; rhetorical questions used as a regular persuasion tool",
            "1.0": "Pervasive; rhetorical questions throughout most arguments",
        },
        "correlation_hints": "Positively correlated with argumentation_style (deductive)",
    },

    # === AFF: Affective ===
    {
        "dimension": "AFF",
        "name": "emotion_word_density",
        "description": "Frequency of explicit emotion words (happy, frustrated, excited, worried)",
        "detection_hint": "Count emotion-laden words and expressions per unit of text",
        "value_anchors": {
            "0.0": "No emotion words used; purely factual/analytical",
            "0.25": "Sparse; one or two emotion words across the text",
            "0.50": "Moderate; emotional language appears in some passages",
            "0.75": "Dense; emotion words in most sentences or paragraphs",
            "1.0": "Saturated with emotional language; almost every sentence expressive",
        },
        "correlation_hints": "Positively correlated with empathy_expression and vulnerability_willingness",
    },
    {
        "dimension": "AFF",
        "name": "emotional_polarity_balance",
        "description": "Ratio of positive to negative emotional expressions",
        "detection_hint": "Classify emotion words as positive or negative, compute ratio",
        "value_anchors": {
            "0.0": "Overwhelmingly negative; almost all emotions negative",
            "0.25": "Skews negative; more negative than positive expressions",
            "0.50": "Balanced; roughly equal positive and negative emotions",
            "0.75": "Skews positive; more positive than negative expressions",
            "1.0": "Overwhelmingly positive; almost all emotions positive",
        },
        "correlation_hints": "Independent of most features; may correlate with empathy_expression",
    },
    {
        "dimension": "AFF",
        "name": "emotional_volatility",
        "description": "How rapidly emotional tone shifts within a conversation",
        "detection_hint": (
            "Track emotional tone per turn/paragraph. Look for: excitement→worry, humor→seriousness, "
            "confidence→doubt, joy→frustration shifts. Count the NUMBER of tone changes. "
            "Even 2-3 shifts in a short text = moderate volatility. A text that goes from happy to "
            "worried to hopeful to anxious shows high volatility even if the shifts are subtle."
        ),
        "value_anchors": {
            "0.0": "Completely stable emotional tone; no shifts",
            "0.25": "Mostly stable; one minor shift across the conversation",
            "0.50": "Some variation; emotional tone shifts a few times",
            "0.75": "Volatile; frequent noticeable shifts in emotional register",
            "1.0": "Extremely volatile; rapid emotional swings within paragraphs",
        },
        "correlation_hints": "Positively correlated with expressive_punctuation; negatively correlated with style_consistency",
    },
    {
        "dimension": "AFF",
        "name": "empathy_expression",
        "description": "Frequency and depth of empathetic responses to others' emotions",
        "detection_hint": "Look for validation, perspective-taking, emotional mirroring phrases",
        "value_anchors": {
            "0.0": "No empathy expression; ignores others' emotions",
            "0.25": "Minimal acknowledgment; brief nods to others' feelings",
            "0.50": "Moderate; sometimes validates or mirrors emotions",
            "0.75": "Empathetic; frequently validates, reflects, and shows understanding",
            "1.0": "Deeply empathetic; consistently mirrors, validates, and explores others' feelings",
        },
        "correlation_hints": "Positively correlated with emotion_word_density and vulnerability_willingness",
    },

    # === INT: Interactional ===
    {
        "dimension": "INT",
        "name": "question_frequency",
        "description": "How often the speaker asks questions in conversation",
        "detection_hint": "Count questions (explicit ? and implicit question forms) per turn",
        "value_anchors": {
            "0.0": "Never asks questions; purely declarative",
            "0.25": "Rare; one question across many turns",
            "0.50": "Moderate; asks questions in roughly half of turns",
            "0.75": "Frequent; most turns include a question",
            "1.0": "Primarily asks questions; response is mostly inquiry",
        },
        "correlation_hints": "Positively correlated with empathy_expression in supportive contexts",
    },
    {
        "dimension": "INT",
        "name": "turn_length",
        "description": "Typical length of a single conversational turn",
        "detection_hint": "Measure average words/sentences per turn",
        "value_anchors": {
            "0.0": "Very brief (1-2 sentences per turn)",
            "0.25": "Short (3-4 sentences per turn)",
            "0.50": "Medium (5-7 sentences per turn; one short paragraph)",
            "0.75": "Long (2-3 paragraphs per turn)",
            "1.0": "Very long (multi-paragraph monologue per turn)",
        },
        "correlation_hints": "Positively correlated with response_elaboration and sentence_length",
    },
    {
        "dimension": "INT",
        "name": "feedback_signal_frequency",
        "description": "Use of backchannel responses (yeah, mm, right, I see, got it)",
        "detection_hint": "Count minimal response tokens that signal listening/acknowledgment",
        "value_anchors": {
            "0.0": "Never uses feedback signals",
            "0.25": "Rare; occasional 'right' or 'I see'",
            "0.50": "Moderate; backchannels appear in some responses",
            "0.75": "Frequent; most responses begin or contain acknowledgment tokens",
            "1.0": "Very frequent; heavy backchanneling throughout",
        },
        "correlation_hints": "Positively correlated with colloquialism",
    },
    {
        "dimension": "INT",
        "name": "response_elaboration",
        "description": "Tendency to elaborate beyond what was asked vs. minimal responses",
        "detection_hint": "Compare response length/content to what the question required",
        "value_anchors": {
            "0.0": "Minimal/exact answers only; nothing extra",
            "0.25": "Slightly beyond minimal; brief additional context",
            "0.50": "Moderate elaboration; adds relevant context and detail",
            "0.75": "Detailed; goes well beyond the question with examples and nuance",
            "1.0": "Always elaborates extensively; responses much longer than required",
        },
        "correlation_hints": "Positively correlated with turn_length and example_frequency",
    },

    # === IDN: Identity ===
    {
        "dimension": "IDN",
        "name": "dialect_markers",
        "description": "Presence of regional or social dialect features in text",
        "detection_hint": "Look for non-standard spellings, regional expressions, dialectal grammar",
        "value_anchors": {
            "0.0": "Standard/neutral language; no dialect features",
            "0.25": "Slight hints; one or two regional expressions",
            "0.50": "Moderate; some dialect features mixed with standard language",
            "0.75": "Strong presence; dialect evident in word choice and grammar",
            "1.0": "Heavy dialect throughout; non-standard forms dominant",
        },
        "correlation_hints": "Positively correlated with colloquialism and grammar_deviation",
    },
    {
        "dimension": "IDN",
        "name": "generational_vocabulary",
        "description": "Use of age/generation-specific terms and references",
        "detection_hint": "Identify slang, cultural references, or expressions tied to a generation",
        "value_anchors": {
            "0.0": "Age-neutral vocabulary; no generational markers",
            "0.25": "Slight hints; one or two generation-specific terms",
            "0.50": "Moderate; occasional generational slang or references",
            "0.75": "Noticeable; generational vocabulary used regularly",
            "1.0": "Strongly generation-marked; vocabulary heavily tied to a specific era",
        },
        "correlation_hints": "Positively correlated with cultural_reference_density and colloquialism",
    },
    {
        "dimension": "IDN",
        "name": "cultural_reference_density",
        "description": "Frequency of references to cultural artifacts (media, memes, historical events, literature)",
        "detection_hint": "Count references to movies, books, memes, public figures, events",
        "value_anchors": {
            "0.0": "No cultural references",
            "0.25": "Rare; one reference in the entire text",
            "0.50": "Moderate; a few cultural references sprinkled in",
            "0.75": "Frequent; cultural references used to illustrate many points",
            "1.0": "Densely referential; cultural artifacts cited constantly",
        },
        "correlation_hints": "Positively correlated with generational_vocabulary and example_frequency",
    },

    # === MET: Metalingual ===
    {
        "dimension": "MET",
        "name": "self_correction_frequency",
        "description": "How often the speaker corrects or amends their own statements",
        "detection_hint": "Look for 'I mean', 'actually', 'well, let me rephrase', corrections",
        "value_anchors": {
            "0.0": "Never self-corrects; all statements final",
            "0.25": "Rare; one correction across the text",
            "0.50": "Moderate; corrects or amends a few times",
            "0.75": "Frequent; regularly revises statements mid-thought",
            "1.0": "Constant self-correction; nearly every paragraph amended",
        },
        "correlation_hints": "Positively correlated with hedging_frequency and metacommentary",
    },
    {
        "dimension": "MET",
        "name": "definition_tendency",
        "description": "Tendency to define terms or explain concepts proactively",
        "detection_hint": (
            "Look for 'by X I mean', 'that is to say', 'in other words', definitional clauses, "
            "parenthetical explanations. Count how often the speaker pauses to define or clarify "
            "terms even when not asked."
        ),
        "value_anchors": {
            "0.0": "Assumes shared understanding; never defines terms",
            "0.25": "Rarely defines; only unusual technical terms explained",
            "0.50": "Sometimes defines; explains terms when they might be ambiguous",
            "0.75": "Frequently defines; proactively explains most concepts used",
            "1.0": "Defines everything explicitly; constant clarification of terms",
        },
        "correlation_hints": "Positively correlated with jargon_density; negatively correlated with ellipsis_frequency",
    },
    {
        "dimension": "MET",
        "name": "metacommentary",
        "description": "Commenting on the conversation itself or one's own communication",
        "detection_hint": "Look for 'I'm going on a tangent', 'to get back to the point', 'I realize I'm being vague'",
        "value_anchors": {
            "0.0": "No metacommentary; never comments on own communication",
            "0.25": "Rare; one meta-comment across the text",
            "0.50": "Moderate; occasionally reflects on own communication style",
            "0.75": "Frequent; regularly comments on the conversation or own expression",
            "1.0": "Pervasive; constant self-aware commentary on how they communicate",
        },
        "correlation_hints": "Positively correlated with self_correction_frequency",
    },

    # === TMP: Temporal ===
    {
        "dimension": "TMP",
        "name": "warmup_pattern",
        "description": "How communication style shifts from start to middle of a conversation",
        "detection_hint": "Compare style features in first 3 turns vs. turns 10+. Measure the delta.",
        "value_anchors": {
            "0.0": "No warmup, immediately at full expression",
            "0.25": "Slight warmup; minor loosening after first turn",
            "0.50": "Moderate; noticeably different style by mid-conversation",
            "0.75": "Significant warmup; takes several turns to open up",
            "1.0": "Long warmup; style shifts dramatically over many turns",
        },
        "correlation_hints": "Positively correlated with vulnerability_willingness trajectory",
    },
    {
        "dimension": "TMP",
        "name": "style_consistency",
        "description": "How stable the communication style remains across a conversation",
        "detection_hint": "Measure variance of key features (formality, sentence length) across turns",
        "value_anchors": {
            "0.0": "Highly variable style; shifts significantly between turns",
            "0.25": "Somewhat inconsistent; noticeable style fluctuations",
            "0.50": "Moderate consistency; occasional style variations",
            "0.75": "Mostly consistent; minor variations only",
            "1.0": "Extremely consistent; same style throughout",
        },
        "correlation_hints": "Negatively correlated with emotional_volatility and register_shift_frequency",
    },
    {
        "dimension": "TMP",
        "name": "adaptation_speed",
        "description": "How quickly the speaker adjusts style to match conversation partner or context",
        "detection_hint": "Measure how many turns it takes for style features to shift when context changes",
        "value_anchors": {
            "0.0": "Does not adapt; same style regardless of partner or context",
            "0.25": "Slow adaptation; takes many turns to shift",
            "0.50": "Moderate; adapts within a few turns",
            "0.75": "Quick; noticeable adaptation within 1-2 turns",
            "1.0": "Adapts almost immediately to new context or partner",
        },
        "correlation_hints": "Positively correlated with context_sensitivity",
    },

    # === ERR: Error Patterns ===
    {
        "dimension": "ERR",
        "name": "typo_frequency",
        "description": "Rate of typographical errors in text",
        "detection_hint": "Count obvious typos, misspellings, transposed letters",
        "value_anchors": {
            "0.0": "Zero typos; perfectly spelled throughout",
            "0.25": "Rare; one or two minor typos in the whole text",
            "0.50": "Moderate; several typos scattered through the text",
            "0.75": "Frequent; multiple typos per paragraph",
            "1.0": "Very frequent; typos in nearly every sentence",
        },
        "correlation_hints": "Positively correlated with grammar_deviation and punctuation_irregularity",
    },
    {
        "dimension": "ERR",
        "name": "grammar_deviation",
        "description": "Frequency of non-standard grammar (intentional or habitual)",
        "detection_hint": "Identify subject-verb disagreement, run-ons, fragments used as style",
        "value_anchors": {
            "0.0": "Textbook grammar; no deviations",
            "0.25": "Mostly correct; one or two informal grammar choices",
            "0.50": "Moderate; some non-standard constructions mixed with correct grammar",
            "0.75": "Frequent; non-standard grammar is common and appears intentional",
            "1.0": "Pervasive grammatical deviations throughout",
        },
        "correlation_hints": "Positively correlated with colloquialism and typo_frequency; negatively correlated with formality",
    },
    {
        "dimension": "ERR",
        "name": "punctuation_irregularity",
        "description": "Non-standard punctuation usage (multiple exclamation marks, no periods, etc.)",
        "detection_hint": "Look for !!! or ???, comma splices, missing periods, excessive ellipses...",
        "value_anchors": {
            "0.0": "Standard punctuation throughout",
            "0.25": "Mostly standard; occasional missing period or extra mark",
            "0.50": "Moderate; some non-standard punctuation patterns",
            "0.75": "Frequent; non-standard punctuation is a noticeable style element",
            "1.0": "Highly irregular punctuation; standard rules mostly ignored",
        },
        "correlation_hints": "Positively correlated with expressive_punctuation and typo_frequency",
    },

    # === CSW: Code-switching ===
    {
        "dimension": "CSW",
        "name": "register_shift_frequency",
        "description": "How often the speaker shifts between formal and informal registers",
        "detection_hint": "Track formality level per sentence and count transitions above threshold",
        "value_anchors": {
            "0.0": "Maintains single register throughout",
            "0.25": "Rare shifts; one or two register changes in the text",
            "0.50": "Moderate; some intentional register shifts",
            "0.75": "Frequent; regularly alternates between formal and informal",
            "1.0": "Constantly shifting registers; every few sentences different",
        },
        "correlation_hints": "Negatively correlated with style_consistency; positively correlated with context_sensitivity",
    },
    {
        "dimension": "CSW",
        "name": "language_mixing",
        "description": "Mixing words or phrases from other languages into primary language",
        "detection_hint": "Identify foreign words, phrases, or code-switching between languages",
        "value_anchors": {
            "0.0": "Monolingual; single language only",
            "0.25": "Rare; one or two borrowed words or phrases",
            "0.50": "Moderate; occasional foreign expressions woven in",
            "0.75": "Frequent; regularly uses words from other languages",
            "1.0": "Heavy multilingual mixing; substantial portions in other languages",
        },
        "correlation_hints": "Positively correlated with cultural_reference_density",
    },
    {
        "dimension": "CSW",
        "name": "context_sensitivity",
        "description": "How strongly style shifts based on audience/context",
        "detection_hint": "Compare style across different conversation contexts for same speaker",
        "value_anchors": {
            "0.0": "Same style regardless of context; no audience adaptation",
            "0.25": "Slight shifts; minor adjustments for different contexts",
            "0.50": "Moderate; noticeable but not dramatic context-dependent shifts",
            "0.75": "Significant; clearly different style for different audiences",
            "1.0": "Dramatically different per context; almost like different speakers",
        },
        "correlation_hints": "Positively correlated with adaptation_speed and register_shift_frequency",
    },

    # === PTX: Para-textual ===
    {
        "dimension": "PTX",
        "name": "emoji_usage",
        "description": "Frequency and diversity of emoji in text communication",
        "detection_hint": "Count emoji per message, note variety vs. repetition of specific emoji",
        "value_anchors": {
            "0.0": "Never uses emoji",
            "0.25": "Rare; one emoji in a long message",
            "0.50": "Moderate; a few emoji per message or response",
            "0.75": "Frequent; emoji in most messages, diverse set",
            "1.0": "Emoji in nearly every sentence; heavy and varied usage",
        },
        "correlation_hints": "Positively correlated with colloquialism and expressive_punctuation; negatively correlated with formality",
    },
    {
        "dimension": "PTX",
        "name": "formatting_habits",
        "description": "Use of bold, italics, lists, headers, code blocks, etc.",
        "detection_hint": "Identify markdown/formatting markers, structured layouts, visual organization",
        "value_anchors": {
            "0.0": "Plain text only; no formatting",
            "0.25": "Minimal; occasional bold or italic for emphasis",
            "0.50": "Moderate; some lists or structured formatting",
            "0.75": "Heavy; regular use of headers, lists, bold, code blocks",
            "1.0": "Extensive formatting throughout; highly structured visual layout",
        },
        "correlation_hints": "Positively correlated with formality in professional contexts",
    },
    {
        "dimension": "PTX",
        "name": "expressive_punctuation",
        "description": "Using punctuation for emotional expression (... for trailing off, !! for excitement)",
        "detection_hint": "Count ellipses, multiple exclamation/question marks, em-dashes for dramatic pause",
        "value_anchors": {
            "0.0": "Punctuation purely grammatical; no expressive use",
            "0.25": "Rare; occasional ellipsis or extra exclamation mark",
            "0.50": "Moderate; some expressive punctuation in emotional passages",
            "0.75": "Frequent; ellipses, exclamation clusters, dashes used regularly",
            "1.0": "Heavily expressive; punctuation is a primary emotional channel",
        },
        "correlation_hints": "Positively correlated with emotional_volatility and emoji_usage",
    },

    # === DSC: Disclosure ===
    {
        "dimension": "DSC",
        "name": "disclosure_depth",
        "description": "How deep self-revelations go (facts → opinions → feelings → beliefs → insights)",
        "detection_hint": "Classify statements: L0 pleasantry, L1 fact, L2 opinion, L3 emotion, L4 belief, L5 insight",
        "value_anchors": {
            "0.0": "Only surface pleasantries; no personal information",
            "0.25": "Factual self-disclosure; shares basic personal facts",
            "0.50": "Opinions shared; expresses personal views and preferences",
            "0.75": "Emotional disclosure; shares feelings, fears, and hopes",
            "1.0": "Deep self-insight; reveals core beliefs, vulnerabilities, and self-awareness",
        },
        "correlation_hints": "Positively correlated with vulnerability_willingness and emotion_word_density",
    },
    {
        "dimension": "DSC",
        "name": "vulnerability_willingness",
        "description": "Willingness to express uncertainty, weakness, or emotional vulnerability",
        "detection_hint": "Look for admissions of not knowing, expressions of fear/doubt, asking for help",
        "value_anchors": {
            "0.0": "Never shows vulnerability; always projects confidence",
            "0.25": "Rare; admits uncertainty only when pressed",
            "0.50": "Moderate; sometimes shares doubts or uncertainties",
            "0.75": "Open; frequently expresses uncertainty and emotional vulnerability",
            "1.0": "Very openly vulnerable; readily shares fears, doubts, weaknesses",
        },
        "correlation_hints": "Positively correlated with disclosure_depth and empathy_expression",
    },
    {
        "dimension": "DSC",
        "name": "reciprocity_sensitivity",
        "description": "How much disclosure increases when the other party also discloses",
        "detection_hint": "Compare disclosure depth before and after the partner shares something personal",
        "value_anchors": {
            "0.0": "Disclosure unaffected by partner; same level regardless",
            "0.25": "Slight response; minor increase after partner discloses",
            "0.50": "Moderate; noticeably more open after partner shares",
            "0.75": "Responsive; clearly matches and slightly exceeds partner's disclosure",
            "1.0": "Strongly reciprocal; disclosure closely mirrors partner's openness",
        },
        "correlation_hints": "Positively correlated with empathy_expression and adaptation_speed",
    },
]


def get_features_for_dimension(dimension_code: str) -> list[dict]:
    """Return all catalog features for a given dimension code."""
    return [f for f in FEATURE_CATALOG if f["dimension"] == dimension_code]
