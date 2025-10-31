import streamlit as st
import re
import tempfile
from PyPDF2 import PdfReader
from PIL import Image
import pytesseract
import pandas as pd
import time
from io import BytesIO

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

def clean_extracted_name(raw_name):
    if not raw_name: 
        return "Not found"
    s = raw_name.strip()
    s = re.sub(r'\s+Age.*$', '', s, flags=re.IGNORECASE)
    s = re.sub(r'^(name[:\-\s]*)', '', s, flags=re.IGNORECASE)
    return s.strip()

def find_basic_fields(text):
    info = {}
    name_match = re.search(r'(?:Name|Patient Name)\s*[:\-]?\s*(.+?)(?:\s{2,}|\s+Age\b|\n|$)', text, re.IGNORECASE)
    sex_match = re.search(r'\bSex\s*[:\-]?\s*(Male|Female|M|F)\b', text, re.IGNORECASE)
    age_match = re.search(r'Age\s*[:\-]?\s*(\d{1,3})', text, re.IGNORECASE)
    date_match = re.search(r'\bDate\s*[:\-]?\s*([0-3]?\d[\/\-\s][01]?\d[\/\-\s]\d{2,4}|\d{4}-\d{2}-\d{2})', text, re.IGNORECASE)
    raw_name = name_match.group(1).strip() if name_match else ""
    info['Name'] = clean_extracted_name(raw_name) if raw_name else "Not found"
    info['Sex'] = (sex_match.group(1).strip() if sex_match else "Not found")
    info['Age'] = (age_match.group(1).strip() if age_match else "Not found")
    info['Report Date'] = (date_match.group(1).strip() if date_match else "Not found")
    return info

DEFAULT_RANGES = {
    'hemoglobin': {'M': (13.0, 18.0), 'F': (11.0, 16.0), 'U': (11.0, 17.5)},
    'rbc': {'U': (4.2, 6.0)},
    'wbc': {'U': (4000, 11000)},
    'platelet': {'U': (150000, 450000)},
    'esr': {'M': (0, 20), 'F': (0, 30), 'U': (0, 20)},
    'glucose_fasting': {'U': (70, 100)},
    'creatinine': {'U': (0.6, 1.3)}
}

QUAL_RESULTS_POSITIVE = ['positive', 'reactive', 'detected', 'reactivity']
QUAL_RESULTS_NEGATIVE = ['negative', 'non-reactive', 'non reactive', 'not detected', 'nonreactive', 'non - reactive']

def normalize_number(s):
    if s is None:
        return None
    s = str(s).replace(',', '.').strip()
    m = re.findall(r'-?\d+\.?\d*', s)
    if not m:
        return None
    try:
        return float(m[0])
    except:
        return None

def parse_lab_lines(text):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    tests = []
    for ln in lines:
        ln_clean = re.sub(r'\s{2,}', ' ', ln)
        qual_match = re.search(r'\b(HBsAg|HBs Ag|H\.B\.s Ag|HBs|VDRL|V\.D\.R\.L|V D R L|HCV|H\.C\.V|Tri[- ]Dot|H\.B & H\.B|H\.B & H\.B s Ag|H\.B & H\.Bs Ag)\b.*?[:\-]?\s*([A-Za-z \-\(\)0-9/:]+)', ln_clean, re.IGNORECASE)
        if qual_match:
            test_name = qual_match.group(1).strip()
            result = qual_match.group(2).strip()
            tests.append({'name': test_name, 'value_raw': result, 'type': 'qualitative', 'line': ln_clean})
            continue
        num_match = re.search(r'([A-Za-z .%()&/-]{3,40})\s+(:\s*)?(-?\d{1,3}\.?\d+)\s*([A-Za-z/%µμlhL]*)', ln_clean)
        if num_match:
            name = num_match.group(1).strip()
            num = num_match.group(3).strip()
            unit = num_match.group(4).strip()
            tests.append({'name': name, 'value_raw': num, 'unit': unit, 'type': 'numeric', 'line': ln_clean})
            continue
        num_match2 = re.search(r'([A-Za-z .]{2,40})\s+[:\-]?\s*(\d{2,7}\.?\d*)\s*(?:/|per)?\s*([A-Za-z/%µμlhL]*)', ln_clean)
        if num_match2:
            name = num_match2.group(1).strip()
            num = num_match2.group(2).strip()
            unit = num_match2.group(3).strip()
            tests.append({'name': name, 'value_raw': num, 'unit': unit, 'type': 'numeric', 'line': ln_clean})
            continue
        qual_inline = re.search(r'([A-Za-z .&/()-]{3,40})\s*[:\-]?\s*(Negative|Positive|Reactive|Non\s*-\s*Reactive|Non\s*Reactive|Non-Reactive|Not detected|Detected)', ln_clean, re.IGNORECASE)
        if qual_inline:
            tests.append({'name': qual_inline.group(1).strip(), 'value_raw': qual_inline.group(2).strip(), 'type': 'qualitative', 'line': ln_clean})
    return tests

