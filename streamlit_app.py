# streamlit_app.py

import streamlit as st
import tempfile
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
    
    # PASTE API KEY (Bring Your Own API System)
    st.subheader("🔑 Gemini API Key")
    gemini_api_key = st.text_input(
        "Paste your Gemini API Key", 
        type="password", 
        help="This key is NOT stored. It's used once per session for the AI analysis."
    )
    
    # Input URL (For Hyperlinking)
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

# PASTE TRANSCRIPT (Must contain timestamps)
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
    
    # --- Validation: Enforcing BYOA and Required Inputs ---
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
        # The user's key is securely passed here.
        summary_data = summarize_with_gemini(gemini_api_key, transcript_text)

    # --- Output and Download ---
    if summary_data:
        st.success("✅ Analysis complete! Your PDF and Excel files are ready for download.")
        st.subheader(f"Summary Title: {summary_data.get('main_subject', 'Untitled Summary')}")
        
        st.header("3️⃣ Download PDF and XLS Sheets")
        
        # Files are generated in temporary memory (Path(".")) for cloud safety
        font_path = Path(".") 
        base_name = "AI_Study_Guide"
        
        # Use tempfile for safe file handling in the cloud environment
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # --- REQUIRED OUTPUT 1: PDF (Hyperlinked Notes) ---
            pdf_path = temp_path / f"{base_name}.pdf"
            save_to_pdf(summary_data, video_id, font_path, pdf_path) 
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download Structured Notes (PDF)",
                    data=f.read(),
                    file_name=f"{base_name}.pdf",
                    mime="application/pdf"
                )

            # --- REQUIRED OUTPUT 2: XLSX (Excel Data Sheet) ---
            excel_path = temp_path / f"{base_name}.xlsx"
            save_to_excel(summary_data, excel_path)
            with open(excel_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download Summary Data (XLSX Sheet)",
                    data=f.read(),
                    file_name=f"{base_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
    else:
        st.error("❌ Analysis failed. Please verify your API key and ensure the transcript is correctly formatted.")
