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
    st.set_page_config(page_title="Medical Report Analyzer", layout="centered")
    st.markdown("""
    <style>
    body, .stApp {
        background-color: #f9fafc;
        color: #222;
    }
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        text-align: center;
        color: #1c3d5a;
        margin-bottom: 0.5rem;
    }
    .subtext {
        text-align: center;
        color: #555;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    .metric-box {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='main-title'>🩺 Medical Report Analyzer</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtext'>Upload your medical report to extract and analyze patient details.</div>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Upload a PDF, Image (JPG/PNG), or Text File", type=["pdf", "jpg", "jpeg", "png", "txt"], label_visibility="collapsed")

    if uploaded_file:
        with st.spinner("🔍 Extracting text from your file..."):
            if uploaded_file.type == "application/pdf":
                report_text = extract_text_from_pdf(uploaded_file)
            elif uploaded_file.type in ["image/jpeg", "image/png", "image/jpg"]:
                report_text = extract_text_from_image(uploaded_file)
            elif uploaded_file.type == "text/plain":
                report_text = extract_text_from_txt(uploaded_file)
            else:
                report_text = ""

        if not report_text.strip():
            st.error("Could not extract text from file. Please upload a clearer or supported report.")
            return

        info = extract_info(report_text)
        alerts = analyze(info)

        st.markdown("### 🧾 Extracted Report Details")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"<div class='metric-box'><b>Patient Name:</b><br>{info['Name']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-box'><b>Age:</b><br>{info['Age']}</div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='metric-box'><b>Blood Pressure:</b><br>{info['Blood Pressure']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-box'><b>Temperature:</b><br>{info['Temperature']}</div>", unsafe_allow_html=True)

        st.markdown("### 💊 Diagnosis & Medications")
        st.write(f"**Diagnosis:** {info['Diagnosis']}")
        st.write(f"**Medications:** {info['Medications']}")

        st.markdown("### ⚠️ Health Alerts")
        if alerts:
            for alert in alerts:
                st.warning(alert)
        else:
            st.success("✅ No critical alerts found.")

        with st.expander("Show Extracted Raw Text"):
            st.text_area("Extracted Text", report_text, height=250)

        summary = download_results(info, alerts)
        st.download_button("📥 Download Analysis Result", summary, file_name="medical_report_analysis.txt", mime="text/plain")
    else:
        st.info("Upload a file above to start analyzing your report.")

if __name__ == "__main__":
    main()
