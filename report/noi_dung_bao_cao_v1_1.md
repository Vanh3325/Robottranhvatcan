# 1. Giới thiệu (Introduction)

## 1.1. Động lực (Motivation)

Robot di động là một mô hình phù hợp để kết hợp kiến thức về vi điều khiển, cảm biến, điều khiển động cơ và lập trình hệ thống nhúng. Bài toán phát hiện vật cản và lựa chọn hướng di chuyển giúp kiểm chứng toàn bộ chuỗi xử lý từ đo khoảng cách đến điều khiển cơ cấu chấp hành.

Đề tài sử dụng ESP32, hai động cơ DC qua driver TB6612FNG và một cảm biến siêu âm gắn trên servo. Phiên bản firmware đã được triển khai theo chế độ tự động: robot chạy tiến chậm, phát hiện vật cản phía trước, dừng, quét hai bên, lùi một đoạn và rẽ về phía có khoảng cách đo lớn hơn. Nhóm thực hiện xác nhận chương trình đã chạy trên phần cứng và các chức năng của phiên bản tự động hoạt động đạt yêu cầu thử nghiệm.

Trong báo cáo, AMR được hiểu là nguyên mẫu robot di động có khả năng phản ứng với vật cản. Cấu hình và mã nguồn hiện tại chưa có định vị, lập bản đồ hoặc điều hướng tới tọa độ. App Python và phương án ESP-NOW đã được thiết kế ở phía máy tính; firmware được đánh giá là bản tự hành độc lập, chưa chứa phần nhận lệnh không dây.

## 1.2. Mục tiêu (Objectives)

Mục tiêu chính là xây dựng robot ESP32 có thể chạy chậm, đo khoảng cách theo hướng servo và tự lựa chọn hướng tránh vật cản. Các tham số điều khiển phải phản ánh đúng cấu hình đã nạp và đã được nhóm kiểm thử.

@table Bảng 1. Mục tiêu và mức độ hoàn thành
| Mã | Mục tiêu | Mức độ hoàn thành |
|---|---|---|
| MT01 | Điều khiển hai động cơ DC qua TB6612 | Đã chạy trên phần cứng; nhóm xác nhận đạt |
| MT02 | Điều khiển servo và đọc siêu âm theo hướng | Đã kiểm thử chức năng; nhóm xác nhận đạt |
| MT03 | Chạy tiến, dừng, quét, lùi và rẽ tránh vật cản | Đã kiểm thử chu trình tự động; nhóm xác nhận đạt |
| MT04 | Theo dõi khoảng cách và trạng thái qua Serial | Có log 115200 baud trong firmware; nhóm xác nhận hoạt động |
| MT05 | Điều khiển từ app Python qua ESP-NOW | Đã có app/mô phỏng và đặc tả; chưa tích hợp trong firmware hiện tại |

Kết quả “đạt” trong báo cáo là xác nhận kiểm thử chức năng của nhóm thực hiện. Chưa có bộ số liệu định lượng về sai số khoảng cách, thời gian dừng, số lần lặp hay tỷ lệ tránh va chạm để suy ra các chỉ tiêu thống kê.

## 1.3. Nội dung chính (Main Contents)

Báo cáo trình bày yêu cầu và kiến trúc hệ thống; bảng GPIO, PWM và các tham số đúng theo firmware; nguyên lý đọc siêu âm, điều khiển servo và motor; lưu đồ chương trình tự động; phần app Python và giao tiếp dự kiến; kết quả kiểm thử chức năng cùng hướng phát triển. Phụ lục ghi lại cấu hình để thuận tiện đối chiếu khi nạp hoặc chỉnh sửa chương trình.

# 2. Yêu cầu đối với thiết kế (Requirements)

## 2.1. Yêu cầu chung

Robot sử dụng cơ cấu hai bánh chủ động điều khiển độc lập. Cảm biến siêu âm được gắn trên servo để đo phía trước, bên trái và bên phải. ESP32 nhận xung Echo, tính khoảng cách, so sánh với ngưỡng 30 cm và phát tín hiệu cho TB6612. Firmware hiện tại vận hành tự động ngay sau trình tự khởi tạo, không yêu cầu thao tác ARM từ app.

@table Bảng 2. Chức năng của firmware đã triển khai
| Mã | Chức năng | Hành vi trong mã nguồn |
|---|---|---|
| F01 | Khởi tạo hệ thống | Cấu hình GPIO/LEDC, bật STBY, đặt motor 0 và servo tâm |
| F02 | Tự chạy sau khởi tạo | Chờ 800 ms, in READY rồi tăng PWM tiến tới 46/54 |
| F03 | Phát hiện vật cản | Đo phía trước; khoảng cách không lớn hơn 30 cm kích hoạt tránh |
| F04 | Khảo sát hai bên | Servo tới trái 150°, phải 30°; đo hai mẫu ở mỗi hướng |
| F05 | Lùi trước khi rẽ | PWM logic trái/phải −34/−50; giữ thêm 220 ms sau ramp |
| F06 | Chọn hướng | Trái lớn hơn hoặc bằng phải thì rẽ trái; còn lại rẽ phải |
| F07 | Rẽ một bánh | Rẽ trái dùng 0/56; rẽ phải dùng 42/0, giữ thêm 380 ms |
| F08 | Giám sát Serial | FRONT định kỳ theo millis; SCAN, TURN và trạng thái vật cản |

![Hình 1. Kiến trúc bản tự hành và phần mở rộng app ESP-NOW](architecture_actual.png)

