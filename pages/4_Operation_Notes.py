import streamlit as st
import pandas as pd
import io
import re
import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_bytes

st.title("4 - Operation Notes (Same Depth & After 15)")

# Data storage
if 'op_notes_data' not in st.session_state:
    st.session_state.op_notes_data = pd.DataFrame(columns=["Depth1", "Depth2", "Notes"])
if 'well_name' not in st.session_state:
    st.session_state.well_name = "Well Name"

# Entry options
st.subheader("Data Entry Options")

tab1, tab2 = st.tabs(["1. Upload Mud Log PDF", "2. Upload Excel Sheet"])

with tab1:
    pdf_file = st.file_uploader("Upload Mud Log PDF", type=["pdf"])
    if pdf_file:
        try:
            images = convert_from_bytes(pdf_file.read())
            extracted = []
            well_name = None

            for page_img in images:
                # OCR with data for position
                data = pytesseract.image_to_data(page_img, output_type=pytesseract.Output.DICT)

                depths = []
                notes = []
                prev_y = 0
                current_note = ""
                current_depth = None

                for i in range(len(data['level'])):
                    text = data['text'][i].strip()
                    if not text:
                        continue

                    # Well name detection
                    if not well_name and "Well" in text:
                        well_name = data['text'][i+1] if i+1 < len(data['text']) else text.split("Well")[-1].strip()

                    # Depth column (assume left side, numbers)
                    if re.match(r'^\d{3,5}$', text):
                        current_depth = int(text)
                        prev_y = data['top'][i]

                    # Notes column (right side, non-lith)
                    else:
                        y = data['top'][i]
                        if abs(y - prev_y) < 20:  # same row
                            if not re.match(r'^(LST|SH|SST|SD|CLY|GY|MARL|ANH|SLT|DL|LS|MD|PK|WD|GLC|HAL|PYR|QZ|FLD|BAS|GRN|VOL|IGN|MET|UNK)\b', text.upper(), re.I):
                                current_note += " " + text

                    # End of row/note
                    if current_note and (i == len(data['level']) - 1 or abs(data['top'][i+1] - y) > 20):
                        if current_depth is not None:
                            extracted.append({
                                "Depth1": current_depth,
                                "Depth2": current_depth + 15,
                                "Notes": current_note.strip()
                            })
                        current_note = ""
                        current_depth = None

            if extracted:
                df = pd.DataFrame(extracted)
                st.session_state.op_notes_data = pd.concat([st.session_state.op_notes_data, df]).drop_duplicates().reset_index(drop=True)
                if well_name:
                    st.session_state.well_name = well_name
                st.success(f"Extracted {len(extracted)} notes with depths")
            else:
                st.warning("No operation notes detected. Enter manually.")

        except Exception as e:
            st.error(f"PDF processing error: {e}")

with tab2:
    excel_file = st.file_uploader("Upload Excel Sheet", type=["xlsx", "xls"])
    if excel_file:
        try:
            df = pd.read_excel(excel_file, sheet_name=None)
            # Assume first sheet or 'Sheet1'
            sheet = df[list(df.keys())[0]]
            # Columns: Depth Start, Depth End, Comment
            data_df = sheet.rename(columns={
                sheet.columns[0]: "Depth1",
                sheet.columns[1]: "Depth2",
                sheet.columns[2]: "Notes"
            })[["Depth1", "Depth2", "Notes"]]

            # Well name from cell or header
            well_name = sheet.iloc[0, 2] if "Well" in str(sheet.iloc[0, 0]) else "Well Name"
            st.session_state.well_name = well_name

            st.session_state.op_notes_data = pd.concat([st.session_state.op_notes_data, data_df]).drop_duplicates().reset_index(drop=True)
            st.success("Loaded notes from Excel")

        except Exception as e:
            st.error(f"Excel processing error: {e}")

# Current entries: editable table
st.subheader("Current Entries (Edit / QC)")

if st.session_state.op_notes_data.empty:
    st.info("No notes yet. Upload or add manually.")
else:
    edited_df = st.data_editor(
        st.session_state.op_notes_data,
        num_rows="dynamic",
        column_config={
            "Depth1": st.column_config.NumberColumn("Depth (ft)", min_value=0, step=1),
            "Depth2": st.column_config.NumberColumn("Depth2 (auto +15)", min_value=0, step=1),
            "Notes": st.column_config.TextColumn("Operation Notes")
        },
        use_container_width=True
    )

    # Auto update Depth2
    edited_df["Depth2"] = edited_df["Depth1"] + 15
    st.session_state.op_notes_data = edited_df.reset_index(drop=True)

# Preview and download section
st.subheader("Formatted Text Preview & Download")

if not st.session_state.op_notes_data.empty:
    output = io.StringIO()
    output.write(f"Well:          {st.session_state.well_name}\n\n")

    for _, row in st.session_state.op_notes_data.iterrows():
        output.write(f"{int(row['Depth1']):<8} {int(row['Depth2']):<8} \"{row['Notes']}\"\n")

    # Preview
    st.code(output.getvalue(), language="text")

    # Download
    st.download_button(
        label="Download Operation Notes PRN",
        data=output.getvalue(),
        file_name=f"Operation Notes ({st.session_state.well_name}).prn",
        mime="text/plain"
    )
else:
    st.info("No data to preview/download.")
