import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path

st.set_page_config(page_title="ระบบประมาณการความต้องการแพทย์เวชศาสตร์ครอบครัว", layout="wide")

DATA_PATH = Path(__file__).parent / "RF_F4_forecast_2569_2573_strata.csv.gz"
HEALTH_NEEDS = ["Acute", "Chronic", "Prevention"]
HEALTH_TH = {"Acute": "บริการเฉียบพลัน", "Chronic": "บริการโรคเรื้อรัง", "Prevention": "บริการส่งเสริมสุขภาพและป้องกันโรค"}
HEALTH_SHORT = {"Acute": "เฉียบพลัน", "Chronic": "โรคเรื้อรัง", "Prevention": "ส่งเสริมสุขภาพ"}
HEALTH_COLOR = {"Acute": "#C25B12", "Chronic": "#2E5A87", "Prevention": "#00703C"}
HOS_TH = {1: "หน่วยบริการปฐมภูมิ", 2: "โรงพยาบาลชุมชน", 3: "โรงพยาบาลทั่วไป", 4: "โรงพยาบาลศูนย์", 5: "โรงพยาบาลมหาวิทยาลัย", 6: "โรงพยาบาลและสถานพยาบาลอื่น ๆ"}
DEFAULTS = {"std_Acute": 6.55, "std_Chronic": 6.55, "std_Prevention": 6.55, "awt": 1680.0, "unmet": 0.0}
FONT = "Sarabun"
GREEN, GREEN_DARK, GREEN_SOFT, TOTAL_BG = "#00703C", "#004D29", "#E7F2EC", "#FFF7D6"

# ---------------------------------------------------------------- styles
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;500;600;700&display=swap');