Phạm vi kiểm thử đã được xác nhận là các chức năng tự hành trong mã nguồn. Bản hiện tại chưa có nhận lệnh manual, ARM, estop phần mềm, ACK ứng dụng hoặc watchdog mất liên kết. Các chức năng này được đặt trong phần mở rộng app/ESP-NOW, không dùng làm tiêu chí đã đạt của firmware tự động.

## 2.2. Đặc tả kỹ thuật (Specification)

Các hằng số dưới đây được trích từ chương trình nhóm đã chạy thành công. Giá trị thời gian là tham số phần mềm; không được hiểu là số đo thực tế của quãng đường, góc quay hoặc thời gian bánh dừng hoàn toàn.

@table Bảng 3. Các tham số đúng theo firmware đã kiểm thử
| Hạng mục | Giá trị cấu hình | Ý nghĩa |
|---|---|---|
| PWM motor | 20.000 Hz; 8 bit | Hai đầu ra PWMA/PWMB, duty 0–255 |
| PWM servo | 50 Hz; 14 bit | Chu kỳ 20 ms; duty theo độ rộng xung |
| PWM tiến | Trái 46; phải 54 | Giá trị logic trước bù chiều motor phải |
| PWM lùi | Trái −34; phải −50 | Được truyền vào hàm ramp |
| PWM rẽ | Trái 42; phải 56 | Mỗi lần rẽ chỉ chạy một bánh |
| Bù chiều motor phải | RIGHT_MOTOR_SIGN = −1 | Đảo dấu tại setRightMotor() |
| Ramp motor | Bước 2 đơn vị, chờ 20 ms mỗi bước | Áp dụng cả tăng, giảm tốc và đổi chiều |
| Ngưỡng vật cản | 30,0 cm | Tránh khi frontCm ≤ 30 |
| Góc servo | Giữa 90°; trái 150°; phải 30° | Quy ước đã dùng trong chương trình |
| Di chuyển servo | 1° mỗi 15 ms; chờ ổn định 250 ms | Thời gian chờ sau khi tới hướng đo |
| Đo Echo | Timeout 30.000 µs | pulseIn(ECHO_PIN, HIGH, 30000UL) |
| Lọc khi nhìn hai bên | 2 mẫu cách nhau 40 ms | Trung bình nếu cả hai nhỏ hơn 399 cm |
| Thời gian giữ lùi/rẽ | 220 ms / 380 ms | Bắt đầu sau khi ramp tới PWM đích |
| Serial / vòng lặp | 115200 baud; delay cuối loop 80 ms | FRONT có điều kiện in mỗi 500 ms |

### 2.2.1. Kiến trúc tổng thể

Trong phiên bản đã chạy, quyết định điều hướng được thực hiện hoàn toàn trên ESP32. Đường dữ liệu chính là siêu âm → ESP32 → TB6612 → hai motor. Servo quay cảm biến theo lệnh của ESP32; Serial phục vụ theo dõi trạng thái khi có kết nối với máy tính. Robot không cần gateway hay cloud để thực hiện chu trình tránh vật cản hiện tại.

Phần mở rộng sử dụng app Python → USB → ESP32 gateway → ESP-NOW → ESP32 robot. Kiến trúc này được giữ lại cho giai đoạn điều khiển từ xa. Mã nguồn hiện có không gọi Wi-Fi/ESP-NOW, không phân tích JSON và không đọc lệnh từ Serial; vì vậy app chưa thể điều khiển trực tiếp bản firmware này bằng giao thức đã đề xuất.

### 2.2.2. Đặc tả Node IoT (ESP32 trên robot)

ESP32 điều khiển bảy tín hiệu của TB6612, một đầu ra servo, một Trigger và một Echo. Các chân 47 và 48 trong cấu hình mới thay thế hoàn toàn phương án ESP32-WROOM-32 của bản thiết kế ban đầu. Báo cáo lấy số GPIO trong code làm căn cứ; tên thương mại chính xác của board chưa được ghi trong mã. Tập chân này phù hợp với các board thuộc nhóm ESP32-S3 có đưa các GPIO tương ứng ra ngoài; cần đối chiếu sơ đồ board khi thay phần cứng [2].

Mã nguồn tổ chức bằng các hàm riêng cho PWM, chiều motor, ramp, góc servo, đo khoảng cách và tránh vật cản. Các biến currentLeftPwm, currentRightPwm và currentServoAngle theo dõi giá trị lệnh phần mềm hiện tại. Chúng không phải số đo từ encoder hoặc cảm biến vị trí servo.

### 2.2.3. Đặc tả Gateway (ESP32)

Gateway là thành phần của phương án mở rộng, chưa có trong firmware tự hành đã cung cấp. Nhiệm vụ dự kiến là chuyển tiếp dữ liệu USB serial và ESP-NOW giữa app với robot. Khi bổ sung, cần thống nhất MAC peer, kênh Wi-Fi, cách đóng gói và xác nhận lệnh. Hai thiết bị ESP-NOW phải sử dụng cấu hình radio phù hợp để trao đổi được dữ liệu [1].

Gateway không được coi log FRONT/SCAN hiện tại là ACK điều khiển. Để dùng app, cần thêm bộ nhận lệnh trên robot và phần gửi trạng thái có cấu trúc. Các lệnh STOP phải có đường xử lý phù hợp với chương trình nhúng; chỉ đổi cổng COM ở app không tạo ra chức năng còn thiếu trong firmware.

### 2.2.4. Đặc tả Cloud (nếu có)

