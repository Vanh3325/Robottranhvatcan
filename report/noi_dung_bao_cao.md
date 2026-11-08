# 1. Giới thiệu (Introduction)

## 1.1. Động lực (Motivation)

Robot di động là một đối tượng phù hợp để kết hợp kiến thức về hệ thống nhúng, cảm biến, điều khiển động cơ và truyền thông không dây. Trong môi trường học tập, bài toán xây dựng robot có thể di chuyển, phát hiện vật cản và nhận lệnh từ máy tính giúp kiểm tra toàn bộ chuỗi xử lý: thu thập dữ liệu, ra quyết định, phát lệnh chấp hành và giám sát trạng thái.

Đề tài lựa chọn ESP32 làm bộ điều khiển, hai động cơ DC tạo chuyển động vi sai và TB6612FNG làm tầng công suất. Một cảm biến siêu âm được đặt trên servo để khảo sát nhiều hướng mà không phải bố trí nhiều cảm biến. App Python đảm nhiệm điều khiển thủ công, lựa chọn chế độ tự tránh vật cản và lưu dữ liệu kiểm chứng. Liên kết ESP-NOW giữa hai ESP32 cho phép trao đổi cục bộ mà không yêu cầu máy chủ Internet.

Trong phạm vi báo cáo, AMR được hiểu là nguyên mẫu robot di động có khả năng phản ứng với vật cản và điều khiển từ xa. Hệ thống chưa có encoder, IMU hoặc bộ định vị; do đó chưa thực hiện SLAM, lập bản đồ, xác định tọa độ hay lập kế hoạch đường đi tới đích. Cách xác định phạm vi này giúp mục tiêu và phép thử phù hợp với phần cứng thực tế.

## 1.2. Mục tiêu (Objectives)

Mục tiêu tổng quát là thiết kế một nguyên mẫu robot di động vi sai dùng ESP32 và xây dựng app Python phục vụ điều khiển, theo dõi trạng thái và thử nghiệm thuật toán tránh vật cản.

@table Bảng 1. Mục tiêu và cách đánh giá
| Mã | Mục tiêu cụ thể | Cách đánh giá |
|---|---|---|
| MT01 | Điều khiển độc lập hai động cơ DC bằng TB6612 | Kiểm tra chiều quay, PWM, dừng từng kênh |
| MT02 | Đo khoảng cách ở phía trước và hai bên bằng siêu âm trên servo | So sánh với thước tại các góc đã hiệu chỉnh |
| MT03 | Chạy thủ công và tự chọn hướng tránh vật cản | Thử kịch bản có vật cản, ngõ hẹp, hai bên bị chặn |
| MT04 | Điều khiển từ Python qua USB gateway và ESP-NOW | Xác nhận lệnh, phản hồi trạng thái, lưu CSV |
| MT05 | Dừng khi mất liên kết hoặc dữ liệu cảm biến không hợp lệ | Ngắt USB/RF, giả lập mất echo và đo thời gian dừng |

Trạng thái hiện tại: đã xây dựng mã app Python, bộ mô phỏng và kiểm tra phần mềm. Thiết kế phần cứng, bảng chân và thuật toán nhúng là phương án để tích hợp; firmware ESP32, ảnh lắp ráp và số liệu robot thật sẽ được chủ đề tài cung cấp sau.

## 1.3. Nội dung chính (Main Contents)

Báo cáo gồm năm phần: giới thiệu; xác định yêu cầu và giao diện hệ thống; trình bày thiết kế phần cứng, thuật toán nhúng và app; xây dựng phương pháp kiểm chứng; đánh giá mức độ hoàn thành và hướng phát triển. Phụ lục cung cấp cách chạy app, ví dụ bản tin và danh sách thông tin cần chốt trước khi ghép firmware.

# 2. Yêu cầu đối với thiết kế (Requirements)

## 2.1. Yêu cầu chung

Đầu vào của hệ thống gồm lệnh người vận hành, xung Echo của cảm biến siêu âm và trạng thái liên kết. Đầu ra gồm tín hiệu PWM/chiều quay của hai động cơ, góc điều khiển servo và các bản tin phản hồi về máy tính. Robot sử dụng điều khiển vi sai: cùng chiều để tiến/lùi, khác chiều hoặc khác mức PWM để đổi hướng.

@table Bảng 2. Yêu cầu chức năng của hệ thống
| Mã | Yêu cầu chức năng | Điều kiện chấp nhận dự kiến |
|---|---|---|
| F01 | Khởi động ở trạng thái dừng, chưa ARM | Hai PWM bằng 0; không tự chạy sau reset |
| F02 | Tiến, lùi, quay trái/phải trong manual | Chỉ chạy khi giữ lệnh và đã được robot xác nhận ARM |
| F03 | Quét khoảng cách ở nhiều hướng | Gắn góc đo và thời điểm đo; loại mẫu mất Echo |
| F04 | Auto tránh vật cản tại chỗ | Dừng, quét, chọn hướng thoáng, quay từng bước và đo lại |
| F05 | Giám sát bằng app | Hiển thị mode, ARM, khoảng cách, góc và PWM phản hồi |
| F06 | STOP và estop phần mềm | STOP hủy ARM; estop phải được xóa chốt rõ ràng |
| F07 | Phát hiện lỗi truyền thông | Mất ACK/telemetry thì khóa điều khiển; robot có watchdog riêng |
| F08 | Lưu dữ liệu kiểm chứng | CSV có thời gian, nguồn SIMULATION/SERIAL và giá trị nhận |

![Hình 1. Kiến trúc chức năng và luồng dữ liệu của hệ thống](architecture.png)

Robot làm việc trên mặt phẳng trong nhà, ở tốc độ thấp và dưới giám sát. Một siêu âm phía trước không bao phủ phía sau, mép bàn hay toàn bộ vùng bánh xe khi quay. Thiết kế tránh vật cản vì vậy ưu tiên dừng và khảo sát lại; không mặc định mọi thao tác lùi hoặc quay đều an toàn.

## 2.2. Đặc tả kỹ thuật (Specification)

Các giá trị sau là cấu hình khởi đầu để thử nghiệm, chưa phải thông số đã đo của nguyên mẫu. Khi thay board, loại servo, nguồn hoặc động cơ, cần cập nhật bảng tương ứng.

