import streamlit as st
import pandas as pd
import io
import re
import zipfile
import openpyxl  # for merged cells and better cell access
import math

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

    excel_file = st.file_uploader("Upload Gyro / Survey Excel File", type=["xlsx", "xls"], key="uploader_gyro_survey")

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
    excel_file = st.file_uploader("Upload Fm Tops Excel (optional)", type=["xlsx", "xls"], key="fm_tops_uploader")

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


with tab_mud_log_ascii:
    st.title("Mud Log ASCII-1 and ASCII-5 Generator")
    uploaded_file = st.file_uploader("Upload Excel File (.xls or .xlsx)", type=["xls", "xlsx"], key="uploader_ascii_drlg_gas")
    
    prn1_content = None
    prn5_content = None
    well_name = "Unknown_Well"
    df_drlg1 = None
    df_gas5 = None
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        uploaded_file.seek(0)
        
        # ─── Try modern .xlsx first ──────────────────────────────────────────────
        try:
            wb = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
            sheet_names = wb.sheet_names
            st.success("Loaded as modern .xlsx")
        except Exception:
            try:
                wb = pd.ExcelFile(io.BytesIO(file_bytes), engine="xlrd")
                sheet_names = wb.sheet_names
                st.warning("Loaded as legacy .xls (Excel 97-2003 format)")
            except Exception as e:
                st.error("Cannot read the file with openpyxl or xlrd.")
                st.error("Please open in Excel → Save As → .xlsx format and try again.")
                st.stop()
        
        # Find well name (simple search in all sheets)
        for sheet_name in sheet_names:
            try:
                df_temp = pd.read_excel(wb, sheet_name=sheet_name, header=None, dtype=str)
                for _, row in df_temp.iterrows():
                    for val in row:
                        if pd.notna(val) and isinstance(val, str) and "WELL:" in val.upper():
                            parts = val.upper().split("WELL:")
                            if len(parts) > 1:
                                well_name = parts[1].strip().replace("\n", " ").strip()
                                st.info(f"Well name detected: **{well_name}**")
                                break
                    if well_name != "Unknown_Well":
                        break
            except:
                continue
            if well_name != "Unknown_Well":
                break
        
        # ─── Load DRLG 1 ─────────────────────────────────────────────────────────
        if "DRLG 1" in sheet_names:
            try:
                df_drlg1 = pd.read_excel(
                    wb,
                    sheet_name="DRLG 1",
                    header=None,
                    dtype=str,
                    keep_default_na=False
                )
                st.success("DRLG 1 sheet loaded")
            except Exception as e:
                st.warning(f"Could not read DRLG 1: {e}")
        
        # ─── Load GAS 5 ──────────────────────────────────────────────────────────
        if "GAS 5" in sheet_names:
            try:
                df_gas5 = pd.read_excel(
                    wb,
                    sheet_name="GAS 5",
                    header=None,
                    dtype=str,
                    keep_default_na=False
                )
                st.success("GAS 5 sheet loaded")
            except Exception as e:
                st.warning(f"Could not read GAS 5: {e}")
        
        # ─── Process ASCII 1 (MD, WOB, RPM) ──────────────────────────────────────
        if df_drlg1 is not None:
            # Look for header row containing T_Dpth / Depth, WOB, RPM
            header_row_idx = None
            for i, row in df_drlg1.iterrows():
                row_str = row.astype(str).str.upper().str.strip()
                if any("T_DPTH" in x or "DEPTH" in x or "MD" in x for x in row_str):
                    if any("WOB" in x for x in row_str) and any("RPM" in x for x in row_str):
                        header_row_idx = i
                        break
            if header_row_idx is not None:
                # Assume data starts 2 rows below header (after units)
                data_start = header_row_idx + 2
                df_data = df_drlg1.iloc[data_start:].copy()
                # Find column indices
                cols = df_drlg1.iloc[header_row_idx].astype(str).str.upper().str.strip()
                depth_col = wob_col = rpm_col = None
                for j, val in enumerate(cols):
                    if "T_DPTH" in val or "DEPTH" in val or "MD" in val:
                        depth_col = j
                    if "WOB" in val:
                        wob_col = j
                    if "RPM" in val:
                        rpm_col = j
                if depth_col is not None and wob_col is not None and rpm_col is not None:
                    data = []
                    for _, row in df_data.iterrows():
                        md_v = row.iloc[depth_col]
                        w_v = row.iloc[wob_col]
                        r_v = row.iloc[rpm_col]
                        if pd.notna(md_v) and md_v != '':
                            try:
                                d = float(md_v)
                                w = float(w_v) if pd.notna(w_v) and w_v != '' else 0.0
                                if math.isnan(w): w = 0.0
                                r = float(r_v) if pd.notna(r_v) and r_v != '' else 0.0
                                if math.isnan(r): r = 0.0
                                data.append((d, w, r))
                            except:
                                continue
                    if data:
                        #prn1_content = f" Well: {well_name}\n MD WOB RPM\n" + "\n".join(f" {int(d)} {int(w)} {int(r)}" for d, w, r in data) + "\n"
                        # ── Better aligned format ────────────────────────────────────────
                        lines = []
                        lines.append(f"Well: {well_name}")
                        lines.append("")  # empty line after well name
                        lines.append("   MD     WOB     RPM")
                
                        for d, w, r in data:
                            # Right-align MD (width 6), WOB (width 6), RPM (width 6)
                            line = f"{int(d):6d} {int(w):6d} {int(r):6d}"
                            lines.append(line)
                
                        prn1_content = "\n".join(lines) + "\n"
        
        # ─── Process ASCII 5 (MD, ROP, TG, C1–C5) ───────────────────────────────
        if df_gas5 is not None:
            header_row_idx = None
            for i, row in df_gas5.iterrows():
                row_str = row.astype(str).str.upper().str.strip()
                if any("T_DPTH" in x or "DEPTH" in x or "MD" in x for x in row_str):
                    if any("ROP" in x for x in row_str) and any("C1" in x for x in row_str):
                        header_row_idx = i
                        break
            if header_row_idx is not None:
                data_start = header_row_idx + 2
                df_data = df_gas5.iloc[data_start:].copy()
                cols = df_gas5.iloc[header_row_idx].astype(str).str.upper().str.strip()
                depth_col = next((j for j, v in enumerate(cols) if "T_DPTH" in v or "DEPTH" in v or "MD" in v), None)
                rop_col = next((j for j, v in enumerate(cols) if "ROP" in v), None)
                tg_col = next((j for j, v in enumerate(cols) if "TG" in v or "T_GAS" in v), None)
                gas_cols = []
                for name in ["C1", "C2", "C3", "IC4", "NC4", "C5", "C4I", "C4N"]:
                    idx = next((j for j, v in enumerate(cols) if name in v), None)
                    if idx is not None:
                        gas_cols.append((name, idx))
                # Assume order C1 C2 C3 C4I C4N C5
                if depth_col is not None and rop_col is not None and tg_col is not None and len(gas_cols) >= 6:
                    data = []
                    for _, row in df_data.iterrows():
                        values = []
                        md_v = row.iloc[depth_col]
                        if pd.notna(md_v) and md_v != '':
                            try:
                                values.append(float(md_v))
                                rop_v = row.iloc[rop_col]
                                rop = float(rop_v) if pd.notna(rop_v) and rop_v != '' else 0.0
                                if math.isnan(rop): rop = 0.0
                                values.append(rop)
                                tg_v = row.iloc[tg_col]
                                tg = float(tg_v) if pd.notna(tg_v) and tg_v != '' else 0.0
                                if math.isnan(tg): tg = 0.0
                                values.append(tg)
                                for _, idx in gas_cols[:6]:  # take first 6
                                    v = row.iloc[idx]
                                    vv = float(v) if pd.notna(v) and v != '' else 0.0
                                    if math.isnan(vv): vv = 0.0
                                    values.append(vv)
                                data.append(values)
                            except (ValueError, TypeError):
                                continue
                    if data:
                        # prn5_content = f" Well: {well_name}\n MD ROP TG C1 C2 C3 C4I C4N C5\n" + "\n".join(f" {int(v[0])} {v[1]:.1f} {int(v[2])} {int(v[3])} {int(v[4])} {int(v[5])} {int(v[6])} {int(v[7])} {int(v[8])}" for v in data) + "\n"
                        lines = []
                        lines.append(f"Well:           {well_name}")
                        lines.append("")  # empty line
                        lines.append("   MD     ROP      TG      C1      C2      C3     C4I     C4N      C5")
            
                        for v in data:
                            # MD right-aligned width 6, ROP 1 decimal width 7, others integers width 7-8
                            line = (
                                f"{int(v[0]):6d} "          # MD
                                f"{v[1]:7.1f} "             # ROP
                                f"{int(v[2]):7d} "          # TG
                                f"{int(v[3]):7d} "          # C1
                                f"{int(v[4]):7d} "          # C2
                                f"{int(v[5]):7d} "          # C3
                                f"{int(v[6]):7d} "          # C4I
                                f"{int(v[7]):7d} "          # C4N
                                f"{int(v[8]):7d}"           # C5
                            )
                            lines.append(line)
                        
                        prn5_content = "\n".join(lines) + "\n"

    
    # ─── Previews & Downloads ────────────────────────────────────────────────
    # This block is now safely inside the tab
    if prn1_content or prn5_content:
        st.markdown("---")

        # ─── ASCII 1 Preview ─────────────────────────────────────────────────────
        if prn1_content:
            st.subheader("ASCII 1 PRN Preview (scroll to see full content - copy-paste ready)")
            st.caption("Scroll down to see the full content. Use Ctrl+F to search within the preview.")
        # Create a scrollable container with fixed height
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
                    {prn1_content.replace("\n", "<br>").replace(" ", "&nbsp;")}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            st.download_button(
                label="Download Mud Log Ascii 1.prn",
                data=prn1_content,
                file_name=f"{well_name} Mud Log Ascii 1.prn",
                mime="text/plain",
                key="ascii1_dl"
            )

        
        # ─── ASCII 5 Preview ─────────────────────────────────────────────────────
        if prn5_content:
            st.subheader("ASCII 5 PRN Preview (scroll to see full content - copy-paste ready)")
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
                    {prn5_content.replace("\n", "<br>").replace(" ", "&nbsp;")}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            st.download_button(
                label="Download Mud Log Ascii 5.prn",
                data=prn5_content,
                file_name=f"{well_name} Mud Log Ascii 5.prn",
                mime="text/plain",
                key="ascii5_dl"
            )

        # ─── Combined ZIP Download ───────────────────────────────────────────────
        if prn1_content and prn5_content:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(f"{well_name} Mud Log Ascii 1.prn", prn1_content)
                zf.writestr(f"{well_name} Mud Log Ascii 5.prn", prn5_content)
            zip_buffer.seek(0)
            st.download_button(
                label="Download ZIP (Ascii 1 & 5)",
                data=zip_buffer,
                file_name=f"{well_name} Mud Log Ascii 1 & 5.zip",
                mime="application/zip",
                key="ascii_zip_dl"
            )