Hệ thống hiện không sử dụng cloud, tài khoản hoặc cơ sở dữ liệu Internet. Thuật toán tự động nằm trên ESP32, còn Serial được dùng để quan sát. App Python có khả năng ghi CSV ở phía máy tính trong chế độ mô phỏng hoặc khi nhận đúng telemetry sau tích hợp. Nếu bổ sung cloud, chức năng điều khiển trực tiếp và dừng tại robot vẫn cần được thiết kế độc lập với đường Internet.

### 2.2.5. Đặc tả Website/App

App Python/Tkinter đã được xây dựng ở phần mềm máy tính với các chức năng chọn nguồn kết nối, điều khiển hướng khi giữ nút/phím, đổi mode, ARM, STOP/estop phần mềm, đặt góc servo, đồ thị và ghi CSV. Chế độ mô phỏng cho phép kiểm tra giao diện và giao thức mà không cần robot.

Đối với firmware hiện tại, các chức năng nói trên là giao diện đã chuẩn bị cho giai đoạn tích hợp. Robot tự chạy theo setup()/loop() và chưa nhận các lệnh này. Phần app không được ghi là đã điều khiển robot qua ESP-NOW trong kết quả kiểm thử hiện tại.

### 2.2.6. Đặc tả truyền thông

Giao tiếp đã triển khai là Serial.begin(115200) cùng các thông báo dạng văn bản. Trong loop(), chương trình in khoảng cách FRONT khi thời gian kể từ lần in trước đạt 500 ms. Khi đang thực hiện hàm tránh vật cản có nhiều delay, thông báo FRONT có thể bị gián đoạn; đây không phải luồng telemetry cố định 2 Hz trong mọi trạng thái.

@table Bảng 4. Thông báo Serial có trong chương trình
| Thông báo | Thời điểm / ý nghĩa |
|---|---|
| # READY - SLOW AUTO FORWARD | Kết thúc khởi tạo, chuẩn bị gọi forward() |
| # FRONT …cm | Giá trị phía trước, theo điều kiện in mỗi 500 ms trong loop |
| # OBSTACLE - STOP AND SCAN | Khoảng cách trước không lớn hơn 30 cm |
| # SCAN left=…cm right=…cm | Kết quả đo bên trái và bên phải |
| # TURN LEFT / # TURN RIGHT | Hướng được chọn theo phép so sánh hai bên |

Đây là mô tả định dạng lấy từ mã nguồn, không phải log đo được đính kèm. Firmware chỉ gửi thông tin qua Serial; chưa có hàm nhận lệnh, xác nhận ACK hoặc bản tin JSON. Giao thức JSON/ESP-NOW trong PROTOCOL.md của app là đặc tả cho phần mở rộng.

Khi tích hợp, app dự kiến sử dụng mã phiên, số thứ tự lệnh, ACK và telemetry. Giới hạn nội dung 240 byte trong thiết kế app nằm dưới mức 250 byte của ESP-NOW v1 [1]. Cần thêm watchdog liên kết, quyền điều khiển manual/auto và cơ chế dừng ưu tiên trên robot; các cơ chế này chưa được thực hiện bởi code tự hành hiện tại.

### 2.2.7. Yêu cầu phi chức năng

Phiên bản tự hành ưu tiên di chuyển chậm và thay đổi PWM từng bước để hạn chế thay đổi đột ngột. Các giá trị PWM trái/phải khác nhau được chọn cho từng hành động; nhóm xác nhận mô hình hoạt động đạt khi chạy thử. Chưa có dữ liệu tốc độ hoặc quãng đường để quy đổi các mức PWM này sang m/s.

Chương trình hiện dùng vòng chờ trong moveMotorsSlow(), servoMoveSlow(), pulseIn() và các lệnh delay(). Cách lập trình này đơn giản cho chu trình tự hành đã thử, nhưng có thể làm chậm việc nhận lệnh nếu bổ sung điều khiển không dây. Do đó yêu cầu xử lý STOP/ESP-NOW kịp thời thuộc giai đoạn refactor theo thời gian không chặn.

# 3. Thực hiện hệ thống (Implementation)

## 3.1. Kiến trúc phần cứng (Hardware Architecture)

Robot gồm hai động cơ DC điều khiển độc lập qua TB6612FNG và cụm siêu âm trên servo. ESP32 đọc khoảng cách trước để quyết định tiếp tục tiến hay thực hiện chu trình tránh. Nhóm đã kiểm thử mô hình thực và xác nhận các khối hoạt động ổn trong các phép thử chức năng đã thực hiện.

### 3.1.1. Danh sách linh kiện

@table Bảng 5. Linh kiện và phạm vi sử dụng
| STT | Linh kiện / số lượng | Chức năng |
|---|---|---|
| 1 | ESP32 / 1 board | Bộ điều khiển trung tâm; dùng GPIO đúng bảng 6 |
| 2 | TB6612FNG / 1 module | Hai cầu H cho hai động cơ DC |
| 3 | Động cơ DC / 2 | Bánh trái và bánh phải |
| 4 | Cảm biến siêu âm / 1 | Đo khoảng cách; mã linh kiện chưa ghi trong code |
| 5 | Servo / 1 | Quay cảm biến về 30°, 90°, 150° |
| 6 | Khung, bánh và giá đỡ / 1 bộ | Cơ cấu robot và cụm quét |
| 7 | Nguồn, dây nối và công tắc / 1 bộ | Cấp điện và kết nối mô hình |
| 8 | ESP32 gateway / dự kiến 1 | Chỉ cần khi mở rộng điều khiển ESP-NOW từ app |

HC-SR04 và SG90 được dùng làm linh kiện tham chiếu cho phần giải thích nguyên lý. Mã nguồn không xác định tên module, điện áp pin, dòng motor hoặc cấu hình bộ nguồn; các thông tin này cần điền theo linh kiện thực tế thay vì suy ra từ GPIO.

