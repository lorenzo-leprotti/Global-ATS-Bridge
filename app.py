import streamlit as st
import pdfplumber
import io
import google.generativeai as genai
import json
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# --- CONFIGURATION ---
st.set_page_config(page_title="Global ATS Bridge (MVP)", layout="wide")

# Initialize Gemini 2.5 Flash
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception:
    st.error("🚨 API Key missing! Check .streamlit/secrets.toml")
    st.stop()

# --- THE "HANDS": PDF GENERATOR FUNCTION ---
def generate_resume_pdf(data):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER
    
    # METADATA & FONT SETUP
    c.setTitle(f"Resume - {data.get('contact_info', {}).get('name', 'Candidate')}")
    
    # HELPER: DRAW LINE
    def draw_line(y):
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.5)
        c.line(50, y, width - 50, y)
        return y - 15

    # CURSOR TRACKER (Keeps track of where we are writing on the page)
    y = height - 50
    
    # 1. HEADER (Name & Contact)
    contact = data.get("contact_info", {})
    name = contact.get("name", "Name Not Found").upper()
    info_line = f"{contact.get('location', '')} | {contact.get('email', '')} | {contact.get('phone', '')}"
    
    c.setFont("Times-Bold", 16)
    c.drawCentredString(width / 2, y, name)
    y -= 20
    
    c.setFont("Times-Roman", 10)
    c.drawCentredString(width / 2, y, info_line)
    y -= 15
    
    # 2. WORK AUTHORIZATION (The "Visa Signal")
    visa = data.get("work_authorization", "Unknown Status")
    c.setFont("Times-Bold", 10)
    c.drawCentredString(width / 2, y, f"WORK AUTHORIZATION: {visa}")
    y -= 25

    # 3. EDUCATION SECTION
    c.setFont("Times-Bold", 12)
    c.drawString(50, y, "EDUCATION")
    y -= 5
    y = draw_line(y)
    
    for edu in data.get("education", []):
        # University & Location (Right Aligned)
        c.setFont("Times-Bold", 10)
        c.drawString(50, y, edu.get("university", "University"))
        
        # Degree & GPA
        c.setFont("Times-Roman", 10)
        y -= 12
        degree_line = f"{edu.get('degree', 'Degree')} -- {edu.get('gpa_converted', '')}"
        c.drawString(50, y, degree_line)
        y -= 20
        
    y -= 10 # Spacer

    # 4. EXPERIENCE SECTION
    c.setFont("Times-Bold", 12)
    c.drawString(50, y, "PROFESSIONAL EXPERIENCE")
    y -= 5
    y = draw_line(y)
    
    for exp in data.get("experience", []):
        # Company & Role
        c.setFont("Times-Bold", 10)
        c.drawString(50, y, f"{exp.get('company', 'Company')} | {exp.get('role', 'Role')}")
        y -= 12
        
        # Bullets
        c.setFont("Times-Roman", 10)
        for bullet in exp.get("bullets", [])[:3]: # Limit to top 3 bullets per role for MVP
            c.drawString(65, y, f"• {bullet}")
            y -= 12
        y -= 10

    c.save()
    buffer.seek(0)
    return buffer

# --- THE "BRAIN": SYSTEM PROMPT ---
# --- THE "BRAIN": DYNAMIC SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are an expert Resume Architect. Your goal is to parse ANY resume format and normalize it for US ATS systems.

ALGORITHM:
1. SCAN: Read the document and identify every distinct section (e.g., "Work History", "Academic Background", "Projects", "Patents", "Publications").
2. MAP: For each section, determine the best US Standard Category:
   - "Experience" (Work History, Employment, Internships)
   - "Education" (Academics, Degrees, Certifications)
   - "Skills" (Tech Stack, Tools, Languages)
   - "Summary" (Profile, Bio, Objective)
   - "Other" (Volunteering, Awards, Patents, everything else)
3. EXTRACT: Keep the content verbatim (do not summarize). Fix grammar/action verbs only.
4. GRADES: If you see grades in Education, keep the original AND append "(US Equivalent: X.X)" if calculable.

OUTPUT SCHEMA (JSON):
{
  "contact_info": { "name": "...", "email": "...", "location": "...", "phone": "...", "linkedin": "..." },
  "work_authorization": "...",
  "sections": [
    {
      "original_title": "String (e.g., 'My Code')",
      "us_category": "Skills", 
      "content": ["Python", "Streamlit", ...] 
    },
    {
      "original_title": "String (e.g., 'Career Journey')",
      "us_category": "Experience",
      "entries": [ 
         { "header": "Company A", "subheader": "Role B", "date": "2020-2023", "bullets": ["Did X", "Did Y"] } 
      ]
    }
  ]
}
"""

# --- THE UI (Frontend) ---
st.title("🧠 ATS Engine: Powered by Gemini 2.5 Flash")

col1, col2 = st.columns(2)
with col1:
    visa_status = st.selectbox("Target Visa Status", ["F-1 OPT (Stem)", "H-1B", "US Citizen"])
with col2:
    uploaded_file = st.file_uploader("Upload CV (PDF)", type="pdf")

if uploaded_file and st.button("🚀 Process & Generate"):
    
    # 1. READ (Input)
    with st.spinner("Reading PDF..."):
        try:
            uploaded_file.seek(0)
            file_stream = io.BytesIO(uploaded_file.getvalue())
            raw_text = ""
            with pdfplumber.open(file_stream) as pdf:
                for page in pdf.pages:
                    raw_text += page.extract_text() + "\n"
        except Exception as e:
            st.error(f"Read Error: {e}")
            st.stop()

    # 2. THINK (Process)
    with st.spinner("Gemini is restructuring..."):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
            full_prompt = f"{SYSTEM_PROMPT}\nUSER STATUS: {visa_status}\nRESUME:\n{raw_text}"
            response = model.generate_content(full_prompt)
            ai_data = json.loads(response.text)
            st.success("Analysis Complete!")
        except Exception as e:
            st.error(f"AI Error: {e}")
            st.stop()

    # 3. WRITE (Output)
    st.subheader("🎉 Your US-Optimized Resume")
    
    # Generate the PDF in memory
    pdf_bytes = generate_resume_pdf(ai_data)
    
    # Show Download Button
    st.download_button(
        label="📄 Download US-Standard PDF",
        data=pdf_bytes,
        file_name="Optimized_Resume.pdf",
        mime="application/pdf",
        type="primary"
    )
    
    # Show Debug Data below
    with st.expander("See Extracted Data (Debug)"):
        st.json(ai_data)