@table Bảng 3. Cấu hình kỹ thuật khởi đầu
| Hạng mục | Phương án / giá trị khởi đầu | Trạng thái |
|---|---|---|
| Board robot | ESP32 DevKit dùng ESP32-WROOM-32 cổ điển | Giả định để lập bảng chân |
| Bộ truyền động | Hai động cơ DC và TB6612FNG | Cấu hình do chủ đề tài xác nhận |
| Cảm biến / servo | HC-SR04 và SG90 làm ví dụ | Chưa xác nhận mã linh kiện thực tế |
| Mạch gateway | Một ESP32 riêng nối máy tính qua USB | Cần có để dùng ESP-NOW từ PC |
| PWM động cơ | 20 kHz, độ phân giải 8 bit; lệnh có dấu ±255 | Đề xuất, phải kiểm tra timer |
| Servo | 50 Hz; dải phần mềm 30–150°, tâm 90° | Hiệu chỉnh xung và giới hạn cơ khí |
| Đo siêu âm | Khoảng cách giữa hai lần phát >60 ms; timeout 25 ms | Theo nguyên tắc cảm biến và cấu hình thử |
| Ngưỡng vật cản | Dừng 30 cm; cho đi lại khi >40 cm | Cần hiệu chỉnh bằng quãng đường dừng |
| Nhịp giao tiếp | Heartbeat 100 ms; telemetry 100 ms | Mục tiêu tích hợp |
| Watchdog robot | Liên kết 500 ms; lệnh drive manual 300 ms | Yêu cầu firmware |
| App | ACK 650 ms; hello 3 s; telemetry 1 s | Đã triển khai trong app |

### 2.2.1. Kiến trúc tổng thể

Hệ thống gồm ba lớp. Lớp máy tính chạy app Python. Lớp gateway chuyển đổi USB serial và ESP-NOW, không tự tạo xác nhận thay robot. Lớp robot xử lý đo khoảng cách, điều khiển servo, thuật toán tránh vật cản và TB6612. Quyết định dừng do vật cản và watchdog nằm trên robot để vẫn có hiệu lực khi máy tính hoặc đường truyền gặp lỗi.

Luồng điều khiển: thao tác trên app → kiểm tra trạng thái → bản tin JSON → USB gateway → ESP-NOW unicast → kiểm tra lệnh ở robot → điều khiển đầu ra → ACK/telemetry quay về app. Kết quả gửi thành công ở tầng MAC không chứng minh robot đã thực thi; vì vậy hệ thống dùng ACK ở tầng ứng dụng [1].

### 2.2.2. Đặc tả Node IoT (ESP32 trên robot)

Node robot điều khiển bảy tín hiệu của TB6612, một tín hiệu servo, một chân Trigger và một chân Echo. Board giả định là ESP32-WROOM-32 dùng lõi Xtensa; tiêu đề Node ARM trong mẫu được thay bằng ESP32 cho đúng cấu hình [2]. Sơ đồ chân trong báo cáo không áp dụng trực tiếp cho ESP32-C3/S3 hoặc board có cách đưa chân khác.

Node có các module logic: nhận/kiểm tra gói tin, quản lý phiên và ARM, đo siêu âm, lập lịch servo, điều khiển động cơ, máy trạng thái tránh vật cản, watchdog và gửi telemetry. Tác vụ mạng chỉ chuyển dữ liệu qua hàng đợi; tác vụ điều khiển là nơi duy nhất cập nhật trạng thái chấp hành.

### 2.2.3. Đặc tả Gateway (ESP32)

Gateway là ESP32 thứ hai, cấp nguồn từ USB máy tính và sử dụng cổng USB-UART có sẵn trên DevKit. Gateway nhận JSON theo từng dòng ở 115200 baud, bỏ ký tự xuống dòng và phát nguyên nội dung qua ESP-NOW. Ở chiều ngược lại, gateway thêm LF vào ACK/telemetry nhận từ robot rồi chuyển lên máy tính. Hai ESP32 phải sử dụng đúng MAC peer và cùng kênh Wi-Fi [1].

Gateway cần giới hạn độ dài, giữ đúng ranh giới bản tin và báo lỗi cục bộ qua kênh log riêng. Không trộn câu debug vào giữa JSON. Bản tin ACK của robot phải được chuyển tiếp nguyên vẹn, tránh giao diện báo sẵn sàng khi chỉ gateway đang hoạt động. Khi nạp code cần kiểm tra phiên bản Arduino-ESP32/ESP-IDF vì chữ ký callback có thể khác giữa các phiên bản.

### 2.2.4. Đặc tả Cloud (nếu có)

Phiên bản này không sử dụng cloud, cơ sở dữ liệu Internet hoặc tài khoản đăng nhập. Lệnh và phản hồi đi trong mạng cục bộ; nhật ký lưu thành CSV trên máy tính do người dùng chọn. Việc bỏ cloud giúp tập trung vào điều khiển và tránh vật cản, đồng thời cho phép thử nghiệm khi không có Internet. Nếu bổ sung cloud, chỉ nên dùng cho lưu trữ hoặc thống kê; liên động dừng vẫn phải nằm ở robot.

### 2.2.5. Đặc tả Website/App

App desktop được viết bằng Python/Tkinter, có hai nguồn kết nối: mô phỏng và cổng COM thật. Màn hình chính gồm chọn kết nối, trạng thái liên kết, nút ARM, chọn manual/auto, điều khiển hướng khi giữ, thanh PWM, STOP, estop phần mềm, đặt góc servo, trạng thái robot, đồ thị khoảng cách và ghi CSV.

Chế độ mô phỏng chạy không cần ESP32 hoặc pyserial. Chế độ COM yêu cầu pyserial và firmware tuân thủ giao thức. App không phát ESP-NOW trực tiếp từ card Wi-Fi máy tính; ESP32 gateway thực hiện phần radio. Giao diện chỉ cho phép chuyển động sau ACK hello, telemetry và ACK ARM.

### 2.2.6. Đặc tả truyền thông

Giao thức đề xuất dùng JSON ASCII, mỗi bản tin USB kết thúc bằng LF; mỗi nội dung tối đa 240 byte không tính LF. Giới hạn này nằm dưới mức 250 byte của ESP-NOW v1 để thuận lợi tích hợp [1]. Việc dùng JSON giúp đọc log và đối chiếu firmware; khi cần tối ưu có thể thay bằng cấu trúc nhị phân qua adapter, nhưng phải thống nhất kiểu dữ liệu, thứ tự byte và kiểm tra phiên bản.