### 3.1.2. Khối xử lý trung tâm (ESP32)

Bảng đấu nối được cập nhật trực tiếp từ các dòng #define của firmware đã được nhóm kiểm thử [8]. AIN1/AIN2 và BIN1/BIN2 quyết định chiều quay; PWMA/PWMB quyết định duty. STBY được bật mức HIGH trong setup() và không bị hạ về LOW khi gọi stopCar().

@table Bảng 6. Cấu hình GPIO thực tế trong firmware
| Tín hiệu | Hằng số trong code | GPIO / kết nối |
|---|---|---|
| TB6612 PWMA | TB_PWMA_PIN | GPIO21 |
| TB6612 AIN1 | TB_AIN1_PIN | GPIO48 |
| TB6612 AIN2 | TB_AIN2_PIN | GPIO47 |
| TB6612 STBY | TB_STBY_PIN | GPIO39 |
| TB6612 BIN1 | TB_BIN1_PIN | GPIO40 |
| TB6612 BIN2 | TB_BIN2_PIN | GPIO41 |
| TB6612 PWMB | TB_PWMB_PIN | GPIO42 |
| Siêu âm ECHO | ECHO_PIN | GPIO4, cấu hình INPUT |
| Siêu âm TRIG | TRIG_PIN | GPIO5, cấu hình OUTPUT |
| Servo signal | SERVO_PIN | GPIO7, đầu ra LEDC |
| TB6612 AO1/AO2 | Không khai báo GPIO | Hai đầu động cơ trái |
| TB6612 BO1/BO2 | Không khai báo GPIO | Hai đầu động cơ phải |

![Hình 2. Sơ đồ nối khối theo GPIO thực tế của firmware](wiring_actual.png)

Nguồn VCC/VM và cách chuyển mức Echo không được mã hóa trong chương trình. Với module Echo mức 5 V, cần chuyển về mức phù hợp GPIO ESP32; nếu dùng HC-SR04 có thể sử dụng mạch chia áp đã được tính theo nguồn và dung sai thực tế. Các ghi chú nguồn trong sơ đồ là nguyên tắc đấu điện, không xác nhận một linh kiện bảo vệ cụ thể đã có trên mạch.

### 3.1.3. Cảm biến đầu vào

Hàm readDistanceCm() đưa TRIG xuống LOW 2 µs, lên HIGH 10 µs rồi về LOW. Độ rộng Echo được đọc bằng pulseIn(ECHO_PIN, HIGH, 30000UL). Khoảng cách được tính bằng durationUs × 0,0343 × 0,5, theo nguyên tắc đo thời gian truyền khứ hồi của siêu âm [4].

Trong code hiện tại, nếu không có Echo trong thời hạn hoặc khoảng cách tính được nhỏ hơn 2 cm/lớn hơn 400 cm, hàm trả về 400,0 cm. Giá trị này vừa đại diện cho ngoài phạm vi/mất phản hồi vừa có thể được hiểu là phía trước đang xa. Vì 400 lớn hơn ngưỡng 30 cm, loop() tiếp tục nhánh forward(). Đây là hành vi của phiên bản đang chạy; mã chưa có cờ sensor_ok để phân biệt lỗi cảm biến với đường thoáng.

Khi đo hai bên, lookAndMeasure() đưa servo tới góc yêu cầu, chờ 250 ms, lấy hai lần đo cách nhau 40 ms. Một mẫu được xét hợp lệ cho bước này khi nhỏ hơn 399 cm. Nếu cả hai hợp lệ thì lấy trung bình; nếu chỉ một hợp lệ thì dùng mẫu đó; nếu không có mẫu hợp lệ thì trả về 400 cm. Không có bộ lọc trung vị ba mẫu trong firmware hiện tại.

Thông số HC-SR04 tham chiếu khuyến nghị chu kỳ phát cách nhau trên 60 ms [4]. Bản đã thử dùng khoảng chờ 40 ms giữa hai lần đo bên, ngoài thời gian thực hiện phép đo. Việc tối ưu chu kỳ và cách phân biệt mất Echo là hướng hiệu chỉnh tiếp theo; kết quả chạy tốt của nhóm được ghi nhận cho cấu hình hiện có.

### 3.1.4. Khối chấp hành

Hai motor được điều khiển bằng LEDC 20 kHz, 8 bit. setLeftMotor() giới hạn lệnh trong [-255,255], chọn AIN1/AIN2 theo dấu và ghi độ lớn vào PWMA. setRightMotor() nhân lệnh với RIGHT_MOTOR_SIGN = −1 trước khi chọn BIN1/BIN2, giúp thống nhất ý nghĩa lệnh tiến/lùi với cách lắp và đấu dây motor phải.

@table Bảng 7. Lệnh motor và cách tạo chuyển động
| Hàm / trạng thái | PWM logic trái | PWM logic phải | Hành vi |
|---|---|---|---|
| forward() | 46 | 54 | Hai bánh chạy tiến theo quy ước đã bù chiều |
| backward() | −34 | −50 | Hai bánh chạy lùi |
| turnLeft() | 0 | 56 | Dừng bánh trái, chạy bánh phải |
| turnRight() | 42 | 0 | Chạy bánh trái, dừng bánh phải |
| stopCar() | Giảm dần về 0 | Giảm dần về 0 | Giảm PWM qua hàm ramp; STBY vẫn HIGH |

