import streamlit as st
import pandas as pd
import io
import zipfile
from PIL import Image, ImageDraw, ImageFont


st.sidebar.markdown("---")
st.sidebar.header("Global Settings")

well_name_input = st.sidebar.text_input(
    "Well Name",
    value=st.session_state.get('well_name', 'ABRAR-84'),
    key="well_name_input"
)

if st.sidebar.button("Apply Well Name", type="primary"):
    if well_name_input.strip():
        st.session_state.well_name = well_name_input.strip()
        # Place success message here - it will show until next rerun or page change
        st.sidebar.success(f"Well Name: **{st.session_state.well_name}** applied ✅")
       # st.rerun()  # optional - removes it faster but refreshes the app
    else:
        st.sidebar.error("Please enter a well name")
# Now every tab can use st.session_state.well_name


# ─── Sidebar Copyright / Watermark Footer (visible on ALL pages) ──────────
#st.sidebar.markdown("---")  # separator line above the copyright
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style="
        text-align: center; 
        color: #888; 
        font-size: 0.85rem; 
        padding: 12px 8px; 
        margin-top: auto;
        border-top: 1px solid #444;
    ">
        © 2026 Ahmed Samy<br>
        Composite Log Data Preparation App<br>
        Proprietary Software – All Rights Reserved<br>
        Private Property – For internal use only<br>
        Copyright protected – Do not distribute
    </div>
    """,
    unsafe_allow_html=True
)



st.set_page_config(page_title="Petrel Composite Log Prep", layout="wide", page_icon="🛢️")  # optional)
                   
st.title("Petrel Composite Log Data Preparation App")
st.markdown("### Tab 9: Perforation (Before 5 & After 5)")




#st.title("10 - Perforation (Before 5 & After 5)")

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
        "Perf_010": 100,
        "Perf_015": 100,
        "Perf_020": 120,
        "Perf_025": 140,
        "Perf_030": 40,
        "Perf_035": 50,
        "Perf_040": 110,
        "Perf_045": 100
    }

    bottom_y_offsets = {
        "Perf_005": 300,
        "Perf_010": 300,
        "Perf_015": 300,
        "Perf_020": 320,
        "Perf_025": 340,
        "Perf_030": 165,
        "Perf_035": 185,
        "Perf_040": 210,
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
