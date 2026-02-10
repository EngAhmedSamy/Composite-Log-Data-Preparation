import streamlit as st

# ─── Sidebar Copyright / Watermark Footer (visible on ALL pages) ──────────
#st.sidebar.markdown("---")  # separator line above the copyright
#st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style="
        text-align: center; 
        color: #888; 
        font-size: 0.85rem; 
        padding: 12px 8px; 
        margin-top: auto;
        border-top: 1px solid #444;
    ">
        © 2026 Ahmed Samy<br>
        Composite Log Data Preparation App<br>
        Proprietary Software – All Rights Reserved<br>
        Private Property – For internal use only<br>
        Copyright protected – Do not distribute
    </div>
    """,
    unsafe_allow_html=True
)



st.set_page_config(page_title="Petrel Composite Log Prep", layout="wide", page_icon="🛢️")  # optional)
                   
st.title("Petrel Composite Log Data Preparation App")
st.markdown("### Tab 10: Help (How to use the app ?!)")

st.info("Streamlit application for preparing Petrel-ready Composite Log data.")
st.info("Detailed Manual for using the app is coming up soon!")
