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

# Icons dictionary (size to file bytes)
# Icons dictionary (size → bytes)
if 'icons' not in st.session_state:
    st.session_state.icons = {}

# Load default icons from repo folder (icons/8.5.png etc.)
common_sizes = ["8.5\"", "12.25\"", "17.5\""]
for size in common_sizes:
    # Only load if not already in session (prevents override loss on reruns)
    if size not in st.session_state.icons:
        file_name = size.replace('"', '') + '.png'  # 17.5" → 17.5.png
        try:
            with open(f"assets/bits/{file_name}", "rb") as f:
                st.session_state.icons[size] = f.read()
            # Optional: show success once
            if 'icons_loaded' not in st.session_state:
                st.session_state.icons_loaded = True
                st.toast(f"Default icon loaded for {size}", icon="✅")
        except FileNotFoundError:
            pass  # Will be handled in warning later if missing

# Optional: let user override/replace any icon
with st.expander("Override / Replace Default Icons (optional)"):
    for size in common_sizes:
        uploaded = st.file_uploader(
            f"Replace icon for {size}",
            type=["png", "jpg", "jpeg"],
            key=f"override_{size.replace('.', '_')}"
        )
        if uploaded:
            st.session_state.icons[size] = uploaded.getvalue()
            st.success(f"Icon for {size} replaced!")

# Section: Upload mud log file (PDF or image) for OCR
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

# Data editor for manual input/editing
st.subheader("Bit Data (Edit/Add Rows)")
edited_data = st.data_editor(
    st.session_state.bits_data,
    num_rows="dynamic",
    column_config={
        "Bit Number": st.column_config.NumberColumn(help="Integer bit number (auto-assigned if blank)"),
        "Size": st.column_config.SelectboxColumn(
            options=common_sizes,
            help="Choose bit size",
            required=True
        ),
        "Depth In": st.column_config.NumberColumn(help="Depth in (integer)")
    },
    use_container_width=True
)

# Auto-assign Bit Number for new rows (where NaN)
if not edited_data.empty:
    max_bit = edited_data['Bit Number'].max()
    if pd.isna(max_bit):
        max_bit = 0
    for idx in edited_data[pd.isna(edited_data['Bit Number'])].index:
        max_bit += 1
        edited_data.at[idx, 'Bit Number'] = max_bit

st.session_state.bits_data = edited_data

# Function to generate PNG (from previous update)
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

    # Top text: "BIT #1,"
    top_text = f"BIT #{bit_no},"
    bbox = draw.textbbox((0, 0), top_text, font=big_font)
    text_w = bbox[2] - bbox[0]
    x = (width - text_w) // 2
    y_top = 25
    draw.text((x, y_top), top_text, fill="black", font=big_font)

    # Size line with underline
    size_text = f"{size.replace('\"', '')}''"
    bbox_size = draw.textbbox((0, 0), size_text, font=size_font)
    size_w = bbox_size[2] - bbox_size[0]
    x_size = (width - size_w) // 2
    y_size = y_top + 65
    draw.text((x_size, y_size), size_text, fill="black", font=size_font)
    
    # underline_y = y_size + 50
    # underline_start = x_size - 8
    # underline_end = x_size + size_w + 8
    # draw.line([(underline_start, underline_y), (underline_end, underline_y)], fill="black", width=4)

    # Bit icon
    icon_y_start = 170
    if icon_bytes:
        icon = Image.open(io.BytesIO(icon_bytes))
        target_width = int(width * 0.82)
        aspect = icon.height / icon.width
        target_height = int(target_width * aspect)
        icon = icon.resize((target_width, target_height), Image.LANCZOS)
        icon_x = (width - target_width) // 2
        image.paste(icon, (icon_x, icon_y_start), icon if icon.mode == 'RGBA' else None)

    # Bottom depth
    depth_text = f"{depth_in}'"
    bbox_depth = draw.textbbox((0, 0), depth_text, font=depth_font)
    depth_w = bbox_depth[2] - bbox_depth[0]
    x_depth = (width - depth_w) // 2
    y_depth = height - 110
    draw.text((x_depth, y_depth), depth_text, fill="black", font=depth_font)

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
        
        png_buf = generate_bit_png(int(bit_no), size, int(depth_in), icon_bytes)
        
        st.image(png_buf.getvalue(), caption=f"Bit {bit_no}", width=150)
        
        d30 = int(depth_in) + 30
        d70 = int(depth_in) + 70
        filename = f"Bit {bit_no}. ({d30} - {d70}).png"
        
        st.download_button(f"Download {filename}", data=png_buf.getvalue(), file_name=filename, mime="image/png")
        
        zf.writestr(filename, png_buf.getvalue())

if not st.session_state.bits_data.empty:
    zip_buf.seek(0)
    st.download_button("Download All as ZIP", data=zip_buf, file_name="bits_pngs.zip", mime="application/zip")