# ────────────────────────────────────────────────
# 4. Mud & DRLG Parameters
# ────────────────────────────────────────────────
with tab_mud_drlg_params:
    st.header("Mud & Drilling Parameters")
    
    uploaded_file = st.file_uploader(
        "Upload Excel File (.xls or .xlsx) for Mud & Drilling Parameters",
        type=["xls", "xlsx"],
        key="mud_drlg_params_uploader"
    )
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        uploaded_file.seek(0)
        
        well_name = st.session_state.get('well_name', 'Unknown Well')
        
        drilling_prn = None
        mud_prn = None
        
        # ─── Load workbook ───────────────────────────────────────────────────────
        try:
            wb = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
            sheet_names = wb.sheet_names
            st.success("Loaded as modern .xlsx")
        except Exception:
            try:
                wb = pd.ExcelFile(io.BytesIO(file_bytes), engine="xlrd")
                sheet_names = wb.sheet_names
                st.warning("Loaded as legacy .xls (Excel 97-2003 format)")
            except Exception as e:
                st.error("Cannot read the file with openpyxl or xlrd.")
                st.error("Please open in Excel → Save As → .xlsx format and try again.")
                st.stop()
        
        # Well name fallback (if not already set)
        if well_name == 'Unknown Well':
            for sheet_name in sheet_names:
                try:
                    df_temp = pd.read_excel(wb, sheet_name=sheet_name, header=None, dtype=str)
                    for _, row in df_temp.iterrows():
                        for val in row:
                            if pd.notna(val) and isinstance(val, str) and "WELL:" in val.upper():
                                parts = val.upper().split("WELL:")
                                if len(parts) > 1:
                                    well_name = parts[1].strip().replace("\n", " ").strip()
                                    st.info(f"Well name detected: **{well_name}**")
                                    break
                        if well_name != "Unknown Well":
                            break
                except:
                    continue
                if well_name != "Unknown Well":
                    break
        
        # ─── Find sheets (flexible matching) ─────────────────────────────────────
        drilling_sheet = None
        mud_sheet = None
        for s in sheet_names:
            s_lower = s.lower().strip()
            if any(word in s_lower for word in ['drilling', 'drlg', 'drill', 'param', 'wob', 'rpm', 'spp']):
                drilling_sheet = s
            elif any(word in s_lower for word in ['mud', 'mw', 'vis', 'cl', 'mwt']):
                mud_sheet = s
        
        # ─── Helper function: format parameters in fixed-width columns ──────────
        def build_quoted_text(parts, label_width=10, value_width=14):
            """
            Builds a quoted string with fixed-width fields for each parameter.
            - label_width: width for label (WOB:, MWT:, etc.)
            - value_width: width for the value (right-aligned)
            
            Example output:
            "WOB:     1-10     RPM:     60-70     SPP:   630-820    GPM:      370      "
            """
            formatted = []
            i = 0
            while i < len(parts):
                part = str(parts[i]).strip()
                
                # Label detected
                if part.endswith(':') or part.upper() in ['WOB', 'RPM', 'SPP', 'GPM', 'MWT', 'VIS', 'CL', 'K']:
                    label = part
                    i += 1
                    value = ""
                    if i < len(parts):
                        value = str(parts[i]).strip()
                        i += 1
                    
                    # Format label left-aligned, value right-aligned
                    label_part = f"{label:<{label_width}}"
                    value_part = f"{value:>{value_width}}"
                    combined = label_part + value_part
                    formatted.append(combined)
                
                else:
                    # Standalone value or text
                    formatted.append(f"{part:>{value_width}}")
                    i += 1
            
            # Join with NO extra spaces (padding is already inside each field)
            return '"' + ''.join(formatted) + '"'
        
        
        # ─── Process Drilling Parameters ────────────────────────────────────────
        if drilling_sheet:
            try:
                df = pd.read_excel(wb, sheet_name=drilling_sheet, header=None, dtype=str, keep_default_na=False)
                st.success(f"Drilling sheet loaded: {drilling_sheet}")
                
                data = []
                for _, row in df.iterrows():
                    depth_v = None
                    text_parts = []
                    for val in row:
                        val_str = str(val).strip()
                        if depth_v is None and val_str and val_str.replace('.', '', 1).replace('-', '', 1).isdigit():
                            depth_v = val_str
                        elif val_str:
                            cleaned = val_str.replace('\n', ' ').replace('\r', ' ').strip()
                            if cleaned:
                                text_parts.append(cleaned)
                    
                    if depth_v and text_parts:
                        try:
                            d = int(float(depth_v))
                            quoted_text = build_quoted_text(text_parts, label_width=10, value_width=14)  # ← key line
                            data.append((d, quoted_text))
                        except:
                            continue
                
                if data:
                    lines = [f"Well: {well_name}"]
                    for d, quoted in data:
                        d2 = d + 20
                        line = f"{d:<15}{d2:<15}{quoted}"
                        lines.append(line)
                    drilling_prn = "\n".join(lines) + "\n"
                else:
                    st.warning("No valid drilling data found")
            except Exception as e:
                st.warning(f"Drilling sheet error: {e}")
        
        # ─── Process Mud Parameters ─────────────────────────────────────────────
        if mud_sheet:
            try:
                df = pd.read_excel(wb, sheet_name=mud_sheet, header=None, dtype=str, keep_default_na=False)
                st.success(f"Mud sheet loaded: {mud_sheet}")
                
                data = []
                for _, row in df.iterrows():
                    depth_v = None
                    text_parts = []
                    for val in row:
                        val_str = str(val).strip()
                        if depth_v is None and val_str and val_str.replace('.', '', 1).replace('-', '', 1).isdigit():
                            depth_v = val_str
                        elif val_str:
                            cleaned = val_str.replace('\n', ' ').replace('\r', ' ').strip()
                            if cleaned:
                                text_parts.append(cleaned)
                    
                    if depth_v and text_parts:
                        try:
                            d = int(float(depth_v))
                            quoted_text = build_quoted_text(text_parts, label_width=10, value_width=14)  # ← same width
                            data.append((d, quoted_text))
                        except:
                            continue
                
                if data:
                    lines = [f"Well: {well_name}"]
                    for d, quoted in data:
                        d2 = d + 20
                        line = f"{d:<15}{d2:<15}{quoted}"
                        lines.append(line)
                    mud_prn = "\n".join(lines) + "\n"
                else:
                    st.warning("No valid mud data found")
            except Exception as e:
                st.warning(f"Mud sheet error: {e}")
        
        # ─── Previews & Downloads ────────────────────────────────────────────────
        if drilling_prn or mud_prn:
            st.markdown("---")
            
            if drilling_prn:
                st.subheader("Drilling Parameters PRN Preview (scroll to see full content - copy-paste ready)")
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
                            font-family: 'Courier New', monospace;
                            font-size: 14px;
                            padding: 16px;
                            border-radius: 6px;
                            border: 1px solid #444;
                            white-space: pre;
                            line-height: 1.4;
                        ">
                        {drilling_prn.replace("\n", "<br>").replace(" ", "&nbsp;")}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                st.download_button(
                    label="Download Drilling Parameters .prn",
                    data=drilling_prn,
                    file_name=f"{well_name} Drilling Parameters.prn",
                    mime="text/plain",
                    key="drlg_dl"
                )
            
            if mud_prn:
                st.subheader("Mud Parameters PRN Preview (scroll to see full content - copy-paste ready)")
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
                            font-family: 'Courier New', monospace;
                            font-size: 14px;
                            padding: 16px;
                            border-radius: 6px;
                            border: 1px solid #444;
                            white-space: pre;
                            line-height: 1.4;
                        ">
                        {mud_prn.replace("\n", "<br>").replace(" ", "&nbsp;")}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                st.download_button(
                    label="Download Mud Parameters .prn",
                    data=mud_prn,
                    file_name=f"{well_name} Mud Parameters.prn",
                    mime="text/plain",
                    key="mud_dl"
                )
            
            if drilling_prn and mud_prn:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    if drilling_prn:
                        zf.writestr(f"{well_name} Drilling Parameters.prn", drilling_prn)
                    if mud_prn:
                        zf.writestr(f"{well_name} Mud Parameters.prn", mud_prn)
                zip_buffer.seek(0)
                
                st.download_button(
                    label="Download ZIP (Mud & Drilling)",
                    data=zip_buffer,
                    file_name=f"{well_name} Mud & Drilling Parameters.zip",
                    mime="application/zip",
                    key="mud_drlg_zip"
                )