@table Bảng 4. Các trường bản tin trong giao thức đề xuất
| Trường | Ý nghĩa |
|---|---|
| v, t | Phiên bản 1; loại cmd, ack hoặc telemetry |
| s | Mã phiên gồm 12 ký tự hex; đổi mỗi lần kết nối |
| seq, cmd | Số thứ tự lệnh và tên lệnh; ACK phải khớp cả hai |
| left, right | PWM có dấu trong [-255,255]; không phải vận tốc đo |
| value / angle | Chế độ manual/auto hoặc góc servo 30–150° |
| status, reason | ACK ok/error và lý do nếu bị từ chối |
| sensor_ok, distance_cm | Tình trạng phép đo; null khi dữ liệu không hợp lệ |

```json
{"v":1,"t":"cmd","s":"012345abcdef","seq":3,"cmd":"drive","left":110,"right":110}
{"v":1,"t":"ack","s":"012345abcdef","seq":3,"cmd":"drive","status":"ok"}
```

Các lệnh gồm hello, arm, drive, mode, servo, stop, estop, reset_estop và heartbeat. Robot kiểm tra MAC nguồn, phiên, seq, giới hạn và điều kiện chế độ. Lệnh trùng không được thực thi lại; gói cũ đến muộn không được bật lại động cơ. Chi tiết đầy đủ và ví dụ telemetry nằm trong PROTOCOL.md đi kèm app.

App phát heartbeat mỗi 100 ms. Khi giữ hướng manual, app phát drive mới mỗi 100 ms; khi thả gửi drive 0/0. Robot phải có hai thời hạn độc lập: mất liên kết 500 ms thì dừng và hủy ARM; drive manual quá 300 ms thì PWM về 0 dù heartbeat còn đến. Chế độ auto trong đề tài cũng chịu watchdog liên kết. Mã phiên chỉ giúp tách các lần kết nối; bảo vệ đường truyền cần ghép peer và cấu hình khóa ESP-NOW phù hợp [1].

### 2.2.7. Yêu cầu phi chức năng

Hệ thống ưu tiên dừng có kiểm soát hơn duy trì chuyển động khi thiếu dữ liệu. Không dùng thao tác chờ dài để đo Echo hoặc quay servo trong callback mạng. Giao diện phải giữ phản hồi trong lúc nhận serial; dữ liệu từ luồng đọc đi qua hàng đợi trước khi cập nhật Tkinter. Dữ liệu thiếu, cũ hoặc không hợp lệ phải được hiển thị rõ thay vì thay bằng giá trị có vẻ hợp lý.

Mục tiêu thử nghiệm gồm thời gian phản hồi lệnh ở điều kiện thuận lợi dưới 200 ms ở phân vị 95, không treo app khi mở serial lỗi, không tự ARM sau reconnect và có log để truy vết. Đây là tiêu chí thiết kế, chưa phải kết quả đã đạt trên robot. Tham số nguồn, dòng kẹt động cơ và giới hạn cơ khí phải được kiểm tra trước khi chạy sàn.

# 3. Thực hiện hệ thống (Implementation)

## 3.1. Kiến trúc phần cứng (Hardware Architecture)

Khung robot gồm hai bánh chủ động lắp với hai động cơ DC và một bánh tự do đỡ thân. Hai bánh có thể quay độc lập để tạo chuyển động vi sai. Cụm siêu âm đặt phía trước, cao hơn mặt sàn và gắn chắc trên servo để hạn chế rung. Pin, mạch công suất và dây dẫn phải được cố định để không mắc vào bánh hoặc trục servo.

### 3.1.1. Danh sách linh kiện

Danh sách dưới đây phân biệt phần cứng đã được chủ đề tài mô tả với phần bổ sung/giả định để hoàn chỉnh phương án. Chưa điền đơn giá vì chưa có danh sách mua thực tế.

@table Bảng 5. Danh sách linh kiện và chức năng
| STT | Linh kiện / số lượng | Chức năng và ghi chú |
|---|---|---|
| 1 | ESP32 robot / 1 | Xử lý cảm biến, điều khiển và radio; loại DevKit cần xác nhận |
| 2 | ESP32 gateway / 1 | Cầu nối USB–ESP-NOW; phần bổ sung theo kiến trúc PC |
| 3 | TB6612FNG / 1 module | Hai cầu H điều khiển hai động cơ; xác nhận đúng module |
| 4 | Động cơ DC / 2 | Bánh trái/phải; chưa có điện áp, tỉ số truyền, dòng kẹt |
| 5 | Cảm biến siêu âm / 1 | Đo khoảng cách; HC-SR04 là mẫu minh họa |
| 6 | Servo / 1 | Quay cảm biến; SG90 là mẫu minh họa |
| 7 | Khung, 2 bánh chủ động, bánh tự do / 1 bộ | Cơ cấu robot vi sai |
| 8 | Pin, bảo vệ pin, công tắc / 1 bộ | Nguồn cơ động; chọn theo động cơ và bộ hạ áp |
| 9 | Bộ nguồn hạ áp / theo thiết kế | Cấp rail logic/cảm biến và servo phù hợp tải |
| 10 | Điện trở chia áp, tụ lọc, dây, đầu nối | Chuyển mức Echo, lọc nguồn và đấu nối |

### 3.1.2. Khối xử lý trung tâm (ESP32)

Phương án chọn các chân không dùng cho flash và tránh chân strapping phổ biến của ESP32 cổ điển. GPIO34 chỉ làm đầu vào nên phù hợp cho Echo. UART0 được giữ cho nạp code và log. GPIO16/17 không được sử dụng trong bảng này để hạn chế xung đột trên một số module có PSRAM; toàn bộ bảng vẫn phải đối chiếu với board thực tế [2].

