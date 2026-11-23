from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from code_utils import CodeAnalysisError, analyze_python_source, insert_docstrings
from generator import GeminiGenerationError, generate_documentation

load_dotenv()

st.set_page_config(
    page_title="Code Documentation Generator",
    page_icon="📘",
    layout="wide",
)

st.title("📘 Code Documentation Generator")
st.write(
    "Upload a Python file to generate useful docstrings and a project README "
    "with Gemini. Your original program logic is preserved; generated "
    "docstrings are inserted into the source file."
)

with st.sidebar:
    st.header("Project details")
    project_name = st.text_input("Project name", placeholder="e.g. Student Management System")
    project_context = st.text_area(
        "Additional context (optional)",
        placeholder="Briefly describe what the project is intended to do.",
        height=120,
    )
    st.caption("The Gemini API key is read from your local .env file. Do not upload it to GitHub.")

uploaded_file = st.file_uploader("Upload a Python file", type=["py"])

if uploaded_file is not None:
    raw_bytes = uploaded_file.getvalue()

    if len(raw_bytes) > 200_000:
        st.error("This demo currently supports Python files up to 200 KB.")
        st.stop()

    try:
        source_code = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        st.error("The uploaded file is not UTF-8 encoded. Save it as UTF-8 and upload it again.")
        st.stop()

    try:
        analysis = analyze_python_source(source_code)
    except CodeAnalysisError as exc:
        st.error(str(exc))
        st.stop()

    st.success(f"Loaded **{uploaded_file.name}** successfully.")
    col1, col2, col3 = st.columns(3)
    col1.metric("Lines of code", analysis["line_count"])
    col2.metric("Functions / methods", analysis["function_count"])
    col3.metric("Classes", analysis["class_count"])

    with st.expander("Preview uploaded Python code"):
        st.code(source_code, language="python", line_numbers=True)

    if st.button("Generate documentation", type="primary", use_container_width=True):
        try:
            with st.spinner("Gemini is analysing your code and generating documentation..."):
                result = generate_documentation(
                    source_code=source_code,
                    targets=analysis["targets"],
                    api_key=None,
                    project_name=project_name.strip() or Path(uploaded_file.name).stem,
                    project_context=project_context.strip(),
                )
                documented_code, inserted_count = insert_docstrings(
                    source_code,
                    analysis["targets"],
                    result["docstrings"],
                )

            st.session_state["generated"] = {
                "code": documented_code,
                "readme": result["readme"],
                "inserted_count": inserted_count,
                "filename": Path(uploaded_file.name).name,
                "project_name": project_name.strip() or Path(uploaded_file.name).stem,
            }
        except (GeminiGenerationError, CodeAnalysisError) as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")

if "generated" in st.session_state:
    generated = st.session_state["generated"]
    st.divider()
    st.subheader("Generated documentation")
    st.success(
        f"Documentation generated. Added {generated['inserted_count']} new docstring(s). "
        "Existing docstrings were left unchanged."
    )

    code_tab, readme_tab = st.tabs(["Documented Python file", "README.md"])

    with code_tab:
        st.code(generated["code"], language="python", line_numbers=True)
        output_name = f"{Path(generated['filename']).stem}_documented.py"
        st.download_button(
            "Download documented Python file",
            data=generated["code"].encode("utf-8"),
            file_name=output_name,
            mime="text/x-python",
            use_container_width=True,
        )

    with readme_tab:
        st.markdown(generated["readme"])
        st.download_button(
            "Download README.md",
            data=generated["readme"].encode("utf-8"),
            file_name="README.md",
            mime="text/markdown",
            use_container_width=True,
        )
