# streamlit_app.py
import streamlit as st
from pathlib import Path
import io

# Import all logic from the local utils.py file
from utils import (
    summarize_with_gemini, 
    get_video_id, 
    save_to_pdf, 
    save_to_excel
) 

st.set_page_config(page_title="Gemini Study Guide Generator", layout="centered")

# --- UI Layout ---
st.title("📚 AI Study Guide Generator")
st.markdown("Convert transcripts into structured, hyperlinked study notes using the Gemini API. Outputs: PDF notes (hyperlinked) and XLSX data sheets.")

# ----------------------------------------------------
# 1. SIDEBAR: BYO-API and URL Input
# ----------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuration (Required)")
    
    st.subheader("🔑 Gemini API Key")
    gemini_api_key = st.text_input(
        "Paste your Gemini API Key", 
        type="password", 
        help="This key is NOT stored. It's used once per session for the AI analysis."
    )
    
    st.subheader("🔗 Video Link")
    video_url = st.text_input(
        "YouTube Video URL",
        placeholder="https://www.youtube.com/watch?v=...",
        help="Required for generating clickable timestamps."
    )
    video_id = get_video_id(video_url)

# ----------------------------------------------------
# 2. MAIN AREA: Transcript Input
# ----------------------------------------------------
st.header("1️⃣ Paste Transcript")
transcript_text = st.text_area(
    "Video Transcript (with timestamps)", 
    height=300,
    placeholder="Example: [00:30] Welcome to the lesson. [01:15] Today we discuss the derivative."
)

# ----------------------------------------------------
# 3. PROCESSING AND DOWNLOAD
# ----------------------------------------------------
st.header("2️⃣ Generate Notes")
if st.button("Generate Study Guide", use_container_width=True, type="primary"):
    
    # --- Validation ---
    if not gemini_api_key:
        st.error("🛑 **API Key Required.** Please enter your Gemini API Key in the sidebar to proceed.")
        st.stop()
    if not transcript_text.strip():
        st.error("🛑 Please paste a transcript to begin.")
        st.stop()
    if not video_id:
        st.error("🛑 Please enter a valid YouTube URL.")
        st.stop()

    # --- API Call ---
    with st.spinner("Analyzing transcript and generating structured notes..."):
        summary_data = summarize_with_gemini(gemini_api_key, transcript_text)

    # --- Output and Download ---
    if summary_data:
        st.success("✅ Analysis complete! Your PDF and Excel files are ready for download.")
        st.subheader(f"Summary Title: {summary_data.get('main_subject', 'Untitled Summary')}")

        font_path = Path(".")
        base_name = "AI_Study_Guide"

        # --- MEMORY-SAFE FILES ---
        # PDF
        pdf_bytes_io = io.BytesIO()
        save_to_pdf(summary_data, video_id, font_path, pdf_bytes_io)
        pdf_bytes = pdf_bytes_io.getvalue()

        # Excel
        excel_bytes_io = io.BytesIO()
        save_to_excel(summary_data, excel_bytes_io)
        excel_bytes = excel_bytes_io.getvalue()

        # --- Tabs for Download ---
        tab_pdf, tab_excel = st.tabs(["📄 PDF Notes", "📊 Excel Sheet"])

        with tab_pdf:
            st.download_button(
                label="⬇️ Download PDF",
                data=pdf_bytes,
                file_name=f"{base_name}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        with tab_excel:
            st.download_button(
                label="⬇️ Download Excel",
                data=excel_bytes,
                file_name=f"{base_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        # --- Optional Preview ---
        st.markdown("### 🔍 Preview of First Topics")
        for topic in summary_data.get("topic_breakdown", [])[:3]:
            details_preview = ", ".join([d['detail'] for d in topic.get('details', [])])
            st.markdown(f"**{topic.get('topic', '')}**: {details_preview}")

    else:
        st.error("❌ Analysis failed. Please verify your API key and ensure the transcript is correctly formatted.")