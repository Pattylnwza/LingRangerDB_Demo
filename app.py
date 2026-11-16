
import os
import re
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="ลิง Ranger DB_Thai LCI & LCA", page_icon="🌱", layout="wide")

st.markdown("""
<style>
/* Base layout: keep the existing desktop design. */
.stApp {background: #f5f8f6;}
.block-container {
    padding-top: 1.4rem;
    padding-left: clamp(1rem, 3vw, 2rem);
    padding-right: clamp(1rem, 3vw, 2rem);
    max-width: 1500px;
}
.hero {
    background: linear-gradient(115deg,#123d32,#24745c);
    padding: 26px 30px;
    border-radius: 18px;
    color: white;
    margin-bottom: 18px;
}
.hero h1 {color:white; margin:0; font-size:2rem; line-height:1.25;}
.hero p {color:#d8eee4; margin:8px 0 0 0; line-height:1.5;}
div[data-testid="stMetric"] {
    background:white;
    border:1px solid #e2ebe5;
    padding:14px;
    border-radius:14px;
    min-width:0;
}
.note {
    background:#fff8e7;
    border-left:4px solid #e3a72f;
    padding:12px 15px;
    border-radius:8px;
    color:#604b1b;
}
.small-muted {color:#64748b; font-size:0.88rem;}

/* Prevent charts and tables from exceeding the available screen width. */
div[data-testid="stPlotlyChart"],
div[data-testid="stDataFrame"],
div[data-testid="stTable"] {
    max-width:100%;
    min-width:0;
}

/* Tablet: wrap multi-column sections into two columns. */
@media (max-width: 900px) {
    .block-container {
        padding-top: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 0.75rem !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        flex: 1 1 calc(50% - 0.75rem) !important;
        width: calc(50% - 0.75rem) !important;
        max-width: calc(50% - 0.75rem) !important;
        min-width: 0 !important;
    }
    .hero {padding: 22px 24px;}
    .hero h1 {font-size: 1.7rem;}
}

/* Mobile: stack columns vertically and use more compact spacing. */
@media (max-width: 600px) {
    .block-container {
        padding-top: 0.75rem;
        padding-left: 0.75rem;
        padding-right: 0.75rem;
    }
    div[data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
        gap: 0.65rem !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        flex: 1 1 100% !important;
        width: 100% !important;
        max-width: 100% !important;
        min-width: 0 !important;
    }
    .hero {
        padding: 18px;
        border-radius: 14px;
        margin-bottom: 14px;
    }
    .hero h1 {font-size: 1.35rem;}
    .hero p {font-size: 0.9rem;}
    div[data-testid="stMetric"] {padding: 11px;}
    div[data-testid="stMetricLabel"] {font-size: 0.82rem;}
    div[data-testid="stMetricValue"] {font-size: 1.35rem;}
    h1 {font-size: 1.45rem !important;}
    h2 {font-size: 1.25rem !important;}
    h3 {font-size: 1.1rem !important;}
    button, [data-testid="stDownloadButton"] button {
        max-width: 100%;
        white-space: normal;
    }
}
</style>
""", unsafe_allow_html=True)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TABLES = ["flow_category", "geography", "lci_exchange", "lci_flow", "lci_process", "lci_source", "technology", "unit"]

@st.cache_data
def load_csv_tables():
    """Load only the supplied CSV files; no generated or inferred observations are added."""
    missing = [name + ".csv" for name in TABLES if not os.path.exists(os.path.join(DATA_DIR, name + ".csv"))]
    if missing:
        raise FileNotFoundError("ไม่พบไฟล์ในโฟลเดอร์ data: " + ", ".join(missing))
    return {name: pd.read_csv(os.path.join(DATA_DIR, name + ".csv")) for name in TABLES}

try:
    D = load_csv_tables()
