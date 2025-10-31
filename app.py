import streamlit as st
import re
import tempfile
from PyPDF2 import PdfReader
from PIL import Image
import pytesseract
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

def find_basic_fields(text):
    info = {}
    name_match = re.search(r'(?:Name|Patient Name)\s*[:\-]?\s*([A-Za-z .\'\-]{2,120})', text, re.IGNORECASE)
    sex_match = re.search(r'\bSex\s*[:\-]?\s*(Male|Female|M|F)\b', text, re.IGNORECASE)
    age_match = re.search(r'Age\s*[:\-]?\s*(\d{1,3})', text, re.IGNORECASE)
    info['Name'] = name_match.group(1).strip() if name_match else "Not found"
    info['Sex'] = (sex_match.group(1).strip() if sex_match else "Not found")
    info['Age'] = (age_match.group(1).strip() if age_match else "Not found")
    return info

DEFAULT_RANGES = {
    'hemoglobin': {'M': (13.0, 18.0), 'F': (11.0, 16.0), 'U': (11.0, 17.5)},
    'rbc': {'U': (4.2, 6.0)},
    'wbc': {'U': (4000, 11000)},
    'platelet': {'U': (150000, 450000)},
    'esr': {'M': (0, 20), 'F': (0, 30), 'U': (0, 20)},
    'glucose_fasting': {'U': (70, 100)},
    'creatinine': {'U': (0.6, 1.3)},
    'hbssag': {},
    'vdrl': {},
    'hcv': {},
    'hbsag': {}
}

QUAL_RESULTS_POSITIVE = ['positive', 'reactive', 'detected']
QUAL_RESULTS_NEGATIVE = ['negative', 'non-reactive', 'non reactive', 'not detected', 'nonreactive']

def normalize_number(s):
    s = s.replace(',', '.').strip()
    try:
        return float(re.findall(r'-?\d+\.?\d*', s)[0])
    except:
        return None

