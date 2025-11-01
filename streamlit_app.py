# streamlit_app.py

import streamlit as st
from pathlib import Path
import io

# Import all logic from the local utils.py file
# This assumes your utils.py file is present and correct.
from utils import (
    summarize_with_gemini, 
    get_video_id, 
    save_to_pdf, 
    save_to_excel
) 

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="AI Study Guide Generator",
    layout="centered",  # Centered layout is cleaner
    initial_sidebar_state="expanded"
)

# --- 2. Sidebar for Configuration (BYOA) ---
# This is the best place for API keys and global settings.
with st.sidebar:
    st.header("⚙️ Configuration")
    st.markdown("This app runs on a 'Bring Your Own API' model.")
    
    st.subheader("🔑 Gemini API Key")
    gemini_api_key = st.text_input(
        "Paste your Gemini API Key", 
        type="password", 
        help="Your key is not stored. It is only used for this session."
    )
    
    st.subheader("🔗 Video Link")
    video_url = st.text_input(
        "Paste the YouTube Video URL",
        placeholder="https://www.youtube.com/watch?v=...",
        help="Required for generating clickable timestamps in the PDF."
    )
    video_id = get_video_id(video_url)

# --- 3. Main Page Title ---
st.title("📚 AI Study Guide Generator")
st.markdown("Convert any video transcript into structured, hyperlinked study notes (PDF) and data (Excel).")

# Initialize session state to hold the summary data
if 'summary_data' not in st.session_state:
    st.session_state.summary_data = None

# --- 4. Input Card ---
# We use a native Streamlit container with a border for a clean "card" look.
with st.container(border=True):
    st.header("1. Paste Your Transcript")
    
    transcript_text = st.text_area(
        "Video Transcript (must include timestamps)", 
        height=300,
        placeholder="Example: [00:30] Welcome to the lesson. [01:15] Today we discuss the derivative.",
        label_visibility="collapsed"
    )

    generate_button = st.button(
        "Generate Study Guide", 
        use_container_width=True, 
        type="primary"
    )

# --- 5. Processing Logic ---
# This logic runs *only* when the generate button is clicked.
if generate_button:
    # Reset previous summary
    st.session_state.summary_data = None
    
    # --- Validation ---
    if not gemini_api_key:
        st.error("🛑 **API Key Required.** Please enter your Gemini API Key in the sidebar.")
    elif not transcript_text.strip():
        st.error("🛑 **Transcript Required.** Please paste a transcript to begin.")
    elif not video_id:
        st.error("🛑 **Valid URL Required.** Please enter a valid YouTube URL.")
    else:
        # --- API Call ---
        with st.spinner("Analyzing transcript and generating structured notes..."):
            try:
                summary_data = summarize_with_gemini(gemini_api_key, transcript_text)
                
                if summary_data:
                    # Store the result in session state to display it
                    st.session_state.summary_data = summary_data
                    st.success("✅ Analysis complete! Your download links are ready below.")
                else:
                    st.error("❌ **Analysis Failed.** The API returned an empty response. Please check your transcript or API key.")
            
            except Exception as e:
                st.error(f"❌ **An Error Occurred:** {e}")

# --- 6. Output Card ---
# This section *only* appears if 'summary_data' exists in the session state.
if st.session_state.summary_data:
    data = st.session_state.summary_data
    
    with st.container(border=True):
        st.header("2. Download Your Files")
        st.markdown(f"Your guide for **'{data.get('main_subject', 'Untitled Summary')}'** is ready.")

        # --- File Generation (In Memory) ---
        # This is the safe way to handle files in Streamlit for downloads.
        try:
            font_path = Path(".") # Assumes fonts are in the root directory
            base_name = "AI_Study_Guide"

            # --- PDF File ---
            pdf_bytes_io = io.BytesIO()
            save_to_pdf(data, video_id, font_path, pdf_bytes_io)
            pdf_bytes = pdf_bytes_io.getvalue()

            # --- Excel File ---
            excel_bytes_io = io.BytesIO()
            save_to_excel(data, excel_bytes_io)
            excel_bytes = excel_bytes_io.getvalue()

            # --- Download Buttons (in columns for a clean look) ---
            col1, col2 = st.columns(2)
            
            with col1:
                st.download_button(
                    label="⬇️ Download PDF Notes",
                    data=pdf_bytes,
                    file_name=f"{base_name}_Notes.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            with col2:
                st.download_button(
                    label="⬇️ Download Excel Sheet",
                    data=excel_bytes,
                    file_name=f"{base_name}_Data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

        except Exception as e:
            st.error(f"❌ **File Creation Error:** Failed to generate download files. Error: {e}")

