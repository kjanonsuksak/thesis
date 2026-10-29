# WISN Family Medicine Planner (Streamlit)

## วิธีเริ่มต้น
1. ติดตั้ง Python 3.10+
2. แตกไฟล์ ZIP นี้
3. เปิด Terminal/Command Prompt ในโฟลเดอร์โปรเจกต์
4. ติดตั้ง dependencies: `pip install -r requirements.txt`
5. รัน: `streamlit run app.py`

## ไฟล์
- `app.py`: แอปพลิเคชัน Streamlit
- `RF_F4_forecast_2569_2573_strata.csv.gz`: ชุดข้อมูลผลพยากรณ์แบบบีบอัด (ลดขนาดไฟล์)
- `requirements.txt`: ไลบรารีที่จำเป็น

## หมายเหตุ
- แอปใช้ผลพยากรณ์ที่เตรียมไว้ ไม่ได้ฝึก Random Forest ใหม่
- ชุดข้อมูลมีปี พ.ศ. 2569–2573 ตามไฟล์ที่ได้รับ
- ค่าเริ่มต้น: standard time 6.55 นาที/ครั้ง, AWT 1,680 ชั่วโมง/คน/ปี, Unmet Need 0%
- ผล FTE เป็นประมาณการความต้องการตามสมมติฐาน ไม่ใช่จำนวนบุคลากรขาดแคลน
- ตรวจสอบนิยามหน่วยและแหล่งที่มาของค่าพยากรณ์ก่อนใช้อ้างอิงทางวิชาการ
