"""Revision 1.1: match the user's tested firmware without modifying firmware."""
from pathlib import Path
import json
import re
import shutil
from PIL import Image, ImageDraw
import build_report as base

ROOT=base.ROOT
ATTACHMENT=Path(r'C:\Users\Dan Viet\.codex\attachments\626e5ff6-3d5d-4797-874b-7a28f5433a2f\Văn bản đã dán.txt')


def diagrams_actual():
    assets=base.ASSETS
    f=base.font; box=base.text_block; arrow=base.arrow; heading=base.diagram_heading
    im=Image.new('RGB',(1600,1000),'white'); d=ImageDraw.Draw(im)
    heading(d,'KIẾN TRÚC BẢN ĐÃ CHẠY VÀ PHẦN MỞ RỘNG','Firmware hiện tại: tự hành trên ESP32; Serial chỉ xuất trạng thái',1600)
    box(d,(40,160,470,370),'SIÊU ÂM + SERVO','TRIG 5 • ECHO 4\nServo GPIO7: 30° / 90° / 150°',size=25)
    box(d,(585,160,1015,370),'ESP32 TỰ HÀNH','Đo trước → so sánh 30 cm\nDừng → quét → lùi → rẽ')
    box(d,(1130,160,1560,370),'TB6612 + 2 MOTOR','PWMA 21 • PWMB 42\nRamp: bước 2 mỗi 20 ms',size=25)
    arrow(d,(480,265),(575,265),True); arrow(d,(1025,265),(1120,265))
    box(d,(585,435,1015,585),'SERIAL MONITOR','115200 baud • FRONT / SCAN\nREADY / OBSTACLE / TURN',size=24)
    arrow(d,(800,380),(800,425))
    d.line((40,645,1560,645),fill='#a8b6bf',width=2)
    d.text((40,670),'PHẦN MỞ RỘNG CHƯA TÍCH HỢP TRONG FIRMWARE',font=f(30,True),fill='#4a6372')
    box(d,(40,740,470,920),'APP PYTHON','Giao diện + mô phỏng\nJSON / ACK dự kiến',fill='#f6f6f6')
    box(d,(585,740,1015,920),'ESP32 GATEWAY','USB serial ⇄ ESP-NOW\nCần bổ sung firmware',fill='#f6f6f6')
    box(d,(1130,740,1560,920),'BỘ NHẬN Ở ROBOT','Nhận lệnh • mode • STOP\nACK • telemetry • watchdog',fill='#f6f6f6',size=24)
    arrow(d,(480,830),(575,830),True); arrow(d,(1025,830),(1120,830),True)
    im.save(assets/'architecture_actual.png')

    im=Image.new('RGB',(1600,1120),'white'); d=ImageDraw.Draw(im)
    heading(d,'CẤU HÌNH GPIO ĐÚNG THEO CODE ĐÃ THỬ','Các chân lấy từ hằng số trong firmware đã được nhóm kiểm thử trên mô hình',1600)
    box(d,(40,150,450,435),'ESP32 ROBOT','PWMA 21 • AIN1 48 • AIN2 47\nSTBY 39\nBIN1 40 • BIN2 41 • PWMB 42',title_size=29,size=25)
    box(d,(650,150,1040,435),'TB6612FNG','Kênh A → motor trái\nKênh B → motor phải\nSTBY đặt HIGH trong setup',size=25)
    box(d,(1230,150,1560,275),'MOTOR TRÁI','AO1 / AO2',title_size=27,size=25)
    box(d,(1230,310,1560,435),'MOTOR PHẢI','BO1 / BO2\nBù dấu logic −1',title_size=27,size=23)
    arrow(d,(460,285),(640,285)); arrow(d,(1050,215),(1220,215)); arrow(d,(1050,370),(1220,370))
    box(d,(40,535,450,735),'SERVO','Signal GPIO7\n50 Hz • 14 bit\nGiữa 90° • trái 150° • phải 30°',title_size=29,size=24)
    box(d,(650,535,1040,735),'SIÊU ÂM','TRIG GPIO5 • ECHO GPIO4\nTrigger 10 µs\nEcho timeout 30.000 µs',title_size=29,size=25)
    box(d,(1230,535,1560,735),'MỨC ĐIỆN ÁP','Nếu Echo 5 V:\nchuyển mức trước GPIO',title_size=27,size=24)
    arrow(d,(245,445),(245,525)); arrow(d,(460,420),(640,545),True); arrow(d,(1050,630),(1220,630))
    box(d,(40,850,1560,1020),'NGUỒN VÀ GND','GND chung giữa ESP32, driver, siêu âm và servo\nVM theo motor; VCC/nguồn servo theo module; mã không chỉ rõ mạch nguồn thực tế',title_size=30,size=27)
    d.text((40,1050),'GPIO là cấu hình thực tế; ghi chú nguồn/chuyển mức là nguyên tắc thiết kế.',font=f(25),fill='#4e6675')
    im.save(assets/'wiring_actual.png')

    im=Image.new('RGB',(1600,1540),'white'); d=ImageDraw.Draw(im)
    heading(d,'CHU TRÌNH TỰ ĐỘNG ĐÚNG THEO FIRMWARE','Các khoảng giữ lệnh bắt đầu sau ramp; điều khiển hiện tại dùng delay',1600)
    box(d,(440,130,1160,275),'SETUP','GPIO + LEDC • STBY HIGH • motor 0\nServo 90° → chờ 800 ms → tiến 46/54',title_size=29,size=25)
    box(d,(440,345,1160,475),'ĐỌC KHOẢNG CÁCH TRƯỚC','pulseIn timeout 30.000 µs\nKhông Echo / ngoài dải → trả 400 cm',title_size=28,size=25)
    arrow(d,(800,285),(800,335))
    box(d,(440,540,1160,645),'FRONT ≤ 30 cm ?','So sánh trong loop()',title_size=30,size=25)
    arrow(d,(800,485),(800,530))
    box(d,(35,520,340,690),'TIẾN 46 / 54','Nhánh front > 30\nCuối loop chờ 80 ms',title_size=27,size=23)
    arrow(d,(430,590),(350,590)); d.text((350,540),'Không',font=f(24),fill='#3d6074')
    box(d,(440,715,1160,875),'DỪNG VÀ QUÉT','stop qua ramp → chờ 150 ms\nĐo trái 150° → phải 30°\nVề tâm 90° → chờ 200 ms',title_size=29,size=25)
    arrow(d,(800,655),(800,705)); d.text((820,665),'Có',font=f(24),fill='#3d6074')
    box(d,(440,945,1160,1075),'LÙI RỒI DỪNG','PWM −34 / −50 → giữ 220 ms\nstop qua ramp → chờ 120 ms',title_size=29,size=25)
    arrow(d,(800,885),(800,935))
    box(d,(35,1160,720,1310),'NẾU TRÁI ≥ PHẢI: RẼ TRÁI','PWM trái 0 • phải 56\nChỉ bánh phải chạy',title_size=27,size=26)
    box(d,(880,1160,1565,1310),'CÒN LẠI: RẼ PHẢI','PWM trái 42 • phải 0\nChỉ bánh trái chạy',title_size=27,size=26)
    arrow(d,(650,1085),(375,1150)); arrow(d,(950,1085),(1225,1150))
    box(d,(440,1380,1160,1510),'KẾT THÚC TRÁNH','Giữ rẽ 380 ms → stop → chờ 120 ms\nServo về giữa → tiến 46/54 → loop',title_size=29,size=25)
    arrow(d,(375,1320),(650,1370)); arrow(d,(1225,1320),(950,1370))
    im.save(assets/'flowchart_actual.png')


