"""Proposed AMR protocol v1. Firmware must implement this contract."""
from __future__ import annotations

import json
import math
import re

MAX_FRAME = 240  # excluding LF; fits in a 250-byte ESP-NOW v1 payload
COMMANDS = {"hello", "arm", "drive", "mode", "servo", "stop", "estop",
            "reset_estop", "heartbeat"}
SESSION = re.compile(r"[0-9a-f]{12}\Z")


class ProtocolError(ValueError):
    pass


def integer(value, low, high):
    return type(value) is int and low <= value <= high


def validate(m: dict) -> dict:
    if not isinstance(m, dict) or type(m.get("v")) is not int or m["v"] != 1:
        raise ProtocolError("Expected protocol version 1")
    if not isinstance(m.get("s"), str) or not SESSION.fullmatch(m["s"]):
        raise ProtocolError("Invalid session")
    kind = m.get("t")
    if kind in ("cmd", "ack"):
        if (not integer(m.get("seq"), 0, 2147483647)
                or not isinstance(m.get("cmd"), str) or m["cmd"] not in COMMANDS):
            raise ProtocolError("Invalid sequence or command")
        if kind == "ack":
            if m.get("status") not in ("ok", "error"):
                raise ProtocolError("Invalid ACK status")
            if "reason" in m and (not isinstance(m["reason"], str) or len(m["reason"]) > 64):
                raise ProtocolError("Invalid ACK reason")
        elif m["cmd"] == "drive":
            if not all(integer(m.get(k), -255, 255) for k in ("left", "right")):
                raise ProtocolError("Motor PWM must be in [-255,255]")
        elif m["cmd"] == "mode" and m.get("value") not in ("manual", "auto"):
            raise ProtocolError("Invalid mode")
        elif m["cmd"] == "servo" and not integer(m.get("angle"), 30, 150):
            raise ProtocolError("Servo angle must be in [30,150]")
    elif kind == "telemetry":
        if m.get("mode") not in ("manual", "auto"):
            raise ProtocolError("Invalid telemetry mode")
        if not all(type(m.get(k)) is bool for k in ("armed", "estop", "sensor_ok")):
            raise ProtocolError("Invalid telemetry flags")
        if not all(integer(m.get(k), -255, 255) for k in ("left", "right")):
            raise ProtocolError("Invalid telemetry PWM")
        if not integer(m.get("servo"), 30, 150):
            raise ProtocolError("Invalid telemetry angle")
        distance = m.get("distance_cm")
        if distance is not None and (type(distance) not in (int, float)
                or not math.isfinite(distance) or not 0 <= distance <= 1000):
            raise ProtocolError("Invalid distance")
        if m["sensor_ok"] and distance is None:
            raise ProtocolError("Valid sensor needs a distance")
    else:
        raise ProtocolError("Unknown message type")
    return m


def encode(message: dict) -> bytes:
    validate(message)
    try:
        raw = json.dumps(message, ensure_ascii=True, separators=(",", ":"),
                         allow_nan=False).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise ProtocolError(str(exc)) from exc
    if len(raw) > MAX_FRAME:
        raise ProtocolError("Frame exceeds 240 bytes")
    return raw + b"\n"


def decode(raw: bytes) -> dict:
    if raw.endswith(b"\n"):
        raw = raw[:-1]
    if raw.endswith(b"\r"):
        raw = raw[:-1]
    if len(raw) > MAX_FRAME:
        raise ProtocolError("Frame exceeds 240 bytes")
    try:
        message = json.loads(raw.decode("ascii"),
                             parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
    except (UnicodeError, ValueError) as exc:
        raise ProtocolError("Invalid JSON/ASCII frame") from exc
    return validate(message)


class LineFramer:
    """Preserve fragments across serial timeouts; discard oversized lines in full."""
    def __init__(self):
        self.buffer = bytearray()
        self.dropping = False

    def feed(self, data: bytes):
        lines = []
        for byte in data:
            if byte == 10:
                if self.buffer and not self.dropping:
                    lines.append(bytes(self.buffer))
                self.buffer.clear()
                self.dropping = False
            elif not self.dropping:
                self.buffer.append(byte)
                if len(self.buffer) > MAX_FRAME + 1:  # allow CRLF
                    self.buffer.clear()
                    self.dropping = True
        return lines
