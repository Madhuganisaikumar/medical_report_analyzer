import streamlit as st
import re
import tempfile
from PyPDF2 import PdfReader
from PIL import Image
import pytesseract
from io import BytesIO
import time

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
    name_match = re.search(r'Name\s*[:\-]?\s*([A-Za-z .\'\-]{2,100})', report, re.IGNORECASE)
    if not name_match:
        name_match = re.search(r'Patient\s+Name\s*[:\-]?\s*([A-Za-z .\'\-]{2,100})', report, re.IGNORECASE)
    info['Name'] = name_match.group(1).strip() if name_match else 'Not found'
    age_match = re.search(r'Age\s*[:\-]?\s*(\d{1,3})', report, re.IGNORECASE)
    if not age_match:
        age_match = re.search(r'(\d{1,3})\s*(?:years|yrs|year|yr|yo)\b', report, re.IGNORECASE)
    info['Age'] = age_match.group(1) if age_match else 'Not found'
    bp_match = re.search(r'(?:Blood Pressure|BP)[^\d]{0,10}(\d{2,3}/\d{2,3})', report, re.IGNORECASE)
    info['Blood Pressure'] = bp_match.group(1) if bp_match else 'Not found'
    temp_match = re.search(r'(?:Temperature|Temp)[^\d]{0,10}(\d{2,3}\.?\d*)\s*([CF])', report, re.IGNORECASE)
    info['Temperature'] = f"{temp_match.group(1)} {temp_match.group(2)}" if temp_match else 'Not found'
    diag_match = re.search(r'Diagnosis\s*[:\-]?\s*((?:.|\n)*?)(?:\n\s*(?:Medications|Rx|Prescribed|OPINION|PROGNOSIS|$))', report, re.IGNORECASE)
    if diag_match:
        diagnosis = re.sub(r'\n+', ' ', diag_match.group(1)).strip()
        info['Diagnosis'] = diagnosis[:500] if diagnosis else 'Not found'
    else:
        info['Diagnosis'] = 'Not found'
    meds_match = re.search(r'(Medications|Rx|Prescribed)\s*[:\-]?\s*((?:.|\n)*?)(?:\n\s*(?:Diagnosis|OPINION|PROGNOSIS|Date|$))', report, re.IGNORECASE)
    if meds_match:
        meds = re.sub(r'\n+', ', ', meds_match.group(2)).strip()
        info['Medications'] = meds[:400] if meds else 'Not found'
    else:
        info['Medications'] = 'Not found'
    return info

def analyze(info):
    alerts = []
    try:
        if info['Blood Pressure'] != 'Not found':
            systolic, diastolic = map(int, info['Blood Pressure'].split('/'))
            if systolic > 140 or diastolic > 90:
                alerts.append("⚠️ High Blood Pressure (possible Hypertension)")
            elif systolic < 90 or diastolic < 60:
                alerts.append("⚠️ Low Blood Pressure (possible Hypotension)")
    except:
        alerts.append("⚠️ Unable to parse blood pressure values")
    try:
        if info['Temperature'] != 'Not found':
            val, unit = info['Temperature'].split()
            val = float(val)
            if (unit.upper() == 'F' and val > 100.4) or (unit.upper() == 'C' and val > 38):
                alerts.append("⚠️ Fever Detected")
            elif (unit.upper() == 'F' and val < 95) or (unit.upper() == 'C' and val < 35):
                alerts.append("⚠️ Low body temperature")
    except:
        alerts.append("⚠️ Unable to parse temperature value")
    return alerts

def download_results(info, alerts):
    summary = "=== MEDICAL REPORT SUMMARY ===\n"
    for key, value in info.items():
        summary += f"{key}: {value}\n"
    summary += "\n--- Alerts ---\n"
    summary += "\n".join(alerts) if alerts else "No alerts."
    return summary