Các giá trị trong bảng là lệnh trước khi bù dấu motor phải. Ví dụ forward() yêu cầu phải +54, nhưng setRightMotor() đổi thành −54 để đưa BIN1 LOW, BIN2 HIGH và duty 54. Lệnh PWM là mức điều khiển phần mềm, không phải tốc độ đo từ encoder.

moveMotorsSlow() thay đổi PWM của mỗi bánh tối đa 2 đơn vị trong mỗi vòng, sau đó delay(20). Các bánh được cập nhật trong cùng vòng cho tới khi cả hai đạt đích. Từ 0 lên lệnh tiến 46/54 cần 27 bước, tương ứng khoảng 540 ms chờ phần mềm, chưa kể thời gian thực thi. stopCar() cũng đi qua ramp nên không phải dừng tức thời; từ mức phải 56 về 0 cần 28 bước tương tự.

Tại đích PWM = 0, chương trình đặt cả hai chân chiều của kênh xuống LOW và duty bằng 0. Không có lệnh hạ STBY trong stopCar(). Cần phân biệt trạng thái này với tắt công suất bằng STBY LOW và với phanh chủ động. Khi phân tích quãng dừng phải dựa trên chuyển động thực tế, không chỉ dựa vào tên hàm [3].

Servo dùng PWM 50 Hz, độ phân giải 14 bit. servoWriteRaw() giới hạn góc 0–180° và ánh xạ độ rộng xung theo 500 + góc × 2000/180 µs. Góc 90° tương ứng 1500 µs; 30° khoảng 833 µs; 150° khoảng 2166 µs do phép chia số nguyên. servoMoveSlow() thay đổi từng 1° và chờ 15 ms mỗi bước. Quy ước trái 150°, phải 30° là quy ước trong mã đã chạy, không đổi ngược theo bản thiết kế cũ.

Thông số nguồn của driver, motor và servo phải theo đúng linh kiện. Theo datasheet TB6612FNG, VCC và VM là hai miền nguồn khác nhau; dải hoạt động VCC 2,7–5,5 V và VM 2,5–13,5 V. Khả năng tải cần xét dòng kẹt motor và tản nhiệt của module, không sử dụng dòng đỉnh như dòng liên tục [3].

## 3.2. Lập trình hệ thống nhúng

Firmware được cung cấp sử dụng Arduino.h và esp_arduino_version.h. Chương trình chạy theo setup()/loop() cùng các hàm xử lý tuần tự. Không có máy trạng thái ARM/manual/estop hoặc task nhận lệnh mạng trong phiên bản này. Lưu đồ sau mô tả đúng thứ tự của mã đã kiểm thử [8].

![Hình 3. Lưu đồ tự động đúng theo setup loop và avoidObstacle](flowchart_actual.png)

Khi frontCm ≤ 30, avoidObstacle() giảm PWM về 0, chờ 150 ms, đo bên trái rồi bên phải, đưa servo về 90° và chờ 200 ms. Sau đó robot lùi, giữ lệnh thêm 220 ms, giảm về 0 và chờ 120 ms. Nếu leftCm ≥ rightCm thì gọi turnLeft(), ngược lại gọi turnRight(). Sau thời gian giữ rẽ 380 ms, robot giảm về 0, chờ 120 ms, đưa servo về giữa và gọi forward().

Phiên bản thực tế khác phương án ban đầu ở hai điểm: robot có bước lùi trước khi rẽ; khi rẽ chỉ một bánh chạy, không quay hai bánh ngược chiều. Code không có điều kiện cả hai bên bị chặn thì đứng yên. Ngay cả khi hai giá trị cùng nhỏ, chương trình vẫn chọn bên lớn hơn hoặc bằng; nếu cả hai cùng 400 thì chọn trái theo nhánh >=.

### 3.2.1. Thiết lập Clock cho hệ thống

Mã nguồn không gọi setCpuFrequencyMhz() hoặc tự cấu hình thạch anh, nên xung CPU phụ thuộc board và tùy chọn biên dịch. Báo cáo không gán một xung CPU cố định chỉ từ khả năng tối đa của họ chip. Các thông số thời gian được xác định rõ là tần số PWM, độ phân giải, delay và timeout.

Với Arduino-ESP32 từ phiên bản 3, mã dùng ledcAttach(pin, frequency, resolution) và ledcWrite(pin, duty). Với phiên bản nhỏ hơn 3, mã dùng ledcSetup(), ledcAttachPin() và ghi theo kênh: motor trái 0, motor phải 1, servo 2. Hai nhánh được chọn bằng ESP_ARDUINO_VERSION_MAJOR; không có căn cứ khẳng định nhóm đã thử cả hai nhánh trên mọi phiên bản core [7], [8].

@table Bảng 8. Các khoảng thời gian trong chu trình thực tế
| Công đoạn | Giá trị trong code | Cách hiểu |
|---|---|---|
| Khởi tạo servo tâm | delay(800) | Trước thông báo READY và forward() |
| Ramp motor | 20 ms / bước 2 PWM | Có thời gian tăng và giảm riêng |
| Servo quay chậm | 15 ms / bước 1° | 60° cần khoảng 900 ms chờ vòng lặp |
| Servo ổn định khi đo | 250 ms | Sau khi tới mỗi hướng trái/phải |
| Hai mẫu đo bên | Cách nhau 40 ms | Ngoài thời gian pulseIn() |
| Echo | Tối đa 30.000 µs mỗi lần | Hàm có chờ đồng bộ |
| Dừng trước quét | 150 ms | Sau khi stopCar() hoàn thành ramp |
| Về tâm sau quét | 200 ms | Sau khi servoMoveSlow(90) hoàn thành |
| Giữ lùi / rẽ | 220 / 380 ms | Sau khi đã đạt PWM đích |
| Chờ sau dừng | 120 ms | Sau lùi và sau rẽ |
| Cuối loop | 80 ms | Không làm chu kỳ loop cố định khi đang tránh |