@table Bảng 6. Bảng đấu nối dự kiến cho ESP32-WROOM-32
| Tín hiệu | GPIO / nguồn | Kết nối và lưu ý |
|---|---|---|
| TB6612 AIN1, AIN2 | GPIO25, GPIO26 | Chiều quay động cơ trái |
| TB6612 PWMA | GPIO27 | PWM động cơ trái, 20 kHz đề xuất |
| TB6612 BIN1, BIN2 | GPIO32, GPIO33 | Chiều quay động cơ phải |
| TB6612 PWMB | GPIO14 | PWM động cơ phải, cùng tần số với PWMA |
| TB6612 STBY | GPIO13 | Kéo xuống bằng 10 kΩ để mặc định tắt khi reset |
| TB6612 VCC / GND | 3V3 / GND chung | Nguồn logic 3,3 V để phù hợp mức GPIO |
| TB6612 VM | Rail động cơ | Theo động cơ và giới hạn TB6612; không dùng 3V3 |
| TB6612 AO1/AO2 | Động cơ trái | Hiệu chỉnh cực tính để PWM dương là tiến |
| TB6612 BO1/BO2 | Động cơ phải | Đối chiếu chiều lắp bánh và dây |
| Siêu âm TRIG | GPIO18 | Nếu module không nhận chắc mức 3,3 V, dùng đệm chuyển mức |
| Siêu âm ECHO | GPIO34 qua chia áp | Ví dụ 10 kΩ phía Echo và 18 kΩ xuống GND |
| Siêu âm VCC / GND | 5 V / GND chung | Áp dụng nếu dùng HC-SR04 |
| Servo signal | GPIO19 | PWM 50 Hz, kênh/timer riêng với PWM động cơ |
| Servo V+ / GND | Nguồn servo riêng / GND chung | Theo đúng loại servo; không lấy dòng từ GPIO/3V3 |

![Hình 2. Sơ đồ nối khối và phân phối nguồn dự kiến](wiring.png)

Với chia áp Echo gồm R1 = 10 kΩ từ Echo tới GPIO và R2 = 18 kΩ từ GPIO xuống GND, điện áp danh định tại GPIO là 5 × 18/(10+18) ≈ 3,21 V. Cần tính cả dung sai điện trở và rail 5 V, đồng thời đo kiểm trước khi nối ESP32. Không nối trực tiếp Echo 5 V vào GPIO 3,3 V. Mạch chia áp này chỉ dành cho tín hiệu Echo, không dùng để cấp nguồn cho module.

### 3.1.3. Cảm biến đầu vào

Nếu sử dụng HC-SR04, vi điều khiển phát xung Trigger mức cao ít nhất 10 µs; cảm biến phát sóng siêu âm và đưa độ rộng xung Echo về bộ xử lý. Từ thời gian truyền khứ hồi t, khoảng cách được ước lượng bằng d = c × t/2. Với c xấp xỉ 343 m/s ở nhiệt độ phòng, d(cm) ≈ t(µs) × 0,0343/2. Ví dụ t = 2000 µs cho khoảng cách khoảng 34,3 cm. Đây là ví dụ tính toán, không phải số liệu đo [4].

Mỗi mẫu đo phải gồm giá trị, cờ hợp lệ, góc servo và dấu thời gian. Khi không có Echo hoặc quá timeout 25 ms, trả về trạng thái không hợp lệ; không gán khoảng cách bằng 0 rồi hiểu là đường thoáng. Chỉ lấy mẫu sau khi servo đã ổn định và giữ khoảng phát lớn hơn 60 ms theo hướng dẫn HC-SR04. Có thể lấy ba mẫu hợp lệ và dùng trung vị, nhưng chi phí thời gian của bộ lọc phải được cộng vào chu kỳ quét [4].

Cảm biến siêu âm có thể phản hồi kém với bề mặt nghiêng, vật mảnh, vải mềm hoặc vật ở vùng quá gần. Thông số trong datasheet không đồng nghĩa sai số của cả hệ lắp ráp. Góc quét và ngưỡng dừng cần được thử với vật cản đại diện ở độ cao thực tế.

### 3.1.4. Khối chấp hành

TB6612FNG điều khiển hai động cơ DC bằng hai cầu H. Nguồn logic VCC và nguồn động cơ VM là hai miền riêng. Theo datasheet, dải hoạt động VCC là 2,7–5,5 V và VM là 2,5–13,5 V; giá trị VM 15 V là giới hạn tuyệt đối, không phải điện áp làm việc đề xuất [3]. Phương án dùng VCC = 3,3 V; VM chọn theo nhãn động cơ và điện áp pin khi đầy.

Dòng 1,2 A trung bình và 3,2 A đỉnh thường được nêu cho IC không cho phép cấp 3,2 A liên tục. Cần đối chiếu điều kiện xung, công suất nhiệt, PCB module và dòng kẹt từng động cơ. Nếu dòng kẹt hoặc nhiệt độ vượt khả năng mạch, phải đổi driver hoặc động cơ. Không thể chốt loại pin và cầu chì khi chưa có số liệu này [3].

@table Bảng 7. Nguyên tắc điều khiển một kênh TB6612
| Trạng thái | STBY | IN1 / IN2 / PWM | Ý nghĩa |
|---|---|---|---|
| Standby | 0 | Không quan trọng | Đầu ra trở kháng cao, tắt cầu H |
| Quay chiều 1 | 1 | 1 / 0 / PWM | Điều chỉnh duty theo độ lớn lệnh |
| Quay chiều 2 | 1 | 0 / 1 / PWM | Đảo chiều so với hàng trên |
| Stop trở kháng cao | 1 | 0 / 0 / 1 | Thả trôi theo bảng trạng thái của IC |
| Short brake | 1 | 1 / 1 / bất kỳ | Phanh ngắn mạch; cần đánh giá quán tính/dòng |

Khi đổi chiều, hạ duty về 0 và chuyển trạng thái theo trình tự đã kiểm tra; tránh đảo chiều đột ngột ở PWM lớn. Lệnh STOP cần xác định rõ dùng short brake ban đầu hay tắt STBY sau đó. PWM bằng 0 và tắt STBY có thể tạo chế độ điện khác nhau; quãng đường dừng phải đo trên robot thay vì suy từ tên lệnh [3].

Servo được cấp bằng rail phù hợp loại thực tế; nếu dùng SG90 tham khảo cần đối chiếu thông số nguồn của nhà sản xuất [5]. Tín hiệu 50 Hz dùng timer riêng với hai PWM 20 kHz để tránh thư viện servo đổi tần số của động cơ. Góc 30°, 90°, 150° chỉ là quy ước phần mềm; cần chỉnh tâm, xác định bên trái/phải và giới hạn để không ép chạm cơ khí. Telemetry phản hồi góc đã ra lệnh, không đo trực tiếp góc trục servo.

