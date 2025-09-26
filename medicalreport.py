import re

def load_report(file_path):
    with open(file_path, 'r') as file:
        return file.read()

def extract_info(report):
    info = {}

    # Extract name
    name_match = re.search(r'Patient Name:\s*(.*)', report)
    info['Name'] = name_match.group(1) if name_match else 'Not found'

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
    info['Diagnosis'] = diag_match.group(1) if diag_match else 'Not found'

    # Medications
    meds_match = re.search(r'Medications:\s*(.*)', report)
    info['Medications'] = meds_match.group(1) if meds_match else 'Not found'

    return info

def analyze(info):
    alerts = []

    # Check BP
    if info['Blood Pressure'] != 'Not found':
        systolic = int(info['Blood Pressure'].split('/')[0])
        diastolic = int(info['Blood Pressure'].split('/')[1])
        if systolic > 140 or diastolic > 90:
            alerts.append("⚠️ High Blood Pressure")

    # Check Temperature
    if info['Temperature (F)'] != 'Not found' and info['Temperature (F)'] > 100.4:
        alerts.append("⚠️ Fever Detected")

    return alerts

def display(info, alerts):
    print("\n=== Medical Report Summary ===")
    for key, value in info.items():
        print(f"{key}: {value}")
    print("\n--- Alerts ---")
    if alerts:
        for alert in alerts:
            print(alert)
    else:
        print("No alerts.")

if __name__ == "__main__":
    report_text = load_report("sample_report.txt")
    extracted_info = extract_info(report_text)
    alerts = analyze(extracted_info)
    display(extracted_info, alerts)
