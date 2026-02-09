import streamlit as st
import pandas as pd
import io
import re
import zipfile
import openpyxl  # for merged cells and better cell access

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

    # Predefined Fm Tops list
    fm_tops_list = [
        "Dabaa Fm",
        "Apollonia Fm",
        "Khoman Fm",
        "Abu Roash 'A' Mbr",
        "Abu Roash 'B' Mbr",
        "Abu Roash 'C' Mbr",
        "Abu Roash 'D' Mbr",
        "Abu Roash 'E' Mbr",
        "Abu Roash 'F' Mbr",
        "Upper Abu Roash 'G' Mbr",
        "Middle Abu Roash 'G' Mbr",
        "Lower Abu Roash 'G' Mbr",
        "Upper Bahariya Fm",
        "Lower Bahariya Fm",
        "Kharita Fm"
    ]

    # Normalized list for matching (lowercase, no spaces/quotes)
    normalized_tops = {fm.lower().replace(" ", "").replace("'", "").replace('"', ""): fm for fm in fm_tops_list}

    # Data storage
    if 'fm_tops_data' not in st.session_state:
        st.session_state.fm_tops_data = {fm: {'selected': False, 'MD': 0, 'TVDSS': 0} for fm in fm_tops_list}

    # Flag to track if auto-fill was done for current file
    if 'auto_filled' not in st.session_state:
        st.session_state.auto_filled = False
    if 'last_excel_name' not in st.session_state:
        st.session_state.last_excel_name = None
    if 'matched_tops' not in st.session_state:
        st.session_state.matched_tops = []

    # Upload Excel option
    excel_file = st.file_uploader("Upload Fm Tops Excel (optional)", type=["xlsx", "xls"])

    # Auto-fill logic - only run once per file
    if excel_file:
        current_file_name = excel_file.name

        # Reset for new file
        if st.session_state.last_excel_name != current_file_name:
            st.session_state.auto_filled = False
            st.session_state.matched_tops = []
            st.session_state.last_excel_name = current_file_name

        # Run auto-fill only if not already done for this file
        if not st.session_state.auto_filled:
            try:
                upload_df = pd.read_excel(excel_file, sheet_name=0)

                # Find well name
                well_name = st.session_state.get('well_name', 'Unknown Well')
                found = False
                for i in range(len(upload_df)):
                    for j in range(len(upload_df.columns)):
                        cell = str(upload_df.iloc[i, j]).strip().upper()
                        if 'WELL' in cell:
                            if j + 1 < len(upload_df.columns) and pd.notna(upload_df.iloc[i, j+1]):
                                well_name = str(upload_df.iloc[i, j+1]).strip()
                                found = True
                            elif i + 1 < len(upload_df) and pd.notna(upload_df.iloc[i+1, j]):
                                well_name = str(upload_df.iloc[i+1, j]).strip()
                                found = True
                            if found:
                                break
                    if found:
                        break
                st.session_state.well_name = well_name

                # Auto-fill depths
                matched = []
                for i in range(len(upload_df)):
                    for j in range(len(upload_df.columns)):
                        cell = str(upload_df.iloc[i, j]).strip().lower().replace(" ", "").replace("'", "").replace('"', "")
                        if cell in normalized_tops:
                            fm = normalized_tops[cell]

                            if j + 1 < len(upload_df.columns) and pd.notna(upload_df.iloc[i, j+1]):
                                try:
                                    md = int(upload_df.iloc[i, j+1])
                                except:
                                    md = 0
                                tvdss = 0
                                if j + 2 < len(upload_df.columns) and pd.notna(upload_df.iloc[i, j+2]):
                                    try:
                                        tvdss = int(upload_df.iloc[i, j+2])
                                    except:
                                        tvdss = 0

                                st.session_state.fm_tops_data[fm]['MD'] = md
                                st.session_state.fm_tops_data[fm]['TVDSS'] = tvdss
                                st.session_state.fm_tops_data[fm]['selected'] = True
                                matched.append(fm)

                # Store matches and flag
                st.session_state.matched_tops = matched
                st.session_state.auto_filled = True

                if matched:
                    st.success(f"Matched and auto-filled {len(matched)} Fm Tops: {', '.join(matched)}. Review below.")
                    st.rerun()  # Refresh UI once to show updated inputs
                else:
                    st.warning("No matching Fm Tops found in Excel. Check names or enter manually.")

            except Exception as e:
                st.error(f"Error reading Excel: {str(e)}")

    # Always show persistent match message if we have previous matches
    if st.session_state.matched_tops:
        st.success(f"Matched and auto-filled {len(st.session_state.matched_tops)} Fm Tops: {', '.join(st.session_state.matched_tops)}. Review below.")

    # Input form: checkboxes + MD/TVDSS
    st.subheader("Select and Edit Fm Tops")
    for fm in fm_tops_list:
        # Use a dynamic key that changes when upload happens
        upload_key = st.session_state.get('last_excel_name', 'no_upload')
        selected = st.checkbox(
            fm,
            value=st.session_state.fm_tops_data[fm]['selected'],
            key=f"select_{fm}_{upload_key}"
        )
        col_md, col_tvdss = st.columns(2)
        with col_md:
            md = st.number_input(
                "MD (ft)",
                min_value=0,
                value=st.session_state.fm_tops_data[fm]['MD'],
                key=f"md_{fm}_{upload_key}"
            )
        with col_tvdss:
            tvdss = st.number_input(
                "TVDSS (ft)",
                value=st.session_state.fm_tops_data[fm]['TVDSS'],
                key=f"tvdss_{fm}_{upload_key}"
            )
        # Update session state with current widget values
        st.session_state.fm_tops_data[fm]['selected'] = selected
        st.session_state.fm_tops_data[fm]['MD'] = md
        st.session_state.fm_tops_data[fm]['TVDSS'] = tvdss

    # Preview & Download PRN
    st.subheader("PRN Preview & Download")
    selected_tops = [fm for fm in fm_tops_list if st.session_state.fm_tops_data[fm]['selected']]

    if not selected_tops:
        st.info("No Fm Tops selected. Check boxes above to include.")
    else:
        well_name = st.session_state.get('well_name', 'Unknown Well')
        prn_output = io.StringIO()
        prn_output.write(f"Well:           {well_name}\n\n")

        for fm in selected_tops:
            md = int(st.session_state.fm_tops_data[fm]['MD'])
            tvdss = int(st.session_state.fm_tops_data[fm]['TVDSS'])
            prn_output.write(f"{md-6:>5} {md-6 + 3:>22} \"{fm}\"\n")
            prn_output.write(f"{md+5:>5} {md+5 + 4:>22} \"@ {md} ft (- {tvdss} ft TVDSS )\"\n")

        prn_content = prn_output.getvalue()

        st.code(prn_content, language="text")

        st.download_button(
            label="Download Fm Tops PRN",
            data=prn_content,
            file_name=f"({well_name}) Fm Tops.prn",
            mime="text/plain",
            type="primary"
        )