Nguồn phải có GND chung giữa ESP32, driver, cảm biến và servo. Dòng motor/servo đi về nguồn bằng đường riêng đủ tiết diện, tránh chạy qua đường GND nhỏ của board ESP32. Đặt tụ lọc gần module theo datasheet, thêm tụ dung lượng phù hợp sau khi đo sụt áp và nhiễu. Không nối song song tùy ý rail 5 V ngoài với USB nếu board không có bảo vệ chống cấp ngược. Khi chọn pin nhiều cell cần mạch bảo vệ và sạc đúng loại.

## 3.2. Lập trình hệ thống nhúng

Phần này là thiết kế thuật toán và giao diện firmware để triển khai sau khi có mã nguồn ESP32 thực tế. Báo cáo không khẳng định các hàm nhúng dưới đây đã được nạp hoặc chạy trên robot. Có thể triển khai bằng Arduino-ESP32 hoặc ESP-IDF; cấu hình ngoại vi cuối cùng phải theo phiên bản sử dụng.

Máy trạng thái chính gồm IDLE, MANUAL, AUTO_FORWARD, AUTO_SCAN, AUTO_TURN và FAULT/ESTOP. Mọi trạng thái chuyển động đều bị chặn bởi estop, watchdog và dữ liệu khoảng cách cần thiết. Chế độ mặc định là IDLE với PWM bằng 0 và chưa ARM.

![Hình 3. Lưu đồ điều khiển tránh vật cản và ưu tiên dừng](flowchart.png)

Auto chạy tiến khi có mẫu đo trước hợp lệ và khoảng trống vượt ngưỡng. Khi gặp vật cản, robot dừng, quét trái–giữa–phải và chỉ chọn bên có khoảng trống hợp lệ. Nếu hai bên đều dưới ngưỡng hoặc phép đo không chắc chắn, robot tiếp tục dừng và báo trạng thái bị chặn. Không tự lùi vì cấu hình không có cảm biến sau.

Khi một bên thoáng, robot quay ở PWM thấp theo từng bước thời gian ngắn, dừng và đo lại hướng trước. Thời gian quay chỉ là ước lượng; không xem đó là góc quay chính xác khi chưa có encoder/IMU. Có thể luân phiên hướng ưu tiên khi hai bên gần bằng nhau để giảm hiện tượng chọn qua lại, nhưng vẫn phải đánh giá khoảng trống trong vùng quét của thân robot.

### 3.2.1. Thiết lập Clock cho hệ thống

Với ESP32 cổ điển, cấu hình CPU 240 MHz có thể được dùng làm điểm xuất phát, còn xung thạch anh và clock ngoại vi do board cùng framework quản lý [2]. Đây là lựa chọn dự kiến, không phải số đo cấu hình của firmware chưa cung cấp. Thuật toán cần lập lịch bằng bộ đếm thời gian đơn điệu, không đếm vòng lặp CPU để tạo khoảng chờ.

Hai kênh PWM motor dùng chung tần số đề xuất 20 kHz và độ phân giải 8 bit; servo dùng tài nguyên timer khác ở 50 Hz. Khi ghép thư viện phải kiểm tra việc cấp phát LEDC/MCPWM để tránh xung đột. Xung Trigger 10 µs dùng bộ định thời có độ phân giải phù hợp; đo Echo bằng capture/RMT/ngắt hoặc phương thức có timeout hữu hạn.

@table Bảng 8. Lịch tác vụ đề xuất
| Tác vụ | Chu kỳ / giới hạn | Ghi chú |
|---|---|---|
| Kiểm tra liên động và PWM | Khoảng 10 ms | Luôn ưu tiên stop/estop/watchdog |
| Kiểm tra hàng đợi nhận | Mỗi vòng tác vụ điều khiển | Không xử lý dài trong callback Wi-Fi |
| Phát siêu âm | Lớn hơn 60 ms mỗi lần | Không phát khi servo chưa ổn định |
| Chờ servo sau đổi góc | Ban đầu 200 ms, cần đo lại | Không dùng delay chặn tác vụ liên động |
| Telemetry | 100 ms | Cho phép lặp giá trị nếu chưa có mẫu mới |
| Watchdog liên kết | 500 ms | Hết hạn dừng và hủy ARM |
| Watchdog drive manual | 300 ms | Heartbeat không thay thế lệnh drive mới |

Nếu lấy ba mẫu với chu kỳ trên 60 ms tại ba góc và chờ servo cho từng lần chuyển góc, một lượt quét có thể mất trên một giây. Vì vậy robot phải dừng trong giai đoạn quét; không đặt mục tiêu làm mới đủ ba hướng ở 10 Hz. Tần số telemetry 10 Hz là tốc độ gửi trạng thái, không phải tần số có phép đo mới ở mọi hướng.

### 3.2.2. Khởi tạo cảm biến

Trình tự khởi tạo đề xuất: đặt PWM = 0 và STBY = 0; cấu hình GPIO và timer; đưa servo về tâm; chờ ổn định theo lịch; đo khoảng cách trước; khởi tạo Wi-Fi/ESP-NOW và peer; sau đó phát trạng thái chưa ARM. Thứ tự luôn bảo đảm công suất motor chưa được bật trong quá trình boot.

Khi đo, tạo Trigger, ghi nhận cạnh lên/cạnh xuống Echo và kiểm tra khoảng thời gian. Loại mẫu quá thời hạn, vượt vùng hợp lệ của module hoặc không thuộc góc đã ổn định. Nếu cảm biến lỗi liên tiếp, đưa về FAULT hoặc hủy ARM theo chính sách thống nhất và báo sensor_ok=false. Không giữ một mẫu cũ quá lâu rồi dùng như phép đo hiện tại.

Ở manual, khi đã đưa cảm biến sang bên để quan sát, lệnh tiến cần đưa servo về tâm và lấy phép đo trước mới trước khi chạy. Với auto, mỗi phép đo được lưu vào ô trái/giữa/phải cùng dấu thời gian. Phiên bản telemetry tối giản hiện chỉ gửi phép đo gần nhất và góc tương ứng; khi cần hiển thị đủ ba hướng phải mở rộng giao thức một cách có phiên bản.

