<div align="center">

# ⚡ NexaBuild — AI Website Builder

**Generate complete websites from a single prompt using Google Gemini.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-2.5%20Flash-4285F4?style=flat&logo=google&logoColor=white)](https://ai.google.dev/)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-FF4B4B?style=flat&logo=streamlit)](https://website-builder-ai.streamlit.app/)

![NexaBuild Banner](images/)

</div>

---

## 🌐 Live Demo

👉 **[website-builder-ai.streamlit.app](https://website-builder-ai.streamlit.app/)**

---

## 📌 About

**NexaBuild** is a Generative AI-powered website builder that turns plain English descriptions into fully functional websites. Powered by **Google Gemini 2.5 Flash**, it generates HTML, CSS, and JavaScript instantly — no coding required.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 AI Generation | Describe your website in plain text and get full HTML/CSS/JS instantly |
| 💬 Chat to Edit | Refine your site by chatting with the AI (e.g. "make the background blue") |
| 👁️ Live Preview | See your generated website rendered in real time inside the app |
| 💻 Code Editor | Edit HTML, CSS, and JS files directly in a VS Code–style editor |
| 📦 ZIP Download | Download the complete source code as a ready-to-deploy ZIP package |
| 🚀 GitHub Pages Deploy | Deploy your site directly to GitHub Pages with one click |
| 📚 Version History | Track changes across AI edits in the session |

---

## 🛠️ Tech Stack

- **Python 3.10+**
- **Streamlit** — UI framework
- **Google Generative AI SDK** — `google-generativeai` (Gemini 2.5 Flash)
- **Requests** — GitHub Pages deployment API calls
- **python-dotenv** — API key management

---

## 📁 Project Structure

```
Website-Builder-Ai/
├── main.py              # Main Streamlit app (UI, routing, pages)
├── ai/
│   ├── utils.py         # WebsiteGenerator class, ZIP creation
│   └── deploy.py        # GitHubDeployer class for GitHub Pages
├── images/              # App logo and assets
├── requirements.txt     # Python dependencies
└── .gitignore
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Aqibahmed12/Website-Builder-Ai.git
cd Website-Builder-Ai
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up your Gemini API key

Create a `.env` file in the root directory:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

Get your free API key at [aistudio.google.com](https://aistudio.google.com/).

### 4. Run the app

```bash
streamlit run main.py
```

Open `http://localhost:8501` in your browser.

---

## 🧑‍💻 How to Use

1. **Describe your website** — Type a prompt like *"A dark portfolio for a photographer with a gallery grid and contact form"*
2. **Click Generate** — Gemini writes the HTML, CSS, and JS for you
3. **Preview instantly** — See your site live in the Preview tab
4. **Chat to refine** — Use the AI chat sidebar to request changes in plain English
5. **Edit manually** — Switch to the Code Editor tab for direct edits
6. **Export or deploy** — Download a ZIP or push to GitHub Pages

---

## 📦 Requirements

```
streamlit>=1.18
google-generativeai>=0.5.0
requests>=2.28
python-dotenv>=1.0
```

---

## 🔑 Environment Variables

| Variable | Description |
|---|---|
| `GOOGLE_API_KEY` | Your Google Gemini API key (required) |

For GitHub Pages deployment, you'll also need a **GitHub Personal Access Token** entered directly in the app UI.

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests to improve the project.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push and open a Pull Request

---

## 👤 Author

**Aqib Ahmed**
- GitHub: [@Aqibahmed12](https://github.com/Aqibahmed12)

---

## 📄 License

This project is open source. See the repository for details.
