"""
Building Code Advisor - เว็บฟอร์มช่วยพิจารณาเบื้องต้นตาม พ.ร.บ.ควบคุมอาคาร
รันด้วยคำสั่ง: streamlit run app.py
"""

import streamlit as st
from dataclasses import dataclass
from typing import Optional

# ==============================
# 1) ฐานข้อมูลกฎเกณฑ์
# ==============================

LIVE_LOAD_DB = {
    "บ้านพักอาศัย": {"load": 150, "source": "กฎกระทรวง 2566"},
    "หอพัก/อพาร์ตเมนต์": {"load": 200, "source": "กฎกระทรวงฉบับที่ 6 (2527)"},
    "โรงแรม/อาคารชุด": {"load": 400, "source": "กฎกระทรวง 2566 (ปรับเพิ่มจากเดิม 300)"},
    "สำนักงาน": {"load": 300, "source": "กฎกระทรวงฉบับที่ 6 (2527)"},
    "สถานศึกษา": {"load": 300, "source": "ห้ามลดน้ำหนักบรรทุกจรตามชั้น"},
    "สถานพยาบาล": {"load": 300, "source": "ห้ามลดน้ำหนักบรรทุกจรตามชั้น"},
    "ร้านค้า/ห้างสรรพสินค้า": {"load": 500, "source": "กฎกระทรวงฉบับที่ 6 (2527)"},
    "หอประชุม/โรงมหรสพ": {"load": 400, "source": "กฎกระทรวงฉบับที่ 6 (2527)"},
    "ที่จอดรถ": {"load": 400, "source": "ห้ามลดน้ำหนักบรรทุกจรตามชั้น"},
    "คลังสินค้า/โรงงาน": {"load": 500, "source": "อาจต้องคำนวณเฉพาะจุดถ้าเกิน 500"},
}

SETBACK_RULES = [
    {"wall": "มีช่องเปิด", "max_height": 9, "setback": 2.0, "note": "กฎกระทรวงฉบับที่ 55"},
    {"wall": "ทึบ", "max_height": 9, "setback": 0.5,
     "note": "ถ้า < 0.5 ม. ต้องมีหนังสือยินยอมจากเจ้าของที่ดินข้างเคียง"},
    {"wall": "มีช่องเปิด", "max_height": float("inf"), "setback": 3.0, "note": "อาคารสูงเกิน 9 ม."},
    {"wall": "ทึบ", "max_height": float("inf"), "setback": 2.0, "note": "อาคารสูงเกิน 9 ม."},
]

ROAD_SETBACK_MIN_WIDTH = 10.0
ROAD_SETBACK_DISTANCE = 6.0


# ==============================
# 2) Logic functions
# ==============================

def get_live_load(building_use: str) -> dict:
    return LIVE_LOAD_DB.get(building_use, {
        "load": None, "source": None,
    })

def get_setback(wall_type: str, height_m: float) -> dict:
    for rule in SETBACK_RULES:
        if rule["wall"] == wall_type and height_m <= rule["max_height"]:
            return rule
    return {"setback": None, "note": "ไม่พบเงื่อนไขที่ตรงกัน"}

def get_road_setback(road_width_m: float) -> dict:
    if road_width_m < ROAD_SETBACK_MIN_WIDTH:
        return {
            "required": True,
            "note": f"ถนนกว้าง {road_width_m} ม. (< 10 ม.) ต้องร่นแนวอาคารจากกึ่งกลางถนนอย่างน้อย {ROAD_SETBACK_DISTANCE} ม."
        }
    return {"required": False, "note": "ถนนกว้างเพียงพอ ไม่ต้องร่นเพิ่มเติมจากกรณีนี้"}

def classify_building_size(total_floor_area_m2: float, height_m: float) -> str:
    if total_floor_area_m2 >= 10000 or height_m >= 23:
        return "🔴 อาคารขนาดใหญ่พิเศษ (ต้องพิจารณา EIA และมาตรการเพิ่มเติม)"
    elif total_floor_area_m2 >= 2000 or height_m >= 15:
        return "🟠 อาคารขนาดใหญ่ (ต้องปฏิบัติตามกฎกระทรวงอาคารขนาดใหญ่)"
    elif height_m > 23:
        return "🟠 อาคารสูง (ต้องมีระบบดับเพลิง/ลิฟต์ดับเพลิงตามกฎหมายอาคารสูง)"
    else:
        return "🟢 อาคารทั่วไป"


