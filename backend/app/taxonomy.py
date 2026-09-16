"""Curated symptom phrase -> specialty taxonomy.

Used by both the fuzzy-match layer (rapidfuzz, in-process) and the embedding
fallback layer (phrases are embedded into the ChromaDB `symptom_taxonomy`
collection). Keep phrases short and colloquial (how a patient would type
them), not clinical terms a patient wouldn't use.
"""

Rule = dict[str, list[str]]

# Each rule fires if the input fuzzy-matches (via partial_ratio) *every* alternative-group it
# lists. A single-item rule ("any" of one group) covers standalone red flags — "seizure" or
# "unconscious" alone is unambiguous. A multi-group rule requires all groups present, for
# symptoms that are only alarming in combination: "chest pain" alone is too common (could be
# a muscle strain) to trigger an ER redirect by itself, but "chest pain" + "can't breathe"
# together is a textbook heart-attack/PE presentation.
EMERGENCY_RULES: list[Rule] = [
    {"unconsciousness": ["unconscious", "not responding", "unresponsive"]},
    {"suicidal": ["suicidal", "want to kill myself", "want to end my life"]},
    {"seizure": ["seizure", "convulsions", "convulsing"]},
    {"bleeding": ["severe bleeding", "heavy bleeding that won't stop"]},
    {"overdose": ["overdose", "took too many pills"]},
    {"allergic reaction": ["severe allergic reaction", "throat closing up", "throat is closing"]},
    {"burns": ["severe burns"]},
    {"coughing/vomiting blood": ["coughing blood", "vomiting blood"]},
    {"stroke signs": ["stroke symptoms", "face drooping", "slurred speech", "sudden numbness one side"]},
    {
        "chest pain": ["chest pain", "chest tightness", "crushing chest pain"],
        "breathing difficulty": ["can't breathe", "cant breathe", "breathless", "shortness of breath"],
    },
]

SYMPTOM_TAXONOMY: dict[str, list[str]] = {
    "Cardiology": [
        "chest pain",
        "chest tightness",
        "heart palpitations",
        "irregular heartbeat",
        "racing heart",
        "shortness of breath on exertion",
        "high blood pressure",
        "swelling in legs and ankles",
        "dizziness when standing up",
        "fainting spells",
        "fatigue with exertion",
        "family history of heart disease",
        "high cholesterol",
        "chest discomfort when climbing stairs",
        "heart murmur",
    ],
    "Dermatology": [
        "skin rash",
        "itchy skin",
        "acne breakout",
        "mole changed shape or color",
        "dry flaky skin",
        "hives",
        "eczema flare up",
        "psoriasis patches",
        "hair loss",
        "excessive sweating",
        "skin discoloration",
        "persistent skin redness",
        "fungal infection on skin",
        "nail discoloration",
        "wart or skin growth",
    ],
    "Pediatrics": [
        "child has a fever",
        "baby won't stop crying",
        "child not eating well",
        "child has an ear infection",
        "vaccination schedule",
        "child has a persistent cough",
        "growth and development check",
        "child has diarrhea",
        "child has a rash",
        "newborn checkup",
        "child is unusually tired",
        "child has trouble sleeping",
        "child complaining of stomach ache",
        "delayed speech in toddler",
        "child has recurring headaches",
    ],
    "Orthopedics": [
        "back pain",
        "knee pain",
        "joint pain",
        "sprained ankle",
        "shoulder pain",
        "fracture or broken bone",
        "arthritis pain",
        "neck stiffness",
        "muscle strain",
        "pain after a fall",
        "limited range of motion",
        "hip pain",
        "sports injury",
        "swelling in a joint",
        "chronic lower back pain",
    ],
    "General Physician": [
        "common cold",
        "fever",
        "sore throat",
        "headache",
        "body aches",
        "fatigue and tiredness",
        "nausea",
        "mild stomach ache",
        "seasonal allergies",
        "cough",
        "general checkup",
        "flu symptoms",
        "mild dizziness",
        "loss of appetite",
        "trouble sleeping",
        "annual physical exam",
    ],
}
