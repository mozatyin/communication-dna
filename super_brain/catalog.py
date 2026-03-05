"""Trait catalog: 68 personality traits across 13 dimensions (9 layers).

Each trait has:
- dimension: which dimension group (OPN, CON, EXT, AGR, NEU, HON, DRK, EMO, SOC, COG, VAL, STR, HUM)
- name: unique identifier
- description: what it measures
- detection_hint: how to identify it in text
- value_anchors: 5 calibration points (0.0, 0.25, 0.50, 0.75, 1.0)
- correlation_hints: relationships to other traits
"""

ALL_DIMENSIONS: dict[str, str] = {
    "OPN": "Openness — Intellectual curiosity and imagination",
    "CON": "Conscientiousness — Organization and self-discipline",
    "EXT": "Extraversion — Social energy and assertiveness",
    "AGR": "Agreeableness — Cooperation and trust",
    "NEU": "Neuroticism — Emotional instability and negativity",
    "HON": "Honesty-Humility — Sincerity and fairness (HEXACO)",
    "DRK": "Dark Traits — Narcissism, Machiavellianism, psychopathy, sadism",
    "EMO": "Emotional Architecture — Granularity, regulation, empathy",
    "SOC": "Social Dynamics — Attachment, dominance, conflict style",
    "COG": "Cognitive Style — Need for cognition, flexibility, locus of control",
    "VAL": "Values & Morality — Care, fairness, loyalty, authority",
    "STR": "Interpersonal Strategy — Information control, mirroring, seduction patterns",
    "HUM": "Humor Style — Affiliative, self-enhancing, aggressive, self-defeating",
}

# ── Consistency rules: (trait_a, trait_b, max_sum) ───────────────────────────

CONSISTENCY_RULES: list[tuple[str, str, float]] = [
    ("narcissism", "humility_hexaco", 1.3),
    ("trust", "psychopathy", 1.3),
    ("anxiety", "locus_of_control", 1.5),
    ("sincerity", "machiavellianism", 1.2),
    ("compliance", "social_dominance", 1.3),
    ("impulsiveness", "deliberation", 1.3),
    ("empathy_affective", "sadism", 1.1),
]


