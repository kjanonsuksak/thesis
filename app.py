import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="WISN Family Medicine Planner", page_icon="🩺", layout="wide")
st.title("เครื่องมือประมาณความต้องการกำลังคนแพทย์เวชศาสตร์ครอบครัว")
st.caption("Forecast-based workload estimation | WISN-inspired planning tool")

DATA_PATH = Path(__file__).parent / "RF_F4_forecast_2569_2573_strata.csv.gz"
HEALTH_NEEDS = ["Acute", "Chronic", "Prevention"]
HEALTH_TH = {"Acute":"บริการเฉียบพลัน (Acute)", "Chronic":"บริการโรคเรื้อรัง (Chronic)", "Prevention":"บริการส่งเสริมสุขภาพและป้องกันโรค (Prevention)"}
HOS_TH = {1:"หน่วยบริการปฐมภูมิ",2:"โรงพยาบาลชุมชน",3:"โรงพยาบาลทั่วไป",4:"โรงพยาบาลศูนย์",5:"โรงพยาบาลมหาวิทยาลัย",6:"โรงพยาบาลและสถานพยาบาลอื่น ๆ"}

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH, compression="gzip")
    expected = {"health_need","province","hos_type","sex","age_group","cci","year","pred_rate","Population","จำนวนการใช้บริการ"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"ไม่พบคอลัมน์ที่จำเป็น: {', '.join(missing)}")
    df["hos_type"] = pd.to_numeric(df["hos_type"], errors="coerce").astype("Int64")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(int)
    df["จำนวนการใช้บริการ"] = pd.to_numeric(df["จำนวนการใช้บริการ"], errors="coerce").fillna(0)
    df["pred_rate"] = pd.to_numeric(df["pred_rate"], errors="coerce").fillna(0)
    return df

try:
    data = load_data()
except Exception as e:
    st.error(f"โหลดข้อมูลไม่สำเร็จ: {e}")
    st.info("วางไฟล์ RF_F4_forecast_2569_2573_strata.csv.gz ไว้ในโฟลเดอร์เดียวกับ app.py")
    st.stop()

with st.sidebar:
    st.header("1) เลือกขอบเขตการวิเคราะห์")
    years = sorted(data.year.unique().tolist())
    year = st.selectbox("ปี พ.ศ.", years, index=0)
    provinces = ["ทุกจังหวัด"] + sorted(data.province.dropna().unique().tolist())
    province = st.selectbox("จังหวัด", provinces)
    hos_options = ["ทุกประเภท"] + sorted(data.hos_type.dropna().astype(int).unique().tolist())
    hos_pick = st.selectbox("ประเภทหน่วยบริการ", hos_options, format_func=lambda x: x if x=="ทุกประเภท" else f"{x} — {HOS_TH.get(x,'')}")
    needs = st.multiselect("Health Need", HEALTH_NEEDS, default=HEALTH_NEEDS)

    st.header("2) กำหนดพารามิเตอร์ WISN")
    st.caption("ค่าเริ่มต้นเป็นสมมติฐานตัวอย่างจากกรอบการศึกษานี้ สามารถปรับเพื่อวิเคราะห์สถานการณ์ได้")
    std_default = {"Acute":6.55, "Chronic":6.55, "Prevention":6.55}
    standard = {}
    for n in HEALTH_NEEDS:
        standard[n] = st.number_input(f"เวลามาตรฐาน {n} (นาที/ครั้ง)", min_value=0.0, max_value=240.0, value=std_default[n], step=0.25)
    awt = st.number_input("AWT (ชั่วโมง/คน/ปี)", min_value=1.0, max_value=3000.0, value=1680.0, step=24.0)
    unmet_pct = st.number_input("ปรับเพิ่ม Unmet Need (%)", min_value=0.0, max_value=300.0, value=0.0, step=0.5,
        help="ตั้งต้น 0% เพื่อแสดงค่าตามจำนวนบริการพยากรณ์ หากมีหลักฐานรองรับจึงค่อยปรับ")
    st.caption("การปรับ Unmet Need เป็น scenario ไม่ใช่ค่าที่ระบบยืนยันว่าเหมาะกับทุกกลุ่มบริการ")

