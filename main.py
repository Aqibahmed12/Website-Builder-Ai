# main.py — AI Website Builder (Final Version)
# Works perfectly with the updated utils.py using google.generativeai only

import streamlit as st
from datetime import datetime
from ai.utils import WebsiteGenerator, create_zip_bytes
from ai.deploy import GitHubDeployer

# -------------------------------------------------------
# Streamlit Page Config
# -------------------------------------------------------
st.set_page_config(
    page_title="AI Website Builder",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------
# Session State Initialization
# -------------------------------------------------------
if "files" not in st.session_state:
    st.session_state.files = {
        "index.html": "<h1>Welcome</h1>",
        "styles.css": "body{font-family:Arial}",
        "script.js": "console.log('ready')"
    }

if "history" not in st.session_state:
    st.session_state.history = []

if "chat" not in st.session_state:
    st.session_state.chat = []

# -------------------------------------------------------
# Sidebar — Chat-based Editing (like Canva)
# -------------------------------------------------------
with st.sidebar:
    st.header("💬 AI Code Assistant")
    st.caption("Ask the AI to modify your website code.")

    chat_msg = st.text_area("Message", placeholder="Example: Add a hero section...")

    if st.button("Send"):
        try:
            gen = WebsiteGenerator()
            updated = gen.edit_files(chat_msg, st.session_state.files)

            st.session_state.files = updated
            st.session_state.chat.append(("user", chat_msg))
            st.session_state.chat.append(("ai", "✔ Changes applied successfully."))

            st.session_state.history.append({
                "time": str(datetime.now()),
                "action": "AI Edit",
                "files": updated.copy()
            })
            st.success("AI updated the website!")
        except Exception as e:
            st.error("AI Error: " + str(e))

    if st.session_state.chat:
        st.subheader("📝 Chat History")
        for role, msg in st.session_state.chat[-10:]:
            st.write(f"**{role}:** {msg}")

# -------------------------------------------------------
# Layout Columns (Left: Controls, Right: Preview)
# -------------------------------------------------------
left, right = st.columns([2, 3])

# -------------------------------------------------------
# Left Panel — Website Generator + Editor
# -------------------------------------------------------
with left:
    st.header("✨ Create a Website")

    prompt = st.text_area(
        "Describe your website",
        height=200,
        placeholder="Example: A modern portfolio website with navbar, hero section, cards, footer..."
    )

    model_choice = st.selectbox(
        "Choose Model",
        ["auto", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        index=0
    )

    if st.button("🚀 Generate Website"):
        try:
            gen = WebsiteGenerator(model=model_choice)
            result = gen.generate_website(prompt)

            st.session_state.files = result["files"]

            st.session_state.history.append({
                "time": str(datetime.now()),
                "action": "Generated Website",
                "files": st.session_state.files.copy()
            })

            st.success("Website created successfully!")
        except Exception as e:
            st.error("Generation Error: " + str(e))

    # ---------------------------------------------------
    # File Editor
    # ---------------------------------------------------
    st.subheader("🛠 Edit Files")

    fname = st.selectbox("Select file", list(st.session_state.files.keys()))

    code = st.text_area(
        f"Editing {fname}",
        st.session_state.files[fname],
        height=250
    )

    if st.button("💾 Save File"):
        st.session_state.files[fname] = code

        st.session_state.history.append({
            "time": str(datetime.now()),
            "action": f"Edited {fname}",
            "files": st.session_state.files.copy()
        })

        st.success("File saved.")

    # ---------------------------------------------------
    # Version History
    # ---------------------------------------------------
    st.subheader("📚 Version History")
    if st.session_state.history:
        for i, entry in enumerate(reversed(st.session_state.history[-10:])):
            with st.expander(f"{entry['time']} — {entry['action']}"):
                for fn in entry["files"].keys():
                    st.write(f"- {fn}")

                if st.button("Restore", key=f"restore_{i}"):
                    st.session_state.files = entry["files"].copy()
                    st.success("Restored version.")
                    st.stop()

    else:
        st.info("No versions yet.")


# -------------------------------------------------------
# Right Panel — Live Preview
# -------------------------------------------------------
with right:
    st.header("🌐 Live Preview")

    gen = WebsiteGenerator()
    html_preview = gen.combine_to_html(st.session_state.files)

    st.components.v1.html(html_preview, height=700, scrolling=True)

# -------------------------------------------------------
# Bottom Actions
# -------------------------------------------------------
st.markdown("---")
col1, col2 = st.columns(2)

# ------------------ Download ZIP -----------------------
with col1:
    st.subheader("📦 Download Project")

    zip_bytes = create_zip_bytes(st.session_state.files)
    st.download_button(
        "Download ZIP",
        data=zip_bytes,
        file_name="website.zip",
        mime="application/zip"
    )

# ------------------ GitHub Deploy -----------------------
with col2:
    st.subheader("🚀 Deploy to GitHub Pages")

    repo = st.text_input("Repository Name", "ai-website")
    token = st.text_input("GitHub Token", type="password")

    if st.button("Deploy"):
        try:
            dep = GitHubDeployer(token)
            result = dep.deploy_to_github_pages(repo, st.session_state.files)

            st.success("Deployed Successfully!")
            st.write("🌍 Live URL:", result["url"])
        except Exception as e:
            st.error("Deploy Error: " + str(e))
