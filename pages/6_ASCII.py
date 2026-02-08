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
            # Read the Excel sheet named 'GMS' (or first sheet if name differs)
            df = pd.read_excel(excel_file, sheet_name='GMS')

            # Step 1: Extract Well Name
            well_name = st.session_state.get('well_name', 'Unknown Well')
            for _, row in df.iterrows():
                row_str = ' '.join(row.astype(str))
                if 'Well' in row_str:
                    match = re.search(r'Well\s*[:=-]?\s*([A-Za-z0-9_-]+)', row_str, re.IGNORECASE)
                    if match:
                        well_name = match.group(1).strip()
                        break
            st.session_state.well_name = well_name  # Update global well name
            st.write(f"**Detected Well Name:** {well_name}")

            # Step 2: Find start of numeric data (first row with valid MD)
            data_start_idx = None
            for idx, row in df.iterrows():
                if pd.notna(row.iloc[0]) and str(row.iloc[0]).replace('.', '').isdigit():
                    data_start_idx = idx
                    break

            if data_start_idx is None:
                st.error("Could not find numeric MD column in the sheet.")
            else:
                # Take data from the first numeric row onward
                data_df = df.iloc[data_start_idx:, :3].copy()
                # Assume columns: MD, INC (ANG), AZI
                data_df.columns = ['MD', 'INC', 'AZI']

                # Clean: keep only rows with valid MD (numeric)
                data_df = data_df[pd.to_numeric(data_df['MD'], errors='coerce').notnull()]

                # Convert to numeric
                data_df['MD'] = pd.to_numeric(data_df['MD'], errors='coerce')
                data_df['INC'] = pd.to_numeric(data_df['INC'], errors='coerce')
                data_df['AZI'] = pd.to_numeric(data_df['AZI'], errors='coerce')

                # Remove rows where MD == 0 except the very first one
                zero_rows = data_df[data_df['MD'] == 0]
                if not zero_rows.empty:
                    first_zero = zero_rows.index[0]
                    data_df = data_df.drop(zero_rows.index[1:])  # keep only first zero

                # Reset index
                data_df = data_df.reset_index(drop=True)

                # Preview extracted data
                st.subheader("Extracted Gyro Data")
                st.dataframe(data_df[['MD', 'INC', 'AZI']], use_container_width=True)

                # Generate PRN output
                prn_lines = [f"Well: {well_name}\n"]
                for _, row in data_df.iterrows():
                    md = int(row['MD'])
                    inc = row['INC']
                    azi = row['AZI']
                    # Format: MD ANG AZI (space delimited)
                    prn_lines.append(f"{md} {inc:.2f} {azi:.2f}\n")

                prn_content = "".join(prn_lines)

                # Preview PRN content
                st.subheader("PRN Preview (copy-paste ready)")
                st.code(prn_content, language="text")

                # Download button
                st.download_button(
                    label="Download (Well Name) Gyro.prn",
                    data=prn_content,
                    file_name=f"({well_name}) Gyro.prn",
                    mime="text/plain"
                )

        except Exception as e:
            st.error(f"Error reading Excel file: {str(e)}")
            st.info("Make sure the file has a sheet named 'GMS' or adjust sheet_name in code.")
            

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