df = data[(data.year == year) & (data.health_need.isin(needs))]
if province != "ทุกจังหวัด":
    df = df[df.province == province]
if hos_pick != "ทุกประเภท":
    df = df[df.hos_type == hos_pick]

if df.empty:
    st.warning("ไม่มีข้อมูลตรงกับตัวเลือกนี้")
    st.stop()

df = df.copy()
df["Health Need"] = df.health_need.map(HEALTH_TH)
df["ประเภทหน่วยบริการ"] = df.hos_type.astype(int).map(HOS_TH)
df["ปริมาณบริการฐาน (ครั้ง)"] = df["จำนวนการใช้บริการ"]
df["ปริมาณบริการหลังปรับ (ครั้ง)"] = df.apply(lambda r: r["จำนวนการใช้บริการ"] * (1+unmet_pct/100), axis=1)
df["เวลามาตรฐาน (นาที/ครั้ง)"] = df.health_need.map(standard)
df["ภาระงาน (ชั่วโมง)"] = df["ปริมาณบริการหลังปรับ (ครั้ง)"] * df["เวลามาตรฐาน (นาที/ครั้ง)"] / 60
df["ความต้องการกำลังคน (FTE)"] = df["ภาระงาน (ชั่วโมง)"] / awt

volume = df["ปริมาณบริการหลังปรับ (ครั้ง)"].sum()
workhours = df["ภาระงาน (ชั่วโมง)"].sum()
fte = df["ความต้องการกำลังคน (FTE)"].sum()
basevol = df["ปริมาณบริการฐาน (ครั้ง)"].sum()
a,b,c,d=st.columns(4)
a.metric("ปริมาณบริการพยากรณ์",f"{basevol:,.0f} ครั้ง")
b.metric("บริการหลังปรับ scenario",f"{volume:,.0f} ครั้ง")
c.metric("ภาระงาน",f"{workhours:,.0f} ชั่วโมง")
d.metric("ความต้องการกำลังคน",f"{fte:,.2f} FTE")

st.info("FTE ในหน้านี้คำนวณจากบริการที่เลือก × เวลามาตรฐาน ÷ 60 ÷ AWT และปรับ Unmet Need ตามค่าที่ผู้ใช้ระบุ โดยไม่ใช่จำนวนแพทย์ที่ขาดแคลนหรือจำนวนที่ควรบรรจุทันที")

tab1,tab2,tab3=st.tabs(["สรุปตาม Health Need","สรุปตามหน่วยบริการ","รายละเอียด/ส่งออก"])
with tab1:
    summary = df.groupby("health_need",as_index=False).agg(
        service_base=("ปริมาณบริการฐาน (ครั้ง)","sum"),
        service_adjusted=("ปริมาณบริการหลังปรับ (ครั้ง)","sum"),
        workload_hours=("ภาระงาน (ชั่วโมง)","sum"),
        FTE=("ความต้องการกำลังคน (FTE)","sum"))
    summary["Health Need"] = summary.health_need.map(HEALTH_TH)
    st.dataframe(summary[["Health Need","service_base","service_adjusted","workload_hours","FTE"]].rename(columns={
        "service_base":"บริการฐาน (ครั้ง)","service_adjusted":"บริการหลังปรับ (ครั้ง)","workload_hours":"ภาระงาน (ชั่วโมง)"}).style.format({
        "บริการฐาน (ครั้ง)":"{:,.0f}","บริการหลังปรับ (ครั้ง)":"{:,.0f}","ภาระงาน (ชั่วโมง)":"{:,.1f}","FTE":"{:,.3f}"}),use_container_width=True,hide_index=True)
    st.bar_chart(summary.set_index("Health Need")["FTE"])
