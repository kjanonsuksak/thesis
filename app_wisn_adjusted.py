# app.py
# Family Medicine WISN-inspired workforce planning tool
# Install: pip install streamlit pandas pyarrow openpyxl
# Run: streamlit run app.py

import io
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Family Medicine WISN",
    page_icon="🩺",
    layout="wide",
)

# -----------------------------
# Defaults aligned with study assumptions
# -----------------------------
DEFAULT_STANDARD_MIN = {
    "Acute": 6.55,
    "Chronic": 6.55,
    "Prevention": 6.55,
}
DEFAULT_AWT = 1680.0
DEFAULT_UNMET = 1.49

st.title("เครื่องมือประมาณความต้องการกำลังคนแพทย์เวชศาสตร์ครอบครัว")
st.caption("Forecast-based workload estimation | WISN-inspired planning tool")

st.info(
    "เครื่องมือนี้ประมาณความต้องการกำลังคน (FTE) จากปริมาณบริการและสมมติฐานที่กำหนด "
    "ไม่ใช่จำนวนแพทย์ที่ขาดแคลนหรือจำนวนที่ต้องบรรจุจริง "
    "ควรตรวจสอบฐานข้อมูลและสมมติฐานก่อนนำผลไปใช้วางแผน"
)

with st.sidebar:
    st.header("1) ขอบเขตการวิเคราะห์")
    st.markdown("**อัปโหลดข้อมูลพยากรณ์**")
    uploaded = st.file_uploader(
        "ไฟล์ CSV, Excel หรือ Parquet",
        type=["csv", "xlsx", "xls", "parquet"],
        help="ใช้ข้อมูลระดับจังหวัด × ปี × Health Need โดยมีอัตราบริการต่อ 1,000 ประชากรและประชากร",
    )

    st.divider()
    st.header("2) พารามิเตอร์ WISN")
    st.caption("ค่าเริ่มต้นตามกรอบสมมติฐานของการศึกษานี้ แก้ไขได้เพื่อวิเคราะห์สถานการณ์ทางเลือก")

    standard_min = {}
    for need, default in DEFAULT_STANDARD_MIN.items():
        standard_min[need] = st.number_input(
            f"เวลามาตรฐาน {need} (นาที/ครั้ง)",
            min_value=0.01,
            max_value=240.0,
            value=float(default),
            step=0.05,
            format="%.2f",
            key=f"std_{need}",
        )

    awt = st.number_input(
        "AWT (ชั่วโมง/คน/ปี)",
        min_value=1.0,
        max_value=4000.0,
        value=DEFAULT_AWT,
        step=10.0,
        format="%.0f",
    )
    unmet_pct = st.number_input(
        "ปรับเพิ่ม Unmet Need (%)",
        min_value=0.0,
        max_value=500.0,
        value=DEFAULT_UNMET,
        step=0.1,
        format="%.2f",
        help="ค่าเริ่มต้นตามสมมติฐานการศึกษา 1.49% สามารถเปลี่ยนเพื่อวิเคราะห์สถานการณ์ทางเลือกได้",
    )
    st.caption(
        f"ค่าที่ใช้ในรอบนี้: Acute {standard_min['Acute']:.2f}, "
        f"Chronic {standard_min['Chronic']:.2f}, "
        f"Prevention {standard_min['Prevention']:.2f} นาที/ครั้ง | "
        f"AWT {awt:,.0f} ชม./ปี | Unmet Need {unmet_pct:.2f}%"
    )

st.subheader("แนวทางการเตรียมข้อมูล")
st.markdown(
    """
ข้อมูลควรมีอย่างน้อย 5 คอลัมน์ โดยหนึ่งแถวแทน **จังหวัด × ปี × Health Need**
- `province` — ชื่อจังหวัด
- `year` — ปี พ.ศ. เช่น 2569
- `health_need` — `Acute`, `Chronic` หรือ `Prevention`
- `rate_per_1000` — อัตราบริการพยากรณ์ต่อประชากร 1,000 คน
- `population` — จำนวนประชากรของจังหวัด/กลุ่มประชากรที่ตรงกับอัตรานั้น

หากข้อมูลต้นทางเป็นรายกลุ่มอายุและเพศ ให้คงแถวแยกกลุ่มไว้ได้
โดยเพิ่มคอลัมน์ `age_group` และ `sex` ตามต้องการ แต่ต้องให้ประชากรและอัตราอยู่ในระดับเดียวกัน
"""
)

