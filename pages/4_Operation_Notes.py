import streamlit as st
import pandas as pd
import io
import re
from pdf2image import convert_from_bytes
import pytesseract
import cv2
import numpy as np

st.title("4 - Operation Notes (Same Depth & After 15)")

# Session state for data
if 'op_notes_data' not in st.session_state:
    st.session_state.op_notes_data = pd.DataFrame(columns=["Depth1", "Depth2", "Quote", "Notes"])
if 'well_name' not in st.session_state:
    st.session_state.well_name = "Unknown Well"

# Data Entry Options
st.subheader("Data Entry Options")
tab1, tab2 = st.tabs(["1. Upload Mud Log PDF", "2. Upload Excel Sheet"])

with tab1:
    pdf_file = st.file_uploader("Upload Mud Log PDF", type="pdf")
    if pdf_file:
        try:
            images = convert_from_bytes(pdf_file.read())
            extracted = []
            well_name = None

            for page in images:
                img_cv = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
                text = pytesseract.image_to_string(img_cv)
                lines = [line.strip() for line in text.splitlines() if line.strip()]

                if not well_name:
                    match = re.search(r'Well:\s*(\S+)', text)
                    if match:
                        well_name = match.group(1)
                        st.session_state.well_name = well_name

                in_section = False
                current_depth = None
                note_lines = []

                for line in lines:
                    if "LITHOLOGY DESCRIPTIONS AND REMARKS" in line.upper():
                        in_section = True
                        continue
                    if in_section:
                        depth_match = re.match(r'^(\d{3,5})\s', line)
                        if depth_match:
                            if current_depth is not None and note_lines:
                                extracted.append({
                                    "Depth1": current_depth,
                                    "Depth2": current_depth + 15,
                                    "Quote": '"',
                                    "Notes": ' '.join(note_lines)
                                })
                            current_depth = int(depth_match.group(1))
                            note_lines = []
                            line = line[depth_match.end():].strip()

                        # Skip lithology
                        if re.match(r'^(LST|SH|SST|SD|CLY|GY|MARL|ANH|SLT|DL|LS|MD|PK|WD|GLC|HAL|PYR|QZ|FLD|BAS|GRN|VOL|IGN|MET|UNK)\b', line.upper()):
                            continue

                        if line:
                            note_lines.append(line)

                if current_depth is not None and note_lines:
                    extracted.append({
                        "Depth1": current_depth,
                        "Depth2": current_depth + 15,
                        "Quote": '"',
                        "Notes": ' '.join(note_lines)
                    })

            if extracted:
                new_df = pd.DataFrame(extracted)
                st.session_state.op_notes_data = pd.concat([st.session_state.op_notes_data, new_df]).drop_duplicates().reset_index(drop=True)
                st.success(f"Extracted {len(extracted)} notes from PDF")
            else:
                st.warning("No operation notes extracted")

        except Exception as e:
            st.error(f"PDF processing error: {e}")

with tab2:
    excel_file = st.file_uploader("Upload Excel Sheet", type=["xlsx", "xls"])
    if excel_file:
        try:
            df = pd.read_excel(excel_file, sheet_name=None)
            sheets = list(df.keys())
            selected_sheet = st.selectbox("Select Sheet", sheets)

            sheet_df = df[selected_sheet]
            # Assume columns: Depth Start or Depth1, Depth End or Depth2, Comment or Notes
            columns = sheet_df.columns.tolist()
            depth1_col = st.selectbox("Depth1 Column", columns, index=columns.index("Depth Start") if "Depth Start" in columns else 0)
            depth2_col = st.selectbox("Depth2 Column", columns, index=columns.index("Depth End") if "Depth End" in columns else 1)
            notes_col = st.selectbox("Notes Column", columns, index=columns.index("Comment") if "Comment" in columns else 2)

            data_df = sheet_df[[depth1_col, depth2_col, notes_col]].rename(columns={
                depth1_col: "Depth1",
                depth2_col: "Depth2",
                notes_col: "Notes"
            })
            data_df["Quote"] = '"'
            st.session_state.op_notes_data = pd.concat([st.session_state.op_notes_data, data_df[["Depth1", "Depth2", "Quote", "Notes"]]]).reset_index(drop=True)

            # Well name from Excel
            well_match = re.search(r'Well:\s*(\S+)', sheet_df.to_string())
            if well_match:
                st.session_state.well_name = well_match.group(1)

            st.success(f"Loaded {len(data_df)} notes from Excel")

        except Exception as e:
            st.error(f"Excel processing error: {e}")

# Current Entries - Editable Table
st.subheader("Current Entries (QC & Edit)")
st.write(f"Fixed Well Name: {st.session_state.well_name}")

if st.session_state.op_notes_data.empty:
    st.info("No data. Upload to start.")
else:
    edited_df = st.data_editor(
        st.session_state.op_notes_data,
        num_rows="dynamic",
        column_config={
            "Depth1": st.column_config.NumberColumn("Depth1", min_value=0, step=1),
            "Depth2": st.column_config.NumberColumn("Depth2", min_value=0, step=1),
            "Quote": st.column_config.TextColumn("Quote", default='"', width="small"),
            "Notes": st.column_config.TextColumn("Notes", width="large")
        },
        use_container_width=True,
        hide_index=False
    )

    # Auto-update Depth2 if Depth1 changed
    edited_df["Depth2"] = edited_df["Depth1"] + 15
    edited_df["Quote"] = '"'
    st.session_state.op_notes_data = edited_df.reset_index(drop=True)

# Preview & Download PRN
st.subheader("Formatted PRN Preview & Download")

if not st.session_state.op_notes_data.empty:
    prn_content = io.StringIO()
    prn_content.write(f"Well:          {st.session_state.well_name}\n\n")

    for _, row in st.session_state.op_notes_data.iterrows():
        depth1 = int(row["Depth1"])
        depth2 = int(row["Depth2"])
        quote = row["Quote"]
        notes = row["Notes"]
        prn_content.write(f"{depth1:>8} {depth2:>8} {quote:>1} {notes}\n")

    # Preview
    st.code(prn_content.getvalue(), language="text")

    # Download
    st.download_button(
        label="Download PRN File",
        data=prn_content.getvalue(),
        file_name=f"Operation notes ({st.session_state.well_name}).prn",
        mime="text/plain"
    )
else:
    st.info("No data to preview/export.")