def analyze(building_use, height_m, wall_type, land_width_m, land_depth_m,
            road_width_m, floor_area_m2):
    live_load = get_live_load(building_use)
    setback = get_setback(wall_type, height_m)
    road_check = get_road_setback(road_width_m)
    size_class = classify_building_size(floor_area_m2, height_m)

    warnings = []
    land_ok = True
    if setback.get("setback") is not None:
        min_required_width = setback["setback"] * 2
        if land_width_m < min_required_width:
            land_ok = False
            warnings.append(
                f"ที่ดินกว้าง {land_width_m} ม. อาจไม่พอสำหรับระยะร่นขั้นต่ำ "
                f"{setback['setback']} ม. ทั้งสองด้าน (ต้องการอย่างน้อย {min_required_width} ม.)"
            )

    return {
        "size_class": size_class,
        "live_load": live_load,
        "setback": setback,
        "road_check": road_check,
        "land_ok": land_ok,
        "warnings": warnings,
    }


# ==============================
# 3) Streamlit UI
# ==============================

st.set_page_config(page_title="ระบบช่วยพิจารณาอาคารเบื้องต้น", page_icon="🏗️", layout="centered")

st.title("🏗️ ระบบช่วยพิจารณาข้อกำหนดอาคารเบื้องต้น")
st.caption("⚠️ เป็นเครื่องมือช่วยคัดกรองเบื้องต้นเท่านั้น ไม่ทดแทนการตรวจสอบโดยวิศวกร/สถาปนิกที่มีใบอนุญาต")

st.divider()

with st.form("building_form"):
    st.subheader("📋 กรอกข้อมูลอาคารและที่ดิน")

    col1, col2 = st.columns(2)

    with col1:
        building_use = st.selectbox("ประเภทการใช้อาคาร", list(LIVE_LOAD_DB.keys()))
        building_height = st.number_input("ความสูงอาคาร (เมตร)", min_value=0.0, value=9.0, step=0.5)
        wall_type = st.radio("ประเภทผนังด้านที่ใกล้แนวเขตที่ดิน", ["มีช่องเปิด", "ทึบ"])

    with col2:
        land_width = st.number_input("ความกว้างที่ดิน (เมตร)", min_value=0.0, value=15.0, step=0.5)
        land_depth = st.number_input("ความลึกที่ดิน (เมตร)", min_value=0.0, value=20.0, step=0.5)
        road_width = st.number_input("ความกว้างถนนหน้าที่ดิน (เมตร)", min_value=0.0, value=8.0, step=0.5)

    floor_area = st.number_input("พื้นที่ใช้สอยรวมทั้งอาคาร (ตร.ม.)", min_value=0.0, value=1500.0, step=50.0)

    submitted = st.form_submit_button("🔍 วิเคราะห์ผล", use_container_width=True)

if submitted:
    result = analyze(building_use, building_height, wall_type, land_width,
                      land_depth, road_width, floor_area)

    st.divider()
    st.subheader("📊 ผลการพิจารณาเบื้องต้น")

    st.info(f"**ประเภทอาคาร:** {result['size_class']}")

    c1, c2 = st.columns(2)
    with c1:
        ll = result["live_load"]
        if ll["load"]:
            st.metric("น้ำหนักบรรทุกจรที่ต้องออกแบบ", f"{ll['load']} กก./ตร.ม.")
            st.caption(f"อ้างอิง: {ll['source']}")
        else:
            st.warning("ไม่พบข้อมูลในฐานข้อมูล กรุณาตรวจสอบกับกฎกระทรวงโดยตรง")

    with c2:
        sb = result["setback"]
        if sb.get("setback") is not None:
            st.metric("ระยะร่นขั้นต่ำจากแนวเขตที่ดิน", f"{sb['setback']} เมตร")
            st.caption(sb["note"])

    st.write(f"**ระยะร่นจากถนน:** {result['road_check']['note']}")

    if result["warnings"]:
        st.error("⚠️ **คำเตือน:**\n" + "\n".join(f"- {w}" for w in result["warnings"]))
    else:
        st.success("✅ ที่ดินกว้างเพียงพอตามเงื่อนไขระยะร่นเบื้องต้นที่ตรวจสอบ")

    with st.expander("ดูข้อมูล Input ทั้งหมด"):
        st.json({
            "ประเภทการใช้อาคาร": building_use,
            "ความสูง (ม.)": building_height,
            "ประเภทผนัง": wall_type,
            "ความกว้างที่ดิน (ม.)": land_width,
            "ความลึกที่ดิน (ม.)": land_depth,
            "ความกว้างถนน (ม.)": road_width,
            "พื้นที่ใช้สอยรวม (ตร.ม.)": floor_area,
        })