if uploaded is None:
    st.warning("เริ่มต้นโดยอัปโหลดไฟล์ข้อมูลพยากรณ์ เพื่อให้ระบบคำนวณผลตามข้อมูลจริง")
    sample = pd.DataFrame({
        "province": ["ตัวอย่างจังหวัด", "ตัวอย่างจังหวัด", "ตัวอย่างจังหวัด"],
        "year": [2569, 2569, 2569],
        "health_need": ["Acute", "Chronic", "Prevention"],
        "rate_per_1000": [297.529, 462.353, 252.302],
        "population": [100000, 100000, 100000],
    })
    st.markdown("**ตัวอย่างโครงสร้างข้อมูล (ตัวเลขประกอบการสาธิตเท่านั้น)**")
    st.dataframe(sample, use_container_width=True, hide_index=True)
    st.stop()

# -----------------------------
# Load data
# -----------------------------
try:
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        raw = pd.read_csv(uploaded)
    elif name.endswith((".xlsx", ".xls")):
        raw = pd.read_excel(uploaded)
    elif name.endswith(".parquet"):
        raw = pd.read_parquet(uploaded)
    else:
        st.error("ชนิดไฟล์ไม่รองรับ")
        st.stop()
except Exception as e:
    st.error(f"อ่านไฟล์ไม่สำเร็จ: {e}")
    st.stop()

st.subheader("ตรวจสอบและจับคู่คอลัมน์")
st.caption("เลือกคอลัมน์ให้ตรงกับข้อมูลต้นทางก่อนคำนวณ")
cols = list(raw.columns)

def find_col(candidates):
    lower_map = {str(c).strip().lower(): c for c in cols}
    for candidate in candidates:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]
    return cols[0]

with st.expander("กำหนดคอลัมน์ข้อมูล", expanded=True):
    c1, c2, c3 = st.columns(3)
    province_col = c1.selectbox("คอลัมน์จังหวัด", cols, index=cols.index(find_col(["province", "จังหวัด"])))
    year_col = c2.selectbox("คอลัมน์ปี พ.ศ.", cols, index=cols.index(find_col(["year", "ปี", "ปี พ.ศ."])))
    need_col = c3.selectbox("คอลัมน์ Health Need", cols, index=cols.index(find_col(["health_need", "health need", "ประเภทบริการ"])))
    c4, c5 = st.columns(2)
    rate_col = c4.selectbox("คอลัมน์อัตราบริการต่อ 1,000 ประชากร", cols, index=cols.index(find_col(["rate_per_1000", "service_rate_per_1000", "rate"])))
    pop_col = c5.selectbox("คอลัมน์ประชากร", cols, index=cols.index(find_col(["population", "ประชากร"])))

df = raw.rename(columns={
    province_col: "province",
    year_col: "year",
    need_col: "health_need",
    rate_col: "rate_per_1000",
    pop_col: "population",
}).copy()

required = ["province", "year", "health_need", "rate_per_1000", "population"]
try:
    df["year"] = pd.to_numeric(df["year"], errors="raise").astype(int)
    df["rate_per_1000"] = pd.to_numeric(df["rate_per_1000"], errors="raise")
    df["population"] = pd.to_numeric(df["population"], errors="raise")
except Exception:
    st.error("คอลัมน์ปี อัตราบริการ และประชากร ต้องเป็นตัวเลข")
    st.stop()

df["province"] = df["province"].astype(str).str.strip()
df["health_need"] = df["health_need"].astype(str).str.strip()
df = df[df["province"].ne("") & df["health_need"].ne("")].copy()

# Standardize health-need labels
label_map = {
    "acute": "Acute", "บริการเฉียบพลัน": "Acute", "บริการเจ็บป่วยเฉียบพลัน": "Acute",
    "chronic": "Chronic", "บริการโรคเรื้อรัง": "Chronic",
    "prevention": "Prevention", "บริการส่งเสริมสุขภาพและป้องกันโรค": "Prevention",
}
df["health_need"] = df["health_need"].map(
    lambda x: label_map.get(x.lower(), x)
)

valid_needs = list(DEFAULT_STANDARD_MIN)
unknown = sorted(set(df["health_need"]) - set(valid_needs))
if unknown:
    st.warning(f"พบประเภทบริการที่ยังไม่มีเวลามาตรฐาน: {', '.join(unknown)}")
    st.caption("แถวเหล่านี้จะไม่ถูกนำมาคำนวณ จนกว่าจะปรับชื่อ Health Need ให้ตรงกับ Acute, Chronic หรือ Prevention")

df = df[df["health_need"].isin(valid_needs)].copy()
df = df[df["population"].ge(0) & df["rate_per_1000"].ge(0)].copy()