### 3.2.3. Chương trình điều khiển (hàm main)

Vòng điều khiển dùng một nguồn trạng thái duy nhất để tránh tác vụ mạng và tác vụ cảm biến cùng ghi đầu ra motor. Khi nhận lệnh, kiểm tra cú pháp, phiên, thứ tự, mode và ARM trước khi cập nhật yêu cầu. ACK chỉ phản ánh lệnh được chấp nhận/từ chối; không đồng nghĩa robot đã đi tới một vị trí mong muốn.

```text
Khởi tạo → PWM=0, chưa ARM, manual
Lặp:
  Đọc hàng đợi lệnh; kiểm tra phiên/seq; xử lý STOP trước
  Nếu estop hoặc mất liên kết: dừng, hủy ARM
  Nếu cảm biến bắt buộc lỗi/cũ: dừng và báo lỗi
  Nếu manual: áp dụng drive còn hạn và liên động khoảng cách
  Nếu auto: tiến hoặc dừng–quét–chọn hướng–quay từng bước
  Cập nhật servo/đo Echo theo lịch không chặn
  Gửi ACK và telemetry đến gateway
```

Ngưỡng dừng phải lớn hơn tổng khoảng đi được trong thời gian trễ, quãng phanh và biên dự phòng. Với vận tốc v, độ trễ xử lý T, gia tốc giảm tốc a và biên khoảng cách dự phòng, điều kiện thiết kế là:

@equation stop_distance

Ví dụ minh họa với v = 0,2 m/s, độ trễ 0,25 s, gia tốc giảm tốc 0,5 m/s² và biên 0,10 m cho khoảng dừng yêu cầu ít nhất 0,19 m. Giá trị 30 cm chỉ là ngưỡng thử ban đầu; các số trên chưa được đo trên robot. Nếu độ trễ hoặc quãng phanh thực tế lớn hơn, cần tăng khoảng dừng và giảm PWM.

Với hai bánh cách nhau b, quan hệ lý tưởng giữa vận tốc bánh phải, bánh trái và vận tốc thân robot là:

@equation differential

Trong đó v là vận tốc tịnh tiến, ω là vận tốc góc; hai chỉ số R và L biểu diễn bánh phải và bánh trái. Không có encoder thì vận tốc từng bánh chưa được đo, và PWM không tỷ lệ tuyến tính với vận tốc khi thay tải hoặc điện áp pin. Vì vậy điều khiển vi sai ở đây là điều khiển hở; cần hệ số cân bằng bánh sau khi thử, chưa thể khẳng định robot đi thẳng hoặc quay đúng góc.

## 3.3. Lập trình App/Website

App desktop sử dụng Tkinter cho giao diện và pyserial cho USB. Phần nhận serial chạy trong luồng nền có timeout, đưa gói qua hàng đợi; vòng giao diện cập nhật khoảng 40 ms. Bộ ghép dòng giữ các byte chưa hoàn chỉnh qua nhiều lần đọc, loại toàn bộ dòng quá dài rồi đồng bộ lại ở LF tiếp theo. Cách tổ chức này phù hợp với việc một JSON có thể bị chia thành nhiều lần đọc [6].

@table Bảng 9. Các module phần mềm bàn giao
| Module | Nội dung đã triển khai |
|---|---|
| main.py | Khởi động app; tùy chọn --demo |
| gui.py | Nút hướng/phím giữ, trạng thái, đồ thị khoảng cách, CSV |
| controller.py | Phiên kết nối, pending ACK, ARM, mode, watchdog phía app |
| protocol.py | Mã hóa, kiểm tra kiểu/giới hạn và ghép dòng serial |
| transport.py | SerialTransport và bộ mô phỏng DemoTransport |
| test_system.py | Các bài kiểm tra giao thức, liên động và lỗi |
| PROTOCOL.md | Hợp đồng gateway/robot và thời hạn các lệnh |

![Hình 4. Sơ đồ bố trí giao diện app Python theo mã đã xây dựng](app_layout.png)

Hình 4 là sơ đồ bố trí chức năng dựng từ mã giao diện, không phải ảnh chạy robot hoặc minh chứng thực nghiệm. Khi hoàn thiện tích hợp nên thay/bổ sung ảnh app đang nhận telemetry SERIAL và ảnh tổng thể robot.

Quy trình sử dụng: chọn kết nối; chờ ACK hello và telemetry; nhấn ARM; chọn manual hoặc auto. Ở manual, giữ W/A/S/D hoặc nút hướng để chạy. Thả phím/nút gửi PWM 0/0. STOP/Space hủy ARM và về manual. Estop/Esc chốt dừng khẩn phần mềm; muốn chạy lại phải xóa chốt rồi ARM. Mất focus cửa sổ cũng gửi STOP để tránh lệnh giữ tiếp tục ngoài ý muốn.

App không dùng ACK sai phiên hoặc sai tên lệnh để mở khóa. Khi đang chờ xác nhận chuyển mode, lệnh manual mới bị chặn. ACK ARM đến muộn sau STOP bị bỏ qua. Khi một lệnh không được ACK trong 650 ms hoặc telemetry quá 1 s, app báo lỗi, hủy cho phép điều khiển và yêu cầu kết nối lại. Phần cứng thật vẫn cần watchdog trên robot vì app không thể bảo đảm gói STOP đến nơi khi RF đã mất.

Đồ thị chỉ nối các mẫu khoảng cách hợp lệ; mẫu không hợp lệ tạo khoảng ngắt. CSV ghi thời gian máy tính, nguồn SIMULATION/SERIAL, mã phiên, mode, ARM, estop, sensor_ok, khoảng cách, góc và hai PWM. Nhật ký mô phỏng không được dùng như kết quả đo cảm biến. Góc servo/PWM phản hồi đều là trạng thái lệnh phần mềm, chưa phải đo góc hoặc đo vòng quay độc lập.

Bộ mô phỏng giúp thử giao thức, chuyển trạng thái và mất liên kết mà không có robot. Khoảng cách biến thiên được tạo bằng hàm toán học; mô phỏng không tái hiện lực phanh, độ trượt bánh, dòng điện, sóng siêu âm hay hình học không gian. Khi có firmware khác với JSON đề xuất, cần viết adapter ở gateway hoặc cập nhật protocol.py/transport.py rồi chạy lại kiểm tra trước khi nối motor.