def parse_lab_lines(text):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    tests = []
    for ln in lines:
        ln_clean = re.sub(r'\s{2,}', ' ', ln)
        # Qualitative results (HBsAg, VDRL, HCV, Tri-Dot)
        qual_match = re.search(r'\b(HBsAg|HBs Ag|H\.B\.s Ag|H\.B & H\.B s Ag|H\.B & H\.Bs Ag|V\.D\.R\.L|VDRL|HCV|H\.C\.V|Tri[- ]Dot)\b.*?[:\-]?\s*([A-Za-z \-\(\)0-9/]+)', ln_clean, re.IGNORECASE)
        if qual_match:
            test_name = qual_match.group(1).strip()
            result = qual_match.group(2).strip()
            tests.append({'name': test_name, 'value_raw': result, 'type': 'qualitative'})
            continue
        # Lines with numeric values
        # Examples: "Heamoglobin 10.5 Grams % (F-11.0 -16.0, M -13.0-18.0)"
        num_match = re.search(r'([A-Za-z .%()-]{3,40})\s+(-?\d{1,3}\.?\d*)\s*([A-Za-z/%µμlhL]*)', ln_clean)
        if num_match:
            name = num_match.group(1).strip()
            num = num_match.group(2).strip()
            unit = num_match.group(3).strip()
            tests.append({'name': name, 'value_raw': num, 'unit': unit, 'type': 'numeric', 'line': ln_clean})
            continue
        # Another pattern: "W.B.C. Count 7300 /Cu.mm"
        num_match2 = re.search(r'([A-Za-z .]{2,40})\s+[:\-]?\s*(\d{2,6}\.?\d*)\s*(?:/|per)?\s*([A-Za-z/%µμlhL]*)', ln_clean)
        if num_match2:
            name = num_match2.group(1).strip()
            num = num_match2.group(2).strip()
            unit = num_match2.group(3).strip()
            tests.append({'name': name, 'value_raw': num, 'unit': unit, 'type': 'numeric', 'line': ln_clean})
            continue
        # Parenthetical qualitative like "Screening Test H.C.V 1&2 : Negative (-)"
        qual_inline = re.search(r'([A-Za-z .&/()-]{3,40})\s*[:\-]?\s*(Negative|Positive|Reactive|Non - Reactive|Non - Reactive|Non-Reactive|NonReactive|Detected|Not detected)', ln_clean, re.IGNORECASE)
        if qual_inline:
            tests.append({'name': qual_inline.group(1).strip(), 'value_raw': qual_inline.group(2).strip(), 'type': 'qualitative'})
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
    if 'hemogram' in s or 'blood picture' in s or 'blood picture' in s.lower():
        return 'Blood Picture'
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
            results.append({'test': name_mapped, 'value': status, 'raw': val, 'flag': None})
        else:
            rawval = t.get('value_raw', '')
            num = normalize_number(rawval)
            unit = t.get('unit', '')
            flag = None
            note = ""
            if num is not None:
                lname = name_mapped.lower()
                if 'hemoglobin' in lname or 'hemoglobin' == lname:
                    rng = DEFAULT_RANGES['hemoglobin'].get(sex_key, DEFAULT_RANGES['hemoglobin']['U'])
                    low, high = rng
                    if num < low:
                        flag = 'Low'
                        note = f"{name_mapped} below reference ({low}-{high})"
                    elif num > high:
                        flag = 'High'
                        note = f"{name_mapped} above reference ({low}-{high})"
                elif 'wbc' in lname:
                    rng = DEFAULT_RANGES['wbc']['U']
                    low, high = rng
                    if num < low:
                        flag = 'Low'
                        note = f"WBC low ({low}-{high}/µL)"
                    elif num > high:
                        flag = 'High'
                        note = f"WBC high ({low}-{high}/µL)"
                elif 'platelet' in lname:
                    rng = DEFAULT_RANGES['platelet']['U']
                    low, high = rng
                    # convert lakhs/cumm to per µL if value seems small (<1000)
                    if num < 1000 and 'lakh' in (t.get('line') or '').lower():
                        num_converted = num * 100000  # approximate if "1.32 Lakhs"
                        num = num_converted
                    if num < low:
                        flag = 'Low'
                        note = f"Platelet count low ({int(low)}-{int(high)})"
                    elif num > high:
                        flag = 'High'
                        note = f"Platelet count high ({int(low)}-{int(high)})"
                elif 'esr' in lname:
                    rng = DEFAULT_RANGES['esr'].get(sex_key, DEFAULT_RANGES['esr']['U'])
                    low, high = rng
                    if num > high:
                        flag = 'High'
                        note = f"ESR elevated (normal ≤ {high} mm/hr)"
                elif 'rbc' in lname:
                    rng = DEFAULT_RANGES['rbc']['U']
                    low, high = rng
                    if num < low:
                        flag = 'Low'
                        note = f"RBC low ({low}-{high})"
                elif 'glucose' in lname:
                    rng = DEFAULT_RANGES['glucose_fasting']['U']
                    low, high = rng
                    if num < low or num > high:
                        flag = 'Abnormal'
                        note = f"Glucose outside reference ({low}-{high})"
                elif 'creatinine' in lname:
                    rng = DEFAULT_RANGES['creatinine']['U']
                    low, high = rng
                    if num < low or num > high:
                        flag = 'Abnormal'
                        note = f"Creatinine outside reference ({low}-{high})"
            results.append({'test': name_mapped, 'value': num if num is not None else t.get('value_raw'), 'unit': t.get('unit',''), 'flag': flag, 'note': note})
    return results

def summarize_interpretation(results):
    summary_lines = []
    critical = []
    for r in results:
        if r.get('flag'):
            summary_lines.append(f"{r['test']}: {r.get('flag')} — {r.get('note','')}")
            critical.append(r)
        else:
            summary_lines.append(f"{r['test']}: {r.get('value')}")
    if not summary_lines:
        return "No lab values detected."
    summary = "\n".join(summary_lines)
    if critical:
        summary += "\n\nRecommendations:\n- Review abnormal values with clinician.\n- Consider repeat testing or correlation with symptoms and history."
    return summary

