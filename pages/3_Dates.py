import streamlit as st
import pandas as pd
import io
import zipfile
from PIL import Image, ImageDraw, ImageFont
from datetime import date



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
st.markdown("### Tab 3: Dates (Same Depth & After 10)")




#st.title("3 - Date (Same Depth & After 10)")

# ────────────────────────────────────────────────
#   Data storage
# ────────────────────────────────────────────────
if 'date_data' not in st.session_state:
    st.session_state.date_data = pd.DataFrame(columns=["No.", "Date", "Depth"])

# ────────────────────────────────────────────────
#   Add new date form
# ────────────────────────────────────────────────
st.subheader("Add new Date entry")

cols = st.columns([1.5, 2.5, 1.5, 1])
with cols[0]:
    selected_date = st.date_input(
        "Select Date",
        value=date.today(),
        format="DD/MM/YYYY",
        key="new_date"
    )

with cols[1]:
    depth = st.number_input(
        "Depth (ft)",
        min_value=0,
        step=1,
        value=0,
        key="new_date_depth"
    )

if st.button("➕ Add Date", type="primary", use_container_width=True):
    if selected_date:
        # Get next No.
        next_no = int(st.session_state.date_data["No."].max()) + 1 if not st.session_state.date_data.empty else 1

        new_row = pd.DataFrame({
            "No.": [next_no],
            "Date": [selected_date],
            "Depth": [depth]
        })
        st.session_state.date_data = pd.concat(
            [st.session_state.date_data, new_row],
            ignore_index=True
        )
        st.success(f"Added Date #{next_no}: {selected_date.strftime('%d/%m/%Y')} @ {depth} ft")
        st.rerun()
    else:
        st.warning("Please select a date and enter depth")

# ────────────────────────────────────────────────
#   Show current entries + delete
# ────────────────────────────────────────────────
st.subheader("Current Date Entries")

if st.session_state.date_data.empty:
    st.info("No dates added yet. Use the form above.")
else:
    # Format Date for display
    display_df = st.session_state.date_data.copy()
    display_df["Date"] = display_df["Date"].apply(lambda d: d.strftime("%d/%m/%Y"))

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=False
    )

    to_remove = st.multiselect(
        "Select entry(s) to remove",
        options=st.session_state.date_data.index.tolist(),
        format_func=lambda i: f"Date #{st.session_state.date_data.loc[i, 'No.']} - {st.session_state.date_data.loc[i, 'Date'].strftime('%d/%m/%Y')} @ {st.session_state.date_data.loc[i, 'Depth']}'"
    )

    if st.button("🗑️ Remove selected", type="secondary"):
        if to_remove:
            st.session_state.date_data = st.session_state.date_data.drop(to_remove).reset_index(drop=True)
            # Renumber No.
            st.session_state.date_data["No."] = range(1, len(st.session_state.date_data) + 1)
            st.success(f"Removed {len(to_remove)} entry(s)")
            st.rerun()

# ────────────────────────────────────────────────
#   PNG generation function
# ────────────────────────────────────────────────
def generate_date_png(no, selected_date, depth):
    width, height = 653, 213
    image = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)

    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
        font = ImageFont.truetype(font_path, 100)  # Large font to match figure # ← reduced from 120 → safer for long dates
    except:
        font = ImageFont.load_default()

    date_text = selected_date.strftime("%d/%m/%Y")  # e.g. "27/01/2026"
    bbox = draw.textbbox((0, 0), date_text, font=font)  # Get bounding box to calculate exact centering
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Center text # Center horizontally & vertically with small offset upward # Draw red text
    draw.text(
        ((width - text_w) // 2, (height - text_h) // 2 - 8),  # ← -8 moves text slightly up (tune this: -15 to +5)
        date_text,
        fill=(255, 0, 0, 255),  # Red
        font=font
    )

    image.info['dpi'] = (330, 330)

    buf = io.BytesIO()
    image.save(buf, format="PNG", dpi=(330, 330))
    buf.seek(0)
    return buf.getvalue()

# ────────────────────────────────────────────────
#   Previews & Downloads
# ────────────────────────────────────────────────
st.subheader("Previews & Downloads")

if not st.session_state.date_data.empty:
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        for i, row in st.session_state.date_data.iterrows():
            no = row["No."]
            selected_date = row["Date"]
            depth = int(row["Depth"])

            png_bytes = generate_date_png(no, selected_date, depth)

            st.image(png_bytes, width=300, caption=f"Date #{no} - {selected_date.strftime('%d/%m/%Y')} @ {depth}'")

            fname = f"Date-{int(no)}. ({depth} - {depth + 10}).png"

            st.download_button(
                f"Download {fname}",
                png_bytes,
                file_name=fname,
                mime="image/png",
                key=f"date_dl_{i}"
            )

            zf.writestr(fname, png_bytes)

    zip_buf.seek(0)
    st.download_button(
        "Download all Dates as ZIP",
        zip_buf.getvalue(),
        file_name="dates_all.zip",
        mime="application/zip"
    )
else:
    st.info("Add at least one date entry to generate previews/downloads.")
