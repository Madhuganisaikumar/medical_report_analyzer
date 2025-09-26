import streamlit as st
import re
import tempfile
from PyPDF2 import PdfReader

def load_report_from_pdf(pdf_file):
    # Save the uploaded file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(pdf_file.read())
        tmp_file_path = tmp_file.name
    # Read PDF text
    reader = PdfReader(tmp_file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def extract_info(report):
    info = {}

    # Extract name
    name_match = re.search(r'Patient Name:\s*(.*)', report)
    info['Name'] = name_match.group(1).strip() if name_match else 'Not found'

    # Age
    age_match = re.search(r'Age:\s*(\d+)', report)
    info['Age'] = int(age_match.group(1)) if age_match else 'Not found'

    # Blood Pressure
    bp_match = re.search(r'Blood Pressure:\s*([\d/]+)', report)
    info['Blood Pressure'] = bp_match.group(1) if bp_match else 'Not found'

    # Temperature
    temp_match = re.search(r'Temperature:\s*([\d.]+)\s*F', report)
    info['Temperature (F)'] = float(temp_match.group(1)) if temp_match else 'Not found'

    # Diagnosis
    diag_match = re.search(r'Diagnosis:\s*(.*)', report)
    info['Diagnosis'] = diag_match.group(1).strip() if diag_match else 'Not found'

    # Medications
    meds_match = re.search(r'Medications:\s*(.*)', report)
    info['Medications'] = meds_match.group(1).strip() if meds_match else 'Not found'

    return info

def analyze(info):
    alerts = []

    # Check BP
    if info['Blood Pressure'] != 'Not found':
        try:
            systolic = int(info['Blood Pressure'].split('/')[0])
            diastolic = int(info['Blood Pressure'].split('/')[1])
            if systolic > 140 or diastolic > 90:
                alerts.append("⚠️ High Blood Pressure")
        except Exception:
            alerts.append("⚠️ Unable to parse blood pressure values.")

    # Check Temperature
    if info['Temperature (F)'] != 'Not found':
        try:
            if info['Temperature (F)'] > 100.4:
                alerts.append("⚠️ Fever Detected")
        except Exception:
            alerts.append("⚠️ Unable to parse temperature value.")

    return alerts

def main():
    st.title("Medical Report Analyzer")

    st.write(
        """
        Upload a medical report in PDF format.  
        The app will extract key information and provide health alerts based on the data in the report.
        """
    )

    uploaded_file = st.file_uploader("Upload PDF report", type=["pdf"])

    if uploaded_file is not None:
        with st.spinner("Extracting and analyzing report..."):
            report_text = load_report_from_pdf(uploaded_file)
            if not report_text.strip():
                st.error("Could not extract text from PDF. Please check if the PDF contains selectable text.")
                return

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

if __name__ == "__main__":
    main()