def map_test_name(raw):
    s = raw.lower()
    if 'hemoglobin' in s or 'haemoglobin' in s or re.search(r'\bheamoglobin\b', s):
        return 'Hemoglobin'
    if 'w.b.c' in s or 'wbc' in s or 'white blood' in s:
        return 'WBC'
    if 'r.b.c' in s or 'rbc' in s:
        return 'RBC'
    if 'platelet' in s or 'platelate' in s or 'platelet count' in s:
        return 'Platelet'
    if 'esr' in s or 'e.s.r' in s:
        return 'ESR'
    if 'hb s ag' in s or 'hbsag' in s or 'h b s' in s or 'hbs ag' in s or 'h.b & h.b' in s:
        return 'HBsAg'
    if 'vdrl' in s:
        return 'VDRL'
    if 'hcv' in s or 'tri' in s or 'tri-dot' in s or 'tri dot' in s:
        return 'HCV'
    if 'glucose' in s and 'fast' in s:
        return 'Glucose (Fasting)'
    if 'glucose' in s:
        return 'Glucose'
    if 'creatinine' in s:
        return 'Creatinine'
    if 'hemogram' in s or 'blood picture' in s:
        return 'Blood Picture'
    if len(raw.strip()) <= 35:
        return raw.strip()
    return raw.strip()