Các giá trị REVERSE_TIME_MS và TURN_TIME_MS là thời gian giữ lệnh sau ramp, không phải tổng thời gian chuyển động lùi/rẽ. Một lượt tránh còn gồm thời gian giảm tốc, di chuyển servo và đo. Do đó không mô tả thuật toán hiện tại như vòng điều khiển 10 ms hoặc telemetry ổn định 10 Hz.

### 3.2.2. Khởi tạo cảm biến

Trong setup(), chương trình mở Serial 115200, cấu hình các chân chiều và STBY thành OUTPUT, TRIG thành OUTPUT, ECHO thành INPUT rồi khởi tạo LEDC. Tiếp theo đặt STBY HIGH, TRIG LOW và gọi stopCar(). Servo được đặt ngay ở tâm bằng servoWriteRaw(90), biến currentServoAngle được đồng bộ bằng 90, sau đó chờ 800 ms.

Sau khởi tạo, chương trình in READY và gọi forward(). Vì currentLeftPwm/currentRightPwm ban đầu bằng 0 nên stopCar() đầu tiên không phải giảm một PWM đang chạy. Firmware không yêu cầu một phép đo trước hợp lệ hoặc lệnh ARM trước lần tiến đầu tiên. Lần đọc khoảng cách đầu trong loop() diễn ra sau khi hàm forward() trong setup() hoàn thành.

Việc đọc cảm biến là đồng bộ qua pulseIn() với timeout hữu hạn. Kết quả ngoại lệ được chuẩn hóa thành 400 cm như đã mô tả. Khi phát triển thêm, có thể tách giá trị đo và cờ hợp lệ để xử lý mất phản hồi khác với vật ở xa; đây là cải tiến, không phải hành vi đang có.

### 3.2.3. Chương trình điều khiển (hàm main)

Vòng loop() đo frontCm, kiểm tra thời gian để in FRONT, so sánh ngưỡng và gọi avoidObstacle() hoặc forward(). Cuối vòng chờ 80 ms. Khi đang chạy ổn ở 46/54, gọi forward() lại không tạo thêm bước ramp vì PWM hiện tại đã bằng đích; khi quay trở lại từ trạng thái dừng thì ramp được thực hiện đầy đủ.

```text
setup:
  GPIO + LEDC; STBY HIGH; motor 0; servo 90°
  chờ 800 ms; in READY; forward(46,54) qua ramp
loop:
  front = readDistanceCm(); in FRONT nếu đã qua 500 ms
  nếu front <= 30 cm:
    stop qua ramp; chờ 150 ms
    đo trái 150°; đo phải 30°; về 90°; chờ 200 ms
    lùi(-34,-50); giữ 220 ms; stop; chờ 120 ms
    trái >= phải ? rẽ trái(0,56) : rẽ phải(42,0)
    giữ 380 ms; stop; chờ 120 ms; về tâm; forward
  ngược lại: forward
  chờ 80 ms
```

Ở cơ cấu hai bánh cách nhau b, quan hệ động học lý tưởng giữa vận tốc bánh và thân robot là:

@equation differential

Trong đó R/L biểu diễn bánh phải/trái, v là vận tốc tịnh tiến và ω là vận tốc góc. Các công thức giải thích vì sao dừng một bánh và chạy bánh còn lại tạo ra chuyển động rẽ. Firmware chưa đo vận tốc bánh hoặc góc quay, nên thời gian 380 ms không xác định một góc quay tuyệt đối. Giá trị PWM trái/phải khác nhau là cấu hình đã được nhóm chọn khi thử mô hình.

## 3.3. Lập trình App/Website

App Python/Tkinter ở bản thiết kế trước vẫn được giữ làm phần mềm máy tính của hướng mở rộng. Mã gồm main.py, gui.py, controller.py, protocol.py, transport.py và test_system.py. App có mô phỏng để kiểm tra luồng lệnh/trạng thái, xử lý serial theo hàng đợi, vẽ đồ thị và ghi CSV.

@table Bảng 9. Trạng thái của phần mềm máy tính và tích hợp
| Thành phần | Trạng thái hiện tại |
|---|---|
| Giao diện Tkinter | Đã xây dựng và kiểm tra đối tượng giao diện |
| Bộ mô phỏng | Có thể thử ARM, manual/auto, dừng và lỗi truyền thông |
| Kiểm tra tự động | 27 bài kiểm tra giao thức/logic đã đạt ở phiên bản app bàn giao |
| SerialTransport / JSON | Đã có phía app; chờ firmware gửi/nhận theo giao thức |
| ESP-NOW gateway | Chưa có mã trong firmware được cung cấp |
| Nhận lệnh ở robot | Chưa có trong setup()/loop() hiện tại |
| Điều khiển robot thật từ app | Chưa được xác nhận cho bản firmware tự hành này |

![Hình 4. Bố trí app Python dành cho phần mở rộng điều khiển](app_layout.png)

Hình 4 là sơ đồ giao diện theo mã phần mềm, không phải ảnh app đã điều khiển robot qua ESP-NOW. Khi chạy mô phỏng, dữ liệu là tổng hợp và được ghi nguồn SIMULATION. Firmware mới cung cấp chỉ xuất các dòng FRONT/SCAN, còn app hiện đọc JSON có cấu trúc; hai định dạng cần adapter hoặc thay đổi thống nhất trước khi kết nối thực.

