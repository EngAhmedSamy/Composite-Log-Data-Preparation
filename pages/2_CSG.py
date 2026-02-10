import streamlit as st
import pandas as pd
import io
import zipfile
from PIL import Image, ImageDraw, ImageFont
import cv2
import pytesseract
import re
from pdf2image import convert_from_bytes


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
st.markdown("### Tab 2: CSG (Before 20 & After 20)")


#st.title("2 - CSG (Before 20 & After 20)")

# ────────────────────────────────────────────────
#   Icons (loaded from repo + optional override)
# ────────────────────────────────────────────────
csg_types = [
    "20\" Cond.",
    "13 3/8\"",
    "9 5/8\"",
    "7\" Liner",
    "Liner hanger",
    "PBTD"
]

if 'csg_icons' not in st.session_state:
    st.session_state.csg_icons = {}

for typ in csg_types:
    if typ not in st.session_state.csg_icons:
        fname = typ.replace('"', '').replace(' ', '_').replace('/', '_') + ".png"
        try:
            with open(f"assets/CSG/{fname}", "rb") as f:
                st.session_state.csg_icons[typ] = f.read()
        except FileNotFoundError:
            pass

with st.expander("Override icons (optional)"):
    for typ in csg_types:
        f = st.file_uploader(f"Replace icon for {typ}", type=["png","jpg","jpeg"], key=f"up_{typ}")
        if f is not None:
            st.session_state.csg_icons[typ] = f.getvalue()
            st.success(f"{typ} icon updated")

# ────────────────────────────────────────────────
#   Data storage
# ────────────────────────────────────────────────
if 'csg_data' not in st.session_state:
    st.session_state.csg_data = pd.DataFrame(columns=["Type", "Depth In"])

# ────────────────────────────────────────────────
#   Add new entry form
# ────────────────────────────────────────────────
st.subheader("Add new CSG / Liner entry")

cols = st.columns([3, 2, 1])
with cols[0]:
    selected_type = st.selectbox(
        "CSG / Liner Type",
        options=csg_types,
        index=None,
        placeholder="Select type...",
        key="new_csg_type"
    )

with cols[1]:
    depth_ft = st.number_input(
        "Depth In (ft)",
        min_value=0,
        step=1,
        value=None,
        key="new_csg_depth"
    )

if st.button("➕ Add Entry", type="primary", use_container_width=True):
    if selected_type and depth_ft is not None:
        new_row = pd.DataFrame({
            "Type": [selected_type],
            "Depth In": [depth_ft]
        })
        st.session_state.csg_data = pd.concat(
            [st.session_state.csg_data, new_row],
            ignore_index=True
        )
        # Optional: reset inputs (Streamlit reruns anyway)
        st.success(f"Added: {selected_type} @ {depth_ft} ft")
        st.rerun()
    else:
        st.warning("Please select type and enter depth")

# ────────────────────────────────────────────────
#   Show current entries + delete option
# ────────────────────────────────────────────────
st.subheader("Current Entries")

if st.session_state.csg_data.empty:
    st.info("No entries yet. Add one above.")
else:
    # Display table
    st.dataframe(
        st.session_state.csg_data,
        use_container_width=True,
        hide_index=False
    )

    # Delete selected row
    to_delete = st.multiselect(
        "Select row(s) to remove",
        options=st.session_state.csg_data.index.tolist(),
        format_func=lambda i: f"{st.session_state.csg_data.loc[i, 'Type']} @ {st.session_state.csg_data.loc[i, 'Depth In']}'"
    )

    if st.button("🗑️ Remove selected", type="secondary"):
        if to_delete:
            st.session_state.csg_data = st.session_state.csg_data.drop(to_delete).reset_index(drop=True)
            st.success(f"Removed {len(to_delete)} row(s)")
            st.rerun()



# ────────────────────────────────────────────────
#   OCR from mud log (kept as before)
# ────────────────────────────────────────────────
# st.subheader("Import from Mud Log (optional)")

