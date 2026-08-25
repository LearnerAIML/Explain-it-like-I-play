"""
Explain it Like I Play - AI Learning Lab
----------------------------------------
Users pick a favorite video game and a technical/CS topic.
Gemini generates a structured, game-specific learning package containing:
- A game-mechanic explanation
- Concept -> game-mechanic mapping
- "Where the analogy breaks" warning
- Game -> real concept -> code bridge
- An interactive step-by-step simulation
- A 3-question Boss Battle
- A reverse-learning challenge

The AI response is requested as strict JSON. A deterministic fallback package
keeps the preset topics usable if Gemini returns invalid JSON or fails.
"""

import json
import os
import re
from copy import deepcopy

import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv


# ---------------------------------------------------------
# 1. SETUP: Load API key and configure Gemini
# ---------------------------------------------------------
load_dotenv()

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except (KeyError, FileNotFoundError):
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    st.error(
        "⚠️ GEMINI_API_KEY not found. Add it to your .env file (local) "
        "or to Streamlit Cloud's Secrets (deployed app)."
    )
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.0-flash"


# ---------------------------------------------------------
# 2. PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(
    page_title="Explain it Like I Play",
    page_icon="🎮",
    layout="wide",
)


# ---------------------------------------------------------
# 3. SESSION STATE
# ---------------------------------------------------------
DEFAULT_STATE = {
    "history": [],
    "total_explanations": 0,
    "last_game": "Minecraft",
    "current_package": None,
    "current_topic": "",
    "current_game": "",
    "current_difficulty": 2,
    "simulation_step": 0,
    "simulation_feedback": None,
    "quiz_submitted": False,
    "quiz_answers": {},
    "reverse_answer": "",
    "reverse_checked": False,
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = deepcopy(value)


# ---------------------------------------------------------
# 4. STATIC DATA
# ---------------------------------------------------------
GAMES = ["Minecraft", "Mario", "Valorant", "Chess"]

GAME_EMOJIS = {
    "Minecraft": "🧱",
    "Mario": "🍄",
    "Valorant": "🎯",
    "Chess": "♟️",
}

PRESET_TOPICS = [
    "Recursion",
    "Load Balancing",
    "Binary Search",
    "TCP/IP Handshake",
    "Caching",
    "Race Conditions",
    "Public Key Encryption",
    "Garbage Collection",
    "Other (type your own)",
]

DIFFICULTY_LEVELS = {
    1: "Explain like I'm a total beginner (very simple, short sentences).",
    2: "Explain at a casual hobbyist level (some technical words are okay).",
    3: "Explain at a college-student level (assume basic CS/engineering background).",
    4: "Explain at an advanced/interview-prep level (precise, in-depth, still game-themed).",
}


# Deterministic fallback content for the 8 preset topics.
# Gemini is still attempted first; these are used only on invalid/failed
# structured generation.
FALLBACK_ANALOGIES = {
    "Minecraft": {
        "Recursion": "Think of a crafting recipe that asks for the same recipe inside itself. A big task keeps breaking into smaller copies of the same task until it reaches a simple craftable item.",
        "Load Balancing": "Imagine several Minecraft farms serving players. A smart helper sends new players to the farm with the least work instead of overloading one farm.",
        "Binary Search": "You have a sorted chest of items. Instead of checking every slot, check the middle, decide which half can contain the item, and repeat.",
        "TCP/IP Handshake": "Before two Minecraft players start a reliable trade, they first agree that the connection is ready, then confirm the other side is ready too.",
        "Caching": "A frequently used item stays in your hotbar or a nearby chest. You grab it quickly instead of walking back to a distant storage room every time.",
        "Race Conditions": "Two players try to take the final diamond from the same chest at the same moment. The result depends on which action is processed first.",
        "Public Key Encryption": "A locked Minecraft chest can have a public lock mechanism everyone can use to send you something, while only your private key can open it.",
        "Garbage Collection": "Unused blocks and items lying around become clutter. A cleanup system finds objects nobody needs anymore and removes them to recover space.",
    },
    "Mario": {
        "Recursion": "A level contains a challenge that leads to a smaller version of the same challenge. Mario keeps solving smaller copies until reaching the simplest case.",
        "Load Balancing": "Several pipes lead to different service areas. Incoming players are routed toward the less busy pipe so one area does not become overloaded.",
        "Binary Search": "You are looking for a hidden power-up in an ordered set of locations. Check the middle location, then discard the half where it cannot be.",
        "TCP/IP Handshake": "Before Mario and the server exchange level data reliably, both sides first establish and confirm that the connection is ready.",
        "Caching": "A power-up you just used often is kept nearby, so you can reuse it immediately instead of fetching it from a far-away location.",
        "Race Conditions": "Two game events try to update Mario's life count at nearly the same time. The final value can depend on which update happens first.",
        "Public Key Encryption": "Anyone can use your public lock to prepare a secret package for you, but only your private key can unlock it.",
        "Garbage Collection": "Old game objects that are no longer reachable can be cleaned up so the running level does not waste memory on things nobody can use.",
    },
    "Valorant": {
        "Recursion": "Think of a strategy that contains a smaller version of the same decision: solve the smaller round situation first, then use that result as part of the larger one.",
        "Load Balancing": "A match coordinator distributes players across available servers so one server does not get flooded while others sit mostly idle.",
        "Binary Search": "Instead of checking every possible angle or location, test the middle of a sorted search space and eliminate half after each result.",
        "TCP/IP Handshake": "Before a reliable data exchange begins, client and server first establish and confirm the connection so both know communication can proceed.",
        "Caching": "A frequently needed ability or piece of game data is kept close to the player so it can be reused quickly instead of being fetched again.",
        "Race Conditions": "Two agents attempt to trigger the same shared event nearly simultaneously. Which update wins can change the final state.",
        "Public Key Encryption": "Your public key is like a lock teammates can use to secure a message for you, while the matching private key is what lets you open it.",
        "Garbage Collection": "Temporary game objects that are no longer needed are detected and removed so memory stays available for active objects.",
    },
    "Chess": {
        "Recursion": "A position contains a smaller decision tree of the same problem. Analyze a move, then recursively analyze the resulting position until a base position is reached.",
        "Load Balancing": "Imagine several analysis boards handling candidate variations. New positions are assigned to the less busy board so work is distributed efficiently.",
        "Binary Search": "A sorted set of candidate moves can be narrowed by checking a middle candidate and discarding the impossible half after each result.",
        "TCP/IP Handshake": "Before two players exchange a reliable game state, both sides establish that communication is available and acknowledge the setup.",
        "Caching": "Keep results for positions you have already analyzed. When the same position appears again, reuse the stored answer instead of calculating it from scratch.",
        "Race Conditions": "Two simultaneous updates to a shared game state can conflict, and the final result depends on ordering unless the update is coordinated.",
        "Public Key Encryption": "A public key lets anyone encrypt a message intended for you, while only your private key can decrypt it.",
        "Garbage Collection": "Analysis may create many temporary position objects. Once nothing references them, a cleanup process can reclaim their memory.",
    },
}

FALLBACK_BREAKS = {
    "Recursion": "The game analogy shows repeated self-similar work, but real recursion is implemented with function calls and a call stack.",
    "Load Balancing": "Game servers are simplified here; real load balancers use health checks, routing algorithms, capacity, and sometimes session-aware rules.",
    "Binary Search": "Binary search only works directly when the search space is ordered and the comparison lets you discard half of it.",
    "TCP/IP Handshake": "The analogy simplifies networking. TCP setup, packet delivery, retransmission, and IP routing are separate mechanisms.",
    "Caching": "A cache is not just 'nearby storage': it also involves freshness, eviction policies, cache keys, and consistency trade-offs.",
    "Race Conditions": "A race condition is not merely two actions being simultaneous; it occurs when timing/order affects an unsafe shared state.",
    "Public Key Encryption": "The lock analogy hides the cryptographic math. Public-key encryption relies on computationally hard mathematical problems and key pairs.",
    "Garbage Collection": "Real garbage collectors use reachability analysis and runtime-specific algorithms such as tracing, generational collection, or reference counting.",
}

FALLBACK_CODE = {
    "Recursion": {
        "language": "python",
        "code": "def countdown(n):\n    if n == 0:\n        return\n    print(n)\n    countdown(n - 1)",
        "explanation": "The base case stops the chain; the recursive call solves a smaller version of the same problem.",
    },
    "Load Balancing": {
        "language": "python",
        "code": "servers = [3, 1, 5]\nleast_busy = min(range(len(servers)), key=servers.__getitem__)",
        "explanation": "A simple policy sends new work to the currently least-loaded server.",
    },
    "Binary Search": {
        "language": "python",
        "code": "def binary_search(a, x):\n    lo, hi = 0, len(a) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if a[mid] == x: return mid\n        if a[mid] < x: lo = mid + 1\n        else: hi = mid - 1\n    return -1",
        "explanation": "Each comparison removes half of the remaining ordered search space.",
    },
    "TCP/IP Handshake": {
        "language": "text",
        "code": "Client  -> SYN      -> Server\nClient  <- SYN-ACK  <- Server\nClient  -> ACK      -> Server",
        "explanation": "The three-way handshake establishes the TCP connection before normal data transfer.",
    },
    "Caching": {
        "language": "python",
        "code": "cache = {}\n\ndef get_user(uid):\n    if uid in cache:\n        return cache[uid]\n    value = load_from_db(uid)\n    cache[uid] = value\n    return value",
        "explanation": "Return a previously stored value when possible; otherwise fetch and cache it.",
    },
    "Race Conditions": {
        "language": "python",
        "code": "with lock:\n    balance = balance - amount",
        "explanation": "Synchronizing the critical section prevents unsafe interleaving of shared-state updates.",
    },
    "Public Key Encryption": {
        "language": "text",
        "code": "ciphertext = encrypt(public_key, message)\nmessage = decrypt(private_key, ciphertext)",
        "explanation": "The public key encrypts; the corresponding private key decrypts.",
    },
    "Garbage Collection": {
        "language": "python",
        "code": "objects = []\nobjects.append(build_object())\ndel objects[0]  # object may become unreachable",
        "explanation": "Once an object is unreachable, a garbage collector can eventually reclaim its memory.",
    },
}

FALLBACK_KEY_POINTS = {
    "Recursion": ["A base case stops the recursion.", "Each call works on a smaller instance.", "The call stack stores active calls."],
    "Load Balancing": ["Requests are distributed across resources.", "The goal is to avoid overload.", "Strategies can consider current load and health."],
    "Binary Search": ["The data must be ordered.", "Each comparison can discard half the search space.", "Time complexity is O(log n)."],
    "TCP/IP Handshake": ["TCP establishes a connection before reliable transfer.", "The classic setup uses SYN, SYN-ACK, ACK.", "IP routing is separate from TCP reliability."],
    "Caching": ["Caches store reusable results.", "A cache improves latency and can reduce backend work.", "Freshness and eviction are important trade-offs."],
    "Race Conditions": ["Shared state is involved.", "Timing/order changes the result.", "Synchronization can prevent unsafe interleavings."],
    "Public Key Encryption": ["There is a public/private key pair.", "The public key can be shared.", "The private key must remain secret."],
    "Garbage Collection": ["Unreachable objects can be reclaimed.", "The runtime manages memory automatically.", "Collection has performance trade-offs."],
}

TOPIC_SIMULATION = {
    "Recursion": {
        "title": "🧱 Recursive Crafting",
        "steps": [
            {
                "scenario": "A huge build requires the same smaller structure again and again. Your crafting table asks for a smaller copy of the same recipe.",
                "question": "What should the process do next?",
                "options": ["Keep creating smaller copies until the recipe is simplest", "Repeat the largest recipe forever", "Skip the smaller recipe"],
                "correct_index": 0,
                "explanation": "A recursive algorithm repeatedly solves a smaller version of the same problem until it reaches a base case.",
            },
            {
                "scenario": "You reach the smallest craftable item.",
                "question": "What is this condition called in recursion?",
                "options": ["Load balancer", "Base case", "Cache miss"],
                "correct_index": 1,
                "explanation": "The base case stops further recursive calls.",
            },
        ],
    },
    "Load Balancing": {
        "title": "⚙️ Server Village",
        "steps": [
            {
                "scenario": "Three Minecraft servers currently have 8, 2, and 6 active players.",
                "question": "Where should the next player preferably go?",
                "options": ["The server with 8 players", "The server with 2 players", "Always server 1"],
                "correct_index": 1,
                "explanation": "A simple least-load strategy sends new work to the least busy healthy server.",
            },
            {
                "scenario": "Server 2 becomes unhealthy.",
                "question": "What should a real load balancer do?",
                "options": ["Continue sending traffic to it", "Detect the failure and route elsewhere", "Stop the whole internet"],
                "correct_index": 1,
                "explanation": "Health checks help prevent traffic being sent to unavailable resources.",
            },
        ],
    },
    "Binary Search": {
        "title": "🔎 Search the Sorted Chest",
        "steps": [
            {
                "scenario": "Your chest slots contain sorted item IDs from 1 to 100. You need item 73.",
                "question": "What is the best first move?",
                "options": ["Check slot 1", "Check the middle", "Check every slot"],
                "correct_index": 1,
                "explanation": "Binary search starts near the middle so half the remaining search space can be discarded.",
            },
            {
                "scenario": "The middle value is 50 and you need 73.",
                "question": "Which half can be discarded?",
                "options": ["Values below 50", "Values above 50", "Neither"],
                "correct_index": 0,
                "explanation": "Because the collection is sorted, all smaller values can be eliminated.",
            },
        ],
    },
    "TCP/IP Handshake": {
        "title": "🤝 Establish the Connection",
        "steps": [
            {
                "scenario": "Your client wants a reliable TCP connection to a server.",
                "question": "What happens first in the classic setup?",
                "options": ["SYN is sent", "The connection immediately closes", "The application skips networking"],
                "correct_index": 0,
                "explanation": "The client begins the classic TCP three-way handshake with SYN.",
            },
            {
                "scenario": "The server replies with SYN-ACK.",
                "question": "What completes the classic handshake?",
                "options": ["Another SYN from the server", "ACK from the client", "A DNS cache clear"],
                "correct_index": 1,
                "explanation": "The client sends ACK, completing the three-way handshake.",
            },
        ],
    },
    "Caching": {
        "title": "📦 Keep It Nearby",
        "steps": [
            {
                "scenario": "A player repeatedly requests the same item data.",
                "question": "What should a cache do?",
                "options": ["Store a reusable copy", "Delete the database", "Randomly change the result"],
                "correct_index": 0,
                "explanation": "Caching keeps reusable results closer to the requester.",
            },
            {
                "scenario": "The cached data is old.",
                "question": "What real cache concern does this show?",
                "options": ["Freshness/invalidity", "Recursion", "Binary search"],
                "correct_index": 0,
                "explanation": "Caches trade speed for possible staleness, so freshness policies matter.",
            },
        ],
    },
    "Race Conditions": {
        "title": "⚔️ Last Diamond Race",
        "steps": [
            {
                "scenario": "Two players try to take the final diamond from the same shared chest.",
                "question": "Why can the final state be unpredictable?",
                "options": ["The operation order matters", "Diamonds disable networking", "The chest is always copied"],
                "correct_index": 0,
                "explanation": "When unsynchronized shared updates interleave, timing/order can change the result.",
            },
            {
                "scenario": "The server puts a lock around the critical operation.",
                "question": "What is the goal?",
                "options": ["Allow unsafe interleaving", "Coordinate access to shared state", "Make the operation recursive"],
                "correct_index": 1,
                "explanation": "Synchronization prevents conflicting updates from interleaving unsafely.",
            },
        ],
    },
    "Public Key Encryption": {
        "title": "🔐 Send a Locked Package",
        "steps": [
            {
                "scenario": "Anyone needs to send you a secret message.",
                "question": "Which key should they use to encrypt it?",
                "options": ["Your public key", "Your private key", "A random key nobody knows"],
                "correct_index": 0,
                "explanation": "The public key is shareable and can be used to encrypt a message intended for the key owner.",
            },
            {
                "scenario": "You receive the encrypted package.",
                "question": "Which key should decrypt it in this simplified model?",
                "options": ["Your public key", "Your private key", "The sender's username"],
                "correct_index": 1,
                "explanation": "The matching private key is kept secret and is used for decryption in this simplified analogy.",
            },
        ],
    },
    "Garbage Collection": {
        "title": "🧹 Clean the Unused Area",
        "steps": [
            {
                "scenario": "A game object is no longer reachable by anything in the running program.",
                "question": "What can the runtime eventually do?",
                "options": ["Reclaim its memory", "Make it mandatory to keep forever", "Turn it into a network packet"],
                "correct_index": 0,
                "explanation": "Garbage collection reclaims memory occupied by unreachable objects.",
            },
            {
                "scenario": "Many objects are still reachable.",
                "question": "Should the collector remove them just because they exist?",
                "options": ["Yes, always", "No, reachability matters", "Only if they are colorful"],
                "correct_index": 1,
                "explanation": "Reachable objects may still be needed and should not be reclaimed.",
            },
        ],
    },
}

FALLBACK_QUIZ = {
    topic: [
        {
            "question": f"Which statement is most accurate about {topic}?",
            "options": [
                FALLBACK_KEY_POINTS[topic][0],
                "It works only because of a video game's rules.",
                "It has no relationship to real software systems.",
                "It always requires exactly one fixed implementation.",
            ],
            "correct_index": 0,
            "explanation": FALLBACK_KEY_POINTS[topic][0],
        },
        {
            "question": f"What is the key lesson when learning {topic}?",
            "options": [
                FALLBACK_KEY_POINTS[topic][1],
                "Ignore edge cases completely.",
                "Replace the technical idea with the analogy.",
                "Assume every system implements it identically.",
            ],
            "correct_index": 0,
            "explanation": FALLBACK_KEY_POINTS[topic][1],
        },
        {
            "question": f"Which statement helps avoid a common misunderstanding of {topic}?",
            "options": [
                FALLBACK_BREAKS[topic],
                "The game analogy is literally identical to production systems.",
                "The analogy removes every implementation detail.",
                "No assumptions are needed.",
            ],
            "correct_index": 0,
            "explanation": FALLBACK_BREAKS[topic],
        },
    ]
    for topic in FALLBACK_KEY_POINTS
}


# ---------------------------------------------------------
# 5. Structured Gemini generation + validation
# ---------------------------------------------------------
def extract_json(text: str) -> dict:
    """Extract JSON even if Gemini wraps it in a markdown code fence."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Gemini response did not contain a JSON object.")
    return json.loads(cleaned[start : end + 1])


def validate_package(data: dict) -> bool:
    """Strictly validate the minimum UI contract before rendering."""
    required = ["explanation", "mapping", "analogy_break", "code_example", "simulation", "quiz", "reverse_challenge"]
    if not isinstance(data, dict) or any(key not in data for key in required):
        return False

    if not isinstance(data["explanation"], str) or not data["explanation"].strip():
        return False
    if not isinstance(data["mapping"], list) or not data["mapping"]:
        return False
    if not isinstance(data["analogy_break"], str):
        return False

    code = data["code_example"]
    if not isinstance(code, dict) or not all(k in code for k in ["language", "code", "explanation"]):
        return False

    simulation = data["simulation"]
    if not isinstance(simulation, dict) or "title" not in simulation or "steps" not in simulation:
        return False
    if not isinstance(simulation["steps"], list) or not simulation["steps"]:
        return False

    if not isinstance(data["quiz"], list) or len(data["quiz"]) < 3:
        return False

    for question in data["quiz"] + simulation["steps"]:
        if not isinstance(question, dict):
            return False
        if not all(k in question for k in ["question", "options", "correct_index", "explanation"]):
            # Simulation uses "scenario" as well; question itself is still required.
            return False
        if not isinstance(question["options"], list) or len(question["options"]) < 2:
            return False
        if not isinstance(question["correct_index"], int):
            return False
        if not 0 <= question["correct_index"] < len(question["options"]):
            return False

    reverse = data["reverse_challenge"]
    if not isinstance(reverse, dict) or not all(k in reverse for k in ["prompt", "key_points"]):
        return False
    if not isinstance(reverse["key_points"], list) or not reverse["key_points"]:
        return False

    return True


def build_fallback_package(game: str, topic: str) -> dict:
    """Create a deterministic package when live JSON generation is unavailable."""
    if topic in FALLBACK_ANALOGIES.get(game, {}):
        analogy = FALLBACK_ANALOGIES[game][topic]
    else:
        analogy = (
            f"Use {game} as the mental model: map the main moving parts of "
            f"{topic} to concrete game mechanics, then track what changes when "
            "one part fails or scales."
        )

    if topic in FALLBACK_CODE:
        code_example = FALLBACK_CODE[topic]
        key_points = FALLBACK_KEY_POINTS[topic]
        simulation = deepcopy(TOPIC_SIMULATION[topic])
        quiz = deepcopy(FALLBACK_QUIZ[topic])
        analogy_break = FALLBACK_BREAKS[topic]
    else:
        code_example = {
            "language": "python",
            "code": "# Translate the core idea into a small function or data flow here.",
            "explanation": "A concrete code example can be generated when Gemini is available.",
        }
        key_points = [
            "Identify the inputs and outputs.",
            "Track the main state changes.",
            "Connect the analogy back to the real implementation.",
        ]
        simulation = {
            "title": "🎮 Concept Simulation",
            "steps": [
                {
                    "scenario": f"Imagine the main actors in {topic} as objects inside {game}.",
                    "question": "What should you do first when solving a new technical problem?",
                    "options": ["Identify the inputs, state, and goal", "Ignore the constraints", "Guess without checking"],
                    "correct_index": 0,
                    "explanation": "Understanding inputs, state, and goals is a reliable starting point.",
                },
                {
                    "scenario": f"Now one part of the {game} scenario changes unexpectedly.",
                    "question": "What is the best next step?",
                    "options": ["Reason about the changed state", "Pretend nothing changed", "Delete all context"],
                    "correct_index": 0,
                    "explanation": "Technical reasoning depends on tracking state and consequences.",
                },
            ],
        }
        quiz = [
            {
                "question": f"What should you verify first when learning {topic}?",
                "options": key_points + ["That the analogy sounds cool."],
                "correct_index": 0,
                "explanation": key_points[0],
            },
            {
                "question": f"Which approach is safest when using a game analogy for {topic}?",
                "options": [
                    "Use the analogy to build intuition, then return to the real concept.",
                    "Treat the analogy as the exact implementation.",
                    "Ignore technical definitions entirely.",
                    "Use unrelated game mechanics.",
                ],
                "correct_index": 0,
                "explanation": "Analogies are for intuition; the real technical model still matters.",
            },
            {
                "question": f"What is a common mistake when learning {topic} through an analogy?",
                "options": [
                    "Assuming every part of the analogy maps perfectly to reality.",
                    "Checking the real concept afterward.",
                    "Testing yourself after the explanation.",
                    "Asking for an alternative analogy.",
                ],
                "correct_index": 0,
                "explanation": "Analogies simplify reality and can hide important differences.",
            },
        ]
        analogy_break = (
            "This is only an intuition aid. Real implementations can differ substantially "
            "in algorithms, constraints, failure modes, and performance."
        )

    return {
        "explanation": analogy,
        "mapping": [
            {
                "concept_part": topic,
                "game_mechanic": f"{game} mechanic used as the main mental model",
                "why": "The mechanic gives a familiar mental model for tracking the technical idea.",
            },
            {
                "concept_part": "System behavior",
                "game_mechanic": "Cause-and-effect inside the game",
                "why": "Changes in the game state make technical consequences easier to visualize.",
            },
        ],
        "analogy_break": analogy_break,
        "code_example": code_example,
        "simulation": simulation,
        "quiz": quiz,
        "reverse_challenge": {
            "prompt": f"Explain {topic} in 2–4 sentences without mentioning {game} or any game mechanics.",
            "key_points": key_points,
        },
    }


def generate_learning_package(
    game: str,
    topic: str,
    difficulty_instruction: str,
    alternative_analogy: bool = False,
) -> dict:
    """
    One main Gemini call returns a strict JSON learning package.
    If anything fails, use a deterministic fallback.
    """
    mode_instruction = (
        "Try a DIFFERENT game mechanic than the most obvious analogy. "
        "Make the alternative concrete and still technically correct."
        if alternative_analogy
        else "Use the clearest concrete mechanics from the chosen game."
    )

    system_prompt = f"""
You are "GameSensei", an AI tutor.
The chosen game is: {game}
The technical topic is: {topic}

Your goal is to teach the real technical idea through the user's game knowledge,
not to replace the real concept with a misleading analogy.

DIFFICULTY:
{difficulty_instruction}

CORE RULES:
1. Map important parts of the technical concept to specific, recognizable mechanics,
   items, rules, characters, or systems from {game}.
2. Keep the explanation compact: about 60–120 words.
3. Explicitly include where the analogy BREAKS or becomes inaccurate.
4. Include a tiny code/data-flow example that connects the game intuition to the real concept.
5. Generate a 2–3 step interactive simulation. Each step must have 2–4 choices and one correct_index.
6. Generate exactly 3 Boss Battle questions. Each needs 3–4 options and one correct_index.
7. Generate a reverse-learning challenge that asks the learner to explain the real concept
   WITHOUT using the game analogy. Include 3–5 key_points for self-checking.
8. Keep every analogy technically responsible. Do not claim the game mechanic is literally
   how the real technology works.
9. {mode_instruction}

RETURN JSON ONLY. No markdown fences, no commentary, no extra keys are needed.
JSON schema:
{{
  "explanation": "string",
  "mapping": [
    {{"concept_part": "string", "game_mechanic": "string", "why": "string"}}
  ],
  "analogy_break": "string",
  "code_example": {{
    "language": "string",
    "code": "string",
    "explanation": "string"
  }},
  "simulation": {{
    "title": "string",
    "steps": [
      {{
        "scenario": "string",
        "question": "string",
        "options": ["string", "string", "string"],
        "correct_index": 0,
        "explanation": "string"
      }}
    ]
  }},
  "quiz": [
    {{
      "question": "string",
      "options": ["string", "string", "string"],
      "correct_index": 0,
      "explanation": "string"
    }}
  ],
  "reverse_challenge": {{
    "prompt": "string",
    "key_points": ["string", "string", "string"]
  }}
}}
"""

    user_prompt = (
        f"Create the complete learning package for '{topic}' using {game}. "
        "The analogy should match the game the learner actually selected."
    )

    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=system_prompt,
        )

        response = model.generate_content(
            user_prompt,
            generation_config={
                "temperature": 0.7,
                "response_mime_type": "application/json",
            },
        )

        data = extract_json(response.text)
        if not validate_package(data):
            raise ValueError("Gemini returned JSON that did not match the learning-package schema.")
        return data

    except Exception as exc:
        # Keep the app usable and surface a clear reason in the UI.
        st.session_state["generation_fallback_reason"] = str(exc)
        return build_fallback_package(game, topic)


# ---------------------------------------------------------
# 6. UI HELPERS
# ---------------------------------------------------------
def reset_learning_state():
    st.session_state.simulation_step = 0
    st.session_state.simulation_feedback = None
    st.session_state.quiz_submitted = False
    st.session_state.quiz_answers = {}
    st.session_state.reverse_answer = ""
    st.session_state.reverse_checked = False


def render_mapping(mapping):
    st.subheader("🧩 Concept → Game Mechanics")
    for item in mapping:
        with st.container(border=True):
            st.markdown(f"**{item['concept_part']}** → 🎮 **{item['game_mechanic']}**")
            st.caption(item["why"])


def render_simulation(simulation):
    st.subheader("🎮 Interactive Simulation")
    st.caption("Make decisions one step at a time. The simulation uses the generated scenario, not a static paragraph.")

    steps = simulation["steps"]
    step_index = st.session_state.simulation_step
    step_index = min(step_index, len(steps) - 1)
    step = steps[step_index]

    st.markdown(f"### {simulation['title']}")
    st.info(f"**Scenario:** {step.get('scenario', 'You are now inside the scenario.')}")

    choice = st.radio(
        step["question"],
        step["options"],
        key=f"simulation_choice_{st.session_state.current_topic}_{step_index}",
    )

    if st.button(
        "✅ Check Decision",
        key=f"check_simulation_{st.session_state.current_topic}_{step_index}",
        use_container_width=True,
    ):
        selected_index = step["options"].index(choice)
        is_correct = selected_index == step["correct_index"]
        st.session_state.simulation_feedback = {
            "is_correct": is_correct,
            "text": step["explanation"],
        }

    feedback = st.session_state.simulation_feedback
    if feedback is not None:
        if feedback["is_correct"]:
            st.success("Correct — that matches the core concept.")
        else:
            st.warning("Not quite — use the consequence in the scenario to reason it out.")
        st.caption(feedback["text"])

        if step_index < len(steps) - 1:
            if st.button("➡️ Next Step", key=f"next_simulation_{step_index}", use_container_width=True):
                st.session_state.simulation_step += 1
                st.session_state.simulation_feedback = None
                st.rerun()
        else:
            st.success("🏁 Simulation complete. Now test yourself in the Boss Battle.")
            if st.button("🔄 Restart Simulation", key="restart_simulation", use_container_width=True):
                st.session_state.simulation_step = 0
                st.session_state.simulation_feedback = None
                st.rerun()


def render_quiz(quiz):
    st.subheader("⚔️ Boss Battle")
    st.caption("Answer all 3 questions, then submit once to see your score.")

    for i, question in enumerate(quiz[:3]):
        st.markdown(f"**Boss Question {i + 1}:** {question['question']}")
        st.radio(
            "Choose one:",
            question["options"],
            key=f"quiz_{st.session_state.current_topic}_{i}",
            index=None,
            label_visibility="collapsed",
        )

    if st.button("🏆 Submit Boss Battle", use_container_width=True):
        answers = {}
        for i, question in enumerate(quiz[:3]):
            key = f"quiz_{st.session_state.current_topic}_{i}"
            selected = st.session_state.get(key)
            answers[i] = selected
        st.session_state.quiz_answers = answers
        st.session_state.quiz_submitted = True

    if st.session_state.quiz_submitted:
        score = 0
        for i, question in enumerate(quiz[:3]):
            selected = st.session_state.quiz_answers.get(i)
            if selected is not None:
                selected_index = question["options"].index(selected)
                if selected_index == question["correct_index"]:
                    score += 1

        st.metric("Boss Battle Score", f"{score}/3")

        for i, question in enumerate(quiz[:3]):
            selected = st.session_state.quiz_answers.get(i)
            if selected is None:
                st.info(f"Question {i + 1}: Not answered.")
                continue

            selected_index = question["options"].index(selected)
            if selected_index == question["correct_index"]:
                st.success(f"Q{i + 1}: Correct — {question['explanation']}")
            else:
                correct = question["options"][question["correct_index"]]
                st.error(f"Q{i + 1}: Correct answer: {correct}. {question['explanation']}")


def render_reverse_learning(challenge):
    st.subheader("🧠 Learn It Without the Game")
    st.caption("This checks whether you understood the real concept rather than only memorizing the analogy.")

    answer = st.text_area(
        challenge["prompt"],
        key=f"reverse_answer_{st.session_state.current_topic}",
        height=130,
    )

    if st.button("🔍 Self-Check My Explanation", use_container_width=True):
        st.session_state.reverse_answer = answer.strip()
        st.session_state.reverse_checked = True

    if st.session_state.reverse_checked:
        if not st.session_state.reverse_answer:
            st.warning("Write a short explanation first.")
            return

        st.markdown("**Key points your explanation should cover:**")
        for point in challenge["key_points"]:
            st.write(f"• {point}")

        st.info(
            "Compare your answer with these points. This is a structured self-check, "
            "not a claim that keyword matching proves mastery."
        )


def render_package(package, game, topic):
    st.success("Done! Your learning package is ready 👇")
    st.markdown("---")
    st.markdown(
        f"### {GAME_EMOJIS.get(game, '🎮')} {topic}, explained through {game}"
    )

    tabs = st.tabs([
        "🎮 Explanation",
        "🕹️ Simulation",
        "⚔️ Boss Battle",
        "🧠 Real Understanding",
    ])

    with tabs[0]:
        st.markdown(package["explanation"])
        render_mapping(package["mapping"])

        with st.expander("⚠️ Where the analogy breaks", expanded=True):
            st.write(package["analogy_break"])

        st.subheader("💻 Game → Concept → Code")
        st.code(package["code_example"]["code"], language=package["code_example"]["language"])
        st.caption(package["code_example"]["explanation"])

    with tabs[1]:
        render_simulation(package["simulation"])

    with tabs[2]:
        render_quiz(package["quiz"])

    with tabs[3]:
        render_reverse_learning(package["reverse_challenge"])


# ---------------------------------------------------------
# 7. SIDEBAR: stats + history
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] [data-testid="stMetricValue"] {
        font-size: 1.1rem;
        white-space: normal;
        word-break: break-word;
    }
    [data-testid="stSidebar"] [data-testid="stMetricLabel"] {
        font-size: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("📊 Session Stats")

    st.metric(
        label="Explanations Generated",
        value=st.session_state.total_explanations,
        delta=1 if st.session_state.total_explanations > 0 else None,
    )
    st.metric(
        label="Last Game Used",
        value=f"{GAME_EMOJIS.get(st.session_state.last_game, '')} {st.session_state.last_game}",
    )

    st.divider()
    st.subheader("🕘 History")

    if st.session_state.history:
        st.data_editor(
            st.session_state.history,
            use_container_width=True,
            hide_index=True,
            disabled=True,
            key="history_editor",
        )

        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.history = []
            st.session_state.total_explanations = 0
            st.session_state.current_package = None
            st.rerun()
    else:
        st.caption("No explanations yet. Generate one to see it here!")


# ---------------------------------------------------------
# 8. MAIN PAGE
# ---------------------------------------------------------
st.title("🎮 Explain it Like I Play")
st.markdown(
    "##### Turn tricky engineering topics into game logic you already understand — then prove you understand the real concept."
)
st.divider()

left, right = st.columns([1, 1])

with left:
    selected_game = st.selectbox(
        "🕹️ Pick your favorite game",
        options=GAMES,
        index=GAMES.index(st.session_state.last_game)
        if st.session_state.last_game in GAMES
        else 0,
    )

with right:
    topic_choice = st.selectbox(
        "🧠 Pick a topic (or choose 'Other')",
        options=PRESET_TOPICS,
    )

custom_topic = ""
if topic_choice == "Other (type your own)":
    custom_topic = st.text_input(
        "✏️ Type your own engineering/CS topic",
        placeholder="e.g. Dynamic Programming, Load Balancers, OAuth...",
    )

difficulty = st.slider(
    "🎚️ Explanation difficulty",
    min_value=1,
    max_value=4,
    value=2,
    help="1 = Total beginner  •  4 = Advanced / interview-level",
)
st.caption(
    f"Selected level: **{difficulty}** — "
    f"{DIFFICULTY_LEVELS[difficulty].split('(')[0].strip()}"
)

generate_col, alternative_col = st.columns([3, 1])

with generate_col:
    submitted = st.button(
        "✨ Generate Learning Package",
        use_container_width=True,
        type="primary",
    )

with alternative_col:
    alternative_requested = st.button(
        "🔄 New Analogy",
        use_container_width=True,
        help="Regenerate using a different game mechanic.",
    )


# ---------------------------------------------------------
# 9. HANDLE GENERATION
# ---------------------------------------------------------
request_generation = submitted or alternative_requested

if request_generation:
    final_topic = (
        custom_topic.strip()
        if topic_choice == "Other (type your own)"
        else topic_choice
    )

    if not final_topic:
        st.warning("⚠️ Please enter a topic before generating an explanation.")
    else:
        # Reset any old interactive state before creating a new package.
        reset_learning_state()

        action_label = (
            f"Trying a different {selected_game} analogy..."
            if alternative_requested
            else f"Building a {selected_game} explanation for '{final_topic}'..."
        )

        # The old wording was: "Asking Chess to explain 'Bios'..."
        # This phrasing is grammatically wrong because the game is the analogy,
        # not the entity doing the explaining.
        with st.spinner(action_label):
            package = generate_learning_package(
                game=selected_game,
                topic=final_topic,
                difficulty_instruction=DIFFICULTY_LEVELS[difficulty],
                alternative_analogy=alternative_requested,
            )

        st.session_state.current_package = package
        st.session_state.current_topic = final_topic
        st.session_state.current_game = selected_game
        st.session_state.current_difficulty = difficulty

        st.session_state.total_explanations += 1
        st.session_state.last_game = selected_game
        st.session_state.history.append(
            {
                "Game": selected_game,
                "Topic": final_topic,
                "Difficulty": difficulty,
                "Mode": "Alternative analogy" if alternative_requested else "AI + fallback",
            }
        )

        fallback_reason = st.session_state.pop("generation_fallback_reason", None)
        if fallback_reason:
            st.info(
                "ℹ️ Gemini's structured response was unavailable, so the app used its "
                "built-in reliable fallback for this topic."
            )


# ---------------------------------------------------------
# 10. RENDER CURRENT PACKAGE
# ---------------------------------------------------------
if st.session_state.current_package:
    render_package(
        st.session_state.current_package,
        st.session_state.current_game,
        st.session_state.current_topic,
    )


# ---------------------------------------------------------
# 11. FOOTER
# ---------------------------------------------------------
st.divider()
st.caption("Built with Streamlit + Google Gemini API | Explain it Like I Play © 2026")
st.markdown(
    "<p style='text-align: center; color: gray;'>Made with ❤️ by Varad</p>",
    unsafe_allow_html=True,
)
