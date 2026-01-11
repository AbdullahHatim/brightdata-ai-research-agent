# Bright Data AI Research Agent 🍋

An autonomous AI Research Agent that performs web searches (SERP), scrapes page content, and synthesizes answers using LLMs. Features a "basic" fast mode and a "deep discovery" mode for complex topics, all wrapped in a fresh Lemon-Themed Web GUI.

## Features

- **Gemini 3.0 Flash Preview Integration**: Uses Google's latest model for high-speed, low-cost reasoning.
- **Lemon Agent GUI**: A modern, clean web interface built with React + Vite and FastAPI.
- **Two Modes**:
  - **Basic (Fast)**: Classic SERP search + Synthesis. Good for quick facts.
  - **Deep Discovery**: Advanced multi-step research using Deep Search agents (Scrapers, Social Search).
- **History Tracking**: Automatically saves research sessions for later review.
- **Citations**: Every claim is backed by a verifiable source link.

## Prerequisites

- Python 3.10+
- Node.js & npm (for the GUI)
- **Bright Data Account**:
  - API Key
  - SERP API Zone (for basic search)
  - *Optional:* Web Unlocker / Dataset capabilities for deep mode.
- **Google Gemini API Key**: [Get one here](https://aistudio.google.com/)

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/mattvideoproductions/brightdata-ai-research-agent.git
   cd brightdata-ai-research-agent
   ```

2. **Set up Python Backend**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up React Frontend**:
   ```bash
   cd web_ui
   npm install
   cd ..
   ```

4. **Configuration**:
   Copy `.env.example` to `.env` and fill in your keys:
   ```bash
   cp .env.example .env
   ```
   **Required Settings**:
   ```ini
   # LLM Choice (Recommended: Gemini 3.0 Flash)
   LLM_PROVIDER="google"
   GOOGLE_API_KEY="your_gemini_key"
   GOOGLE_MODEL="gemini-3-flash-preview"

   # Bright Data
   BRIGHTDATA_API_KEY="your_bd_key"
   BRIGHTDATA_SERP_ZONE="serp_api1"
   ```
   *(Note: OpenAI and Ollama providers are theoretically supported but untested in this version).*

## Usage

### Run the GUI (Recommended)

You need two terminal windows:

**Terminal 1 (Backend):**
```bash
source .venv/bin/activate
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

**Terminal 2 (Frontend):**
```bash
cd web_ui
npm run dev
```

Open **http://localhost:5173** in your browser.

- Enter your question.
- Toggle between **Basic** and **Discovery** modes.
- Access **History** via the clock icon in the top right.

### CLI Usage (Legacy)
You can still run agents directly from the command line:
```bash
# Basic Agent
python -m basic_agent "What is the latest on Quantum Computing?"

# Web Discovery Agent
python -m web_discovery_agent "Analyze the market trends for NVDA vs AMD"
```

## Project Structure

- `basic_agent/`: Simple SERP-based research logic.
- `web_discovery_agent/`: Advanced logic (Social search, Deep scraping).
- `shared/`: Common utilities (LLM abstraction, Bright Data client).
- `server.py`: FastAPI backend.
- `web_ui/`: React frontend.
- `outputs/`: JSON/Markdown logs of all runs.

## License
MIT
