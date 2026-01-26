import streamlit as st
from PIL import Image, ImageDraw
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
BASE_DIR = os.path.dirname(__file__)
BIT_ICON_PATHS = {
    '17.5"': os.path.join(BASE_DIR, "assets/bits/bit_17_5.png"),
    '12.25"': os.path.join(BASE_DIR, "assets/bits/bit_12_25.png"),
    '8.5"': os.path.join(BASE_DIR, "assets/bits/bit_8_5.png"),
}

# ---------------- LAYOUT ----------------
left, right = st.columns([1, 2])

# ---------------- INPUT ----------------
with left:
    st.markdown("### Bit Input")

    bit_no = st.number_input("Bit Number", min_value=1, step=1)
    bit_size = st.selectbox("Bit Size", ['17.5"', '12.25"', '8.5"'])
    depth_in = st.number_input("Depth In (ft)", min_value=0, step=1)

    if st.button("➕ Add Bit"):
        st.session_state.bits.append({
            "bit_no": bit_no,
            "bit_size": bit_size,
            "depth": depth_in
        })
        st.success(f"Bit #{bit_no} added")

# ---------------- IMAGE GENERATOR ----------------
def generate_bit_png(bit):
    canvas = Image.new("RGB", (299, 598), "white")
    draw = ImageDraw.Draw(canvas)

    icon = Image.open(BIT_ICON_PATHS[bit["bit_size"]]).convert("RGBA")
    icon.thumbnail((220, 220))

    draw.text((60, 20), f"BIT # {bit['bit_no']}", fill="black")
    draw.text((90, 70), bit["bit_size"], fill="black")

    canvas.paste(icon, ((299 - icon.width)//2, 140), icon)
    draw.text((110, 500), f"{bit['depth']}`", fill="black")

    return canvas

# ---------------- PREVIEW ----------------
with right:
    st.markdown("### Preview")

    previews = []
    for bit in st.session_state.bits:
        img = generate_bit_png(bit)
        st.image(img, width=200, caption=f"Bit #{bit['bit_no']}")
        previews.append(img)

# ---------------- SAVE ----------------
if st.session_state.bits:
    st.markdown("### Save Output")

    select_all = st.checkbox("Select All")
    selected = []

    for i, bit in enumerate(st.session_state.bits):
        checked = st.checkbox(
            f"Bit #{bit['bit_no']} ({bit['depth']+30}-{bit['depth']+70})",
            value=select_all,
            key=f"chk_{i}"
        )
        selected.append(checked)

    if st.button("💾 Save Selected"):
        zip_buffer = io.BytesIO()

        with ZipFile(zip_buffer, "w") as zip_file:
            for i, bit in enumerate(st.session_state.bits):
                if selected[i]:
                    img = generate_bit_png(bit)
                    name = f"Bit {bit['bit_no']} ({bit['depth']+30}-{bit['depth']+70}).png"
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format="PNG")
                    zip_file.writestr(name, img_bytes.getvalue())

        st.download_button(
            "Download ZIP",
            data=zip_buffer.getvalue(),
            file_name="Bits_Petrel_Output.zip",
            mime="application/zip"
        )
