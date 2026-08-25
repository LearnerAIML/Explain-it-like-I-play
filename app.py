"""
Explain it Like I Play - AI Learning Lab
----------------------------------------
Users pick a favorite video game and a technical/CS topic.
Gemini generates a structured, game-specific learning package.
"""

import json
import os
import re
import time
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

# ---------------------------------------------------------
# 2. SESSION STATE
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
    "theme": "Dark",
    "selected_model": "gemini-3.5-flash"
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = deepcopy(value)


# ---------------------------------------------------------
# 3. PAGE CONFIG & CUSTOM CSS
# ---------------------------------------------------------
st.set_page_config(
    page_title="Explain it Like I Play",
    page_icon="🎮",
    layout="wide",
)

def apply_custom_css(theme):
    """Injects professional gaming/tech UI styling with dynamic theming."""
    
    if theme == "Light":
        bg_color = "#f0f2f6"
        grid_color = "rgba(0, 0, 0, 0.05)"
        card_bg = "rgba(255, 255, 255, 0.85)"
        border_color = "rgba(0, 0, 0, 0.1)"
    else:
        bg_color = "#0e1117"
        grid_color = "rgba(255, 255, 255, 0.04)"
        card_bg = "rgba(14, 17, 23, 0.8)"
        border_color = "rgba(255, 255, 255, 0.05)"

    st.markdown(
        f"""
        <style>
        /* 1. Subtle Tech/Gaming Grid Background */
        .stApp {{
            background-color: {bg_color};
            background-image: 
                linear-gradient({grid_color} 1px, transparent 1px),
                linear-gradient(90deg, {grid_color} 1px, transparent 1px);
            background-size: 30px 30px;
            transition: background-color 0.3s ease;
        }}

        /* 2. Glassmorphism for the main content block */
        .block-container {{
            background: {card_bg} !important;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-radius: 20px;
            border: 1px solid {border_color};
            padding-top: 2rem !important;
            padding-bottom: 3rem !important;
            margin-top: 2rem;
            margin-bottom: 2rem;
            transition: background 0.3s ease;
        }}

        /* 3. Pointer cursor for interactive elements */
        button, a, input, select, textarea, .stSelectbox {{
            cursor: pointer !important;
        }}

        /* 4. Glow effect on Primary Generate Button */
        [data-testid="baseButton-primary"] {{
            background: linear-gradient(135deg, #FF4B4B, #FF8A4B);
            border: none;
            box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4);
            transition: all 0.3s ease;
        }}
        [data-testid="baseButton-primary"]:hover {{
            box-shadow: 0 6px 20px rgba(255, 75, 75, 0.7);
            transform: translateY(-2px);
        }}
        
        /* 5. Sleeker Headers */
        h1, h2, h3 {{
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

apply_custom_css(st.session_state.theme)

# ---------------------------------------------------------
# 4. STATIC DATA
# ---------------------------------------------------------
GAMES = ["Minecraft", "Mario", "Valorant", "Chess", "Other (Custom)"]

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
    "Other (Custom)"
]

DIFFICULTY_LEVELS = {
    1: "Explain like I'm a total beginner (very simple, short sentences).",
    2: "Explain at a casual hobbyist level (some technical words are okay).",
    3: "Explain at a college-student level (assume basic CS/engineering background).",
    4: "Explain at an advanced/interview-prep level (precise, in-depth, still game-themed).",
}

MODEL_OPTIONS = [
    "gemini-3.5-flash",
    "gemini-3.6-flash (might not be available right now due to API constraints)"
]

# ---------------------------------------------------------
# 5. Structured Gemini generation + validation
# ---------------------------------------------------------
def extract_json(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Gemini response did not contain a JSON object.")
    return json.loads(cleaned[start : end + 1])

def validate_package(data: dict) -> bool:
    required = ["explanation", "mapping", "analogy_break", "code_example", "simulation", "quiz", "reverse_challenge"]
    if not isinstance(data, dict) or any(key not in data for key in required):
        return False
    return True

def generate_learning_package(
    game: str,
    topic: str,
    difficulty_instruction: str,
    model_name: str,
    alternative_analogy: bool = False,
) -> dict | None:
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

Your goal is to teach the real technical idea through the user's game knowledge.

DIFFICULTY:
{difficulty_instruction}

CORE RULES:
1. Map important parts of the technical concept to specific, recognizable mechanics from {game}.
2. Keep the explanation compact: about 60–120 words.
3. Explicitly include where the analogy BREAKS or becomes inaccurate.
4. Include a tiny code/data-flow example that connects the game intuition to the real concept.
5. Generate a 2–3 step interactive simulation. Each step must have 2–4 choices and one correct_index.
6. Generate exactly 3 Boss Battle questions. Each needs 3–4 options and one correct_index.
7. Generate a reverse-learning challenge explaining the real concept WITHOUT using the game. Include 3–5 key_points.
8. {mode_instruction}

RETURN JSON ONLY. No markdown fences.
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
        "options": ["string", "string"],
        "correct_index": 0,
        "explanation": "string"
      }}
    ]
  }},
  "quiz": [
    {{
      "question": "string",
      "options": ["string", "string"],
      "correct_index": 0,
      "explanation": "string"
    }}
  ],
  "reverse_challenge": {{
    "prompt": "string",
    "key_points": ["string", "string"]
  }}
}}
"""

    user_prompt = f"Create the complete learning package for '{topic}' using {game}."
    
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt,
    )

    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                user_prompt,
                generation_config={
                    "temperature": 0.7,
                    "response_mime_type": "application/json",
                },
            )

            data = extract_json(response.text)
            if not validate_package(data):
                raise ValueError("Gemini returned invalid JSON schema.")
            return data

        except Exception as exc:
            if attempt == max_retries - 1:
                st.error(f"❌ API not available or model constraint hit. Error details: {str(exc)}")
                return None
            time.sleep(1.5)

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

    choice_key = f"simulation_choice_{st.session_state.current_topic}_{step_index}"
    st.radio(step["question"], step["options"], key=choice_key)

    def handle_check_decision():
        selected_choice = st.session_state[choice_key]
        selected_idx = step["options"].index(selected_choice)
        st.session_state.simulation_feedback = {
            "is_correct": selected_idx == step["correct_index"],
            "text": step["explanation"],
        }

    def handle_next_step():
        st.session_state.simulation_step += 1
        st.session_state.simulation_feedback = None

    def handle_restart_sim():
        st.session_state.simulation_step = 0
        st.session_state.simulation_feedback = None

    st.button(
        "✅ Check Decision",
        key=f"check_simulation_{st.session_state.current_topic}_{step_index}",
        use_container_width=True,
        on_click=handle_check_decision
    )

    feedback = st.session_state.simulation_feedback
    if feedback is not None:
        if feedback["is_correct"]:
            st.success("Correct — that matches the core concept.")
        else:
            st.warning("Not quite — use the consequence in the scenario to reason it out.")
        st.caption(feedback["text"])

        if step_index < len(steps) - 1:
            st.button("➡️ Next Step", key=f"next_simulation_{step_index}", use_container_width=True, on_click=handle_next_step)
        else:
            st.success("🏁 Simulation complete. Now test yourself in the Boss Battle.")
            st.button("🔄 Restart Simulation", key="restart_simulation", use_container_width=True, on_click=handle_restart_sim)

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

    def handle_quiz_submit():
        answers = {}
        for idx in range(min(3, len(quiz))):
            key = f"quiz_{st.session_state.current_topic}_{idx}"
            answers[idx] = st.session_state.get(key)
        st.session_state.quiz_answers = answers
        st.session_state.quiz_submitted = True

    st.button("🏆 Submit Boss Battle", use_container_width=True, on_click=handle_quiz_submit)

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
    
    text_key = f"reverse_answer_{st.session_state.current_topic}"
    st.text_area(challenge["prompt"], key=text_key, height=130)

    def handle_reverse_check():
        st.session_state.reverse_answer = st.session_state.get(text_key, "").strip()
        st.session_state.reverse_checked = True

    st.button("🔍 Self-Check My Explanation", use_container_width=True, on_click=handle_reverse_check)

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
# Top Right Customization Options
top_col1, top_col2, top_col3 = st.columns([2, 1, 1])

