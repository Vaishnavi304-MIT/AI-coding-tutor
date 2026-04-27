import streamlit as st
import os
import subprocess
import tempfile
from langchain_groq import ChatGroq

# ============================================================
# CONFIG
# ============================================================
os.environ["GROQ_API_KEY"] = "enter the Groq key"

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2,
    max_tokens=700
)

st.set_page_config(page_title="AI Coding Tutor", layout="wide")

# ============================================================
# HEADER
# ============================================================
st.markdown("""
<style>
header {visibility:hidden;}

.fixed-header {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 65px;
    background: linear-gradient(90deg,#4f46e5,#7c3aed);
    color: white;
    z-index: 9999;
    display: flex;
    align-items: center;
    padding-left: 20px;
    font-size: 22px;
    font-weight: bold;
}

.main > div {
    padding-top: 80px;
}

section[data-testid="stSidebar"] {
    margin-top: 65px;
}
</style>

<div class="fixed-header">
🤖 AI Coding Tutor
</div>
""", unsafe_allow_html=True)

# ============================================================
# CACHE
# ============================================================
@st.cache_data(show_spinner=False)
def cached_llm(prompt):
    return llm.invoke(prompt).content

def ask_llm(prompt):
    return cached_llm(prompt)

# ============================================================
# SESSION STATE
# ============================================================
defaults = {
    "messages": [],
    "language": "Python",
    "context": "learn",
    "current_question": "",
    "show_editor": False,
    "code": "",
    "last_state": {}
}
for k,v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
# RESET
# ============================================================
def reset_app():
    st.session_state.messages = []
    st.session_state.current_question = ""
    st.session_state.show_editor = False
    st.session_state.code = ""

# ============================================================
# INTENT DETECTION
# ============================================================
def detect_intent(text):
    t = text.lower()

    if any(k in t for k in ["new problem","another problem","next question"]):
        return "new_problem"

    if any(k in t for k in ["hint","help"]):
        return "help"

    if "solution" in t:
        return "solution"

    return "general"

# ============================================================
# CODE EXTRACTION
# ============================================================
def extract_code(text):
    if "```" in text:
        code = text.split("```")[1]
        lines = code.split("\n")
        if lines[0].lower() in ["python","cpp","c","java"]:
            lines = lines[1:]
        return "\n".join(lines)
    return None

# ============================================================
# AGENTS
# ============================================================
def learn_agent(user_input):
    lang = st.session_state.language
    return ask_llm(f"Explain in {lang}: {user_input}")

def practice_agent(user_input):
    q = st.session_state.current_question
    return ask_llm(f"""
User solving:
{q}

User question:
{user_input}

Give hint only unless solution is asked.
""")

def dsa_agent(user_input):
    q = st.session_state.current_question
    return ask_llm(f"""
DSA Problem:
{q}

User question:
{user_input}

Explain approach and logic only.
""")

# ============================================================
# ROUTER
# ============================================================
def tutor(user_input):

    intent = detect_intent(user_input)
    ctx = st.session_state.context

    # NEW PROBLEM
    if intent == "new_problem":
        reset_app()
        st.session_state.context = ctx

        if ctx == "practice":
            q = ask_llm(f"""
Generate a {st.session_state.language} coding problem.

STRICT:
- No story
- Only coding
- Format: Problem, Input, Output, Constraints, Example
- Add function with TODO
- No solution
""")
        elif ctx == "dsa":
            q = ask_llm("""
Generate a DSA problem.

STRICT:
- No story
- Focus on arrays/strings/trees/graphs
- Format properly
- Add TODO code
- No solution
""")
        else:
            return ask_llm("Give coding problem")

        st.session_state.current_question = q
        return q

    # HELP
    if intent == "help":
        return ask_llm(f"Give hint only:\n{st.session_state.current_question}")

    # SOLUTION
    if intent == "solution":
        return ask_llm(f"Solve:\n{st.session_state.current_question}")

    # ROUTING
    if ctx == "practice":
        return practice_agent(user_input)

    if ctx == "dsa":
        return dsa_agent(user_input)

    return learn_agent(user_input)

# ============================================================
# CODE RUNNER
# ============================================================
def run_code(code):
    if st.session_state.language != "Python":
        return "⚠️ Only Python supported"

    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "main.py")
            open(path,"w").write(code)

            result = subprocess.run(
                ["python", path],
                capture_output=True,
                text=True
            )
            return result.stdout or result.stderr
    except Exception as e:
        return str(e)

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.title("⚙️ Controls")

if st.sidebar.button("🧹 Clear Chat"):
    reset_app()
    st.rerun()

lang = st.sidebar.selectbox("Language", ["Python","C++","Java","JavaScript"])
mode = st.sidebar.radio("Mode", ["Learn","Practice","DSA"])

if st.session_state.last_state != {"mode":mode,"lang":lang}:
    reset_app()
    st.session_state.last_state = {"mode":mode,"lang":lang}

st.session_state.language = lang

# MODE SET
if mode == "Learn":
    st.session_state.context = "learn"

if mode == "Practice":
    if st.sidebar.button("🎯 Get Question"):
        reset_app()
        st.session_state.context = "practice"
        st.session_state.current_question = ask_llm("""
Generate coding problem.

STRICT:
- No story
- Proper format
- TODO code
- No solution
""")

if mode == "DSA":
    if st.sidebar.button("📘 Learn DSA"):
        reset_app()
        st.session_state.context = "learn"
        st.session_state.messages.append({
            "role":"assistant",
            "content": ask_llm("Teach DSA basics")
        })

    if st.sidebar.button("🎯 Practice DSA"):
        reset_app()
        st.session_state.context = "dsa"
        st.session_state.current_question = ask_llm("""
Generate DSA problem.

STRICT:
- No story
- Proper format
- TODO code
- No solution
""")

# ============================================================
# QUESTION UI
# ============================================================
if st.session_state.current_question:
    st.write(st.session_state.current_question)

    code_input = st.text_area("Your Code")

    col1,col2,col3 = st.columns(3)

    with col1:
        if st.button("▶ Run"):
            st.code(run_code(code_input))

    with col2:
        if st.button("💡 Help"):
            st.session_state.messages.append({
                "role":"assistant",
                "content": tutor("help")
            })

    with col3:
        if st.button("🧠 Solution"):
            st.session_state.messages.append({
                "role":"assistant",
                "content": tutor("solution")
            })

# ============================================================
# CHAT
# ============================================================
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        code = extract_code(msg["content"])
        if code:
            st.code(code)
            if st.button("💻 Open in Editor", key=f"editor_{i}"):
                st.session_state.code = code
                st.session_state.show_editor = True
                st.rerun()

# ============================================================
# INPUT
# ============================================================
user = st.chat_input("Ask coding...")

if user:
    st.session_state.show_editor = False

    st.session_state.messages.append({"role":"user","content":user})

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("⏳ Thinking...")

        reply = tutor(user)

        placeholder.markdown(reply)

    st.session_state.messages.append({"role":"assistant","content":reply})

# ============================================================
# EDITOR
# ============================================================
if st.session_state.show_editor:

    st.subheader("💻 Code Editor")

    code = st.text_area("Code", st.session_state.code)

    if st.button("▶ Run Code"):
        st.code(run_code(code))

    if st.button("❌ Close Editor"):
        st.session_state.show_editor = False
        st.rerun()
