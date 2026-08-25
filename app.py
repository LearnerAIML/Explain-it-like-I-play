"""
Explain it Like I Play - AI Dictionary
----------------------------------------
Users pick a favorite video game and type in a complex engineering/CS topic.
The AI explains that topic ENTIRELY using the mechanics of that specific game.

Built with: Streamlit + Google Gemini API
Author: Varad
"""

import os
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

# ---------------------------------------------------------
# 1. SETUP: Load API key and configure Gemini
# ---------------------------------------------------------
load_dotenv()  # reads variables from .env file into the environment (local dev)

# Works both locally (.env file) and on Streamlit Cloud (st.secrets).
# st.secrets is checked first since that's how Streamlit Cloud stores it.
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

# The model we use for generating explanations
MODEL_NAME = "gemini-3.5-flash"


# ---------------------------------------------------------
# 2. PAGE CONFIG (must be the first Streamlit command)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Explain it Like I Play",
    page_icon="🎮",
    layout="wide",
)


# ---------------------------------------------------------
# 3. SESSION STATE: keeps data alive between reruns
# ---------------------------------------------------------
# st.session_state prevents "memory loss" every time the app reruns.
if "history" not in st.session_state:
    st.session_state.history = []  # stores past explanations (list of dicts)

if "total_explanations" not in st.session_state:
    st.session_state.total_explanations = 0

if "last_game" not in st.session_state:
    st.session_state.last_game = "Minecraft"


# ---------------------------------------------------------
# 4. STATIC DATA: games and preset topics
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


# ---------------------------------------------------------
# 5. FUNCTION: Build the prompt and call Gemini
# ---------------------------------------------------------
def generate_explanation(game: str, topic: str, difficulty_instruction: str) -> str:
    """
    Sends a request to the Gemini API asking it to explain `topic`
    using only the mechanics/world of `game`.
    """
    system_prompt = f"""
    You are "GameSensei", an AI tutor that explains complex engineering and
    computer science topics ENTIRELY through the mechanics, items, characters,
    or rules of the video game: {game}.

    Rules you must follow:
    1. Do NOT give a generic textbook definition. Every explanation must be
       wrapped in {game}'s world, characters, items, or mechanics.
    2. Draw a clear analogy: map each part of the technical concept to a
       specific in-game mechanic (be concrete, not vague).
    3. {difficulty_instruction}
    4. Keep the tone fun and engaging, like a knowledgeable friend explaining
       it over a gaming session.
    5. STRICT LENGTH LIMIT: Keep the ENTIRE explanation between 50 and 100
       words. Do not go over 100 words under any circumstance — be concise
       and punchy, not exhaustive.
    6. Use plenty of relevant emojis throughout the explanation (not just at
       the start) to make it feel fun and interactive.
    7. End with a short 1-line "Quick Recap 🔁" that ties the analogy back to
       the real technical term.
    8. Use markdown formatting (bold, bullet points) to make it easy to read.
    """

    user_prompt = f"Explain the concept of '{topic}' using {game}."

    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system_prompt,
    )

    response = model.generate_content(user_prompt)
    return response.text


# ---------------------------------------------------------
# 6. SIDEBAR: KPIs + history
# ---------------------------------------------------------
# Shrinks the sidebar's metric value font so full game names
# (e.g. "Minecraft") display in full instead of being cut off as "M...".
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

    # Stacked vertically instead of side-by-side columns so each
    # metric has full width to show the complete game name.
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
        # st.data_editor lets the user browse (and even tweak) past queries
        st.data_editor(
            st.session_state.history,
            use_container_width=True,
            hide_index=True,
            disabled=True,  # read-only history log
            key="history_editor",
        )

        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.history = []
            st.session_state.total_explanations = 0
            st.rerun()
    else:
        st.caption("No explanations yet. Generate one to see it here!")


# ---------------------------------------------------------
# 7. MAIN PAGE: Header
# ---------------------------------------------------------
st.title("🎮 Explain it Like I Play")
st.markdown(
    "##### Turn tricky engineering topics into game logic you already understand."
)
st.divider()


# ---------------------------------------------------------
# 8. INPUTS: game, topic, difficulty
# ---------------------------------------------------------
# NOTE: These selectors are OUTSIDE st.form on purpose. Streamlit only
# reruns the script (and reveals new widgets like the custom-topic
# textbox) when a widget's on_change fires — but a form freezes all
# widgets inside it until the submit button is clicked. Keeping the
# topic dropdown outside the form lets the "Other" textbox appear
# immediately when selected. The actual Gemini API call is still
# gated behind a single button press below, so there's no extra cost.
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
    topic_choice = st.selectbox("🧠 Pick a topic (or choose 'Other')", options=PRESET_TOPICS)

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
st.caption(f"Selected level: **{difficulty}** — {DIFFICULTY_LEVELS[difficulty].split('(')[0].strip()}")

submitted = st.button("✨ Generate Explanation", use_container_width=True)


# ---------------------------------------------------------
# 9. HANDLE SUBMISSION
# ---------------------------------------------------------
if submitted:
    final_topic = custom_topic.strip() if topic_choice == "Other (type your own)" else topic_choice

    if not final_topic:
        st.warning("⚠️ Please enter a topic before generating an explanation.")
    else:
        with st.spinner(f"Asking {selected_game} to explain '{final_topic}'..."):
            try:
                explanation = generate_explanation(
                    game=selected_game,
                    topic=final_topic,
                    difficulty_instruction=DIFFICULTY_LEVELS[difficulty],
                )

                # Update session state (this is what prevents memory loss)
                st.session_state.total_explanations += 1
                st.session_state.last_game = selected_game
                st.session_state.history.append(
                    {
                        "Game": selected_game,
                        "Topic": final_topic,
                        "Difficulty": difficulty,
                    }
                )

                st.success("Done! Here's your explanation 👇")
                st.markdown("---")
                st.markdown(f"### {GAME_EMOJIS.get(selected_game, '🎮')} {final_topic}, explained via {selected_game}")
                st.markdown(explanation)

            except Exception as e:
                st.error(f"❌ Something went wrong while calling the Gemini API: {e}")


# ---------------------------------------------------------
# 10. FOOTER
# ---------------------------------------------------------
st.divider()
st.caption("Built with Streamlit + Google Gemini API | Explain it Like I Play © 2026")
st.markdown(
    "<p style='text-align: center; color: gray;'>Made with ❤️ by Varad</p>",
    unsafe_allow_html=True,
)
