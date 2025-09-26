import streamlit as st
import re
import tempfile
from PyPDF2 import PdfReader
from PIL import Image
import pytesseract
import requests
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
    return text

def extract_text_from_image(uploaded_file):
    img = Image.open(uploaded_file)
    text = pytesseract.image_to_string(img)
    return text

def extract_text_from_txt(uploaded_file):
    return uploaded_file.read().decode("utf-8")

def extract_info(report):
    info = {}

    # Flexible regex for Name (avoid picking up legal notes)
    name_match = re.search(
        r'(?:Name\s*:\s*|^Name\s*:\s*)([^,\n\r0-9]{2,100})', report, re.IGNORECASE | re.MULTILINE)
    if not name_match:
        # Try format "Name .... Dr Tan Ah Moi"
        name_match = re.search(r'Name[^\n\r:]{0,10}:?\s*([A-Za-z .\'\-]{3,100})', report)
    info['Name'] = name_match.group(1).strip() if name_match else 'Not found'

    # Flexible regex for Age (try several formats)
    age_match = re.search(r'Age\s*[:\-]?\s*(\d{1,3})', report, re.IGNORECASE)
    if not age_match:
        age_match = re.search(r'(\d{1,3})\s*(?:years|yrs|year|yr|yo)\b', report, re.IGNORECASE)
    info['Age'] = age_match.group(1) if age_match else 'Not found'

    # Blood Pressure (BP)
    bp_match = re.search(r'(?:Blood Pressure|BP)[^\d]{0,10}(\d{2,3}/\d{2,3})', report, re.IGNORECASE)
    info['Blood Pressure'] = bp_match.group(1) if bp_match else 'Not found'

    # Temperature
    temp_match = re.search(r'Temperature[^\d]{0,10}(\d{2,3}\.?\d*)\s*([CF])', report, re.IGNORECASE)
    if temp_match:
        info['Temperature'] = f"{temp_match.group(1)} {temp_match.group(2)}"
    else:
        info['Temperature'] = 'Not found'

    # Diagnosis: Try to find block after "Diagnosis" up to next section or medications
    diag_match = re.search(
        r'Diagnosis\s*[:\-]?\s*((?:.|\n)*?)(?:\n\s*(?:SECTION|Medications|Rx|Prescribed|OPINION|PROGNOSIS|DECLARATION|Date|Signature|$))',
        report, re.IGNORECASE
    )
    if diag_match:
        diagnosis_text = diag_match.group(1)
        # Remove legal notes if present
        diagnosis_text = re.sub(r'(?i)section \d+.*', '', diagnosis_text)
        # Remove trailing numbers, lines
        diagnosis_text = diagnosis_text.strip().replace('\n', ' ')
        # Just keep lines that look like diagnoses (numbered or itemized)
        diagnosis_lines = [line.strip() for line in diagnosis_text.split('\n') if line.strip()]
        diagnosis = ' '.join(diagnosis_lines)
        diagnosis = re.sub(r'(\d+\s*-\s*)', '', diagnosis)  # remove section numbers
        info['Diagnosis'] = diagnosis[:300] if diagnosis else 'Not found'
    else:
        info['Diagnosis'] = 'Not found'

    # Medications: Try to find block after "Medications" up to next section
    meds_match = re.search(
        r'(Medications|Rx|Prescribed)\s*[:\-]?\s*((?:.|\n)*?)(?:\n\s*(?:SECTION|Diagnosis|OPINION|PROGNOSIS|DECLARATION|Date|Signature|$))',
        report, re.IGNORECASE
    )
    if meds_match:
        meds_text = meds_match.group(2)
        # Remove legal notes if present
        meds_text = re.sub(r'(?i)section \d+.*', '', meds_text)
        # Just keep lines that look like medicines
        meds_lines = [line.strip() for line in meds_text.split('\n') if line.strip()]
        meds = ', '.join(meds_lines)
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
        except Exception:
            alerts.append("⚠️ Unable to parse blood pressure values.")
    if info.get('Temperature', 'Not found') != 'Not found':
        try:
            value, unit = info['Temperature'].split()
            value = float(value)
            if (unit.upper() == 'F' and value > 100.4) or (unit.upper() == 'C' and value > 38):
                alerts.append("⚠️ Fever Detected")
        except Exception:
            alerts.append("⚠️ Unable to parse temperature value.")
    return alerts

