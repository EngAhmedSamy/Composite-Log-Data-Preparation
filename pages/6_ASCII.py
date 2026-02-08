import streamlit as st

st.title("6 - ASCII")

# Sub-tabs for the different ASCII categories
tab_gyro, tab_fm_tops, tab_mud_log_ascii, tab_mud_drlg_params, tab_desc_comment, tab_oil_shows = st.tabs([
    "1 - Gyro",
    "2 - Fm Tops",
    "3 - Mud Log (ASCII-1, ASCII-5)",
    "4 - Mud & DRLG Parameters",
    "5 - Mud Log DESC Comment",
    "6 - Oil Shows Intensity"
])

# ────────────────────────────────────────────────
# 1. Gyro
# ────────────────────────────────────────────────
with tab_gyro:
    st.header("Gyro Data")
    st.info("Gyro data preparation coming soon. Add your logic here (upload, process, generate LAS/ASCII, etc.)")

# ────────────────────────────────────────────────
# 2. Fm Tops
# ────────────────────────────────────────────────
with tab_fm_tops:
    st.header("Formation Tops")
    st.info("Formation Tops preparation coming soon. Add input form, table, export to ASCII/LAS, etc.")

# ────────────────────────────────────────────────
# 3. Mud Log (ASCII-1, ASCII-5)
# ────────────────────────────────────────────────
with tab_mud_log_ascii:
    st.header("Mud Log ASCII (1 & 5)")
    st.info("Mud Log ASCII-1 and ASCII-5 preparation coming soon. Typically includes depth, ROP, gas, etc.")

# ────────────────────────────────────────────────
# 4. Mud & DRLG Parameters
# ────────────────────────────────────────────────
with tab_mud_drlg_params:
    st.header("Mud & Drilling Parameters")
    st.info("Mud properties and drilling parameters preparation coming soon.")

# ────────────────────────────────────────────────
# 5. Mud Log DESC Comment (with sub-header for lithology types)
# ────────────────────────────────────────────────
with tab_desc_comment:
    st.header("Mud Log Description Comment")
    st.subheader("This tab is for preparing the Mud Log Description Comments for:")

    lith_types = ["Clay", "Shale", "Sand", "SST", "SLT.ST", "LST", "Oil Shows"]
    for lit in lith_types:
        st.markdown(f"- **{lit}**")

    st.info("Description comment preparation coming soon. Will support multi-line text input per type, depth association, and formatted ASCII/PRN output.")

# ────────────────────────────────────────────────
# 6. Oil Shows Intensity
# ────────────────────────────────────────────────
with tab_oil_shows:
    st.header("Oil Shows Intensity")
    st.info("Oil shows intensity preparation coming soon. Likely includes depth, intensity level, fluorescence, etc.")
