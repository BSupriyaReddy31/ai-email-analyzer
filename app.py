import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
import json
import base64
import urllib.parse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# --- 1. Page Configuration & Custom CSS ---
st.set_page_config(page_title="Email Analyzer", page_icon="📧", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .header-icon { background-color: #2b9e90; color: white; padding: 10px 15px; border-radius: 8px; font-size: 24px; margin-right: 15px; }
    div.stButton > button { background-color: #4db6ac; color: white; border: none; border-radius: 6px; padding: 10px; }
    div.stButton > button:hover { background-color: #2b9e90; color: white; }
    .sentiment-badge { background-color: #1a73e8; color: white; padding: 3px 10px; border-radius: 12px; font-size: 14px; font-weight: bold; }
    .tts-card { background-color: #eef5f2; padding: 15px; border-radius: 8px; border: 1px solid #d1e2da; margin-top: 15px; }
    </style>
""", unsafe_allow_html=True)

# --- Helper Function to Decode Gmail Text ---
def get_email_body(payload):
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
    elif 'body' in payload and 'data' in payload['body']:
        return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    return "Could not extract plain text from this email."

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

if 'analyzed' not in st.session_state:
    st.session_state.analyzed = False
if 'gmail_creds' not in st.session_state:
    st.session_state.gmail_creds = None

email_text_to_analyze = ""

with col1:
    with st.container(border=True):
        st.markdown("**💬 Email Input**")
        tab1, tab2 = st.tabs(["Paste Text", "Gmail API"])
        
        # --- TAB 1: PASTE TEXT ---
        with tab1:
            manual_text = st.text_area("Paste your email text here...", height=250, label_visibility="collapsed")
            if manual_text:
                email_text_to_analyze = manual_text

        # --- TAB 2: GMAIL API ---
        with tab2:
            if "google_credentials_json" not in st.secrets:
                st.error("Google credentials not found in Streamlit Secrets!")
            else:
                client_config = json.loads(st.secrets["google_credentials_json"])
                scopes = ['https://www.googleapis.com/auth/gmail.readonly']
                
                if not st.session_state.gmail_creds:
                    # 1. Generate the link and SAVE the secret verifier in memory
                    if 'auth_url' not in st.session_state:
                        flow = Flow.from_client_config(client_config, scopes=scopes, redirect_uri='http://localhost')
                        auth_url, _ = flow.authorization_url(prompt='consent')
                        st.session_state.auth_url = auth_url
                        st.session_state.code_verifier = flow.code_verifier # <--- The Magic Fix

                    st.markdown(f"**Step 1:** [Click here to securely log in with Google]({st.session_state.auth_url})")
                    st.info("After logging in, ignore the 'Site can't be reached' error. Copy the **ENTIRE URL** from the top of your browser and paste it below.")
                    
                    user_input = st.text_input("**Step 2:** Paste the ENTIRE URL here:")
                    
                    if st.button("Connect Inbox"):
                        if not user_input:
                            st.warning("Please paste the URL first!")
                        else:
                            with st.spinner("Authenticating with Google..."):
                                try:
                                    if "localhost" in user_input:
                                        parsed_url = urllib.parse.urlparse(user_input)
                                        extracted_code = urllib.parse.parse_qs(parsed_url.query)['code'][0]
                                    else:
                                        extracted_code = user_input
                                    
                                    extracted_code = urllib.parse.unquote(extracted_code).strip()

                                    # 2. Rebuild the flow and INJECT the saved verifier
                                    flow = Flow.from_client_config(client_config, scopes=scopes, redirect_uri='http://localhost')
                                    flow.code_verifier = st.session_state.code_verifier # <--- Injecting it back
                                    
                                    flow.fetch_token(code=extracted_code)
                                    st.session_state.gmail_creds = flow.credentials.to_json()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                else:
                    st.success("✅ Securely connected to Gmail!")
                    try:
                        creds = Credentials.from_authorized_user_info(json.loads(st.session_state.gmail_creds), scopes)
                        service = build('gmail', 'v1', credentials=creds)
                        
                        results = service.users().messages().list(userId='me', maxResults=5).execute()
                        messages = results.get('messages', [])
                        
                        if not messages:
                            st.info("No recent emails found.")
                        else:
                            email_dict = {}
                            for msg in messages:
                                msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                                headers = msg_data['payload']['headers']
                                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
                                body = get_email_body(msg_data['payload'])
                                email_dict[subject] = body
                            
                            selected_subject = st.selectbox("Select a recent email to analyze:", list(email_dict.keys()))
                            email_text_to_analyze = email_dict[selected_subject]
                            
                            with st.expander("Preview Selected Email"):
                                st.write(email_text_to_analyze)
                                
                    except Exception as e:
                        st.error(f"Error fetching emails: {e}")
        analyze_clicked = st.button("⚡ Analyze Email", use_container_width=True)

# --- 4. Processing & State Updates ---
if analyze_clicked:
    if not api_key:
        st.sidebar.error("Please enter your Gemini API Key first.")
    elif not email_text_to_analyze.strip():
        st.warning("Please provide an email to analyze (either paste it or select from Gmail).")
    else:
        with st.spinner("Analyzing email with Gemini..."):
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                prompt = f"""
                Analyze the following email and extract insights exactly in this format:
                LANGUAGE: [Language name]
                SENTIMENT: [Positive/Neutral/Negative/Urgent]
                VOICE_TONE: [Tone]
                ACTION_ITEMS: [Bulleted list or "None"]
                TTS_SUMMARY: [1-line conversational voice summary]
                
                Email text:
                {email_text_to_analyze}
                """
                
                response = model.generate_content(prompt)
                result_text = response.text
                
                st.session_state.lang = "Unknown"
                st.session_state.sentiment = "Neutral"
                st.session_state.tone = "Standard"
                st.session_state.summary = "Summary generation failed."
                st.session_state.actions = "None"

                for line in result_text.split('\n'):
                    if line.startswith("LANGUAGE:"): st.session_state.lang = line.replace("LANGUAGE:", "").strip()
                    elif line.startswith("SENTIMENT:"): st.session_state.sentiment = line.replace("SENTIMENT:", "").strip()
                    elif line.startswith("VOICE_TONE:"): st.session_state.tone = line.replace("VOICE_TONE:", "").strip()
                    elif line.startswith("TTS_SUMMARY:"): st.session_state.summary = line.replace("TTS_SUMMARY:", "").strip()
                    elif line.startswith("ACTION_ITEMS:"): st.session_state.actions = result_text.split("ACTION_ITEMS:")[1].split("TTS_SUMMARY:")[0].strip()
                
                tts = gTTS(text=st.session_state.summary, lang='en', slow=False)
                tts.save("summary_audio.mp3")
                st.session_state.analyzed = True
                
            except Exception as e:
                st.error(f"Error: {e}")

# --- 5. Output Column ---
with col2:
    if not st.session_state.analyzed:
        with st.container(border=True):
            st.markdown("<div style='height: 380px; display: flex; align-items: center; justify-content: center; color: #64748b;'>Analysis results will appear here</div>", unsafe_allow_html=True)
    else:
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
            
        st.markdown(f"""
            <div class="tts-card">
                <p style="font-size: 12px; color: #64748b; font-weight: bold;">TTS SUMMARY</p>
                <p style="font-weight: 500;">{st.session_state.summary}</p>
            </div>
        """, unsafe_allow_html=True)
        
        if os.path.exists("summary_audio.mp3"):
            st.audio("summary_audio.mp3")