def main():
    raw=ATTACHMENT.read_text(encoding='utf-8-sig')
    expected={'TB_PWMA_PIN':21,'TB_AIN2_PIN':47,'TB_AIN1_PIN':48,'TB_STBY_PIN':39,
              'TB_BIN1_PIN':40,'TB_BIN2_PIN':41,'TB_PWMB_PIN':42,'ECHO_PIN':4,'TRIG_PIN':5,'SERVO_PIN':7}
    actual={k:int(v) for k,v in re.findall(r'^#define\s+(\w+)\s+(\d+)',raw,re.M)}
    assert all(actual.get(k)==v for k,v in expected.items())
    # Retain the supplied code as source evidence, without changing it.
    (ROOT/'report/firmware_da_kiem_thu.ino').write_text(raw,encoding='utf-8')
    abstract=('Đề tài xây dựng robot di động AMR sử dụng ESP32, hai động cơ DC qua TB6612FNG và cảm biến siêu âm trên servo. '
              'Firmware tự chạy tiến sau khởi tạo, đo khoảng cách phía trước và kích hoạt tránh vật cản ở ngưỡng 30 cm. '
              'Chu trình tránh gồm giảm PWM về không, quét trái và phải, lùi, chọn bên có khoảng cách lớn hơn rồi rẽ bằng một bánh trước khi tiến lại. '
              'Motor dùng PWM 20 kHz, 8 bit và ramp từng bước; servo dùng 50 Hz, 14 bit với các hướng 90°, 150° và 30°. '
              'Nhóm thực hiện đã chạy thử mô hình và xác nhận các chức năng của bản tự động hoạt động đạt. '
              'Báo cáo cập nhật GPIO, thông số và lưu đồ đúng theo mã đã kiểm thử; kết quả được ghi ở mức chức năng, chưa công bố số liệu định lượng chưa được cung cấp. '
              'App Python đã có giao diện và mô phỏng; ESP-NOW, nhận lệnh và xác nhận từ robot là phần mở rộng chưa có trong firmware hiện tại.')
    base.main({'reference':ROOT/'Bao_cao_AMR_ESP32_hoan_thien.docx',
               'output':ROOT/'Bao_cao_AMR_ESP32_cap_nhat_code_thuc_te.docx',
               'content':ROOT/'report/noi_dung_bao_cao_v1_1.md',
               'title':'ROBOT AMR DÙNG ESP32\nTRÁNH VẬT CẢN BẰNG SIÊU ÂM QUÉT SERVO\nVÀ THIẾT KẾ APP PYTHON QUA ESP-NOW',
               'abstract':abstract,'append_history':True,
               'history':['V1.1','08/11/2026','Nhóm thực hiện','GPIO, PWM và thuật toán theo code; kiểm thử tự hành đạt'],
               'diagrams':diagrams_actual})
    (ROOT/'tmp/firmware_config_v1_1.json').write_text(json.dumps(expected,indent=2),encoding='utf-8')


if __name__=='__main__': main()
