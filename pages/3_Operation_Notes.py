import streamlit as st
import pandas as pd
import io
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes
import cv2
import numpy as np
import re

st.title("4 - Operation Notes (Same Depth & After 15)")

# ────────────────────────────────────────────────
#   Data storage
# ────────────────────────────────────────────────
if 'op_notes_data' not in st.session_state:
    st.session_state.op_notes_data = pd.DataFrame(columns=["Depth1", "Depth2", "Notes"])
if 'well_name' not in st.session_state:
    st.session_state.well_name = "Well Name"

# ────────────────────────────────────────────────
#   Entry options
# ────────────────────────────────────────────────
st.subheader("Data Entry Options")

tab1, tab2 = st.tabs(["1. Upload Mud Log PDF", "2. Upload Excel Sheet"])

with tab1:
    pdf_file = st.file_uploader("Upload Mud Log PDF", type=["pdf"])
    if pdf_file:
        try:
            # Convert PDF to images
            images = convert_from_bytes(pdf_file.read())

            extracted = []
            well_name = None

            for page in images:
                # OCR the page
                text = pytesseract.image_to_string(page)

                # Find well name (assume from first page, e.g., line containing "Well:")
                if not well_name:
                    match = re.search(r'Well:\s*(\S+)', text)
                    if match:
                        well_name = match.group(1)

                # Find LITHOLOGY DESCRIPTIONS AND REMARKS section
                lines = text.splitlines()
                in_section = False
                for line in lines:
                    if "LITHOLOGY DESCRIPTIONS AND REMARKS" in line.upper():
                        in_section = True
                    elif in_section:
                        # Skip black lithology (starts with LST, SH, etc.)
                        if re.match(r'^(LST|SH|SST|SD|CLY|GY|MARL|ANH|SLT|DL|LS|MD|PK|WD|GLC|HAL|PYR|QZ|FLD|BAS|GRN|VOL|IGN|MET|UNK)\b', line.upper(), re.I):
                            continue
                        # Extract other lines (assumed colored or boxed)
                        # Simple heuristic: lines not starting with lith codes
                        # For better color detection, use CV
                        if line.strip():
                            # Assume depth + note format, e.g., "Sh. Dk gy, gy. It gy v blk y-sb."
                            extracted.append({"Notes": line.strip()})

            # Basic depth assignment (you may need to improve parsing)
            # Assume depths from context or add manually
            if extracted:
                df = pd.DataFrame(extracted)
                df["Depth1"] = range(0, len(df) * 10, 10)  # Placeholder depths
                df["Depth2"] = df["Depth1"] + 10
                st.session_state.op_notes_data = pd.concat([st.session_state.op_notes_data, df[["Depth1", "Depth2", "Notes"]]])
                if well_name:
                    st.session_state.well_name = well_name
                st.success("Extracted notes from PDF")
            else:
                st.warning("No operation notes found in PDF")

        except Exception as e:
            st.error(f"Error processing PDF: {e}")

with tab2:
    excel_file = st.file_uploader("Upload Excel Sheet", type=["xlsx", "xls"])
    if excel_file:
        try:
            df = pd.read_excel(excel_file)
            # Assume columns: Depth1, Depth2, Notes, and Well Name in cell or header
            if 'Well' in df.columns or df.iloc[0].str.contains('Well').any():
                well_name = df[df.iloc[:,0].str.contains('Well', na=False)].iloc[0,1] if not df.empty else "Well Name"
                st.session_state.well_name = well_name
            # Filter to data rows
            data_df = df[["Depth1", "Depth2", "Notes"]]  # Adjust column names if different
            st.session_state.op_notes_data = pd.concat([st.session_state.op_notes_data, data_df])
            st.success("Loaded data from Excel")
        except Exception as e:
            st.error(f"Error processing Excel: {e}")

# ────────────────────────────────────────────────
#   Current entries (editable table)
# ────────────────────────────────────────────────
st.subheader("Current Operation Notes Entries")
st.write(f"Fixed Well Name: {st.session_state.well_name}")

if st.session_state.op_notes_data.empty:
    st.info("No notes yet. Upload or add manually.")
else:
    edited_df = st.data_editor(
        st.session_state.op_notes_data,
        num_rows="dynamic",
        column_config={
            "Depth1": st.column_config.NumberColumn("Depth1", min_value=0, step=1),
            "Depth2": st.column_config.NumberColumn("Depth2", min_value=0, step=1),
            "Notes": st.column_config.TextColumn("Notes")
        },
        use_container_width=True
    )

    # Auto-set Depth2 = Depth1 + 10
    edited_df["Depth2"] = edited_df["Depth1"] + 10
    st.session_state.op_notes_data = edited_df

# ────────────────────────────────────────────────
#   Preview and download formatted text file
# ────────────────────────────────────────────────
st.subheader("Formatted Text Preview & Download")

if not st.session_state.op_notes_data.empty:
    # Generate space-delimited text
    output = io.StringIO()
    output.write(f"Well: {st.session_state.well_name}\n\n")
    output.write("Depth1 Depth2 Notes\n")
    for _, row in st.session_state.op_notes_data.iterrows():
        output.write(f"{row['Depth1']:<6} {row['Depth2']:<6} {row['Notes']}\n")

    # Preview
    st.code(output.getvalue(), language="text")

    # Download
    st.download_button(
        label="Download Operation Notes TXT",
        data=output.getvalue(),
        file_name=f"Operation Notes ({st.session_state.well_name}).txt",
        mime="text/plain"
    )
else:
    st.info("No data to export.")
