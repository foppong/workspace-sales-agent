"""
File: app.py
Description: eSignature Demo - Sidebar Chat + Exit Flow.
Reviewers: Engineering Manager & Principal Engineer
"""
import streamlit as st
import script
import base64
import os

# --- 1. CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Contract Draft - Google Docs")

# --- 2. ASSET HANDLING ---
def get_base64_image(image_path):
    if not os.path.exists(image_path):
        return None
    with open(image_path, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

bg_base64 = get_base64_image("Contract Draft.png")

# --- 3. STATE MANAGEMENT ---
if 'view' not in st.session_state: st.session_state.view = "PRESCREEN"
if 'chat_open' not in st.session_state: st.session_state.chat_open = False
if 'current_step' not in st.session_state: st.session_state.current_step = 0
if 'history' not in st.session_state:
    first_msg = script.get_state(0)
    st.session_state.history = [{"role": "bot", "text": first_msg['text']}]

# --- 4. CSS INJECTION ---
def inject_css():
    if bg_base64:
        bg_rule = f'background-image: url("data:image/png;base64,{bg_base64}"); background-size: cover; background-position: top center; background-attachment: fixed;'
    else:
        bg_rule = 'background-color: #f1f3f4;'

    st.markdown(f"""
        <style>
            /* 1. APP BACKGROUND */
            [data-testid="stAppViewContainer"] {{ {bg_rule} }}
            
            /* 2. HIDE DEFAULTS */
            [data-testid="stHeader"], [data-testid="stToolbar"] {{ display: none; }}
            .block-container {{ padding: 0 !important; max-width: 100%; }}
            
            /* 3. SIDEBAR HIJACK */
            section[data-testid="stSidebar"] {{
                width: 380px !important;
                min-width: 380px !important;
                height: 600px !important;
                position: fixed !important;
                top: auto !important; bottom: 20px !important;
                left: auto !important; right: 20px !important;
                border-radius: 16px !important;
                box-shadow: 0 12px 48px rgba(0,0,0,0.25) !important;
                border: 1px solid #e0e0e0 !important;
                z-index: 99999 !important;
                background-color: white !important;
                display: flex !important; flex-direction: column !important;
            }}
            div[data-testid="stSidebarUserContent"] {{
                padding: 0 !important; overflow-y: auto !important; flex-grow: 1 !important;
            }}
            div[data-testid="collapsedControl"] {{ display: none; }}
            
            /* 4. CHAT ELEMENTS */
            .chat-header {{
                background-color: #0b57d0; color: white;
                padding: 16px 20px; font-size: 16px; font-weight: 500;
                position: sticky; top: 0; z-index: 100;
            }}
            .legal-text {{
                font-size: 11px; color: #5f6368; text-align: center;
                margin: 20px 15px; line-height: 1.5;
            }}
            .legal-text a {{ color: #0b57d0; text-decoration: none; }}
            
            .bot-bubble {{
                background: #f1f3f4; color: #202124; align-self: flex-start;
                padding: 12px 16px; border-radius: 18px 18px 18px 4px;
                font-size: 14px; line-height: 1.5; margin-bottom: 10px;
                margin-left: 20px; margin-right: 40px;
            }}
            .user-bubble {{
                background: #e8f0fe; color: #0b57d0; align-self: flex-end;
                padding: 12px 16px; border-radius: 18px 18px 4px 18px;
                font-size: 14px; text-align: right; margin-bottom: 10px;
                margin-left: 40px; margin-right: 20px;
            }}
            
            /* 5. TRIGGER BUTTON POSITIONING */
            div:has(#fix-chat-button) + div button {{
                position: fixed !important;
                bottom: 30px !important; right: 30px !important;
                width: 60px !important; height: 60px !important;
                border-radius: 50% !important;
                background-color: #0b57d0 !important; color: white !important;
                border: none !important; box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
                z-index: 100000 !important;
                font-size: 24px !important;
                display: flex !important; align-items: center !important; justify-content: center !important;
            }}
            div:has(#fix-chat-button) + div button:hover {{ transform: scale(1.05); }}
            
            /* 6. OPTION CHIPS */
            div.stButton button {{
                width: 100%; text-align: left; justify-content: flex-start;
                background: white !important; border: 1px solid #dadce0 !important;
                color: #0b57d0 !important; border-radius: 20px !important;
                padding: 8px 16px !important; font-size: 14px !important;
                font-weight: 500 !important; margin-bottom: 5px !important;
            }}
            div.stButton button:hover {{ background: #f0f4fc !important; border-color: #d2e3fc !important; }}
            
            /* 7. FOOTER INPUT */
            .fake-input {{
                border-top: 1px solid #f1f3f4; padding: 15px;
                background: white; margin-top: 10px; position: sticky; bottom: 0;
            }}
            .input-box {{
                width: 100%; padding: 12px 15px; background: #f8f9fa;
                border-radius: 24px; border: 1px solid #dadce0;
                color: #bdc1c6; font-size: 14px;
            }}
            
            /* Landing Page Styles */
            .persona-header {{ font-size: 24px; font-weight: 600; color: #202124; margin-bottom: 10px; }}
            .persona-sub {{ font-size: 16px; color: #5f6368; margin-bottom: 20px; }}
            
            /* ENDED SCREEN CARD */
            .ended-card {{
                background: white; padding: 40px; border-radius: 16px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.1); text-align: center;
                max-width: 400px; margin: 100px auto;
            }}
        </style>
    """, unsafe_allow_html=True)

# --- 5. RENDERERS ---

def render_prescreen():
    """Detailed Persona Card."""
    st.markdown("""<style>[data-testid="stAppViewContainer"] { background-color: #f0f2f5; background-image: none !important; }</style>""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('<div class="persona-header">👤 Demo Persona: Sarah</div>', unsafe_allow_html=True)
            st.markdown('<div class="persona-sub">Founder & Creative Director at "Sarah Designs"</div>', unsafe_allow_html=True)
            st.divider()
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**🏢 Business Profile**")
                st.caption("Boutique Branding Agency (3 employees). She deals with high-ticket clients ($10k+ projects).")
                st.markdown("**🧠 Motivations**")
                st.caption("Obsessed with looking professional. Hates administrative friction. Needs to close deals fast.")
            with col_b:
                st.markdown("**🛠 Tech Stack**")
                st.caption("Gmail, Drive, Docs (Business Starter).")
                st.markdown("**🔥 The Pain Point**")
                st.caption("Currently pays **$10/month** for DocuSign Personal. It's annoying to download PDFs, upload them, and manage two logins.")
            st.divider()
            st.info("**🎯 The Upgrade Goal:** Upsell to **Business Standard** ($12/mo) via eSignature integration.")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 Enter Workspace Demo", type="primary", use_container_width=True):
                st.session_state.view = "DEMO"
                st.rerun()

def render_ended():
    """Exit Screen."""
    inject_css() # Keep background
    st.markdown("""
        <div class="ended-card">
            <div style="font-size: 48px; margin-bottom: 20px;">👋</div>
            <h2 style="color: #202124; margin-bottom: 10px;">Thanks for chatting!</h2>
            <p style="color: #5f6368; margin-bottom: 30px;">We hope this helped you explore how Google Workspace can streamline your business.</p>
        </div>
    """, unsafe_allow_html=True)

    # Button to go back to Landing Page
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        if st.button("Return to Start", type="primary", use_container_width=True):
            st.session_state.view = "PRESCREEN"
            st.session_state.chat_open = False
            st.session_state.current_step = 0
            st.session_state.history = []
            # Reload first message
            first_msg = script.get_state(0)
            st.session_state.history = [{"role": "bot", "text": first_msg['text']}]
            st.rerun()

def render_demo():
    inject_css()

    # A. CLOSED STATE
    if not st.session_state.chat_open:
        st.markdown("""
            <div style="position: fixed; bottom: 35px; right: 100px; background: white; padding: 14px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); max-width: 220px; font-family: sans-serif; font-size: 14px; color: #3c4043; z-index: 999;">
                I’m powered by Google AI. Together, we can use Workspace Premium features to help your business grow. Interested to chat?
            </div>
        """, unsafe_allow_html=True)
        st.markdown('<div id="fix-chat-button"></div>', unsafe_allow_html=True)
        if st.button("💬", key="open_chat"):
            st.session_state.chat_open = True
            st.rerun()

    # B. OPEN STATE (Sidebar)
    if st.session_state.chat_open:
        with st.sidebar:
            st.markdown("""<div class="chat-header"><span>Google Workspace Guide</span></div>""", unsafe_allow_html=True)

            with st.container():
                st.markdown("""
                    <div class="legal-text">
                        This product uses AI and may display inaccurate info. Your chat activity may be used to improve the product and your use is subject to Google’s <a href="#">Terms</a>, <a href="#">AI Use Policy</a>, and <a href="#">Privacy Policy</a>. <a href="#">Learn more</a>.
                    </div>
                """, unsafe_allow_html=True)

                for msg in st.session_state.history:
                    css_class = "user-bubble" if msg['role'] == "user" else "bot-bubble"
                    st.markdown(f"<div class='{css_class}'>{msg['text']}</div>", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

            step_data = script.get_state(st.session_state.current_step)
            if step_data and step_data['options']:
                for opt in step_data['options']:
                    if st.button(opt['label'], key=f"btn_{st.session_state.current_step}_{opt['label']}"):
                        st.session_state.history.append({"role": "user", "text": opt['label']})
                        next_step_id = opt['next']
                        next_state = script.get_state(next_step_id)
                        if next_state:
                            st.session_state.history.append({"role": "bot", "text": next_state['text']})
                        st.session_state.current_step = next_step_id
                        st.rerun()

            st.markdown("""<div class="fake-input"><div class="input-box">Add details or ask a question...</div></div>""", unsafe_allow_html=True)

            # EXIT FLOW: Triggers "ENDED" view
            if st.button("Close Chat", type="secondary"):
                st.session_state.view = "ENDED"
                st.rerun()

# --- 6. ROUTER ---
if st.session_state.view == "PRESCREEN":
    render_prescreen()
elif st.session_state.view == "ENDED":
    render_ended()
else:
    render_demo()