Phương án tích hợp là bổ sung tầng nhận lệnh cho robot, chọn chế độ auto/manual và chuyển các delay dài sang bộ lập lịch không chặn. Lệnh STOP phải giảm/tắt đầu ra theo chính sách rõ ràng và được xử lý ưu tiên. Tiếp đó mới bổ sung ACK, telemetry và watchdog liên kết để app phát hiện mất phản hồi. Không đánh đồng kết quả 27 kiểm tra mô phỏng với phép thử radio hoặc kiểm thử điều khiển robot thật.

# 4. Kiểm chứng (Validation)

## 4.1. Kiểm chứng chức năng

Nhóm thực hiện đã chạy firmware trên mô hình và xác nhận các chức năng tự hành hoạt động đạt. Nội dung kiểm chứng đối chiếu mã nguồn và kết quả thử nghiệm do nhóm xác nhận. Mức xác nhận là chức năng; chưa có dữ liệu số, ảnh hoặc log gốc đính kèm để tính sai số và độ tin cậy thống kê.

@table Bảng 10. Kết quả kiểm thử chức năng trên robot
| Chức năng | Nội dung đối chiếu với code | Kết quả do nhóm xác nhận |
|---|---|---|
| Cấu hình GPIO và PWM | Các chân bảng 6, motor 20 kHz/8 bit, servo 50 Hz/14 bit | Đạt; mô hình đã chạy ổn với cấu hình này |
| Chạy tiến | forward() với PWM logic 46/54 và bù dấu motor phải | Đạt |
| Dừng và ramp | Thay đổi PWM từng bước 2, chờ 20 ms, về 0 | Đạt chức năng giảm tốc/dừng |
| Đo khoảng cách | Trigger/Echo và hiển thị FRONT | Đạt chức năng đọc/hiển thị |
| Quét servo | Tâm 90°, trái 150°, phải 30°, quay từng bước | Đạt |
| Đo hai bên | Hai mẫu mỗi hướng, lựa chọn/average theo điều kiện hợp lệ | Đạt chức năng khảo sát |
| Lùi trong chu trình tránh | PWM −34/−50, giữ lệnh sau ramp 220 ms | Đạt |
| Rẽ trái / phải | 0/56 hoặc 42/0 theo so sánh khoảng cách | Đạt |
| Tránh vật cản tự động | Trước ≤30 cm → dừng, quét, lùi, rẽ, tiến lại | Đạt trong các lần thử của nhóm |
| Serial trạng thái | READY, FRONT, OBSTACLE, SCAN và TURN | Đạt chức năng theo dõi |

Các kết quả trên không gán thêm số lần thử, thời gian phản hồi đo được hoặc tỷ lệ thành công chưa được cung cấp. Ví dụ 220 ms và 380 ms là hằng số trong code; không thể dùng trực tiếp làm thời gian lùi/rẽ đo bằng video vì còn có ramp và quán tính cơ khí.

@table Bảng 11. Phân biệt kết quả đã có và nội dung cần bổ sung
| Nội dung | Căn cứ hiện có | Kết luận / bước tiếp theo |
|---|---|---|
| Hoạt động phần cứng tự hành | Mã nguồn và xác nhận nhóm đã chạy đạt | Ghi nhận đạt về chức năng |
| Sai số siêu âm | Chưa có số đo đối chiếu thước | Có thể bổ sung MAE và tỷ lệ mẫu hợp lệ |
| Quãng dừng/góc rẽ | Có tham số phần mềm, chưa có số đo cơ khí | Không công bố giá trị đo chưa thực hiện |
| Mất Echo/ngoài dải | Đã rõ hành vi trả 400 cm trong code | Chưa có cơ chế dừng lỗi cảm biến riêng |
| Hai bên đều bị chặn | Code vẫn chọn bên lớn hơn hoặc bằng | Có thể bổ sung điều kiện đứng yên chờ |
| App mô phỏng | Có mã và log 27 bài kiểm tra đạt | Chỉ xác nhận phần mềm máy tính |
| ESP-NOW/ACK/watchdog | Chưa có trong firmware này | Thực hiện ở giai đoạn tích hợp |
| Ảnh, CSV và video | Chưa đính kèm trong lần cập nhật | Bổ sung minh chứng gốc khi hoàn thiện hồ sơ |

Để có đánh giá định lượng, có thể đo khoảng cách chuẩn ở nhiều mốc và ghi cả mẫu mất Echo; tính MAE trên các mẫu hợp lệ cùng tỷ lệ hợp lệ. Với chuyển động, đo thời gian từ phát hiện vật cản tới khi đứng yên và quãng dừng thực để hiệu chỉnh ngưỡng 30 cm. Việc bổ sung các số đo này không thay thế kết quả chức năng đã được nhóm xác nhận.

Giới hạn rút ra từ mã cần được mô tả trung thực: mất Echo được ánh xạ thành 400 cm, chưa có cảm biến phía sau cho bước lùi và chưa có điều kiện dừng khi cả hai hướng đều gần vật cản. Những giới hạn này là nội dung cải tiến, không làm thay đổi thông tin nhóm đã chạy thành công các kịch bản thử hiện có.

## 4.2. Minh chứng video

Video minh chứng nên thể hiện bật nguồn và tự chạy sau khởi tạo, log FRONT, dừng khi gặp vật cản, servo quét trái/phải, bước lùi, chọn hướng rẽ và tiến trở lại. Có thể đặt robot và Serial Monitor trong cùng khung hình để đối chiếu hành vi với các dòng SCAN/TURN.

