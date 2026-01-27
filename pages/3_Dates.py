import streamlit as st
import pandas as pd
import io
import zipfile
from PIL import Image, ImageDraw, ImageFont
from datetime import date

st.title("3 - Date (Same Depth & After 10)")

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
        font = ImageFont.truetype(font_path, 120)  # Large font to match figure
    except:
        font = ImageFont.load_default()

    date_text = selected_date.strftime("%d/%m/%Y")
    bbox = draw.textbbox((0, 0), date_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Center text
    draw.text(
        ((width - text_w) // 2, (height - text_h) // 2),
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
