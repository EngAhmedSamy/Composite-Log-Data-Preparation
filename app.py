import streamlit as st
import pandas as pd
import numpy as np
import io
import zipfile
from PIL import Image, ImageDraw, ImageFont
import cv2
import pytesseract
import re

st.title("Petrel Composite Log Data Preparation App")
st.markdown("### Tab 1: 1-Bits (After 30 & After 70)")

# Session state for data
if 'bits_data' not in st.session_state:
    st.session_state.bits_data = pd.DataFrame(columns=["Bit Number", "Size", "Depth In"])

# Icons dictionary (size to uploaded file bytes)
if 'icons' not in st.session_state:
    st.session_state.icons = {}

# Section: Upload icons for common sizes
with st.expander("Upload Bit Icons (per size)"):
    common_sizes = ["17.5\"", "12.25\"", "8.5\""]
    for size in common_sizes:
        uploaded_icon = st.file_uploader(f"Upload icon for {size} (PNG/JPG)", type=["png", "jpg", "jpeg"], key=f"icon_{size}")
        if uploaded_icon:
            st.session_state.icons[size] = uploaded_icon.getvalue()
            st.success(f"Icon uploaded for {size}")

# Section: Upload mud log image for OCR
mud_log = st.file_uploader("Upload Mud Log Image (for OCR extraction)", type=["png", "jpg", "jpeg"])
if mud_log:
    try:
        # Read image with OpenCV
        img_array = np.frombuffer(mud_log.read(), np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        # Preprocess: Grayscale, threshold
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        # OCR
        text = pytesseract.image_to_string(thresh)
        
        # Parse text into data (assuming table structure from your example)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        parsed_bits = []
        for line in lines:
            parts = re.split(r'\s+', line)
            if len(parts) >= 7:
                try:
                    bit_no = int(parts[0])          # e.g. 1, 2, 3
                    size = parts[4]                 # e.g. 17.5"
                    depth_in = int(parts[6])        # e.g. 92
                    parsed_bits.append({"Bit Number": bit_no, "Size": size, "Depth In": depth_in})
                except (ValueError, IndexError):
                    pass
        
        if parsed_bits:
            new_df = pd.DataFrame(parsed_bits)
            st.session_state.bits_data = pd.concat([st.session_state.bits_data, new_df]).drop_duplicates().reset_index(drop=True)
            st.success(f"Extracted {len(parsed_bits)} bits from mud log!")
        else:
            st.warning("No data extracted from image. Check image quality or enter manually.")
    except Exception as e:
        st.error(f"OCR error: {e}")

# Data editor for manual input/editing
st.subheader("Bit Data (Edit/Add Rows)")
edited_data = st.data_editor(
    st.session_state.bits_data,
    num_rows="dynamic",
    column_config={
        "Bit Number": st.column_config.NumberColumn(help="Integer bit number"),
        "Size": st.column_config.TextColumn(help="e.g., 17.5\""),
        "Depth In": st.column_config.NumberColumn(help="Depth in (integer)")
    },
    use_container_width=True
)
st.session_state.bits_data = edited_data

# Function to generate PNG
def generate_bit_png(bit_no, size, depth_in, icon_bytes):
    width, height = 299, 598
    image = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # Try to use a bold serif font - DejaVuSerif-Bold is usually good enough
    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
        big_font = ImageFont.truetype(font_path, 52)      # BIT # & number
        size_font = ImageFont.truetype(font_path, 46)     # size with underline
        depth_font = ImageFont.truetype(font_path, 72)    # bottom depth
    except:
        # Fallback - will be smaller & thinner
        big_font = ImageFont.load_default()
        size_font = ImageFont.load_default()
        depth_font = ImageFont.load_default()

    # ── Top text: "BIT #1," ─────────────────────────────────────────────
    top_text = f"BIT #{bit_no},"
    bbox = draw.textbbox((0, 0), top_text, font=big_font)
    text_w = bbox[2] - bbox[0]
    x = (width - text_w) // 2
    y_top = 25
    draw.text((x, y_top), top_text, fill="black", font=big_font)

    # ── Size line with underline ────────────────────────────────────────
    size_text = f"{size}''"
    bbox_size = draw.textbbox((0, 0), size_text, font=size_font)
    size_w = bbox_size[2] - bbox_size[0]
    x_size = (width - size_w) // 2
    y_size = y_top + 65   # below the BIT line
    
    draw.text((x_size, y_size), size_text, fill="black", font=size_font)
    
    # Underline - a bit longer than the text
    #underline_y = y_size + 50
    #underline_start = x_size - 8
    #underline_end = x_size + size_w + 8
    #draw.line([(underline_start, underline_y), (underline_end, underline_y)], fill="black", width=4)

    # ── Bit icon ────────────────────────────────────────────────────────
    icon_y_start = 170          # starts quite high
    if icon_bytes:
        icon = Image.open(io.BytesIO(icon_bytes))
        
        # Make icon quite large - about 80-85% of width
        target_width = int(width * 0.82)
        aspect = icon.height / icon.width
        target_height = int(target_width * aspect)
        
        icon = icon.resize((target_width, target_height), Image.LANCZOS)
        
        # Center horizontally, place vertically after size text
        icon_x = (width - target_width) // 2
        image.paste(icon, (icon_x, icon_y_start), icon if icon.mode == 'RGBA' else None)

    # ── Bottom depth ────────────────────────────────────────────────────
    depth_text = f"{depth_in}'"
    bbox_depth = draw.textbbox((0, 0), depth_text, font=depth_font)
    depth_w = bbox_depth[2] - bbox_depth[0]
    x_depth = (width - depth_w) // 2
    
    # Place very low - adjust this value if needed (closer to bottom)
    y_depth = height - 110
    draw.text((x_depth, y_depth), depth_text, fill="black", font=depth_font)

    # Set DPI metadata
    image.info['dpi'] = (150, 150)
    
    buf = io.BytesIO()
    image.save(buf, format="PNG", dpi=(150, 150))
    buf.seek(0)
    return buf

# Preview and Download
st.subheader("Previews and Downloads")
zip_buf = io.BytesIO()
with zipfile.ZipFile(zip_buf, "w") as zf:
    for idx, row in st.session_state.bits_data.iterrows():
        bit_no = row["Bit Number"]
        size = row["Size"]
        depth_in = row["Depth In"]
        
        if pd.isna(bit_no) or pd.isna(size) or pd.isna(depth_in):
            continue
        
        icon_bytes = st.session_state.icons.get(size, None)
        if not icon_bytes:
            st.warning(f"No icon for size {size}. Skipping Bit {bit_no}.")
            continue
        
        png_buf = generate_bit_png(int(bit_no), size.replace('"', ''), int(depth_in), icon_bytes)
        
        # Preview (small)
        st.image(png_buf.getvalue(), caption=f"Bit {bit_no}", width=150)
        
        d30 = int(depth_in) + 30
        d70 = int(depth_in) + 70
        filename = f"Bit {bit_no}. ({d30} - {d70}).png"
        
        st.download_button(f"Download {filename}", data=png_buf.getvalue(), file_name=filename, mime="image/png")
        
        zf.writestr(filename, png_buf.getvalue())

if not st.session_state.bits_data.empty:
    zip_buf.seek(0)
    st.download_button("Download All as ZIP", data=zip_buf, file_name="bits_pngs.zip", mime="application/zip")






