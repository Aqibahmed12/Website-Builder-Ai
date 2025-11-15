# ai/utils.py


import os
import json
import streamlit as st
import google.generativeai as genai
import io
import zipfile


API_KEY = st.secrets["API_KEY"]
genai.configure(api_key=API_KEY)

DEFAULT_MODEL = "gemini-2.5-flash"

# -----------------------------------------------------
# Force valid JSON from Gemini output
# -----------------------------------------------------
def force_json(text):
    """
    Gemini sometimes outputs JSON with extra words or markdown.
    This function extracts and fixes JSON safely.
    """
    text = text.strip()

    # Try direct JSON
    try:
        return json.loads(text)
    except:
        pass

    # Remove code fences
    if "```" in text:
        text = text.split("```")[1]
        text = text.replace("json", "").strip()
        try:
            return json.loads(text)
        except:
            pass

    # Extract JSON manually using first '{' to last '}'
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            extracted = text[start:end+1]
            return json.loads(extracted)
        except:
            pass

    raise ValueError("Gemini returned invalid JSON:\n" + text)


# -----------------------------------------------------
# Website Generator Class
# -----------------------------------------------------
class WebsiteGenerator:
    def __init__(self, model="auto"):
        self.model = DEFAULT_MODEL if model == "auto" else model

    # ------------------------------
    # Main AI call
    # ------------------------------
    def _call_ai(self, prompt):
        system = """
You are an AI website generator.
Respond ONLY with valid JSON. No explanations.

JSON format:
{
 "index.html": "...",
 "styles.css": "...",
 "script.js": "...",
 "backend.py": "..." (optional)
}

Rules:
- Do NOT write markdown.
- Do NOT write extra text.
- MUST return pure JSON.
"""

        full_prompt = system + "\nUser Request:\n" + prompt

        model = genai.GenerativeModel(self.model)
        response = model.generate_content(full_prompt)

        text = response.text
        return force_json(text)

    # ------------------------------
    # Public method
    # ------------------------------
    def generate_website(self, prompt):
        files = self._call_ai(prompt)
        return {"files": files}

    # ------------------------------
    # Chat-based editing
    # ------------------------------
    def edit_files(self, user_msg, current_files):
        prompt = f"""
Modify these website files according to the user's message.

User message:
{user_msg}

Current files:
{json.dumps(current_files, indent=2)}

Return ONLY JSON of updated files.
"""
        return self._call_ai(prompt)

    # ------------------------------
    # Live preview
    # ------------------------------
    def combine_to_html(self, files):
        html = files.get("index.html", "")
        css = files.get("styles.css", "")
        js = files.get("script.js", "")

        return f"""
<!doctype html>
<html>
<head>
<meta charset='utf-8'>
<style>{css}</style>
</head>
<body>
{html}
<script>{js}</script>
</body>
</html>
"""


# -----------------------------------------------------
# ZIP creator
# -----------------------------------------------------
def create_zip_bytes(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            z.writestr(name, content.encode("utf-8"))
    buf.seek(0)
    return buf.getvalue()
