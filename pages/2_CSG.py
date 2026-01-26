import streamlit as st
import pandas as pd
import numpy as np
import io
import zipfile
from PIL import Image, ImageDraw, ImageFont
import cv2
import pytesseract
import re

st.title("2-CSG (Before 20 & After 20)")

# Session state for data — only Type and Depth In
if 'csg_data' not in st.session_state:
    st.session_state.csg_data = pd.DataFrame(columns=["Type", "Depth In"])

# Icons dictionary (type → bytes)
if 'csg_icons' not in st.session_state:
    st.session_state.csg_icons = {}

# Load default icons from repo folder
common_types = ["20\" Cond.", "13 3/8\"", "9 5/8\"", "7\" Liner", "Liner hanger", "PBTD"]
for csg_type in common_types:
    if csg_type not in st.session_state.csg_icons:
        file_name = csg_type.replace(" ", "_").replace('"', '').replace('/', '_') + '.png'
        try:
            with open(f"icons/{file_name}", "rb") as f:
                st.session_state.csg_icons[csg_type] = f.read()
            if 'csg_icons_loaded' not in st.session_state:
                st.session_state.csg_icons_loaded = True
                st.toast(f"Default icon loaded for {csg_type}", icon="✅")
        except FileNotFoundError:
            pass

# Optional override icons
with st.expander("Override / Replace Default Icons (optional)"):
    for csg_type in common_types:
        uploaded = st.file_uploader(
            f"Replace icon for {csg_type}",
            type=["png", "jpg", "jpeg"],
            key=f"override_csg_{csg_type.replace(' ', '_').replace('/', '_')}"
        )
        if uploaded:
            st.session_state.csg_icons[csg_type] = uploaded.getvalue()
            st.success(f"Icon for {csg_type} replaced!")

# Upload mud log file (PDF or image) for OCR
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

        text = ''
        for img in images:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            text += pytesseract.image_to_string(thresh) + '\n'

        # Parse WELL CONFIGURATION table
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        parsed_csg = []
        in_table = False
        for line in lines:
            if "WELL CONFIGURATION" in line.upper():
                in_table = True
                continue
            if in_table:
                parts = re.split(r'\s+', line)
                if len(parts) >= 4:
                    try:
                        csg_type_raw = parts[2]  # CASING SIZE
                        # Try to match to one of our common types
                        csg_type = next((t for t in common_types if csg_type_raw in t or t in csg_type_raw), None)
                        if csg_type:
                            depth_in = int(parts[3])  # SHOE DEPTH (FT.)
                            parsed_csg.append({"Type": csg_type, "Depth In": depth_in})
                    except (ValueError, IndexError):
                        pass

        if parsed_csg:
            new_df = pd.DataFrame(parsed_csg)
            # Append only new unique combinations to avoid duplicates
            st.session_state.csg_data = pd.concat([st.session_state.csg_data, new_df]).drop_duplicates().reset_index(drop=True)
            st.success(f"Extracted {len(parsed_csg)} CSG entries!")
        else:
            st.warning("No matching CSG data found in the file. Try manual entry.")
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")

# Data editor — only Type and Depth In
st.subheader("CSG Data (Edit/Add Rows)")
edited_data = st.data_editor(
    st.session_state.csg_data,
    num_rows="dynamic",
    column_config={
        "Type": st.column_config.SelectboxColumn(
            options=common_types,
            help="Select CSG / Liner type",
            required=True
        ),
        "Depth In": st.column_config.NumberColumn(
            help="Shoe depth / setting depth (ft)",
            required=True
        )
    },
    use_container_width=True,
    hide_index=False   # shows row numbers but not as "CSG Number"
)

st.session_state.csg_data = edited_data

# PNG generation function
def generate_csg_png(csg_type, depth_in, icon_bytes):
    width, height = 354, 592
    image = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)

    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
        top_font = ImageFont.truetype(font_path, 40)
        depth_font = ImageFont.truetype(font_path, 60)
    except:
        top_font = ImageFont.load_default()
        depth_font = ImageFont.load_default()

    # Top text
    if csg_type == "Liner hanger":
        top_text = "Liner\nHanger"
    else:
        top_text = csg_type.replace('"', "''")
    bbox = draw.textbbox((0, 0), top_text, font=top_font)
    text_w = bbox[2] - bbox[0]
    draw.text(((width - text_w) / 2, 30), top_text, fill="black", font=top_font, align="center")

    # Icon
    icon_y = 120
    if icon_bytes:
        icon = Image.open(io.BytesIO(icon_bytes))
        target_width = int(width * 0.75)
        aspect = icon.height / icon.width if icon.width > 0 else 1
        target_height = int(target_width * aspect)
        icon = icon.resize((target_width, target_height), Image.LANCZOS)
        icon_x = (width - target_width) // 2
        image.paste(icon, (icon_x, icon_y), icon if icon.mode == 'RGBA' else None)

    # Bottom depth
    bottom_text = f"{int(depth_in)}'"
    bbox = draw.textbbox((0, 0), bottom_text, font=depth_font)
    text_w = bbox[2] - bbox[0]
    draw.text(((width - text_w) / 2, height - 120), bottom_text, fill="black", font=depth_font)

    # To 8-bit palette mode
    image = image.convert('P', palette=Image.ADAPTIVE, colors=256)
    image.info['dpi'] = (150, 150)

    buf = io.BytesIO()
    image.save(buf, format="PNG", dpi=(150, 150))
    buf.seek(0)
    return buf

# Previews & Downloads
st.subheader("Previews and Downloads")

if not st.session_state.csg_data.empty:
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        for idx, row in st.session_state.csg_data.iterrows():
            csg_type = row["Type"]
            depth_in = row["Depth In"]

            if pd.isna(csg_type) or pd.isna(depth_in):
                continue

            icon_bytes = st.session_state.csg_icons.get(csg_type)
            if not icon_bytes:
                st.warning(f"No icon found for '{csg_type}'. Skipping.")
                continue

            png_buf = generate_csg_png(csg_type, depth_in, icon_bytes)

            # Small preview
            st.image(png_buf.getvalue(), caption=f"{csg_type} @ {depth_in}'", width=150)

            d_minus = int(depth_in) - 20
            d_plus = int(depth_in) + 20
            safe_type = csg_type.replace(" ", "_").replace('/', '_').replace('"', '')
            filename = f"{safe_type}.({d_minus}-{d_plus}).png"

            st.download_button(
                label=f"Download {filename}",
                data=png_buf.getvalue(),
                file_name=filename,
                mime="image/png"
            )

            zf.writestr(filename, png_buf.getvalue())

    zip_buf.seek(0)
    st.download_button(
        "Download All as ZIP",
        data=zip_buf,
        file_name="csg_pngs.zip",
        mime="application/zip"
    )
else:
    st.info("Add at least one CSG entry to generate previews/downloads.")
