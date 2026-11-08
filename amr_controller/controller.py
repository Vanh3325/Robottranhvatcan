"""Headless control state machine, shared by UI and tests."""
from __future__ import annotations

import time
import uuid
from protocol import encode


class Controller:
    ACK_TIMEOUT = 0.65
    TELEMETRY_TIMEOUT = 1.0
    HEARTBEAT = 0.10
    DRIVE_INTERVAL = 0.10

    def __init__(self, send, clock=time.monotonic, log=lambda text: None):
        self.send_bytes, self.clock, self.log = send, clock, log
        self.connected = self.ready = self.armed = self.estop = False
        self.mode = "manual"
        self.session = ""
        self.seq = 0
        self.pending = {}
        self.telemetry = None
        self.last_telemetry = None
        self.last_heartbeat = self.last_drive = 0.0
        self.requested = (0, 0)
        self.fault = ""

    def connect(self):
        self.session = uuid.uuid4().hex[:12]
        self.seq = 0
        self.connected, self.ready, self.armed = True, False, False
        self.estop, self.mode = False, "manual"
        self.telemetry, self.last_telemetry = None, None
        self.pending.clear()
        self.requested = (0, 0)
        self.fault = ""
        self.last_heartbeat = self.clock()
        self._command("hello")

    def _command(self, cmd, **fields):
        if not self.connected:
            return
        self.seq += 1
        message = dict(v=1, t="cmd", s=self.session, seq=self.seq, cmd=cmd, **fields)
        try:
            self.send_bytes(encode(message))
        except Exception as exc:
            self._fault(f"Lỗi truyền: {exc}", transmit=False)
            return
        self.pending[self.seq] = (self.clock(), cmd, fields)

    def _fault(self, reason, transmit=True):
        if self.fault:
            return
        self.fault = reason
        self.log(reason)
        self.armed, self.ready, self.mode = False, False, "manual"
        self.requested = (0, 0)
        self.pending.clear()
        if transmit and self.connected:
            self._command("estop")
        self.estop = True

    def transport_error(self, reason):
        self._fault(reason, transmit=False)

    def disconnect(self):
        if self.connected:
            self._command("stop")
        self.connected = self.ready = self.armed = False
        self.requested = (0, 0)
        self.pending.clear()

    def receive(self, m):
        if not self.connected or m["s"] != self.session:
            return
        now = self.clock()
        if m["t"] == "ack":
            item = self.pending.get(m["seq"])
            if not item or item[1] != m["cmd"]:
                return
            self.pending.pop(m["seq"])
            if self.fault:
                return
            if m["status"] != "ok":
                self._fault("Robot từ chối: " + m.get("reason", m["cmd"]))
                return
            cmd = m["cmd"]
            if cmd == "hello":
                self.ready = True
                self.last_telemetry = now  # grace period for first telemetry
            elif cmd == "arm":
                self.armed = True
            elif cmd == "mode":
                self.mode = item[2]["value"]
            elif cmd == "reset_estop":
                self.estop = False
                self.armed = False
            if cmd not in ("drive", "heartbeat", "servo"):
                self.log(f"Robot xác nhận: {cmd} ({(now-item[0])*1000:.0f} ms)")
        elif m["t"] == "telemetry":
            self.last_telemetry, self.telemetry = now, m
            if m["estop"]:
                self.estop, self.armed = True, False
                self.requested = (0, 0)
            elif not m["sensor_ok"]:
                if self.armed or self.requested != (0, 0):
                    self.stop()
                    self.log("Cảm biến không hợp lệ: đã gửi STOP và hủy ARM.")
            elif not m["armed"]:
                self.armed = False
                self.requested = (0, 0)

    def can_control(self):
        return self.connected and self.ready and not self.fault and not self.estop

    def arm(self):
        if (self.can_control() and self.telemetry and self.telemetry["sensor_ok"]
                and self.last_telemetry is not None
                and self.clock() - self.last_telemetry <= self.TELEMETRY_TIMEOUT and not self.armed):
            if not any(c == "arm" for _, c, _ in self.pending.values()):
                self._command("arm")

    def drive(self, left, right):
        if self.can_control() and self.armed and self.mode == "manual":
            if any(c == "mode" for _, c, _ in self.pending.values()):
                return
            self.requested = (int(left), int(right))
            self._command("drive", left=int(left), right=int(right))
            self.last_drive = self.clock()

    def release_drive(self):
        if self.requested != (0, 0):
            self.requested = (0, 0)
            if self.can_control():
                self._command("drive", left=0, right=0)

    def stop(self):
        self.requested = (0, 0)
        self.armed, self.mode = False, "manual"
        # Ignore late arm/mode ACKs after stop.
        self.pending = {s: p for s, p in self.pending.items()
                        if p[1] not in ("arm", "mode", "drive", "reset_estop")}
        if self.connected:
            self._command("stop")

    def emergency_stop(self):
        self.stop()
        self.estop = True
        if self.connected:
            self._command("estop")

    def reset_estop(self):
        if self.ready and not self.fault and self.estop:
            self._command("reset_estop")

    def set_mode(self, mode):
        if self.can_control() and self.armed:
            if not any(c == "mode" for _, c, _ in self.pending.values()):
                self.release_drive()
                self._command("mode", value=mode)

    def servo(self, angle):
        if (self.can_control() and self.mode == "manual" and self.requested == (0, 0)
                and not any(c == "mode" for _, c, _ in self.pending.values())):
            self._command("servo", angle=int(angle))

    def tick(self):
        if not self.connected or self.fault:
            return
        now = self.clock()
        for sent, cmd, _ in list(self.pending.values()):
            timeout = 3.0 if cmd == "hello" else self.ACK_TIMEOUT
            if now - sent > timeout:
                self._fault(f"Mất ACK cho {cmd}; cần kết nối lại")
                return
        if self.ready:
            if self.last_telemetry is None or now - self.last_telemetry > self.TELEMETRY_TIMEOUT:
                self._fault("Mất telemetry; cần kết nối lại")
                return
            if now - self.last_heartbeat >= self.HEARTBEAT:
                self._command("heartbeat")
                self.last_heartbeat = now
            if self.requested != (0, 0) and now - self.last_drive >= self.DRIVE_INTERVAL:
                self.drive(*self.requested)
