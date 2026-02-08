import streamlit as st
import pandas as pd
import io
import zipfile
from PIL import Image, ImageDraw, ImageFont

st.title("10 - Perforation (Before 5 & After 5)")

# ────────────────────────────────────────────────
#   Data storage
# ────────────────────────────────────────────────
if 'perforation_data' not in st.session_state:
    st.session_state.perforation_data = pd.DataFrame(columns=["No.", "Type", "Depth From", "Depth To"])

# ────────────────────────────────────────────────
#   Add new perforation form
# ────────────────────────────────────────────────
st.subheader("Add Perforation")

col_type, col_from, col_to = st.columns([3, 2, 2])
with col_type:
    perf_type = st.selectbox(
        "Perforation Type",
        options=["Perf_005", "Perf_010", "Perf_015", "Perf_020", "Perf_025", "Perf_030", "Perf_035", "Perf_040", "Perf_045"],
        index=None,
        placeholder="Select type...",
        key="new_perf_type"
    )

with col_from:
    depth_from = st.number_input(
        "Depth From (ft)",
        min_value=0,
        step=1,
        value=0,
        key="new_perf_from"
    )

with col_to:
    depth_to = st.number_input(
        "Depth To (ft)",
        min_value=0,
        step=1,
        value=0,
        key="new_perf_to"
    )

if st.button("➕ Add Perforation", type="primary"):
    if perf_type and depth_from >= 0 and depth_to >= depth_from:
        next_no = 1 if st.session_state.perforation_data.empty else int(st.session_state.perforation_data["No."].max()) + 1
        new_row = pd.DataFrame({
            "No.": [next_no],
            "Type": [perf_type],
            "Depth From": [depth_from],
            "Depth To": [depth_to]
        })
        st.session_state.perforation_data = pd.concat([st.session_state.perforation_data, new_row], ignore_index=True)
        st.success(f"Added #{next_no}: {perf_type} {depth_from} - {depth_to} ft")
        st.rerun()
    else:
        st.warning("Select type and valid depths (To >= From)")

# ────────────────────────────────────────────────
#   Current entries + delete
# ────────────────────────────────────────────────
st.subheader("Current Perforations")

if st.session_state.perforation_data.empty:
    st.info("No perforations added yet.")
else:
    st.dataframe(
        st.session_state.perforation_data,
        use_container_width=True,
        hide_index=False
    )

    to_remove = st.multiselect(
        "Select to remove",
        options=st.session_state.perforation_data.index.tolist(),
        format_func=lambda i: f"#{st.session_state.perforation_data.loc[i, 'No.']} – {st.session_state.perforation_data.loc[i, 'Type']} {st.session_state.perforation_data.loc[i, 'Depth From']} - {st.session_state.perforation_data.loc[i, 'Depth To']}'"
    )

    if st.button("🗑️ Remove selected", type="secondary"):
        if to_remove:
            st.session_state.perforation_data = st.session_state.perforation_data.drop(to_remove).reset_index(drop=True)
            st.session_state.perforation_data["No."] = range(1, len(st.session_state.perforation_data) + 1)
            st.success(f"Removed {len(to_remove)} perforation(s)")
            st.rerun()

# ────────────────────────────────────────────────
#   PNG generation function
# ────────────────────────────────────────────────
def generate_perforation_png(no, perf_type, depth_from, depth_to):
    # Size dict by type
    sizes = {
        "Perf_005": (655, 1004),
        "Perf_010": (655, 1331),
        "Perf_015": (655, 1654),
        "Perf_020": (655, 1980),
        "Perf_025": (655, 2304),
        "Perf_030": (655, 2631),
        "Perf_035": (655, 2953),
        "Perf_040": (655, 3279),
        "Perf_045": (655, 3603)
    }
    width, height = sizes.get(perf_type, (655, 1004))  # fallback to Perf_005

    image = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Load font
    try:
        font_path = "Fonts/Times_New_Roman_Bold.ttf"
        font_size = 160  # adjust as needed
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()
        font_size = 60

    
# Position offsets per type (distance from top/bottom edge)
    top_y_offsets = {
        "Perf_005": 100,
        "Perf_010": 300,
        "Perf_015": 100,
        "Perf_020": 120,
        "Perf_025": 140,
        "Perf_030": 160,
        "Perf_035": 180,
        "Perf_040": 200,
        "Perf_045": 220
    }

    bottom_y_offsets = {
        "Perf_005": 100,
        "Perf_010": 300,
        "Perf_015": 100,
        "Perf_020": 120,
        "Perf_025": 140,
        "Perf_030": 160,
        "Perf_035": 180,
        "Perf_040": 200,
        "Perf_045": 220
    }

    top_y = top_y_offsets.get(perf_type, 80)         # default 80 if type missing
    bottom_y = bottom_y_offsets.get(perf_type, 80)   # default 80
    
    
    # Top: F/Depth From
    top_text = f"F/{int(depth_from)}"
    bbox = draw.textbbox((0, 0), top_text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, top_y), top_text, fill=(0, 0, 0, 255), font=font)

    # Bottom: T/Depth To
    bottom_text = f"T/{int(depth_to)}"
    bbox = draw.textbbox((0, 0), bottom_text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, height - bottom_y), bottom_text, fill=(0, 0, 0, 255), font=font)

    # Middle icon from GitHub
    icon_fname = f"{perf_type.lower()}.png"  # e.g. perf_005.png
    try:
        icon = Image.open(f"assets/Perforations/{icon_fname}").convert("RGBA")
        icon_w = width - 100  # almost full width – adjust if needed
        icon_h = int(icon.height * icon_w / icon.width)
        icon = icon.resize((icon_w, icon_h), Image.LANCZOS)
        icon_x = (width - icon_w) // 2
        icon_y = (height - icon_h) // 2
        image.paste(icon, (icon_x, icon_y), icon)
    except Exception as e:
        st.warning(f"Icon load error: {e}")
        # Fallback black dot
        # draw.ellipse((width//2 - 20, height//2 - 20, width//2 + 20, height//2 + 20), fill=(0, 0, 0, 255))
        draw.rectangle(((width//4, height//2 - 150), (3*width//4, height//2 + 150)), outline=(255, 0, 0, 255), width=10)

    image.info['dpi'] = (330, 330)
    buf = io.BytesIO()
    image.save(buf, format="PNG", dpi=(330, 330))
    buf.seek(0)
    return buf.getvalue()

# ────────────────────────────────────────────────
#   Previews & Downloads
# ────────────────────────────────────────────────
st.subheader("Previews & Downloads")

if not st.session_state.perforation_data.empty:
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        for i, row in st.session_state.perforation_data.iterrows():
            no = row["No."]
            perf_type = row["Type"]
            d_from = int(row["Depth From"])
            d_to = int(row["Depth To"])

            png_bytes = generate_perforation_png(no, perf_type, d_from, d_to)

            st.image(png_bytes, width=200, caption=f"#{no} {perf_type} {d_from} - {d_to}")

            fname = f"{perf_type} ({d_from - 5} - {d_to + 5}).png"

            st.download_button(
                f"Download {fname}",
                png_bytes,
                file_name=fname,
                mime="image/png",
                key=f"dl_perf_{i}"
            )

            zf.writestr(fname, png_bytes)

    zip_buf.seek(0)
    st.download_button(
        "Download All as ZIP",
        zip_buf.getvalue(),
        "perforations_all.zip",
        mime="application/zip"
    )
else:
    st.info("Add at least one perforation to generate previews/downloads.")
