# streamlit_app.py

import streamlit as st
from pathlib import Path
import io
import json
import re

# Import all logic from the local utils.py file
from utils import (
    summarize_with_gemini, 
    get_video_id, 
    save_to_pdf, 
    save_to_excel,
    format_timestamp,
    COLORS
) 

# --- Custom macOS CSS Injection ---
def inject_mac_theme():
    css = f"""
    <style>
    /* Global Theme and Typography (SF Pro is simulated by Inter) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    :root {{
        --mac-bg: #F5F5F7;
        --mac-accent: #007AFF;
        --mac-accent-hover: #0060e6;
        --mac-gray: #8E8E93;
        --mac-text: #1D1D1F;
        --mac-shadow: rgba(0, 0, 0, 0.08);
        --mac-radius: 10px;
    }}

    html, body, .stApp {{
        font-family: 'Inter', sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
        color: var(--mac-text);
        background-color: var(--mac-bg);
    }}

    /* Main Headers */
    .stApp header h1 {{
        font-weight: 700;
        text-align: center;
        color: var(--mac-text);
        font-size: 2.2rem;
        margin-bottom: 0;
        padding-top: 15px;
    }}
    h2 {{ /* Section Headings */
        font-weight: 500;
        color: var(--mac-text);
        border-bottom: 1px solid rgba(0, 0, 0, 0.05);
        padding-bottom: 5px;
        margin-top: 15px;
    }}

    /* Sidebar, Inputs, and Text Areas */
    .stSidebar {{
        background-color: white !important;
        padding: 1rem 0.5rem;
        border-right: 1px solid rgba(0, 0, 0, 0.05);
        box-shadow: 2px 0 10px var(--mac-shadow);
    }}
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {{
        border-radius: var(--mac-radius) !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        padding: 10px !important;
    }}
    .stTextInput label, .stTextArea label {{
        font-weight: 500;
        color: var(--mac-text);
    }}

    /* Card Styling */
    .card-container {{
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 10px var(--mac-shadow);
        border: 1px solid rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }}

    /* Primary Button Styling (macOS Accent) */
    .stButton>button {{
        background-color: var(--mac-accent) !important;
        color: white !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 10px 18px !important;
        font-weight: 500;
        transition: background-color 0.1s ease, box-shadow 0.1s ease;
    }}
    .stButton>button:hover {{
        background-color: var(--mac-accent-hover) !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
    }}

    /* Download Button Styling */
    .stDownloadButton>button {{
        background-color: var(--mac-bg) !important;
        color: var(--mac-text) !important;
        border: 1px solid rgba(0, 0, 0, 0.15) !important;
        border-radius: 8px !important;
        transition: background-color 0.1s ease, border-color 0.1s ease;
        padding: 8px 12px !important;
        font-weight: 500;
        width: 100%;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    }}
    .stDownloadButton>button:hover {{
        background-color: rgba(0, 0, 0, 0.03) !important;
        border-color: rgba(0, 0, 0, 0.2);
    }}
    
    /* Custom Notification Style */
    .stAlert {{
        border-radius: 10px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

st.set_page_config(page_title="Gemini Study Guide Generator", layout="wide")
inject_mac_theme() # Apply macOS theme

st.title("📚 AI Study Guide Generator")
st.markdown("Minimalistic notes generator for academic content. Outputs: PDF notes (hyperlinked) and XLSX data sheets.")

# Initialize session state for preview if not present
if 'summary_data' not in st.session_state:
    st.session_state.summary_data = None

# --- Main Layout: Two Columns ---
col_input, col_preview = st.columns([1, 1.2])

# ----------------------------------------------------
# 1. SIDEBAR: BYO-API and URL Input
# ----------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Configuration (Required)")
    
    # PASTE API KEY (Bring Your Own API System)
    st.markdown("#### 🔑 Gemini API Key")
    gemini_api_key = st.text_input(
        "Paste your Gemini API Key", 
        type="password", 
        key="api_key_input",
        label_visibility="collapsed",
        placeholder="Enter your Gemini API Key..."
    )
    
    # Input URL (For Hyperlinking)
    st.markdown("#### 🔗 Video Link")
    video_url = st.text_input(
        "YouTube Video URL",
        key="url_input",
        label_visibility="collapsed",
        placeholder="https://www.youtube.com/watch?v=...",
        help="Required for clickable timestamps."
    )
    video_id = get_video_id(video_url)

# ----------------------------------------------------
# 2. INPUT COLUMN
# ----------------------------------------------------
with col_input:
    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    st.markdown("## 1️⃣ Input Transcript")

    # PASTE TRANSCRIPT (Must contain timestamps)
    transcript_text = st.text_area(
        "Video Transcript (with timestamps)", 
        height=450,
        placeholder="[00:05] The lecture begins. [01:30] We introduce the core topic...",
        key="transcript_input"
    )

    if st.button("Generate Study Guide", use_container_width=True):
        # --- Validation: Enforcing BYOA and Required Inputs ---
        if not gemini_api_key:
            st.error("🛑 **API Key Required.** Please enter your Gemini API Key in the sidebar.")
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

        if summary_data:
            st.session_state.summary_data = summary_data
            st.experimental_rerun() # Rerun to update preview column
        else:
            st.session_state.summary_data = None
            st.error("❌ Analysis failed. Please verify your API key and transcript.")
            
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------------------------------------------
# 3. PREVIEW/OUTPUT COLUMN
# ----------------------------------------------------
with col_preview:
    if st.session_state.summary_data:
        data = st.session_state.summary_data
        st.markdown('<div class="card-container">', unsafe_allow_html=True)
        st.markdown("## 2️⃣ Generated Output")
        st.success(f"✅ Success! **{data.get('main_subject', 'Untitled Summary')}**")

        st.markdown("### 📄 Preview of Topics")
        
        # --- Topic Preview ---
        for i, topic_item in enumerate(data.get("topic_breakdown", [])):
            topic_title = topic_item.get('topic', 'Topic')
            details_count = len(topic_item.get('details', []))
            
            with st.expander(f"**{topic_title}** ({details_count} key points)"):
                for detail in topic_item.get('details', [])[:5]: # Limit details for brevity
                    time_sec = detail.get('time', 0)
                    time_str = format_timestamp(time_sec)
                    detail_text = detail.get('detail', 'No detail provided')
                    # Replace <hl> tags with bold markdown for preview
                    preview_text = detail_text.replace('<hl>', '**').replace('</hl>', '**')
                    st.markdown(f"• **`{time_str}`**: {preview_text}")
                if details_count > 5:
                    st.markdown(f"*... and {details_count - 5} more points.*")

        st.markdown("---")
        
        # --- Downloads (Using Tabs as requested) ---
        st.markdown("### 💾 Downloads")
        tab_pdf, tab_excel = st.tabs(["📄 PDF Notes", "📊 Excel Sheet"])

        font_path = Path(".") 
        base_name = "AI_Study_Guide"
        
        # Use io.BytesIO for efficient in-memory file streaming
        pdf_bytes_io = io.BytesIO()
        save_to_pdf(data, video_id, font_path, pdf_bytes_io)
        pdf_bytes = pdf_bytes_io.getvalue()

        excel_bytes_io = io.BytesIO()
        save_to_excel(data, excel_bytes_io)
        excel_bytes = excel_bytes_io.getvalue()
        
        with tab_pdf:
            st.markdown("Download your hyperlinked study guide, perfect for reading.")
            st.download_button(
                label="⬇️ Download PDF (Notes)",
                data=pdf_bytes,
                file_name=f"{base_name}_Notes.pdf",
                mime="application/pdf"
            )

        with tab_excel:
            st.markdown("Download the raw, structured data table for analysis.")
            st.download_button(
                label="⬇️ Download Excel (Data)",
                data=excel_bytes,
                file_name=f"{base_name}_Data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    else:
        st.info("💡 **Ready to Start:** Enter your API Key and a YouTube URL in the sidebar, then paste your transcript on the left to generate the study guide.")