except Exception as exc:
    st.error(f"โหลด CSV ไม่สำเร็จ: {exc}")
    st.info("ตรวจสอบว่าไฟล์ CSV ทั้ง 8 ไฟล์อยู่ในโฟลเดอร์ data ซึ่งอยู่ระดับเดียวกับ app.py")
    st.stop()

proc = D["lci_process"].copy()
exch = D["lci_exchange"].copy()
flows = D["lci_flow"].copy()
units = D["unit"].copy()
tech = D["technology"].copy()
sources = D["lci_source"].copy()

# Scope filter: exclude these two flows from every feature in this submission.
EXCLUDED_FLOW_NAMES = {"agricultural waste", "municipal solid waste"}
excluded_flow_mask = flows["flow_name"].astype(str).str.strip().str.casefold().isin(EXCLUDED_FLOW_NAMES)
excluded_flow_ids = flows.loc[excluded_flow_mask, "flow_id"].dropna().tolist()
flows_in_scope = flows.loc[~excluded_flow_mask].copy()
exch = exch[~exch["flow_id"].isin(excluded_flow_ids)].copy()

# Normalize key fields without filling missing values or inventing records.
for frame, columns in [
    (proc, ["process_id", "reference_year", "reference_month", "technology_id", "source_id", "geography_id"]),
    (exch, ["exchange_id", "process_id", "flow_id", "unit_id", "source_id"]),
    (flows, ["flow_id", "category_id"]),
    (units, ["unit_id"]),
    (tech, ["technology_id"]),
    (sources, ["source_id", "source_year"]),
]:
    for col in columns:
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
exch["amount"] = pd.to_numeric(exch["amount"], errors="coerce")

# Join the exchange to its process, flow, unit, technology and documented source.
joined = (
    exch.merge(
        proc[["process_id", "reference_year", "reference_month", "technology_id", "source_id", "process_name", "description"]],
        on="process_id", how="left", suffixes=("_exchange", "_process"), validate="many_to_one"
    )
    .merge(flows_in_scope[["flow_id", "flow_name", "category_id", "flow_type", "compartment"]],
           on="flow_id", how="left", validate="many_to_one")
    .merge(units[["unit_id", "unit_name", "unit_symbol", "dimension"]],
           on="unit_id", how="left", validate="many_to_one")
    .merge(tech[["technology_id", "technology_name"]],
           on="technology_id", how="left", validate="many_to_one")
)

# Keep provenance IDs separately and verify that exchange and process cite the same source.
joined = joined.rename(columns={"source_id_exchange": "exchange_source_id", "source_id_process": "process_source_id"})
joined = joined.merge(
    sources[["source_id", "source_name", "source_type", "publisher", "source_year", "reference_url", "notes"]].rename(columns={"notes": "source_notes"}),
    left_on="exchange_source_id", right_on="source_id", how="left", validate="many_to_one"
)
joined["reference_year"] = pd.to_numeric(joined["reference_year"], errors="coerce")
joined["reference_month"] = pd.to_numeric(joined["reference_month"], errors="coerce")

# Evidence gate: only records with an existing source row, URL, and matching source IDs are eligible.
joined["source_id_match"] = (
    joined["exchange_source_id"].notna()
    & joined["process_source_id"].notna()
    & (joined["exchange_source_id"] == joined["process_source_id"])
)
joined["has_source_reference"] = (
    joined["source_name"].notna()
    & joined["publisher"].notna()
    & joined["reference_url"].fillna("").astype(str).str.strip().ne("")
)
joined["is_traceable"] = joined["source_id_match"] & joined["has_source_reference"]
verified = joined[joined["is_traceable"]].copy()

st.sidebar.markdown("## 🌱 ลิง Ranger DB")
page = st.sidebar.radio("เมนูหลัก", ["Dashboard", "Data Explorer", "Data Comparison", "AI Data Chatbot"])
st.sidebar.caption("Data source: CSV files only")
st.sidebar.caption(f"ข้อมูลที่ตรวจสอบแหล่งอ้างอิงแล้ว: {len(verified):,} / {len(joined):,} exchanges")
st.sidebar.caption("ไม่มีการสร้างหรือเติมค่าข้อมูลที่ไม่มีใน CSV")

