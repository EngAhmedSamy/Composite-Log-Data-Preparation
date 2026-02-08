import streamlit as st
import pandas as pd
import io
import zipfile
from PIL import Image, ImageDraw, ImageFont

st.title("Tab 8 - Complete Loss (Before 25 & After 15)")

# ────────────────────────────────────────────────
#   Data storage
# ────────────────────────────────────────────────
if 'complete_loss_data' not in st.session_state:
    st.session_state.complete_loss_data = pd.DataFrame(columns=["No.", "Depth From", "Depth To"])

# ────────────────────────────────────────────────
#   Add new complete loss form
# ────────────────────────────────────────────────
st.subheader("Add Complete Loss")

col_from, col_to = st.columns(2)
with col_from:
    depth_from = st.number_input(
        "Depth From (ft)",
        min_value=0,
        step=1,
        value=0,
        key="new_loss_from"
    )

with col_to:
    depth_to = st.number_input(
        "Depth To (ft)",
        min_value=0,
        step=1,
        value=0,
        key="new_loss_to"
    )

if st.button("➕ Add Complete Loss", type="primary"):
    if depth_from >= 0 and depth_to >= depth_from:
        next_no = 1 if st.session_state.complete_loss_data.empty else int(st.session_state.complete_loss_data["No."].max()) + 1
        new_row = pd.DataFrame({
            "No.": [next_no],
            "Depth From": [depth_from],
            "Depth To": [depth_to]
        })
        st.session_state.complete_loss_data = pd.concat([st.session_state.complete_loss_data, new_row], ignore_index=True)
        st.success(f"Added Complete Loss #{next_no}: {depth_from} - {depth_to} ft")
        st.rerun()
    else:
        st.warning("Please enter valid depths (To >= From)")

# ────────────────────────────────────────────────
#   Current entries + delete
# ────────────────────────────────────────────────
st.subheader("Current Complete Loss Entries")

if st.session_state.complete_loss_data.empty:
    st.info("No entries added yet. Use the form above.")
else:
    st.dataframe(
        st.session_state.complete_loss_data,
        use_container_width=True,
        hide_index=False
    )

    to_remove = st.multiselect(
        "Select to remove",
        options=st.session_state.complete_loss_data.index.tolist(),
        format_func=lambda i: f"#{st.session_state.complete_loss_data.loc[i, 'No.']} – {st.session_state.complete_loss_data.loc[i, 'Depth From']} - {st.session_state.complete_loss_data.loc[i, 'Depth To']}'"
    )

    if st.button("🗑️ Remove selected", type="secondary"):
        if to_remove:
            st.session_state.complete_loss_data = st.session_state.complete_loss_data.drop(to_remove).reset_index(drop=True)
            st.session_state.complete_loss_data["No."] = range(1, len(st.session_state.complete_loss_data) + 1)
            st.success(f"Removed {len(to_remove)} entry(s)")
            st.rerun()

# ────────────────────────────────────────────────
#   PNG generation function
# ────────────────────────────────────────────────
def generate_complete_loss_png(no, depth_from, depth_to):
    width, height = 760, 1304
    image = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Load font (Times New Roman Bold)
    try:
        font_path = "Fonts/Times_New_Roman_Bold.ttf"  # from GitHub repo
        font_size = 200      # ← starting font size for depth text
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()
        font_size = 80

    # Top: F/Depth From
    top_text = f"F/{int(depth_from)}"
    bbox = draw.textbbox((0, 0), top_text, font=font)
    text_w = bbox[2] - bbox[0]
    draw.text(((width - text_w) // 2, 100), top_text, fill=(0, 0, 0, 255), font=font) # ← 80 is distance from top

    # Bottom: T/Depth To
    bottom_text = f"T/{int(depth_to)}"
    bbox = draw.textbbox((0, 0), bottom_text, font=font)
    text_w = bbox[2] - bbox[0]
    draw.text(((width - text_w) // 2, height - 250), bottom_text, fill=(0, 0, 0, 255), font=font) # ← 180 is distance from bottom

    # Middle: Complete loss icon from GitHub
    icon_path = "assets/Complete_Loss/Complete_Loss.png"  # uploaded to GitHub
    try:
        icon = Image.open(icon_path).convert("RGBA")
        icon_w = 800  # adjust width # ← change this number to control icon width
        icon_h = int(icon.height * icon_w / icon.width) # ← height is auto-calculated based on width
        icon = icon.resize((icon_w, icon_h), Image.LANCZOS)
        icon_x = (width - icon_w) // 2
        icon_y = (height - icon_h) // 2
        image.paste(icon, (icon_x, icon_y), icon)
    except Exception as e:
        st.warning(f"Icon not loaded: {e}")
        # Fallback: draw a simple red rectangle
        draw.rectangle(((width//4, height//2 - 150), (3*width//4, height//2 + 150)), outline=(255, 0, 0, 255), width=10)
    
    # Set DPI to 330 and keep 32-bit (RGBA) during processing    
    image.info['dpi'] = (330, 330)
    image = image.convert('P', palette=Image.ADAPTIVE, colors=256)  # 8-bit

    # Save as PNG (preserves alpha = 32-bit)
    buf = io.BytesIO()
    image.save(buf, format="PNG", dpi=(330, 330))
    buf.seek(0)
    return buf.getvalue()

# ────────────────────────────────────────────────
#   Previews & Downloads
# ────────────────────────────────────────────────
st.subheader("Previews & Downloads")

if not st.session_state.complete_loss_data.empty:
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        for i, row in st.session_state.complete_loss_data.iterrows():
            no = row["No."]
            depth_from = row["Depth From"]
            depth_to = row["Depth To"]

            png_bytes = generate_complete_loss_png(no, depth_from, depth_to)

            st.image(png_bytes, width=200, caption=f"Complete Loss #{no}: {depth_from} - {depth_to} ft")

            d_min = int(depth_from) - 25
            d_max = int(depth_to) + 15
            fname = f"Com. Loss ({d_min} - {d_max}).png"

            st.download_button(
                f"Download {fname}",
                png_bytes,
                file_name=fname,
                mime="image/png",
                key=f"dl_loss_{i}"
            )

            zf.writestr(fname, png_bytes)

    zip_buf.seek(0)
    st.download_button(
        "Download All as ZIP",
        zip_buf.getvalue(),
        "complete_loss_all.zip",
        mime="application/zip"
    )
else:
    st.info("Add at least one entry to generate previews/downloads.")
