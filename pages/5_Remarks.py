import streamlit as st
import pandas as pd
import io
import zipfile
from PIL import Image, ImageDraw, ImageFont
from textwrap import wrap


st.sidebar.markdown("---")
st.sidebar.header("Global Settings")

well_name_input = st.sidebar.text_input(
    "Well Name",
    value=st.session_state.get('well_name', 'ABRAR-84'),
    key="well_name_input"
)

if st.sidebar.button("Apply Well Name", type="primary"):
    if well_name_input.strip():
        st.session_state.well_name = well_name_input.strip()
        # Place success message here - it will show until next rerun or page change
        st.sidebar.success(f"Well Name: **{st.session_state.well_name}** applied ✅")
       # st.rerun()  # optional - removes it faster but refreshes the app
    else:
        st.sidebar.error("Please enter a well name")
# Now every tab can use st.session_state.well_name


# ─── Sidebar Copyright / Watermark Footer (visible on ALL pages) ──────────
#st.sidebar.markdown("---")  # separator line above the copyright
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style="
        text-align: center; 
        color: #888; 
        font-size: 0.85rem; 
        padding: 12px 8px; 
        margin-top: auto;
        border-top: 1px solid #444;
    ">
        © 2026 Ahmed Samy<br>
        Composite Log Data Preparation App<br>
        Proprietary Software – All Rights Reserved<br>
        Private Property – For internal use only<br>
        Copyright protected – Do not distribute
    </div>
    """,
    unsafe_allow_html=True
)



st.set_page_config(page_title="Petrel Composite Log Prep", layout="wide", page_icon="🛢️")  # optional)
                   
st.title("Petrel Composite Log Data Preparation App")
st.markdown("### Tab 5: Remarks (Before 10 & After 10)")




#st.title("5 - Remarks")

# ────────────────────────────────────────────────
#   Data storage
# ────────────────────────────────────────────────
# Data storage
if 'remarks_data' not in st.session_state:
    st.session_state.remarks_data = pd.DataFrame(columns=["No.", "Remark", "Depth In"])

# Use session state keys to clear inputs after adding
if 'remark_text' not in st.session_state:
    st.session_state.remark_text = ""
if 'remark_depth' not in st.session_state:
    st.session_state.remark_depth = 0
    
# ────────────────────────────────────────────────
#   Add new remark form
# ────────────────────────────────────────────────
# ... (keep all previous imports and data storage code) ...

# Add new remark form
st.subheader("Add Remark")

col_text, col_depth = st.columns([5, 2])

with col_text:
    remark_text = st.text_area(
        "Remark Text (press Enter for new line)",
        value=st.session_state.get('remark_text', ""),
        height=140,                     # taller area for comfort
        placeholder="Gas System Tested\n& Calibrated OK\n(or any multiline text)",
        key="remark_text_area"
    )

with col_depth:
    depth_in = st.number_input(
        "Depth In (ft)",
        min_value=0,
        step=1,
        value=st.session_state.get('remark_depth', 0),
        key="remark_depth_input"
    )

if st.button("➕ Add Remark", type="primary"):
    if remark_text.strip() and depth_in >= 0:
        next_no = 1 if st.session_state.remarks_data.empty else int(st.session_state.remarks_data["No."].max()) + 1
        
        new_row = pd.DataFrame({
            "No.": [next_no],
            "Remark": [remark_text],          # ← keep original newlines
            "Depth In": [depth_in]
        })
        st.session_state.remarks_data = pd.concat(
            [st.session_state.remarks_data, new_row],
            ignore_index=True
        )
        
        # Reset inputs
        st.session_state.remark_text = ""
        st.session_state.remark_depth = 0
        st.success(f"Added Remark #{next_no} @ {depth_in} ft")
        st.rerun()
    else:
        st.warning("Please enter remark text and depth")

# ... (keep the current entries table and remove logic) ...

# ────────────────────────────────────────────────
#   Current entries + delete
# ────────────────────────────────────────────────
st.subheader("Current Remarks")

if st.session_state.remarks_data.empty:
    st.info("No remarks added yet. Use the form above.")
else:
    st.dataframe(
        st.session_state.remarks_data,
        use_container_width=True,
        hide_index=False
    )

    to_remove = st.multiselect(
        "Select remark(s) to remove",
        options=st.session_state.remarks_data.index.tolist(),
        format_func=lambda i: f"#{st.session_state.remarks_data.loc[i, 'No.']} – {st.session_state.remarks_data.loc[i, 'Remark'][:50]}... @ {st.session_state.remarks_data.loc[i, 'Depth In']}'"
    )

    if st.button("🗑️ Remove selected", type="secondary"):
        if to_remove:
            st.session_state.remarks_data = st.session_state.remarks_data.drop(to_remove).reset_index(drop=True)
            st.session_state.remarks_data["No."] = range(1, len(st.session_state.remarks_data) + 1)
            st.success(f"Removed {len(to_remove)} remark(s)")
            st.rerun()

# The rest of your code (generate_remark_png + previews/downloads) stays the same
# ... paste your current generate_remark_png and preview/download section here ...
# ────────────────────────────────────────────────
#   PNG generation function
# ────────────────────────────────────────────────
# Updated PNG generation – preserves line breaks
def generate_remark_png(no, remark_text, depth_in):
    width, height = 3449, 792
    image = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Load font (DejaVu fallback – reliable on cloud)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 220)
    except:
        font = ImageFont.load_default()

    # Use the raw text with \n preserved – no extra wrapping needed
    # (you can still add manual \n by pressing Enter)
    text_block = remark_text

    # Dynamically reduce font size if needed
    font_size = 220
    while font_size > 40:
        bbox = draw.multiline_textbbox((0, 0), text_block, font=font, align="center")
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        if text_w <= width * 0.90 and text_h <= height * 0.80:
            break

        font_size -= 10
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", font_size)
        except:
            pass

    # Center
    x = (width - text_w) // 2
    y = (height - text_h) // 2 - 20  # slight upward shift

    # Draw red, bold, multiline text
    draw.multiline_text(
        (x, y),
        text_block,
        fill=(255, 0, 0, 255),  # red
        font=font,
        align="center",
        spacing=20              # controls vertical spacing between lines
    )

    image.info['dpi'] = (330, 330)
    image = image.convert('P', palette=Image.ADAPTIVE, colors=256)

    buf = io.BytesIO()
    image.save(buf, format="PNG", dpi=(330, 330))
    buf.seek(0)
    return buf.getvalue()

# ... (keep the rest: previews, downloads, ZIP, etc.) ...

# ────────────────────────────────────────────────
#   Previews & Downloads
# ────────────────────────────────────────────────
st.subheader("Previews & Downloads")

if not st.session_state.remarks_data.empty:
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        for i, row in st.session_state.remarks_data.iterrows():
            no = row["No."]
            remark = row["Remark"]
            depth = int(row["Depth In"])

            png_bytes = generate_remark_png(no, remark, depth)

            st.image(png_bytes, width=300, caption=f"Remark #{no} @ {depth}'")

            d_minus = int(depth) - 10
            d_plus = int(depth) + 10
            fname = f"Remark-{int(no)}. ({d_minus} - {d_plus}).png"

            st.download_button(
                f"Download {fname}",
                png_bytes,
                file_name=fname,
                mime="image/png",
                key=f"remark_dl_{i}"
            )

            zf.writestr(fname, png_bytes)

    zip_buf.seek(0)
    st.download_button(
        "Download all Remarks as ZIP",
        zip_buf.getvalue(),
        file_name="remarks_all.zip",
        mime="application/zip"
    )
else:
    st.info("Add at least one remark to generate previews/downloads.")
