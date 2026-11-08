# Giao thức đề xuất AMR v1

Đây là hợp đồng tích hợp cho firmware người dùng cung cấp sau. App đã triển khai phía máy tính và mô phỏng; chưa nạp hoặc xác nhận trên ESP32 thật.

## Đường truyền

`Python → USB serial 115200 8N1 → ESP32 gateway ⇄ ESP-NOW unicast ⇄ ESP32 robot`

Máy tính thông thường cần ESP32 gateway USB; app không phát ESP-NOW trực tiếp từ card Wi-Fi của máy tính. Hai ESP32 phải cùng kênh Wi-Fi và đăng ký đúng MAC. Chọn kênh cố định phù hợp tại nơi thử; không kết nối gateway vào AP có thể tự đổi kênh trong lúc chạy. Dùng peer unicast và cấu hình PMK/LMK riêng nếu triển khai mã hóa ESP-NOW.

USB dùng một JSON ASCII mỗi dòng, kết thúc LF; nhận được cả CRLF. Một dòng có tối đa 240 byte không tính LF. Gateway bỏ LF trước khi gửi ESP-NOW, giữ nguyên nội dung JSON, rồi thêm LF khi chuyển phản hồi robot về USB. Không thêm nhãn debug vào dòng JSON; log debug phải dùng kênh khác. Chỉ chuyển ACK do robot tạo; callback gửi ESP-NOW thành công không thay thế ACK ứng dụng.

## Phong bì chung

| Trường | Quy định |
|---|---|
| `v` | Số nguyên 1 |
| `t` | `cmd`, `ack`, `telemetry` |
| `s` | 12 ký tự hex thường, mã phiên mới mỗi lần kết nối |
| `seq` | Chỉ cmd/ack; số nguyên tăng dần 1…2147483647 trong một phiên |

Gateway chuyển tiếp nguyên gói. Robot kiểm tra phiên, phiên bản, độ dài, kiểu dữ liệu, giới hạn, MAC nguồn và số thứ tự trước khi thực thi. `hello` hợp lệ từ peer được ghép đôi thiết lập phiên mới và đưa PWM về 0, hủy ARM, chuyển manual; không xóa chốt estop. Không tự khôi phục lệnh chuyển động sau reset hoặc reconnect. Mã phiên phục vụ loại gói cũ, không phải thông tin xác thực hay khóa mã hóa.

## Lệnh

Ví dụ (thay `s` bằng phiên app hiện tại):

```json
{"v":1,"t":"cmd","s":"012345abcdef","seq":1,"cmd":"hello"}
{"v":1,"t":"cmd","s":"012345abcdef","seq":2,"cmd":"arm"}
{"v":1,"t":"cmd","s":"012345abcdef","seq":3,"cmd":"drive","left":110,"right":110}
{"v":1,"t":"cmd","s":"012345abcdef","seq":4,"cmd":"mode","value":"auto"}
{"v":1,"t":"cmd","s":"012345abcdef","seq":5,"cmd":"servo","angle":90}
{"v":1,"t":"cmd","s":"012345abcdef","seq":6,"cmd":"stop"}
{"v":1,"t":"cmd","s":"012345abcdef","seq":7,"cmd":"estop"}
{"v":1,"t":"cmd","s":"012345abcdef","seq":8,"cmd":"reset_estop"}
{"v":1,"t":"cmd","s":"012345abcdef","seq":9,"cmd":"heartbeat"}
```

| Lệnh | Hành vi bắt buộc tại robot |
|---|---|
| hello | Mở phiên và đưa về manual, chưa ARM, PWM 0; giữ estop |
| arm | Chỉ cho phép khi không estop, cảm biến hợp lệ và robot đang dừng |
| drive | PWM có dấu `left/right` trong [-255,255], chỉ nhận khi manual và đã ARM |
| mode | `manual` hoặc `auto`; dừng bánh trước khi đổi; cần ARM |
| servo | Góc nguyên 30…150 độ, chỉ manual và hai PWM bằng 0 |
| stop | PWM 0, hủy ARM, về manual; không xóa estop |
| estop | Dừng, hủy ARM, về manual và chốt dừng khẩn phần mềm |
| reset_estop | Xóa chốt khi đang dừng; vẫn chưa ARM |
| heartbeat | Gia hạn liên kết nếu phiên và seq hợp lệ; không ARM hay đổi PWM |

