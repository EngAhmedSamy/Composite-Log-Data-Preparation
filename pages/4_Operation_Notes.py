import streamlit as st
import pandas as pd
import io
import re
import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_bytes


st.sidebar.markdown("---")
st.sidebar.header("Global Settings")

well_name_input = st.sidebar.text_input(
    "Well Name",
    value=st.session_state.get('well_name', 'ABRAR-84'),
    key="well_name_input"
)

if st.sidebar.button("Apply Well Name", type="primary"):
    if well_name_input.strip():
        st.session_state.well_name = well_name_input.strip()
        # Place success message here - it will show until next rerun or page change
        st.sidebar.success(f"Well Name: **{st.session_state.well_name}** applied ✅")
       # st.rerun()  # optional - removes it faster but refreshes the app
    else:
        st.sidebar.error("Please enter a well name")
# Now every tab can use st.session_state.well_name


# ─── Sidebar Copyright / Watermark Footer (visible on ALL pages) ──────────
#st.sidebar.markdown("---")  # separator line above the copyright
st.sidebar.markdown("---")
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
st.markdown("### Tab 4: Operation Notes (Same Depth & After 15)")




#st.title("4 - Operation Notes (Same Depth & After 15)")

# Well name from session state (global setting)
well_name = st.session_state.get('well_name', 'Unknown Well')
st.info(f"Using well name: **{well_name}**")

# Session state for storing multiple notes
if 'op_notes' not in st.session_state:
    st.session_state.op_notes = []  # list of (depth, note)

# Form to add a new note
with st.form("add_operation_note"):
    col1, col2 = st.columns([1, 3])
    with col1:
        depth = st.number_input("Depth", min_value=0, step=1, value=0, key="op_depth")
    with col2:
        note = st.text_area("Operation Note", height=120, key="op_note")
    
    submitted = st.form_submit_button("Add Note")
    if submitted and depth >= 0 and note.strip():
        st.session_state.op_notes.append((depth, note.strip()))
        st.success(f"Added note at depth {depth}")
        st.rerun()

# Display and manage added notes
st.subheader("Added Notes")
if st.session_state.op_notes:
    # Sort by depth for consistent order
    sorted_notes = sorted(st.session_state.op_notes, key=lambda x: x[0])
    
    for i, (d, n) in enumerate(sorted_notes):
        col1, col2, col3 = st.columns([1, 4, 1])
        col1.metric("Depth", d)
        col2.text(n[:150] + "..." if len(n) > 150 else n)
        if col3.button("Remove", key=f"remove_op_{i}"):
            del st.session_state.op_notes[i]
            st.rerun()
else:
    st.info("No notes added yet. Use the form above.")

# ─── Generate PRN automatically if there are notes ────────────────────────
if st.session_state.op_notes:
    # Sort by depth
    sorted_notes = sorted(st.session_state.op_notes, key=lambda x: x[0])
    
    lines = [f"Well: {well_name}"]
    
    for d, note in sorted_notes:
        d2 = d + 10
        # Clean note: replace line breaks with space
        cleaned_note = note.replace('\n', ' ').replace('\r', ' ').strip()
        line = f"{d:<15}{d2:<15}\"{cleaned_note}\""
        lines.append(line)
    
    prn_content = "\n".join(lines) + "\n"
    
    # ─── Preview ────────────────────────────────────────────────────────────
    st.subheader("Operation Notes PRN Preview (scroll to see full content - copy-paste ready)")
    st.caption("Scroll down to see the full content. Use Ctrl+F to search within the preview.")
    
    with st.container():
        st.markdown(
            f"""
            <div style="
                height: 400px;
                overflow-y: auto;
                overflow-x: auto;
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Courier New', Courier, monospace;
                font-size: 14px;
                padding: 16px;
                border-radius: 6px;
                border: 1px solid #444;
                white-space: pre;
                line-height: 1.4;
            ">
            {prn_content.replace("\n", "<br>").replace(" ", "&nbsp;")}
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # ─── Download ──────────────────────────────────────────────────────────
    st.download_button(
        label="Download Operation Notes .prn",
        data=prn_content,
        file_name=f"{well_name} Operation Notes.prn",
        mime="text/plain",
        key="operation_notes_download"
    )
    
    # Clear all button
    if st.button("Clear All Notes"):
        st.session_state.op_notes = []
        st.rerun()
else:
    st.info("Add notes above to generate the PRN.")
