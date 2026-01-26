# Cell 1: Install dependencies
!pip install -q streamlit pyngrok pillow opencv-python-headless pytesseract pdf2image
!apt-get install -y tesseract-ocr poppler-utils

# Cell 2: Write the Streamlit app code to app.py
%%writefile app.py
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
        
        # Parse text into data (assuming table structure)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        parsed_bits = []
        for line in lines[2:]:  # Skip header and title
            parts = re.split(r'\s+', line)
            if len(parts) >= 7:
                bit_no = parts[0]
                size = parts[4]  # e.g., 17.5"
                depth_in = parts[6]  # e.g., 92
                try:
                    bit_no = int(bit_no)
                    depth_in = int(depth_in)
                    parsed_bits.append({"Bit Number": bit_no, "Size": size, "Depth In": depth_in})
                except ValueError:
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
    # Create blank image
    width, height = 299, 598
    image = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # Fonts (use system font in Colab)
    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
        top_font = ImageFont.truetype(font_path, 40)
        bottom_font = ImageFont.truetype(font_path, 60)
    except:
        top_font = ImageFont.load_default()
        bottom_font = ImageFont.load_default()
    
    # Top text: BIT #<no>, <size>'
    top_text = f"BIT #{bit_no}, {size}'"
    bbox = draw.textbbox((0,0), top_text, font=top_font)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) / 2, 20), top_text, fill="black", font=top_font)
    
    # Bottom text: <depth_in>'
    bottom_text = f"{depth_in}'"
    bbox = draw.textbbox((0,0), bottom_text, font=bottom_font)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) / 2, height - 100), bottom_text, fill="black", font=bottom_font)
    
    # Icon: Resize and paste in middle
    if icon_bytes:
        icon = Image.open(io.BytesIO(icon_bytes))
        icon = icon.resize((200, 200), Image.ANTIALIAS)
        image.paste(icon, ((width - 200) // 2, (height - 200) // 2), icon if icon.mode == 'RGBA' else None)
    
    # Set DPI
    image.info['dpi'] = (150, 150)
    
    # Save to bytes
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
            st.warning(f"No icon uploaded for size {size}. Skipping preview/download for Bit {bit_no}.")
            continue
        
        png_buf = generate_bit_png(bit_no, size.replace('"', ''), int(depth_in), icon_bytes)  # Remove " for text
        
        # Preview
        st.image(png_buf.getvalue(), caption=f"Preview: Bit {bit_no}", width=150)
        
        # Filename
        d30 = int(depth_in) + 30
        d70 = int(depth_in) + 70
        filename = f"Bit {bit_no}. ({d30} - {d70}).png"
        
        # Individual download
        st.download_button(f"Download {filename}", data=png_buf.getvalue(), file_name=filename)
        
        # Add to ZIP
        zf.writestr(filename, png_buf.getvalue())

if not st.session_state.bits_data.empty:
    zip_buf.seek(0)
    st.download_button("Download All as ZIP", data=zip_buf, file_name="bits_pngs.zip")

