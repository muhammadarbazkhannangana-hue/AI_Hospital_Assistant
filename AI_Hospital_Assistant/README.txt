AI HOSPITAL ASSISTANT - SETUP

1. Extract this ZIP directly inside your AI_Hospital_Assistant folder.
2. Open .env in Notepad and replace your_groq_api_key_here with your real Groq API key.
   Do not share the key or upload .env publicly.
3. Save the file.
4. Open Command Prompt in this project folder and activate the existing virtual environment:
   .venv\Scripts\activate.bat
   (If using PowerShell, run: cmd /k ".venv\Scripts\activate.bat")
5. Install/verify dependencies:
   python -m pip install -r requirements.txt
6. Start the app:
   streamlit run app.py
7. Your browser should open the local Streamlit app.

If the Groq model name is unavailable to your account, edit GROQ_MODEL in .env to a model
currently listed in your Groq Console. Restart Streamlit after editing .env.

PDF/RAG:
- A sample PDF is included at data/hospital_info.pdf.
- You can also upload a PDF in the Hospital PDF / RAG page.
- The first RAG use may download the sentence-transformer embedding model.

SAFETY:
This is an educational demo only. Do not use it for real patient records, medical diagnosis,
prescriptions, emergency triage, or real hospital operations.