PWM dương tương ứng bánh chạy tiến sau khi hiệu chỉnh chiều dây/động cơ. Dấu âm là lùi. Giá trị là duty 8 bit, không phải RPM, m/s hay tốc độ đo được. Nếu firmware dùng độ phân giải PWM khác, quy đổi ở lớp điều khiển động cơ.

## ACK và telemetry

Robot ACK sau khi kiểm tra và chấp nhận hoặc từ chối lệnh:

```json
{"v":1,"t":"ack","s":"012345abcdef","seq":3,"cmd":"drive","status":"ok"}
{"v":1,"t":"ack","s":"012345abcdef","seq":3,"cmd":"drive","status":"error","reason":"not_armed"}
{"v":1,"t":"telemetry","s":"012345abcdef","mode":"manual","armed":false,"estop":false,"sensor_ok":true,"distance_cm":72.5,"servo":90,"left":0,"right":0}
```

`reason` là chuỗi ASCII tối đa 64 ký tự. Telemetry định kỳ 10 Hz; khoảng cách cm hoặc `null` khi mất echo, kèm `sensor_ok=false`. Góc `servo` là góc đã yêu cầu, không phải góc đo bằng cảm biến vị trí. PWM telemetry là đầu ra phần mềm đã áp dụng sau liên động, không đo trực tiếp dòng điện hay vòng quay.

Robot phải chống lặp: lưu các seq gần đây và kết quả ACK. Gói lặp không thực thi lần hai nhưng có thể trả lại ACK cũ. Seq thấp hơn lệnh mới nhất và không nằm trong bộ nhớ lặp phải bị loại; không thực thi lệnh cũ đến muộn. Có thể ưu tiên dừng hợp lệ của phiên hiện tại; tuyệt đối không cho lệnh cũ bật lại động cơ. App không tự gửi lại lệnh chuyển động khi ACK mất; app chuyển lỗi và yêu cầu kết nối lại.

## Thời gian và liên động

- App: heartbeat mỗi 100 ms; giữ phím gửi lại drive mỗi 100 ms, seq mới. Thả phím gửi drive 0/0.
- Robot: watchdog liên kết tối đa 500 ms từ gói điều khiển/heartbeat hợp lệ gần nhất; hết hạn dừng, hủy ARM, manual. Chế độ auto cũng chịu watchdog trong thiết kế này.
- Robot: thêm watchdog drive tối đa 300 ms khi manual có PWM khác 0. Heartbeat không gia hạn tuổi lệnh drive. Nhờ vậy heartbeat còn hoạt động không giữ lệnh chạy đã cũ.
- App: `hello` chờ tối đa 3 s (cho gateway reset khi mở USB), các ACK khác 650 ms; mất telemetry >1 s thì khóa điều khiển và gửi estop nếu đường truyền còn dùng được. Lệnh stop khi ngắt app là cố gắng cuối, không bảo đảm RF đã nhận.
- Không đặt delay dài trong callback ESP-NOW. Callback chỉ kiểm tra sơ bộ và đưa gói vào hàng đợi; tác vụ điều khiển đọc hàng đợi và phát ACK.
- Khi cảm biến không hợp lệ: không coi 0 là xa vô hạn. Dừng chuyển động, báo lỗi; không tự lùi vì robot không có cảm biến sau.
- Khi đi tiến manual: đưa cảm biến về phía trước, chờ ổn định và phép đo hợp lệ mới cho tiến. Phải dừng hoặc khóa tiến khi cảm biến đang nhìn bên, dữ liệu trước đã cũ hoặc khoảng cách dưới ngưỡng. Nút servo chỉ điều khiển khi robot đứng yên.
- Lùi/quay manual chỉ thử tốc độ thấp dưới giám sát vì không đủ phủ cảm biến. Thuật toán auto đề xuất dừng để quét, chọn bên thoáng và quay từng bước; không tự lùi mù.
- Dừng khẩn trong app là chức năng phần mềm. Công tắc nguồn/nút cắt công suất vật lý phải hoạt động độc lập nếu bổ sung vào mô hình.

## Ghép với firmware có sẵn

Nếu firmware dùng gói nhị phân, không ép thay toàn bộ: viết adapter ở gateway hoặc sửa `protocol.py`/`transport.py` theo cấu trúc thực tế. Cần cung cấp mã hai ESP32, loại board, chân nối, MAC/kênh, baudrate và ví dụ TX/RX để xác nhận. Chưa có firmware không thể khẳng định app điều khiển được robot thật.

Tham chiếu: [ESP-NOW Espressif](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/network/esp_now.html), [pySerial](https://pyserial.readthedocs.io/en/latest/pyserial_api.html).