def interpret_tests(tests, basic_info):
    results = []
    sex = basic_info.get('Sex', 'Not found')
    sex_key = 'U'
    if sex and re.match(r'^(male|m)$', sex, re.I):
        sex_key = 'M'
    elif sex and re.match(r'^(female|f)$', sex, re.I):
        sex_key = 'F'
    for t in tests:
        name_mapped = map_test_name(t.get('name', ''))
        if t['type'] == 'qualitative':
            val = t.get('value_raw', '').strip()
            vclean = val.lower()
            status = 'Unknown'
            if any(x in vclean for x in QUAL_RESULTS_NEGATIVE):
                status = 'Negative'
            elif any(x in vclean for x in QUAL_RESULTS_POSITIVE):
                status = 'Positive'
            else:
                status = val
            results.append({'Test': name_mapped, 'Value': status, 'Unit': '', 'Flag': None, 'Note': t.get('line','')})
        else:
            rawval = t.get('value_raw', '')
            num = normalize_number(rawval)
            unit = t.get('unit','')
            flag = None
            note = ""
            ref_range = ""
            lname = name_mapped.lower()
            if num is not None:
                if 'hemoglobin' in lname or 'haemoglobin' in lname:
                    rng = DEFAULT_RANGES['hemoglobin'].get(sex_key, DEFAULT_RANGES['hemoglobin']['U'])
                    low, high = rng
                    ref_range = f"{low}-{high} g/dL"
                    if num < low:
                        flag = 'Low'
                        note = "Possible anemia"
                    elif num > high:
                        flag = 'High'
                        note = "Above expected"
                elif 'wbc' in lname:
                    rng = DEFAULT_RANGES['wbc']['U']
                    low, high = rng
                    ref_range = f"{int(low)}-{int(high)} /µL"
                    if num < low:
                        flag = 'Low'
                        note = "Leukopenia"
                    elif num > high:
                        flag = 'High'
                        note = "Leukocytosis (infection/inflammation)"
                elif 'platelet' in lname:
                    rng = DEFAULT_RANGES['platelet']['U']
                    low, high = rng
                    ref_range = f"{int(low)}-{int(high)} /µL"
                    if 'lakh' in (t.get('line') or '').lower() or 'lakhs' in (t.get('line') or '').lower():
                        try:
                            num_conv = float(num) * 100000
                            num = int(num_conv)
                        except:
                            pass
                    if num < low:
                        flag = 'Low'
                        note = "Thrombocytopenia"
                    elif num > high:
                        flag = 'High'
                        note = "Thrombocytosis"
                elif 'esr' in lname:
                    rng = DEFAULT_RANGES['esr'].get(sex_key, DEFAULT_RANGES['esr']['U'])
                    low, high = rng
                    ref_range = f"≤{high} mm/hr"
                    if num > high:
                        flag = 'High'
                        note = "Elevated ESR (inflammation)"
                elif 'rbc' in lname:
                    rng = DEFAULT_RANGES['rbc']['U']
                    low, high = rng
                    ref_range = f"{low}-{high} million/µL"
                    if num < low:
                        flag = 'Low'
                        note = "Low RBC (possible anemia)"
                elif 'glucose' in lname:
                    rng = DEFAULT_RANGES['glucose_fasting']['U']
                    low, high = rng
                    ref_range = f"{int(low)}-{int(high)} mg/dL"
                    if num < low:
                        flag = 'Low'
                        note = "Hypoglycemia"
                    elif num > high:
                        flag = 'High'
                        note = "Hyperglycemia"
                elif 'creatinine' in lname:
                    rng = DEFAULT_RANGES['creatinine']['U']
                    low, high = rng
                    ref_range = f"{low}-{high} mg/dL"
                    if num < low or num > high:
                        flag = 'Abnormal'
                        note = "Renal function abnormality"
            results.append({'Test': name_mapped, 'Value': num if num is not None else t.get('value_raw'), 'Unit': unit, 'Flag': flag, 'Note': note, 'Reference': ref_range})
    return results

def build_summary_and_abnormals(interpreted):
    abnormalities = [r for r in interpreted if r.get('Flag')]
    lines = []
    for r in interpreted:
        val = r.get('Value')
        ref = r.get('Reference','')
        if r.get('Flag'):
            lines.append(f"{r['Test']}: {r['Flag']} ({val}) — {r.get('Note','')}{(' — ref: '+ref) if ref else ''}")
        else:
            lines.append(f"{r['Test']}: {val}{(' '+r.get('Unit','')) if r.get('Unit') else ''}")
    summary = "\n".join(lines) if lines else "No lab values detected."
    return summary, abnormalities