with tab2:
    s2=df.groupby("ประเภทหน่วยบริการ",as_index=False).agg(
        visits=("ปริมาณบริการฐาน (ครั้ง)","sum"), workload=("ภาระงาน (ชั่วโมง)","sum"), FTE=("ความต้องการกำลังคน (FTE)","sum"))
    st.dataframe(s2.style.format({"visits":"{:,.0f}","workload":"{:,.1f}","FTE":"{:,.3f}"}),use_container_width=True,hide_index=True)
    st.bar_chart(s2.set_index("ประเภทหน่วยบริการ")["FTE"])
with tab3:
    showcols=["year","province","hos_type","ประเภทหน่วยบริการ","health_need","sex","age_group","cci","pred_rate","Population",
              "ปริมาณบริการฐาน (ครั้ง)","ปริมาณบริการหลังปรับ (ครั้ง)","เวลามาตรฐาน (นาที/ครั้ง)","ภาระงาน (ชั่วโมง)","ความต้องการกำลังคน (FTE)"]
    st.dataframe(df[showcols].rename(columns={"year":"ปี","province":"จังหวัด","hos_type":"รหัสประเภทหน่วยบริการ","health_need":"Health Need","sex":"รหัสเพศ","age_group":"กลุ่มอายุ","cci":"CCI","pred_rate":"อัตราพยากรณ์ต้นทาง"}),use_container_width=True,height=440)
    out=df[showcols].copy()
    csv=out.to_csv(index=False).encode("utf-8-sig")
    st.download_button("ดาวน์โหลดผลการคำนวณ CSV",data=csv,file_name=f"WISN_FTE_{year}.csv",mime="text/csv")

with st.expander("คำอธิบายสูตรและข้อควรระวัง"):
    st.markdown("""
    **สูตรหลัก**

    - บริการหลังปรับ = จำนวนบริการพยากรณ์ × (1 + Unmet Need/100)
    - ภาระงาน (ชั่วโมง) = บริการหลังปรับ × เวลามาตรฐาน (นาที/ครั้ง) ÷ 60
    - ความต้องการกำลังคน (FTE) = ภาระงาน (ชั่วโมง) ÷ AWT (ชั่วโมง/คน/ปี)

    **ข้อควรระวัง**
    1. ผลิตภัณฑ์นี้ใช้จำนวนบริการจากไฟล์ผลพยากรณ์เป็นฐาน ไม่ได้ฝึกหรือรัน Random Forest ใหม่
    2. ผลรวม FTE จะเปลี่ยนตามตัวกรอง พารามิเตอร์ และขอบเขตบริการที่เลือก
    3. AWT 1,680 ชั่วโมง/ปี และเวลามาตรฐาน 6.55 นาที/ครั้ง เป็นค่าตั้งต้นของการศึกษา ควรทบทวนความเหมาะสมก่อนใช้จริง
    4. การคำนวณราย Health Need ใช้เวลามาตรฐานเดียวกันเป็นค่าเริ่มต้นเท่านั้น สามารถปรับแยกหมวดเมื่อมีหลักฐานรองรับ
    5. ไม่ควรนำผลต่างระหว่าง FTE กับจำนวนแพทย์มาเรียกว่าการขาดแคลน หากยังไม่มีข้อมูลกำลังคนจริงและนิยามหน่วยงานที่เปรียบเทียบตรงกัน
    6. ตรวจสอบความหมายของ pred_rate และ Population กับแหล่งสร้างไฟล์ก่อนนำไปอ้างอิงเชิงนโยบาย โดยไม่ควรรวมคอลัมน์ Population ข้าม strata เพราะประชากรอาจถูกทำซ้ำในแต่ละมิติ
    """)
st.caption("Prototype สำหรับการวิจัย/ทดสอบการคำนวณ ไม่ใช่ระบบปฏิบัติการหรือคำแนะนำการจัดสรรกำลังคน")
