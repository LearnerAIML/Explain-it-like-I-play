# 🎮 Explain it Like I Play

```
$ whoami
> An AI dictionary that explains hard engineering concepts
> using ONLY the game you already love playing.

$ echo "Recursion, but make it Minecraft"
> "It's like crafting a crafting table to craft a crafting table..."
```

<p align="center">
  <img src="https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/Powered%20by-Gemini%20API-4285F4?style=for-the-badge&logo=google&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
</p>

---

## `> about`

**Explain it Like I Play** takes a complex engineering or CS topic (like
*Recursion*, *Load Balancing*, or *TCP/IP Handshakes*) and re-explains it
**entirely through the mechanics of a video game you already understand** —
Minecraft, Mario, Valorant, or Chess.

No generic textbook definitions. Every explanation is a concrete, mapped
analogy: your game's items, characters, and rules become the technical
concept.

---

## `> demo`

🔗 **Live App:** `PASTE_YOUR_STREAMLIT_LIVE_LINK_HERE`

---

## `> features`

```
[✔] Pick from 4 games: Minecraft, Mario, Valorant, Chess
[✔] 8 preset CS topics + custom topic input
[✔] 4 difficulty levels (Beginner -> Interview-level)
[✔] Session stats via st.metric KPI cards
[✔] Browsable explanation history via st.data_editor
[✔] Zero memory loss between reruns (st.session_state)
[✔] Single API call per request (st.form)
```

---

## `> architecture`

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for the full system diagram and
data flow.

```mermaid
flowchart LR
    A[User Input] --> B[Streamlit UI]
    B --> C[Gemini API]
    C --> B
    B --> D[Rendered Explanation]
```

---

## `> setup`

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/explain-it-like-i-play.git
cd explain-it-like-i-play
```

### 2. Install dependencies

**Using `uv`  (recommended — faster):**
```bash
uv venv
source .venv/bin/activate      # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

**Or using plain `pip`:**
```bash
python -m venv .venv
source .venv/bin/activate      # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Add your Gemini API key
```bash
cp .env.example .env
```
Then open `.env` and paste your key:
```
GEMINI_API_KEY=your_actual_key_here
```
Get a free key at → https://aistudio.google.com/app/apikey

### 4. Run the app
```bash
streamlit run app.py
```

---

## `> tech_stack`

| Layer | Tool |
|---|---|
| Frontend / UI | Streamlit |
| AI Engine | Google Gemini API (`gemini-2.0-flash`) |
| Env Management | `python-dotenv` |
| Package Manager | `uv` (or pip) |
| Language | Python 3.10+ |

---

## `> project_structure`

```
explain-it-like-i-play/
├── app.py                # Main Streamlit application
├── requirements.txt      # Python dependencies
├── .env.example           # Template for API key (safe to commit)
├── .env                    # Your real API key (NEVER commit this)
├── .gitignore
├── ARCHITECTURE.md        # System design + Mermaid diagram
└── README.md
```

---

## `> author`

Built by **Varad** — B.Tech CS (AIML), as a hackathon / recruitment showcase
project.

```
$ echo "Made with Python, Gemini, and one too many Minecraft analogies."
```
