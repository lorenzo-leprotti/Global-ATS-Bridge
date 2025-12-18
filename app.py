import streamlit as st
import pdfplumber
import io

# 1. Page Config (Must be the first Streamlit command)
st.set_page_config(page_title="ATS Engine Debugger", layout="wide")

st.title("⚙️ ATS Engine: PDF Parser Debugger")
st.markdown("---")

# 2. The Input (File Uploader)
uploaded_file = st.file_uploader("Upload your CV (PDF)", type="pdf")

if uploaded_file:
    # 3. The "Engine" Check
    st.info("File received. Attempting to parse...")

    try:
        # --- THE FIX: Handle Streamlit's BytesIO stream correctly ---
        # Reset cursor to start just in case
        uploaded_file.seek(0)
        
        # Explicitly wrap the bytes for pdfplumber
        file_stream = io.BytesIO(uploaded_file.getvalue())
        
        # 4. Extract Text
        full_text = ""
        with pdfplumber.open(file_stream) as pdf:
            # Loop through pages (robustness check)
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    full_text += f"\n--- Page {i+1} ---\n{text}"
        
        # 5. The Verdict (Did it work?)
        if len(full_text) > 50:
            st.success(f"✅ SUCCESS! Extracted {len(full_text)} characters.")
            
            # Show the raw text so you can inspect if it's "garbage" or "clean"
            with st.expander("🔍 Inspect Extracted Text"):
                st.text_area("Raw Content", full_text, height=400)
        else:
            st.warning("⚠️ Parsed successfully, but found very little text. Is this an image-based PDF?")

    except Exception as e:
        # If it crashes, show the exact technical error
        st.error("❌ CRITICAL FAILURE")
        st.error(f"Error Details: {e}")