with top_col2:
    theme_choice = st.selectbox(
        "🎨 Theme",
        options=["Dark", "Light"],
        index=0 if st.session_state.theme == "Dark" else 1,
        key="theme_selector"
    )
    if theme_choice != st.session_state.theme:
        st.session_state.theme = theme_choice
        st.rerun()

with top_col3:
    model_choice = st.selectbox(
        "⚙️ Model",
        options=MODEL_OPTIONS,
        index=0,
        key="model_selector"
    )

st.title("🎮 Explain it Like I Play")
st.markdown(
    "##### Turn tricky engineering topics into game logic you already understand — then prove you understand the real concept."
)
st.divider()

# Input Setup
left, right = st.columns([1, 1])

with left:
    selected_game_preset = st.selectbox(
        "🕹️ Pick your favorite game",
        options=GAMES,
        index=GAMES.index(st.session_state.last_game) if st.session_state.last_game in GAMES else 0,
    )
    
    if selected_game_preset == "Other (Custom)":
        custom_game = st.text_input("✏️ Enter custom game name", placeholder="e.g. Dark Souls, Stardew Valley...")
    else:
        custom_game = ""

with right:
    topic_preset = st.selectbox(
        "🧠 Pick a preset topic",
        options=PRESET_TOPICS,
    )
    
    if topic_preset == "Other (Custom)":
        custom_topic = st.text_input("✏️ Enter custom technical topic", placeholder="e.g. Dynamic Programming, OAuth...")
    else:
        custom_topic = ""

difficulty = st.slider(
    "🎚️ Explanation difficulty",
    min_value=1,
    max_value=4,
    value=2,
    help="1 = Total beginner  •  4 = Advanced / interview-level",
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
    )

# ---------------------------------------------------------
# 9. HANDLE GENERATION
# ---------------------------------------------------------
request_generation = submitted or alternative_requested

if request_generation:
    final_game = custom_game.strip() if selected_game_preset == "Other (Custom)" else selected_game_preset
    final_topic = custom_topic.strip() if topic_preset == "Other (Custom)" else topic_preset

    if not final_topic or not final_game:
        st.warning("⚠️ Please ensure both a game and a topic are provided before generating.")
    else:
        reset_learning_state()

        # Parse the actual API model name from the UI string
        actual_model = model_choice.split(" ")[0]

        action_label = (
            f"Trying a different {final_game} analogy..."
            if alternative_requested
            else f"Building a {final_game} explanation for '{final_topic}'..."
        )

        with st.spinner(action_label):
            package = generate_learning_package(
                game=final_game,
                topic=final_topic,
                difficulty_instruction=DIFFICULTY_LEVELS[difficulty],
                model_name=actual_model,
                alternative_analogy=alternative_requested,
            )

        if package:
            st.session_state.current_package = package
            st.session_state.current_topic = final_topic
            st.session_state.current_game = final_game
            st.session_state.current_difficulty = difficulty

            st.session_state.total_explanations += 1
            st.session_state.last_game = final_game
            st.session_state.history.append(
                {
                    "Game": final_game,
                    "Topic": final_topic,
                    "Difficulty": difficulty,
                    "Mode": "Alternative analogy" if alternative_requested else "AI Generated",
                }
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