import streamlit as st
import pandas as pd
import io
import zipfile
from PIL import Image, ImageDraw, ImageFont
from textwrap import wrap

st.title("5 - Remarks")

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
st.subheader("Add Remark")

col_text, col_depth = st.columns([5, 2])

with col_text:
    remark_text = st.text_area(
        "Remark Text (press Enter for new line)",
        value=st.session_state.remark_text,
        height=120,
        placeholder="Add one remark\nor two remarks\n(or any multi-line text)",
        key="remark_text_area"
    )

with col_depth:
    depth_in = st.number_input(
        "Depth In (ft)",
        min_value=0,
        step=1,
        value=st.session_state.remark_depth,
        key="remark_depth_input"
    )

if st.button("➕ Add Remark", type="primary"):
    if remark_text.strip() and depth_in >= 0:
        next_no = 1 if st.session_state.remarks_data.empty else int(st.session_state.remarks_data["No."].max()) + 1
        
        new_row = pd.DataFrame({
            "No.": [next_no],
            "Remark": [remark_text],
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
def generate_remark_png(no, remark_text, depth_in):
    width, height = 3449, 792
    image = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)

    # ─── Load font from GitHub repo folder ───
    font = None
    font_size = 240  # starting size

    try:
        # Path relative to the script (works on Streamlit Cloud)
        font_path = "Fonts/Times_New_Roman_Bold.ttf"
        font = ImageFont.truetype(font_path, font_size)
    except Exception as e:
        st.warning(f"Could not load custom font: {e}")
        # Fallback to default (small)
        font = ImageFont.load_default()
        font_size = 80

    # Wrap long text
    from textwrap import wrap
    wrapped_lines = wrap(remark_text, width=55)  # adjust 55 to change wrap length
    text_block = "\n".join(wrapped_lines)

    # Reduce font size until text fits nicely
    while font_size > 40:
        bbox = draw.multiline_textbbox((0, 0), text_block, font=font, align="center")
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        if text_w <= width * 0.90 and text_h <= height * 0.80:
            break

        font_size -= 10
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            pass  # keep current font if resize fails

    # Center the text
    x = (width - text_w) // 2
    y = (height - text_h) // 2 - 25  # slight upward adjustment

    # Draw **red, bold, centered** text
    draw.multiline_text(
        (x, y),
        text_block,
        fill=(255, 0, 0, 255),  # red
        font=font,
        align="center",
        spacing=18              # line spacing
    )

    # DPI & 8-bit
    image.info['dpi'] = (330, 330)
    image = image.convert('P', palette=Image.ADAPTIVE, colors=256)

    buf = io.BytesIO()
    image.save(buf, format="PNG", dpi=(330, 330))
    buf.seek(0)
    return buf.getvalue()

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
