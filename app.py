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
        text += page.extract_text() or ""
    return text

def extract_text_from_image(uploaded_file):
    img = Image.open(uploaded_file)
    text = pytesseract.image_to_string(img)
    return text

def extract_text_from_txt(uploaded_file):
    return uploaded_file.read().decode("utf-8")

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

def download_results(info, alerts):
    # Generates a summary for download
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

def main():
    st.set_page_config(page_title="Medical Report Analyzer", layout="wide")
    tabs = st.tabs(["🏠 Home", "📄 Guide to Upload", "⬆️ Analyze Report", "⬇️ Download Results"])

    # Home Tab
    with tabs[0]:
        st.title("Medical Report Analyzer")
        st.markdown(
            """
            Welcome to the Medical Report Analyzer!  
            This tool helps you analyze medical reports in PDF, image, or text format.  
            You will receive an instant summary and health alerts based on your report.
            """
        )
        st.markdown("#### Features")
        st.markdown("""
        - Upload PDF, image (JPG/PNG), or text files containing medical reports.
        - Extracts key details: Patient Name, Age, Blood Pressure, Temperature, Diagnosis, Medications.
        - Flags high blood pressure and fever automatically.
        - Download the analysis result as a text file.
        """)

    # Guide Tab
    with tabs[1]:
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
            Age: 45
            Blood Pressure: 150/95
            Temperature: 101.2 F
            Diagnosis: Hypertension
            Medications: Lisinopril, Aspirin
            ```
            For images, ensure the report text is clear and readable.
            """
        )

    # Analyze Tab
    with tabs[2]:
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

                # Save for download tab
                st.session_state["download_info"] = extracted_info
                st.session_state["download_alerts"] = alerts

    # Download Tab
    with tabs[3]:
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