st.markdown("""
<div class="hero">
<h1>Thai Electricity & Power Generation</h1>
<p>LCI Data Intelligence Platform · สำรวจ วิเคราะห์ และเปรียบเทียบข้อมูลการผลิตไฟฟ้าของประเทศไทย</p>
</div>
""", unsafe_allow_html=True)

if verified.empty:
    st.error("ไม่พบรายการที่ผ่านการตรวจสอบ Provenance กรุณาตรวจสอบ source_id และ reference_url ใน CSV")
    st.stop()

years = sorted(verified["reference_year"].dropna().astype(int).unique().tolist())
if not years:
    st.error("ไม่พบปีอ้างอิงในข้อมูล CSV")
    st.stop()
default_year = 2022 if 2022 in years else years[-1]


def get_co2_by_year(df):
    # Use exact CO2 OUTPUT records only; no estimates, interpolation, or extrapolation.
    mask = (
        df["direction"].astype(str).str.strip().str.upper().eq("OUTPUT")
        & df["flow_name"].astype(str).str.match(r"^CO2(?:\s|$|-)", case=False, na=False)
    )
    return df[mask & df["amount"].notna() & df["reference_year"].notna()].copy()

co2_records = get_co2_by_year(verified)
co2_data = co2_records.groupby(["reference_year", "flow_name", "unit_symbol"], as_index=False)["amount"].sum()

if page == "Dashboard":
    st.subheader("Dashboard ภาพรวม")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("จำนวน Process", f"{verified['process_id'].nunique():,}")
    c2.metric("Exchange ที่มี Provenance", f"{len(verified):,}")
    c3.metric("ช่วงปีที่มีแหล่งอ้างอิง", f"{int(min(years))}–{int(max(years))}")
    c4.metric("จำนวน Flow", f"{flows_in_scope['flow_id'].nunique():,}")

    st.markdown("### ภาพรวมการปล่อย CO₂ จากข้อมูลที่มีแหล่งอ้างอิง")
    co2_year = co2_records.groupby(["reference_year", "unit_symbol"], as_index=False)["amount"].sum()
    if not co2_year.empty:
        co2_year["reference_year"] = co2_year["reference_year"].astype(int)
        co2_year = co2_year.sort_values("reference_year")
        fig = px.line(
            co2_year, x="reference_year", y="amount", color="unit_symbol", markers=True,
            labels={"reference_year": "ปี", "amount": "ปริมาณ CO₂", "unit_symbol": "หน่วย"},
            title="CO₂ emissions reported in source CSVs (annual)"
        )
        actual_years = sorted(co2_year["reference_year"].unique().tolist())
        fig.update_xaxes(tickmode="array", tickvals=actual_years,
                         ticktext=[str(y) for y in actual_years])
        # Do not visually bridge missing years in the series.
        fig.update_traces(connectgaps=False)
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig, width="stretch")
        st.caption("จุดข้อมูลมาจาก CO₂ OUTPUT ที่มี source_id ตรงกันระหว่าง lci_exchange.csv และ lci_process.csv และมี URL ใน lci_source.csv เท่านั้น")
    else:
        st.info("ไม่พบข้อมูล CO₂ ที่มีแหล่งอ้างอิงครบถ้วนใน CSV")

    left, right = st.columns(2)
    with left:
        st.markdown("### CO₂ แยกตามประเภท")
        co2_years = sorted(co2_records["reference_year"].dropna().astype(int).unique().tolist())
        if co2_years:
            selected_year = st.selectbox("เลือกปีสำหรับกราฟ", co2_years,
                                         index=co2_years.index(default_year) if default_year in co2_years else len(co2_years)-1,
                                         key="dash_year")
            part = co2_records[co2_records.reference_year == selected_year]
            if not part.empty:
                part_summary = part.groupby(["flow_name", "unit_symbol"], as_index=False)["amount"].sum()
                fig = px.bar(part_summary, x="flow_name", y="amount", color="unit_symbol",
                             labels={"flow_name": "ประเภท", "amount": "ปริมาณ", "unit_symbol": "หน่วย"},
                             title=f"CO₂ by flow · {selected_year}")
                fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
                st.plotly_chart(fig, width="stretch")
        else:
            st.info("ไม่มีข้อมูล CO₂ ที่ตรวจสอบแหล่งที่มาได้")

    with right:
        st.markdown("### ปริมาณไฟฟ้าที่ผลิต/รายงาน")
        electricity = verified[(verified.direction.astype(str).str.upper() == "OUTPUT") &
                               verified.flow_name.astype(str).str.startswith("Electricity", na=False) &
                               verified.amount.notna() & verified.reference_year.notna()]
        elec_year = electricity.groupby(["reference_year", "flow_name", "unit_symbol"], as_index=False)["amount"].sum()
        if not elec_year.empty:
            fig = px.area(elec_year, x="reference_year", y="amount", color="flow_name",
                          labels={"reference_year": "ปี", "amount": "ปริมาณไฟฟ้า", "flow_name": "ประเภทไฟฟ้า"},
                          hover_data=["unit_symbol"], title="Electricity output by reported type")
            fig.update_traces(connectgaps=False)
            fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("ไม่พบข้อมูล Electricity output ที่มีแหล่งอ้างอิงครบถ้วน")

    st.markdown('<div class="note"><b>ข้อควรทราบ:</b> แสดงเฉพาะข้อมูลที่มีแถวอ้างอิงใน lci_source.csv และ URL ต้นทาง ไม่ได้ประมาณค่าในปีที่ไม่มีข้อมูล ข้อมูล CO₂ นี้ไม่ใช่ค่า GWP (kg CO₂-eq) หรือ Carbon Intensity ต่อ kWh โดยอัตโนมัติ</div>', unsafe_allow_html=True)