# uploaded_file = st.file_uploader("PDF or Image", type=["pdf","png","jpg","jpeg"])

# if uploaded_file:
#     try:
#         content = uploaded_file.read()
#         images = []

#         if uploaded_file.type == "application/pdf":
#             images = convert_from_bytes(content)
#         else:
#             from io import BytesIO
#             import numpy as np
#             img = Image.open(BytesIO(content))
#             images = [img]

#         text = ""
#         for img_pil in images:
#             img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
#             gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
#             _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
#             text += pytesseract.image_to_string(thresh) + "\n"

#         # Simple parsing – improve later if needed
#         parsed = []
#         for line in text.splitlines():
#             line = line.strip()
#             if not line:
#                 continue
#             parts = re.split(r'\s{2,}', line)
#             if len(parts) >= 3:
#                 casing = parts[1] if len(parts) > 1 else ""
#                 try:
#                     depth = int(float(parts[-1].replace(',', '')))
#                     for t in csg_types:
#                         if t.replace('"','') in casing or casing in t.replace('"',''):
#                             parsed.append({"Type": t, "Depth In": depth})
#                             break
#                 except:
#                     pass

#         if parsed:
#             new_df = pd.DataFrame(parsed)
#             st.session_state.csg_data = pd.concat(
#                 [st.session_state.csg_data, new_df],
#                 ignore_index=True
#             ).drop_duplicates(subset=["Type", "Depth In"]).reset_index(drop=True)
#             st.success(f"Imported {len(parsed)} matching entries")
#             st.rerun()
#         else:
#             st.info("No recognizable casing data found in the file.")

#     except Exception as e:
#         st.error(f"Could not process file: {str(e)}")



# ────────────────────────────────────────────────
#   PNG generation & downloads (unchanged logic)
# ────────────────────────────────────────────────
def generate_csg_png(csg_type, depth, icon_bytes):
    w, h = 354, 592
    img = Image.new("RGBA", (w, h), (255,255,255,255))
    draw = ImageDraw.Draw(img)

    try:
        font_big   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 42)
        font_depth = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 68)
    except:
        font_big = font_depth = ImageFont.load_default()

    # Title
   # title = "Liner\nHanger" if csg_type == "Liner hanger" else csg_type.replace('"', "''")
    #draw.text((w//2, 45), title, font=font_big, fill="black", anchor="mm", align="center")

    # Icon
    if icon_bytes:
        icon = Image.open(io.BytesIO(icon_bytes)).convert("RGBA")
        iw = int(w * 0.78)
        ih = int(icon.height * iw / icon.width)
        icon = icon.resize((iw, ih), Image.LANCZOS)
        img.paste(icon, ((w - iw)//2, 0), icon)

    # Depth
    draw.text((w//2, h - 100), f"{int(depth)}'", font=font_depth, fill="black", anchor="mm")

    img = img.convert("P", palette=Image.ADAPTIVE, colors=256)
    img.info["dpi"] = (150, 150)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

st.subheader("Previews & Downloads")

if not st.session_state.csg_data.empty:
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        for i, row in st.session_state.csg_data.iterrows():
            typ = row["Type"]
            dep = int(row["Depth In"])

            if typ not in st.session_state.csg_icons:
                st.warning(f"Missing icon: {typ}")
                continue

            png_data = generate_csg_png(typ, dep, st.session_state.csg_icons[typ])

            st.image(png_data, width=140, caption=f"{typ}  {dep}'")

            safe = typ.replace('"','').replace(' ','_').replace('/','_')
            name = f"{safe}.({dep-20}-{dep+20}).png"

            st.download_button(
                f"Download {name}",
                png_data,
                file_name=name,
                mime="image/png",
                key=f"dl_{i}"
            )

            zf.writestr(name, png_data)

    zip_buf.seek(0)
    st.download_button(
        "Download all as ZIP",
        zip_buf.getvalue(),
        file_name="csg_all.zip",
        mime="application/zip"
    )