# ────────────────────────────────────────────────
# 5. Mud Log DESC Comment (with sub-header for lithology types)
# ────────────────────────────────────────────────
with tab_desc_comment:
    #st.header("Mud Log Description Comment")
    st.header("Lithology Descriptions")
    #st.subheader("This tab is for preparing the Mud Log Description Comments for:")

    #lith_types = ["Clay", "Shale", "Sand", "SST", "SLT.ST", "LST", "Oil Shows"]
    #for lit in lith_types:
        #st.markdown(f"- **{lit}**")
    
    st.info("Upload the lithology Excel file to extract descriptions from SST, SH, LST, etc. sheets.")
    
    uploaded_file = st.file_uploader(
        "Upload Lithology Excel File (.xls or .xlsx)",
        type=["xls", "xlsx"],
        key="lithology_uploader"
    )
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        uploaded_file.seek(0)
        
        well_name = st.session_state.get('well_name', 'Unknown Well')
        
        lith_prns = {}  # lith_type -> prn_content
        
        # ─── Load workbook ───────────────────────────────────────────────────────
        try:
            wb = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
            sheet_names = wb.sheet_names
            st.success("Loaded as modern .xlsx")
        except Exception:
            try:
                wb = pd.ExcelFile(io.BytesIO(file_bytes), engine="xlrd")
                sheet_names = wb.sheet_names
                st.warning("Loaded as legacy .xls (Excel 97-2003 format)")
            except Exception as e:
                st.error("Cannot read the file.")
                st.stop()
        
        # Find well name if not already set
        if well_name == 'Unknown Well':
            for sheet_name in sheet_names:
                try:
                    df_temp = pd.read_excel(wb, sheet_name=sheet_name, header=None, dtype=str)
                    for _, row in df_temp.iterrows():
                        for val in row:
                            if pd.notna(val) and isinstance(val, str) and "WELL:" in val.upper():
                                parts = val.upper().split("WELL:")
                                if len(parts) > 1:
                                    well_name = parts[1].strip().replace("\n", " ").strip()
                                    st.info(f"Well name detected: **{well_name}**")
                                    break
                        if well_name != "Unknown Well":
                            break
                except:
                    continue
                if well_name != "Unknown Well":
                    break
        
        # ─── Define lithology types and keywords ─────────────────────────────────
        lith_keywords = {
            'SST': ['sst', 's.st'],
            'CLY': ['cly', 'clay'],
            'SLTST': ['sltst', 'slt.st', 'siltstone'],
            'SH': ['sh', 'shale'],
            'LST': ['lst', 'limestone'],
            'DOL': ['dol', 'dolomite'],
            'OIL SHOWS': ['oil shows', 'oil show', 'w/'],
            'SD': ['sd', 'sand']
        }
        
        # ─── Find and process lithology sheets ───────────────────────────────────
        for lith_type, keywords in lith_keywords.items():
            found_sheet = None
            for s in sheet_names:
                s_lower = s.lower().strip().replace(' ', '').replace('.', '')
                if any(kw in s_lower for kw in keywords):
                    found_sheet = s
                    break
            
            if found_sheet:
                try:
                    df = pd.read_excel(wb, sheet_name=found_sheet, header=None, dtype=str, keep_default_na=False)
                    st.success(f"{lith_type} sheet loaded: {found_sheet}")
                    
                    # Find depth and description columns
                    depth_col = None
                    desc_col = None
                    for i, row in df.iterrows():
                        for j, val in enumerate(row):
                            val_str = str(val).strip()
                            if val_str.replace('.', '', 1).isdigit() and depth_col is None:
                                depth_col = j
                                if j + 1 < len(row):
                                    desc_col = j + 1
                                break
                        if depth_col is not None:
                            break
                    
                    if depth_col is not None and desc_col is not None:
                        data = []
                        for _, row in df.iterrows():
                            depth_v = row.iloc[depth_col]
                            desc_v = row.iloc[desc_col]
                            if pd.notna(depth_v) and str(depth_v).strip().replace('.', '', 1).isdigit() and pd.notna(desc_v) and str(desc_v).strip():
                                try:
                                    d = int(float(depth_v))
                                    desc = str(desc_v).replace('\n', ' ').replace('\r', ' ').strip()
                                    if desc:
                                        data.append((d, desc))
                                except:
                                    continue
                        
                        if data:
                            lines = [f"Well: {well_name}"]
                            for d, desc in data:
                                d2 = d + 10
                                line = f"{d:<15}{d2:<15}\"{desc}\""
                                lines.append(line)
                            lith_prns[lith_type] = "\n".join(lines) + "\n"
                        else:
                            st.warning(f"No valid depth/description data found in {found_sheet}")
                    else:
                        st.warning(f"Could not find depth/description columns in {found_sheet}")
                except Exception as e:
                    st.warning(f"Error reading {found_sheet}: {e}")
            else:
                st.info(f"No sheet found for {lith_type}")
        
        # ─── Previews & Downloads ────────────────────────────────────────────────
        if lith_prns:
            st.markdown("---")
            
            for lith_type, lith_prn in lith_prns.items():
                st.subheader(f"{lith_type} Description PRN Preview (scroll to see full content - copy-paste ready)")
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
                        {lith_prn.replace("\n", "<br>").replace(" ", "&nbsp;")}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                st.download_button(
                    label=f"Download {lith_type} Description .prn",
                    data=lith_prn,
                    file_name=f"{well_name} {lith_type} Description.prn",
                    mime="text/plain",
                    key=f"lith_download_{lith_type.lower().replace(' ', '_')}"
                )
            
            # ZIP all lithology PRNs
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for lith_type, lith_prn in lith_prns.items():
                    zf.writestr(f"{well_name} {lith_type} Description.prn", lith_prn)
            zip_buffer.seek(0)
            
            st.download_button(
                label="Download ZIP (All Lithology Descriptions)",
                data=zip_buffer,
                file_name=f"{well_name} All Lithology Descriptions.zip",
                mime="application/zip",
                key="lith_zip_all"
            )
        else:
            st.info("No lithology descriptions found in the uploaded file.")




# ────────────────────────────────────────────────
# 6. Oil Shows Intensity
# ────────────────────────────────────────────────
with tab_oil_shows:
    st.header("Oil Shows Intensity")
    st.info("Oil shows intensity preparation coming soon. Likely includes depth, intensity level, fluorescence, etc.")
