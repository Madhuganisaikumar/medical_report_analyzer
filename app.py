import streamlit as st
import re
import tempfile
from PyPDF2 import PdfReader
from PIL import Image
import pytesseract

def extract_text_from_pdf(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name
    reader = PdfReader(tmp_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text.strip()

def extract_text_from_image(uploaded_file):
    img = Image.open(uploaded_file).convert("L")
    text = pytesseract.image_to_string(img, config="--psm 6")
    return text.strip()

def extract_text_from_txt(uploaded_file):
    return uploaded_file.read().decode("utf-8").strip()

def extract_info(report):
    info = {}
    name_match = re.search(r'Name\s*[:\-]?\s*([A-Za-z .\'\-]{3,100})', report, re.IGNORECASE)
    info['Name'] = name_match.group(1).strip() if name_match else 'Not found'
    age_match = re.search(r'Age\s*[:\-]?\s*(\d{1,3})', report, re.IGNORECASE)
    if not age_match:
        age_match = re.search(r'(\d{1,3})\s*(?:years|yrs|year|yr|yo)\b', report, re.IGNORECASE)
    info['Age'] = age_match.group(1) if age_match else 'Not found'
    bp_match = re.search(r'(?:Blood Pressure|BP)[^\d]{0,10}(\d{2,3}/\d{2,3})', report, re.IGNORECASE)
    info['Blood Pressure'] = bp_match.group(1) if bp_match else 'Not found'
    temp_match = re.search(r'Temperature[^\d]{0,10}(\d{2,3}\.?\d*)\s*([CF])', report, re.IGNORECASE)
    info['Temperature'] = f"{temp_match.group(1)} {temp_match.group(2)}" if temp_match else 'Not found'
    diag_match = re.search(r'Diagnosis\s*[:\-]?\s*((?:.|\n)*?)(?:\n\s*(?:Medications|Rx|Prescribed|OPINION|$))', report, re.IGNORECASE)
    if diag_match:
        diagnosis = re.sub(r'\n+', ' ', diag_match.group(1)).strip()
        info['Diagnosis'] = diagnosis[:300] if diagnosis else 'Not found'
    else:
        info['Diagnosis'] = 'Not found'
    meds_match = re.search(r'(Medications|Rx|Prescribed)\s*[:\-]?\s*((?:.|\n)*?)(?:\n\s*(?:Diagnosis|OPINION|PROGNOSIS|Date|$))', report, re.IGNORECASE)
    if meds_match:
        meds = re.sub(r'\n+', ', ', meds_match.group(2)).strip()
        info['Medications'] = meds[:200] if meds else 'Not found'
    else:
        info['Medications'] = 'Not found'
    return info

def analyze(info):
    alerts = []
    if info['Blood Pressure'] != 'Not found':
        try:
            systolic, diastolic = map(int, info['Blood Pressure'].split('/'))
            if systolic > 140 or diastolic > 90:
                alerts.append("⚠️ High Blood Pressure")
        except:
            alerts.append("⚠️ Unable to parse blood pressure values.")
    if info['Temperature'] != 'Not found':
        try:
            val, unit = info['Temperature'].split()
            val = float(val)
            if (unit.upper() == 'F' and val > 100.4) or (unit.upper() == 'C' and val > 38):
                alerts.append("⚠️ Fever Detected")
        except:
            alerts.append("⚠️ Unable to parse temperature value.")
    return alerts

def download_results(info, alerts):
    summary = "=== MEDICAL REPORT SUMMARY ===\n"
    for key, value in info.items():
        summary += f"{key}: {value}\n"
    summary += "\n--- Alerts ---\n"
    summary += "\n".join(alerts) if alerts else "No alerts."
    return summary

def main():
    st.set_page_config(page_title="Medical Report Analyzer", layout="wide")

    st.markdown("""
    <style>
    body, .stApp { background-color: #f8fafc; color: #1c1c1c; }
    h1, h2, h3, h4, h5 { color: #1c3d5a; }
    .main-title {
        text-align: center;
        font-size: 2.6rem;
        font-weight: 800;
        color: #164b72;
        margin-top: 0.5rem;
    }
    .subtext {
        text-align: center;
        color: #4b5563;
        font-size: 1.1rem;
        margin-bottom: 1.5rem;
    }
    .section {
        background: white;
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 3px 6px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem;
    }
    .metric-box {
        background: #fefefe;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='main-title'>🩺 Medical Report Analyzer</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtext'>Upload your medical report to automatically extract key details and get quick health insights.</div>", unsafe_allow_html=True)

    with st.container():
        st.markdown("### 🚀 Steps to Analyze Your Report")
        steps = """
        1️⃣ Upload your medical report file (PDF, image, or text).  
        2️⃣ The system will extract patient data like Name, Age, BP, etc.  
        3️⃣ Get alerts for any abnormal readings.  
        4️⃣ Download a summarized report instantly.
        """
        st.info(steps)

    st.markdown("### ✨ Key Features")
    st.markdown("""
    - 📄 Works with PDF, image, or plain text reports  
    - 🔍 Smart text extraction using OCR  
    - ⚠️ Automatic health alerts for high BP or fever  
    - 💊 Summarized diagnosis and medications  
    - 📥 Instant downloadable results  
    """)

    st.markdown("---")
    st.header("📂 Upload and Analyze Your Report")

    uploaded_file = st.file_uploader(
        "Upload a PDF, Image (JPG/PNG), or Text File",
        type=["pdf", "jpg", "jpeg", "png", "txt"]
    )

    confidence_slider = st.slider("🔧 Confidence Threshold (for text clarity)", 50, 100, 85)
    st.caption(f"Recommended: Keep above 80 for better OCR accuracy (current: {confidence_slider}%)")

    if uploaded_file:
        with st.spinner("Analyzing your report..."):
            if uploaded_file.type == "application/pdf":
                report_text = extract_text_from_pdf(uploaded_file)
            elif uploaded_file.type in ["image/jpeg", "image/png", "image/jpg"]:
                report_text = extract_text_from_image(uploaded_file)
            elif uploaded_file.type == "text/plain":
                report_text = extract_text_from_txt(uploaded_file)
            else:
                report_text = ""

        if not report_text.strip():
            st.error("❌ Could not extract text. Please check file clarity.")
            return

        info = extract_info(report_text)
        alerts = analyze(info)

        st.markdown("### 🧾 Extracted Information")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"<div class='metric-box'><b>Name</b><br>{info['Name']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-box'><b>Age</b><br>{info['Age']}</div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='metric-box'><b>Blood Pressure</b><br>{info['Blood Pressure']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-box'><b>Temperature</b><br>{info['Temperature']}</div>", unsafe_allow_html=True)

        st.markdown("### 💊 Diagnosis & Medications")
        st.write(f"**Diagnosis:** {info['Diagnosis']}")
        st.write(f"**Medications:** {info['Medications']}")

        st.markdown("### ⚠️ Health Alerts")
        if alerts:
            for alert in alerts:
                st.warning(alert)
        else:
            st.success("✅ No abnormal readings detected.")

        st.markdown("### 📄 Download or Preview")
        summary = download_results(info, alerts)
        st.download_button("📥 Download Analysis Result", summary, file_name="medical_report_analysis.txt", mime="text/plain")
        st.text_area("Report Preview", summary, height=250)
    else:
        st.info("⬆️ Upload a file above to begin analysis.")

    st.markdown("---")
    st.markdown("### 🧠 Sample Output Preview")
    st.code("""
    === MEDICAL REPORT SUMMARY ===
    Name: John Doe
    Age: 45
    Blood Pressure: 150/95
    Temperature: 101.2 F
    Diagnosis: Hypertension, Mild Fever
    Medications: Lisinopril, Paracetamol

    --- Alerts ---
    ⚠️ High Blood Pressure
    ⚠️ Fever Detected
    """, language="text")

if __name__ == "__main__":
    main()
