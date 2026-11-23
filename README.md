# Code Documentation Generator

A Streamlit application that uses the Gemini API to generate Python docstrings and a README.md for an uploaded `.py` file.

## Features

- Upload a Python source file.
- Analyse modules, classes, functions, and methods using Python's AST module.
- Generate missing docstrings with Gemini.
- Preserve existing docstrings.
- Generate a README.md based on the uploaded source.
- Download the documented Python file and README separately.
- Insert generated docstrings into the original source instead of asking the LLM to rewrite the program.

## Tech stack

- Python
- Streamlit
- Google Gen AI Python SDK (`google-genai`)
- python-dotenv
- Python AST and tokenize modules

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env`.
4. Add your Gemini API key to `.env`:

   ```env
   GEMINI_API_KEY=your_actual_api_key
   GEMINI_MODEL=gemini-3.8-flash
   ```

5. Start the application:

   ```bash
   streamlit run app.py
   ```

6. Open the local URL shown in the terminal, upload a `.py` file, and click **Generate documentation**.

## Security

Never commit `.env` or publish your API key. The `.gitignore` file excludes `.env` and common virtual-environment folders.

## Current limitations

- UTF-8 Python files up to 200 KB are supported by the demo UI.
- Generated documentation should be reviewed for accuracy before using it in production.
- The application does not execute uploaded Python code.
