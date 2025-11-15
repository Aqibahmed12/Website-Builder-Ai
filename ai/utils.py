# ai/utils.py
# Helper utilities and LLM integration for AI Website Builder
#
# Upgraded by Gemini:
# - WebsiteGenerator __init__ now accepts api_key and model from the UI.
# - _call_gemini is rewritten to use the modern v1beta generateContent endpoint.
#   - It supports systemInstruction for better AI guidance.
#   - It supports force_json=True (responseMimeType) for reliable website generation.
# - generate_website: Uses system instruction and JSON mode.
# - chat_response: Uses system instruction and can return a dict to update files.
# - Removed google-auth logic to simplify and prioritize user-provided API key.

import os
import json
import requests
import zipfile
import io
import difflib
from typing import Dict, Any, List, Optional, Union


# -----------------------------------------------------------------------------
# WebsiteGenerator
# -----------------------------------------------------------------------------
class WebsiteGenerator:
    """
    Generates website files by calling an LLM. Prefers Gemini (via API key)
    and falls back to Hugging Face if configured.
    """

    def __init__(self,
                 api_key: Optional[str] = None,
                 model: str = "gemini-1.5-pro-latest",
                 hf_token: Optional[str] = None,
                 hf_model: str = "google/flan-t5-large",
                 request_timeout: int = 45):

        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self.gemini_model = model

        self.hf_token = hf_token
        self.hf_api_url = f"https://api-inference.huggingface.co/models/{hf_model}"
        self.request_timeout = request_timeout

    def call_llm(self,
                 user_prompt: str,
                 system_instruction: str,
                 max_tokens: int = 4096,
                 force_json: bool = False) -> str:
        """
        Unified LLM call:
         - Prefers Gemini if self.api_key is set.
         - Falls back to Hugging Face if self.hf_token is set.
        """
        if self.api_key:
            try:
                return self._call_gemini(
                    prompt=user_prompt,
                    system_instruction=system_instruction,
                    max_tokens=max_tokens,
                    api_key=self.api_key,
                    model_name=self.gemini_model,
                    force_json=force_json
                )
            except Exception as e:
                print(f"Gemini call failed: {e}")
                # Fall through to Hugging Face if configured
                if not self.hf_token:
                    raise e  # Re-raise if no fallback

        if self.hf_token:
            # Note: HF fallback doesn't support system instructions or JSON mode
            return self._call_huggingface(f"{system_instruction}\n\n{user_prompt}", max_tokens)

        raise RuntimeError("No LLM API key configured (neither Google AI nor Hugging Face).")

    def _call_gemini(self,
                     prompt: str,
                     system_instruction: str,
                     max_tokens: int,
                     api_key: str,
                     model_name: str,
                     force_json: bool = False) -> str:
        """
        Call Google's Generative Language API (v1beta) for Gemini models.
        Uses the modern generateContent endpoint.
        """
        # Use v1beta, which supports systemInstruction and responseMimeType
        base_url = "https://generativelanguage.googleapis.com/v1beta"
        model_path = f"models/{model_name}"
        url = f"{base_url}/{model_path}:generateContent?key={api_key}"

        headers = {"Content-Type": "application/json"}

        generation_config = {
            "temperature": 0.7,
            "topP": 0.9,
            "maxOutputTokens": max_tokens
        }

        # --- NEW: Force JSON output ---
        if force_json:
            generation_config["responseMimeType"] = "application/json"

        body = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": generation_config
        }

        resp = requests.post(url, headers=headers, json=body, timeout=self.request_timeout)

        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text}")

        data = resp.json()

        # --- NEW: Simplified and robust extraction ---
        try:
            # Standard path for text/JSON responses
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            # Handle potential safety blocks or empty responses
            if "promptFeedback" in data:
                feedback = data["promptFeedback"]
                raise RuntimeError(f"Gemini API blocked prompt: {feedback}")
            raise RuntimeError(f"Failed to parse Gemini response: {e} | Response: {data}")

    def _call_huggingface(self, prompt: str, max_tokens: int = 1024) -> str:
        """
        Call Hugging Face Inference API (fallback). Requires HUGGINGFACEHUB_API_TOKEN.
        """
        if not self.hf_token:
            raise RuntimeError("Hugging Face token not provided.")

        headers = {"Authorization": f"Bearer {self.hf_token}", "Content-Type": "application/json"}
        payload = {
            "inputs": prompt,
            "parameters": {"max_new_tokens": max_tokens, "temperature": 0.7, "top_p": 0.9}
        }
        resp = requests.post(self.hf_api_url, headers=headers, json=payload, timeout=self.request_timeout)

        if resp.status_code != 200:
            raise RuntimeError(f"HuggingFace API error {resp.status_code}: {resp.text}")

        data = resp.json()
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "generated_text" in data[0]:
            return data[0]["generated_text"]

        raise RuntimeError(f"Failed to parse HuggingFace response: {data}")

    # -----------------------------
    # High-level workflows
    # -----------------------------

    def generate_website(self, prompt: str, include_backend: str = "None", responsive: bool = True) -> Dict[str, Any]:
        """
        Generate website files. Instructs the model to return ONLY JSON.
        """
        system_instruction = f"""
You are an expert full-stack web developer. Your sole purpose is to generate a valid JSON object 
containing the files for a complete website based on the user's prompt.

You MUST return ONLY a single, valid JSON object with one top-level key: "files".
The "files" key must be a dictionary where keys are filenames (e.g., "index.html", "styles.css", "script.js") 
and values are the complete code content for that file as a string.

- ALWAYS include index.html, styles.css, and script.js.
- Write modern, clean, and commented code.
- `index.html` must be a complete HTML5 document.
- `styles.css` should be responsive {"(use @media queries)" if responsive else ""}.
- `script.js` should handle interactivity.
- {"Include a `backend.py` file using " + include_backend if include_backend != "None" else "Do NOT include a backend.py file."}
- Do NOT include any other text, pleasantries, or explanations. ONLY THE JSON.
"""

        user_prompt = f"Generate the website files for: {prompt}"

        # Call the LLM with force_json=True
        raw_json_string = self.call_llm(
            user_prompt,
            system_instruction,
            max_tokens=8192,  # Allow large output for full website
            force_json=True
        )

        try:
            parsed = json.loads(raw_json_string)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON from model. Error: {e}\nRaw response: {raw_json_string}")

        files = parsed.get("files", {})

        # Ensure required files exist or provide defaults
        if "index.html" not in files:
            files["index.html"] = self._default_index(prompt)
        if "styles.css" not in files:
            files["styles.css"] = self._default_css()
        if "script.js" not in files:
            files["script.js"] = self._default_js()
        if include_backend != "None" and "backend.py" not in files:
            files["backend.py"] = self._default_backend(include_backend)

        return {"files": files, "metadata": parsed.get("metadata", {})}

    def chat_response(self, messages: List[Dict[str, str]], current_files: Dict[str, str]) -> Union[str, Dict]:
        """
        Create conversational responses OR JSON updates for files.
        """
        system_instruction = f"""
You are an AI assistant helping a user refine their website.
The user has the following files: {list(current_files.keys())}

- If the user asks a general question, provide a concise, helpful text answer.
- If the user asks to modify the code, change a style, or add a feature, you MUST 
  respond with ONLY a valid JSON object.
- The JSON object must have this format:
  {{"message": "I've updated the files...", "files_updated": {{"filename.html": "new file content...", "styles.css": "new css..."}}}}
- Only include files that were changed in "files_updated".
- Do NOT respond with JSON for simple conversation.
"""

        transcript = "\n".join([f"{m['role']}:{m['text']}" for m in messages])
        user_prompt = f"Conversation history:\n{transcript}\n\nLatest user message: {messages[-1]['text']}"

        # Call LLM without force_json, as it might be a text reply
        raw_reply = self.call_llm(
            user_prompt,
            system_instruction,
            max_tokens=4096,
            force_json=False
        )

        # --- NEW: Check if the reply is JSON (a file update) or text (chat) ---
        try:
            # Attempt to parse as JSON first
            parsed = json.loads(raw_reply)
            if isinstance(parsed, dict) and "files_updated" in parsed:
                # It's a file update!
                return parsed  # Return the whole dict
        except json.JSONDecodeError:
            # It's not JSON, so it must be a plain text chat message
            pass

        return raw_reply.strip()  # Return the text message

    def explain_code(self, code: str) -> str:
        system_instruction = "You are a code documentation expert. Explain the following code clearly and concisely. Use markdown for formatting."
        prompt = f"Please explain this code:\n\n```\n{code}\n```"
        try:
            return self.call_llm(prompt, system_instruction, max_tokens=1024)
        except Exception as e:
            return f"Could not contact LLM for explanation. Error: {e}"

    # -----------------------------
    # Helpers & fallbacks
    # -----------------------------

    def fallback_site(self, prompt: str) -> Dict[str, str]:
        return {
            "index.html": self._default_index(prompt),
            "styles.css": self._default_css(),
            "script.js": self._default_js()
        }

    def fallback_chat_reply(self, user_text: str) -> str:
        return f"I'm currently unable to reach the AI model. (User asked: {user_text})"

    def _default_index(self, prompt: str) -> str:
        title = "AI Generated Site (Fallback)"
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{title}</title>
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <header><h1>{title}</h1><p>{prompt}</p></header>
  <main><section class="hero">
    <h2>Welcome</h2>
    <p>This is a fallback site generated when the AI model could not be reached.</p>
    <button id="cta">Call to action</button>
  </section></main>
  <script src="script.js"></script>