# 4. Kiểm chứng (Validation)

## 4.1. Kiểm chứng chức năng

Việc kiểm chứng được tách thành kiểm tra phần mềm đã thực hiện và thử nghiệm phần cứng chưa có dữ liệu. Các phép thử trên máy tính dùng Python 3.12.14, thư viện unittest và bộ mô phỏng; không dùng kết quả này để kết luận về khoảng cách radio, sai số cảm biến hoặc hiệu quả tránh va chạm ngoài thực tế.

@table Bảng 10. Kết quả kiểm tra phần mềm
| Nhóm thử | Nội dung | Kết quả thực tế |
|---|---|---|
| Giao thức | Mã hóa/giải mã, chia nhỏ dòng, CRLF, nhiều bản tin | Đạt qua kiểm tra tự động |
| Dữ liệu lỗi | PWM ngoài dải, JSON sai, NaN, dòng quá dài, ngân sách byte | Đạt qua kiểm tra tự động |
| Cho phép chạy | Kết nối chưa ARM; chỉ ARM sau ACK hợp lệ | Đạt với bộ mô phỏng |
| Dừng và chốt | STOP, ACK ARM muộn, estop và ACK reset muộn | Đạt với bộ mô phỏng |
| Chế độ | Auto chặn drive manual, chặn drive khi chờ ACK mode | Đạt với bộ mô phỏng |
| Mất liên kết | Mất ACK, mất telemetry, phiên sai, lỗi ghi serial | Đạt với đối tượng mô phỏng |
| Khôi phục | Mã phiên mới khi reconnect; không tự ARM | Đạt với bộ mô phỏng |
| Liên động robot giả lập | Sensor lỗi, watchdog liên kết và lease drive độc lập | Đạt với bộ mô phỏng |

Tổng số bài kiểm tra và log chi tiết được ghi trong TEST_RESULTS.txt đi kèm. Kết quả cuối cùng phải đối chiếu đúng log chạy của phiên bản mã bàn giao. Kiểm tra serial ở đây bao gồm bộ ghép dòng và xử lý lỗi bằng dữ liệu giả; chưa xác nhận USB-UART của board hay đường ESP-NOW thật.

@table Bảng 11. Kế hoạch kiểm chứng trên robot thật
| Mã / chức năng | Điều kiện thử | Kết quả mong đợi | Thực tế |
|---|---|---|---|
| HW01 / Boot | Nâng bánh, bật nguồn/reset nhiều lần | PWM 0, chưa ARM; không giật bánh | Chưa đo |
| HW02 / Motor | Nâng bánh; PWM thấp từng kênh | Chiều đúng; không reset do sụt áp | Chưa đo |
| HW03 / Khoảng cách | Vật phẳng tại 10/20/30/50/100 cm; mỗi mốc 20 mẫu | Sai số và tỷ lệ mẫu hợp lệ được thống kê | Chưa đo |
| HW04 / Servo | Tâm/trái/phải, ít nhất 10 chu kỳ | Không chạm cơ khí; hướng đúng quy ước | Chưa đo |
| HW05 / Manual | Sàn trống, tốc độ thấp, giữ/thả hướng | Thả dừng; STOP hủy ARM | Chưa đo |
| HW06 / Auto | Vật trước, trái bị chặn, phải bị chặn | Dừng–quét–chọn bên thoáng | Chưa đo |
| HW07 / Bị bao vây | Cả hai bên gần vật cản | Tiếp tục dừng; không tự lùi mù | Chưa đo |
| HW08 / Lỗi sensor | Che/ngắt Echo trong điều kiện kiểm soát | Dừng, báo không hợp lệ, không dùng mẫu cũ | Chưa đo |
| HW09 / Mất USB/RF | Khi manual và auto, ngắt liên kết có giám sát | Watchdog robot dừng trong giới hạn đặt | Chưa đo |
| HW10 / Reconnect | Khôi phục sau HW09 | Không tự chạy; cần ARM lại | Chưa đo |
| HW11 / Nhiệt/nguồn | Chạy tải vừa, theo dõi điện áp và nhiệt | Không quá nhiệt/sụt áp vượt giới hạn linh kiện | Chưa đo |

Đối với siêu âm, ghi cả mẫu mất Echo thay vì xóa khỏi tập dữ liệu. Tính sai số trung bình tuyệt đối MAE bằng trung bình độ lớn chênh lệch giữa từng mẫu hợp lệ và khoảng cách chuẩn. Tỷ lệ hợp lệ bằng số mẫu hợp lệ chia tổng số mẫu thử. Cần ghi vật liệu, góc đặt vật, nhiệt độ gần đúng và độ cao lắp để giải thích sai số.

Đối với truyền thông, gửi ít nhất 100 lệnh ở từng khoảng cách thử, ghi thời gian từ phát lệnh đến ACK tại app và thống kê trung vị, phân vị 95 cùng tỷ lệ mất ACK. Phép đo này là độ trễ vòng lệnh–ACK qua gateway và robot; không phải độ trễ một chiều và không đo trực tiếp thời điểm bánh bắt đầu quay. Không thực hiện thử liên tục các lệnh chuyển động khi robot không được giám sát.

Đối với dừng, đo từ lúc xuất hiện điều kiện lỗi đến lúc bánh dừng bằng video hoặc tín hiệu đo phù hợp. Thời hạn phần mềm 500 ms chỉ là giới hạn phát hiện mất liên kết; tổng thời gian đứng yên còn có chu kỳ tác vụ, xử lý công suất và quán tính. Khoảng dừng thực phải dùng để chỉnh ngưỡng 30/40 cm. Mỗi kịch bản tránh vật cản nên lặp ít nhất 10 lần, ghi va chạm, dừng đúng và trường hợp kẹt để đánh giá minh bạch.

Minh chứng cần bổ sung gồm ảnh dây nguồn/driver, ảnh giá đỡ servo, ảnh app nhận dữ liệu SERIAL, CSV gốc, log test và video chạy. Chưa có các dữ liệu này nên báo cáo chỉ xác nhận phần thiết kế và phần mềm máy tính, chưa kết luận toàn hệ thống đạt yêu cầu.