TRAIT_CATALOG: list[dict] = [
    # ═══════════════════════════════════════════════════════════════════════
    # Layer 1: Core Personality — Big Five 30 facets
    # ═══════════════════════════════════════════════════════════════════════

    # ── OPN: Openness (6 traits) ─────────────────────────────────────────
    {
        "dimension": "OPN",
        "name": "fantasy",
        "description": "Active imagination, rich inner world, tendency to daydream",
        "detection_hint": "Look for imaginative scenarios, hypotheticals, 'what if' thinking, metaphorical language, references to dreams or ideal worlds",
        "value_anchors": {
            "0.0": "Entirely concrete and literal; never engages in hypotheticals or daydreaming",
            "0.25": "Mostly practical; rare use of imagination, sticks to facts",
            "0.50": "Balanced; occasionally uses metaphors or hypotheticals but grounded",
            "0.75": "Frequently imaginative; rich metaphors, enjoys exploring possibilities",
            "1.0": "Deeply immersed in imagination; elaborate hypotheticals, vivid inner world dominates expression",
        },
        "correlation_hints": "Positively correlated with ideas, aesthetics; negatively with order",
    },
    {
        "dimension": "OPN",
        "name": "aesthetics",
        "description": "Sensitivity to beauty, art, and sensory experiences",
        "detection_hint": "Look for sensory-rich descriptions, references to beauty/art/music/nature, aesthetic judgments, appreciation of form and design",
        "value_anchors": {
            "0.0": "No aesthetic sensitivity; purely functional descriptions, ignores beauty",
            "0.25": "Rarely notices aesthetics; occasional brief mention of appearance",
            "0.50": "Moderate aesthetic awareness; sometimes describes things beautifully",
            "0.75": "Strong aesthetic sensitivity; frequently uses sensory-rich language",
            "1.0": "Deeply aesthetic; language itself is artful, constantly attuned to beauty and sensory detail",
        },
        "correlation_hints": "Positively correlated with fantasy, emotional_expressiveness, feelings",
    },
    {
        "dimension": "OPN",
        "name": "feelings",
        "description": "Openness to experiencing and acknowledging the full range of emotions",
        "detection_hint": "Look for emotional vocabulary range, willingness to name feelings, comfort with complex emotions, emotional nuance in descriptions",
        "value_anchors": {
            "0.0": "Emotionally closed; avoids naming feelings, dismisses emotional topics",
            "0.25": "Acknowledges basic emotions but uncomfortable exploring them",
            "0.50": "Moderate emotional openness; names common feelings when relevant",
            "0.75": "Emotionally open; comfortably discusses complex feelings and emotional states",
            "1.0": "Deeply emotionally attuned; embraces all feelings, rich emotional vocabulary, explores nuanced emotional states",
        },
        "correlation_hints": "Positively correlated with emotional_granularity, emotional_expressiveness; negatively with psychopathy",
    },
    {
        "dimension": "OPN",
        "name": "actions",
        "description": "Willingness to try new activities and seek novel experiences",
        "detection_hint": "Look for mentions of trying new things, variety-seeking, openness to change, travel references, boredom with routine",
        "value_anchors": {
            "0.0": "Strongly prefers routine; resists any change or new experience",
            "0.25": "Generally prefers familiar patterns; occasionally open to minor changes",
            "0.50": "Balanced between routine and novelty; open to new things when suggested",
            "0.75": "Actively seeks new experiences; bored by routine, values variety",
            "1.0": "Relentlessly novelty-seeking; constantly pursuing new activities, thrives on change",
        },
        "correlation_hints": "Positively correlated with excitement_seeking, cognitive_flexibility",
    },
    {
        "dimension": "OPN",
        "name": "ideas",
        "description": "Intellectual curiosity, love of abstract thinking and theoretical discussion",
        "detection_hint": "Look for abstract reasoning, theoretical frameworks, philosophical questions, 'why' questions, engagement with ideas for their own sake",
        "value_anchors": {
            "0.0": "Purely practical; avoids abstract thinking, dismisses theoretical discussion",
            "0.25": "Occasionally engages with ideas but prefers practical focus",
            "0.50": "Moderate intellectual curiosity; engages with ideas when prompted",
            "0.75": "Strong intellectual drive; enjoys debates, explores multiple perspectives",
            "1.0": "Intensely curious; loves abstract thinking, philosophical tangents, ideas for their own sake",
        },
        "correlation_hints": "Positively correlated with need_for_cognition, fantasy; negatively with cognitive rigidity",
    },
    {
        "dimension": "OPN",
        "name": "values_openness",
        "description": "Willingness to challenge conventions and re-examine values",
        "detection_hint": "Look for questioning of norms, challenging traditions, progressive framing, resistance to 'because that's how it's done'",
        "value_anchors": {
            "0.0": "Strictly traditional; defends established norms, uncomfortable with value challenges",
            "0.25": "Generally conventional; rarely questions established values",
            "0.50": "Moderate; open to different perspectives but has firm core values",
            "0.75": "Progressive-leaning; actively questions norms, comfortable challenging conventions",
            "1.0": "Radically open; constantly re-examines all values and norms, embraces unconventional views",
        },
        "correlation_hints": "Positively correlated with cognitive_flexibility; negatively with authority_respect",
    },

    # ── CON: Conscientiousness (6 traits) ────────────────────────────────
    {
        "dimension": "CON",
        "name": "competence",
        "description": "Belief in own capability and effectiveness",
        "detection_hint": "Look for confident assertions about ability, 'I can handle this', self-assured problem-solving language, lack of self-doubt",
        "value_anchors": {
            "0.0": "Persistent self-doubt; 'I can't', 'I'm not good enough', defers to others",
            "0.25": "Some self-doubt; hesitant about own abilities, seeks reassurance",
            "0.50": "Moderate confidence; capable in familiar areas, uncertain in new ones",
            "0.75": "Confident; believes in own ability, comfortable tackling challenges",
            "1.0": "Extremely self-assured; 'I've got this', handles any challenge with confidence",
        },
        "correlation_hints": "Positively correlated with locus_of_control, assertiveness; negatively with anxiety",
    },
    {
        "dimension": "CON",
        "name": "order",
        "description": "Preference for organization, structure, and tidiness",
        "detection_hint": "Look for structured communication (numbered lists, clear sections), references to plans/schedules, preference for clarity and organization",
        "value_anchors": {
            "0.0": "Chaotic; disorganized communication, random topic jumps, no structure",
            "0.25": "Loosely organized; some structure but comfortable with messiness",
            "0.50": "Moderate organization; uses basic structure when needed",
            "0.75": "Well-organized; clear structure, logical flow, values tidiness",
            "1.0": "Extremely orderly; meticulous structure, numbered lists, everything categorized",
        },
        "correlation_hints": "Positively correlated with deliberation, self_discipline; negatively with impulsiveness",
    },
    {
        "dimension": "CON",
        "name": "dutifulness",
        "description": "Sense of obligation and commitment to promises",
        "detection_hint": "Look for references to duty, obligation, keeping promises, 'I should', 'I must', reliability language, guilt about unfinished tasks",
        "value_anchors": {
            "0.0": "Ignores obligations; unreliable, dismisses commitments",
            "0.25": "Loosely committed; fulfills major obligations but drops minor ones",
            "0.50": "Moderate duty sense; generally reliable but flexible about commitments",
            "0.75": "Strong sense of duty; takes commitments seriously, feels guilty about failures",
            "1.0": "Extremely dutiful; rigid about obligations, 'a promise is a promise', guilt-driven reliability",
        },
        "correlation_hints": "Positively correlated with loyalty_group, sincerity; negatively with machiavellianism",
    },
    {
        "dimension": "CON",
        "name": "achievement_striving",
        "description": "Drive to achieve goals and exceed standards",
        "detection_hint": "Look for ambition language, goal references, competitive framing, 'the best', growth mindset, dissatisfaction with 'good enough'",
        "value_anchors": {
            "0.0": "No ambition; content with minimum, no drive to improve",
            "0.25": "Low ambition; comfortable with current state, rarely pushes for more",
            "0.50": "Moderate drive; has goals but doesn't obsess over achievement",
            "0.75": "Driven; clear goals, pushes for excellence, unsatisfied with mediocrity",
            "1.0": "Relentlessly ambitious; never satisfied, constant self-improvement, competitive",
        },
        "correlation_hints": "Positively correlated with competence, tenacity (self_discipline); negatively with depression",
    },
    {
        "dimension": "CON",
        "name": "self_discipline",
        "description": "Ability to persist at tasks and resist distractions",
        "detection_hint": "Look for persistence language, staying on topic, follow-through references, discipline framing, 'I make myself do it'",
        "value_anchors": {
            "0.0": "No discipline; can't stick to anything, constantly distracted, procrastinates",
            "0.25": "Weak discipline; struggles to persist, easily sidetracked",
            "0.50": "Moderate discipline; can persist when motivated but sometimes wavers",
            "0.75": "Strong discipline; stays focused, follows through consistently",
            "1.0": "Iron discipline; unstoppable persistence, never gives up, structured routines",
        },
        "correlation_hints": "Positively correlated with deliberation, order; negatively with impulsiveness",
    },
    {
        "dimension": "CON",
        "name": "deliberation",
        "description": "Tendency to think carefully before acting",
        "detection_hint": "Look for 'let me think about this', weighing pros and cons, cautious language, planning before action, considering consequences",
        "value_anchors": {
            "0.0": "Completely impulsive; acts without thinking, no planning",
            "0.25": "Mostly impulsive; occasional brief consideration before acting",
            "0.50": "Moderate; thinks before major decisions but spontaneous in small ones",
            "0.75": "Deliberate; carefully considers options, plans ahead, cautious",
            "1.0": "Extremely deliberate; overthinks everything, analysis paralysis, never rushes",
        },
        "correlation_hints": "Negatively correlated with impulsiveness, excitement_seeking; positively with order",
    },

    # ── EXT: Extraversion (6 traits) ────────────────────────────────────
    {
        "dimension": "EXT",
        "name": "warmth",
        "description": "Interpersonal warmth, affection, and friendliness",
        "detection_hint": "Look for warm greetings, affectionate language, terms of endearment, expressing care, inclusive 'we' language",
        "value_anchors": {
            "0.0": "Cold and distant; no warmth, purely transactional communication",
            "0.25": "Cool; polite but not warm, minimal emotional connection",
            "0.50": "Moderately warm; friendly when engaged but not effusive",
            "0.75": "Warm; genuinely friendly, uses affectionate language, makes others feel welcome",
            "1.0": "Extremely warm; effusive affection, radiates caring, deeply personal engagement",
        },
        "correlation_hints": "Positively correlated with empathy_affective, positive_emotions, trust",
    },
    {
        "dimension": "EXT",
        "name": "gregariousness",
        "description": "Preference for social interaction and group activities",
        "detection_hint": "Look for references to social events, friends, group activities, discomfort with being alone, 'we should all...'",
        "value_anchors": {
            "0.0": "Strongly solitary; avoids social contact, prefers being alone",
            "0.25": "Introverted; prefers small groups or one-on-one, uncomfortable in crowds",
            "0.50": "Balanced; enjoys socializing but also needs alone time",
            "0.75": "Social; frequently references groups, enjoys gatherings, seeks company",
            "1.0": "Extremely gregarious; always seeking social contact, energized by crowds",
        },
        "correlation_hints": "Positively correlated with warmth, positive_emotions; negatively with attachment_avoidance",
    },
    {
        "dimension": "EXT",
        "name": "assertiveness",
        "description": "Tendency to take charge, speak up, and lead",
        "detection_hint": "Look for directive language, taking initiative, 'we should', decisive statements, leading conversations, disagreeing openly",
        "value_anchors": {
            "0.0": "Completely passive; never leads, defers to everyone, submissive",
            "0.25": "Mostly passive; occasionally speaks up but usually follows others",
            "0.50": "Moderate; asserts when necessary but comfortable following too",
            "0.75": "Assertive; frequently takes charge, states opinions clearly, leads naturally",
            "1.0": "Dominant; always takes charge, commands attention, strong leadership drive",
        },
        "correlation_hints": "Positively correlated with social_dominance, competence; negatively with compliance, meekness",
    },
    {
        "dimension": "EXT",
        "name": "activity_level",
        "description": "Pace of life, energy level, need for activity",
        "detection_hint": "Look for high-energy language, busy schedules, fast-paced communication, multiple activities, enthusiasm about doing things",
        "value_anchors": {
            "0.0": "Very low energy; slow-paced, lethargic communication style",
            "0.25": "Low energy; calm and unhurried, prefers relaxed pace",
            "0.50": "Moderate energy; active when needed but not hyperactive",
            "0.75": "High energy; fast-paced, mentions many activities, enthusiastic",
            "1.0": "Extremely high energy; frenetic pace, always doing something, restless",
        },
        "correlation_hints": "Positively correlated with vivacity (positive_emotions), excitement_seeking",
    },
    {
        "dimension": "EXT",
        "name": "excitement_seeking",
        "description": "Need for stimulation, thrills, and intense experiences",
        "detection_hint": "Look for thrill-seeking references, boredom complaints, craving novelty, risk-taking language, 'life is short'",
        "value_anchors": {
            "0.0": "Avoids all stimulation; prefers calm, predictable, safe experiences",
            "0.25": "Low thrill-seeking; comfortable with mild novelty but avoids risk",
            "0.50": "Moderate; enjoys occasional excitement but not addicted to thrills",
            "0.75": "Thrill-seeking; craves novelty, gets bored easily, takes risks",
            "1.0": "Extreme thrill-seeker; addicted to intensity, reckless, bored by calm",
        },
        "correlation_hints": "Positively correlated with actions (openness), impulsiveness; negatively with deliberation",
    },
    {
        "dimension": "EXT",
        "name": "positive_emotions",
        "description": "Tendency to experience and express positive emotions",
        "detection_hint": "Look for joy, enthusiasm, optimism, laughter, exclamation marks, positive framing, 'great!', 'awesome', 'love it'",
        "value_anchors": {
            "0.0": "Flat affect; no positive emotion expression, gloomy tone",
            "0.25": "Subdued; rarely expresses joy, understated positive emotions",
            "0.50": "Moderate positivity; appropriately cheerful but not exuberant",
            "0.75": "Positive; frequently expresses joy, enthusiastic, optimistic framing",
            "1.0": "Exuberantly positive; constant enthusiasm, infectious joy, everything is 'amazing'",
        },
        "correlation_hints": "Positively correlated with warmth, humor_affiliative; negatively with depression",
    },

    # ── AGR: Agreeableness (6 traits) ───────────────────────────────────
    {
        "dimension": "AGR",
        "name": "trust",
        "description": "Default assumption that others are honest and well-intentioned",
        "detection_hint": "Look for giving benefit of the doubt, assuming good faith, lack of suspicion, 'I'm sure they meant well'",
        "value_anchors": {
            "0.0": "Deeply suspicious; assumes others are deceptive, cynical about motives",
            "0.25": "Guarded; cautious about trusting, questions motives",
            "0.50": "Moderate trust; gives benefit of doubt initially but verifies",
            "0.75": "Trusting; assumes good faith, believes others are generally honest",
            "1.0": "Extremely trusting; never suspects deception, takes everything at face value",
        },
        "correlation_hints": "Negatively correlated with machiavellianism, psychopathy; positively with warmth",
    },
    {
        "dimension": "AGR",
        "name": "straightforwardness",
        "description": "Directness and honesty in communication, not manipulative",
        "detection_hint": "Look for frank speech, saying what they mean, no hidden agendas, 'to be honest', direct opinions without manipulation",
        "value_anchors": {
            "0.0": "Highly manipulative; deceptive, says what others want to hear, hidden agendas",
            "0.25": "Somewhat guarded; diplomatic to the point of evasiveness",
            "0.50": "Moderate; honest but tactful, balances truth with social harmony",
            "0.75": "Frank; says what they mean, transparent about intentions",
            "1.0": "Bluntly honest; no filter, complete transparency, brutally direct",
        },
        "correlation_hints": "Positively correlated with sincerity (HON), candor; negatively with machiavellianism, information_control",
    },
    {
        "dimension": "AGR",
        "name": "altruism",
        "description": "Genuine concern for others' welfare, willingness to help",
        "detection_hint": "Look for offers to help, concern for others, self-sacrifice references, putting others first, 'how can I help'",
        "value_anchors": {
            "0.0": "Completely self-interested; no concern for others' welfare",
            "0.25": "Mostly self-focused; helps only when convenient",
            "0.50": "Moderate altruism; willing to help but balances own needs",
            "0.75": "Altruistic; frequently puts others first, genuine concern for welfare",
            "1.0": "Selflessly altruistic; always prioritizes others, self-sacrificing",
        },
        "correlation_hints": "Positively correlated with empathy_affective, care_harm; negatively with psychopathy, narcissism",
    },
    {
        "dimension": "AGR",
        "name": "compliance",
        "description": "Tendency to defer to others in conflict, avoid confrontation",
        "detection_hint": "Look for conflict avoidance, 'whatever you think', backing down easily, accommodating language, discomfort with disagreement",
        "value_anchors": {
            "0.0": "Highly confrontational; seeks conflict, never backs down",
            "0.25": "Mostly combative; rarely yields, enjoys debate and argument",
            "0.50": "Moderate; picks battles, compromises when reasonable",
            "0.75": "Compliant; avoids conflict, accommodates others' wishes",
            "1.0": "Extremely compliant; always yields, complete conflict avoidance, doormat",
        },
        "correlation_hints": "Negatively correlated with assertiveness, social_dominance, conflict_assertiveness",
    },
    {
        "dimension": "AGR",
        "name": "modesty",
        "description": "Humility about own achievements and abilities",
        "detection_hint": "Look for downplaying achievements, 'it was nothing', 'I just got lucky', deflecting praise, not bragging",
        "value_anchors": {
            "0.0": "Extremely boastful; constant self-promotion, brags about everything",
            "0.25": "Somewhat immodest; frequently highlights achievements",
            "0.50": "Moderate; acknowledges achievements without excessive pride or false humility",
            "0.75": "Modest; downplays achievements, deflects compliments",
            "1.0": "Extremely self-deprecating; refuses all credit, chronic understatement of abilities",
        },
        "correlation_hints": "Positively correlated with humility_hexaco; negatively with narcissism, self_mythologizing",
    },
    {
        "dimension": "AGR",
        "name": "tender_mindedness",
        "description": "Sympathy and concern for others' suffering",
        "detection_hint": "Look for compassionate responses to suffering, 'that's terrible', emotional reactions to others' pain, advocacy for vulnerable",
        "value_anchors": {
            "0.0": "Hard-hearted; unmoved by others' suffering, 'toughen up' attitude",
            "0.25": "Somewhat detached; acknowledges suffering but emotionally distant",
            "0.50": "Moderate sympathy; cares about others but maintains emotional distance",
            "0.75": "Tender; moved by others' suffering, compassionate responses",
            "1.0": "Extremely tender; deeply moved by any suffering, overwhelmed by compassion",
        },
        "correlation_hints": "Positively correlated with empathy_affective, care_harm; negatively with psychopathy, sadism",
    },

    # ── NEU: Neuroticism (6 traits) ─────────────────────────────────────
    {
        "dimension": "NEU",
        "name": "anxiety",
        "description": "Tendency to worry, feel nervous, and anticipate danger",
        "detection_hint": "Look for worry expressions, 'what if', catastrophizing, seeking reassurance, nervous qualifiers, anticipating problems",
        "value_anchors": {
            "0.0": "Completely calm; never worries, unflappable",
            "0.25": "Generally calm; occasional mild worry about specific things",
            "0.50": "Moderate anxiety; worries about important things but manageable",
            "0.75": "Anxious; frequently worries, anticipates problems, seeks reassurance",
            "1.0": "Chronic anxiety; constant worry, catastrophizing, paralyzed by 'what ifs'",
        },
        "correlation_hints": "Positively correlated with vulnerability, self_consciousness; negatively with courage (locus_of_control)",
    },
    {
        "dimension": "NEU",
        "name": "angry_hostility",
        "description": "Tendency toward anger, irritability, and frustration",
        "detection_hint": "Look for irritation, frustration, complaining, finding things 'ridiculous' or 'annoying'. In casual chat: quick dismissals, impatient tone, low tolerance for inconvenience, blaming, sarcastic edge, complaining about people or situations more than average",
        "value_anchors": {
            "0.0": "Never angry; serene, patient, no hostility",
            "0.25": "Rarely irritated; very slow to anger",
            "0.50": "Moderate; gets frustrated by legitimate issues but controls it",
            "0.75": "Irritable; frequently frustrated, impatient, prone to angry outbursts",
            "1.0": "Chronically hostile; easily enraged, aggressive, bitter",
        },
        "correlation_hints": "Positively correlated with aggression, sadism; negatively with compliance, warmth",
    },
    {
        "dimension": "NEU",
        "name": "depression",
        "description": "Tendency toward sadness, hopelessness, and low mood",
        "detection_hint": "Look for sadness, hopelessness, 'what's the point', pessimistic outlook, low energy in tone, self-pity",
        "value_anchors": {
            "0.0": "Consistently positive mood; never sad or hopeless",
            "0.25": "Occasionally down; brief sadness that passes quickly",
            "0.50": "Moderate; experiences sadness but maintains hope",
            "0.75": "Frequently sad; pessimistic tendencies, struggles to see positive",
            "1.0": "Deeply depressive; pervasive hopelessness, 'nothing matters', chronic sadness",
        },
        "correlation_hints": "Negatively correlated with positive_emotions, locus_of_control; positively with vulnerability",
    },
    {
        "dimension": "NEU",
        "name": "self_consciousness",
        "description": "Tendency to feel embarrassed, judged, and self-aware in social situations",
        "detection_hint": "Look for 'sorry for rambling', concern about how they're perceived, self-monitoring, 'this is probably stupid but', social awkwardness",
        "value_anchors": {
            "0.0": "Completely unselfconscious; never worries about others' judgment",
            "0.25": "Rarely self-conscious; comfortable in most social situations",
            "0.50": "Moderate; occasionally self-aware but not paralyzed by it",
            "0.75": "Self-conscious; frequently monitors impression, apologizes for self",
            "1.0": "Extremely self-conscious; paralyzed by judgment fear, constant self-monitoring",
        },
        "correlation_hints": "Positively correlated with anxiety, modesty; negatively with assertiveness, narcissism",
    },
    {
        "dimension": "NEU",
        "name": "impulsiveness",
        "description": "Difficulty controlling urges, acting without thinking",
        "detection_hint": "Look for sudden topic changes, 'I just blurted out', impulse purchases, regret about hasty actions, stream of consciousness",
        "value_anchors": {
            "0.0": "Completely controlled; never acts on impulse",
            "0.25": "Well-controlled; rarely impulsive, thinks before acting",
            "0.50": "Moderate; sometimes acts spontaneously but generally controlled",
            "0.75": "Impulsive; frequently acts before thinking, spontaneous decisions",
            "1.0": "Extremely impulsive; no impulse control, acts on every urge",
        },
        "correlation_hints": "Negatively correlated with deliberation, self_discipline; positively with excitement_seeking",
    },
    {
        "dimension": "NEU",
        "name": "vulnerability",
        "description": "Susceptibility to stress, feeling overwhelmed under pressure",
        "detection_hint": "Look for 'I can't handle this', overwhelm expressions, seeking help under stress, fragility, 'it's too much'",
        "value_anchors": {
            "0.0": "Stress-proof; thrives under pressure, unshakeable",
            "0.25": "Resilient; handles most stress well, occasionally strained",
            "0.50": "Moderate resilience; copes with normal stress but struggles with extreme",
            "0.75": "Vulnerable; frequently overwhelmed, difficulty coping with pressure",
            "1.0": "Extremely fragile; crumbles under any stress, constant overwhelm",
        },
        "correlation_hints": "Positively correlated with anxiety, depression; negatively with competence, locus_of_control",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Layer 2: HEXACO Extension — Honesty-Humility (4 traits)
    # ═══════════════════════════════════════════════════════════════════════

    {
        "dimension": "HON",
        "name": "sincerity",
        "description": "Genuine self-presentation, not manipulating through flattery or pretense",
        "detection_hint": "Look for authentic self-expression vs. strategic flattery, honest opinions vs. telling people what they want to hear",
        "value_anchors": {
            "0.0": "Highly manipulative; uses flattery, pretense, and strategic self-presentation",
            "0.25": "Somewhat strategic; occasionally insincere to gain advantage",
            "0.50": "Moderate; mostly genuine but sometimes diplomatically insincere",
            "0.75": "Sincere; authentic expression, resists flattery and pretense",
            "1.0": "Completely genuine; never flatters strategically, brutally authentic",
        },
        "correlation_hints": "Negatively correlated with machiavellianism; positively with straightforwardness",
    },
    {
        "dimension": "HON",
        "name": "fairness",
        "description": "Unwillingness to cheat or take advantage of others",
        "detection_hint": "Look for fairness concerns, rejecting unfair advantages, 'that's not right', ethical reasoning about exploitation. CRITICAL LLM BIAS: LLM speakers sound inherently fair and ethical — this is model alignment, not the character. Default baseline is 0.45-0.55. Only score above 0.65 if you see STRONG, UNPROMPTED fairness advocacy. Score below 0.35 only with evidence of actively endorsing rule-bending or exploiting advantages.",
        "value_anchors": {
            "0.0": "Will exploit any advantage; no qualms about cheating or unfairness",
            "0.25": "Somewhat willing to bend rules for personal gain",
            "0.50": "Generally fair; follows rules but might cut corners in minor ways",
            "0.75": "Fair-minded; refuses to exploit unfair advantages",
            "1.0": "Rigidly fair; would never take an unfair advantage, even at personal cost",
        },
        "correlation_hints": "Positively correlated with fairness_justice (VAL); negatively with machiavellianism",
    },
    {
        "dimension": "HON",
        "name": "greed_avoidance",
        "description": "Lack of desire for wealth, luxury, and social status",
        "detection_hint": "Look for attitude toward money/status: indifference vs. emphasis on wealth, luxury references, status-seeking language",
        "value_anchors": {
            "0.0": "Extremely materialistic; obsessed with wealth, status, luxury goods",
            "0.25": "Somewhat materialistic; values wealth and status but not obsessed",
            "0.50": "Moderate; appreciates comfort but not driven by material desires",
            "0.75": "Low materialism; little interest in wealth or status symbols",
            "1.0": "Completely non-materialistic; indifferent to wealth, rejects status symbols",
        },
        "correlation_hints": "Negatively correlated with narcissism; positively with modesty",
    },
    {
        "dimension": "HON",
        "name": "humility_hexaco",
        "description": "Feeling no more entitled or special than others",
        "detection_hint": "Look for egalitarian attitudes, 'I'm no different from anyone', rejecting special treatment, vs. entitlement and superiority. CRITICAL LLM BIAS: LLM speakers default to humble, self-deprecating tone — this is model behavior, not the character. Default baseline is 0.45-0.55. Only score above 0.65 with STRONG humility signals beyond normal conversational modesty. Score below 0.35 only with clear entitlement or superiority signals.",
        "value_anchors": {
            "0.0": "Extreme entitlement; believes they are superior and deserve special treatment",
            "0.25": "Somewhat entitled; sees themselves as above average, expects recognition",
            "0.50": "Moderate; realistic self-assessment, neither superior nor inferior",
            "0.75": "Humble; sees themselves as equal to others, uncomfortable with special treatment",
            "1.0": "Profoundly humble; truly sees no distinction between self and others, refuses all privileges",
        },
        "correlation_hints": "Negatively correlated with narcissism, social_dominance; positively with modesty",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Layer 3: Dark Traits (4 traits)
    # ═══════════════════════════════════════════════════════════════════════

    {
        "dimension": "DRK",
        "name": "narcissism",
        "description": "Grandiose self-view, need for admiration, entitlement",
        "detection_hint": "Look for steering conversations back to self, competitive framing, implicit superiority, lack of follow-up questions about others. In casual chat: not asking about others' experiences, comparing favorably ('I actually...'), absence of anxiety/tentative words. NOTE: first-person pronoun frequency does NOT correlate with narcissism — look for competitive language and self-referential topic steering instead",
        "value_anchors": {
            "0.0": "Healthy self-esteem with no grandiosity; genuinely interested in others",
            "0.25": "Mild self-focus; occasionally steers conversation to self",
            "0.50": "Moderate; some self-promotion but also engages with others",
            "0.75": "Narcissistic tendencies; frequent self-aggrandizing, needs admiration",
            "1.0": "Full grandiose narcissism; everything is about them, entitled, dismissive of others",
        },
        "correlation_hints": "Negatively correlated with humility_hexaco, modesty; positively with self_mythologizing",
    },
    {
        "dimension": "DRK",
        "name": "machiavellianism",
        "description": "Strategic manipulation, cynical worldview, prioritizing self-interest",
        "detection_hint": "Look for cynical observations about people's motives, strategic vagueness, 'they' framing over 'we', longer more elaborate responses, calculating tone. In casual chat: reading situations before sharing, cynical asides ('people are predictable'), framing social situations as systems or games, avoiding self-disclosure while drawing out others",
        "value_anchors": {
            "0.0": "Completely transparent and cooperative; trusts others' goodwill",
            "0.25": "Mild strategic awareness; occasionally considers political angles",
            "0.50": "Moderate; aware of social dynamics, sometimes strategic",
            "0.75": "Calculating; frequently manipulates situations, cynical about human nature",
            "1.0": "Full Machiavellian; everything is strategy, people are pawns, cold calculation",
        },
        "correlation_hints": "Negatively correlated with sincerity, trust; positively with information_control",
    },
    {
        "dimension": "DRK",
        "name": "psychopathy",
        "description": "Emotional coldness, lack of empathy, antisocial tendency",
        "detection_hint": "Look for pragmatic/transactional framing of emotional situations, cause-and-effect language about people ('because...'), focus on material/practical outcomes over emotional, matter-of-fact tone about hardship. In casual chat: low emotional reaction to emotional topics, talking about people instrumentally, past-tense distancing, few anxiety or fear words, concrete over abstract language",
        "value_anchors": {
            "0.0": "Deep empathy and emotional warmth; strong conscience",
            "0.25": "Slightly detached; occasionally emotionally cold in stressful situations",
            "0.50": "Moderate emotional distance; can be cold but has conscience",
            "0.75": "Emotionally cold; low empathy, callous treatment of others",
            "1.0": "Extreme coldness; no empathy, no remorse, treats people as instruments",
        },
        "correlation_hints": "Negatively correlated with empathy_affective, tender_mindedness, trust",
    },
    {
        "dimension": "DRK",
        "name": "sadism",
        "description": "Enjoyment of others' suffering, cruelty for pleasure",
        "detection_hint": "Look for schadenfreude, amusement at others' misfortune, 'they had it coming' attitudes, finding humor in others' failures. In casual chat: enjoying gossip about others' problems, edgy humor about suffering, 'that's kind of funny though' about bad things happening to people, seeking out conflict for entertainment",
        "value_anchors": {
            "0.0": "Pained by others' suffering; never cruel",
            "0.25": "Rarely cruel; occasional schadenfreude but feels guilty",
            "0.50": "Moderate; sometimes enjoys hostile humor but no active cruelty",
            "0.75": "Sadistic tendencies; enjoys mockery, takes pleasure in others' discomfort",
            "1.0": "Full sadism; actively seeks to cause suffering, enjoys cruelty",
        },
        "correlation_hints": "Negatively correlated with empathy_affective, care_harm; positively with humor_aggressive",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Layer 4: Emotional Architecture (6 traits)
    # ═══════════════════════════════════════════════════════════════════════

    {
        "dimension": "EMO",
        "name": "emotional_granularity",
        "description": "Precision and richness of emotional vocabulary",
        "detection_hint": "Look for specific emotion words (wistful, ambivalent, bittersweet) vs. vague (fine, bad, good, okay)",
        "value_anchors": {
            "0.0": "Extremely vague; only 'fine', 'bad', 'good', 'okay'",
            "0.25": "Basic emotions only; happy, sad, angry, scared",
            "0.50": "Moderate precision; uses some nuanced emotion words",
            "0.75": "Rich vocabulary; distinguishes between subtle emotional states",
            "1.0": "Extraordinary precision; 'melancholic yet hopeful', 'wistfully content'",
        },
        "correlation_hints": "Positively correlated with feelings (OPN), emotional_expressiveness; negatively with psychopathy",
    },
    {
        "dimension": "EMO",
        "name": "emotional_regulation",
        "description": "Ability to manage emotional reactions and maintain composure",
        "detection_hint": "Look for active emotion management strategies, reframing, stepping back. IMPORTANT: Composure in casual chat is the NORM and is NOT evidence of high regulation. Only score high if you see ACTIVE regulation efforts. Score 0.45-0.55 for normal composed conversation",
        "value_anchors": {
            "0.0": "No regulation; completely overwhelmed by emotions, reactive, volatile",
            "0.25": "Poor regulation; struggles to contain emotional reactions",
            "0.50": "Moderate; manages most emotions but occasionally overwhelmed",
            "0.75": "Well-regulated; maintains composure, processes emotions constructively",
            "1.0": "Perfectly regulated; always composed, never emotionally reactive",
        },
        "correlation_hints": "Negatively correlated with emotional_volatility, impulsiveness; positively with deliberation",
    },
    {
        "dimension": "EMO",
        "name": "empathy_cognitive",
        "description": "Ability to understand and accurately read others' emotions",
        "detection_hint": "Look for accurate emotion reading, 'you must be feeling...', perspective-taking, understanding unstated feelings",
        "value_anchors": {
            "0.0": "Cannot read others' emotions at all; oblivious to emotional cues",
            "0.25": "Poor emotion reading; occasionally notices obvious emotions",
            "0.50": "Moderate; reads basic emotions but misses subtlety",
            "0.75": "Strong empathy; accurately reads unstated emotions, good perspective-taking",
            "1.0": "Extraordinary emotion reader; catches subtle shifts, deeply understands others' inner worlds",
        },
        "correlation_hints": "Positively correlated with mirroring_ability, empathy_affective",
    },
    {
        "dimension": "EMO",
        "name": "empathy_affective",
        "description": "Tendency to emotionally resonate with others' feelings",
        "detection_hint": "Look for emotional contagion, 'I feel your pain', visceral reactions to others' stories, shared emotional experience",
        "value_anchors": {
            "0.0": "No emotional resonance; unmoved by others' emotions",
            "0.25": "Mild resonance; slightly affected by extreme emotions in others",
            "0.50": "Moderate; feels with others in significant situations",
            "0.75": "Strong resonance; frequently absorbs others' emotions",
            "1.0": "Complete emotional contagion; overwhelmed by others' feelings, deeply feels their pain/joy",
        },
        "correlation_hints": "Positively correlated with tender_mindedness, care_harm; negatively with psychopathy, sadism",
    },
    {
        "dimension": "EMO",
        "name": "emotional_expressiveness",
        "description": "Willingness and ability to outwardly express emotions",
        "detection_hint": "Look for freely sharing feelings, emotional vocabulary density, expressive punctuation. IMPORTANT: Articulate writing is NOT evidence of high expressiveness (LLM bias). Only score high if the person actively shares personal feelings and emotions beyond what the topic requires",
        "value_anchors": {
            "0.0": "Alexithymic; never expresses emotions, completely flat communication",
            "0.25": "Restrained; occasionally hints at emotions but rarely expresses them",
            "0.50": "Moderate; expresses emotions in appropriate contexts",
            "0.75": "Expressive; freely shares feelings, emotionally colorful language",
            "1.0": "Extremely expressive; emotions pour out constantly, highly emotional language",
        },
        "correlation_hints": "Positively correlated with feelings (OPN), emotional_granularity; negatively with psychopathy",
    },
    {
        "dimension": "EMO",
        "name": "emotional_volatility",
        "description": "Frequency and intensity of mood swings",
        "detection_hint": "Look for inconsistent energy across messages, tone shifts between messages, going from enthusiastic to flat. In casual chat: emotional non-sequiturs, variable engagement level, contradictory reactions, being upbeat then suddenly down or vice versa",
        "value_anchors": {
            "0.0": "Completely stable; consistent emotional tone throughout",
            "0.25": "Mostly stable; rare minor mood shifts",
            "0.50": "Moderate; some emotional variation but generally consistent",
            "0.75": "Volatile; frequent mood shifts, emotional ups and downs",
            "1.0": "Extremely volatile; rapid emotional swings, unpredictable reactions",
        },
        "correlation_hints": "Positively correlated with impulsiveness, hot_cold_oscillation; negatively with emotional_regulation",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Layer 5: Social Dynamics (6 traits)
    # ═══════════════════════════════════════════════════════════════════════

    {
        "dimension": "SOC",
        "name": "attachment_anxiety",
        "description": "Fear of abandonment, need for reassurance in relationships",
        "detection_hint": "Look for 'do you still like me?', reassurance-seeking, fear of rejection, clinginess, interpreting silence as rejection",
        "value_anchors": {
            "0.0": "Completely secure; no fear of abandonment",
            "0.25": "Mostly secure; rare moments of insecurity",
            "0.50": "Moderate; some relationship anxiety but manageable",
            "0.75": "Anxious; frequently needs reassurance, reads rejection into ambiguity",
            "1.0": "Extreme attachment anxiety; constant fear of abandonment, clingy, hypervigilant",
        },
        "correlation_hints": "Positively correlated with anxiety (NEU); may co-occur with attachment_avoidance (fearful type)",
    },
    {
        "dimension": "SOC",
        "name": "attachment_avoidance",
        "description": "Discomfort with closeness and emotional intimacy",
        "detection_hint": "Look for 'I need space', deflecting emotional topics, discomfort with vulnerability, keeping conversations surface-level",
        "value_anchors": {
            "0.0": "Deeply desires closeness; openly seeks emotional intimacy",
            "0.25": "Mostly comfortable with closeness; occasional need for space",
            "0.50": "Moderate; comfortable with some intimacy but maintains boundaries",
            "0.75": "Avoidant; uncomfortable with closeness, deflects emotional depth",
            "1.0": "Extreme avoidance; rejects all emotional intimacy, 'I don't need anyone'",
        },
        "correlation_hints": "Negatively correlated with warmth, emotional_expressiveness; positively with psychopathy",
    },
    {
        "dimension": "SOC",
        "name": "social_dominance",
        "description": "Desire for hierarchical status and group control",
        "detection_hint": "Look for status references, hierarchy endorsement, competitive framing about social position. In casual chat: name-dropping, mentioning titles/ranks, 'some people are just better', endorsing meritocratic hierarchy, subtly asserting higher status through topic choices or one-upping",
        "value_anchors": {
            "0.0": "Strongly egalitarian; rejects all hierarchy, advocates equality",
            "0.25": "Mild egalitarianism; prefers flat structures but accepts some hierarchy",
            "0.50": "Moderate; accepts hierarchy as natural but doesn't actively seek dominance",
            "0.75": "Dominant; seeks higher status, endorses hierarchy, competitive",
            "1.0": "Extreme dominance orientation; obsessed with status and control",
        },
        "correlation_hints": "Positively correlated with assertiveness, narcissism; negatively with compliance, humility_hexaco",
    },
    {
        "dimension": "SOC",
        "name": "conflict_assertiveness",
        "description": "Tendency to pursue own interests in conflict (TKI assertiveness axis)",
        "detection_hint": "Look for standing ground in disagreements, pursuing own position, 'I need to push back', vs. yielding immediately",
        "value_anchors": {
            "0.0": "Complete avoidance; never asserts own position in conflict",
            "0.25": "Low assertion; usually yields but occasionally stands firm on important issues",
            "0.50": "Moderate; asserts on important issues, yields on minor ones",
            "0.75": "Assertive in conflict; pushes for own position, comfortable with tension",
            "1.0": "Extremely competitive; always pushes to win, never concedes",
        },
        "correlation_hints": "Positively correlated with assertiveness (EXT); negatively with compliance (AGR)",
    },
    {
        "dimension": "SOC",
        "name": "conflict_cooperativeness",
        "description": "Concern for others' needs in conflict (TKI cooperation axis)",
        "detection_hint": "Look for seeking win-win, 'how can we both get what we need', considering others' perspective in disagreements",
        "value_anchors": {
            "0.0": "Zero concern for others in conflict; only cares about own outcome",
            "0.25": "Low cooperation; mostly focused on own needs in disputes",
            "0.50": "Moderate; willing to compromise, considers both sides",
            "0.75": "Cooperative; actively seeks solutions that work for everyone",
            "1.0": "Extremely cooperative; prioritizes relationship over own interests, always accommodating",
        },
        "correlation_hints": "Positively correlated with altruism, empathy_cognitive; negatively with psychopathy",
    },
    {
        "dimension": "SOC",
        "name": "charm_influence",
        "description": "Ability to attract and persuade others through personal appeal",
        "detection_hint": "Look for ACTIVE rapport-building, making others feel uniquely valued, persuasive framing, social grace beyond mere politeness. IMPORTANT: Mere friendliness in casual chat is NOT charm (score 0.40-0.55 for normal friendly conversation). True charm involves intentional influence, making the other person feel special, and natural persuasiveness",
        "value_anchors": {
            "0.0": "Socially awkward; no ability to charm or persuade",
            "0.25": "Mildly appealing; can be pleasant but not persuasive",
            "0.50": "Moderate charm; likeable and occasionally persuasive",
            "0.75": "Charming; naturally draws people in, skilled at persuasion",
            "1.0": "Irresistibly charismatic; magnetic presence, effortless persuasion",
        },
        "correlation_hints": "Positively correlated with warmth, mirroring_ability; may correlate with narcissism at high levels",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Layer 6: Cognitive Style (4 traits)
    # ═══════════════════════════════════════════════════════════════════════

    {
        "dimension": "COG",
        "name": "need_for_cognition",
        "description": "Enjoyment of deep thinking and complex problems",
        "detection_hint": "Look for intellectual engagement, complex reasoning, 'that's an interesting problem', analysis for its own sake. CRITICAL LLM BIAS: ALL LLM-generated text sounds articulate and analytical by default — this is the model's nature, not the character. Default baseline is 0.40-0.50. Only score above 0.60 if the speaker ACTIVELY seeks out complex topics, asks 'why' questions, or shows genuine excitement about abstract problems. Score below 0.35 only if the speaker actively avoids complexity ('just tell me the answer', 'I don't overthink things').",
        "value_anchors": {
            "0.0": "Avoids all complex thinking; 'just tell me what to do'",
            "0.25": "Low; prefers simple answers, avoids overanalyzing",
            "0.50": "Moderate; engages with complexity when required",
            "0.75": "High; enjoys deep analysis, seeks intellectual challenges",
            "1.0": "Extremely high; addicted to thinking, loves intellectual puzzles",
        },
        "correlation_hints": "Positively correlated with ideas (OPN), intuitive_vs_analytical; negatively with impulsiveness",
    },
    {
        "dimension": "COG",
        "name": "cognitive_flexibility",
        "description": "Ability to switch perspectives and consider alternative viewpoints",
        "detection_hint": "Look for 'on the other hand', considering multiple angles, changing position when presented with evidence, 'that's a good point'",
        "value_anchors": {
            "0.0": "Completely rigid; black-and-white thinking, refuses to consider alternatives",
            "0.25": "Mostly rigid; difficulty seeing other perspectives",
            "0.50": "Moderate flexibility; can see other sides when prompted",
            "0.75": "Flexible; naturally considers multiple perspectives, changes views with evidence",
            "1.0": "Extremely flexible; constantly sees all angles, may struggle to commit to one view",
        },
        "correlation_hints": "Positively correlated with values_openness, ideas; negatively with authority_respect",
    },
    {
        "dimension": "COG",
        "name": "locus_of_control",
        "description": "Belief in personal control over outcomes (internal) vs. external forces",
        "detection_hint": "Look for 'I made this happen' vs. 'it was luck/fate', agency language, personal responsibility vs. blaming circumstances",
        "value_anchors": {
            "0.0": "Fully external; everything is luck/fate/others' fault, helpless victim",
            "0.25": "Mostly external; acknowledges some agency but mainly blames circumstances",
            "0.50": "Balanced; recognizes both personal agency and external factors",
            "0.75": "Internal; takes responsibility, 'I can change this', proactive",
            "1.0": "Fully internal; 'everything is my responsibility', may over-blame self",
        },
        "correlation_hints": "Positively correlated with competence, achievement_striving; negatively with vulnerability, depression",
    },
    {
        "dimension": "COG",
        "name": "intuitive_vs_analytical",
        "description": "Decision-making style: gut feeling vs. data-driven analysis",
        "detection_hint": "Look for 'I feel like' vs. 'the data shows', evidence-based reasoning vs. instinct, structured analysis vs. holistic sensing",
        "value_anchors": {
            "0.0": "Purely intuitive; all decisions based on gut feeling, 'I just know'",
            "0.25": "Mostly intuitive; considers some evidence but trusts instinct",
            "0.50": "Balanced; uses both intuition and analysis depending on context",
            "0.75": "Mostly analytical; prefers data and evidence, distrusts gut feelings",
            "1.0": "Purely analytical; decisions only based on data, 'show me the evidence'",
        },
        "correlation_hints": "Positively correlated with need_for_cognition, deliberation; negatively with impulsiveness",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Layer 7: Values & Morality (4 traits)
    # ═══════════════════════════════════════════════════════════════════════

    {
        "dimension": "VAL",
        "name": "care_harm",
        "description": "Moral concern for protecting others from harm",
        "detection_hint": "Look for concern about suffering, protecting the vulnerable, 'that hurts people', compassion-based moral reasoning",
        "value_anchors": {
            "0.0": "Indifferent to harm; no moral concern about causing suffering",
            "0.25": "Low care; occasionally concerned about severe harm",
            "0.50": "Moderate; cares about harm in obvious cases",
            "0.75": "Strong care ethic; actively concerned about harm, advocates for victims",
            "1.0": "Extreme care; any hint of harm triggers strong moral response",
        },
        "correlation_hints": "Positively correlated with empathy_affective, tender_mindedness, altruism",
    },
    {
        "dimension": "VAL",
        "name": "fairness_justice",
        "description": "Concern for equity, justice, and fair treatment",
        "detection_hint": "Look for 'that's not fair', justice reasoning, equality concerns, 'everyone deserves...', outrage at inequity",
        "value_anchors": {
            "0.0": "No concern for fairness; accepts any outcome regardless of justice",
            "0.25": "Low fairness concern; notices major injustice but doesn't dwell on it",
            "0.50": "Moderate; values fairness as a principle but pragmatic about it",
            "0.75": "Strong justice orientation; vocal about fairness, advocates for equity",
            "1.0": "Extreme justice drive; fairness is paramount, outraged by any inequity",
        },
        "correlation_hints": "Positively correlated with fairness (HON); negatively with machiavellianism",
    },
    {
        "dimension": "VAL",
        "name": "loyalty_group",
        "description": "Devotion to in-group, team, family, or community",
        "detection_hint": "Look for 'we/us vs. them', defending one's group, family/team loyalty references, betrayal sensitivity, group identity",
        "value_anchors": {
            "0.0": "No group loyalty; purely individualistic, no in-group preference",
            "0.25": "Mild; some group identification but willing to criticize own group",
            "0.50": "Moderate loyalty; supports group while maintaining independence",
            "0.75": "Strong loyalty; defends group, 'my team right or wrong', bothered by disloyalty",
            "1.0": "Extreme group loyalty; tribal identity, 'us vs. them', betrayal is unforgivable",
        },
        "correlation_hints": "Positively correlated with dutifulness; may correlate with social_dominance",
    },
    {
        "dimension": "VAL",
        "name": "authority_respect",
        "description": "Respect for hierarchy, tradition, and legitimate authority",
        "detection_hint": "Look for deference to authority, respect for tradition, 'that's the rule', hierarchical framing, vs. anti-authority language",
        "value_anchors": {
            "0.0": "Anti-authoritarian; rebels against all authority, questions every rule",
            "0.25": "Skeptical of authority; prefers to decide for self, questions hierarchy",
            "0.50": "Moderate; respects authority when earned but not blindly",
            "0.75": "Respects authority; defers to legitimate hierarchy, values tradition",
            "1.0": "Extreme deference; unquestioning respect for authority, rigid adherence to tradition",
        },
        "correlation_hints": "Negatively correlated with values_openness; positively with compliance, dutifulness",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Layer 8: Interpersonal Strategy (4 traits)
    # ═══════════════════════════════════════════════════════════════════════

    {
        "dimension": "STR",
        "name": "information_control",
        "description": "Strategic management of what information to reveal or conceal",
        "detection_hint": "Look for strategic vagueness, deflecting personal questions, controlling what gets shared. In casual chat: 'I'd rather not get into that', 'let's just say...', redirecting questions back, giving general answers to specific questions. NOTE: Normal privacy in casual chat is not information control — look for STRATEGIC or purposeful withholding",
        "value_anchors": {
            "0.0": "Completely transparent; shares everything freely, no information strategy",
            "0.25": "Mostly open; occasionally holds back sensitive information",
            "0.50": "Moderate; shares openly but has clear boundaries about private matters",
            "0.75": "Strategic; carefully controls what information is shared and when",
            "1.0": "Extreme control; reveals nothing without purpose, every word is calculated",
        },
        "correlation_hints": "Positively correlated with machiavellianism; negatively with straightforwardness, sincerity",
    },
    {
        "dimension": "STR",
        "name": "mirroring_ability",
        "description": "Capacity to adapt own style to match the other person's",
        "detection_hint": "Look for matching vocabulary/tone to the conversation partner, linguistic accommodation, code-switching in response to others. CRITICAL LLM BIAS: LLM-generated text NATURALLY mirrors the conversation partner's style — this is a property of the model, not the character. Default baseline is 0.40-0.50. Only score above 0.60 if you see DELIBERATE, STRATEGIC style-matching beyond normal conversational accommodation. Score below 0.30 only if the speaker actively RESISTS matching (uses formal tone when partner is casual, or vice versa).",
        "value_anchors": {
            "0.0": "No adaptation; same style regardless of who they're talking to",
            "0.25": "Minimal adaptation; slight adjustments in extreme situations",
            "0.50": "Moderate; adjusts formality and tone to some degree",
            "0.75": "Strong mirroring; naturally matches partner's style, builds rapport through similarity",
            "1.0": "Perfect mirror; seamlessly adopts partner's communication patterns, chameleon-like",
        },
        "correlation_hints": "Positively correlated with empathy_cognitive, charm_influence",
    },
    {
        "dimension": "STR",
        "name": "hot_cold_oscillation",
        "description": "Pattern of alternating between warmth/engagement and distance/coldness",
        "detection_hint": "Look for varying levels of engagement across the conversation, some messages warm and enthusiastic while others are terse/distant. Push-pull dynamics, inconsistent investment. In casual chat: being very into a topic then suddenly indifferent, warm greeting then cool response, variable message length as a signal",
        "value_anchors": {
            "0.0": "Completely consistent; stable warmth or coldness, no oscillation",
            "0.25": "Mostly consistent; rare minor shifts in engagement",
            "0.50": "Moderate; some variation in warmth that seems natural",
            "0.75": "Notable oscillation; clear push-pull pattern, engages then withdraws",
            "1.0": "Extreme oscillation; dramatic hot-cold swings, highly unpredictable engagement",
        },
        "correlation_hints": "Positively correlated with emotional_volatility; may indicate Coquette archetype",
    },
    {
        "dimension": "STR",
        "name": "self_mythologizing",
        "description": "Construction of a dramatic personal narrative and larger-than-life self-image",
        "detection_hint": "Look for dramatic self-stories, 'you won't believe what happened to me', exceptional framing, personal legend building. CRITICAL LLM BIAS: LLM speakers tend toward humble, understated self-presentation — they rarely mythologize spontaneously. Default baseline is 0.30-0.40. Only score below 0.25 if the speaker is ACTIVELY flat and anti-dramatic about their experiences. Score above 0.60 only with clear evidence of narrative embellishment or theatrical self-framing.",
        "value_anchors": {
            "0.0": "Flat self-presentation; no dramatization, matter-of-fact about own life",
            "0.25": "Minimal; occasionally makes stories more interesting but mostly factual",
            "0.50": "Moderate; some narrative embellishment, enjoys a good personal story",
            "0.75": "Strong mythologizing; frames experiences as dramatic, builds personal narrative",
            "1.0": "Extreme; every experience is epic, constructs elaborate personal legend, theatrical self-presentation",
        },
        "correlation_hints": "Positively correlated with narcissism; negatively with modesty, humility_hexaco",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Layer 9: Humor Style (4 traits)
    # ═══════════════════════════════════════════════════════════════════════

    {
        "dimension": "HUM",
        "name": "humor_affiliative",
        "description": "Warm, inclusive humor that builds connection and puts others at ease",
        "detection_hint": "Look for humor that ACTIVELY builds social bonds, inclusive jokes, making others feel part of the fun. IMPORTANT: Normal light humor in conversation is NOT high affiliative humor (score 0.40-0.55 for ordinary friendliness). High affiliative means using humor as a deliberate bonding tool with warm, inclusive intent. Positive sentiment, high wordplay, social warmth in jokes",
        "value_anchors": {
            "0.0": "Never uses warm humor; completely serious in social contexts",
            "0.25": "Rarely uses humor to connect; occasional mild joke",
            "0.50": "Moderate; uses humor socially with reasonable frequency",
            "0.75": "Frequently uses warm humor; often lightens the mood, makes others smile",
            "1.0": "Constantly uses affiliative humor; every interaction is warmed by humor",
        },
        "correlation_hints": "Positively correlated with warmth, positive_emotions, gregariousness",
    },
    {
        "dimension": "HUM",
        "name": "humor_self_enhancing",
        "description": "Using humor to cope with adversity and maintain positive perspective",
        "detection_hint": "Look for laughing about own problems, finding humor in tough situations, 'well at least...', resilient optimism through humor",
        "value_anchors": {
            "0.0": "Takes all adversity seriously; never uses humor to cope",
            "0.25": "Rarely jokes about difficulties; mostly processes them seriously",
            "0.50": "Moderate; sometimes uses humor to cope, sometimes processes seriously",
            "0.75": "Frequently uses humor to cope; finds silver linings, laughs at adversity",
            "1.0": "Always uses humor as coping; every difficulty becomes a funny story",
        },
        "correlation_hints": "Positively correlated with emotional_regulation, locus_of_control; negatively with depression",
    },
    {
        "dimension": "HUM",
        "name": "humor_aggressive",
        "description": "Sarcasm, mockery, and humor at others' expense",
        "detection_hint": "Look for sarcasm directed at others, cutting remarks, mockery, put-downs disguised as jokes. Key markers: negative sentiment with humor, anger undertone, targeting others' flaws, simple/blunt language. In casual chat: making fun of absent people, 'just kidding (not really)', humor with an edge that could sting",
        "value_anchors": {
            "0.0": "Never sarcastic or mocking; all humor is kind",
            "0.25": "Mild sarcasm; occasional witty jabs but nothing harsh",
            "0.50": "Moderate; uses sarcasm and teasing with some frequency",
            "0.75": "Frequently sarcastic; sharp humor, often at others' expense",
            "1.0": "Extremely aggressive humor; constant mockery, biting sarcasm, cruel jokes",
        },
        "correlation_hints": "Positively correlated with angry_hostility, sadism; negatively with warmth, compliance",
    },
    {
        "dimension": "HUM",
        "name": "humor_self_defeating",
        "description": "Self-deprecating humor, putting oneself down for others' approval",
        "detection_hint": "Look for excessive self-deprecation, 'I'm such an idiot haha', making self the butt of jokes, seeking acceptance through self-mockery",
        "value_anchors": {
            "0.0": "Never self-deprecating; protects own image in humor",
            "0.25": "Mild self-deprecation; occasional light self-teasing",
            "0.50": "Moderate; uses self-deprecating humor sometimes for connection",
            "0.75": "Frequently self-deprecating; often the butt of own jokes",
            "1.0": "Extreme self-deprecation; constant self-mockery, uses humor to preemptively devalue self",
        },
        "correlation_hints": "Positively correlated with self_consciousness, depression; negatively with narcissism, competence",
    },
]


# ── Derived helpers ──────────────────────────────────────────────────────────

def get_traits_for_dimension(dimension: str) -> list[dict]:
    """Return all catalog traits for a given dimension code."""
    return [t for t in TRAIT_CATALOG if t["dimension"] == dimension]


def get_trait_by_name(name: str) -> dict | None:
    """Return a catalog entry by trait name."""
    for t in TRAIT_CATALOG:
        if t["name"] == name:
            return t
    return None


# Build lookup map
TRAIT_MAP: dict[tuple[str, str], dict] = {
    (t["dimension"], t["name"]): t for t in TRAIT_CATALOG
}