Nhóm đã xác nhận thử nghiệm thực tế đạt; liên kết video hoặc tệp ghi hình chưa được đính kèm. Phần này để bổ sung đường dẫn minh chứng, không điền một liên kết hoặc nội dung đo giả định.

# 5. Kết luận (Conclusion)

Robot ESP32 với siêu âm trên servo, hai motor DC và TB6612FNG đã được triển khai; nhóm xác nhận các chức năng tự hành chạy đạt. GPIO, PWM, ramp và thời gian được mô tả đúng theo firmware. Robot tự tiến sau khởi tạo; khi khoảng cách trước không lớn hơn 30 cm thì dừng, quét hai bên, lùi, rẽ bằng một bánh rồi tiếp tục tiến. Kết quả được ghi nhận ở mức chức năng đã thử.

App Python đã có giao diện, mô phỏng và kiểm tra phần mềm. Firmware hiện tại chưa có ESP-NOW hoặc nhận lệnh app; giai đoạn tiếp theo là tích hợp truyền thông và điều khiển từ xa, sau đó đánh giá bằng các phép đo định lượng.

## Hướng phát triển

Ưu tiên tách lỗi cảm biến khỏi khoảng cách và xử lý trường hợp hai bên bị chặn. Có thể bổ sung cảm biến sau, encoder và đo quãng dừng để hiệu chỉnh. Khi ghép app/ESP-NOW, cần lập lịch không chặn, nhận lệnh, STOP ưu tiên, ACK, telemetry và watchdog trên cơ sở cấu hình GPIO đã chạy ổn.

# Tài liệu tham khảo

[1] Espressif Systems. ESP-NOW, ESP-IDF Programming Guide. https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/network/esp_now.html. Truy cập ngày 08/11/2026.

[2] Espressif Systems. ESP32-S3 Series Datasheet, mục chân GPIO và LED PWM. https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf. Truy cập ngày 08/11/2026. Tài liệu đối chiếu nhóm chân; tên board thương mại cần ghi theo mô hình thực tế.

[3] Toshiba Electronic Devices & Storage Corporation. TB6612FNG Datasheet. https://toshiba.semicon-storage.com/info/datasheet_en_20141001.pdf?did=10660. Truy cập ngày 08/11/2026.

[4] ELECFREAKS. Ultrasonic Ranging Module HC-SR04, tài liệu lưu trữ tại SparkFun. https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf. Truy cập ngày 08/11/2026.

[5] TowerPro. SG90 Digital. https://towerpro.com.tw/product/sg90-7/. Truy cập ngày 08/11/2026. Dùng làm tham chiếu khi module thực tế đúng loại.

[6] pySerial. API documentation. https://pyserial.readthedocs.io/en/latest/pyserial_api.html. Truy cập ngày 08/11/2026.

[7] Espressif Systems. Arduino-ESP32 LED Control (LEDC). https://docs.espressif.com/projects/arduino-esp32/en/latest/api/ledc.html. Truy cập ngày 08/11/2026.

[8] Nhóm thực hiện. Mã nguồn firmware robot tự động đã chạy thử, cung cấp ngày 08/11/2026; gồm setup(), loop(), avoidObstacle() và các hằng số GPIO/PWM. Kết quả kiểm thử chức năng do nhóm xác nhận.

# Phụ lục A. Cấu hình và đối chiếu chương trình

## A.1. Các khai báo chân đang sử dụng

```cpp
#define TB_PWMA_PIN 21
#define TB_AIN2_PIN 47
#define TB_AIN1_PIN 48
#define TB_STBY_PIN 39
#define TB_BIN1_PIN 40
#define TB_BIN2_PIN 41
#define TB_PWMB_PIN 42
#define ECHO_PIN 4
#define TRIG_PIN 5
#define SERVO_PIN 7
```

Thứ tự AIN2 trước AIN1 trong khai báo không làm thay đổi ý nghĩa chân: AIN1 là GPIO48 và AIN2 là GPIO47. Đây là điểm cần kiểm tra khi đọc bảng đấu nối hoặc chuyển dây sang board khác.

## A.2. Chạy app ở chế độ mô phỏng

Trong thư mục amr_controller, chạy lệnh dưới đây hoặc nhấp run_demo.bat trên Windows. Chế độ này kiểm tra phần mềm máy tính; dữ liệu không phải phép đo từ bản firmware tự hành hiện tại.

```text
python main.py --demo
python -m unittest -v test_system
```

Để điều khiển phần cứng cần hoàn thiện gateway/robot theo PROTOCOL.md hoặc viết adapter cho giao thức thực tế. Không coi việc nhận được các dòng FRONT qua Serial là đã nhận đúng telemetry JSON của app.

## A.3. Thông tin và minh chứng cần bổ sung vào hồ sơ

@table Bảng 12. Thông tin hoàn thiện hồ sơ báo cáo
| Nội dung | Trạng thái |
|---|---|
| Họ tên, MSSV và đóng góp | Người thực hiện tự điền |
| GPIO, PWM và trình tự thuật toán | Đã cập nhật theo firmware đã thử |
| Kết quả chức năng tự hành | Đã cập nhật đạt theo xác nhận của nhóm |
| Tên board, mã cảm biến/servo, pin và motor | Điền đúng linh kiện lắp thực tế |
| GitHub và phiên bản Arduino-ESP32 đã dùng | Bổ sung thông tin môi trường nạp |
| Ảnh và đường dẫn video | Bổ sung minh chứng gốc |
| Số liệu sai số, quãng dừng, số lần thử | Bổ sung khi thực hiện phép đo định lượng |
