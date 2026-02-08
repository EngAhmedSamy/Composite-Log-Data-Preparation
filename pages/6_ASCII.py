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
            # Read the FIRST sheet (index 0), no header to scan all cells
            df = pd.read_excel(excel_file, sheet_name=0, header=None)

            # Show first 20 rows for reference
            st.subheader("First 20 rows of the sheet (for reference)")
            st.dataframe(df.head(20), use_container_width=True)

            # ──────────────────────────────
            # Find Well Name (search all cells, look right or below)
            # ──────────────────────────────
            well_name = st.session_state.get('well_name', 'Unknown Well')
            found_well = False
            for i in range(len(df)):
                for j in range(len(df.columns)):
                    cell = str(df.iloc[i, j]).strip().upper()
                    if 'WELL' in cell or 'WELL NAME' in cell:
                        # Try right (same row, next cell)
                        if j + 1 < len(df.columns) and pd.notna(df.iloc[i, j+1]):
                            well_name = str(df.iloc[i, j+1]).strip()
                            found_well = True
                        # Try below (next row, same column)
                        elif i + 1 < len(df) and pd.notna(df.iloc[i+1, j]):
                            well_name = str(df.iloc[i+1, j]).strip()
                            found_well = True
                        if found_well:
                            break
                if found_well:
                    break

            st.session_state.well_name = well_name
            st.success(f"**Well Name:** {well_name}")

            # ──────────────────────────────
            # Find columns: MD, INC/ANG, AZI/AZ (flexible: header + unit or header only)
            # ──────────────────────────────
            md_col = inc_col = azi_col = None

            for i in range(len(df) - 1):
                for j in range(len(df.columns)):
                    cell = str(df.iloc[i, j]).strip().upper()
                    below = str(df.iloc[i+1, j]).strip().upper()

                    # MD column
                    if "MD" in cell:
                        if "FT" in below or pd.isna(below) or below == '':
                            md_col = j

                    # INC/ANG column
                    if ("INC" in cell or "ANG" in cell):
                        if "DEG" in below or pd.isna(below) or below == '':
                            inc_col = j

                    # AZI/AZ column
                    if "AZI" in cell or "AZ" in cell:
                        azi_col = j

            # Fallback: if no match with unit, look for headers alone
            if md_col is None:
                for i in range(len(df)):
                    for j in range(len(df.columns)):
                        cell = str(df.iloc[i, j]).strip().upper()
                        if "MD" in cell:
                            md_col = j
                            break
                    if md_col is not None:
                        break

            if inc_col is None:
                for i in range(len(df)):
                    for j in range(len(df.columns)):
                        cell = str(df.iloc[i, j]).strip().upper()
                        if "INC" in cell or "ANG" in cell:
                            inc_col = j
                            break
                    if inc_col is not None:
                        break

            if azi_col is None:
                for i in range(len(df)):
                    for j in range(len(df.columns)):
                        cell = str(df.iloc[i, j]).strip().upper()
                        if "AZI" in cell or "AZ" in cell:
                            azi_col = j
                            break
                    if azi_col is not None:
                        break

            # Check which columns were found
            found_cols = []
            if md_col is not None: found_cols.append("MD")
            if inc_col is not None: found_cols.append("INC/ANG")
            if azi_col is not None: found_cols.append("AZI/AZ")

            if not found_cols:
                st.error("Could not find any of MD, INC/ANG, or AZI/AZ columns.")
            else:
                st.info(f"Found columns: {', '.join(found_cols)}")

                # Data starts after header + unit row (or after header if no unit)
                start_row = 0
                for i in range(len(df)):
                    if any(pd.notna(df.iloc[i, c]) for c in [md_col, inc_col, azi_col] if c is not None):
                        start_row = i + 2  # skip header and unit
                        break

                # Extract available columns
                cols_to_take = []
                if md_col is not None: cols_to_take.append(md_col)
                if inc_col is not None: cols_to_take.append(inc_col)
                if azi_col is not None: cols_to_take.append(azi_col)

                data_df = df.iloc[start_row:, cols_to_take].copy()
                data_df.columns = ['MD' if c == md_col else 'INC' if c == inc_col else 'AZI' for c in cols_to_take]

                # Clean
                for col in data_df.columns:
                    data_df[col] = pd.to_numeric(data_df[col], errors='coerce')

                data_df = data_df.dropna(subset=['MD'])

                # Keep only first zero row
                zero_mask = data_df['MD'] == 0
                if zero_mask.sum() > 1:
                    data_df = data_df.drop(data_df[zero_mask].index[1:])

                data_df = data_df.reset_index(drop=True)

                # Show extracted data
                st.subheader("Extracted Gyro Data")
                st.dataframe(data_df, use_container_width=True)

                # Generate aligned PRN
                prn_lines = [f"Well: {well_name}\n\n"]
                header = "MD"
                if 'INC' in data_df.columns:
                    header += "   INC"
                if 'AZI' in data_df.columns:
                    header += "   AZI"
                prn_lines.append(header + "\n")

                for _, row in data_df.iterrows():
                    md = int(row['MD'])
                    line = f"{md:>5}"
                    if 'INC' in data_df.columns:
                        line += f" {row['INC']:>7.2f}"
                    if 'AZI' in data_df.columns:
                        line += f" {row['AZI']:>7.2f}"
                    prn_lines.append(line + "\n")

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
            st.error(f"Error processing file: {str(e)}")
            st.info("Check if the file is valid Excel and contains the expected data.")


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
