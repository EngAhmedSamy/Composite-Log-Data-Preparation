import streamlit as st
import pandas as pd
import io
import zipfile
from PIL import Image

st.title("Tab 7 - Faults")

# Sub-tabs
tab_symbol, tab_comments = st.tabs(["Fault Symbol", "Fault Comments"])

with tab_symbol:
    # Data storage
    if 'fault_symbol_data' not in st.session_state:
        st.session_state.fault_symbol_data = pd.DataFrame(columns=["No.", "Type", "Depth In"])

    # Add new fault symbol
    st.subheader("Add Fault Symbol")

    col_type, col_depth = st.columns([3, 2])
    with col_type:
        fault_type = st.selectbox(
            "Fault Type",
            options=["Between FMs.", "Within FMs."],
            index=None,
            placeholder="Select type...",
            key="new_fault_type"
        )

    with col_depth:
        depth_in = st.number_input(
            "Depth In (ft)",
            min_value=0,
            step=1,
            value=0,
            key="new_fault_depth"
        )

    if st.button("➕ Add Fault Symbol", type="primary"):
        if fault_type and depth_in >= 0:
            next_no = 1 if st.session_state.fault_symbol_data.empty else int(st.session_state.fault_symbol_data["No."].max()) + 1
            new_row = pd.DataFrame({
                "No.": [next_no],
                "Type": [fault_type],
                "Depth In": [depth_in]
            })
            st.session_state.fault_symbol_data = pd.concat([st.session_state.fault_symbol_data, new_row], ignore_index=True)
            st.success(f"Added Fault #{next_no} - {fault_type} @ {depth_in} ft")
            st.rerun()
        else:
            st.warning("Please select type and enter depth")

    # Current entries + delete
    st.subheader("Current Fault Symbols")

    if st.session_state.fault_symbol_data.empty:
        st.info("No fault symbols added yet.")
    else:
        st.dataframe(
            st.session_state.fault_symbol_data,
            use_container_width=True,
            hide_index=False
        )

        to_remove = st.multiselect(
            "Select to remove",
            options=st.session_state.fault_symbol_data.index.tolist(),
            format_func=lambda i: f"#{st.session_state.fault_symbol_data.loc[i, 'No.']} - {st.session_state.fault_symbol_data.loc[i, 'Type']} @ {st.session_state.fault_symbol_data.loc[i, 'Depth In']}'"
        )

        if st.button("🗑️ Remove selected", type="secondary"):
            if to_remove:
                st.session_state.fault_symbol_data = st.session_state.fault_symbol_data.drop(to_remove).reset_index(drop=True)
                st.session_state.fault_symbol_data["No."] = range(1, len(st.session_state.fault_symbol_data) + 1)
                st.success(f"Removed {len(to_remove)} fault(s)")
                st.rerun()

    # PNG generation function
    def generate_fault_png(no, fault_type, depth_in):
        width, height = 156, 32
        image = Image.new('RGBA', (width, height), (255, 255, 255, 255))

        # Load symbol from GitHub repo
        fname = "Between_FMs._Fault.png" if fault_type == "Between FMs." else "Within_FMs._Fault.png"
        try:
            symbol = Image.open(f"assets/Faults/{fname}").convert("RGBA")
            # Resize to exact specs
            symbol = symbol.resize((width, height), Image.LANCZOS)
            image.paste(symbol, (0, 0), symbol)
        except Exception as e:
            st.warning(f"Could not load fault symbol: {e}")
            # Fallback: draw simple red line
            draw = ImageDraw.Draw(image)
            draw.line((0, height//2, width, height//2), fill=(255,0,0,255), width=5)

        image.info['dpi'] = (96, 96)

        buf = io.BytesIO()
        image.save(buf, format="PNG", dpi=(96, 96))
        buf.seek(0)
        return buf.getvalue()

    # Previews & Downloads
    st.subheader("Previews & Downloads")

    if not st.session_state.fault_symbol_data.empty:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            for i, row in st.session_state.fault_symbol_data.iterrows():
                no = row["No."]
                fault_type = row["Type"]
                depth = int(row["Depth In"])

                png_bytes = generate_fault_png(no, fault_type, depth)

                st.image(png_bytes, width=150, caption=f"Fault #{no} - {fault_type} @ {depth}'")

                d_min = depth - 5
                d_max = depth + 5
                fname = f"Fault-{int(no)}. ({d_min} - {d_max}).png"

                st.download_button(
                    f"Download {fname}",
                    png_bytes,
                    file_name=fname,
                    mime="image/png",
                    key=f"dl_fault_{i}"
                )

                zf.writestr(fname, png_bytes)

        zip_buf.seek(0)
        st.download_button(
            "Download All as ZIP",
            zip_buf.getvalue(),
            "faults_all.zip",
            mime="application/zip"
        )
    else:
        st.info("Add at least one fault symbol to generate previews/downloads.")




with tab_comments:
    # Data storage
    if 'fault_comments_data' not in st.session_state:
        st.session_state.fault_comments_data = pd.DataFrame(columns=["No.", "Comment", "Depth In"])

    # Add new fault comment
    st.subheader("Add Fault Comment")

    col_comment, col_depth = st.columns([5, 2])
    with col_comment:
        fault_comment = st.text_area(
            "Fault Comment (multiline OK)",
            height=120,
            placeholder="Enter fault comment here...",
            key="new_fault_comment"
        )

    with col_depth:
        depth_in = st.number_input(
            "Depth In (ft)",
            min_value=0,
            step=1,
            value=0,
            key="new_fault_comment_depth"
        )

    if st.button("➕ Add Comment", type="primary"):
        if fault_comment.strip() and depth_in >= 0:
            next_no = 1 if st.session_state.fault_comments_data.empty else int(st.session_state.fault_comments_data["No."].max()) + 1
            new_row = pd.DataFrame({
                "No.": [next_no],
                "Comment": [fault_comment],
                "Depth In": [depth_in]
            })
            st.session_state.fault_comments_data = pd.concat([st.session_state.fault_comments_data, new_row], ignore_index=True)
            st.success(f"Added Comment #{next_no} @ {depth_in} ft")
            st.rerun()
        else:
            st.warning("Please enter comment and depth")

    # Current entries + delete
    st.subheader("Current Fault Comments")

    if st.session_state.fault_comments_data.empty:
        st.info("No comments added yet.")
    else:
        st.dataframe(
            st.session_state.fault_comments_data,
            use_container_width=True,
            hide_index=False
        )

        to_remove = st.multiselect(
            "Select to remove",
            options=st.session_state.fault_comments_data.index.tolist(),
            format_func=lambda i: f"#{st.session_state.fault_comments_data.loc[i, 'No.']} – {st.session_state.fault_comments_data.loc[i, 'Comment'][:40]}... @ {st.session_state.fault_comments_data.loc[i, 'Depth In']}'",
            key="multiselect_fault_comments_remove"  # also give unique key to multiselect
        )

        if st.button("🗑️ Remove selected", type="secondary", key="btn_remove_fault_comments"):
            if to_remove:
                st.session_state.fault_comments_data = st.session_state.fault_comments_data.drop(to_remove).reset_index(drop=True)
                st.session_state.fault_comments_data["No."] = range(1, len(st.session_state.fault_comments_data) + 1)
                st.success(f"Removed {len(to_remove)} comment(s)")
                st.rerun()

    # Preview and Download PRN
    st.subheader("PRN Preview & Download")

    if not st.session_state.fault_comments_data.empty:
        output = io.StringIO()
        well_name = st.session_state.get('well_name', 'Well Name')
        output.write(f"Well: {well_name}\n\n")

        for _, row in st.session_state.fault_comments_data.iterrows():
            depth = int(row["Depth In"])
            comment = row["Comment"]
            line = f"{depth - 5} {depth + 5} \"{comment}\\n\""
            output.write(line + "\n")

        # Preview
        st.code(output.getvalue(), language="text")

        # Download
        st.download_button(
            label="Download Description Comment Fault.prn",
            data=output.getvalue(),
            file_name="Description Comment Fault.prn",
            mime="text/plain"
        )
    else:
        st.info("No data to preview/download.")