# ────────────────────────────────────────────────
# 3. Mud Log (ASCII-1, ASCII-5)
# ────────────────────────────────────────────────
import streamlit as st
import pandas as pd
import io
import zipfile
import openpyxl

with tab_mud_log_ascii:
    st.header("Mud Log (ASCII-1, ASCII-5)")

    excel_file = st.file_uploader("Upload Drilling Parameters Excel", type=["xls", "xlsx"])

    if excel_file:
        try:
            wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
            sheet_names = wb.sheetnames

            well_name = st.session_state.get('well_name', 'Unknown Well')
            st.success(f"**Well Name:** {well_name}")

            # ──────────────────────────────
            # ASCII 1: DRLG 1 sheet (MD, WOB, RPM)
            # ──────────────────────────────
            ascii1_prn = None
            if 'DRLG 1' in sheet_names:
                ws = wb['DRLG 1']

                header_row = None
                unit_row = None
                md_col = wob_col = rpm_col = None

                depth_keywords = ["MD", "T_DPTH", "T.DPTH", "DEPTH", "T DEPTH", "MEASURED DEPTH", "T_DPTH FT"]
                wob_keywords = ["WOB", "W.O.B", "WEIGHT ON BIT", "WOB KLBS"]
                rpm_keywords = ["RPM", "R/MIN", "ROTARY SPEED", "RPM R/MIN"]

                # Find header row (row with multiple headers)
                for row_num, row in enumerate(ws.iter_rows(min_row=1, max_row=50), start=1):  # limit to first 50 rows
                    headers_in_row = 0
                    for cell in row:
                        if cell.value:
                            cell_val = str(cell.value).strip().upper()
                            if any(kw in cell_val for kw in depth_keywords + wob_keywords + rpm_keywords):
                                headers_in_row += 1

                    if headers_in_row >= 2:  # at least 2 headers in row
                        header_row = row_num
                        # Check next row for units
                        unit_row = header_row + 1
                        break

                if header_row is None:
                    st.error("Could not find header row in 'DRLG 1' sheet.")
                else:
                    # Scan header row for columns
                    for cell in ws[header_row]:
                        if cell.value:
                            cell_val = str(cell.value).strip().upper()

                            if any(kw in cell_val for kw in depth_keywords):
                                md_col = cell.column

                            if any(kw in cell_val for kw in wob_keywords):
                                wob_col = cell.column

                            if any(kw in cell_val for kw in rpm_keywords):
                                rpm_col = cell.column

                    if md_col is None or wob_col is None or rpm_col is None:
                        st.error("Could not find MD, WOB, RPM columns in 'DRLG 1' sheet.")
                    else:
                        # Data starts after unit row (if present)
                        start_row = unit_row + 1 if unit_row else header_row + 1

                        # Extract data with pandas
                        drlg_df = pd.read_excel(excel_file, sheet_name='DRLG 1', header=None, engine='openpyxl')
                        ascii1_data = drlg_df.iloc[start_row-1:, [md_col-1, wob_col-1, rpm_col-1]].copy()
                        ascii1_data.columns = ['MD', 'WOB', 'RPM']
                        ascii1_data = ascii1_data[pd.to_numeric(ascii1_data['MD'], errors='coerce').notnull()]

                        ascii1_data['MD'] = pd.to_numeric(ascii1_data['MD'])
                        ascii1_data['WOB'] = pd.to_numeric(ascii1_data['WOB'])
                        ascii1_data['RPM'] = pd.to_numeric(ascii1_data['RPM'])

                        st.subheader("Extracted ASCII 1 Data (MD, WOB, RPM)")
                        st.dataframe(ascii1_data, use_container_width=True)

                        ascii1_prn = io.StringIO()
                        ascii1_prn.write(f"Well:           {well_name}\n\n")
                        ascii1_prn.write("  MD    WOB     RPM\n")
                        for _, row in ascii1_data.iterrows():
                            md = int(row['MD'])
                            wob = row['WOB']
                            rpm = row['RPM']
                            ascii1_prn.write(f" {md:>3}    {wob:>3.1f}      {rpm:>3}\n")

                        st.subheader("ASCII 1 PRN Preview")
                        st.code(ascii1_prn.getvalue(), language="text")

                        st.download_button(
                            "Download Mud Log ASCII 1.prn",
                            ascii1_prn.getvalue(),
                            file_name=f"({well_name}) Mud Log ASCII 1.prn",
                            mime="text/plain"
                        )

            # ──────────────────────────────
            # ASCII 5: GAS 5 sheet
            # ──────────────────────────────
            ascii5_prn = None
            if 'GAS 5' in sheet_names:
                ws = wb['GAS 5']

                header_row = None
                unit_row = None
                md_col = rop_col = tg_col = c1_col = c2_col = c3_col = ic4_col = nc4_col = c5_col = None

                depth_keywords = ["MD", "T_DPTH", "T.DPTH", "DEPTH", "T DEPTH", "MEASURED DEPTH", "T_DPTH FT"]
                rop_keywords = ["ROP1", "ROP", "RATE OF PENETRATION", "ROP1 FT/HR"]
                tg_keywords = ["T_GAS", "TG", "TOTAL GAS", "T_GAS %"]
                c1_keywords = ["C1", "METHANE", "C1 PPM"]
                c2_keywords = ["C2", "ETHANE", "C2 PPM"]
                c3_keywords = ["C3", "PROPANE", "C3 PPM"]
                ic4_keywords = ["IC4", "I-C4", "ISOBUTANE", "IC4 PPM"]
                nc4_keywords = ["NC4", "N-C4", "NORMAL BUTANE", "NC4 PPM"]
                c5_keywords = ["C5", "PENTANE", "C5 PPM"]

                # Find header row
                for row_num, row in enumerate(ws.iter_rows(min_row=1, max_row=50), start=1):
                    headers_in_row = 0
                    for cell in row:
                        if cell.value:
                            cell_val = str(cell.value).strip().upper()
                            if any(kw in cell_val for kw in depth_keywords + rop_keywords + tg_keywords + c1_keywords + c2_keywords + c3_keywords + ic4_keywords + nc4_keywords + c5_keywords):
                                headers_in_row += 1

                    if headers_in_row >= 3:  # at least 3 headers in row
                        header_row = row_num
                        unit_row = header_row + 1
                        break

                if header_row is None:
                    st.error("Could not find header row in 'GAS 5' sheet.")
                else:
                    # Scan header row for columns
                    for cell in ws[header_row]:
                        if cell.value:
                            cell_val = str(cell.value).strip().upper()

                            if any(kw in cell_val for kw in depth_keywords):
                                md_col = cell.column

                            if any(kw in cell_val for kw in rop_keywords):
                                rop_col = cell.column

                            if any(kw in cell_val for kw in tg_keywords):
                                tg_col = cell.column

                            if any(kw in cell_val for kw in c1_keywords):
                                c1_col = cell.column

                            if any(kw in cell_val for kw in c2_keywords):
                                c2_col = cell.column

                            if any(kw in cell_val for kw in c3_keywords):
                                c3_col = cell.column

                            if any(kw in cell_val for kw in ic4_keywords):
                                ic4_col = cell.column

                            if any(kw in cell_val for kw in nc4_keywords):
                                nc4_col = cell.column

                            if any(kw in cell_val for kw in c5_keywords):
                                c5_col = cell.column

                    if md_col is None or rop_col is None or tg_col is None or c1_col is None or c2_col is None or c3_col is None or ic4_col is None or nc4_col is None or c5_col is None:
                        st.error("Could not find all columns for ASCII 5 in 'GAS 5' sheet.")
                    else:
                        start_row = unit_row + 1 if unit_row else header_row + 1

                        gas_df = pd.read_excel(excel_file, sheet_name='GAS 5', header=None, engine='openpyxl')
                        ascii5_data = gas_df.iloc[start_row-1:, [md_col-1, rop_col-1, tg_col-1, c1_col-1, c2_col-1, c3_col-1, ic4_col-1, nc4_col-1, c5_col-1]].copy()
                        ascii5_data.columns = ['MD', 'ROP', 'TG', 'C1', 'C2', 'C3', 'C4I', 'C4N', 'C5']
                        ascii5_data = ascii5_data[pd.to_numeric(ascii5_data['MD'], errors='coerce').notnull()]

                        ascii5_data['MD'] = pd.to_numeric(ascii5_data['MD'])
                        for col in ascii5_data.columns[1:]:
                            ascii5_data[col] = pd.to_numeric(ascii5_data[col], errors='coerce').fillna(0)

                        st.subheader("Extracted ASCII 5 Data")
                        st.dataframe(ascii5_data, use_container_width=True)

                        ascii5_prn = io.StringIO()
                        ascii5_prn.write(f"Well:           {well_name}\n\n")
                        ascii5_prn.write("  MD    ROP      TG      C1      C2      C3     C4I     C4N      C5\n")
                        for _, row in ascii5_data.iterrows():
                            md = int(row['MD'])
                            rop = row['ROP']
                            tg = row['TG']
                            c1 = row['C1']
                            c2 = row['C2']
                            c3 = row['C3']
                            c4i = row['C4I']
                            c4n = row['C4N']
                            c5 = row['C5']
                            ascii5_prn.write(f" {md:>3}   {rop:>5.1f}     {tg:>3.0f}     {c1:>4.0f}     {c2:>4.0f}     {c3:>4.0f}     {c4i:>4.0f}     {c4n:>4.0f}     {c5:>4.0f}\n")

                        st.subheader("ASCII 5 PRN Preview")
                        st.code(ascii5_prn.getvalue(), language="text")

                        st.download_button(
                            "Download Mud Log ASCII 5.prn",
                            ascii5_prn.getvalue(),
                            file_name=f"({well_name}) Mud Log ASCII 5.prn",
                            mime="text/plain"
                        )

            # ZIP creation (output only)
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                if ascii1_prn:
                    zf.writestr(f"({well_name}) Mud Log ASCII 1.prn", ascii1_prn.getvalue())
                if ascii5_prn:
                    zf.writestr(f"({well_name}) Mud Log ASCII 5.prn", ascii5_prn.getvalue())

            zip_buf.seek(0)

            st.download_button(
                "Download ZIP (ASCII 1 & 5)",
                zip_buf.getvalue(),
                file_name=f"({well_name}) Mud Log ASCII 1 & 5.zip",
                mime="application/zip"
            )

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.info("Make sure the file has 'DRLG 1' and/or 'GAS 5' sheets.")
















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
