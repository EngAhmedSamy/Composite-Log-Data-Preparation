import streamlit as st
import pandas as pd
import io
import zipfile
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Petrel Prep - CSG", layout="wide")
st.title("2 - CSG (Before 20 & After 20)")

# === Default CSG Types ===
csg_types = [
    "20\" Cond.",
    "13 3/8\"",
    "9 5/8\"",
    "7\" Liner",
    "Liner hanger",
    "PBTD"
]

# === Load icons from GitHub repo (icons folder) ===
if 'csg_icons' not in st.session_state:
    st.session_state.csg_icons = {}

for typ in csg_types:
    if typ not in st.session_state.csg_icons:
        filename = typ.replace('"', '').replace(' ', '_').replace('/', '_') + ".png"
        try:
            with open(f"assets/CSG/{filename}", "rb") as f:
                st.session_state.csg_icons[typ] = f.read()
        except:
            pass  # icon will be missing → warning later

# Optional: override icons
with st.expander("Override Icons (optional)", expanded=False):
    for typ in csg_types:
        uploaded = st.file_uploader(f"Replace {typ}", type=["png", "jpg", "jpeg"], key=typ)
        if uploaded:
            st.session_state.csg_icons[typ] = uploaded.getvalue()
            st.success(f"{typ} icon updated")

# === Initialize empty data if not exists ===
if 'csg_data' not in st.session_state or st.session_state.csg_data.empty:
    st.session_state.csg_data = pd.DataFrame(columns=["Type", "Depth In"])

# === Data Editor with Dropdown ===
st.subheader("CSG Data (Add / Edit)")
df_edited = st.data_editor(
    st.session_state.csg_data,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Type": st.column_config.SelectboxColumn(
            "Type",
            help="Choose casing / liner type",
            options=csg_types,
            required=True,
        ),
        "Depth In": st.column_config.NumberColumn(
            "Depth In (ft)",
            help="Shoe / setting depth",
            min_value=0,
            step=1,
            required=True,
        ),
    },
    hide_index=False,
)

# Save back to session state (only valid rows)
valid_rows = df_edited.dropna(subset=["Type", "Depth In"])
st.session_state.csg_data = valid_rows.reset_index(drop=True)

# === PNG Generation Function ===
def make_csg_png(csg_type: str, depth: int, icon_bytes: bytes) -> bytes:
    w, h = 354, 592
    img = Image.new("RGBA", (w, h), "white")
    draw = ImageDraw.Draw(img)

    # Fonts
    try:
        f_top = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 42)
        f_depth = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 68)
    except:
        f_top = ImageFont.load_default()
        f_depth = ImageFont.load_default()

    # Top text
    top_text = "Liner\nHanger" if csg_type == "Liner hanger" else csg_type.replace('"', "''")
    draw.text((w//2, 40), top_text, font=f_top, fill="black", anchor="mm", align="center")

    # Icon
    if icon_bytes:
        icon = Image.open(io.BytesIO(icon_bytes)).convert("RGBA")
        icon_w = int(w * 0.78)
        icon_h = int(icon.height * icon_w / icon.width)
        icon = icon.resize((icon_w, icon_h), Image.LANCZOS)
        img.paste(icon, ((w - icon_w) // 2, 130), icon)

    # Bottom depth
    draw.text((w//2, h - 110), f"{int(depth)}'", font=f_depth, fill="black", anchor="mm")

    # Convert to 8-bit PNG with 150 DPI
    img = img.convert("P", palette=Image.ADAPTIVE, colors=256)
    img.info["dpi"] = (150, 150)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# === Previews & Downloads ===
st.subheader("Generated PNGs")

if not st.session_state.csg_data.empty:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, row in st.session_state.csg_data.iterrows():
            typ = row["Type"]
            depth = int(row["Depth In"])

            if typ not in st.session_state.csg_icons:
                st.warning(f"No icon for **{typ}** → skipped")
                continue

            png_bytes = make_csg_png(typ, depth, st.session_state.csg_icons[typ])

            # Preview
            st.image(png_bytes, width=160, caption=f"{typ} @ {depth}'")

            # Filename
            safe_name = typ.replace('"', '').replace(' ', '_').replace('/', '_')
            fname = f"{safe_name}.({depth-20}-{depth+20}).png"
            zf.writestr(fname, png_bytes)

            # Individual download
            st.download_button(
                label=f"Download {fname}",
                data=png_bytes,
                file_name=fname,
                mime="image/png",
                key=f"dl_{idx}"
            )

    zip_buffer.seek(0)
    st.download_button(
        label="Download All CSGs as ZIP",
        data=zip_buffer,
        file_name="CSG_PNGs.zip",
        mime="application/zip"
    )
else:
    st.info("Add at least one CSG row above to generate PNGs")

st.success("2-CSG tab is ready & stable!")
