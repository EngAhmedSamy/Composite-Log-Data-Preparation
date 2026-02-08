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
            # Read the sheet named 'GMS' (or first sheet)
            df = pd.read_excel(excel_file, sheet_name='GMS')

            # Show first few rows so user can see the data
            st.subheader("First 20 rows of the uploaded sheet")
            st.dataframe(df.head(20), use_container_width=True)

            # Detect well name
            well_name = st.session_state.get('well_name', 'Unknown Well')
            for _, row in df.iterrows():
                row_str = ' '.join(row.astype(str))
                if 'Well' in row_str:
                    match = re.search(r'Well\s*[:=-]?\s*([A-Za-z0-9_-]+)', row_str, re.IGNORECASE)
                    if match:
                        well_name = match.group(1).strip()
                        break
            st.session_state.well_name = well_name
            st.success(f"**Well Name detected:** {well_name}")

            # Let user specify starting row if auto-detect fails
            st.subheader("Data extraction settings")
            start_row = st.number_input(
                "Start reading data from row (0-based index, usually 10–50)",
                min_value=0,
                value=10,
                step=1,
                help="Look at the table above — choose the first row with numeric MD values"
            )

            # Extract from user-specified row, try first 3 columns
            data_df = df.iloc[start_row:, :3].copy()
            data_df.columns = ['MD', 'INC', 'AZI']

            # Convert MD to numeric and drop rows where MD is not a number
            data_df['MD'] = pd.to_numeric(data_df['MD'], errors='coerce')
            data_df = data_df.dropna(subset=['MD'])

            if data_df.empty:
                st.error("No valid numeric MD values found after the selected row.")
                st.stop()

            # Convert other columns to numeric
            data_df['INC'] = pd.to_numeric(data_df['INC'], errors='coerce')
            data_df['AZI'] = pd.to_numeric(data_df['AZI'], errors='coerce')

            # Remove duplicate zeros (keep only first row if MD=0)
            zero_mask = data_df['MD'] == 0
            if zero_mask.sum() > 1:
                first_zero_idx = data_df[zero_mask].index[0]
                data_df = data_df.drop(data_df[zero_mask].index[1:])

            data_df = data_df.reset_index(drop=True)

            # Preview extracted data
            st.subheader("Extracted Gyro Data")
            st.dataframe(data_df[['MD', 'INC', 'AZI']], use_container_width=True)

            # Generate PRN
            prn_lines = [f"Well: {well_name}\n\n"]
            for _, row in data_df.iterrows():
                md = int(row['MD'])
                inc = row['INC']
                azi = row['AZI']
                prn_lines.append(f"{md} {inc:.2f} {azi:.2f}\n")

            prn_content = "".join(prn_lines)

            st.subheader("PRN Preview (copy-paste ready)")
            st.code(prn_content, language="text")

            st.download_button(
                label="Download Gyro PRN",
                data=prn_content,
                file_name=f"({well_name}) Gyro.prn",
                mime="text/plain",
                type="primary"
            )

        except Exception as e:
            st.error(f"Error reading Excel file: {str(e)}")
            st.info("Make sure the file has a sheet named 'GMS'. If not, try changing sheet_name='Sheet1' in the code.")
            

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
