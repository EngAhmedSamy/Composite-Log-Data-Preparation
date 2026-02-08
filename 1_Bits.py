import streamlit as st
import pandas as pd
import numpy as np
import io
import zipfile
from PIL import Image, ImageDraw, ImageFont
import cv2
import pytesseract
import re

st.set_page_config(page_title="Petrel Composite Log Prep", layout="wide", page_icon="🛢️")  # optional)
                   
st.title("Petrel Composite Log Data Preparation App")
st.markdown("### Tab 1: Bits (After 30 & After 70)")
              
#st.title("1 - Bits (After 30 & After 70)")

# ────────────────────────────────────────────────
#   Icons (from repo + optional override)
# ────────────────────────────────────────────────
bit_sizes = ["8.5\"", "12.25\"", "17.5\""]

if 'bit_icons' not in st.session_state:
    st.session_state.bit_icons = {}

for size in bit_sizes:
    if size not in st.session_state.bit_icons:
        fname = size.replace('"', '') + ".png"  # 17.5" → 17.5.png
        try:
            with open(f"assets/bits/{fname}", "rb") as f:
                st.session_state.bit_icons[size] = f.read()
        except FileNotFoundError:
            pass

with st.expander("Override bit icons (optional)"):
    for size in bit_sizes:
        f = st.file_uploader(f"Replace icon for {size}", type=["png","jpg"], key=f"bit_up_{size}")
        if f is not None:
            st.session_state.bit_icons[size] = f.getvalue()
            st.success(f"{size} icon updated")

# ────────────────────────────────────────────────
# Section: Upload mud log file (PDF or image) for OCR
# ────────────────────────────────────────────────
mud_log = st.file_uploader("Upload Mud Log File (PDF or Image for OCR extraction)", type=["pdf", "png", "jpg", "jpeg"])
if mud_log:
    try:
        file_bytes = mud_log.getvalue()
        file_type = mud_log.type
        images = []

        if 'pdf' in file_type.lower():
            from pdf2image import convert_from_bytes
            pil_images = convert_from_bytes(file_bytes)
            images = [cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR) for pil_img in pil_images]
        else:
            img_array = np.frombuffer(file_bytes, np.uint8)
            images = [cv2.imdecode(img_array, cv2.IMREAD_COLOR)]

        # OCR on each image/page
        text = ''
        for img in images:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            text += pytesseract.image_to_string(thresh) + '\n'

        # Parse text into data
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        parsed_bits = []
        for line in lines:
            parts = re.split(r'\s+', line)
            if len(parts) >= 7:
                try:
                    bit_no = int(parts[0])
                    size = parts[4]  # e.g., 17.5"
                    depth_in = int(parts[6])
                    parsed_bits.append({"Bit Number": bit_no, "Size": size, "Depth In": depth_in})
                except (ValueError, IndexError):
                    pass
        
        if parsed_bits:
            new_df = pd.DataFrame(parsed_bits)
            st.session_state.bits_data = pd.concat([st.session_state.bits_data, new_df]).drop_duplicates().reset_index(drop=True)
            st.success(f"Extracted {len(parsed_bits)} bits from mud log!")
        else:
            st.warning("No data extracted. Check file quality or enter manually.")
    except Exception as e:
        st.error(f"Processing error: {e}")

# ────────────────────────────────────────────────
#   Data storage
# ────────────────────────────────────────────────
if 'bits_data' not in st.session_state:
    st.session_state.bits_data = pd.DataFrame(columns=["Bit Number", "Size", "Depth In"])


# ────────────────────────────────────────────────
#   Add new bit form
# ────────────────────────────────────────────────
st.subheader("Add new Bit")

cols = st.columns([1.2, 2.5, 1.8, 1])
with cols[0]:
    bit_no = st.number_input(
        "Bit #",
        min_value=1,
        step=1,
        value=None,
        key="new_bit_no"
    )

with cols[1]:
    bit_size = st.selectbox(
        "Bit Size",
        options=bit_sizes,
        index=None,
        placeholder="Select size...",
        key="new_bit_size"
    )

with cols[2]:
    depth_in = st.number_input(
        "Depth In (ft)",
        min_value=0,
        step=1,
        value=None,
        key="new_bit_depth"
    )

if st.button("➕ Add Bit", type="primary", use_container_width=True):
    if bit_no is not None and bit_size and depth_in is not None:
        new_row = pd.DataFrame({
            "Bit Number": [int(bit_no)],
            "Size": [bit_size],
            "Depth In": [int(depth_in)]
        })
        st.session_state.bits_data = pd.concat(
            [st.session_state.bits_data, new_row],
            ignore_index=True
        )
        st.success(f"Added Bit #{bit_no} - {bit_size} @ {depth_in} ft")
        st.rerun()
    else:
        st.warning("Please fill all three fields")


# ────────────────────────────────────────────────
#   Show current bits + delete
# ────────────────────────────────────────────────
st.subheader("Current Bits")