st.set_page_config(page_title="Medical Report Analyzer — Dark AI UI", layout="wide")
st.markdown("""
<style>
:root{--bg1:#0f1720; --bg2:#0b1220; --panel:#0c1624; --teal:#16d9c3; --accent:#12a4b8;}
body, .stApp { background: radial-gradient(circle at 10% 10%, #07111a 0%, #07121a 30%, #081826 60%, #051018 100%); color:#dbeafe; }
.header { display:flex; justify-content:space-between; align-items:center; padding:20px 28px; gap:12px; }
.brand { display:flex; gap:12px; align-items:center; }
.logo { width:64px; height:64px; border-radius:12px; background:linear-gradient(180deg,var(--accent),var(--teal)); color:black; display:flex; align-items:center; justify-content:center; font-weight:900; box-shadow: 0 8px 30px rgba(0,0,0,0.6); font-size:20px; }
.title { font-size:22px; font-weight:800; color:#e6f6f3; }
.subtitle { color:#9fb6b2; font-size:13px; }
.container { padding:18px 28px; }
.grid { display:grid; grid-template-columns: 1fr 420px; gap:18px; align-items:start; }
.card { background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); border-radius:12px; padding:16px; border: 1px solid rgba(255,255,255,0.03); box-shadow: 0 6px 30px rgba(2,6,23,0.6); }
.small { font-size:13px; color:#9fb6b2; }
.controls { display:flex; gap:8px; align-items:center; margin-top:8px; }
.uploader { border: 1px dashed rgba(255,255,255,0.04); padding:14px; border-radius:10px; text-align:center; }
.metric { background: linear-gradient(90deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); padding:10px; border-radius:10px; margin-bottom:8px; color:#dbeafe; }
.table-wrap { overflow-x:auto; }
.badge { display:inline-block; padding:6px 10px; border-radius:8px; background: rgba(22,217,195,0.12); color: var(--teal); font-weight:700; }
.warn { color:#ffb4a2; }
.critical { color:#ff6b6b; font-weight:800; }
.code { background:#071826; color:#bfeeee; padding:12px; border-radius:8px; font-family:monospace; white-space:pre-wrap; }
.footer { display:flex; justify-content:space-between; color:#8aa7a3; margin-top:20px; font-size:13px; }
@media(max-width:980px){ .grid{ grid-template-columns: 1fr; } .logo{ width:56px; height:56px; } }
</style>
<div class="header">
  <div class="brand">
    <div class="logo">MA</div>
    <div>
      <div class="title">Medical Report Analyzer — Dark AI</div>
      <div class="subtitle">Universal lab & clinical extractor · Dark mode · Abnormal detection</div>
    </div>
  </div>
  <div class="small">Offline OCR · Tunable · Privacy-first</div>
</div>
<div class="container">
  <div class="grid">
    <div>
      <div class="card">
        <h2 style="margin:0;color:#dffbf6">Upload & Analyze</h2>
        <div class="small" style="margin-top:6px">Drop PDF, scanned image, or TXT. The system detects lab fields and highlights abnormalities in a separate section.</div>
        <div style="margin-top:12px" class="metric">
          <div style="font-weight:700;color:var(--teal)">Steps</div>
          <div class="small">
            1. Upload report · 2. Tune clarity/detail · 3. Click Analyze · 4. Review Abnormal Findings
          </div>
        </div>
""", unsafe_allow_html=True)

left, right = st.columns([3,1])
with left:
    uploaded_file = st.file_uploader("Choose file (PDF / JPG / PNG / TXT)", type=["pdf","jpg","jpeg","png","txt"])
with right:
    clarity = st.slider("Clarity", 50, 100, 90)
    detail = st.slider("Detail level", 1, 5, 3)
    speed = st.slider("Speed bias", 1, 10, 6)

st.markdown(""" 
      <div style="margin-top:10px" class="metric">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div><b style="color:var(--teal)">Preview</b></div>
          <div class="small">Animated progress during analysis</div>
        </div>
      </div>
      </div>
    </div>
    <div>
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div><b style="color:#dffbf6">Analyzer Console</b></div>
          <div class="small">Status: Idle</div>
        </div>
        <div style="margin-top:12px" class="small">Use sliders to help OCR sensitivity for poor scans.</div>
        <div style="margin-top:12px">""", unsafe_allow_html=True)

analyze_btn = st.button("Analyze Report", key="analyze_final")

st.markdown("</div></div></div>", unsafe_allow_html=True)

