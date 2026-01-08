"""
File: app.py
Description: Main entry point.
Updates: Added user-friendly instructions to the Welcome Page.
"""
import streamlit as st
import ui
import logic

# --- 1. Config & Setup ---
st.set_page_config(layout="wide", page_title="Gmail - Workspace Sales Agent")
ui.apply_custom_css()

# --- 2. Session State ---
if "profiles" not in st.session_state: st.session_state.profiles = logic.generate_random_profiles()
if "selected_profile" not in st.session_state: st.session_state.selected_profile = None
if "active_panel" not in st.session_state: st.session_state.active_panel = None
if "messages" not in st.session_state: st.session_state.messages = []
if "lead_score" not in st.session_state: st.session_state.lead_score = "0"
if "simulation_started" not in st.session_state: st.session_state.simulation_started = False
if "exit_page" not in st.session_state: st.session_state.exit_page = False
if "exit_reason" not in st.session_state: st.session_state.exit_reason = None
if "summary_data" not in st.session_state: st.session_state.summary_data = {}
if "current_suggestions" not in st.session_state: st.session_state.current_suggestions = []

# --- 3. Routing Logic ---

# SCENE 1: The Pre-Screen (Welcome Page)
if not st.session_state.simulation_started:
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 6, 1])
    with c2:
        st.title("Workspace Sales Agent Prototype")

        # --- NEW: Instructions Section ---
        with st.container(border=True):
            st.markdown("### 📋 Instructions")
            st.markdown("""
            **Welcome to the future of SMB Sales.** This prototype simulates an AI agent embedded in Gmail.
            
            1. **Select a Persona:** Choose a business below (e.g., "Corner Bakery") to pre-load specific pain points.
            2. **Enter the Workspace:** You will land in a simulated inbox. Click the **Sparkle Icon (✨)** on the far right strip.
            3. **Engage the Agent:** Chat using the **Dynamic Suggestion Chips** or type your own replies.
            4. **Watch the Brain:** Observe the **Lead Score** update in real-time. Try to get it above **70** to see the Upgrade offer.
            """)

        st.divider()
        st.markdown("#### Select a Micro-SMB Persona (<10 Seats)")

        # Profile Cards
        for i, p in enumerate(st.session_state.profiles):
            with st.container(border=True):
                col_info, col_btn = st.columns([4, 1])
                with col_info:
                    st.subheader(f"{p['industry']} ({p['size']})")
                    st.markdown(f"**Pain Point:** {p['pain_point_desc']}")
                    st.caption(f"Current SKU: {p['current_sku']}")
                with col_btn:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Start Simulation", key=f"start_{i}", type="primary", use_container_width=True):
                        st.session_state.selected_profile = p
                        # Initial Hook
                        st.session_state.messages = [{
                            "role": "assistant",
                            "content": f"Hi. I noticed {p['pain_point_title']} is flagging up. That usually kills productivity. How is that impacting your day-to-day?"
                        }]
                        # Initial contextual suggestions
                        st.session_state.current_suggestions = ["Yes, it costs us time.", "Why is this happening?", "It's manageable for now."]
                        st.session_state.lead_score = "0"
                        st.session_state.exit_page = False
                        st.session_state.simulation_started = True
                        st.rerun()

        st.divider()
        if st.button("🔄 Generate New Personas"):
            st.session_state.profiles = logic.generate_random_profiles()
            st.rerun()

# SCENE 2: The Exit Page (Summary)
elif st.session_state.exit_page:
    ui.render_exit_page(st.session_state.selected_profile, st.session_state.summary_data)

