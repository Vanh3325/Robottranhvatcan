# App điều khiển robot AMR ESP32

Giao diện Python/Tkinter bằng tiếng Việt, cần vùng hiển thị tối thiểu khoảng 1000 × 860 pixel. Có chạy mô phỏng không cần linh kiện; chế độ phần cứng dùng USB serial tới một ESP32 gateway, rồi ESP-NOW tới ESP32 robot. Firmware do người dùng bổ sung sau; giao thức hiện tại là phương án đề xuất ở [PROTOCOL.md](PROTOCOL.md).

## Chạy nhanh

Cài Python 3.10 trở lên, chọn thành phần Tcl/Tk khi cài trên Windows. Trong thư mục này:

```powershell
python main.py --demo
```

Hoặc nhấp `run_demo.bat` trên Windows. Mô phỏng không cần pyserial. Dữ liệu trên đồ thị là tổng hợp và được đánh dấu `SIMULATION` trong CSV.

Để dùng cổng COM sau khi có firmware tương thích:

```powershell
python -m pip install -r requirements.txt
python main.py
```

Đóng Serial Monitor Arduino đang giữ cùng cổng. Cắm gateway, chọn COM, nhấn Kết nối; baud mặc định 115200. Một số board reset khi mở USB: chờ ACK hello tối đa 3 giây; nếu lỗi, kết nối lại sau khi board đã khởi động. App chỉ cho ARM khi robot đã ACK hello và gửi telemetry.

## Thao tác

1. Chọn Mô phỏng hoặc COM, kết nối, chờ trạng thái sẵn sàng.
2. Nhấn Cho phép chạy (ARM). Chọn manual hoặc auto sau khi robot xác nhận ARM.
3. Manual: giữ W/A/S/D hoặc các phím mũi tên, hoặc giữ nút trên màn hình. Thả để PWM về 0. Thanh PWM 0…255 là yêu cầu công suất, không đo tốc độ.
4. Space hoặc nút Dừng gửi stop và hủy ARM. Esc/nút dừng khẩn chốt estop phần mềm. Muốn tiếp tục phải xóa chốt rồi ARM lại.
5. Servo cho phép 30…150° khi manual và đang dừng; cách đổi góc ra thực tế cần hiệu chỉnh firmware.
6. Bắt đầu ghi CSV để lưu telemetry có thời gian và nguồn dữ liệu. Mở hộp chọn tệp sẽ gửi stop trước.
7. Khi cửa sổ mất focus, app gửi stop/hủy ARM. Khi mất ACK hoặc telemetry, app báo lỗi, khóa chuyển động và yêu cầu kết nối lại; không tự chạy khi tín hiệu trở lại.

Hai ô lỗi trong vùng mô phỏng dùng để thử mất đường truyền và dữ liệu cảm biến không hợp lệ. Simulator minh họa giao thức, chế độ và khóa điều khiển, không mô phỏng động lực học, lực phanh, bánh xe hay quét siêu âm thật.

## Cấu trúc

| Tệp | Vai trò |
|---|---|
| main.py | Điểm vào chương trình |
| gui.py | Tkinter, bàn phím/nút giữ, trạng thái, đồ thị, CSV |
| controller.py | Phiên, ACK, ARM, mode, heartbeat, timeout |
| transport.py | Serial đọc nền/hàng đợi và DemoTransport |
| protocol.py | Kiểm tra JSON, đóng gói, ghép dòng serial |
| test_system.py | Kiểm tra giao thức và logic lỗi/liên động |

Kiểm tra:

```powershell
python -m unittest -v test_system
```

Phiên bản bàn giao đã chạy 27 test bằng Python 3.12.14. Kiểm tra này xác nhận phần mềm với simulator; phép thử RF và robot thật chưa thực hiện. Các ngưỡng 30 cm, thời gian watchdog và PWM minh họa cần hiệu chỉnh dựa trên kết cấu và quãng đường dừng thực tế.