elif page == "Data Explorer":
    st.subheader("Data Explorer")
    st.write("ทุกแถวในตารางผ่านการตรวจสอบแหล่งอ้างอิงแล้ว สามารถเปิด URL ในคอลัมน์ Provenance เพื่อ Trace back ไปยังแหล่งข้อมูลต้นทาง")
    a, b, c = st.columns(3)
    with a:
        year_options = ["ทั้งหมด"] + years
        year_choice = st.selectbox("ปีอ้างอิง", year_options, index=year_options.index(default_year) if default_year in year_options else 0)
    with b:
        direction_choice = st.selectbox("ทิศทาง", ["ทั้งหมด", "INPUT", "OUTPUT"])
    with c:
        flow_options = ["ทั้งหมด"] + sorted(verified.flow_name.dropna().astype(str).unique().tolist())
        flow_choice = st.selectbox("Flow", flow_options)
    search = st.text_input("ค้นหาชื่อ Process / Flow / Technology / Source", placeholder="เช่น Natural Gas, CO2, EPPO")

    view = verified.copy()
    if year_choice != "ทั้งหมด":
        view = view[view.reference_year == year_choice]
    if direction_choice != "ทั้งหมด":
        view = view[view.direction.astype(str).str.upper() == direction_choice]
    if flow_choice != "ทั้งหมด":
        view = view[view.flow_name == flow_choice]
    if search:
        mask = (
            view.process_name.astype(str).str.contains(search, case=False, na=False) |
            view.flow_name.astype(str).str.contains(search, case=False, na=False) |
            view.technology_name.astype(str).str.contains(search, case=False, na=False) |
            view.source_name.astype(str).str.contains(search, case=False, na=False) |
            view.publisher.astype(str).str.contains(search, case=False, na=False)
        )
        view = view[mask]

    st.caption(f"พบ {len(view):,} รายการที่มี Provenance")
    display_cols = [
        "exchange_id", "process_id", "reference_year", "reference_month", "process_name",
        "technology_name", "flow_name", "direction", "amount", "unit_symbol",
        "exchange_source_id", "source_name", "publisher", "source_year", "reference_url", "source_notes", "notes"
    ]
    display = view[[col for col in display_cols if col in view.columns]].copy()
    display = display.rename(columns={
        "exchange_id": "Exchange ID", "process_id": "Process ID", "reference_year": "ปี",
        "reference_month": "เดือน", "process_name": "Process", "technology_name": "Technology",
        "flow_name": "Flow", "direction": "Direction", "amount": "Amount", "unit_symbol": "Unit",
        "exchange_source_id": "Source ID", "source_name": "Source name", "publisher": "Publisher",
        "source_year": "Source publication year", "reference_url": "Provenance URL", "source_notes": "Source notes", "notes": "Exchange notes"
    })
    st.dataframe(display, width="stretch", hide_index=True, column_config={
        "Provenance URL": st.column_config.LinkColumn("Provenance / Trace back", display_text="เปิดแหล่งอ้างอิง"),
        "Amount": st.column_config.NumberColumn("Amount", format="%,.4f"),
    })
    st.download_button("ดาวน์โหลดผลการค้นหา CSV พร้อม Provenance",
                       view.to_csv(index=False).encode("utf-8-sig"),
                       "lci_explorer_with_provenance.csv", "text/csv")

    with st.expander("รายละเอียด Trace back ของรายการที่เลือก"):
        if not view.empty:
            selected_exchange = st.selectbox("เลือก Exchange ID", view.exchange_id.astype(int).tolist())
            record = view[view.exchange_id == selected_exchange].iloc[0]
            st.markdown(f"**Exchange ID:** {int(record.exchange_id)}  ·  **Process ID:** {int(record.process_id)}")
            st.markdown(f"**Process:** {record.process_name}")
            st.markdown(f"**Flow:** {record.flow_name} · **Amount:** {record.amount} {record.unit_symbol}")
            st.markdown(f"**Source:** {record.source_name}")
            st.markdown(f"**Publisher:** {record.publisher} · **Source year:** {int(record.source_year) if pd.notna(record.source_year) else 'ไม่ระบุ'}")
            st.markdown(f"**Source ID:** {int(record.exchange_source_id)}")
            st.markdown(f"**Reference:** [{record.reference_url}]({record.reference_url})")
            if pd.notna(record.source_notes):
                st.write(f"**Source notes:** {record.source_notes}")
            if pd.notna(record.notes):
                st.write(f"**Exchange notes:** {record.notes}")
            if pd.notna(record.description):
                st.write(f"**Process description:** {record.description}")
        else:
            st.info("ไม่มีรายการให้ตรวจสอบ")

