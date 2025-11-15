# main.py
# AI Website Builder - Streamlit app (Upgraded)
#
# Enhancements:
# - Added st.text_input (type="password") for Google AI API Key.
# - Added st.selectbox for model selection (Gemini 1.5 Pro, etc.).
# - API Key and Model are passed to WebsiteGenerator.
# - Chat "Send" logic now checks if the AI response is a file update (dict)
#   or a simple text message (str) and handles it.

import os
import time
from datetime import datetime, timezone

import streamlit as st
import streamlit.components.v1 as components

from ai.utils import WebsiteGenerator, create_zip_bytes, HtmlDiffRenderer
from ai.deploy import GitHubDeployer


# -----------------------------------------------------------------------------
# Compatibility helpers
# -----------------------------------------------------------------------------
def safe_rerun():
    """
    Attempt to trigger a Streamlit rerun in a way that works across different
    Streamlit versions.
    """
    try:
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
            return
    except Exception:
        pass

    try:
        from streamlit.runtime.scriptrunner import RerunException  # type: ignore
        raise RerunException("User requested rerun via safe_rerun()")
    except Exception:
        st.session_state["_rerun_flag"] = not st.session_state.get("_rerun_flag", False)
        st.stop()


# -----------------------------------------------------------------------------
# Streamlit App Initialization and Configuration
# -----------------------------------------------------------------------------
st.set_page_config(page_title="AI Website Builder", layout="wide", initial_sidebar_state="expanded")

st.markdown("<h1 style='text-align:center'>AI Website Builder</h1>", unsafe_allow_html=True)

# Initialize session state
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "versions" not in st.session_state:
    st.session_state.versions = []
if "current_files" not in st.session_state:
    st.session_state.current_files = {
        "index.html": "",
        "styles.css": "/* styles */",
        "script.js": "// js"
    }
if "llm_error" not in st.session_state:
    st.session_state.llm_error = None

# -----------------------------------------------------------------------------
# Sidebar: API Keys, Model Selection, Chat
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuration")

    # --- NEW: API Key and Model Selection ---
    st.subheader("AI Setup")

    # Try to get key from environment, but allow user input
    default_key = os.environ.get("GOOGLE_API_KEY") or ""
    google_api_key = st.text_input(
        "Google AI API Key",
        value=default_key,
        type="password",
        help="Get your key from Google AI Studio. The app will use this key."
    )

    # Let user select the model
    model_selection = st.selectbox(
        "Select Model",
        ("gemini-2.5-flash", "gemini-1.5-pro-latest", "gemini-1.5-flash-latest", "gemini-pro"),
        index=0,
        help="Gemini 1.5 Pro is powerful but slower. 1.5 Flash is very fast."
    )

    # --- Instantiate helpers ---
    # Pass the user-provided key and model to the generator
    hf_token = os.environ.get("HUGGINGFACEHUB_API_TOKEN")
    github_token = os.environ.get("GITHUB_TOKEN")

    generator = WebsiteGenerator(
        api_key=google_api_key,
        model=model_selection,
        hf_token=hf_token
    )
    deployer = GitHubDeployer(github_token)

    if not google_api_key:
        st.warning("Please enter your Google AI API Key to enable AI features.")

    st.markdown("---")
    st.header("💬 Chat")
    st.subheader("Refine your site")
    st.caption("e.g., 'Make the header text centered' or 'Add a button'")

    # Chat panel
    chat_col1, chat_col2 = st.columns([4, 1])
    with chat_col1:
        chat_input = st.text_input("Message to AI", key="chat_input", label_visibility="collapsed")
    with chat_col2:
        if st.button("Send", key="send_chat", disabled=(not google_api_key)):
            if chat_input and chat_input.strip():
                st.session_state.chat_messages.append({"role": "user", "text": chat_input.strip()})

                try:
                    # --- NEW: Chat logic ---
                    # The generator will now return EITHER a string (chat)
                    # OR a dict (if files were updated)
                    with st.spinner("AI is thinking..."):
                        assistant_reply = generator.chat_response(
                            st.session_state.chat_messages,
                            st.session_state.current_files
                        )

                    if isinstance(assistant_reply, dict):
                        # This was a file update!
                        files_updated = assistant_reply.get("files_updated", {})
                        chat_message = assistant_reply.get("message", "I've updated the files as you requested.")

                        # Update files in session state
                        st.session_state.current_files.update(files_updated)

                        # Add a new version
                        st.session_state.versions.append({
                            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "files": st.session_state.current_files.copy(),
                            "message": f"Chat edit: {chat_input}"
                        })
                        st.session_state.chat_messages.append({"role": "assistant", "text": chat_message})
                        st.toast("✅ AI updated your files!")

                    else:
                        # This was a simple text reply
                        st.session_state.chat_messages.append({"role": "assistant", "text": assistant_reply})

                except Exception as e:
                    st.session_state.llm_error = str(e)
                    st.session_state.chat_messages.append(
                        {"role": "assistant", "text": generator.fallback_chat_reply(chat_input)})

                safe_rerun()

    # Display chat history
    with st.container(height=300):
        for msg in st.session_state.chat_messages[-20:]:
            with st.chat_message(msg["role"]):
                st.markdown(msg['text'])