def download_results(info, alerts):
    summary = "=== Medical Report Summary ===\n"
    for key, value in info.items():
        summary += f"{key}: {value}\n"
    summary += "\n--- Alerts ---\n"
    if alerts:
        for alert in alerts:
            summary += alert + "\n"
    else:
        summary += "No alerts.\n"
    return summary

def show_example_report_image():
    img_url = "https://cdn.pixabay.com/photo/2017/01/09/23/55/medical-1966095_1280.jpg"
    try:
        response = requests.get(img_url)
        img = Image.open(BytesIO(response.content))
        st.image(img, caption="Example Medical Report Format", use_column_width=True)
    except Exception:
        st.info("Could not load example image.")

def show_health_icon():
    icon_url = "https://cdn-icons-png.flaticon.com/512/2698/2698194.png"
    try:
        response = requests.get(icon_url)
        img = Image.open(BytesIO(response.content))
        st.image(img, width=100)
    except Exception:
        pass

def main():
    st.set_page_config(page_title="Medical Report Analyzer", layout="wide")
    show_health_icon()
    st.title("Medical Report Analyzer")
    st.markdown(
        """
        Welcome to the Medical Report Analyzer!  
        This tool helps you analyze medical reports in PDF, image, or text format.  
        You will receive an instant summary and health alerts based on your report.
        """
    )

    show_example_report_image()

    st.markdown("#### Features")
    st.markdown("""
    - Upload PDF, image (JPG/PNG), or text files containing medical reports.
    - Extracts key details: Patient Name, Age, Blood Pressure, Temperature, Diagnosis, Medications.
    - Flags high blood pressure and fever automatically.
    - Download the analysis result as a text file.
    """)

    st.header("Guide to Upload Files")
    st.markdown(
        """
        **Supported File Types:**  
        - PDF (with selectable text)  
        - Image files (JPG, PNG) for scanned or photographed reports  
        - TXT (plain text)
        
        **Sample Format For Text Extraction:**  
        ```
        Patient Name: John Doe
        Age: 45 years
        Blood Pressure: 150/95
        Temperature: 101.2 F
        Diagnosis: Hypertension, Diabetes
        Medications: Lisinopril, Aspirin
        ```
        For images, ensure the report text is clear and readable.
        """
    )

    st.header("Analyze Your Medical Report")
    uploaded_file = st.file_uploader(
        "Upload a PDF, Image (JPG/PNG), or Text File",
        type=["pdf", "jpg", "jpeg", "png", "txt"]
    )

    if uploaded_file:
        with st.spinner("Extracting text from file..."):
            if uploaded_file.type == "application/pdf":
                report_text = extract_text_from_pdf(uploaded_file)
            elif uploaded_file.type in ["image/jpeg", "image/png", "image/jpg"]:
                report_text = extract_text_from_image(uploaded_file)
            elif uploaded_file.type == "text/plain":
                report_text = extract_text_from_txt(uploaded_file)
            else:
                report_text = ""
        
        if not report_text.strip():
            st.error("Could not extract text from file. Please check file quality or format.")
        else:
            extracted_info = extract_info(report_text)
            alerts = analyze(extracted_info)

            st.subheader("Medical Report Summary")
            for key, value in extracted_info.items():
                st.write(f"**{key}:** {value}")

            st.subheader("Alerts")
            if alerts:
                for alert in alerts:
                    st.warning(alert)
            else:
                st.success("No alerts.")

            st.expander("Raw Extracted Text").write(report_text)

            st.session_state["download_info"] = extracted_info
            st.session_state["download_alerts"] = alerts

    st.header("Download Results")
    if "download_info" in st.session_state and "download_alerts" in st.session_state:
        analysis_text = download_results(
            st.session_state["download_info"], st.session_state["download_alerts"]
        )
        st.download_button(
            label="Download Analysis Result",
            data=analysis_text,
            file_name="medical_report_analysis.txt",
            mime="text/plain"
        )
        st.text_area("Preview", analysis_text, height=300)
    else:
        st.info("Analyze a report first to enable downloads.")

if __name__ == "__main__":
    main()
