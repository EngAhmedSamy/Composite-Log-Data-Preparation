import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
from zipfile import ZipFile
import os

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Composite Log Data Preparation", layout="wide")
st.title("Composite Log Data Preparation")
st.subheader("1 – Bits (After 30 & After 70)")

# ---------------- SESSION ----------------
if "bits" not in st.session_state:
    st.session_state.bits = []

# ---------------- PATHS ----------------
BASE = os.path.dirname(__file__)
ASSETS = os.path.join(BASE, "assets", "bits")

TEMPLATES = {
    '17.5"': os.path.join(ASSETS, "template_17_5.png"),
    '12.25"': os.path.join(ASSETS, "template_12_25.png"),
    '8.5"': os.path.join(ASSETS, "template_8_5.png"),
}

SHAPES = {
    '17.5"': os.path.join(ASSETS, "shape_17_5.png"),
    '12.25"': os.path.join(ASSETS, "shape_12_25.png"),
    '8.5"': os.path.join(ASSETS, "shape_8_5.png"),
}

# ---------------- LAYOUT ----------------
left, right = st.columns([1, 2])

# ---------------- INPUT ----------------
with left:
    bit_no = st.number_input("Bit Number", min_value=1, step=1)
    bit_size = st.selectbox("Bit Size", ['17.5"', '12.25"', '8.5"'])
    depth_in = st.number_input("Depth In (ft)", min_value=0, step=1)

    if st.button("➕ Add Bit"):
        st.session_state.bits.append({
            "no": bit_no,
            "size": bit_size,
            "depth": depth_in
        })
        st.success(f"Bit #{bit_no} added")

# ---------------- IMAGE GENERATOR ----------------
def generate_bit_png(bit):
    img = Image.open(TEMPLATES[bit["size"]]).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Clear old text areas
    draw.rectangle((40, 20, 260, 90), fill="white")
    draw.rectangle((40, 90, 260, 160), fill="white")
    draw.rectangle((40, 480, 260, 560), fill="white")

    font = ImageFont.load_default()

    # Write new text
    draw.text((70, 35), f"BIT # {bit['no']},", fill="black", font=font)
    draw.text((95, 105), bit["size"], fill="black", font=font)
    draw.text((100, 500), f"{bit['depth']}`", fill="black", font=font)

    # Replace ONLY bit shape
    shape = Image.open(SHAPES[bit["size"]]).convert("RGBA")
    img.paste(shape, (40, 170), shape)

    return img

# ---------------- PREVIEW ----------------
with right:
    st.markdown("### Preview")
    previews = []

    for bit in st.session_state.bits:
        out = generate_bit_png(bit)
        st.image(out, width=200)
        previews.append(out)

# ---------------- SAVE ----------------
if st.session_state.bits:
    st.markdown("### Save Output")

    select_all = st.checkbox("Select All")
    selected = []

    for i, bit in enumerate(st.session_state.bits):
        checked = st.checkbox(
            f"Bit #{bit['no']} ({bit['depth']+30}-{bit['depth']+70})",
            value=select_all,
            key=f"chk_{i}"
        )
        selected.append(checked)

    if st.button("💾 Save Selected"):
        zip_buffer = io.BytesIO()

        with ZipFile(zip_buffer, "w") as zipf:
            for i, bit in enumerate(st.session_state.bits):
                if selected[i]:
                    img = generate_bit_png(bit)
                    name = f"Bit {bit['no']} ({bit['depth']+30}-{bit['depth']+70}).png"
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    zipf.writestr(name, buf.getvalue())

        st.download_button(
            "Download ZIP",
            data=zip_buffer.getvalue(),
            file_name="Bits_Petrel_Output.zip",
            mime="application/zip"
        )