# -----------------------------------------------------------------------------
# Main Area: Prompt input, buttons, preview, editable code
# -----------------------------------------------------------------------------
left_col, right_col = st.columns([2, 3])

with left_col:
    st.subheader("🚀 Describe your website")
    prompt = st.text_area("Tell the AI what you want (e.g., 'A landing page for a SaaS that sells cookbooks...')",
                          height=200, key="prompt_input")

    # Options
    st.subheader("Options")
    responsive_toggle = st.checkbox("Include responsive mobile version", value=True)
    include_backend = st.selectbox("Backend", ["None", "Flask", "FastAPI"], index=0,
                                   help="Backend file generation is experimental.")
    theme_choice = st.selectbox("Auto Theme Mode", ["Auto (match system)", "Light", "Dark"], index=0)

    # Buttons
    gen_col1, gen_col2, gen_col3 = st.columns(3)
    if gen_col1.button("Generate Website (AI)", disabled=(not google_api_key)):
        st.session_state._last_action = "generate"
        st.session_state._generate_time = time.time()
    if gen_col2.button("Preview Website"):
        st.session_state._last_action = "preview"
    if gen_col3.button("Download ZIP"):
        st.session_state._last_action = "download"

    st.markdown("---")
    st.subheader("🕰️ Version History")
    if st.session_state.versions:
        versions = st.session_state.versions[::-1]  # show recent first
        for idx, ver in enumerate(versions):
            with st.expander(f"{ver['timestamp']} — {ver.get('message', 'auto-generated')}"):
                st.write("Files:")
                for fname in ver["files"].keys():
                    st.write(f"- {fname}")
                if st.button(f"Restore Version {idx}", key=f"restore_{idx}"):
                    st.session_state.current_files = ver["files"].copy()
                    st.success("Restored version.")
                    safe_rerun()
    else:
        st.info("No versions yet. Generate a website to create versions.")

