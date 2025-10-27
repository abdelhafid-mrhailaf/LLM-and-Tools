# LLM Tooling Test

A minimal code to test different open source openai LLM (gpt-oss-120b) and their tool-calling behavior using the OpenAI Python module.

## Features
- Handles function/tool calls:
  - `push_information`
  - `web_search`
- Uses `rich` for colored logs
- Saves each run’s logs to `logs/run-<model>.md`

## Setup
1. Create `.env` with:
OPENAI_API_KEY=your_key
OPENAI_API_BASE=https://api.openai.com/v1

SERPER_API_KEY=your_serper_key
PUSHOVER_USER=your_user
PUSHOVER_TOKEN=your_token

2. Install and run deps:
```bash
pip install -r requirements.txt
python main.py