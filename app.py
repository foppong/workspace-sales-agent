"""
File: app.py
Description: Workspace Upsell Demo - Sidebar Chat + Exit Flow.
Implements Generative UI for dynamic chips and clean state management.
"""
import streamlit as st
import logic
import base64
import os

# --- 1. CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Contract Draft - Google Docs")

def get_base64_image(image_path):
    if not os.path.exists(image_path): return None
    with open(image_path, 'rb') as f: return base64.b64encode(f.read()).decode()

bg_base64 = get_base64_image("Contract Draft.png")

# --- 2. STATE MANAGEMENT ---
if 'view' not in st.session_state: st.session_state.view = "PRESCREEN"
if 'chat_open' not in st.session_state: st.session_state.chat_open = False
if 'history' not in st.session_state:
    first_msg = "From booking the initial client consultation to getting the final proposal signed, which part of the process creates the most administrative friction for your team?"
    st.session_state.history = [{"role": "bot", "text": first_msg}]
if 'suggestions' not in st.session_state:
    st.session_state.suggestions = [
        "Playing calendar ping-pong",
        "Managing client contracts"
    ]

# --- 3. CSS INJECTION ---
def inject_css():
    bg_rule = f'background-image: url("data:image/png;base64,{bg_base64}"); background-size: cover; background-position: top center; background-attachment: fixed;' if bg_base64 else 'background-color: #f1f3f4;'

    st.markdown(f"""
        <style>
            [data-testid="stAppViewContainer"] {{ {bg_rule} }}
            [data-testid="stHeader"], [data-testid="stToolbar"] {{ display: none; }}
            .block-container {{ padding: 0 !important; max-width: 100%; }}
            
            section[data-testid="stSidebar"] {{
                width: 380px !important; min-width: 380px !important; height: 600px !important;
                position: fixed !important; top: auto !important; bottom: 20px !important;
                left: auto !important; right: 20px !important; border-radius: 16px !important;
                box-shadow: 0 12px 48px rgba(0,0,0,0.25) !important; border: 1px solid #e0e0e0 !important;
                z-index: 99999 !important; background-color: white !important;
            }}
            div[data-testid="stSidebarUserContent"] {{ padding: 0 !important; overflow-y: auto !important; }}
            div[data-testid="collapsedControl"] {{ display: none; }}
            
            .chat-header {{ background-color: #0b57d0; color: white; padding: 16px 20px; font-weight: 500; position: sticky; top: 0; z-index: 100; }}
            .legal-text {{ font-size: 11px; color: #5f6368; text-align: center; margin: 20px 15px; }}
            .bot-bubble {{ background: #f1f3f4; padding: 12px 16px; border-radius: 18px 18px 18px 4px; font-size: 14px; margin: 0 40px 10px 20px; }}
            .user-bubble {{ background: #e8f0fe; color: #0b57d0; padding: 12px 16px; border-radius: 18px 18px 4px 18px; font-size: 14px; text-align: right; margin: 0 20px 10px 40px; }}
            
            div:has(#fix-chat-button) + div button {{
                position: fixed !important; bottom: 35px !important; right: 30px !important;
                background-color: #0b57d0 !important; color: white !important;
                border-radius: 24px !important; padding: 12px 24px !important;
                font-size: 16px !important; font-weight: 600 !important;
                z-index: 100000 !important; width: auto !important; height: auto !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.25) !important; border: none !important;
            }}
            div:has(#fix-chat-button) + div button p {{ font-weight: 600 !important; font-size: 16px !important; }}
            
            div.stButton button {{
                width: 100%; text-align: left; background: white !important; border: 1px solid #dadce0 !important;
                color: #0b57d0 !important; border-radius: 20px !important; padding: 8px 16px !important; margin-bottom: 5px !important;
            }}
            .ended-card {{ background: white; padding: 40px; border-radius: 16px; text-align: center; max-width: 400px; margin: 100px auto; }}
        </style>
    """, unsafe_allow_html=True)

# --- 4. RENDERERS ---
def render_prescreen():
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
            st.divider()
            st.info("**🎯 The Upgrade Goal:** Upsell to **Business Standard** ($12/mo) by diagnosing and solving her biggest operational friction.")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 Enter Workspace Demo", type="primary", use_container_width=True):
                st.session_state.view = "DEMO"
                st.rerun()

def render_ended():
    inject_css()
    st.markdown("""<div class="ended-card"><h2>👋 Thanks for chatting!</h2></div>""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        if st.button("Return to Start", type="primary", use_container_width=True):
            st.session_state.clear()
            st.rerun()

def process_user_input(user_text):
    st.session_state.history.append({"role": "user", "text": user_text})
    with st.spinner("Typing..."):
        reply_text, score, new_suggestions = logic.get_gemini_response(
            user_input=user_text,
            chat_history=st.session_state.history[:-1]
        )
    st.session_state.history.append({"role": "bot", "text": reply_text})
    st.session_state.suggestions = new_suggestions
    st.rerun()


def render_demo():
    inject_css()

    if not st.session_state.chat_open:
        st.markdown("""
            <div style="position: fixed; bottom: 100px; right: 30px; background: white; padding: 16px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); max-width: 250px; font-family: sans-serif; font-size: 14px; color: #3c4043; z-index: 999;">
                Hi Sarah! 👋 I'm powered by Google AI. As the owner of Sarah Designs, I know you wear a lot of hats. Together, we can streamline your workflow and save you time. Interested in exploring how?
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<div id="fix-chat-button"></div>', unsafe_allow_html=True)
        if st.button("💬 Let's chat", key="open_chat"):
            st.session_state.chat_open = True
            st.rerun()

    if st.session_state.chat_open:
        with st.sidebar:
            st.markdown("""<div class="chat-header"><span>Google Workspace Guide</span></div>""",
                        unsafe_allow_html=True)
            st.markdown("""<div class="legal-text">This product uses AI.</div>""", unsafe_allow_html=True)

            for msg in st.session_state.history:
                css_class = "user-bubble" if msg['role'] == "user" else "bot-bubble"
                st.markdown(f"<div class='{css_class}'>{msg['text']}</div>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            if st.session_state.suggestions:
                unique_chips = list(dict.fromkeys(st.session_state.suggestions))
                for i, opt in enumerate(unique_chips):
                    if st.button(opt, key=f"dynamic_chip_{i}_{opt}"):
                        # Restored the End Chat routing functionality
                        if opt.lower() == "end chat":
                            st.session_state.view = "ENDED"
                            st.rerun()
                        else:
                            process_user_input(opt)

            user_text = st.chat_input("Add details or ask a question...")
            if user_text:
                process_user_input(user_text)

            st.markdown("<br><hr>", unsafe_allow_html=True)
            if st.button("Close Chat", type="secondary"):
                st.session_state.view = "ENDED"
                st.rerun()

if st.session_state.view == "PRESCREEN":
    render_prescreen()
elif st.session_state.view == "ENDED":
    render_ended()
else:
    render_demo()