# main.py
import streamlit as st
import os
import base64
from datetime import datetime
from ai.utils import WebsiteGenerator, create_zip_bytes
from ai.deploy import GitHubDeployer

# -------------------------------------------------------
# 1. Configuration & Page Icon Logic
# -------------------------------------------------------
# Check for an image in the 'images' folder to use as the Page Icon
page_icon = "⚡"  # Default
if os.path.exists("images"):
    # Find first image file (png, jpg, jpeg, ico, svg)
    valid_exts = [".png", ".jpg", ".jpeg", ".ico", ".svg"]
    for file in os.listdir("images"):
        if any(file.lower().endswith(ext) for ext in valid_exts):
            page_icon = os.path.join("images", file)
            break

st.set_page_config(
    page_title="NexaBuild",
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="collapsed"
)


def load_custom_css():
    st.markdown("""
    <style>
        /* --- Global Variables --- */
        :root {
            --bg-color: #0d1117; /* GitHub Dark Dimmed */
            --card-bg: #161b22;
            --border-color: #30363d;
            --neon-cyan: #00f3ff;
            --neon-purple: #bc13fe;
            --text-primary: #c9d1d9;
            --text-white: #ffffff;
            --vscode-bg: #1e1e1e;
            --vscode-fg: #d4d4d4;
        }

        /* --- Main Background --- */
        .stApp {
            background-color: var(--bg-color);
            color: var(--text-primary);
        }

        /* --- Typography --- */
        h1, h2, h3 {
            color: var(--text-white) !important;
            font-family: 'Inter', sans-serif;
            font-weight: 700;
        }
        p, div, span {
            color: var(--text-primary);
            font-family: 'Inter', sans-serif;
        }

        /* --- Navbar/Footer Styling --- */
        .nav-container {
            background: rgba(22, 27, 34, 0.8);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--border-color);
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .nav-logo {
            font-size: 1.5rem;
            font-weight: bold;
            background: linear-gradient(90deg, var(--neon-cyan), var(--neon-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .nav-links a {
            color: var(--text-primary);
            text-decoration: none;
            margin-left: 20px;
            font-size: 0.9rem;
            transition: color 0.3s;
        }
        .nav-links a:hover {
            color: var(--neon-cyan);
        }

        .footer-container {
            margin-top: 50px;
            padding: 30px;
            border-top: 1px solid var(--border-color);
            text-align: center;
            background: var(--card-bg);
            font-size: 0.9rem;
        }
        .footer-link {
            color: var(--neon-cyan);
            text-decoration: none;
            font-weight: bold;
        }

        /* --- VS Code Style Editor (Text Area) --- */
        textarea {
            background-color: var(--vscode-bg) !important;
            color: var(--vscode-fg) !important;
            font-family: 'Consolas', 'Courier New', monospace !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 4px !important;
            padding: 10px !important;
        }
        /* Fix specific Streamlit Text Area Wrapper */
        .stTextArea > div > div {
            background-color: var(--vscode-bg);
            border: 1px solid var(--border-color);
        }

        /* --- Chat Input & Standard Inputs --- */
        .stTextInput input, .stChatInput textarea {
            background-color: #0d1117 !important;
            color: white !important;
            border: 1px solid var(--border-color) !important;
        }

        /* --- Buttons (High Visibility) --- */
        .stButton > button {
            background: var(--neon-cyan) !important;
            color: #000000 !important; /* Black text for contrast */
            border: none;
            font-weight: bold;
            transition: transform 0.2s;
        }
        .stButton > button:hover {
            transform: scale(1.02);
            box-shadow: 0 0 10px var(--neon-cyan);
        }

        /* Secondary Button Style (if needed) */
        div[data-testid="stHorizontalBlock"] button {
            background: #21262d !important;
            color: var(--neon-cyan) !important;
            border: 1px solid var(--border-color) !important;
        }
        div[data-testid="stHorizontalBlock"] button:hover {
            border-color: var(--neon-cyan) !important;
        }

        /* --- Glass Cards --- */
        .glass-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }

        /* --- Sidebar --- */
        [data-testid="stSidebar"] {
            background-color: #010409;
            border-right: 1px solid #30363d;
        }
    </style>
    """, unsafe_allow_html=True)