# Warn if repeated records at same geographic/time/service level; do not silently aggregate.
key_cols = ["province", "year", "health_need"]
duplicates = df.duplicated(key_cols, keep=False)
if duplicates.any():
    st.error(
        "พบข้อมูลซ้ำในระดับจังหวัด × ปี × Health Need "
        "โปรดตรวจสอบหรือรวมข้อมูลตามวิธีที่ถูกต้องก่อนใช้เครื่องมือ "
        "ระบบจะไม่รวมแถวซ้ำให้อัตโนมัติ เพราะอาจทำให้ประชากรถูกนับซ้ำ"
    )
    st.dataframe(df.loc[duplicates].sort_values(key_cols), use_container_width=True)
    st.stop()

if df.empty:
    st.error("ไม่พบข้อมูลที่ใช้คำนวณได้ หลังตรวจสอบ Health Need")
    st.stop()

# Core workload calculation
df["base_visits"] = df["rate_per_1000"] * df["population"] / 1000.0
df["scenario_visits"] = df["base_visits"] * (1.0 + unmet_pct / 100.0)
df["workload_hours"] = (
    df["scenario_visits"] * df["health_need"].map(standard_min) / 60.0
)
df["fte"] = df["workload_hours"] / awt
df["unmet_pct_used"] = unmet_pct
df["awt_used"] = awt
df["standard_min_used"] = df["health_need"].map(standard_min)

st.divider()
st.subheader("1) เลือกขอบเขตผลลัพธ์")
a, b = st.columns(2)
years = sorted(df["year"].unique().tolist())
provinces = ["ทุกจังหวัด"] + sorted(df["province"].unique().tolist())
selected_year = a.selectbox("ปี พ.ศ.", years, index=0)
selected_province = b.selectbox("จังหวัด", provinces, index=0)
needs = st.multiselect("Health Need", valid_needs, default=valid_needs)

view = df[(df["year"] == selected_year) & df["health_need"].isin(needs)].copy()
if selected_province != "ทุกจังหวัด":
    view = view[view["province"] == selected_province]

if view.empty:
    st.warning("ไม่มีข้อมูลตามตัวกรองที่เลือก")
    st.stop()

# KPI and tables
total_base = view["base_visits"].sum()
total_scenario = view["scenario_visits"].sum()
total_hours = view["workload_hours"].sum()
total_fte = view["fte"].sum()

st.subheader(f"ผลประมาณการ ปี พ.ศ. {selected_year}")
k1, k2, k3, k4 = st.columns(4)
k1.metric("ปริมาณบริการพยากรณ์", f"{total_base:,.0f}", "ครั้ง/ปี")
k2.metric("บริการหลังปรับ Unmet Need", f"{total_scenario:,.0f}", "ครั้ง/ปี")
k3.metric("ภาระงานรวม", f"{total_hours:,.1f}", "ชั่วโมง/ปี")
k4.metric("ความต้องการกำลังคน", f"{total_fte:,.2f}", "FTE")

st.caption(
    f"พารามิเตอร์ที่ใช้: Unmet Need {unmet_pct:.2f}% | "
    f"AWT {awt:,.0f} ชั่วโมง/คน/ปี | "
    "FTE คำนวณจากบริการหลังปรับ × เวลามาตรฐาน ÷ 60 ÷ AWT"
)

summary = (
    view.groupby("health_need", as_index=False)
    .agg(
        base_visits=("base_visits", "sum"),
        scenario_visits=("scenario_visits", "sum"),
        workload_hours=("workload_hours", "sum"),
        fte=("fte", "sum"),
    )
)
summary["health_need"] = pd.Categorical(summary["health_need"], categories=valid_needs, ordered=True)
summary = summary.sort_values("health_need")
summary = summary.rename(columns={
    "health_need": "Health Need",
    "base_visits": "บริการพยากรณ์ (ครั้ง)",
    "scenario_visits": "บริการหลังปรับ (ครั้ง)",
    "workload_hours": "ภาระงาน (ชั่วโมง)",
    "fte": "ความต้องการกำลังคน (FTE)",
})
st.markdown("**สรุปตาม Health Need**")
fmt = {
    "บริการพยากรณ์ (ครั้ง)": "{:,.0f}",
    "บริการหลังปรับ (ครั้ง)": "{:,.0f}",
    "ภาระงาน (ชั่วโมง)": "{:,.1f}",
    "ความต้องการกำลังคน (FTE)": "{:,.2f}",
}
st.dataframe(summary.style.format(fmt), use_container_width=True, hide_index=True)

