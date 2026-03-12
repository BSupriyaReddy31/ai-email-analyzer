import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import os

# --- 1. Page Configuration & Custom CSS ---
st.set_page_config(page_title="Email Analyzer", page_icon="📧", layout="wide")

# Injecting custom CSS to match the exact styling from your screenshots
st.markdown("""
    <style>
    /* Main background and font */
    .stApp { background-color: #f8f9fa; }
    
    /* Header icon styling */
    .header-icon {
        background-color: #2b9e90;
        color: white;
        padding: 10px 15px;
        border-radius: 8px;
        font-size: 24px;
        margin-right: 15px;
    }
    
    /* Teal button styling for Analyze Email */
    div.stButton > button {
        background-color: #4db6ac;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px;
    }
    div.stButton > button:hover {
        background-color: #2b9e90;
        color: white;
    }
    
    /* Sentiment Badge */
    .sentiment-badge {
        background-color: #1a73e8;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 14px;
        font-weight: bold;
    }
    
    /* TTS Summary Card Background */
    .tts-card {
        background-color: #eef5f2;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #d1e2da;
        margin-top: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. Header Section ---
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Enter Gemini API Key:", type="password")

st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 30px;">
        <div class="header-icon">📧</div>
        <div>
            <h2 style="margin: 0; padding: 0; color: #1e293b; font-size: 24px;">Email Analyzer</h2>
            <p style="margin: 0; padding: 0; color: #64748b; font-size: 14px;">AI-powered email insight engine</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 3. Layout: Two Columns ---
col1, space, col2 = st.columns([1, 0.05, 1.2])

# Initialize session state for analysis results
if 'analyzed' not in st.session_state:
    st.session_state.analyzed = False

with col1:
    with st.container(border=True):
        st.markdown("**💬 Email Input**")
        
        # Tabs replicating "Paste Text" and "Gmail"
        tab1, tab2 = st.tabs(["Paste Text", "Gmail"])
        
        with tab1:
            email_text = st.text_area(
                "Paste your email text here (including any attachment text)...", 
                height=300, 
                label_visibility="collapsed"
            )
        with tab2:
            st.info("Gmail API integration goes here.")
            
        analyze_clicked = st.button("⚡ Analyze Email", use_container_width=True)

# --- 4. Processing & State Updates ---
if analyze_clicked:
    if not api_key:
        st.sidebar.error("Please enter API Key first.")
    elif not email_text.strip():
        st.warning("Please paste an email to analyze.")
    else:
        with st.spinner("Analyzing email..."):
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = f"""
                Analyze the following email and extract insights exactly in this format:
                LANGUAGE: [Language name]
                SENTIMENT: [Positive/Neutral/Negative/Urgent]
                VOICE_TONE: [Tone]
                ACTION_ITEMS: [Bulleted list]
                TTS_SUMMARY: [1-line voice summary]
                
                Email text:
                {email_text}
                """
                
                response = model.generate_content(prompt)
                result_text = response.text
                
                # Parse results
                for line in result_text.split('\n'):
                    if line.startswith("LANGUAGE:"): st.session_state.lang = line.replace("LANGUAGE:", "").strip()
                    elif line.startswith("SENTIMENT:"): st.session_state.sentiment = line.replace("SENTIMENT:", "").strip()
                    elif line.startswith("VOICE_TONE:"): st.session_state.tone = line.replace("VOICE_TONE:", "").strip()
                    elif line.startswith("TTS_SUMMARY:"): st.session_state.summary = line.replace("TTS_SUMMARY:", "").strip()
                    elif line.startswith("ACTION_ITEMS:"): st.session_state.actions = result_text.split("ACTION_ITEMS:")[1].split("TTS_SUMMARY:")[0].strip()
                
                # Generate Audio
                tts = gTTS(text=st.session_state.summary, lang='en', slow=False)
                tts.save("summary_audio.mp3")
                
                st.session_state.analyzed = True
                
            except Exception as e:
                st.error(f"Error: {e}")

# --- 5. Output Column (Right Side) ---
with col2:
    if not st.session_state.analyzed:
        # Empty State
        with st.container(border=True):
            st.markdown(
                """
                <div style="height: 380px; display: flex; align-items: center; justify-content: center; color: #64748b;">
                    Analysis results will appear here
                </div>
                """, 
                unsafe_allow_html=True
            )
    else:
        # Filled State
        row1_col1, row1_col2 = st.columns(2)
        
        with row1_col1:
            with st.container(border=True):
                st.markdown("<p style='font-size: 12px; color: #64748b; margin-bottom: 0;'>🌐 LANGUAGE</p>", unsafe_allow_html=True)
                st.markdown(f"**{st.session_state.lang}**")
                
        with row1_col2:
            with st.container(border=True):
                st.markdown("<p style='font-size: 12px; color: #64748b; margin-bottom: 5px;'>⚡ SENTIMENT</p>", unsafe_allow_html=True)
                st.markdown(f"<span class='sentiment-badge'>{st.session_state.sentiment}</span>", unsafe_allow_html=True)
                
        with st.container(border=True):
            st.markdown("<p style='font-size: 12px; color: #64748b; margin-bottom: 0;'>🔊 VOICE TONE SUGGESTION</p>", unsafe_allow_html=True)
            st.markdown(f"**{st.session_state.tone}**")
            
        with st.container(border=True):
            st.markdown("<p style='font-size: 14px; font-weight: bold; margin-bottom: 5px;'>✔️ Action Items</p>", unsafe_allow_html=True)
            st.markdown(st.session_state.actions)
            
        # TTS Summary Box
        st.markdown(f"""
            <div class="tts-card">
                <p style="font-size: 12px; color: #64748b; font-weight: bold;">TTS SUMMARY</p>
                <p style="font-weight: 500;">{st.session_state.summary}</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Audio Player (Acts as the 'Speak' button)
        if os.path.exists("summary_audio.mp3"):
            st.audio("summary_audio.mp3")