html, body, .stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button,
.stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp [data-baseweb="select"] div, .stApp [data-baseweb="tab"], .stApp table, .stApp th, .stApp td,
.stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stCaptionContainer"] {{
  font-family: '{FONT}', sans-serif !important;
}}
[data-testid="stIconMaterial"] {{ font-family: 'Material Symbols Rounded' !important; }}
[data-testid="stDecoration"] {{ display: none; }}
.stApp {{ color: #222; }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1240px; }}

/* Top band */
.band {{ background: {GREEN}; color: #fff; padding: 12px 22px; display: flex; align-items: center; gap: 14px; }}
.band .seal {{ width: 40px; height: 40px; border-radius: 50%; background: #fff; color: {GREEN};
  display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: .78rem; flex: none; }}
.band .name {{ font-size: 1.15rem; font-weight: 700; line-height: 1.35; }}
.band .sub {{ font-size: .85rem; opacity: .9; }}

/* Tabs styled as the menu bar under the band */
.stTabs [data-baseweb="tab-list"] {{ background: {GREEN_SOFT}; border-bottom: 2px solid {GREEN}; gap: 0; padding: 0 10px; }}
.stTabs [data-baseweb="tab"] {{ color: {GREEN_DARK}; padding: 8px 14px; font-size: .95rem; background: transparent; }}
.stTabs [aria-selected="true"] {{ font-weight: 700; color: {GREEN_DARK}; }}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: {GREEN_DARK}; }}
.stTabs [data-baseweb="tab-border"] {{ display: none; }}
.stTabs [data-baseweb="tab-panel"] {{ padding-top: 18px; }}

/* Page heading inside a tab */
.ph {{ font-size: 1.3rem; font-weight: 700; margin: 0 0 2px; color: #222; }}
.pm {{ font-size: .9rem; color: #555; margin: 0 0 14px; }}

/* Table title + official table */
.tt {{ font-size: .95rem; margin: 18px 0 6px; }}
.tt b {{ font-weight: 700; }}
table.off {{ width: 100%; border-collapse: collapse; font-size: .95rem; }}
table.off th {{ background: {GREEN}; color: #fff; font-weight: 600; padding: 8px 10px; border: 1px solid {GREEN}; text-align: center; }}
table.off td {{ border: 1px solid #CFCFCF; padding: 8px 10px; text-align: right; font-variant-numeric: tabular-nums; }}
table.off td.l {{ text-align: left; }}
table.off td.c {{ text-align: center; }}
table.off tr.tot td {{ background: {TOTAL_BG}; font-weight: 700; }}
.src {{ font-size: .84rem; color: #555; margin-top: 8px; line-height: 1.7; }}

/* Sidebar as the filter column */
[data-testid="stSidebar"] {{ background: #FAFAFA; border-right: 1px solid #D9D9D9; }}
.fh {{ font-size: 1rem; font-weight: 700; color: {GREEN}; margin: 0 0 4px; }}
.fh2 {{ font-size: 1rem; font-weight: 700; color: {GREEN}; margin: 18px 0 4px; padding-top: 12px; border-top: 1px solid #DDD; }}
.stButton button, .stDownloadButton button, [data-baseweb="select"] > div, .stNumberInput input,
[data-testid="stExpander"] details {{ border-radius: 2px !important; }}
.stButton button {{ border-color: {GREEN}; color: {GREEN}; }}
.foot {{ font-size: .82rem; color: #666; border-top: 1px solid #DDD; padding-top: 10px; margin-top: 28px; }}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- data
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH, compression="gzip")
    expected = {"health_need", "province", "hos_type", "sex", "age_group", "cci", "year", "pred_rate", "Population", "จำนวนการใช้บริการ"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"ไม่พบคอลัมน์ที่จำเป็น: {', '.join(missing)}")
    df["hos_type"] = pd.to_numeric(df["hos_type"], errors="coerce").astype("Int64")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(int)
    df["จำนวนการใช้บริการ"] = pd.to_numeric(df["จำนวนการใช้บริการ"], errors="coerce").fillna(0)
    df["pred_rate"] = pd.to_numeric(df["pred_rate"], errors="coerce").fillna(0)
    return df


def age_key(a):
    try:
        return int(str(a).split("-")[0].replace("+", ""))
    except ValueError:
        return 999


try:
    data = load_data()
except Exception as e:
    st.error(f"เปิดไฟล์ข้อมูลไม่ได้: {e}")
    st.info("ให้วางไฟล์ RF_F4_forecast_2569_2573_strata.csv.gz ไว้ในโฟลเดอร์เดียวกับ app.py")
    st.stop()

for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)


def reset_params():
    for k, v in DEFAULTS.items():
        st.session_state[k] = v


years = sorted(data.year.unique().tolist())

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown('<div class="fh">เลือกข้อมูล</div>', unsafe_allow_html=True)
    year = st.selectbox("ปี พ.ศ.", years)
    provinces = ["ทุกจังหวัด"] + sorted(data.province.dropna().unique().tolist())
    province = st.selectbox("จังหวัด", provinces)
    hos_options = ["ทุกประเภท"] + sorted(data.hos_type.dropna().astype(int).unique().tolist())
    hos_pick = st.selectbox("ประเภทหน่วยบริการ", hos_options,
                            format_func=lambda x: x if x == "ทุกประเภท" else HOS_TH.get(x, str(x)))
    needs = st.multiselect("ประเภทบริการ (Health Need)", HEALTH_NEEDS, default=HEALTH_NEEDS,
                           format_func=lambda n: HEALTH_TH[n])

    st.markdown('<div class="fh2">ค่าที่ใช้คำนวณ</div>', unsafe_allow_html=True)
    standard = {}
    for n in HEALTH_NEEDS:
        standard[n] = st.number_input(f"เวลาต่อครั้ง: {HEALTH_SHORT[n]} (นาที)", min_value=0.0, max_value=240.0,
                                      step=0.25, key=f"std_{n}")
    awt = st.number_input("เวลาทำงานต่อคนต่อปี, AWT (ชั่วโมง)", min_value=1.0, max_value=3000.0, step=24.0, key="awt",
                          help="เวลาที่แพทย์ 1 คนทำงานได้จริงใน 1 ปี หลังหักวันหยุด วันลา และงานอื่นที่ไม่ใช่การตรวจรักษา")
    unmet_pct = st.number_input("เพิ่ม Unmet Need (%)", min_value=0.0, max_value=300.0, step=5.0, key="unmet",
                                help="ใช้เมื่อต้องการดูว่าถ้ามีผู้ที่ยังเข้าไม่ถึงบริการเพิ่มเข้ามา จะต้องใช้แพทย์เพิ่มเท่าไร ค่าเริ่มต้นคือ 0")
    st.caption("ค่าเริ่มต้นเป็นค่าที่ใช้ในการศึกษา: เวลาต่อครั้ง 6.55 นาที และ AWT 1,680 ชั่วโมง")
    st.button("คืนค่าเริ่มต้น", on_click=reset_params, use_container_width=True)


# ---------------------------------------------------------------- calc
def apply_filters(frame):
    out = frame[frame.health_need.isin(needs)]
    if province != "ทุกจังหวัด":
        out = out[out.province == province]
    if hos_pick != "ทุกประเภท":
        out = out[out.hos_type == hos_pick]
    return out


def add_calc(frame):
    frame = frame.copy()
    frame["ปริมาณบริการฐาน (ครั้ง)"] = frame["จำนวนการใช้บริการ"]
    frame["ปริมาณบริการหลังปรับ (ครั้ง)"] = frame["จำนวนการใช้บริการ"] * (1 + unmet_pct / 100)
    frame["เวลามาตรฐาน (นาที/ครั้ง)"] = frame.health_need.map(standard)
    frame["ภาระงาน (ชั่วโมง)"] = frame["ปริมาณบริการหลังปรับ (ครั้ง)"] * frame["เวลามาตรฐาน (นาที/ครั้ง)"] / 60
    frame["ความต้องการกำลังคน (FTE)"] = frame["ภาระงาน (ชั่วโมง)"] / awt
    return frame


# ---------------------------------------------------------------- band
st.markdown(f"""
<div class="band"><div class="seal">WISN</div>
  <div><div class="name">ระบบประมาณการความต้องการแพทย์เวชศาสตร์ครอบครัว</div>
  <div class="sub">คำนวณด้วยวิธี WISN จากจำนวนครั้งที่คาดว่าจะมาใช้บริการ ปี พ.ศ. {years[0]}–{years[-1]}</div></div>
</div>""", unsafe_allow_html=True)

if not needs:
    st.warning("ยังไม่ได้เลือกประเภทบริการ ให้เลือกอย่างน้อย 1 ประเภทที่ช่องด้านซ้าย")
    st.stop()

scoped = apply_filters(data)
df = scoped[scoped.year == year]
if df.empty:
    st.warning("ไม่มีข้อมูลตามที่เลือก ลองเปลี่ยนจังหวัดหรือประเภทหน่วยบริการ")
    st.stop()

df = add_calc(df)
df["ประเภทบริการ"] = df.health_need.map(HEALTH_TH)
df["ประเภทหน่วยบริการ"] = df.hos_type.astype(int).map(HOS_TH)

basevol = df["ปริมาณบริการฐาน (ครั้ง)"].sum()
volume = df["ปริมาณบริการหลังปรับ (ครั้ง)"].sum()
workhours = df["ภาระงาน (ชั่วโมง)"].sum()
fte = df["ความต้องการกำลังคน (FTE)"].sum()
avg_std = workhours * 60 / volume if volume else 0

place = "ทุกจังหวัด" if province == "ทุกจังหวัด" else f"จังหวัด{province}"
hos_label = "ทุกประเภทหน่วยบริการ" if hos_pick == "ทุกประเภท" else HOS_TH.get(hos_pick, str(hos_pick))
need_label = "บริการทุกประเภท" if len(needs) == 3 else " ".join(HEALTH_TH[n] for n in needs)
scope_line = f"{place} {hos_label} {need_label}"


# ---------------------------------------------------------------- helpers
def table_title(no, text):
    st.markdown(f'<div class="tt"><b>{no}</b> {text}</div>', unsafe_allow_html=True)


def off_table(headers, rows, total=None):
    """rows: list of lists of (value, align) where align in {'l','c','r'}."""
    def tr(cells, cls=""):
        tds = "".join(f'<td class="{a}">{v}</td>' for v, a in cells)
        return f'<tr class="{cls}">{tds}</tr>'
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join(tr(r) for r in rows) + (tr(total, "tot") if total else "")
    st.markdown(f'<table class="off"><tr>{head}</tr>{body}</table>', unsafe_allow_html=True)


def chart_cfg(c, height):
    return (c.properties(height=height)
            .configure(font=FONT)
            .configure_view(strokeWidth=0)
            .configure_axis(labelFontSize=13, titleFontSize=13, titleFontWeight="normal", labelColor="#333", titleColor="#333",
                            gridColor="#E6E6E6", domainColor="#999", tickColor="#999")
            .configure_legend(labelFontSize=13, titleFontSize=13, titleFontWeight="normal", orient="top", symbolType="square"))


need_scale = alt.Scale(domain=[HEALTH_SHORT[n] for n in HEALTH_NEEDS], range=[HEALTH_COLOR[n] for n in HEALTH_NEEDS])
SOURCE = "ที่มา: ผลพยากรณ์จำนวนครั้งการใช้บริการด้วยแบบจำลอง Random Forest"

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["ภาพรวม", "รายหน่วยบริการ", "แนวโน้ม 5 ปี", "รายกลุ่มอายุและจังหวัด", "ดาวน์โหลดข้อมูล", "วิธีคำนวณ"])

# ---------------------------------------------------------------- overview
with tab1:
    st.markdown(f'<div class="ph">ความต้องการแพทย์เวชศาสตร์ครอบครัว ปี {year}</div><div class="pm">{scope_line}</div>',
                unsafe_allow_html=True)
    table_title("ตารางที่ 1", f"ขั้นตอนการคำนวณจำนวนแพทย์ที่ต้องการ ปี {year}")
    off_table(["รายการ", "หน่วย", "จำนวน"], [
        [("1. จำนวนครั้งที่คาดว่าจะมาใช้บริการ", "l"), ("ครั้ง", "c"), (f"{basevol:,.0f}", "r")],
        [(f"2. จำนวนครั้งหลังเพิ่ม Unmet Need {unmet_pct:g}%", "l"), ("ครั้ง", "c"), (f"{volume:,.0f}", "r")],
        [(f"3. เวลาที่แพทย์ต้องใช้ (ข้อ 2 × {avg_std:,.2f} นาที ÷ 60)", "l"), ("ชั่วโมง", "c"), (f"{workhours:,.0f}", "r")],
    ], total=[(f"4. จำนวนแพทย์ที่ต้องการ (ข้อ 3 ÷ {awt:,.0f} ชั่วโมง)", "l"), ("FTE", "c"), (f"{fte:,.2f}", "r")])
    st.markdown(f"""<div class="src">หมายเหตุ: 1 FTE เท่ากับแพทย์ที่ทำงานเต็มเวลา 1 คน ตัวเลขนี้ยังไม่ได้เทียบกับจำนวนแพทย์ที่มีอยู่จริง
    จึงยังบอกไม่ได้ว่าขาดหรือเกินเท่าไร<br>{SOURCE}</div>""", unsafe_allow_html=True)

    by_need = df.groupby("health_need").agg(
        visits=("ปริมาณบริการหลังปรับ (ครั้ง)", "sum"), hours=("ภาระงาน (ชั่วโมง)", "sum"),
        fte=("ความต้องการกำลังคน (FTE)", "sum")).reindex(needs).fillna(0)
    table_title("ตารางที่ 2", f"จำนวนแพทย์ที่ต้องการ แยกตามประเภทบริการ ปี {year}")
    off_table(["ประเภทบริการ", "จำนวนครั้ง", "ชั่วโมง", "FTE", "ร้อยละ"],
              [[(HEALTH_TH[n], "l"), (f"{r.visits:,.0f}", "r"), (f"{r.hours:,.0f}", "r"), (f"{r.fte:,.2f}", "r"),
                (f"{(r.fte / fte * 100 if fte else 0):.1f}", "r")] for n, r in by_need.iterrows()],
              total=[("รวม", "l"), (f"{volume:,.0f}", "r"), (f"{workhours:,.0f}", "r"), (f"{fte:,.2f}", "r"), ("100.0", "r")])

    table_title("ภาพที่ 1", f"จำนวนแพทย์ที่ต้องการ แยกตามประเภทบริการ ปี {year}")
    bn = by_need.reset_index().assign(กลุ่ม=lambda d: d.health_need.map(HEALTH_SHORT))
    base = alt.Chart(bn).encode(
        y=alt.Y("กลุ่ม:N", sort="-x", title=None),
        x=alt.X("fte:Q", title="FTE", scale=alt.Scale(domain=[0, float(bn.fte.max()) * 1.2 or 1])),
        tooltip=[alt.Tooltip("กลุ่ม:N", title="ประเภทบริการ"), alt.Tooltip("fte:Q", title="FTE", format=",.2f")])
    bars = base.mark_bar(size=28).encode(color=alt.Color("กลุ่ม:N", scale=need_scale, legend=None))
    labels = base.mark_text(align="left", dx=6, fontSize=13, color="#222").encode(text=alt.Text("fte:Q", format=",.2f"))
    st.altair_chart(chart_cfg(bars + labels, 56 * len(bn) + 30), use_container_width=True)

# ---------------------------------------------------------------- by service unit
with tab2:
    st.markdown(f'<div class="ph">จำนวนแพทย์ที่ต้องการ รายประเภทหน่วยบริการ ปี {year}</div><div class="pm">{scope_line}</div>',
                unsafe_allow_html=True)
    s2 = df.groupby("ประเภทหน่วยบริการ", as_index=False).agg(
        visits=("ปริมาณบริการหลังปรับ (ครั้ง)", "sum"), hours=("ภาระงาน (ชั่วโมง)", "sum"), fte=("ความต้องการกำลังคน (FTE)", "sum"))
    s2 = s2.sort_values("fte", ascending=False)
    table_title("ตารางที่ 3", "จำนวนแพทย์ที่ต้องการ แยกตามประเภทหน่วยบริการ เรียงจากมากไปน้อย")
    off_table(["ประเภทหน่วยบริการ", "จำนวนครั้ง", "ชั่วโมง", "FTE"],
              [[(r["ประเภทหน่วยบริการ"], "l"), (f"{r.visits:,.0f}", "r"), (f"{r.hours:,.0f}", "r"), (f"{r.fte:,.2f}", "r")]
               for _, r in s2.iterrows()],
              total=[("รวม", "l"), (f"{s2.visits.sum():,.0f}", "r"), (f"{s2.hours.sum():,.0f}", "r"), (f"{s2.fte.sum():,.2f}", "r")])

    s2_need = df.assign(กลุ่ม=df.health_need.map(HEALTH_SHORT)).groupby(["ประเภทหน่วยบริการ", "กลุ่ม"], as_index=False)["ความต้องการกำลังคน (FTE)"].sum()
    table_title("ภาพที่ 2", "จำนวนแพทย์ที่ต้องการ แยกตามประเภทหน่วยบริการและประเภทบริการ")
    c2 = alt.Chart(s2_need).mark_bar(size=22).encode(
        y=alt.Y("ประเภทหน่วยบริการ:N", sort=s2["ประเภทหน่วยบริการ"].tolist(), title=None, axis=alt.Axis(labelLimit=260)),
        x=alt.X("ความต้องการกำลังคน (FTE):Q", title="FTE", stack="zero"),
        color=alt.Color("กลุ่ม:N", scale=need_scale, title="ประเภทบริการ"),
        tooltip=[alt.Tooltip("ประเภทหน่วยบริการ:N"), alt.Tooltip("กลุ่ม:N", title="ประเภทบริการ"),
                 alt.Tooltip("ความต้องการกำลังคน (FTE):Q", title="FTE", format=",.2f")])
    st.altair_chart(chart_cfg(c2, 42 * len(s2) + 50), use_container_width=True)

# ---------------------------------------------------------------- trend
with tab3:
    st.markdown(f'<div class="ph">แนวโน้มจำนวนแพทย์ที่ต้องการ ปี {years[0]}–{years[-1]}</div><div class="pm">{scope_line} (ใช้ค่าคำนวณชุดเดียวกันทุกปี)</div>',
                unsafe_allow_html=True)
    trend = add_calc(scoped)
    t_tot = trend.groupby("year", as_index=False)["ความต้องการกำลังคน (FTE)"].sum()
    t_need = trend.assign(กลุ่ม=trend.health_need.map(HEALTH_SHORT)).groupby(["year", "กลุ่ม"], as_index=False)["ความต้องการกำลังคน (FTE)"].sum()
    wide = t_need.pivot(index="year", columns="กลุ่ม", values="ความต้องการกำลังคน (FTE)").fillna(0)

    cols = [HEALTH_SHORT[n] for n in needs]
    table_title("ตารางที่ 4", "จำนวนแพทย์ที่ต้องการ (FTE) รายปี แยกตามประเภทบริการ")
    off_table(["ปี พ.ศ."] + [HEALTH_TH[n] for n in needs] + ["รวม"],
              [[(str(y), "c")] + [(f"{wide.loc[y].get(c, 0):,.2f}", "r") for c in cols] +
               [(f"{t_tot.set_index('year').loc[y].iloc[0]:,.2f}", "r")] for y in wide.index])
    first, last = t_tot.iloc[0, 1], t_tot.iloc[-1, 1]
    if first:
        st.markdown(f'<div class="src">ปี {years[-1]} ต้องการแพทย์{"เพิ่มขึ้น" if last >= first else "ลดลง"}จากปี {years[0]} '
                    f'{abs(last - first):,.2f} FTE หรือร้อยละ {abs(last / first - 1) * 100:.1f}</div>', unsafe_allow_html=True)

    table_title("ภาพที่ 3", f"จำนวนแพทย์ที่ต้องการรายปี แยกตามประเภทบริการ ปี {years[0]}–{years[-1]}")
    tln = alt.Chart(t_need).mark_line(point=alt.OverlayMarkDef(size=50, filled=True), strokeWidth=2).encode(
        x=alt.X("year:O", title="ปี พ.ศ.", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("ความต้องการกำลังคน (FTE):Q", title="FTE", scale=alt.Scale(zero=False)),
        color=alt.Color("กลุ่ม:N", scale=need_scale, title="ประเภทบริการ"),
        tooltip=[alt.Tooltip("year:O", title="ปี"), alt.Tooltip("กลุ่ม:N", title="ประเภทบริการ"),
                 alt.Tooltip("ความต้องการกำลังคน (FTE):Q", title="FTE", format=",.2f")])
    st.altair_chart(chart_cfg(tln, 320), use_container_width=True)

# ---------------------------------------------------------------- age / province
with tab4:
    st.markdown(f'<div class="ph">จำนวนแพทย์ที่ต้องการ รายกลุ่มอายุและจังหวัด ปี {year}</div><div class="pm">{scope_line}</div>',
                unsafe_allow_html=True)
    ag = df.assign(กลุ่ม=df.health_need.map(HEALTH_SHORT)).groupby(["age_group", "กลุ่ม"], as_index=False)["ความต้องการกำลังคน (FTE)"].sum()
    age_order = sorted(ag.age_group.unique().tolist(), key=age_key)
    table_title("ภาพที่ 4", "จำนวนแพทย์ที่ต้องการ แยกตามกลุ่มอายุของผู้รับบริการ")
    ca = alt.Chart(ag).mark_bar().encode(
        x=alt.X("age_group:N", sort=age_order, title="กลุ่มอายุ (ปี)", axis=alt.Axis(labelAngle=-40)),
        y=alt.Y("ความต้องการกำลังคน (FTE):Q", title="FTE", stack="zero"),
        color=alt.Color("กลุ่ม:N", scale=need_scale, title="ประเภทบริการ"),
        tooltip=[alt.Tooltip("age_group:N", title="กลุ่มอายุ"), alt.Tooltip("กลุ่ม:N", title="ประเภทบริการ"),
                 alt.Tooltip("ความต้องการกำลังคน (FTE):Q", title="FTE", format=",.2f")])
    st.altair_chart(chart_cfg(ca, 320), use_container_width=True)

    if province == "ทุกจังหวัด":
        pv = df.groupby("province", as_index=False)["ความต้องการกำลังคน (FTE)"].sum().sort_values("ความต้องการกำลังคน (FTE)", ascending=False)
        top_n = st.slider("จำนวนจังหวัดที่แสดง", 5, len(pv), min(15, len(pv)))
        table_title("ภาพที่ 5", f"{top_n} จังหวัดที่ต้องการแพทย์มากที่สุด ปี {year}")
        cp = alt.Chart(pv.head(top_n)).mark_bar(color=GREEN, size=14).encode(
            y=alt.Y("province:N", sort="-x", title=None),
            x=alt.X("ความต้องการกำลังคน (FTE):Q", title="FTE"),
            tooltip=[alt.Tooltip("province:N", title="จังหวัด"), alt.Tooltip("ความต้องการกำลังคน (FTE):Q", title="FTE", format=",.2f")])
        st.altair_chart(chart_cfg(cp, 22 * top_n + 40), use_container_width=True)
    else:
        st.caption("ถ้าต้องการเปรียบเทียบรายจังหวัด ให้เลือก “ทุกจังหวัด” ที่ช่องด้านซ้าย")

# ---------------------------------------------------------------- download
with tab5:
    showcols = ["year", "province", "hos_type", "ประเภทหน่วยบริการ", "health_need", "sex", "age_group", "cci", "pred_rate", "Population",
                "ปริมาณบริการฐาน (ครั้ง)", "ปริมาณบริการหลังปรับ (ครั้ง)", "เวลามาตรฐาน (นาที/ครั้ง)", "ภาระงาน (ชั่วโมง)", "ความต้องการกำลังคน (FTE)"]
    out = df[showcols].copy()
    st.markdown(f'<div class="ph">ข้อมูลรายกลุ่มย่อย ปี {year}</div><div class="pm">{scope_line} จำนวน {len(out):,} แถว</div>',
                unsafe_allow_html=True)
    st.download_button("ดาวน์โหลดไฟล์ CSV", data=out.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"WISN_FTE_{year}.csv", mime="text/csv")
    st.dataframe(out.rename(columns={"year": "ปี", "province": "จังหวัด", "hos_type": "รหัสหน่วยบริการ", "health_need": "ประเภทบริการ",
                                     "sex": "รหัสเพศ", "age_group": "กลุ่มอายุ", "cci": "CCI", "pred_rate": "อัตราที่พยากรณ์"}),
                 use_container_width=True, height=460, hide_index=True)

# ---------------------------------------------------------------- method
with tab6:
    st.markdown('<div class="ph">วิธีคำนวณ</div>', unsafe_allow_html=True)
    st.markdown("""
ระบบนี้นำจำนวนครั้งที่คาดว่าจะมาใช้บริการ ซึ่งพยากรณ์ไว้ล่วงหน้าแล้ว มาคำนวณเป็นจำนวนแพทย์ตามวิธี WISN ดังนี้

1. จำนวนครั้งหลังปรับ = จำนวนครั้งที่พยากรณ์ × (1 + Unmet Need ÷ 100)
2. เวลาที่แพทย์ต้องใช้ (ชั่วโมง) = จำนวนครั้งหลังปรับ × เวลาต่อครั้ง (นาที) ÷ 60
3. จำนวนแพทย์ที่ต้องการ (FTE) = เวลาที่แพทย์ต้องใช้ ÷ AWT

**ข้อควรทราบ**

- ระบบไม่ได้สร้างแบบจำลองพยากรณ์ใหม่ แต่ใช้ผลพยากรณ์ที่ทำไว้แล้วจากไฟล์ข้อมูล
- ค่าเริ่มต้น เวลาต่อครั้ง 6.55 นาที และ AWT 1,680 ชั่วโมงต่อปี มาจากการศึกษานี้ ถ้าจะนำไปใช้กับพื้นที่จริง ควรตรวจสอบค่าให้ตรงกับพื้นที่ก่อน
- เวลาต่อครั้งของบริการทั้ง 3 ประเภทตั้งไว้เท่ากัน ถ้ามีข้อมูลเวลาจริงของแต่ละประเภท สามารถแก้ได้ที่ช่องด้านซ้าย
- จำนวน FTE ยังไม่ได้เทียบกับจำนวนแพทย์ที่มีอยู่ จึงไม่ควรนำไปเรียกว่าจำนวนแพทย์ที่ขาด
- คอลัมน์ Population ในไฟล์ดาวน์โหลดเป็นค่าของแต่ละกลุ่มย่อย ไม่ควรนำมารวมกัน เพราะประชากรกลุ่มเดียวกันอาจถูกนับซ้ำ
""")

st.markdown('<div class="foot">ระบบต้นแบบที่พัฒนาขึ้นประกอบวิทยานิพนธ์ ใช้สำหรับศึกษาและทดลองคำนวณ ยังไม่ใช่ระบบที่ใช้จัดสรรอัตรากำลังจริง</div>',
            unsafe_allow_html=True)
