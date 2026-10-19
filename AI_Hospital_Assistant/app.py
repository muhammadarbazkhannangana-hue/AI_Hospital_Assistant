import json
import os
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from groq import Groq
from database import init_db, book_appointment, list_appointments, delete_appointment
from rag import answer_from_pdf, get_pdf_status

load_dotenv()
st.set_page_config(page_title="AI Hospital Assistant", page_icon="🏥", layout="wide")
init_db()

st.title("🏥 AI Hospital Assistant")
st.caption("Educational demo • Not a medical diagnosis service")

api_key = os.getenv("GROQ_API_KEY", "").strip()
model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()
admin_password = os.getenv("ADMIN_PASSWORD", "change_this_demo_password")

with st.sidebar:
    st.header("Project menu")
    page = st.radio("Choose a section", ["AI Chat", "Hospital PDF / RAG", "Book Appointment", "Admin Dashboard"])
    st.divider()
    st.caption(f"Model setting: `{model}`")
    st.caption("Never enter real patient records or sensitive personal data in this demo.")

SYSTEM_PROMPT = """You are a helpful hospital information assistant for an educational demo.
Give general hospital information and explain the supplied hospital document when context is provided.
You are not a doctor and must not diagnose, prescribe medicines, or recommend changing treatment.
For urgent or severe symptoms, advise the user to contact local emergency services or a qualified clinician.
If you do not know an answer, say so. Keep answers clear and concise."""

def get_chat_response(question, context=""):
    if not api_key or api_key == "your_groq_api_key_here":
        return "Groq API key set nahi hai. Project folder ki .env file mein GROQ_API_KEY add karo."
    client = Groq(api_key=api_key)
    user_content = question
    if context:
        user_content = f"Hospital document context (may be incomplete):\n{context}\n\nUser question: {question}"
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
        max_tokens=700,
    )
    return completion.choices[0].message.content or "Sorry, no response was returned."

if page == "AI Chat":
    st.subheader("Ask a general hospital-information question")
    st.info("This demo can answer general questions, but it cannot diagnose illness or replace a healthcare professional.")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    prompt = st.chat_input("Type your question...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    answer = get_chat_response(prompt)
                except Exception as exc:
                    answer = f"API error: {exc}\n\nCheck your `.env` API key and `GROQ_MODEL` value."
            st.markdown(answer)
            if st.button("🔊 Read answer aloud", key=f"speak_{len(st.session_state.messages)}"):
                safe_text = json.dumps(answer)
                components.html(f"""<script>
                const msg = new SpeechSynthesisUtterance({safe_text});
                msg.lang = 'en-US';
                window.speechSynthesis.cancel();
                window.speechSynthesis.speak(msg);
                </script>""", height=0)
        st.session_state.messages.append({"role": "assistant", "content": answer})

elif page == "Hospital PDF / RAG":
    st.subheader("Ask questions using hospital PDF (RAG)")
    st.write("Place your hospital information PDF in the `data` folder as `hospital_info.pdf`, or upload a PDF below.")
    uploaded = st.file_uploader("Upload hospital information PDF", type=["pdf"])
    pdf_path = os.path.join("data", "hospital_info.pdf")
    if uploaded:
        os.makedirs("data", exist_ok=True)
        with open(pdf_path, "wb") as f:
            f.write(uploaded.getbuffer())
        st.success("PDF saved to data/hospital_info.pdf")
    st.caption(get_pdf_status(pdf_path))
    q = st.text_input("Question about the PDF")
    if st.button("Search PDF and answer", type="primary"):
        if not q.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Reading PDF and preparing answer..."):
                try:
                    context = answer_from_pdf(pdf_path, q)
                    if context.startswith("PDF_ISSUE:"):
                        st.warning(context.replace("PDF_ISSUE:", ""))
                    else:
                        st.markdown("**Relevant information found in PDF:**")
                        st.write(context)
                        st.markdown("**AI answer:**")
                        try:
                            st.write(get_chat_response(q, context))
                        except Exception as exc:
                            st.error(f"Groq API error: {exc}")
                except Exception as exc:
                    st.error(f"PDF/RAG error: {exc}")

elif page == "Book Appointment":
    st.subheader("Demo appointment booking")
    st.warning("Use fictional/demo details only. Do not enter real patient information.")
    with st.form("appointment_form"):
        patient_name = st.text_input("Demo patient name")
        department = st.selectbox("Department", ["General", "Cardiology", "Dental", "Eye", "ENT", "Orthopedics", "Other"])
        date = st.date_input("Appointment date")
        time = st.selectbox("Time", ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00"])
        notes = st.text_area("Optional note (no medical details)")
        submitted = st.form_submit_button("Book demo appointment")
    if submitted:
        if not patient_name.strip():
            st.error("Please enter a demo name.")
        else:
            try:
                book_appointment(patient_name.strip(), department, str(date), time, notes.strip())
                st.success("Demo appointment saved in local SQLite database.")
            except Exception as exc:
                st.error(f"Could not save appointment: {exc}")

elif page == "Admin Dashboard":
    st.subheader("Admin Dashboard")
    password = st.text_input("Admin password", type="password")
    if password == admin_password:
        st.success("Admin access granted for this local demo.")
        rows = list_appointments()
        if rows:
            st.dataframe(
                [{"ID": r[0], "Demo name": r[1], "Department": r[2], "Date": r[3], "Time": r[4], "Note": r[5], "Created": r[6]} for r in rows],
                use_container_width=True,
                hide_index=True,
            )
            ids = [r[0] for r in rows]
            selected = st.selectbox("Select appointment ID to delete", ids)
            if st.button("Delete selected demo appointment"):
                delete_appointment(int(selected))
                st.success("Appointment deleted. Refresh the page to update the table.")
        else:
            st.info("No demo appointments have been booked yet.")
    elif password:
        st.error("Incorrect admin password.")
