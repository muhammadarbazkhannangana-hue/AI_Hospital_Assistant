
import json
import os
import uuid

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from groq import Groq
from streamlit_mic_recorder import speech_to_text

from database import (
    init_db,
    book_appointment,
    list_appointments,
    delete_appointment,
)
from rag import answer_from_pdf, get_pdf_status


# ==================================================
# 1. CONFIGURATION
# ==================================================

load_dotenv()

st.set_page_config(
    page_title="AI Hospital Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

api_key = os.getenv("GROQ_API_KEY", "").strip()
model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()
admin_password = os.getenv(
    "ADMIN_PASSWORD",
    "change_this_demo_password",
)

SYSTEM_PROMPT = """
You are a helpful hospital information assistant for an educational demo.

Provide general hospital information and explain supplied hospital documents.
You are not a doctor. Do not diagnose illnesses, prescribe medicines,
or recommend changing medical treatment.

For urgent or severe symptoms, advise the user to contact local emergency
services or a qualified healthcare professional.

If you do not know an answer, say so.
Keep answers clear, useful, and concise.
"""


# ==================================================
# 2. WHITE THEME AND CHATGPT-STYLE DESIGN
# ==================================================

st.markdown(
    """
    <style>
    /* Main page */
    .stApp {
        background-color: #FFFFFF !important;
        color: #202123 !important;
    }

    .main .block-container {
        max-width: 1000px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    /* Header */
    [data-testid="stHeader"] {
        background-color: #FFFFFF !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #F7F7F8 !important;
        border-right: 1px solid #E5E7EB;
    }

    [data-testid="stSidebar"] * {
        color: #202123;
    }

    /* Main text */
    .stMarkdown,
    .stMarkdown p,
    .stMarkdown li,
    h1, h2, h3, h4,
    label {
        color: #202123;
    }

    /* Chat messages */
    [data-testid="stChatMessage"] {
        background-color: #FFFFFF !important;
        border: none;
        border-radius: 12px;
    }

    /* Chat input */
    [data-testid="stChatInput"] {
        background-color: #FFFFFF !important;
        border: 1px solid #D9D9E3 !important;
        border-radius: 18px !important;
    }

    [data-testid="stChatInput"] textarea {
        background-color: #FFFFFF !important;
        color: #202123 !important;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 10px;
        border: 1px solid #D9D9E3;
        background-color: #FFFFFF;
        color: #202123;
        transition: background-color 0.2s;
    }

    .stButton > button:hover {
        background-color: #F0F0F0;
        border-color: #B8B8C5;
        color: #111111;
    }

    /* Form controls */
    input, textarea {
        background-color: #FFFFFF !important;
        color: #202123 !important;
    }

    [data-testid="stSelectbox"] div[data-baseweb="select"] {
        background-color: #FFFFFF;
    }

    /* Subtitle */
    .app-subtitle {
        color: #6B7280 !important;
        font-size: 15px;
    }

    /* Divider */
    hr {
        border-color: #E5E7EB;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# 3. CHAT SESSION STORAGE
# ==================================================

if "chats" not in st.session_state:
    first_chat_id = str(uuid.uuid4())

    st.session_state.chats = {
        first_chat_id: {
            "title": "New chat",
            "messages": [],
        }
    }

    st.session_state.active_chat = first_chat_id

if "active_chat" not in st.session_state:
    st.session_state.active_chat = next(
        iter(st.session_state.chats)
    )

if "voice_transcript" not in st.session_state:
    st.session_state.voice_transcript = ""


def create_new_chat():
    chat_id = str(uuid.uuid4())

    st.session_state.chats[chat_id] = {
        "title": "New chat",
        "messages": [],
    }

    st.session_state.active_chat = chat_id
    st.session_state.voice_transcript = ""


def rename_chat_if_needed(chat_id, question):
    chat = st.session_state.chats[chat_id]

    if chat["title"] == "New chat":
        chat["title"] = question.strip()[:30]


# ==================================================
# 4. GROQ AI RESPONSE WITH CONVERSATION HISTORY
# ==================================================

def get_chat_response(question, history=None, context=""):
    if not api_key or api_key == "your_groq_api_key_here":
        return (
            "Groq API key configure nahi hai. "
            "Apni private .env file mein GROQ_API_KEY check karo."
        )

    client = Groq(api_key=api_key)

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    # Include recent conversation history
    if history:
        for item in history[-12:]:
            if item["role"] in ("user", "assistant"):
                messages.append(
                    {
                        "role": item["role"],
                        "content": item["content"],
                    }
                )

    user_content = question

    if context:
        user_content = (
            "Use the following hospital document context when relevant. "
            "It may be incomplete; do not invent information that is "
            "not supported by the document.\n\n"
            f"DOCUMENT CONTEXT:\n{context}\n\n"
            f"USER QUESTION:\n{question}"
        )

    messages.append(
        {
            "role": "user",
            "content": user_content,
        }
    )

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
        max_tokens=700,
    )

    return (
        completion.choices[0].message.content
        or "Sorry, no response was returned."
    )


# ==================================================
# 5. TEXT-TO-SPEECH
# ==================================================

def speak_answer(answer, key):
    safe_answer = json.dumps(answer).replace("</", "<\\/")

    components.html(
        f"""
        <div style="
            display:flex;
            gap:8px;
            align-items:center;
            font-family:Arial,sans-serif;
        ">
            <button id="speak_{key}" style="
                padding:8px 14px;
                border:1px solid #D9D9E3;
                border-radius:18px;
                background:white;
                color:#202123;
                cursor:pointer;
            ">🔊 Read aloud</button>

            <button id="stop_{key}" style="
                padding:8px 14px;
                border:1px solid #D9D9E3;
                border-radius:18px;
                background:white;
                color:#202123;
                cursor:pointer;
            ">⏹ Stop</button>
        </div>

        <script>
            const answerText = {safe_answer};

            document.getElementById("speak_{key}").onclick = () => {{
                if (!("speechSynthesis" in window)) {{
                    alert("Speech output is not supported by this browser.");
                    return;
                }}

                window.speechSynthesis.cancel();

                const speech = new SpeechSynthesisUtterance(answerText);
                speech.lang = "en-US";
                speech.rate = 1;

                window.speechSynthesis.speak(speech);
            }};

            document.getElementById("stop_{key}").onclick = () => {{
                window.speechSynthesis.cancel();
            }};
        </script>
        """,
        height=55,
    )


# ==================================================
# 6. SIDEBAR
# ==================================================

with st.sidebar:
    st.markdown("## 🏥 Hospital AI")
    st.caption("Your AI hospital information assistant")

    if st.button("＋ New chat", use_container_width=True):
        create_new_chat()
        st.rerun()

    st.divider()
    st.markdown("**Recent chats**")

    for chat_id, chat in reversed(list(st.session_state.chats.items())):
        label = chat["title"]

        if chat_id == st.session_state.active_chat:
            label = "● " + label

        if st.button(
            label,
            key=f"open_chat_{chat_id}",
            use_container_width=True,
        ):
            st.session_state.active_chat = chat_id
            st.session_state.voice_transcript = ""
            st.rerun()

    st.divider()

    page = st.radio(
        "Project sections",
        [
            "AI Chat",
            "Hospital PDF / RAG",
            "Book Appointment",
            "Admin Dashboard",
        ],
    )

    st.divider()
    st.caption(f"AI model: {model}")
    st.caption("Educational demo only.")
    st.caption("Do not enter real patient records or sensitive data.")


# ==================================================
# 7. AI CHAT PAGE
# ==================================================

if page == "AI Chat":

    st.title("How can I help you today?")

    st.markdown(
        '<p class="app-subtitle">'
        'Ask a question, type a message, or use your microphone.'
        '</p>',
        unsafe_allow_html=True,
    )

    st.info(
        "This assistant provides general information only. "
        "It cannot diagnose illnesses or replace a healthcare professional."
    )

    chat_id = st.session_state.active_chat
    messages = st.session_state.chats[chat_id]["messages"]

    # Display previous messages
    for index, msg in enumerate(messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            if msg["role"] == "assistant":
                speak_answer(
                    msg["content"],
                    f"{chat_id.replace('-', '')}_{index}",
                )

    # Voice input
    st.markdown("### 🎙️ Voice input")

    language = st.selectbox(
        "Speech recognition language",
        options=["en-US", "ur-PK"],
        format_func=lambda value: (
            "English" if value == "en-US" else "Urdu"
        ),
        key="voice_language",
    )

    try:
        transcript = speech_to_text(
            language=language,
            start_prompt="🎙️ Start speaking",
            stop_prompt="⏹ Stop recording",
            just_once=True,
            use_container_width=True,
            key=f"mic_{chat_id}",
        )

        if transcript:
            st.session_state.voice_transcript = transcript

    except Exception as exc:
        st.warning(
            "Microphone could not start. Check your browser permission "
            f"and connection. Details: {exc}"
        )

    if st.session_state.voice_transcript:
        st.markdown("**Recognized speech:**")
        st.write(st.session_state.voice_transcript)

        if st.button("Send voice message", type="primary"):
            question = st.session_state.voice_transcript.strip()
            st.session_state.voice_transcript = ""

            if question:
                messages.append(
                    {
                        "role": "user",
                        "content": question,
                    }
                )

                rename_chat_if_needed(chat_id, question)

                with st.spinner("AI is thinking..."):
                    try:
                        answer = get_chat_response(
                            question,
                            history=messages[:-1],
                        )
                    except Exception as exc:
                        answer = (
                            f"API error: {exc}\n\n"
                            "Check your .env configuration, internet "
                            "connection, and GROQ_MODEL setting."
                        )

                messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                    }
                )

            st.rerun()

    # Normal text input
    prompt = st.chat_input("Message Hospital AI...")

    if prompt and prompt.strip():
        prompt = prompt.strip()

        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        rename_chat_if_needed(chat_id, prompt)

        with st.spinner("AI is thinking..."):
            try:
                answer = get_chat_response(
                    prompt,
                    history=messages[:-1],
                )
            except Exception as exc:
                answer = (
                    f"API error: {exc}\n\n"
                    "Check your .env configuration, internet "
                    "connection, and GROQ_MODEL setting."
                )

        messages.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

        st.rerun()


# ==================================================
# 8. HOSPITAL PDF / RAG
# ==================================================

elif page == "Hospital PDF / RAG":

    st.title("📄 Hospital PDF / RAG")

    st.write(
        "Upload a hospital information PDF and ask questions about its contents."
    )

    pdf_path = os.path.join("data", "hospital_info.pdf")

    uploaded = st.file_uploader(
        "Upload hospital information PDF",
        type=["pdf"],
    )

    if uploaded:
        os.makedirs("data", exist_ok=True)

        with open(pdf_path, "wb") as file:
            file.write(uploaded.getbuffer())

        st.success("PDF saved to data/hospital_info.pdf")

    st.caption(get_pdf_status(pdf_path))

    question = st.text_input("Your question about the PDF")

    if st.button("Search PDF and answer", type="primary"):

        if not question.strip():
            st.warning("Please enter a question.")

        else:
            with st.spinner("Searching the hospital PDF..."):
                try:
                    context = answer_from_pdf(pdf_path, question)

                    if context.startswith("PDF_ISSUE:"):
                        st.warning(
                            context.replace("PDF_ISSUE:", "")
                        )

                    else:
                        st.markdown("#### Relevant information from PDF")
                        st.write(context)

                        st.markdown("#### AI answer")

                        try:
                            answer = get_chat_response(
                                question,
                                context=context,
                            )
                            st.markdown(answer)
                            speak_answer(answer, "pdf_answer")

                        except Exception as exc:
                            st.error(f"Groq API error: {exc}")

                except Exception as exc:
                    st.error(f"PDF/RAG error: {exc}")


# ==================================================
# 9. APPOINTMENT BOOKING
# ==================================================

elif page == "Book Appointment":

    st.title("📅 Demo Appointment Booking")

    st.warning(
        "Use fictional demo details only. Do not enter real patient "
        "information or sensitive medical details."
    )

    with st.form("appointment_form"):

        patient_name = st.text_input("Demo patient name")

        department = st.selectbox(
            "Department",
            [
                "General",
                "Cardiology",
                "Dental",
                "Eye",
                "ENT",
                "Orthopedics",
                "Other",
            ],
        )

        appointment_date = st.date_input("Appointment date")

        appointment_time = st.selectbox(
            "Appointment time",
            [
                "09:00",
                "10:00",
                "11:00",
                "12:00",
                "14:00",
                "15:00",
                "16:00",
            ],
        )

        notes = st.text_area(
            "Optional note (no medical details)"
        )

        submitted = st.form_submit_button(
            "Book demo appointment",
            type="primary",
        )

    if submitted:

        if not patient_name.strip():
            st.error("Please enter a demo name.")

        else:
            try:
                book_appointment(
                    patient_name.strip(),
                    department,
                    str(appointment_date),
                    appointment_time,
                    notes.strip(),
                )

                st.success(
                    "Demo appointment saved in the local database."
                )

            except Exception as exc:
                st.error(f"Could not save appointment: {exc}")


# ==================================================
# 10. ADMIN DASHBOARD
# ==================================================

elif page == "Admin Dashboard":

    st.title("🔐 Admin Dashboard")

    password = st.text_input(
        "Admin password",
        type="password",
    )

    if password == admin_password:

        st.success("Admin access granted for this demo.")

        try:
            rows = list_appointments()

            if rows:
                st.dataframe(
                    [
                        {
                            "ID": row[0],
                            "Demo name": row[1],
                            "Department": row[2],
                            "Date": row[3],
                            "Time": row[4],
                            "Note": row[5],
                            "Created": row[6],
                        }
                        for row in rows
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

                appointment_ids = [row[0] for row in rows]

                selected_id = st.selectbox(
                    "Select appointment ID to delete",
                    appointment_ids,
                )

                if st.button("Delete selected appointment"):
                    delete_appointment(int(selected_id))
                    st.success("Appointment deleted.")
                    st.rerun()

            else:
                st.info("No demo appointments have been booked yet.")

        except Exception as exc:
            st.error(f"Could not load appointments: {exc}")

    elif password:
        st.error("Incorrect admin password.")
