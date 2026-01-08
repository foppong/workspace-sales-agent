"""
File: ui.py
Description: Handles Streamlit UI rendering.
"""
import streamlit as st

def apply_custom_css():
    st.markdown("""
        <style>
            [data-testid="stAppViewContainer"] { background-color: white !important; color: #202124 !important; }
            [data-testid="stSidebar"] { background-color: #f6f8fc !important; border-right: 1px solid #e1e4e8; }
            .block-container { padding: 0 !important; max-width: 100%; }
            header { visibility: hidden; }
            
            /* UI Elements */
            .top-bar { display: flex; align-items: center; background-color: #f6f8fc; padding: 8px 20px; border-bottom: 1px solid #e1e4e8; }
            .search-bar { background-color: #eaf1fb; border: none; border-radius: 8px; padding: 12px 20px; width: 100%; max-width: 720px; outline: none; margin-left: 60px; }
            .compose-btn { background-color: #c2e7ff; color: #001d35; border-radius: 16px; padding: 15px 25px; border: none; font-weight: 600; cursor: pointer; margin: 15px 0px 20px 10px; width: 150px; text-align: left; display: flex; gap: 10px;}
            .nav-item { padding: 8px 10px 8px 25px; margin-right: 10px; border-radius: 0 16px 16px 0; cursor: pointer; font-weight: 500; color: #202124; }
            .nav-item.active { background-color: #d3e3fd; color: #001d35; font-weight: 700; }
            
            /* Chat Elements */
            .chat-message { padding: 10px; border-radius: 10px; margin-bottom: 10px; font-size: 14px; }
            .user-msg { background-color: #e3f2fd; text-align: right; margin-left: 20%; }
            .bot-msg { background-color: #f1f3f4; margin-right: 20%; }
            .score-badge { font-size: 11px; font-weight: bold; margin-bottom: 5px; }
            
            /* TINY Suggestion Chips */
            div[data-testid="stHorizontalBlock"] button {
                font-size: 11px !important;
                padding: 2px 8px !important;
                min-height: 0px !important;
                height: auto !important;
                line-height: 1.4 !important;
                border-radius: 12px !important;
                border: 1px solid #dadce0 !important;
                color: #0b57d0 !important;
            }
            div[data-testid="stHorizontalBlock"] button:hover {
                background-color: #e8f0fe !important;
                border-color: #e8f0fe !important;
            }
            
            /* Icon Strip Styling */
            .icon-btn-container button {
                font-size: 20px !important;
                background-color: transparent !important;
                border: none !important;
                color: #5f6368 !important;
                margin-bottom: 20px !important;
                display: block !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }
            .icon-btn-container button:hover {
                background-color: #e1e3e1 !important;
                border-radius: 50%;
                color: #202124 !important;
            }
        </style>
    """, unsafe_allow_html=True)

def render_top_bar(profile):
    st.markdown(f"""
        <div class="top-bar">
            <div style='font-size: 20px; color: #5f6368; margin-right: 20px;'>&#9776;</div>
            <img src="https://ssl.gstatic.com/ui/v1/icons/mail/rfr/logo_gmail_lockup_default_1x_r5.png" style="height: 24px; margin-right: 20px;">
            <input class="search-bar" type="text" placeholder="Search mail">
            <div style="flex-grow: 1;"></div>
            <div style="text-align: right; margin-right: 15px; color: #444; font-size: 13px;">
                <b>{profile['industry']}</b><br>{profile['size']} • {profile['current_sku']}
            </div>
            <div style="background-color: #0b57d0; color: white; border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;">
                {profile['industry'][0]}
            </div>
        </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    st.markdown('<button class="compose-btn">✏️ Compose</button>', unsafe_allow_html=True)
    st.markdown("""
        <div class="nav-item active">📥 Inbox</div>
        <div class="nav-item">⭐️ Starred</div>
        <div class="nav-item">⏰ Snoozed</div>
        <div class="nav-item">📤 Sent</div>
    """, unsafe_allow_html=True)

def render_inbox_empty(profile_name):
    st.markdown("""
        <div style="display: flex; gap: 0px; border-bottom: 1px solid #e1e4e8; margin-top: 10px;">
            <div style="border-bottom: 3px solid #0b57d0; padding: 10px 20px; width: 150px; text-align: center; color: #0b57d0; font-weight: 600;">📥 Primary</div>
            <div style="padding: 10px 20px; width: 150px; text-align: center; color: #5f6368;">🏷️ Promotions</div>
        </div>
        <br><br><br>
        <center>
            <img src='https://www.gstatic.com/images/branding/product/1x/gmail_2020q4_48dp.png' width='60'>
            <h3 style='color: #444;'>Welcome, {0}</h3>
            <div style='color: #666;'>Your Primary tab is empty.</div>
        </center>
    """.format(profile_name), unsafe_allow_html=True)

def render_exit_page(profile, summary_data):
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        track = summary_data.get("Track", "General")

        # Color-coded Banner based on Track
        if track == "UPGRADE":
            st.success("🎉 Outcome: Upgrade Track")
        elif track == "SALES":
            st.info("📞 Outcome: Sales Handoff Track")
        elif track == "SUPPORT":
            st.warning("🛠️ Outcome: Support Track")
        elif track == "EDUCATION":
            st.warning("🎓 Outcome: Education Track")
        else:
            st.error("Outcome: No Interest")

        with st.container(border=True):
            st.markdown(f"### Recap for: {profile['industry']}")
            st.caption(f"Context: {profile['size']} | {profile['current_sku']}")
            st.divider()

            st.markdown("#### 📝 Executive Summary")
            st.write(summary_data.get("Summary", "No summary available."))

            st.divider()

            st.markdown("#### ⏭️ Recommended Next Step")
            next_step = summary_data.get("Next Step", "No action")
            st.info(f"**{next_step}**")
            
            st.divider()
            
            st.markdown("#### 🧠 Sales Tactics Used")
            tactics = summary_data.get("Tactics", "None detected.")
            st.caption(tactics)
                
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Restart Prototype"):
            st.session_state.simulation_started = False
            st.session_state.exit_page = False
            st.rerun()