# SCENE 3: The Gmail Simulator
else:
    profile = st.session_state.selected_profile
    ui.render_top_bar(profile)

    col_layout = [2, 6, 3, 0.7] if st.session_state.active_panel else [2, 9, 0.01, 0.7]
    c_nav, c_main, c_panel, c_strip = st.columns(col_layout)

    with c_nav: ui.render_sidebar()
    with c_main: ui.render_inbox_empty(profile['industry'])

    with c_panel:
        if st.session_state.active_panel:
            with st.container(border=True):
                c_head_1, c_head_2 = st.columns([5, 1])
                with c_head_1:
                    title = "Sales Agent" if st.session_state.active_panel == "agent" else "My Tasks"
                    st.subheader(title)
                with c_head_2:
                    if st.button("✖️", key="close_panel_btn"):
                        st.session_state.active_panel = None
                        st.rerun()
                st.divider()

                if st.session_state.active_panel == "agent":
                    score = int(st.session_state.lead_score)
                    color = "red" if score < 50 else "orange" if score < 80 else "green"
                    st.markdown(f"<div class='score-badge' style='color:{color}'>LEAD SCORE: {score}/100</div>", unsafe_allow_html=True)

                    chat_box = st.container(height=350)
                    with chat_box:
                        for msg in st.session_state.messages:
                            css = "user-msg" if msg["role"] == "user" else "bot-msg"
                            icon = "👤" if msg["role"] == "user" else "🤖"
                            st.markdown(f"<div class='chat-message {css}'>{icon} {msg['content']}</div>", unsafe_allow_html=True)

                    # DYNAMIC SUGGESTIONS
                    s_cols = st.columns(len(st.session_state.current_suggestions))
                    for idx, s in enumerate(st.session_state.current_suggestions):
                        if idx < 3:
                            if s_cols[idx].button(s, key=f"sug_{len(st.session_state.messages)}_{idx}"):
                                 st.session_state.messages.append({"role": "user", "content": s})
                                 resp, new_score, new_chips = logic.get_gemini_response(s, profile, st.session_state.messages)
                                 st.session_state.messages.append({"role": "assistant", "content": resp})
                                 st.session_state.lead_score = new_score
                                 st.session_state.current_suggestions = new_chips
                                 st.rerun()

                    if prompt := st.chat_input("Reply..."):
                        st.session_state.messages.append({"role": "user", "content": prompt})
                        resp, new_score, new_chips = logic.get_gemini_response(prompt, profile, st.session_state.messages)
                        st.session_state.messages.append({"role": "assistant", "content": resp})
                        st.session_state.lead_score = new_score
                        st.session_state.current_suggestions = new_chips
                        st.rerun()

                    st.divider()
                    col_cta_1, col_cta_2 = st.columns(2)
                    with col_cta_1:
                        if st.button("📞 Sales", use_container_width=True):
                            with st.spinner("Analyzing..."):
                                st.session_state.summary_data = logic.summarize_conversation(profile, st.session_state.messages, "contact")
                                st.session_state.exit_page = True
                                st.rerun()
                    with col_cta_2:
                        if score >= 70:
                            if st.button("🚀 Upgrade", type="primary", use_container_width=True):
                                with st.spinner("Processing..."):
                                    st.session_state.summary_data = logic.summarize_conversation(profile, st.session_state.messages, "upgrade")
                                    st.session_state.exit_page = True
                                    st.rerun()

                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("End Chat", type="secondary", use_container_width=True):
                        with st.spinner("Closing..."):
                             st.session_state.summary_data = logic.summarize_conversation(profile, st.session_state.messages, "general")
                             st.session_state.exit_page = True
                             st.rerun()

                elif st.session_state.active_panel == "tasks":
                    st.image("https://www.gstatic.com/images/branding/product/1x/tasks_2020q4_48dp.png", width=60)
                    st.write("No tasks yet.")

    with c_strip:
        st.markdown("<div class='icon-btn-container'>", unsafe_allow_html=True)
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("✅", key="btn_tasks", help="Tasks"):
            st.session_state.active_panel = "tasks" if st.session_state.active_panel != "tasks" else None
            st.rerun()
        st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
        if st.button("✨", key="btn_agent", help="Sales Agent"):
            st.session_state.active_panel = "agent" if st.session_state.active_panel != "agent" else None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)