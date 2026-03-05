"""Map personality traits to natural conversation topics that reveal them (V2.2).

Each trait maps to 2-5 natural conversation topics/questions that would create
conditions for the trait to manifest — Incisive Questions from SoulMap Method.
These are NOT personality probes. They're natural conversation starters that
organically reveal specific traits.
"""

from __future__ import annotations

TRAIT_TOPIC_MAP: dict[str, list[str]] = {
    # Stubbornly hard traits (priority)
    "humor_self_enhancing": [
        "Have you ever had something go completely wrong but it turned out to be a blessing in disguise?",
        "What's the funniest thing that's happened to you recently — like something bad that you can laugh about now?",
        "How do you usually deal with a really bad day?",
    ],
    "social_dominance": [
        "When you're in a group project or team meeting, what role do you naturally take?",
        "How do you handle it when someone suggests a plan you think won't work?",
        "Tell me about a time you had to convince a group to go in a different direction.",
    ],
    "mirroring_ability": [
        "Do you find yourself picking up other people's accents or mannerisms?",
        "Are you the kind of person who adapts to different groups, or do you stay pretty much the same everywhere?",
        "How do you adjust when you're talking to someone very different from you?",
    ],
    "information_control": [
        "Are you pretty open with people or do you tend to keep things close to the chest?",
        "How much do you share about yourself when you first meet someone?",
        "Is there stuff about yourself that even your close friends don't know?",
    ],
    "competence": [
        "What's something you're really good at that you've had to work hard for?",
        "When you face a new challenge at work, how do you approach it?",
        "Tell me about a time you surprised yourself with how well you handled something.",
    ],
    # Dark traits
    "narcissism": [
        "What's something you're proud of that other people might not know about?",
        "Do you think most people around you understand how capable you actually are?",
        "How do you feel when someone gets credit for something you did?",
    ],
    "machiavellianism": [
        "Do you think it's important to be strategic in how you deal with people at work?",
        "What's your take on office politics — necessary evil or just how things work?",
        "Have you ever had to navigate a tricky social situation to get what you needed?",
    ],
    "psychopathy": [
        "When someone comes to you with a personal problem, what's your instinct?",
        "How do you react when someone gets really emotional in front of you?",
        "Do you think people are too sensitive about things these days?",
    ],
    "sadism": [
        "Do you ever find yourself enjoying it when an arrogant person gets taken down a peg?",
        "What's your take on reality TV shows where people get eliminated?",
        "How do you feel about harsh roasts or dark humor?",
    ],
    # Emotional Architecture
    "emotional_granularity": [
        "When you're feeling off, can you usually pinpoint exactly what's bothering you?",
        "Do you find it easy to describe your emotions, or is it more like a general 'good' or 'bad'?",
    ],
    "emotional_regulation": [
        "When something really upsets you, what do you do to calm down?",
        "Do you find it easy to control your emotions in stressful situations?",
    ],
    "emotional_volatility": [
        "Would your friends say your moods change quickly, or are you pretty steady?",
        "Have you ever surprised yourself with a sudden mood shift?",
    ],
    "emotional_expressiveness": [
        "Are you the type of person whose face shows exactly what you're feeling?",
        "Do people usually know when something's bothering you, or are you good at hiding it?",
    ],
    "empathy_cognitive": [
        "Are you good at figuring out what someone's really feeling, even when they don't say it?",
        "When you watch a friend making a bad decision, do you understand why they're doing it?",
    ],
    "empathy_affective": [
        "When a friend is going through a tough time, how does it affect you personally?",
        "Do you find other people's emotions are contagious — like if they're sad, you feel sad?",
    ],
    # Social Dynamics
    "attachment_anxiety": [
        "In relationships, do you tend to worry about whether the other person cares as much as you do?",
        "How do you handle it when someone you're close to suddenly goes quiet?",
    ],
    "attachment_avoidance": [
        "Do you need a lot of alone time in relationships, or do you prefer constant closeness?",
        "How do you feel when someone gets really emotionally dependent on you?",
    ],
    "conflict_assertiveness": [
        "When someone says something you disagree with, do you speak up or let it go?",
        "Tell me about the last time you stood your ground in an argument.",
    ],
    "conflict_cooperativeness": [
        "When you have a disagreement with someone, is your first instinct to find a compromise?",
        "How important is it to you to keep the peace?",
    ],
    # Big Five Facets
    "anxiety": [
        "Are you a worrier, or do you tend to take things as they come?",
        "What keeps you up at night?",
    ],
    "trust": [
        "Do you give people the benefit of the doubt, or do they need to earn your trust?",
        "Have you been burned enough times that you're more careful now?",
    ],
    "warmth": [
        "Would you describe yourself as someone who gets close to people quickly?",
        "How do you show people you care about them?",
    ],
    "assertiveness": [
        "Are you comfortable speaking up in meetings, or do you prefer to listen first?",
        "When you want something, how do you go about getting it?",
    ],
    "self_discipline": [
        "How good are you at sticking to routines or habits?",
        "When you set yourself a goal, how often do you follow through?",
    ],
    "order": [
        "Are you the kind of person with lists and systems, or more go-with-the-flow?",
        "How organized would you say your daily life is?",
    ],
    "achievement_striving": [
        "What are you working toward right now?",
        "Are you someone who's always chasing the next thing, or more content with where you are?",
    ],
    "deliberation": [
        "When you have a big decision to make, do you research it carefully or go with your gut?",
        "Have you ever jumped into something without thinking and regretted it?",
    ],
    "gregariousness": [
        "Do you recharge by being around people or by having alone time?",
        "How often do you go out versus staying in?",
    ],
    "fantasy": [
        "Do you have a vivid imagination? Like daydreams or made-up scenarios?",
        "When you're bored, where does your mind wander?",
    ],
    "ideas": [
        "Do you enjoy abstract conversations — like debating ideas just for the sake of it?",
        "What's something you've been curious about lately?",
    ],
    "feelings": [
        "How in touch would you say you are with your emotions?",
        "Do you pay attention to how things make you feel, or do you just push through?",
    ],
    "values_openness": [
        "Are you the kind of person who challenges traditional ways of doing things?",
        "How do you feel about rules and conventions?",
    ],
    # Honesty-Humility
    "sincerity": [
        "Do you find it hard to fake enthusiasm for something?",
        "Would you rather be honest and hurt someone's feelings, or tell them what they want to hear?",
    ],
    "fairness": [
        "How important is playing fair to you, even when no one's watching?",
        "Have you ever been tempted to cut corners, and what did you do?",
    ],
    "humility_hexaco": [
        "Do you think you deserve special treatment, or are you pretty much like everyone else?",
        "How do you feel about people who act like they're better than others?",
    ],
    "modesty": [
        "When you accomplish something great, do you tell people about it?",
        "How do you react when someone compliments you?",
    ],
    # Humor
    "humor_affiliative": [
        "Do you use humor a lot in your daily conversations?",
        "Would your friends say you're the funny one in the group?",
    ],
    "humor_aggressive": [
        "Do you enjoy teasing people, even if it's a bit edgy?",
        "What's your take on roast humor — funny or just mean?",
    ],
    "humor_self_defeating": [
        "Do you tend to make yourself the butt of the joke?",
        "When you mess up, do you make fun of yourself about it?",
    ],
    # Cognitive Style
    "need_for_cognition": [
        "Do you enjoy solving complex problems, or would you rather keep things simple?",
        "What's the last thing you really geeked out about?",
    ],
    "cognitive_flexibility": [
        "How easy is it for you to change your mind when you get new information?",
        "When someone challenges your opinion, what's your first reaction?",
    ],
    "locus_of_control": [
        "Do you feel like you're in control of what happens in your life?",
        "When things go wrong, do you tend to blame yourself or circumstances?",
    ],
    # Values
    "care_harm": [
        "When you see someone suffering, how does it affect you?",
        "Is compassion something you actively practice or more of a natural instinct?",
    ],
    "fairness_justice": [
        "How do you feel about inequality — is it just how the world works, or something that needs fixing?",
        "Tell me about a time you witnessed something unfair and what you did.",
    ],
    "loyalty_group": [
        "How loyal are you to your friend group or team? Like ride-or-die loyal?",
        "What would you do if a close friend did something you disagreed with?",
    ],
    "authority_respect": [
        "How do you feel about rules and authority figures?",
        "Do you respect the chain of command or think people should earn your respect?",
    ],
    # Interpersonal Strategy
    "hot_cold_oscillation": [
        "Do people ever say you're hard to read — warm one moment, distant the next?",
        "How consistent would you say your energy is with people?",
    ],
    "self_mythologizing": [
        "When you tell stories about your life, do you think you tend to make them more dramatic?",
        "Do your friends ever say you exaggerate?",
    ],
    "charm_influence": [
        "Are you good at getting people to go along with your ideas?",
        "How do you usually persuade someone who disagrees with you?",
    ],
    # AGR facets (previously missing)
    "straightforwardness": [
        "Are you someone who says exactly what you think, or do you soften things?",
        "How do you handle giving someone bad news?",
    ],
    "altruism": [
        "When a stranger asks for help, what's your first instinct?",
        "Do you go out of your way to help people, or do you focus on your own stuff?",
    ],
    "compliance": [
        "When someone pushes back on something you want, how do you usually react?",
        "Are you the type to pick your battles, or do you stand firm on most things?",
    ],
    "tender_mindedness": [
        "How do you react when you see someone having a really hard time?",
        "Do you think society should do more to help people who are struggling?",
    ],
    # NEU facets (previously missing)
    "angry_hostility": [
        "What tends to set you off? Like, what really pushes your buttons?",
        "When someone cuts you off in traffic or is rude, how do you react?",
    ],
    "depression": [
        "Do you ever have stretches where everything just feels kind of flat or pointless?",
        "How do you handle those days when motivation is just gone?",
    ],
    "impulsiveness": [
        "Do you ever buy something on impulse and regret it later?",
        "Are you someone who acts first and thinks later, or the opposite?",
    ],
    "self_consciousness": [
        "Do you worry about what other people think of you?",
        "How do you feel when everyone's attention is on you?",
    ],
    "vulnerability": [
        "When things get really stressful, do you feel like you can handle it or does it overwhelm you?",
        "How do you cope when multiple things go wrong at once?",
    ],
    # EXT facets (previously missing)
    "activity_level": [
        "Are you someone who's always on the go, or do you prefer a slower pace?",
        "How do you spend a typical weekend — packed with plans or chill?",
    ],
    "excitement_seeking": [
        "Do you actively look for thrills and new experiences?",
        "What's the most adventurous thing you've done recently?",
    ],
    "positive_emotions": [
        "Would people describe you as someone who's generally upbeat?",
        "How often do you feel genuinely excited about something?",
    ],
    # OPN facets (previously missing)
    "actions": [
        "Do you prefer trying new things or sticking with what works?",
        "When was the last time you did something completely out of your comfort zone?",
    ],
    "aesthetics": [
        "Are you someone who notices beauty in everyday things — art, nature, architecture?",
        "How important is the aesthetic of your surroundings to you?",
    ],
    # CON facets (previously missing)
    "dutifulness": [
        "How seriously do you take your commitments and responsibilities?",
        "If you promised someone you'd do something but a better offer came up, what would you do?",
    ],
    # HON facets (previously missing)
    "greed_avoidance": [
        "How important is money and status to you compared to other things in life?",
        "Would you take a pay cut for a job you found more meaningful?",
    ],
    # COG facets (previously missing)
    "intuitive_vs_analytical": [
        "When you make decisions, do you go more with your gut or do you analyze the options?",
        "Do you trust your instincts, or do you prefer to look at the data first?",
    ],
}


def get_topics_for_traits(
    trait_names: list[str],
    max_per_trait: int = 1,
) -> list[str]:
    """Get natural conversation topics for a list of traits.

    Args:
        trait_names: Trait names to get topics for.
        max_per_trait: Maximum topics per trait.

    Returns:
        List of conversation topics/questions.
    """
    topics = []
    for name in trait_names:
        if name in TRAIT_TOPIC_MAP:
            topics.extend(TRAIT_TOPIC_MAP[name][:max_per_trait])
    return topics
