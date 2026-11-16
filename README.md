# LingRangerDB_Demo
Demo user interface Electricity &amp; Power Generation database
# Thai LCI & LCA Data Platform — Demo

เดโม่เว็บสำหรับสำรวจข้อมูล Electricity & Power Generation ของประเทศไทยจาก CSV ที่เก็บมา

## ฟังก์ชัน
1. Dashboard — KPI, แนวโน้ม CO₂ และ electricity output
2. Data Explorer — ค้นหา/กรอง/ดาวน์โหลดข้อมูล
3. Data Comparison — เปรียบเทียบ CO₂, electricity output และ fuel input
4. AI Data Chatbot — เดโม่ถาม-ตอบด้วย keyword จากข้อมูลจริง (ยังไม่ใช่ LLM)

## เริ่มต้นใช้งานใน VS Code

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

ติดตั้ง:
```bash
pip install -r requirements.txt
```

รัน:
```bash
streamlit run app.py
```

จากนั้นเปิด URL ที่ Streamlit แสดง (ปกติคือ http://localhost:8501)

## ใช้ PostgreSQL แทน CSV
สร้างไฟล์ `.env` จาก `.env.example` แล้วใส่ connection string:

```env
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/DATABASE
```

แอปจะพยายามอ่านตารางชื่อ:
`flow_category`, `geography`, `lci_exchange`, `lci_flow`, `lci_process`, `lci_source`, `technology`, `unit`

หากเชื่อมต่อไม่ได้ จะกลับไปใช้ CSV ในโฟลเดอร์ `data/` โดยอัตโนมัติ

**อย่า commit `.env` หรือเผยแพร่รหัสผ่านฐานข้อมูล**

## ข้อจำกัดข้อมูลที่ต้องทราบ
- ข้อมูลที่แนบมามี LCI fuel input, electricity output และ CO₂ emissions บางประเภท
- CO₂ emissions ในไฟล์เป็นหน่วยต้นทาง `1,000 Tons` และมาจากการรายงานตามประเภทพลังงาน
- ชุดข้อมูลนี้ยังไม่ใช่ผล LCA ครบวงจร และไม่มีหลักฐานให้คำนวณ GWP (kg CO₂-eq) ต่อ kWh โดยตรง
- เชื้อเพลิงแต่ละชนิดมีหน่วยต่างกัน ห้ามเปรียบเทียบค่าดิบข้ามหน่วยโดยตรง
- Chatbot ในเดโม่เป็น keyword-based เพื่อให้ทดสอบ UX ได้ก่อน ยังไม่ได้เชื่อมต่อ LLM API