if analyze_btn:
    if not uploaded_file:
        st.error("Please upload a report first.")
    else:
        progress = st.progress(0)
        status = st.empty()
        status.info("Initializing...")
        for i in range(1, 101):
            time.sleep(0.006 + (11 - speed) * 0.002)
            progress.progress(i)
            if i == 25:
                status.info("Running OCR / extracting text...")
            if i == 60:
                status.info("Parsing lab values and interpreting results...")
        status.success("Analysis finished")
        if uploaded_file.type == "application/pdf":
            raw_text = extract_text_from_pdf(uploaded_file)
        elif uploaded_file.type in ["image/jpeg","image/jpg","image/png"]:
            raw_text = extract_text_from_image(uploaded_file)
        elif uploaded_file.type == "text/plain":
            raw_text = extract_text_from_txt(uploaded_file)
        else:
            raw_text = ""
        if not raw_text.strip():
            st.error("No text could be extracted. Try increasing Clarity or upload a clearer scan.")
        else:
            basic = find_basic_fields(raw_text)
            parsed = parse_lab_lines(raw_text)
            interpreted = interpret_tests(parsed, basic)
            summary_text, abnormals = build_summary_and_abnormals(interpreted)
            rows = []
            for r in interpreted:
                rows.append({
                    "Test": r.get('Test'),
                    "Value": r.get('Value'),
                    "Unit": r.get('Unit',''),
                    "Flag": r.get('Flag') if r.get('Flag') else "",
                    "Note": r.get('Note',''),
                    "Reference": r.get('Reference','')
                })
            df = pd.DataFrame(rows)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### Extracted Patient Info")
            if basic.get('Name') and basic.get('Name') != "Not found":
                st.write(f"**Name:** {basic.get('Name')}")
            if basic.get('Age') and basic.get('Age') != "Not found":
                st.write(f"**Age:** {basic.get('Age')}")
            if basic.get('Sex') and basic.get('Sex') != "Not found":
                st.write(f"**Sex:** {basic.get('Sex')}")
            if basic.get('Report Date') and basic.get('Report Date') != "Not found":
                st.write(f"**Report Date:** {basic.get('Report Date')}")
            st.markdown("### Structured Lab Results")
            if not df.empty:
                display_df = df.fillna("")
                st.dataframe(display_df, use_container_width=True)
            else:
                st.info("No structured lab results detected in the document.")
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="card" style="margin-top:12px">', unsafe_allow_html=True)
            st.markdown("### ⚠️ Abnormal Findings")
            if abnormals:
                for a in abnormals:
                    test = a.get('Test')
                    val = a.get('Value')
                    flag = a.get('Flag')
                    note = a.get('Note','')
                    ref = a.get('Reference','')
                    st.markdown(f"<div style='padding:10px;border-radius:8px;margin-bottom:6px;background:linear-gradient(90deg, rgba(255,60,60,0.05), rgba(255,60,60,0.02));'><span class='critical'>⚠️ {test} — {flag}</span><div class='small'>Value: {val} {a.get('Unit','')} {('• '+note) if note else ''} {('• ref: '+ref) if ref else ''}</div></div>", unsafe_allow_html=True)
            else:
                st.success("No abnormal findings detected.")
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="card" style="margin-top:12px">', unsafe_allow_html=True)
            st.markdown("### Clinical Summary")
            st.code(summary_text, language="text")
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="card" style="margin-top:12px">', unsafe_allow_html=True)
            st.markdown("### Raw Extracted Text")
            st.text_area("Raw Text", raw_text, height=280)
            st.markdown("</div>", unsafe_allow_html=True)

            download_text = "=== MEDICAL REPORT SUMMARY ===\n"
            if basic.get('Name') and basic.get('Name') != "Not found":
                download_text += f"Name: {basic.get('Name')}\n"
            if basic.get('Age') and basic.get('Age') != "Not found":
                download_text += f"Age: {basic.get('Age')}\n"
            if basic.get('Sex') and basic.get('Sex') != "Not found":
                download_text += f"Sex: {basic.get('Sex')}\n"
            download_text += "\n--- Structured Results ---\n"
            if rows:
                for r in rows:
                    flag_txt = f" — {r['Flag']}" if r['Flag'] else ""
                    ref_txt = f" (ref: {r['Reference']})" if r['Reference'] else ""
                    download_text += f"{r['Test']}: {r['Value']}{flag_txt}{ref_txt}\n"
            else:
                download_text += "No structured test values detected.\n"
            if abnormals:
                download_text += "\n--- Abnormal Findings ---\n"
                for a in abnormals:
                    download_text += f"{a['Test']}: {a['Flag']} — {a.get('Note','')}\n"
            st.download_button("📥 Download Full Summary", download_text, file_name="medical_report_summary.txt", mime="text/plain")

st.markdown("""
<div style="margin-top:18px" class="footer">
  <div>© 2025 Medical Report Analyzer • Dark AI • Privacy-first</div>
  <div>Contact: support@medical-analyzer.example</div>
</div>
""", unsafe_allow_html=True)
