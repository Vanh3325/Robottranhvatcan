"""Vietnamese Tkinter operator panel. Motor control stays disabled until ACK."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from controller import Controller
from transport import DemoTransport, SerialTransport, list_ports


class App:
    def __init__(self, root, demo=False):
        self.root = root
        self.root.title("AMR Control | ESP32 · ESP-NOW")
        self.root.geometry("1120x900")
        self.root.minsize(1000, 860)
        self.root.configure(bg="#eef3f8")
        self.transport = None
        self.controller = Controller(self._send, log=self.log)
        self.rows = []
        self.csv_file = self.csv_writer = None
        self.press_key = None
        self.pending_release = None
        self.last_warning = ""
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind_all("<KeyPress>", self.key_down)
        self.root.bind_all("<KeyRelease>", self.key_up)
        self.root.bind("<FocusOut>", self.focus_out)
        self.log("Sẵn sàng. Chọn Mô phỏng hoặc cổng COM của ESP32 gateway.")
        if demo:
            self.root.after(150, self.connect)
        self.root.after(40, self.tick)

    def _build(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#eef3f8")
        style.configure("TLabelframe", background="#eef3f8")
        style.configure("TLabelframe.Label", font=("Segoe UI", 11, "bold"), background="#eef3f8")
        style.configure("TLabel", background="#eef3f8", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        style.configure("Accent.TButton", background="#126b89", foreground="white")
        style.configure("Danger.TButton", background="#b7283e", foreground="white", font=("Segoe UI", 12, "bold"))
        top = tk.Frame(self.root, bg="#12324c", padx=24, pady=18)
        top.pack(fill="x")
        tk.Label(top, text="AMR / CONTROL STATION", bg="#12324c", fg="white",
                 font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(top, text="ESP32  •  TB6612  •  Siêu âm quét servo  •  ESP-NOW qua USB gateway",
                 bg="#12324c", fg="#bedae7", font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 0))
        connection = ttk.Frame(self.root, padding=(20, 12))
        connection.pack(fill="x")
        self.port = tk.StringVar(value="Mô phỏng")
        self.port_box = ttk.Combobox(connection, textvariable=self.port, width=18,
                                     values=["Mô phỏng"] + list_ports())
        self.port_box.pack(side="left", padx=(0, 8))
        self.refresh_button = ttk.Button(connection, text="Làm mới", command=self.refresh)
        self.refresh_button.pack(side="left", padx=(0, 8))
        self.connect_button = ttk.Button(connection, text="Kết nối", style="Accent.TButton", command=self.toggle_connection)
        self.connect_button.pack(side="left")
        self.status = tk.StringVar(value="CHƯA KẾT NỐI")
        ttk.Label(connection, textvariable=self.status, font=("Segoe UI", 11, "bold")).pack(side="left", padx=18)
        main = ttk.Frame(self.root, padding=(20, 0, 20, 10))
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=4)
        main.columnconfigure(1, weight=5)
        main.rowconfigure(0, weight=1)
        controls = ttk.LabelFrame(main, text="Điều khiển", padding=14)
        controls.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        data = ttk.LabelFrame(main, text="Trạng thái robot", padding=14)
        data.grid(row=0, column=1, sticky="nsew")
        self.arm_button = ttk.Button(controls, text="Cho phép chạy (ARM)", command=self.controller.arm, style="Accent.TButton")
        self.arm_button.pack(fill="x")
        self.mode_buttons = []
        modes = ttk.Frame(controls)
        modes.pack(fill="x", pady=8)
        for text, mode in [("Thủ công", "manual"), ("Tự tránh vật cản", "auto")]:
            b = ttk.Button(modes, text=text, command=lambda m=mode: self.controller.set_mode(m))
            b.pack(side="left", expand=True, fill="x", padx=2)
            self.mode_buttons.append(b)
        self.speed = tk.IntVar(value=110)
        self.speed_text = tk.StringVar(value="PWM yêu cầu: 110 / 255")
        ttk.Label(controls, textvariable=self.speed_text).pack(anchor="w")
        self.speed_scale = tk.Scale(controls, from_=0, to=255, orient="horizontal", variable=self.speed,
                                   bg="#eef3f8", highlightthickness=0, command=self.speed_changed)
        self.speed_scale.pack(fill="x")
        pad = ttk.Frame(controls)
        pad.pack(pady=5)
        self.drive_buttons = []
        for text, direction, row, col in [("↑  W", "up", 0, 1), ("←  A", "left", 1, 0),
                                           ("↓  S", "down", 1, 1), ("D  →", "right", 1, 2)]:
            b = ttk.Button(pad, text=text, width=8, takefocus=False)
            b.grid(row=row, column=col, padx=3, pady=3)
            b.bind("<ButtonPress-1>", lambda e, d=direction: self.start_drive(d))
            b.bind("<ButtonRelease-1>", lambda e: self.release())
            self.drive_buttons.append(b)
        ttk.Label(controls, text="Giữ phím/nút để chạy; thả để dừng bánh.").pack(pady=3)
        self.stop_button = ttk.Button(controls, text="DỪNG & hủy ARM  [Space]", command=self.stop)
        self.stop_button.pack(fill="x", pady=(5, 5))
        ttk.Button(controls, text="DỪNG KHẨN PHẦN MỀM  [Esc]", style="Danger.TButton",
                   command=self.estop).pack(fill="x", pady=3)
        self.reset_button = ttk.Button(controls, text="Xóa chốt dừng khẩn", command=self.controller.reset_estop)
        self.reset_button.pack(fill="x", pady=3)
        scan = ttk.Frame(controls)
        scan.pack(fill="x", pady=(8, 0))
        self.angle = tk.IntVar(value=90)
        ttk.Label(scan, text="Servo (30–150°):").pack(side="left")
        self.angle_spin = ttk.Spinbox(scan, from_=30, to=150, textvariable=self.angle, width=5)
        self.angle_spin.pack(side="left", padx=6)
        self.servo_button = ttk.Button(scan, text="Gửi góc", command=self.send_servo)
        self.servo_button.pack(side="left")
        self.telemetry_text = tk.StringVar(value="Chưa có dữ liệu robot")
        ttk.Label(data, textvariable=self.telemetry_text, font=("Segoe UI", 11),
                   justify="left").pack(anchor="w", pady=(0, 8))
        self.canvas = tk.Canvas(data, bg="white", height=170, highlightthickness=0)
        self.canvas.pack(fill="x", pady=5)
        ttk.Label(data, text="Lịch sử khoảng cách (cm) • dữ liệu nhận được", font=("Segoe UI", 9)).pack(anchor="w")
        self.csv_button = ttk.Button(data, text="Bắt đầu ghi CSV…", command=self.toggle_csv)
        self.csv_button.pack(fill="x", pady=8)
        self.demo_box = ttk.LabelFrame(data, text="Chỉ mô phỏng: kiểm tra lỗi", padding=6)
        self.demo_box.pack(fill="x")
        self.drop_var = tk.BooleanVar()
        self.sensor_var = tk.BooleanVar()
        ttk.Checkbutton(self.demo_box, text="Ngắt đường truyền", variable=self.drop_var,
                         command=self.demo_fault).pack(anchor="w")
        ttk.Checkbutton(self.demo_box, text="Cảm biến không hợp lệ", variable=self.sensor_var,
                         command=self.demo_fault).pack(anchor="w")
        logs = ttk.LabelFrame(self.root, text="Nhật ký", padding=6)
        logs.pack(fill="x", padx=20, pady=(0, 8))
        self.log_text = tk.Text(logs, height=5, bg="#153249", fg="#d8eaf4", relief="flat",
                                 font=("Consolas", 9), state="disabled", wrap="word")
        self.log_text.pack(fill="x")
        ttk.Label(self.root, text="Mô phỏng dùng dữ liệu giả lập. Chế độ COM cần firmware gateway/robot theo PROTOCOL.md.",
                   foreground="#4d6577", font=("Segoe UI", 9)).pack(pady=(0, 8))

    def log(self, text):
        if not hasattr(self, "log_text"):
            return
        self.log_text.configure(state="normal")
        self.log_text.insert("end", datetime.now().strftime("%H:%M:%S ") + text + "\n")
        if int(self.log_text.index("end-1c").split(".")[0]) > 200:
            self.log_text.delete("1.0", "50.0")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def refresh(self):
        self.port_box["values"] = ["Mô phỏng"] + list_ports()

    def _send(self, raw):
        if self.transport:
            self.transport.send(raw)

    def toggle_connection(self):
        self.disconnect() if self.transport else self.connect()

    def connect(self):
        if self.transport:
            return
        try:
            port = self.port.get().strip()
            self.transport = DemoTransport() if port == "Mô phỏng" else SerialTransport(port)
            self.rows.clear()
            self.drop_var.set(False)
            self.sensor_var.set(False)
            self.controller.connect()
            self.log("MÔ PHỎNG: dữ liệu tổng hợp." if isinstance(self.transport, DemoTransport)
                     else f"Mở {port} @115200. Chờ ACK hello và telemetry từ robot.")
        except Exception as exc:
            if self.transport:
                self.transport.close()
            self.transport = None
            self.controller.disconnect()
            messagebox.showerror("Không kết nối được", str(exc))

    def disconnect(self):
        self.release()
        self.controller.disconnect()
        if self.transport:
            self.transport.close()
        self.transport = None
        self.log("Đã ngắt kết nối. Watchdog trên robot phải tự dừng nếu mất lệnh.")

    def start_drive(self, direction):
        if not (self.controller.can_control() and self.controller.armed and self.controller.mode == "manual"):
            return
        self.press_key = direction
        p = self.speed.get()
        pair = {"up": (p, p), "down": (-p, -p), "left": (-p, p), "right": (p, -p)}[direction]
        self.controller.drive(*pair)

    def release(self):
        self.press_key = None
        self.controller.release_drive()

    def speed_changed(self, value):
        self.speed_text.set(f"PWM yêu cầu: {self.speed.get()} / 255")
        if self.press_key:
            self.start_drive(self.press_key)

    def stop(self):
        self.release()
        self.controller.stop()

    def estop(self):
        self.release()
        self.controller.emergency_stop()

    def key_down(self, event):
        if event.keysym == "Escape":
            self.estop()
            return "break"
        if isinstance(event.widget, (ttk.Entry, ttk.Combobox, ttk.Spinbox, tk.Entry, tk.Text)):
            return
        if event.keysym == "space":
            self.stop()
            return "break"
        mapping = {"w": "up", "Up": "up", "s": "down", "Down": "down",
                   "a": "left", "Left": "left", "d": "right", "Right": "right"}
        direction = mapping.get(event.keysym)
        if direction:
            if self.pending_release:
                self.root.after_cancel(self.pending_release)
                self.pending_release = None
            if self.press_key != direction:
                self.start_drive(direction)
            return "break"

    def key_up(self, event):
        mapping = {"w": "up", "Up": "up", "s": "down", "Down": "down",
                   "a": "left", "Left": "left", "d": "right", "Right": "right"}
        if mapping.get(event.keysym) == self.press_key:
            if self.pending_release:
                self.root.after_cancel(self.pending_release)
            self.pending_release = self.root.after(45, self.finish_release)

    def finish_release(self):
        self.pending_release = None
        self.release()

    def focus_out(self, event):
        # Internal focus changes must not stop the robot; leaving the app must.
        self.root.after(60, self.check_focus)

    def check_focus(self):
        # Ttk combobox popdowns are Tcl widgets without Python widget objects.
        # Reading the raw focus path avoids Tkinter's _nametowidget KeyError.
        try:
            focus_path = str(self.root.tk.call("focus", "-displayof", self.root._w))
        except tk.TclError:
            return
        if not focus_path and (self.controller.armed or self.press_key):
            self.stop()
            self.log("Mất focus cửa sổ: đã gửi STOP và hủy ARM.")

    def send_servo(self):
        try:
            angle = self.angle.get()
            if not 30 <= angle <= 150:
                raise ValueError()
            self.controller.servo(angle)
        except (ValueError, tk.TclError):
            messagebox.showerror("Góc servo", "Nhập góc nguyên từ 30 đến 150 độ.")

    def demo_fault(self):
        if isinstance(self.transport, DemoTransport):
            self.transport.drop_link = self.drop_var.get()
            self.transport.sensor_ok = not self.sensor_var.get()

    def toggle_csv(self):
        self.stop()
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = self.csv_writer = None
            self.csv_button.configure(text="Bắt đầu ghi CSV…")
            self.log("Đã lưu nhật ký CSV.")
            return
        name = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                           initialfile="amr_telemetry.csv")
        if name:
            try:
                self.csv_file = open(name, "w", newline="", encoding="utf-8-sig")
                self.csv_writer = csv.writer(self.csv_file)
                self.csv_writer.writerow(["timestamp", "source", "session", "mode", "armed", "estop",
                                          "sensor_ok", "distance_cm", "servo_deg", "left_pwm", "right_pwm"])
                self.csv_button.configure(text="Dừng ghi CSV")
            except OSError as exc:
                messagebox.showerror("Không ghi được CSV", str(exc))

    def draw_chart(self):
        c = self.canvas
        c.delete("all")
        w, h = max(c.winfo_width(), 300), c.winfo_height()
        for y, label in [(20, "150"), (h // 2, "75"), (h - 20, "0")]:
            c.create_line(35, y, w - 10, y, fill="#e3ebf0")
            c.create_text(17, y, text=label, fill="#748b9b", font=("Segoe UI", 8))
        points = []
        for i, value in enumerate(self.rows[-120:]):
            if value is None:
                if len(points) >= 4:
                    c.create_line(*points, fill="#1387a0", width=2)
                points = []
            else:
                points.extend((35 + i * (w - 50) / 119, h - 20 - min(value, 150) / 150 * (h - 40)))
        if len(points) >= 4:
            c.create_line(*points, fill="#1387a0", width=2)

    def tick(self):
        if self.transport:
            try:
                for kind, value in self.transport.poll():
                    if kind == "message":
                        self.controller.receive(value)
                        if value["t"] == "telemetry" and value["s"] == self.controller.session:
                            self.rows.append(value["distance_cm"] if value["sensor_ok"] else None)
                            self.rows = self.rows[-120:]
                            if self.csv_writer:
                                self.csv_writer.writerow([datetime.now().isoformat(timespec="milliseconds"),
                                    "SIMULATION" if isinstance(self.transport, DemoTransport) else "SERIAL",
                                    value["s"], value["mode"], value["armed"], value["estop"],
                                    value["sensor_ok"], value["distance_cm"], value["servo"], value["left"], value["right"]])
                                self.csv_file.flush()
                    elif kind == "error":
                        self.controller.transport_error("Lỗi serial: " + value)
                    elif value != self.last_warning:
                        self.log("Bỏ qua gói lỗi: " + value)
                        self.last_warning = value
                self.controller.tick()
            except Exception as exc:
                self.controller.transport_error(str(exc))
        self.render()
        self.root.after(40, self.tick)

    def render(self):
        c = self.controller
        demo = isinstance(self.transport, DemoTransport)
        prefix = "MÔ PHỎNG | " if demo else "COM | "
        if not self.transport:
            status = "CHƯA KẾT NỐI"
        elif c.fault:
            status = prefix + "LỖI — KẾT NỐI LẠI"
        elif not c.ready:
            status = prefix + "CHỜ ACK ROBOT"
        elif c.estop:
            status = prefix + "ĐÃ CHỐT DỪNG KHẨN"
        else:
            status = prefix + ("ĐÃ ARM" if c.armed else "SẴN SÀNG / CHƯA ARM")
        self.status.set(status)
        self.connect_button.configure(text="Ngắt kết nối" if self.transport else "Kết nối")
        self.port_box.configure(state="disabled" if self.transport else "normal")
        self.refresh_button.configure(state="disabled" if self.transport else "normal")
        enabled = c.can_control()
        self.arm_button.configure(state="normal" if enabled and not c.armed and c.telemetry and c.telemetry["sensor_ok"] else "disabled")
        for b in self.drive_buttons:
            b.configure(state="normal" if enabled and c.armed and c.mode == "manual" else "disabled")
        for b in self.mode_buttons:
            b.configure(state="normal" if enabled and c.armed else "disabled")
        self.servo_button.configure(state="normal" if enabled and c.mode == "manual" and c.requested == (0, 0) else "disabled")
        self.reset_button.configure(state="normal" if c.ready and c.estop and not c.fault else "disabled")
        for child in self.demo_box.winfo_children():
            child.configure(state="normal" if demo else "disabled")
        t = c.telemetry
        if t:
            distance = f"{t['distance_cm']:.1f} cm" if t["sensor_ok"] else "KHÔNG HỢP LỆ"
            age = c.clock() - c.last_telemetry
            self.telemetry_text.set(f"Chế độ robot: {t['mode'].upper()}  |  ARM: {'Có' if t['armed'] else 'Không'}\n"
                f"Khoảng cách: {distance}  |  Servo: {t['servo']}°\n"
                f"PWM phản hồi: Trái {t['left']}  ·  Phải {t['right']}\n"
                f"Tuổi dữ liệu: {age:.2f} s" + (" — CŨ" if age > 1 else ""))
        else:
            self.telemetry_text.set("Chưa có dữ liệu robot")
        self.draw_chart()

    def close(self):
        self.disconnect()
        if self.csv_file:
            self.csv_file.close()
        self.root.destroy()