st.markdown("**สรุปตามจังหวัด**")
province_summary = (
    view.groupby("province", as_index=False)
    .agg(
        base_visits=("base_visits", "sum"),
        scenario_visits=("scenario_visits", "sum"),
        workload_hours=("workload_hours", "sum"),
        fte=("fte", "sum"),
    )
    .sort_values("fte", ascending=False)
    .rename(columns={
        "province": "จังหวัด",
        "base_visits": "บริการพยากรณ์ (ครั้ง)",
        "scenario_visits": "บริการหลังปรับ (ครั้ง)",
        "workload_hours": "ภาระงาน (ชั่วโมง)",
        "fte": "ความต้องการกำลังคน (FTE)",
    })
)
st.dataframe(province_summary.style.format({
    "บริการพยากรณ์ (ครั้ง)": "{:,.0f}",
    "บริการหลังปรับ (ครั้ง)": "{:,.0f}",
    "ภาระงาน (ชั่วโมง)": "{:,.1f}",
    "ความต้องการกำลังคน (FTE)": "{:,.2f}",
}), use_container_width=True, hide_index=True)

with st.expander("รายละเอียดระดับแถวข้อมูล"):
    detail_cols = [
        "province", "year", "health_need", "rate_per_1000", "population",
        "base_visits", "scenario_visits", "standard_min_used",
        "workload_hours", "fte", "unmet_pct_used", "awt_used"
    ]
    detail = view[detail_cols].rename(columns={
        "province": "จังหวัด",
        "year": "ปี พ.ศ.",
        "health_need": "Health Need",
        "rate_per_1000": "อัตราต่อ 1,000",
        "population": "ประชากร",
        "base_visits": "บริการพยากรณ์",
        "scenario_visits": "บริการหลังปรับ",
        "standard_min_used": "เวลามาตรฐาน (นาที/ครั้ง)",
        "workload_hours": "ภาระงาน (ชั่วโมง)",
        "fte": "FTE",
        "unmet_pct_used": "Unmet Need (%)",
        "awt_used": "AWT (ชั่วโมง/ปี)",
    })
    st.dataframe(detail, use_container_width=True, hide_index=True)

# Forecast horizon trend
st.subheader("แนวโน้มตามปี")
trend_source = df[df["health_need"].isin(needs)].copy()
if selected_province != "ทุกจังหวัด":
    trend_source = trend_source[trend_source["province"] == selected_province]
trend = trend_source.groupby(["year", "health_need"], as_index=False).agg(fte=("fte", "sum"))
if not trend.empty:
    chart_data = trend.pivot(index="year", columns="health_need", values="fte").fillna(0)
    st.line_chart(chart_data)
    st.caption("กราฟแสดง FTE ตามพารามิเตอร์ปัจจุบัน ไม่ใช่การคาดการณ์กำลังคนที่มีอยู่จริง")

# Export
st.subheader("ส่งออกผลลัพธ์")
csv_bytes = view.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
st.download_button(
    "ดาวน์โหลดผลลัพธ์ที่กรองเป็น CSV",
    data=csv_bytes,
    file_name=f"family_medicine_wisn_{selected_year}.csv",
    mime="text/csv",
)

xlsx_buffer = io.BytesIO()
with pd.ExcelWriter(xlsx_buffer, engine="openpyxl") as writer:
    summary.to_excel(writer, sheet_name="HealthNeed_Summary", index=False)
    province_summary.to_excel(writer, sheet_name="Province_Summary", index=False)
    view.to_excel(writer, sheet_name="Detail", index=False)
st.download_button(
    "ดาวน์โหลดรายงาน Excel",
    data=xlsx_buffer.getvalue(),
    file_name=f"family_medicine_wisn_{selected_year}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

with st.expander("คำอธิบายและข้อจำกัด"):
    st.markdown(
        """
- ผลลัพธ์คือ **ความต้องการกำลังคนเชิงภาระงาน (FTE)** ภายใต้ข้อมูลและสมมติฐานที่เลือก
  ไม่ใช่จำนวนแพทย์ขาดแคลน เพราะยังไม่ได้หักกำลังคนที่ปฏิบัติงานจริง
- ค่าปรับ Unmet Need เป็นสมมติฐานที่ผู้ใช้เลือกใช้ในรอบคำนวณ ควรบันทึกค่าไว้เมื่อรายงานผล
- การคำนวณนี้สมมติว่าอัตราบริการต่อ 1,000 และประชากรมีหน่วย/ขอบเขตตรงกัน
- หากคำนวณจากข้อมูลแยกอายุและเพศ ต้องใช้ประชากรในกลุ่มเดียวกับอัตราบริการ และตรวจสอบว่าไม่มีการนับซ้ำ
- เวลามาตรฐานและ AWT ที่แสดงเป็นค่าตั้งต้นของเครื่องมือ สามารถเปลี่ยนได้ แต่ควรรายงานค่าที่ใช้จริงทุกครั้ง
"""
    )
