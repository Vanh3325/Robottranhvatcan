"""USB serial adapter and an explicitly labelled protocol simulator."""
from __future__ import annotations

import math
import queue
import threading
import time

from protocol import decode, encode, LineFramer, ProtocolError


class SerialTransport:
    def __init__(self, port, baudrate=115200):
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError("Cài pyserial: python -m pip install -r requirements.txt") from exc
        self.port = serial.Serial(port, baudrate, timeout=0.05, write_timeout=0.15)
        self.events = queue.Queue(maxsize=2000)
        self.running = True
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self):
        framer = LineFramer()
        try:
            while self.running:
                data = self.port.read(256)
                for line in framer.feed(data):
                    try:
                        event = ("message", decode(line))
                    except ProtocolError as exc:
                        event = ("warning", str(exc))
                    self.events.put_nowait(event)
        except Exception as exc:
            if self.running:
                # Keep the error observable even if a noisy serial stream fills the queue.
                try:
                    self.events.get_nowait()
                except queue.Empty:
                    pass
                self.events.put_nowait(("error", str(exc)))

    def send(self, raw):
        if self.port.write(raw) != len(raw):
            raise OSError("Ghi serial không đủ số byte")

    def poll(self):
        events = []
        for _ in range(300):
            try:
                events.append(self.events.get_nowait())
            except queue.Empty:
                break
        return events

    def close(self):
        self.running = False
        self.thread.join(timeout=0.3)
        self.port.close()


class DemoTransport:
    """Synthetic distances/PWM; no claim of physics or hardware validation."""
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.events = []
        self.session = ""
        self.armed = self.estop = False
        self.mode = "manual"
        self.left = self.right = 0
        self.angle = 90
        self.distance = 100.0
        self.sensor_ok = True
        self.last_rx = clock()
        self.last_drive = clock()
        self.last_telemetry = 0.0
        self.drop_link = False
        self.closed = False
        self.started = clock()

    def send(self, raw):
        if self.closed:
            raise OSError("Simulator closed")
        if self.drop_link:
            return
        m = decode(raw)
        if m["t"] != "cmd":
            return
        cmd = m["cmd"]
        if cmd == "hello":
            self.session = m["s"]
            self.armed = False
            self.mode = "manual"
            self.left = self.right = 0
        if m["s"] != self.session:
            return
        self.last_rx = self.clock()
        status, reason = "ok", ""
        if cmd == "estop":
            self.estop = True
            self.armed = False
            self.left = self.right = 0
            self.mode = "manual"
        elif cmd == "stop":
            self.armed = False
            self.left = self.right = 0
            self.mode = "manual"
        elif cmd == "reset_estop":
            self.estop = False
            self.armed = False
        elif cmd == "arm":
            if self.estop or not self.sensor_ok:
                status, reason = "error", "estop_or_sensor"
            else:
                self.armed = True
        elif cmd == "mode":
            if not self.armed or self.estop:
                status, reason = "error", "not_armed"
            else:
                self.mode = m["value"]
                self.left = self.right = 0
        elif cmd == "drive":
            if not self.armed or self.estop or self.mode != "manual":
                status, reason = "error", "drive_rejected"
            else:
                self.left, self.right = m["left"], m["right"]
                self.last_drive = self.clock()
        elif cmd == "servo":
            if self.mode != "manual" or self.left or self.right:
                status, reason = "error", "servo_requires_stop"
            else:
                self.angle = m["angle"]
        ack = dict(v=1, t="ack", s=self.session, seq=m["seq"], cmd=cmd, status=status)
        if reason:
            ack["reason"] = reason
        self.events.append(("message", decode(encode(ack))))

    def poll(self):
        now = self.clock()
        if now - self.last_rx > 0.5:
            self.armed = False
            self.left = self.right = 0
            self.mode = "manual"
        self.distance = round(65 + 50 * math.sin((now - self.started) / 5), 1)
        if not self.sensor_ok:
            self.left = self.right = 0
            self.armed = False
            self.mode = "manual"
        if self.mode == "manual" and now - self.last_drive > 0.3:
            self.left = self.right = 0
        if self.armed and self.mode == "auto" and not self.estop and self.sensor_ok:
            self.angle = int(90 + 50 * math.sin(now * 2))
            self.left, self.right = ((-75, 75) if self.distance < 30 else (100, 100))
        elif self.mode == "manual" and (self.left > 0 or self.right > 0):
            if self.angle != 90 or self.distance < 30 or not self.sensor_ok:
                self.left = self.right = 0
        if not self.drop_link and self.session and now - self.last_telemetry >= 0.1:
            m = dict(v=1, t="telemetry", s=self.session, mode=self.mode,
                     armed=self.armed, estop=self.estop, sensor_ok=self.sensor_ok,
                     distance_cm=self.distance if self.sensor_ok else None,
                     servo=self.angle, left=self.left, right=self.right)
            self.events.append(("message", decode(encode(m))))
            self.last_telemetry = now
        events, self.events = self.events, []
        return events

    def close(self):
        self.closed = True


def list_ports():
    try:
        from serial.tools import list_ports as ports
        return [p.device for p in ports.comports()]
    except ImportError:
        return []