with right_col:
    st.subheader("🖥️ Live Preview")
    preview_height = 700

    # perform actions based on last action
    last_action = st.session_state.get("_last_action", None)
    if last_action == "generate":
        if not prompt or prompt.strip() == "":
            st.warning("Please enter a description for your website.")
            st.session_state._last_action = None  # Reset action
        elif not google_api_key:
            st.error("Please enter your Google AI API Key in the sidebar to generate a site.")
            st.session_state._last_action = None  # Reset action
        else:
            with st.spinner("AI is building your website... This may take a moment."):
                try:
                    gen_result = generator.generate_website(
                        prompt=prompt,
                        include_backend=include_backend,
                        responsive=responsive_toggle
                    )
                    st.session_state.current_files = gen_result["files"]
                    st.session_state.versions.append({
                        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "files": gen_result["files"].copy(),
                        "message": prompt or "Generated site"
                    })
                    st.success("Website generated and saved to version history.")
                    st.session_state._last_action = "preview"
                except Exception as e:
                    st.session_state.llm_error = str(e)
                    st.error(f"AI model failed to generate the site: {e}")
                    st.info("Using fallback template.")
                    st.session_state.current_files = generator.fallback_site(prompt)
                    st.session_state.versions.append({
                        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "files": st.session_state.current_files.copy(),
                        "message": "Fallback generated site due to error"
                    })
                    st.session_state._last_action = "preview"

    # Show preview
    html_content = generator.combine_to_html(st.session_state.current_files)
    if theme_choice == "Dark":
        html_content = html_content.replace("<body", "<body data-theme='dark'")
    elif theme_choice == "Light":
        html_content = html_content.replace("<body", "<body data-theme='light'")

    components.html(html_content, height=preview_height, scrolling=True)

    # Editable code blocks
    st.subheader("✏️ Editable Files")
    file_keys = list(st.session_state.current_files.keys())
    # Ensure backend.py is last if it exists, as it's least likely to be edited
    if "backend.py" in file_keys:
        file_keys.sort(key=lambda x: "z" if x == "backend.py" else x)

    edit_fname = st.selectbox("Select file to edit", file_keys)
    if edit_fname:
        edited_code = st.text_area(f"Editing {edit_fname}", value=st.session_state.current_files[edit_fname],
                                   height=300, key=f"edit_{edit_fname}")
        if st.button("Save File", key="save_file"):
            st.session_state.current_files[edit_fname] = edited_code
            st.session_state.versions.append({
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "files": st.session_state.current_files.copy(),
                "message": f"Edited {edit_fname}"
            })
            st.success(f"Saved {edit_fname} to versions.")

    # Side-by-side diff view (compare last two versions)
    st.subheader("↔️ Diff (last two versions)")
    if len(st.session_state.versions) >= 2:
        newest = st.session_state.versions[-1]["files"]
        previous = st.session_state.versions[-2]["files"]
        diff_renderer = HtmlDiffRenderer()
        if edit_fname:
            src_a = previous.get(edit_fname, "")
            src_b = newest.get(edit_fname, "")
            diff_html = diff_renderer.render(src_a, src_b, fromdesc="previous", todesc="current", fname=edit_fname)
            components.html(diff_html, height=300, scrolling=True)
    else:
        st.info("Need at least 2 versions to show diffs.")

# -----------------------------------------------------------------------------
# Bottom Controls: Download and Deploy
# -----------------------------------------------------------------------------
st.markdown("---")
col_down, col_deploy, col_explain = st.columns([2, 2, 2])

with col_down:
    st.subheader("📦 Download")
    if st.button("Create & Download ZIP"):
        zip_bytes = create_zip_bytes(st.session_state.current_files)
        st.download_button("Download site ZIP", data=zip_bytes, file_name="ai_website.zip", mime="application/zip")

with col_deploy:
    st.subheader("☁️ Deploy to GitHub")
    deploy_repo_name = st.text_input("New GitHub repo name", value=f"ai-website-{int(time.time())}", key="deploy_repo")
    if st.button("Deploy to GitHub Pages", disabled=(not github_token)):
        if not github_token:
            st.error("GITHUB_TOKEN not set in environment. Deployment needs a GitHub Personal Access Token.")
        else:
            try:
                with st.spinner("Creating repository and pushing files..."):
                    deploy_result = deployer.deploy_to_github_pages(repo_name=deploy_repo_name,
                                                                    files=st.session_state.current_files,
                                                                    make_public=True)
                if deploy_result.get("url"):
                    st.success("Deployed successfully!")
                    st.markdown(f"**Live site URL:** {deploy_result['url']}")
                else:
                    st.error("Deployment returned no URL. Check GitHub.")
            except Exception as e:
                st.error(f"Deployment failed: {e}")

with col_explain:
    st.subheader("🧠 Code Explanation")
    explanation_target = st.selectbox("Select file to explain", list(st.session_state.current_files.keys()),
                                      key="explain_target")
    if st.button("Explain Code", disabled=(not google_api_key)):
        try:
            with st.spinner("AI is analyzing the code..."):
                explanation = generator.explain_code(st.session_state.current_files[explanation_target])
            st.write("Explanation:")
            st.markdown(explanation)
        except Exception as e:
            st.error("Failed to explain code. " + str(e))

# -----------------------------------------------------------------------------
# Error / info display
# -----------------------------------------------------------------------------
if st.session_state.llm_error:
    st.error("Last LLM error: " + st.session_state.llm_error)
    st.session_state.llm_error = None  # Clear error after showing

st.markdown("<hr><small>AI Website Builder - Upgraded Version. Ensure your API tokens are set.</small>",
            unsafe_allow_html=True)