## 4.2. Minh chứng video

Video dự kiến gồm các đoạn: giới thiệu phần cứng và nguồn; boot ở trạng thái dừng; kết nối app và ARM; điều khiển manual; dừng/thả phím; servo quét và auto chọn hướng; tình huống bị chặn cả hai bên; ngắt gateway hoặc mất RF; khôi phục mà robot không tự chạy. Khung hình nên đồng thời cho thấy robot và trạng thái app khi có thể.

Liên kết video: chủ đề tài bổ sung sau khi hoàn tất thử nghiệm. Chưa có video minh chứng ở phiên bản hiện tại. Không dùng video bộ mô phỏng để thay cho chứng minh robot thật.

# 5. Kết luận (Conclusion)

Báo cáo đã xây dựng phương án robot di động ESP32 với cảm biến siêu âm trên servo, hai động cơ DC và driver TB6612FNG; mô tả yêu cầu, bảng đấu nối dự kiến, phân phối nguồn, thuật toán tránh vật cản, giao thức ESP-NOW qua gateway và quy trình kiểm chứng. App Python đã được viết cùng chế độ mô phỏng, điều khiển manual/auto, ARM, STOP/estop phần mềm, theo dõi trạng thái, đồ thị và lưu CSV.

Mức hoàn thành được giới hạn theo bằng chứng: phần app và các kiểm tra tự động đã có mã và log; phần firmware, RF, nguồn, quãng đường dừng và tránh vật cản trên robot thật chưa được kiểm chứng. Cần nhận code ESP32 của chủ đề tài để chốt chân, cấu trúc bản tin, timer PWM/servo và hành vi watchdog, sau đó thực hiện các phép thử của Chương 4. Các thông số minh họa không được chuyển thành kết quả thực nghiệm khi chưa đo.

Giới hạn chính là góc nhìn hẹp của một cảm biến, thời gian quét nhiều hướng, điều khiển motor hở và thiếu cảm biến phía sau. Nguyên mẫu hiện hướng tới tránh vật cản phản ứng ở tốc độ thấp; chưa đủ cơ sở cho định vị chính xác, tự đi tới mục tiêu hoặc vận hành độc lập trong không gian có người.

## Hướng phát triển

Ưu tiên tiếp theo là tích hợp firmware và đo kiểm các liên động. Sau đó có thể bổ sung encoder để điều khiển vận tốc vòng kín và odometry; IMU để hỗ trợ hướng quay; cảm biến phía sau/bên hông và phát hiện mép sàn; giám sát pin, dòng motor và công tắc dừng công suất. Khi có dữ liệu định vị đủ tin cậy mới mở rộng sang lập bản đồ và lập kế hoạch đường đi. App có thể bổ sung cấu hình tham số theo phiên bản, hiển thị ba hướng đo và đóng gói thành chương trình độc lập.

# Tài liệu tham khảo

[1] Espressif Systems. ESP-NOW, ESP-IDF Programming Guide. https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/network/esp_now.html. Truy cập ngày 08/11/2026.

[2] Espressif Systems. ESP32 Series Datasheet. https://documentation.espressif.com/esp32_datasheet_en.pdf. Truy cập ngày 08/11/2026.

[3] Toshiba Electronic Devices & Storage Corporation. TB6612FNG Datasheet, mục Operating Range, Absolute Maximum Ratings và Control Function. https://toshiba.semicon-storage.com/info/datasheet_en_20141001.pdf?did=10660. Truy cập ngày 08/11/2026.

[4] ELECFREAKS. Ultrasonic Ranging Module HC-SR04, tài liệu do SparkFun lưu trữ. https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf. Truy cập ngày 08/11/2026.

[5] TowerPro. SG90 Digital, thông số nhà sản xuất. https://towerpro.com.tw/product/sg90-7/. Truy cập ngày 08/11/2026. Chỉ dùng làm tham chiếu khi linh kiện thực tế đúng loại.

[6] pySerial. API documentation. https://pyserial.readthedocs.io/en/latest/pyserial_api.html. Truy cập ngày 08/11/2026.

# Phụ lục A. Chạy app và tích hợp firmware

## A.1. Chạy mô phỏng

Cài Python 3.10 trở lên có Tkinter. Mở thư mục amr_controller và chạy lệnh dưới đây; hoặc nhấp run_demo.bat trên Windows. Mô phỏng không cần pyserial, gateway hoặc robot.

```text
python main.py --demo
```

Chờ trạng thái MÔ PHỎNG / SẴN SÀNG, nhấn ARM và thử các chức năng. Dùng hai ô kiểm mô phỏng để thử mất liên kết và cảm biến không hợp lệ. Mô phỏng luôn được đánh dấu riêng trong giao diện và CSV.

## A.2. Chạy với phần cứng

```text
python -m pip install -r requirements.txt
python main.py
python -m unittest -v test_system
```

Đóng Serial Monitor đang giữ cổng; cắm ESP32 gateway; chọn đúng COM và kết nối. Chỉ tiến hành chạy motor khi firmware hai ESP32 đã tương thích PROTOCOL.md và thử nâng bánh đạt yêu cầu. Nếu code hiện có dùng bản tin khác, cung cấp ví dụ gói TX/RX để chỉnh adapter trước.

## A.3. Thông tin chủ đề tài cần hoàn thiện

@table Bảng 12. Thông tin cần bổ sung khi hoàn thiện nguyên mẫu
| Nội dung | Trạng thái cần bổ sung |
|---|---|
| Họ tên, MSSV, vai trò và tỷ lệ đóng góp | Chủ đề tài tự điền |
| Tên học phần, giảng viên, lớp | Điền theo yêu cầu học phần nếu cần |
| GitHub và phiên bản firmware | Bổ sung sau khi có mã nguồn |
| Board, sensor, servo chính xác | Xác nhận trước khi đấu nguồn/chân |
| Motor, pin, dòng tải/dòng kẹt | Đo/tra thông số để chọn nguồn và driver |
| MAC, kênh radio, baudrate, phiên bản framework | Chốt khi ghép gateway và robot |
| Kích thước bánh/khoảng cách hai bánh | Đo để phân tích cơ cấu vi sai |
| CSV, ảnh, video và bảng kết quả thực | Bổ sung sau thử nghiệm; không thay bằng dữ liệu giả |
