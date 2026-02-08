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
if 'remarks_data' not in st.session_state:
    st.session_state.remarks_data = pd.DataFrame(columns=["No.", "Remark", "Depth In"])

# ────────────────────────────────────────────────
#   Add new remark form
# ────────────────────────────────────────────────
st.subheader("Add new Remark")

cols = st.columns([4, 2, 1])
with cols[0]:
    remark_text = st.text_input(
        "Remark Text",
        value="",
        key="new_remark_text",
        placeholder="Enter remark text here..."
    )

with cols[1]:
    depth_in = st.number_input(
        "Depth In (ft)",
        min_value=0,
        step=1,
        value=0,
        key="new_remark_depth"
    )

if st.button("➕ Add Remark", type="primary", use_container_width=True):
    if remark_text.strip() and depth_in >= 0:
        next_no = int(st.session_state.remarks_data["No."].max()) + 1 if not st.session_state.remarks_data.empty else 1
        new_row = pd.DataFrame({
            "No.": [next_no],
            "Remark": [remark_text],
            "Depth In": [depth_in]
        })
        st.session_state.remarks_data = pd.concat([st.session_state.remarks_data, new_row], ignore_index=True)
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
        format_func=lambda i: f"Remark #{st.session_state.remarks_data.loc[i, 'No.']} - {st.session_state.remarks_data.loc[i, 'Remark'][:50]}... @ {st.session_state.remarks_data.loc[i, 'Depth In']}'"
    )

    if st.button("🗑️ Remove selected", type="secondary"):
        if to_remove:
            st.session_state.remarks_data = st.session_state.remarks_data.drop(to_remove).reset_index(drop=True)
            # Renumber No.
            st.session_state.remarks_data["No."] = range(1, len(st.session_state.remarks_data) + 1)
            st.success(f"Removed {len(to_remove)} remark(s)")
            st.rerun()

# ────────────────────────────────────────────────
#   PNG generation function
# ────────────────────────────────────────────────
def generate_remark_png(no, remark_text, depth_in):
    width, height = 3449, 792
    image = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Try to load Times New Roman Bold
    try:
        # Common path on many systems / Streamlit Cloud
        font_path = "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Bold.ttf"
        font_size = 220  # starting size - large like your example
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        try:
            # Fallback: DejaVu Serif Bold (usually available)
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()
            font_size = 80  # much smaller fallback

    # Wrap long text
    from textwrap import wrap
    wrapped_lines = wrap(remark_text, width=60)  # adjust number for desired line length
    text_block = "\n".join(wrapped_lines)

    # Dynamically reduce font size until it fits nicely
    while True:
        bbox = draw.multiline_textbbox((0, 0), text_block, font=font, align="center")
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        if text_w <= width * 0.92 and text_h <= height * 0.88:
            break

        font_size -= 10
        if font_size < 60:
            break
        font = ImageFont.truetype(font_path, font_size) if 'font_path' in locals() else font

    # Center the text block
    x = (width - text_w) // 2
    y = (height - text_h) // 2 - 20  # slight upward shift to match visual balance

    # Draw bold red text
    draw.multiline_text(
        (x, y),
        text_block,
        fill=(255, 0, 0, 255),  # pure red
        font=font,
        align="center",
        spacing=15  # line spacing
    )

    # Set DPI and convert to 8-bit
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
