import streamlit as st
import pandas as pd
import io
import re

st.title("6 - ASCII")

# Sub-tabs for the different ASCII categories
tab_gyro, tab_fm_tops, tab_mud_log_ascii, tab_mud_drlg_params, tab_desc_comment, tab_oil_shows = st.tabs([
    "1 - Gyro",
    "2 - Fm Tops",
    "3 - Mud Log (ASCII-1, ASCII-5)",
    "4 - Mud & DRLG Parameters",
    "5 - Mud Log DESC Comment",
    "6 - Oil Shows Intensity"
])

# ────────────────────────────────────────────────
# 1. Gyro
# ────────────────────────────────────────────────
with tab_gyro:
    st.header("Gyro Data")

    excel_file = st.file_uploader("Upload Gyro / Survey Excel File", type=["xlsx", "xls"])

    if excel_file is not None:
        try:
            # Read the sheet (assume 'GMS' or first sheet)
            df = pd.read_excel(excel_file, sheet_name='GMS', header=None)  # No header to scan all cells

            # Show first 20 rows for user reference
            st.subheader("First 20 rows of the sheet (for reference)")
            st.dataframe(df.head(20), use_container_width=True)

            # Step 1: Find well name (anywhere with "Well:")
            well_name = st.session_state.get('well_name', 'Unknown Well')
            for i in range(len(df)):
                for j in range(len(df.columns)):
                    cell = str(df.iloc[i, j])
                    if 'Well' in cell:
                        match = re.search(r'Well\s*[:=-]?\s*([A-Za-z0-9_-]+)', cell, re.IGNORECASE)
                        if match:
                            well_name = match.group(1).strip()
                            break
                if well_name != 'Unknown Well':
                    break
            st.session_state.well_name = well_name
            st.success(f"**Well Name detected:** {well_name}")

            # Step 2: Find column indices by searching for "MD" + "FT" below, "INC" + "Deg" below, "AZI"
            md_col = inc_col = azi_col = None

            for i in range(len(df) - 1):  # -1 because we check i+1
                for j in range(len(df.columns)):
                    cell = str(df.iloc[i, j]).strip().upper()
                    below_cell = str(df.iloc[i+1, j]).strip().upper()

                    if "MD" in cell and "FT" in below_cell:
                        md_col = j
                    if "INC" in cell and "DEG" in below_cell:
                        inc_col = j
                    if "AZI" in cell:
                        azi_col = j

            if md_col is None:
                st.error("Could not find column with 'MD' and 'FT' below it.")
            elif inc_col is None:
                st.error("Could not find column with 'INC' and 'Deg' below it.")
            elif azi_col is None:
                st.error("Could not find column with 'AZI'.")
            else:
                # Extract data from the row AFTER the header row (i+1 for each)
                # Assume data starts right after the header+unit row
                header_row = min([i for i in range(len(df)) if df.iloc[i, md_col] == df.iloc[i, md_col]])  # rough
                data_start = header_row + 2  # skip header and unit row

                # Extract the three columns
                data_df = df.iloc[data_start:, [md_col, inc_col, azi_col]].copy()
                data_df.columns = ['MD', 'INC', 'AZI']

                # Clean: convert to numeric, drop invalid rows
                data_df['MD'] = pd.to_numeric(data_df['MD'], errors='coerce')
                data_df['INC'] = pd.to_numeric(data_df['INC'], errors='coerce')
                data_df['AZI'] = pd.to_numeric(data_df['AZI'], errors='coerce')
                data_df = data_df.dropna(subset=['MD'])

                # Remove duplicate zeros (keep only first)
                zero_mask = data_df['MD'] == 0
                if zero_mask.sum() > 1:
                    data_df = data_df.drop(data_df[zero_mask].index[1:])

                data_df = data_df.reset_index(drop=True)

                # Show extracted data
                st.subheader("Extracted Gyro Data (MD, INC, AZI)")
                st.dataframe(data_df, use_container_width=True)

                # Generate PRN
                prn_lines = [f"Well: {well_name}\n\n"]
                for _, row in data_df.iterrows():
                    md = int(row['MD'])
                    inc = row['INC']
                    azi = row['AZI']
                    prn_lines.append(f"{md} {inc:.2f} {azi:.2f}\n")

                prn_content = "".join(prn_lines)

                st.subheader("PRN Preview")
                st.code(prn_content, language="text")

                st.download_button(
                    label="Download Gyro PRN",
                    data=prn_content,
                    file_name=f"({well_name}) Gyro.prn",
                    mime="text/plain",
                    type="primary"
                )

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.info("Try checking sheet name or upload a different file.")

# ────────────────────────────────────────────────
# 2. Fm Tops
# ────────────────────────────────────────────────
with tab_fm_tops:
    st.header("Formation Tops")
    st.info("Formation Tops preparation coming soon. Add input form, table, export to ASCII/LAS, etc.")

# ────────────────────────────────────────────────
# 3. Mud Log (ASCII-1, ASCII-5)
# ────────────────────────────────────────────────
with tab_mud_log_ascii:
    st.header("Mud Log ASCII (1 & 5)")
    st.info("Mud Log ASCII-1 and ASCII-5 preparation coming soon. Typically includes depth, ROP, gas, etc.")

# ────────────────────────────────────────────────
# 4. Mud & DRLG Parameters
# ────────────────────────────────────────────────
with tab_mud_drlg_params:
    st.header("Mud & Drilling Parameters")
    st.info("Mud properties and drilling parameters preparation coming soon.")

# ────────────────────────────────────────────────
# 5. Mud Log DESC Comment (with sub-header for lithology types)
# ────────────────────────────────────────────────
with tab_desc_comment:
    st.header("Mud Log Description Comment")
    st.subheader("This tab is for preparing the Mud Log Description Comments for:")

    lith_types = ["Clay", "Shale", "Sand", "SST", "SLT.ST", "LST", "Oil Shows"]
    for lit in lith_types:
        st.markdown(f"- **{lit}**")

    st.info("Description comment preparation coming soon. Will support multi-line text input per type, depth association, and formatted ASCII/PRN output.")

# ────────────────────────────────────────────────
# 6. Oil Shows Intensity
# ────────────────────────────────────────────────
with tab_oil_shows:
    st.header("Oil Shows Intensity")
    st.info("Oil shows intensity preparation coming soon. Likely includes depth, intensity level, fluorescence, etc.")
