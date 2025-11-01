# utils.py
# -*- coding: utf-8 -*-
import os
import json
import re
from pathlib import Path
import google.generativeai as genai
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import pandas as pd
from io import BytesIO

# --- Configuration and Constants ---

EXPECTED_KEYS = [
    "main_subject", "topic_breakdown", "key_vocabulary",
    "formulas_and_principles", "teacher_insights",
    "exam_focus_points", "common_mistakes_explained"
]

SYSTEM_PROMPT = """ ... (keep your SYSTEM_PROMPT here) ... """

COLORS = {
    "title_bg": (40, 54, 85), "title_text": (255, 255, 255),
    "heading_text": (40, 54, 85), "link_text": (0, 0, 255),
    "body_text": (30, 30, 30), "line": (220, 220, 220),
    "highlight_bg": (255, 255, 0)
}

# --- Helper Functions ---

def get_video_id(url: str) -> str | None:
    patterns = [
        r"(?<=v=)[^&#?]+", r"(?<=be/)[^&#?]+", r"(?<=live/)[^&#?]+",
        r"(?<=embed/)[^&#?]+", r"(?<=shorts/)[^&#?]+"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match: return match.group(0)
    return None

def clean_gemini_response(response_text: str) -> str:
    match = re.search(r'```json\s*(\{.*?\})\s*```|(\{.*?\})', response_text, re.DOTALL)
    if match: return match.group(1) if match.group(1) else match.group(2)
    return response_text.strip()

def summarize_with_gemini(api_key: str, transcript_text: str) -> dict | None:
    print("    > Sending transcript to Gemini API...")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro-latest')
        response = model.generate_content(f"{SYSTEM_PROMPT}\n\nTranscript:\n---\n{transcript_text}")
        cleaned_response = clean_gemini_response(response.text)
        return json.loads(cleaned_response)
    except Exception as e:
        print(f"    > An error occurred with the API call: {e}")
        return None

def format_timestamp(seconds: int) -> str:
    minutes = seconds // 60
    seconds = seconds % 60
    return f"[{minutes:02}:{seconds:02}]"

def ensure_valid_youtube_url(video_id: str) -> str:
    """Returns a properly formatted YouTube base URL."""
    return f"https://www.youtube.com/watch?v={video_id}"

# --- PDF Class ---
class PDF(FPDF):
    def __init__(self, font_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.font_name = "NotoSans"
        self.add_font(self.font_name, "", str(font_path / "NotoSans-Regular.ttf"))
        self.add_font(self.font_name, "B", str(font_path / "NotoSans-Bold.ttf"))

    def create_title(self, title):
        self.set_font(self.font_name, "B", 24)
        self.set_fill_color(*COLORS["title_bg"])
        self.set_text_color(*COLORS["title_text"])
        self.cell(0, 20, title, align="C", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(10)

    def create_section_heading(self, heading):
        self.set_font(self.font_name, "B", 16)
        self.set_text_color(*COLORS["heading_text"])
        self.cell(0, 10, heading, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*COLORS["line"])
        self.line(self.get_x(), self.get_y(), self.get_x() + 190, self.get_y())
        self.ln(5)

    def write_highlighted_text(self, text, style=''):
        self.set_font(self.font_name, style, 11)
        self.set_text_color(*COLORS["body_text"])
        parts = re.split(r'(<hl>.*?</hl>)', text)
        for part in parts:
            if part.startswith('<hl>'):
                highlight_text = part[4:-5]
                self.set_fill_color(*COLORS["highlight_bg"])
                self.set_font(self.font_name, 'B', 11)
                self.cell(self.get_string_width(highlight_text), 7, highlight_text, fill=True)
                self.set_font(self.font_name, style, 11)
            else:
                self.set_fill_color(255, 255, 255)
                self.write(7, part)
        self.ln()

# --- Save to Excel (supports BytesIO) ---
def save_to_excel(data: dict, output):
    flat_data = []
    for key, values in data.items():
        if key == "main_subject" or not values:
            continue
        section_name = key.replace('_', ' ').title()
        for item in values:
            row = {"Section": section_name}
            if isinstance(item, dict):
                if 'details' in item and isinstance(item['details'], list):
                    row["Topic"] = item.get('topic', '')
                    for detail in item['details']:
                        detail_row = row.copy()
                        detail_row["Detail"] = detail.get('detail', '')
                        detail_row["Time (s)"] = detail.get('time', 0)
                        flat_data.append(detail_row)
                else:
                    for sk, sv in item.items():
                        row[sk.replace('_', ' ').title()] = str(sv)
                    flat_data.append(row)
            else:
                flat_data.append({"Section": section_name, "Item": str(item)})

    df = pd.DataFrame(flat_data)
    if isinstance(output, BytesIO):
        df.to_excel(output, index=False, sheet_name="Summary")
        output.seek(0)
    else:
        df.to_excel(str(output), index=False, sheet_name="Summary")

# --- Save to PDF (supports BytesIO) ---
def save_to_pdf(data: dict, video_id: str, font_path: Path, output):
    base_url = ensure_valid_youtube_url(video_id)
    pdf = PDF(font_path=font_path)
    pdf.add_page()
    pdf.create_title(data.get("main_subject", "Video Summary"))

    for key, values in data.items():
        if key == "main_subject" or not values:
            continue
        pdf.create_section_heading(key.replace('_', ' ').title())
        for item in values:
            is_nested = any(isinstance(v, list) for v in item.values())
            if is_nested:
                pdf.set_font(pdf.font_name, "B", 11)
                pdf.multi_cell(0, 7, text=f"  {item.get('topic', '')}")
                for detail_item in item.get('details', []):
                    timestamp_sec = int(detail_item.get('time', 0))
                    link = f"{base_url}&t={timestamp_sec}s"
                    display_text = f"    • {detail_item.get('detail', '')}"
                    pdf.write_highlighted_text(display_text)
                    pdf.set_text_color(*COLORS["link_text"])
                    pdf.cell(0, 7, text=f"[{timestamp_sec//60:02}:{timestamp_sec%60:02}]", link=link, new_x=pdf.get_x(), new_y=pdf.get_y(), align="R")
            else:
                timestamp_sec = int(item.get('time', 0))
                link = f"{base_url}&t={timestamp_sec}s"
                for sk, sv in item.items():
                    if sk != 'time':
                        pdf.set_text_color(*COLORS["body_text"])
                        pdf.set_font(pdf.font_name, "B", 11)
                        pdf.write(7, f"• {sk.replace('_', ' ').title()}: ")
                        pdf.set_font(pdf.font_name, "", 11)
                        pdf.write_highlighted_text(str(sv))
                pdf.set_text_color(*COLORS["link_text"])
                pdf.cell(0, 7, text=f"[{timestamp_sec//60:02}:{timestamp_sec%60:02}]", link=link, new_x=pdf.get_x(), new_y=pdf.get_y(), align="R")
            pdf.ln(4)
        pdf.ln(5)

    if isinstance(output, BytesIO):
        pdf.output(output)
        output.seek(0)
    else:
        pdf.output(str(output))