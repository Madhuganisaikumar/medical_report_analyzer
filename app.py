import streamlit as st
import time
import datetime

# ----------- Custom CSS for splash and desktop ----------
st.markdown("""
    <style>
    body, .stApp { background: #000 !important; }
    .glow {
        font-family: 'Orbitron', monospace, sans-serif;
        font-size: 60px;
        color: #fff;
        text-align: center;
        letter-spacing: 10px;
        text-shadow: 0 0 10px #fff, 0 0 20px #0ff, 0 0 30px #0ff, 0 0 40px #0ff;
        margin-top: 100px;
        animation: flicker 1.5s infinite alternate;
    }
    @keyframes flicker {
      0% { opacity: 1; text-shadow: 0 0 10px #fff, 0 0 20px #0ff, 0 0 30px #0ff, 0 0 40px #0ff;}
      50% { opacity: 0.7; text-shadow: 0 0 20px #fff, 0 0 30px #0ff, 0 0 40px #0ff, 0 0 60px #0ff;}
      100% { opacity: 1; text-shadow: 0 0 14px #fff, 0 0 24px #0ff, 0 0 36px #0ff, 0 0 48px #0ff;}
    }
    .loading-msg {
        color: #aaa;
        text-align: center;
        font-size: 22px;
        margin-bottom: 10px;
        font-family: 'Roboto Mono', monospace;
    }
    .init-status {
        color: #fff;
        text-align: center;
        margin-top: 10px;
        font-size: 18px;
        font-family: 'Roboto Mono', monospace;
    }
    /* Desktop Screen */
    .sidebar-icons img { width: 40px; margin-bottom: 10px; }
    .sidebar-icons .icon-label {
        margin-bottom: 30px;
        font-size: 18px;
        font-family: 'Segoe UI', Arial, sans-serif;
        color: #222;
    }
    .center-logo {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 60vh;
    }
    .center-logo img { max-width: 380px; }
    .taskbar {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100vw;
        background: #222d35;
        display: flex;
        justify-content: center;
        align-items: center;
        height: 60px;
        z-index: 100;
    }
    .taskbar-icons {
        display: flex;
        align-items: center;
        gap: 30px;
    }
    .taskbar-icons .icon-box {
        display: flex;
        flex-direction: column;
        align-items: center;
        color: #fff;
        font-size: 14px;
        margin: 0 12px;
    }
    .taskbar-icons img { width: 36px; margin-bottom: 4px; }
    .taskbar-datetime {
        position: absolute;
        right: 36px;
        color: #fff;
        background: rgba(40,40,40,0.9);
        padding: 8px 18px;
        border-radius: 8px;
        font-size: 16px;
    }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Roboto+Mono&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

def splash_screen():
    loading_msgs = [
        "In",
        "Loading essential services..",
        "Configuring security protocols...",
        "Launching interface..."
    ]
    progress_bar = st.empty()
    glow_header = st.empty()
    loadmsg = st.empty()
    statusmsg = st.empty()
    glow_header.markdown('<div class="glow">ZAP</div>', unsafe_allow_html=True)
    for i in range(101):
        if i < 25:
            msg = loading_msgs[0]
        elif i < 50:
            msg = loading_msgs[1]
        elif i < 85:
            msg = loading_msgs[2]
        else:
            msg = loading_msgs[3]
        loadmsg.markdown(f'<div class="loading-msg">{msg}</div>', unsafe_allow_html=True)
        progress_bar.progress(i)
        statusmsg.markdown(f'<div class="init-status">System initialization: {i}%</div>', unsafe_allow_html=True)
        time.sleep(0.01)
    # Clear splash and set session state
    glow_header.empty()
    loadmsg.empty()
    progress_bar.empty()
    statusmsg.empty()
    st.session_state.loaded = True

if "loaded" not in st.session_state:
    splash_screen()

# ----------- Desktop Portfolio Screen -----------
# Sidebar icons
st.sidebar.markdown("""
    <div class="sidebar-icons">
        <a href="https://drive.google.com/file/d/1cM77ga8TZzhngI30XniL03WammTL4PHU/view?usp=sharing" target="_blank">
            <img src="https://img.icons8.com/ios-filled/50/000000/resume.png"/>
            <div class="icon-label">Resume</div>
        </a>
        <a href="https://github.com/Madhuganisaikumar" target="_blank">
            <img src="https://img.icons8.com/material-rounded/48/000000/github.png"/>
            <div class="icon-label">GitHub</div>
        </a>
        <a href="https://tryhackme.com/p/Madhuganisai" target="_blank">
            <img src="https://raw.githubusercontent.com/Madhuganisaikumar/portfolio/main/thm_icon.png"/>
            <div class="icon-label">THM</div>
        </a>
        <a href="https://www.linkedin.com/in/sai-madhugani/" target="_blank">
            <img src="https://img.icons8.com/color/48/000000/linkedin-circled.png"/>
            <div class="icon-label">Linkedin</div>
        </a>
    </div>
""", unsafe_allow_html=True)

# Center ZAP Logo
st.markdown("""
    <div class="center-logo">
        <img src="https://raw.githubusercontent.com/Madhuganisaikumar/portfolio/main/zap_logo.png" alt="ZAP Logo"/>
    </div>
""", unsafe_allow_html=True)

# Desktop-like taskbar
st.markdown("""
    <div class="taskbar">
        <div class="taskbar-icons">
            <div class="icon-box">
                <img src="https://img.icons8.com/external-outline-juicy-fish/60/external-terminal-coding-outline-outline-juicy-fish.png"/>
                Terminal
            </div>
            <div class="icon-box">
                <img src="https://img.icons8.com/external-flatart-icons-outline-flatarticons/64/external-folder-basic-ui-elements-flatart-icons-outline-flatarticons-1.png"/>
                Certifications
            </div>
            <div class="icon-box">
                <img src="https://img.icons8.com/ios-filled/50/stack-of-photos.png"/>
                Projects
            </div>
        </div>
        <div class="taskbar-datetime">
            {date} | {time}
        </div>
    </div>
""".replace("{date}", datetime.datetime.now().strftime("%a, %b %d, %Y")).replace("{time}", datetime.datetime.now().strftime("%I:%M:%S %p")), unsafe_allow_html=True)