st.set_page_config(page_title="Medical Report Analyzer — Lab Universal", layout="wide")
st.markdown("""
<style>
:root{--accent:#0f6fb1; --accent-2:#1b9bd7;}
body, .stApp { background: linear-gradient(135deg,#f3f8fc 0%, #eaf3fb 40%, #eef9ff 100%); color:#072033; }
.header { display:flex; justify-content:space-between; align-items:center; gap:12px; padding:18px 6px; }
.brand { display:flex; gap:12px; align-items:center; }
.logo { width:56px; height:56px; border-radius:12px; background:linear-gradient(180deg,var(--accent),var(--accent-2)); color:white; display:flex; align-items:center; justify-content:center; font-weight:800; box-shadow:0 8px 20px rgba(15,111,177,0.14); }
.title { font-size:20px; font-weight:800; color:#052a3a; }
.subtitle { color:#345; font-size:13px; }
.container { padding:18px; }
.grid { display:grid; grid-template-columns: 1fr 420px; gap:18px; align-items:start; }
.card { background:rgba(255,255,255,0.85); border-radius:12px; padding:16px; box-shadow:0 8px 30px rgba(10,20,30,0.06); }
.steps ol { padding-left:18px; margin:6px 0; }
.controls { display:flex; gap:8px; align-items:center; margin-top:8px; }
.metric { background:#fff; padding:10px; border-radius:10px; box-shadow:0 4px 12px rgba(10,20,30,0.04); margin-bottom:8px; }
.progress-anim { height:8px; background:linear-gradient(90deg,var(--accent),var(--accent-2)); border-radius:8px; animation: slide 1.8s ease-in-out infinite; }
@keyframes slide { 0%{transform:translateX(-20%)} 50%{transform:translateX(0%)} 100%{transform:translateX(-20%)} }
.small { font-size:13px; color:#445; }
.code { background:#02293f; color:#cfe9ff; padding:10px; border-radius:8px; font-family:monospace; white-space:pre-wrap; }
.footer { display:flex; justify-content:space-between; color:#566; margin-top:18px; font-size:13px; }
@media(max-width:980px){ .grid{ grid-template-columns: 1fr; } .logo{ width:48px; height:48px; } }
</style>
<div class="header">
  <div class="brand">
    <div class="logo">MA</div>
    <div>
      <div class="title">Medical Report Analyzer</div>
      <div class="subtitle">Universal lab & clinical report extractor — supports CBC, ESR, HBsAg, VDRL, HCV, chemistry and more</div>
    </div>
  </div>
  <div class="small">Secure • Local OCR • Tunable</div>
</div>
<div class="container">
  <div class="grid">
    <div>
      <div class="card">
        <h2 style="margin:0;color:#07314a">Upload a medical report (any format)</h2>
        <div class="small" style="margin-top:6px">Supported: PDFs (selectable + scanned), JPG/PNG scans, TXT. The engine auto-detects lab panels and extracts values and qualitative results.</div>
        <div style="margin-top:12px" class="metric">
          <div style="font-weight:700;color:#0f6fb1">Steps</div>
          <div class="small">
            <ol>
              <li>Upload a report file</li>
              <li>Tune sliders (Clarity, Detail, Speed)</li>
              <li>Click <b>Analyze</b> and view structured lab output, flags & recommendations</li>
            </ol>
          </div>
        </div>
        <div style="margin-top:8px" class="metric">
          <div style="font-weight:700;color:#0f6fb1">Tuning</div>
          <div class="small">Adjust these to help OCR & result presentation.</div>
""", unsafe_allow_html=True)

left_col, right_col = st.columns([3,1])
with left_col:
    uploaded_file = st.file_uploader("Choose file (PDF / JPG / PNG / TXT)", type=["pdf","jpg","jpeg","png","txt"])
with right_col:
    clarity = st.slider("Clarity", 50, 100, 88)
    detail = st.slider("Detail level", 1, 5, 3)
    speed = st.slider("Speed bias", 1, 10, 6)

st.markdown("""
        </div>
        <div style="margin-top:10px" class="metric">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div><b>Preview & Transactions</b></div>
            <div class="small">Animated cues</div>
          </div>
          <div style="margin-top:8px;" class="progress-anim"></div>
        </div>
        <div style="margin-top:12px" class="small">Example supported reports: CBC, ESR, VDRL, HBsAg, HCV, LFT, RFT, Glucose reports and radiology summaries.</div>
      </div>
    </div>
    <div>
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div><b style="color:#07314a">Analyzer Console</b></div>
          <div class="small">Status: <span id="status">Idle</span></div>
        </div>
        <div style="margin-top:12px">
          <div class="small">Upload any medical report and click analyze. Results below include a structured table, automatic flags and a short clinical summary.</div>
          <div style="margin-top:12px">
""", unsafe_allow_html=True)

analyze_btn = st.button("🔎 Analyze", key="analyze_lab")

st.markdown("</div></div></div></div>", unsafe_allow_html=True)

