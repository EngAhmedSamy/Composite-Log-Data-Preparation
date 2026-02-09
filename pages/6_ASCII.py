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
from openpyxl import load_workbook
import io
import zipfile

st.title("Mud Log ASCII-1 and ASCII-5")

uploaded_file = st.file_uploader("Upload Excel File", type=["xls", "xlsx"])

if uploaded_file:
    # Load the workbook
    wb = load_workbook(uploaded_file, data_only=True)
    
    # Find well name by searching cells
    well_name = None
    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str) and "WELL:" in cell.value.upper():
                    parts = cell.value.upper().split("WELL:")
                    if len(parts) > 1:
                        well_name = parts[1].strip()
                    break
            if well_name:
                break
        if well_name:
            break
    
    if not well_name:
        well_name = st.text_input("Enter Well Name (not found in Excel)", "Unknown Well")
    else:
        st.info(f"Well Name found: {well_name}")
    
    prn1_content = None
    prn5_content = None
    
    # Process ASCII 1 from 'DRLG 1' sheet
    if "DRLG 1" in wb.sheetnames:
        sheet = wb["DRLG 1"]
        depth_col = None
        header_row = None
        for row_idx in range(1, sheet.max_row + 1):
            for col_idx in range(1, sheet.max_column + 1):
                cell = sheet.cell(row_idx, col_idx)
                if cell.value and isinstance(cell.value, str) and ("DEPTH" in cell.value.upper() or "T_DPTH" in cell.value.upper()):
                    unit_cell = sheet.cell(row_idx + 1, col_idx)
                    if unit_cell.value and "FT" in str(unit_cell.value).upper():
                        wob_cell = sheet.cell(row_idx, col_idx + 1)
                        if wob_cell.value and "WOB" in str(wob_cell.value).upper():
                            wob_unit = sheet.cell(row_idx + 1, col_idx + 1)
                            if wob_unit.value and "KLBS" in str(wob_unit.value).upper():
                                rpm_cell = sheet.cell(row_idx, col_idx + 2)
                                if rpm_cell.value and "RPM" in str(rpm_cell.value).upper():
                                    rpm_unit = sheet.cell(row_idx + 1, col_idx + 2)
                                    if rpm_unit.value and "R/MIN" in str(rpm_unit.value).upper():
                                        depth_col = col_idx
                                        header_row = row_idx
                                        data_start_row = row_idx + 2
                                        break
            if depth_col:
                break
        
        if depth_col:
            data = []
            for r in range(data_start_row, sheet.max_row + 1):
                depth = sheet.cell(r, depth_col).value
                wob = sheet.cell(r, depth_col + 1).value
                rpm = sheet.cell(r, depth_col + 2).value
                if depth is not None:
                    try:
                        depth = float(depth)
                        wob = float(wob) if wob is not None else 0
                        rpm = float(rpm) if rpm is not None else 0
                        data.append((depth, wob, rpm))
                    except ValueError:
                        continue
            
            if data:
                prn1_content = f"Well: {well_name} MD WOB RPM\n"
                for d, w, r in data:
                    prn1_content += f"{d} {w} {r}\n"
    
    # Process ASCII 5 from 'GAS 5' sheet
    if "GAS 5" in wb.sheetnames:
        sheet = wb["GAS 5"]
        depth_col = None
        header_row = None
        for row_idx in range(1, sheet.max_row + 1):
            for col_idx in range(1, sheet.max_column + 1):
                cell = sheet.cell(row_idx, col_idx)
                if cell.value and isinstance(cell.value, str) and ("DEPTH" in cell.value.upper() or "T_DPTH" in cell.value.upper() or "MD" in cell.value.upper()):
                    unit_cell = sheet.cell(row_idx + 1, col_idx)
                    if unit_cell.value and "FT" in str(unit_cell.value).upper():
                        rop_cell = sheet.cell(row_idx, col_idx + 1)
                        if rop_cell.value and "ROP" in str(rop_cell.value).upper():
                            rop_unit = sheet.cell(row_idx + 1, col_idx + 1)
                            if rop_unit.value and "FT/HR" in str(rop_unit.value).upper():
                                tg_cell = sheet.cell(row_idx, col_idx + 2)
                                if tg_cell.value and ("T_GAS" in str(tg_cell.value).upper() or "TG" in str(tg_cell.value).upper()):
                                    tg_unit = sheet.cell(row_idx + 1, col_idx + 2)
                                    if tg_unit.value and "%" in str(tg_unit.value).upper():
                                        c1_cell = sheet.cell(row_idx, col_idx + 3)
                                        if c1_cell.value and "C1" in str(c1_cell.value).upper():
                                            c1_unit = sheet.cell(row_idx + 1, col_idx + 3)
                                            if c1_unit.value and "PPM" in str(c1_unit.value).upper():
                                                c2_cell = sheet.cell(row_idx, col_idx + 4)
                                                if c2_cell.value and "C2" in str(c2_cell.value).upper():
                                                    c2_unit = sheet.cell(row_idx + 1, col_idx + 4)
                                                    if c2_unit.value and "PPM" in str(c2_unit.value).upper():
                                                        c3_cell = sheet.cell(row_idx, col_idx + 5)
                                                        if c3_cell.value and "C3" in str(c3_cell.value).upper():
                                                            c3_unit = sheet.cell(row_idx + 1, col_idx + 5)
                                                            if c3_unit.value and "PPM" in str(c3_unit.value).upper():
                                                                ic4_cell = sheet.cell(row_idx, col_idx + 6)
                                                                if ic4_cell.value and ("IC4" in str(ic4_cell.value).upper() or "C4I" in str(ic4_cell.value).upper()):
                                                                    ic4_unit = sheet.cell(row_idx + 1, col_idx + 6)
                                                                    if ic4_unit.value and "PPM" in str(ic4_unit.value).upper():
                                                                        nc4_cell = sheet.cell(row_idx, col_idx + 7)
                                                                        if nc4_cell.value and ("NC4" in str(nc4_cell.value).upper() or "C4N" in str(nc4_cell.value).upper()):
                                                                            nc4_unit = sheet.cell(row_idx + 1, col_idx + 7)
                                                                            if nc4_unit.value and "PPM" in str(nc4_unit.value).upper():
                                                                                c5_cell = sheet.cell(row_idx, col_idx + 8)
                                                                                if c5_cell.value and "C5" in str(c5_cell.value).upper():
                                                                                    c5_unit = sheet.cell(row_idx + 1, col_idx + 8)
                                                                                    if c5_unit.value and "PPM" in str(c5_unit.value).upper():
                                                                                        depth_col = col_idx
                                                                                        header_row = row_idx
                                                                                        data_start_row = row_idx + 2
                                                                                        break
            if depth_col:
                break
        
        if depth_col:
            data = []
            for r in range(data_start_row, sheet.max_row + 1):
                values = []
                for c in range(0, 9):
                    val = sheet.cell(r, depth_col + c).value
                    if val is not None:
                        try:
                            val = float(val)
                        except ValueError:
                            val = 0
                    else:
                        val = 0
                    values.append(val)
                if values[0] != 0:  # Assume depth > 0
                    data.append(values)
            
            if data:
                prn5_content = f"Well: {well_name} MD ROP TG C1 C2 C3 C4I C4N C5\n"
                for row in data:
                    prn5_content += " ".join(str(v) for v in row) + "\n"
    
    # Previews
    if prn1_content:
        st.subheader("Preview ASCII 1")
        st.text(prn1_content[:2000] + "..." if len(prn1_content) > 2000 else prn1_content)
        st.download_button(
            label="Download ASCII 1 .prn",
            data=prn1_content,
            file_name=f"{well_name} Mud Log Ascii 1.prn",
            mime="text/plain"
        )
    
    if prn5_content:
        st.subheader("Preview ASCII 5")
        st.text(prn5_content[:2000] + "..." if len(prn5_content) > 2000 else prn5_content)
        st.download_button(
            label="Download ASCII 5 .prn",
            data=prn5_content,
            file_name=f"{well_name} Mud Log Ascii 5.prn",
            mime="text/plain"
        )
    
    if prn1_content and prn5_content:
        # Create ZIP (as RAR requires additional libs, using ZIP instead)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr(f"{well_name} Mud Log Ascii 1.prn", prn1_content)
            zf.writestr(f"{well_name} Mud Log Ascii 5.prn", prn5_content)
        zip_buffer.seek(0)
        st.download_button(
            label="Download Both in ZIP (RAR alternative)",
            data=zip_buffer,
            file_name=f"{well_name} Mud Log Ascii 1 & 5.zip",
            mime="application/zip"
        )








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