load_custom_css()

# -------------------------------------------------------
# 2. Session State
# -------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "home"
if "files" not in st.session_state:
    st.session_state.files = {}
if "chat" not in st.session_state:
    st.session_state.chat = []
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Preview"


# -------------------------------------------------------
# 3. Global Components (Header/Footer)
# -------------------------------------------------------
def render_header():
    # Default text logo
    logo_html = "⚡ NexaBuild"

    # Check for logo in images directory
    if os.path.exists("images"):
        # Find any file starting with 'logo' (e.g., logo.png, logo.jpg)
        logo_file = next((f for f in os.listdir("images") if f.lower().startswith("logo.")), None)

        if logo_file:
            try:
                with open(os.path.join("images", logo_file), "rb") as f:
                    encoded_string = base64.b64encode(f.read()).decode()

                ext = logo_file.split('.')[-1].lower()
                mime_type = f"image/{'svg+xml' if ext == 'svg' else ext}"

                # Create HTML image tag
                logo_html = f'<img src="data:{mime_type};base64,{encoded_string}" style="height: 40px; border-radius: 6px;"> NexaBuild'
            except Exception as e:
                print(f"Error loading logo: {e}")

    st.markdown(f"""
    <div class="nav-container">
        <div class="nav-logo">{logo_html}</div>
        <div class="nav-links">
            <a href="#">Home</a>
            <a href="#">Features</a>
            <a href="#">About</a>
            <a href="mailto:@gmail.com" style="color: var(--neon-cyan); border: 1px solid var(--neon-cyan); padding: 5px 10px; border-radius: 5px;">Contact Us</a>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_footer():
    st.markdown("""
    <div class="footer-container">
        <p>Built with ❤️ using Gemini AI</p>
        <p>Need help? <a href="mailto:nexabuild@gmail.com" class="footer-link">Contact Support (nexabuild@gmail.com)</a></p>
        <p style="font-size: 0.8rem; color: #666; margin-top: 10px;">© 2025 NexaBuild. All rights reserved.</p>
    </div>
    """, unsafe_allow_html=True)


# -------------------------------------------------------
# 4. Page: Home
# -------------------------------------------------------
def render_home():
    render_header()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; font-size: 3rem;'>Build Your Dream Website</h1>",
                    unsafe_allow_html=True)
        st.markdown(
            "<p style='text-align: center; font-size: 1.1rem; margin-bottom: 30px;'>Enter a prompt, and let our AI write the code for you.</p>",
            unsafe_allow_html=True)

        # Input Card
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### ⌨️ What do you want to build?")

        with st.form("home_prompt"):
            prompt = st.text_area(
                "Prompt",
                height=120,
                placeholder="e.g. A dark-themed portfolio for a photographer with a gallery grid and contact form...",
                label_visibility="collapsed"
            )

            # Button Row
            b_col1, b_col2 = st.columns([3, 1])
            with b_col2:
                submitted = st.form_submit_button("✨ Generate Site", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

        if submitted and prompt:
            with st.spinner("🤖 Analyzing requirements & writing code..."):
                try:
                    gen = WebsiteGenerator(model="gemini-2.5-flash")
                    result = gen.generate_website(prompt)

                    st.session_state.files = result["files"]
                    st.session_state.chat.append(("user", prompt))
                    st.session_state.chat.append(("ai", "I've created the first version. Check the 'Preview' tab!"))
                    st.session_state.page = "workspace"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    render_footer()


# -------------------------------------------------------
# 5. Page: Workspace
# -------------------------------------------------------
def render_workspace():
    render_header()

    # Top Bar
    col_head1, col_head2 = st.columns([6, 1])
    with col_head1:
        st.markdown("### 🛠️ Workspace")
    with col_head2:
        if st.button("🏠 Exit"):
            st.session_state.page = "home"
            st.session_state.files = {}
            st.session_state.chat = []
            st.rerun()

    st.markdown("---")

    # Sidebar Chat
    with st.sidebar:
        st.markdown("### 💬 AI Assistant")

        # Chat History
        for role, msg in st.session_state.chat:
            if role == "user":
                st.info(f"👤 {msg}")
            else:
                st.success(f"🤖 {msg}")

        # Chat Input
        st.markdown("---")
        user_input = st.chat_input("Type changes here (e.g., 'Make bg blue')...")
        if user_input:
            st.session_state.chat.append(("user", user_input))
            with st.spinner("Applying changes..."):
                try:
                    gen = WebsiteGenerator()
                    updated = gen.edit_files(user_input, st.session_state.files)
                    st.session_state.files = updated
                    st.session_state.chat.append(("ai", "Done! Preview updated."))
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # Main Area
    tab_preview, tab_code, tab_deploy = st.tabs(["👁️ Preview", "💻 Code Editor", "🚀 Export & Deploy"])

    # TAB 1: PREVIEW
    with tab_preview:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        gen = WebsiteGenerator()
        html_preview = gen.combine_to_html(st.session_state.files)
        st.components.v1.html(html_preview, height=750, scrolling=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # TAB 2: CODE EDITOR (VS Code Style)
    with tab_code:
        col_list, col_editor = st.columns([1, 4])

        with col_list:
            st.markdown("##### Files")
            selected_file = st.radio("Select File", list(st.session_state.files.keys()), label_visibility="collapsed")

        with col_editor:
            st.markdown(f"##### Editing: `{selected_file}`")
            # This text area is styled by CSS to look like VS Code
            new_code = st.text_area(
                "Code Editor",
                value=st.session_state.files[selected_file],
                height=600,
                label_visibility="collapsed",
                key=f"editor_{selected_file}"
            )

            if new_code != st.session_state.files[selected_file]:
                if st.button(f"💾 Save Changes to {selected_file}"):
                    st.session_state.files[selected_file] = new_code
                    st.success("File Saved!")
                    st.rerun()

    # TAB 3: EXPORT / DEPLOY
    with tab_deploy:
        st.markdown("### 📦 Export Project")

        # Download Box
        st.markdown("""
        <div class="glass-card" style="border-left: 4px solid var(--neon-cyan);">
            <h4>Download Source Code</h4>
            <p>Get the full source code as a ZIP file to use locally or upload to Netlify/Vercel.</p>
        </div>
        """, unsafe_allow_html=True)

        zip_bytes = create_zip_bytes(st.session_state.files)
        st.download_button(
            label="⬇️ Download ZIP Package",
            data=zip_bytes,
            file_name="my-website-project.zip",
            mime="application/zip",
            type="primary"
        )

        st.markdown("---")
        st.markdown("### 🐙 GitHub Pages Deploy")

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            repo_name = st.text_input("Repository Name", "my-ai-site")
        with col_d2:
            gh_token = st.text_input("GitHub Token", type="password")

        if st.button("🚀 Deploy to GitHub"):
            if not gh_token:
                st.error("GitHub Token is required.")
            else:
                with st.spinner("Deploying..."):
                    try:
                        deployer = GitHubDeployer(gh_token)
                        res = deployer.deploy_to_github_pages(repo_name, st.session_state.files)
                        st.success(f"Live at: {res['url']}")
                        st.markdown(f"[Open Website]({res['url']})")
                    except Exception as e:
                        st.error(f"Deploy failed: {e}")

    render_footer()


# -------------------------------------------------------
# 6. Main Router
# -------------------------------------------------------
if st.session_state.page == "home":
    render_home()
else:
    render_workspace()