elif page == "Data Comparison":
    st.subheader("Data Comparison")
    mode = st.radio("รูปแบบการเปรียบเทียบ", ["CO₂ emissions", "Electricity output", "Fuel input"], horizontal=True)
    if mode == "CO₂ emissions":
        available_years = sorted(co2_records.reference_year.dropna().astype(int).unique().tolist())
    elif mode == "Electricity output":
        subset = verified[(verified.direction.astype(str).str.upper() == "OUTPUT") & verified.flow_name.astype(str).str.startswith("Electricity", na=False)]
        available_years = sorted(subset.reference_year.dropna().astype(int).unique().tolist())
    else:
        subset = verified[verified.direction.astype(str).str.upper() == "INPUT"]
        available_years = sorted(subset.reference_year.dropna().astype(int).unique().tolist())
    if not available_years:
        st.info("ไม่มีข้อมูลที่มี Provenance สำหรับหัวข้อที่เลือก")
    else:
        y1, y2 = st.columns(2)
        with y1:
            year_a = st.selectbox("ปีที่ต้องการดู", available_years,
                                  index=available_years.index(default_year) if default_year in available_years else len(available_years)-1,
                                  key="comp_year")
        with y2:
            chart_type = st.selectbox("รูปแบบกราฟ", ["Bar", "Table"])
        if mode == "CO₂ emissions":
            comp = co2_records[co2_records.reference_year == year_a]
            label = "CO₂ (หน่วยตาม CSV)"
        elif mode == "Electricity output":
            comp = verified[(verified.direction.astype(str).str.upper() == "OUTPUT") &
                            verified.flow_name.astype(str).str.startswith("Electricity", na=False) &
                            (verified.reference_year == year_a)]
            label = "Electricity (หน่วยตาม CSV)"
        else:
            comp = verified[(verified.direction.astype(str).str.upper() == "INPUT") &
                            (~verified.flow_name.astype(str).str.startswith("CO2", na=False)) &
                            (verified.reference_year == year_a)]
            label = "Fuel input (หน่วยต้นทาง)"
        summary = comp.groupby(["flow_name", "unit_symbol"], as_index=False)["amount"].sum().sort_values("amount", ascending=False)
        st.caption(f"เปรียบเทียบข้อมูลปี {year_a} · {label}")
        if summary.empty:
            st.info("ไม่พบข้อมูลตามเงื่อนไขที่เลือก")
        else:
            if chart_type == "Bar":
                fig = px.bar(summary, x="flow_name", y="amount", color="unit_symbol", barmode="group",
                             labels={"flow_name": "ประเภท Flow", "amount": "ปริมาณ", "unit_symbol": "หน่วย"},
                             title=f"{mode} · {year_a}")
                fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
                st.plotly_chart(fig, width="stretch")
            st.dataframe(summary, width="stretch", hide_index=True)
            st.caption("ข้อมูลที่นำมาเปรียบเทียบมี Source ID และ URL อ้างอิงใน CSV")
        if mode == "Fuel input":
            st.markdown('<div class="note">เชื้อเพลิงแต่ละชนิดใช้หน่วยต้นทางต่างกัน จึงไม่ควรจัดอันดับจากค่าตัวเลขดิบข้ามหน่วย</div>', unsafe_allow_html=True)