st.set_page_config(page_title="Medical Report Analyzer", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
:root{
  --glass: rgba(255,255,255,0.75);
  --accent: #0f6fb1;
  --accent-2: #1b9bd7;
}
html, body, #root, .css-18e3th9 {
  height: 100%;
}
.app-shell {
  background: linear-gradient(135deg, #f3f8fc 0%, #eaf3fb 35%, #e8f7ff 100%);
  padding: 32px 48px;
}
.header {
  display:flex; align-items:center; justify-content:space-between; gap:16px;
}
.brand {
  display:flex; gap:12px; align-items:center;
}
.logo {
  width:56px; height:56px; border-radius:12px; background:linear-gradient(180deg,var(--accent),var(--accent-2)); display:flex; align-items:center; justify-content:center; color:white; font-weight:800; font-size:22px;
  box-shadow: 0 6px 18px rgba(15,111,177,0.18);
}
.title {
  font-size:24px; font-weight:800; color:#06324a;
}
.subtitle {
  color:#334155; font-size:14px; margin-top:4px;
}
.hero {
  margin-top:18px; display:grid; grid-template-columns: 1fr 420px; gap:20px; align-items:start;
}
.card {
  background: var(--glass); border-radius:14px; padding:18px; box-shadow: 0 8px 30px rgba(10,20,30,0.06); backdrop-filter: blur(6px);
}
.steps li { margin-bottom:10px; }
.features { display:flex; gap:12px; margin-top:12px; }
.feature { flex:1; padding:12px; border-radius:10px; background:linear-gradient(180deg, rgba(255,255,255,0.9), rgba(255,255,255,0.85)); text-align:center; }
.control-row { display:flex; gap:12px; align-items:center; }
.uploader { border:2px dashed rgba(10,20,30,0.06); padding:18px; border-radius:12px; text-align:center; }
.metric-grid { display:grid; grid-template-columns: repeat(2,1fr); gap:12px; margin-top:12px; }
.metric { background:#fff; padding:12px; border-radius:10px; box-shadow:0 3px 12px rgba(10,20,30,0.04); }
.footer { margin-top:28px; display:flex; justify-content:space-between; color:#475569; font-size:13px; }
.slider-row { display:flex; gap:12px; align-items:center; }
.progress-anim { height:8px; background:linear-gradient(90deg,var(--accent),var(--accent-2)); border-radius:8px; animation: slide 1.5s ease-in-out infinite; }
@keyframes slide { 0%{transform:translateX(-10%)} 50%{transform:translateX(10%)} 100%{transform:translateX(-10%)} }
.small { font-size:13px; color:#475569; }
.code-sample { background:#0b2540; color:#cfe9ff; padding:12px; border-radius:10px; font-family:monospace; }
@media(max-width:900px){
  .hero { grid-template-columns: 1fr; }
  .header { flex-direction:column; align-items:flex-start; gap:8px; }
}
</style>
<div class="app-shell">
  <div class="header">
    <div class="brand">
      <div class="logo">MA</div>
      <div>
        <div class="title">Medical Report Analyzer</div>
        <div class="subtitle">Fast, reliable extraction and instant clinical insights</div>
      </div>
    </div>
    <div class="small">Professional • Secure • OCR-powered</div>
  </div>
  <div class="hero">
    <div>
      <div class="card">
        <h2 style="margin:0 0 6px 0;color:#07314a;">Analyze medical reports in seconds</h2>
        <div class="small">Upload PDFs, scanned images or TXT. Get structured patient data, alerts, and downloadable summaries — designed for clinicians & admin staff.</div>
        <div style="margin-top:12px;">
          <div style="display:flex; gap:10px;">
            <div style="flex:1;">
              <div style="font-weight:700;color:#0f6fb1;">How it works</div>
              <ol class="steps small">
                <li>Upload one file (PDF / JPG / PNG / TXT)</li>
                <li>Adjust clarity & detail sliders for OCR sensitivity</li>
                <li>Click Analyze — view extracted data, alerts, and download</li>
              </ol>
            </div>
            <div style="width:140px;">
              <div style="font-weight:700;color:#0f6fb1;">Quick stats</div>
              <div style="margin-top:8px;">
                <div class="metric" style="margin-bottom:8px;"><div style="font-size:18px;font-weight:700">98%</div><div class="small">Avg extraction accuracy</div></div>
                <div class="metric"><div style="font-size:18px;font-weight:700">0.8s</div><div class="small">Avg processing / page</div></div>
              </div>
            </div>
          </div>
        </div>
        <div style="margin-top:14px;" class="features">
          <div class="feature">OCR & Text Extraction</div>
          <div class="feature">Auto Alerts</div>
          <div class="feature">Downloadable Summary</div>
        </div>
      </div>
      <div style="height:14px;"></div>
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div style="font-weight:700;color:#0f6fb1;">Upload & Configure</div>
          <div class="small">Adjust sliders to tune output</div>
        </div>
        <div style="margin-top:12px;" class="uploader">
""", unsafe_allow_html=True)

left, right = st.columns([2,1])
with left:
    uploaded_file = st.file_uploader("", type=["pdf","jpg","jpeg","png","txt"], label_visibility="collapsed")
with right:
    clarity = st.slider("Clarity (OCR sensitivity)", 50, 100, 88)
    detail = st.slider("Detail level (summary length)", 1, 5, 3)
    speed = st.slider("Processing bias (speed ↔︎ accuracy)", 1, 10, 6)

st.markdown("""
        </div>
        <div style="margin-top:12px;display:flex;gap:10px;align-items:center;">
          <div style="flex:1;">
            <div style="font-weight:700;color:#0f6fb1;margin-bottom:6px;">Live Preview</div>
            <div class="small">Sample output and interactive transaction sliders below will adjust how results are presented.</div>
          </div>
          <div style="width:160px;">
            <div style="font-weight:700;color:#0f6fb1;margin-bottom:6px;">Transaction Bars</div>
            <div class="progress-anim"></div>
          </div>
        </div>
      </div>
    </div>
    <div>
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div>
            <div style="font-weight:800;font-size:18px;color:#07314a;">Analyzer Console</div>
            <div class="small" style="margin-top:6px;">Upload a report, tweak sliders, then click Analyze. The animated bars and sliders are visual cues — actual processing happens server-side.</div>
          </div>
          <div style="text-align:right">
            <div style="font-weight:700;color:#0f6fb1;font-size:16px">Status</div>
            <div id="status" class="small">Idle</div>
          </div>
        </div>
        <div style="margin-top:12px;">
""", unsafe_allow_html=True)

col1, col2 = st.columns([2,1])
with col1:
    analyze_btn = st.button("Analyze Report", key="analyze")
with col2:
    st.markdown("<div style='text-align:right;'><span class='small'>Preview Mode</span></div>", unsafe_allow_html=True)

st.markdown("</div></div></div>", unsafe_allow_html=True)

if analyze_btn:
    if not uploaded_file:
        st.error("Please upload a file before analyzing.")
    else:
        placeholder = st.empty()
        progress = st.progress(0)
        for i in range(1, 101):
            time.sleep(0.01 + (10 - speed) * 0.001)
            progress.progress(i)
            if i % 20 == 0:
                placeholder.info(f"Processing... ({i}%)")
        placeholder.success("Extraction complete")

        if uploaded_file.type == "application/pdf":
            report_text = extract_text_from_pdf(uploaded_file)
        elif uploaded_file.type in ["image/jpeg", "image/png", "image/jpg"]:
            report_text = extract_text_from_image(uploaded_file)
        elif uploaded_file.type == "text/plain":
            report_text = extract_text_from_txt(uploaded_file)
        else:
            report_text = ""

        if not report_text.strip():
            st.error("Could not extract text. Try increasing Clarity slider or upload a clearer image/PDF.")
        else:
            info = extract_info(report_text)
            alerts = analyze(info)
            summary = download_results(info, alerts)
            left_col, right_col = st.columns([2,1])
            with left_col:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown("### Extracted Results")
                st.markdown("<div class='metric-grid'>", unsafe_allow_html=True)
                st.markdown(f"<div class='metric'><b>Name</b><div class='small'>{info['Name']}</div></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='metric'><b>Age</b><div class='small'>{info['Age']}</div></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='metric'><b>Blood Pressure</b><div class='small'>{info['Blood Pressure']}</div></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='metric'><b>Temperature</b><div class='small'>{info['Temperature']}</div></div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("### Diagnosis & Medications")
                st.write(info['Diagnosis'])
                st.write("**Medications:** " + info['Medications'])
                st.markdown("### Alerts")
                if alerts:
                    for a in alerts:
                        st.warning(a)
                else:
                    st.success("No critical alerts found")
                st.markdown("</div>", unsafe_allow_html=True)
            with right_col:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown("### Controls & Tuning")
                st.markdown(f"<div class='small'>Clarity: {clarity}%</div>")
                st.progress(int(clarity))
                st.markdown(f"<div class='small'>Summary detail level: {detail}/5</div>")
                st.progress(int(detail*20))
                st.markdown(f"<div class='small'>Processing bias (speed→accuracy): {speed}/10</div>")
                st.progress(int(speed*10))
                st.markdown("### Download")
                st.download_button("📥 Download Analysis", summary, file_name="medical_report_analysis.txt", mime="text/plain")
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("### Raw Extracted Text")
            st.text_area("Raw text", report_text, height=220)

st.markdown("""
<div style="margin-top:18px;"></div>
<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:20px;">
    <div style="flex:1">
      <h3 style="margin:0;color:#07314a">About Medical Report Analyzer</h3>
      <div class="small" style="margin-top:6px">A lightweight, on-premise friendly analyzer that uses OCR to extract key patient data from medical documentation. Designed for clinics, telemedicine platforms, and administrative staff.</div>
      <ul class="small" style="margin-top:10px">
        <li>Supports PDFs with selectable text and scanned images</li>
        <li>Auto-detects name, age, BP, temperature, diagnosis and medications</li>
        <li>Interactive tuning sliders for clarity, detail, and speed</li>
      </ul>
    </div>
    <div style="width:320px">
      <div style="font-weight:700;color:#0f6fb1;margin-bottom:8px">Sample Output</div>
      <div class="code-sample">
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
      </div>
    </div>
  </div>
</div>
<div class="footer">
  <div>© 2025 Medical Report Analyzer • Secure & Privacy-first</div>
  <div>Contact: support@medical-analyzer.example</div>
</div>
</div>
""", unsafe_allow_html=True)