if st.session_state.bits_data.empty:
    st.info("No bits added yet. Use the form above.")
else:
    st.dataframe(
        st.session_state.bits_data,
        use_container_width=True,
        hide_index=False
    )

    to_remove = st.multiselect(
        "Select bit(s) to remove",
        options=st.session_state.bits_data.index.tolist(),
        format_func=lambda i: f"Bit {st.session_state.bits_data.loc[i, 'Bit Number']} - {st.session_state.bits_data.loc[i, 'Size']} @ {st.session_state.bits_data.loc[i, 'Depth In']}'"
    )

    if st.button("🗑️ Remove selected", type="secondary"):
        if to_remove:
            st.session_state.bits_data = st.session_state.bits_data.drop(to_remove).reset_index(drop=True)
            st.success(f"Removed {len(to_remove)} bit(s)")
            st.rerun()


# ────────────────────────────────────────────────
#   PNG generation function (your previous version)
# ────────────────────────────────────────────────
def generate_bit_png(bit_no, size, depth_in, icon_bytes):
    width, height = 299, 598
    image = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)

    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
        big_font = ImageFont.truetype(font_path, 52)
        size_font = ImageFont.truetype(font_path, 46)
        depth_font = ImageFont.truetype(font_path, 72)
    except:
        big_font = ImageFont.load_default()
        size_font = ImageFont.load_default()
        depth_font = ImageFont.load_default()

    # Top: BIT #1,
    top_text = f"BIT #{int(bit_no)},"
    bbox = draw.textbbox((0, 0), top_text, font=big_font)
    text_w = bbox[2] - bbox[0]
    draw.text(((width - text_w) // 2, 25), top_text, fill="black", font=big_font)

    # Size with underline
    size_text = f"{size.replace('\"', '')}''"
    bbox_size = draw.textbbox((0, 0), size_text, font=size_font)
    size_w = bbox_size[2] - bbox_size[0]
    x_size = (width - size_w) // 2
    y_size = 90
    draw.text((x_size, y_size), size_text, fill="black", font=size_font)

    #underline_y = y_size + 48
    #draw.line([(x_size - 10, underline_y), (x_size + size_w + 10, underline_y)], fill="black", width=5)

        # Icon
    if icon_bytes:
        icon = Image.open(io.BytesIO(icon_bytes))
        target_w = int(width * 0.82)
        aspect = icon.height / icon.width
        target_h = int(target_w * aspect)
        icon = icon.resize((target_w, target_h), Image.LANCZOS)
        icon_x = (width - target_w) // 2
        
        icon_y = 200   # ← you can adjust this number higher/lower # default position for all bits
        
        # Special adjustment only for 17.5" bit
        if size == "17.5\"":
            icon_y = 185   # ← ← ← CHANGE THIS VALUE to control height for 17.5" only
        
        image.paste(icon, (icon_x, icon_y), icon if icon.mode == 'RGBA' else None)

    # Bottom depth
    bottom_text = f"{int(depth_in)}'"
    bbox = draw.textbbox((0, 0), bottom_text, font=depth_font)
    text_w = bbox[2] - bbox[0]
    draw.text(((width - text_w) // 2, height - 110), bottom_text, fill="black", font=depth_font)

    image.info['dpi'] = (150, 150)
    buf = io.BytesIO()
    image.save(buf, format="PNG", dpi=(150, 150))
    buf.seek(0)
    return buf.getvalue()


# ────────────────────────────────────────────────
#   Previews & Downloads
# ────────────────────────────────────────────────
st.subheader("Previews & Downloads")

if not st.session_state.bits_data.empty:
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        for i, row in st.session_state.bits_data.iterrows():
            bit_no = row["Bit Number"]
            size = row["Size"]
            depth = row["Depth In"]

            if pd.isna(bit_no) or pd.isna(size) or pd.isna(depth):
                continue

            icon_bytes = st.session_state.bit_icons.get(size)
            if not icon_bytes:
                st.warning(f"No icon for size {size} — skipping Bit {bit_no}")
                continue

            png_bytes = generate_bit_png(bit_no, size, depth, icon_bytes)

            st.image(png_bytes, width=140, caption=f"Bit {bit_no} - {size} @ {depth}'")

            d30 = int(depth) + 30
            d70 = int(depth) + 70
            safe_size = size.replace('"', '')
            fname = f"Bit {int(bit_no)}. ({d30} - {d70}).png"

            st.download_button(
                f"Download {fname}",
                png_bytes,
                file_name=fname,
                mime="image/png",
                key=f"bit_dl_{i}"
            )

            zf.writestr(fname, png_bytes)

    zip_buf.seek(0)
    st.download_button(
        "Download all Bits as ZIP",
        zip_buf.getvalue(),
        file_name="bits_all.zip",
        mime="application/zip"
    )
else:
    st.info("Add at least one bit above to generate previews/downloads.")