</body>
</html>
"""

    def _default_css(self) -> str:
        return """/* styles.css - fallback */
:root { --bg: #fff; --text: #111; --accent: #007bff; }
[data-theme='dark'] { --bg: #0b0b0f; --text:#e6edf3; --accent:#4da3ff; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial; background:var(--bg); color:var(--text); margin:0; padding:0; }
header { padding:2rem; text-align:center; background:linear-gradient(90deg, rgba(0,123,255,0.08), transparent); }
.hero { padding:3rem; text-align:center; }
button { background:var(--accent); color:white; border:none; padding:0.75rem 1.2rem; border-radius:6px; cursor:pointer; }
@media (max-width:600px) { .hero { padding:1.5rem; } }
"""

    def _default_js(self) -> str:
        return """// script.js - fallback
document.addEventListener('DOMContentLoaded', function(){
  const cta = document.getElementById('cta');
  if (cta) { cta.addEventListener('click', () => alert('Thanks for trying the fallback!')); }
});
"""

    def _default_backend(self, backend_type: str) -> str:
        if backend_type == "FastAPI":
            return """# backend.py - FastAPI fallback
from fastapi import FastAPI
app = FastAPI()
@app.get('/')
async def root(): return {"message": "Hello from FastAPI"}
"""
        return """# backend.py - Flask fallback
from flask import Flask
app = Flask(__name__)
@app.route('/')
def root(): return "Hello from Flask"
if __name__ == '__main__': app.run(debug=True, port=8000)
"""

    def combine_to_html(self, files: Dict[str, str]) -> str:
        html = files.get("index.html", "")
        css = files.get("styles.css", "")
        js = files.get("script.js", "")

        # Inject CSS
        if "</head>" in html:
            html = html.replace("</head>", f"<style>\n{css}\n</style>\n</head>")
        else:
            html = f"<head><style>\n{css}\n</style></head>\n{html}"

        # Inject JS
        if "</body>" in html:
            html = html.replace("</body>", f"<script>\n{js}\n</script>\n</body>")
        else:
            html += f"\n<script>\n{js}\n</script>"

        return html


# -----------------------------------------------------------------------------
# ZIP creation helper (exported as create_zip_bytes)
# -----------------------------------------------------------------------------
def create_zip_bytes(files: Dict[str, str]) -> bytes:
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fname, content in files.items():
            zf.writestr(fname, content.encode("utf-8") if isinstance(content, str) else content)
    mem_zip.seek(0)
    return mem_zip.read()


# -----------------------------------------------------------------------------
# Diff Renderer
# -----------------------------------------------------------------------------
class HtmlDiffRenderer:
    def render(self, a: str, b: str, fromdesc: str = "A", todesc: str = "B", fname: str = "file") -> str:
        a_lines = a.splitlines()
        b_lines = b.splitlines()
        differ = difflib.HtmlDiff(wrapcolumn=80)
        html_table = differ.make_table(a_lines, b_lines, fromdesc=fromdesc, todesc=todesc, context=True, numlines=3)
        wrapper = f"""
<html><head><meta charset="utf-8">
<style>
body {{ font-family: sans-serif; }}
table.diff {{ width:100%; border-collapse:collapse; }}
td.diff_header {{ background:#f7f7f7; font-weight:bold; padding:6px; }}
td {{ padding:6px; vertical-align:top; white-space:pre-wrap; font-family: monospace; }}
.diff_add {{ background: #e6ffec; }}
.diff_chg {{ background: #fff8e1; }}
.diff_sub {{ background: #ffeef0; }}
</style>
</head><body><h4>Diff for {fname}</h4>{html_table}</body></html>
"""
        return wrapper