else:
    st.subheader("AI Data Chatbot")
    st.write("ถามคำถามเกี่ยวกับข้อมูลที่มีแหล่งอ้างอิงใน CSV ได้ เช่น CO₂ ปี 2565 หรือปริมาณไฟฟ้าจาก Natural Gas")
    st.info("โหมดเดโม่: ใช้ Keyword + คำนวณจากข้อมูล CSV ที่ผ่านการตรวจสอบ Provenance ไม่ได้สร้างตัวเลขหรือประมาณค่าปีที่ไม่มีข้อมูล")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    prompt = st.chat_input("ลองถาม เช่น CO2 ปี 2565 เท่าไร หรือปี 2022 ผลิตไฟฟ้าจาก Natural Gas เท่าไร")
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        q = prompt.lower()
        year_match = re.search(r"(19|20)\d{2}|พ\.ศ\.\s*(25\d{2})|ปี\s*(25\d{2})", prompt)
        if year_match:
            nums = re.findall(r"\d{4}", year_match.group(0))
            yr = int(nums[-1]) - 543 if nums and int(nums[-1]) >= 2400 else (int(nums[-1]) if nums else default_year)
        else:
            yr = default_year
        if any(k in q for k in ["agricultural waste", "municipal solid waste", "agricultural", "ขยะเกษตร", "ขยะชุมชน", "ขยะมูลฝอย"]):
            ans = ("Agricultural Waste และ Municipal Solid Waste ถูกตัดออกจากขอบเขตข้อมูลของโปรเจกต์เวอร์ชันนี้ "
                   "จึงไม่แสดงหรือใช้คำนวณใน Dashboard, Data Explorer, Data Comparison และ AI Data Chatbot")
        elif any(k in q for k in ["co2", "carbon", "คาร์บอน", "คาร์บอนไดออกไซด์", "ก๊าซเรือนกระจก"]):
            d = co2_records[co2_records.reference_year == yr]
            if d.empty:
                ans = f"ไม่พบข้อมูล CO₂ ปี {yr} ที่มีแหล่งอ้างอิงครบถ้วนใน CSV จึงไม่สามารถรายงานตัวเลขได้"
            else:
                total_by_unit = d.groupby("unit_symbol").amount.sum()
                totals = "; ".join([f"{v:,.2f} {u}" for u, v in total_by_unit.items()])
                details = d.groupby(["flow_name", "unit_symbol"]).amount.sum()
                lines = "\n".join([f"- {name}: {value:,.2f} {unit}" for (name, unit), value in details.items()])
                sources_used = sorted(d.source_name.dropna().astype(str).unique().tolist())
                ans = (f"จากข้อมูล CSV ที่มีแหล่งอ้างอิง พบ CO₂ emissions ปี **{yr}** รวม **{totals}**\n\n"
                       f"แยกตามประเภท:\n{lines}\n\nแหล่งข้อมูล: {', '.join(sources_used)}\n\n"
                       "หมายเหตุ: เป็นค่า CO₂ ที่รายงานในชุดข้อมูล ไม่ใช่ค่า CO₂-equivalent หรือค่าต่อ kWh โดยอัตโนมัติ")
        elif any(k in q for k in ["ไฟฟ้า", "electricity", "ผลิตไฟฟ้า", "gwh"]):
            d = verified[(verified.reference_year == yr) & (verified.direction.astype(str).str.upper() == "OUTPUT") & verified.flow_name.astype(str).str.startswith("Electricity", na=False)]
            if d.empty:
                ans = f"ไม่พบข้อมูล Electricity output ปี {yr} ที่มีแหล่งอ้างอิงใน CSV"
            else:
                details = d.groupby(["flow_name", "unit_symbol"]).amount.sum()
                ans = f"ข้อมูล Electricity output ปี **{yr}**:\n\n" + "\n".join([f"- {name}: {value:,.2f} {unit}" for (name, unit), value in details.items()])
                ans += "\n\nแหล่งข้อมูล: " + ", ".join(sorted(d.source_name.dropna().astype(str).unique().tolist()))
        elif any(k in q for k in ["เชื้อเพลิง", "fuel", "natural gas", "ถ่านหิน", "ลิกไนต์"]):
            d = verified[(verified.reference_year == yr) & (verified.direction.astype(str).str.upper() == "INPUT")]
            if d.empty:
                ans = f"ไม่พบข้อมูล Fuel input ปี {yr} ที่มีแหล่งอ้างอิงใน CSV"
            else:
                details = d.groupby(["flow_name", "unit_symbol"]).amount.sum()
                ans = f"ข้อมูล Fuel input ปี **{yr}**:\n\n" + "\n".join([f"- {name}: {value:,.2f} {unit}" for (name, unit), value in details.items()])
                ans += "\n\nแหล่งข้อมูล: " + ", ".join(sorted(d.source_name.dropna().astype(str).unique().tolist()))
        else:
            ans = "ตอนนี้ตอบได้ในหัวข้อ CO₂ emissions, Electricity output และ Fuel input โดยใช้เฉพาะข้อมูล CSV ที่มีแหล่งอ้างอิง ลองถามเช่น ‘CO2 ปี 2565 เท่าไร’"
        st.session_state.chat_history.append({"role": "assistant", "content": ans})
        st.rerun()
    st.caption("คำตอบอ้างอิงจาก CSV ที่โหลดอยู่เท่านั้น หากไม่มีข้อมูลหรือไม่มีแหล่งอ้างอิง ระบบจะแจ้งว่าไม่พบข้อมูล")