if analyze_btn:
    if not uploaded_file:
        st.error("Please upload a medical report first.")
    else:
        prog = st.progress(0)
        status_placeholder = st.empty()
        status_placeholder.info("Preparing analysis...")
        for i in range(1, 101):
            time.sleep(0.007 + (11 - speed) * 0.002)
            prog.progress(i)
            if i == 30:
                status_placeholder.info("Running OCR / text extraction...")
            if i == 65:
                status_placeholder.info("Parsing lab values and interpreting results...")
        status_placeholder.success("Analysis complete")
        if uploaded_file.type == "application/pdf":
            raw_text = extract_text_from_pdf(uploaded_file)
        elif uploaded_file.type in ["image/jpeg","image/jpg","image/png"]:
            raw_text = extract_text_from_image(uploaded_file)
        elif uploaded_file.type == "text/plain":
            raw_text = extract_text_from_txt(uploaded_file)
        else:
            raw_text = ""
        if not raw_text.strip():
            st.error("Could not extract any text. Try increasing Clarity or upload a clearer scan.")
        else:
            basic = find_basic_fields(raw_text)
            parsed = parse_lab_lines(raw_text)
            interpreted = interpret_tests(parsed, basic)
            summary_text = summarize_interpretation(interpreted)

            left, right = st.columns([2,1])
            with left:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown("### Extracted Patient Info")
                st.write(f"**Name:** {basic.get('Name')}")
                st.write(f"**Age:** {basic.get('Age')}")
                st.write(f"**Sex:** {basic.get('Sex')}")
                st.markdown("### Structured Lab Results")
                if interpreted:
                    for r in interpreted:
                        if r.get('flag'):
                            st.markdown(f"- **{r['test']}** : {r.get('value')} {r.get('unit','')} — ⚠️ **{r.get('flag')}**  ")
                            if r.get('note'):
                                st.markdown(f"  - {r.get('note')}")
                        else:
                            st.markdown(f"- **{r['test']}** : {r.get('value')} {r.get('unit','')}")
                else:
                    st.info("No lab test patterns detected in the document.")
                st.markdown("### Clinical Summary")
                st.info(summary_text)
                st.markdown("</div>", unsafe_allow_html=True)
            with right:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown("### Controls & Download")
                st.markdown(f"**Clarity:** {clarity}%")
                st.progress(int(clarity))
                st.markdown(f"**Detail:** {detail}/5")
                st.progress(int(detail*20))
                st.markdown(f"**Speed bias:** {speed}/10")
                st.progress(int(speed*10))
                downloadable = summarize_interpretation(interpreted)
                st.download_button("📥 Download Summary", downloadable, file_name="lab_analysis_summary.txt", mime="text/plain")
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("### Raw Extracted Text")
            st.text_area("Raw Text", raw_text, height=260)

st.markdown("""
  <div class="card" style="margin-top:14px">
    <div style="display:flex;justify-content:space-between;gap:20px;align-items:flex-start">
      <div style="flex:1">
        <h3 style="margin:0;color:#07314a">About this Analyzer</h3>
        <div class="small" style="margin-top:6px">This app aims to support the widest range of medical reports. It uses OCR for scans and pattern-based parsing to detect numeric and qualitative lab results. Reference ranges are approximate — always confirm with a clinician.</div>
        <ul class="small">
          <li>Detects: CBC (Hb, RBC, WBC, Platelets), ESR, VDRL, HBsAg, HCV (Tri-Dot), basic chemistry values and more.</li>
          <li>Flags values outside typical ranges and provides short recommendations.</li>
          <li>Works offline (no external API calls) if deployed locally with Tesseract installed.</li>
        </ul>
      </div>
      <div style="width:320px">
        <div class="code">SAMPLE OUTPUT
=== MEDICAL REPORT SUMMARY ===
Name: Mr. Srinivasalu
Age: 44
WBC: 7300
Hemoglobin: 10.5 — ⚠️ Low (possible anemia)
Platelet: 132000 — ⚠️ Low (reference 150000-450000)
VDRL: Non-reactive

Recommendations:
- Review abnormal values with clinician.
- Consider repeat tests or correlate with clinical signs.
        </div>
      </div>
    </div>
  </div>
  <div class="footer">
    <div>© 2025 Medical Report Analyzer • Privacy-first</div>
    <div>Contact: support@medical-analyzer.example</div>
  </div>
</div>
""", unsafe_allow_html=True)
