import json
import unittest
from controller import Controller
from protocol import encode, decode, ProtocolError, LineFramer
from transport import DemoTransport


class Clock:
    def __init__(self):
        self.time = 10.0
    def __call__(self):
        return self.time
    def advance(self, dt):
        self.time += dt


class ProtocolTests(unittest.TestCase):
    def command(self, **kwargs):
        return dict(v=1, t="cmd", s="012345abcdef", seq=1, cmd="drive", left=100, right=-100, **kwargs)

    def test_round_trip(self):
        m = self.command()
        self.assertEqual(decode(encode(m)), m)

    def test_fragmented_serial(self):
        raw = encode(self.command())
        framer = LineFramer()
        self.assertEqual(framer.feed(raw[:8]), [])
        self.assertEqual(framer.feed(raw[8:-1]), [])
        self.assertEqual(decode(framer.feed(raw[-1:])[0]), self.command())

    def test_multiple_frames_crlf(self):
        raw = encode(self.command()).replace(b"\n", b"\r\n")
        lines = LineFramer().feed(raw + raw)
        self.assertEqual(len(lines), 2)
        self.assertEqual(decode(lines[0]), self.command())

    def test_oversize_resynchronizes_at_newline(self):
        good = encode(self.command())
        lines = LineFramer().feed(b"x" * 9000 + b"\n" + good)
        self.assertEqual(len(lines), 1)
        self.assertEqual(decode(lines[0]), self.command())

    def test_rejects_out_of_range_pwm(self):
        for value in (256, -256, True, 10.5):
            m = self.command()
            m["left"] = value
            with self.assertRaises(ProtocolError):
                encode(m)

    def test_rejects_malformed_messages(self):
        for data in (b"{}", b"[]", b"bad", b'{"v":true}', b'\xff',
                     b'{"v":1,"t":"cmd","s":"012345abcdef","seq":1,"cmd":[]}'):
            with self.assertRaises(ProtocolError):
                decode(data)

    def test_rejects_nan(self):
        m = dict(v=1, t="telemetry", s="012345abcdef", mode="manual", armed=False,
                 estop=False, sensor_ok=True, left=0, right=0, servo=90, distance_cm=float("nan"))
        with self.assertRaises(ProtocolError):
            encode(m)

    def test_wire_budget(self):
        m = dict(v=1, t="telemetry", s="012345abcdef", mode="manual", armed=False,
                 estop=False, sensor_ok=True, left=-255, right=-255, servo=150, distance_cm=1000.0)
        self.assertLessEqual(len(encode(m)), 241)


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.transport = DemoTransport(self.clock)
        self.sent = []
        def send(raw):
            self.sent.append(decode(raw))
            self.transport.send(raw)
        self.core = Controller(send, clock=self.clock)
        self.core.connect()
        self.pump()

    def pump(self):
        for kind, m in self.transport.poll():
            if kind == "message":
                self.core.receive(m)

    def step(self, dt=0.1):
        self.clock.advance(dt)
        self.core.tick()
        self.pump()

    def arm(self):
        self.core.arm()
        self.pump()
        self.assertTrue(self.core.armed)

    def test_connect_is_not_arm(self):
        self.assertTrue(self.core.ready)
        self.assertFalse(self.core.armed)
        self.core.drive(100, 100)
        self.assertFalse(any(m["cmd"] == "drive" for m in self.sent))

    def test_arm_only_after_ack(self):
        self.core.arm()
        self.assertFalse(self.core.armed)
        self.pump()
        self.assertTrue(self.core.armed)

    def test_hold_and_release(self):
        self.arm()
        self.core.drive(90, 90)
        self.step()
        self.assertEqual(self.core.requested, (90, 90))
        self.core.release_drive()
        self.pump()
        self.assertEqual((self.transport.left, self.transport.right), (0, 0))

    def test_stop_disarms_and_ignores_late_arm_ack(self):
        self.core.arm()
        self.core.stop()
        self.pump()
        self.assertFalse(self.core.armed)
        self.assertEqual(self.core.mode, "manual")

    def test_estop_latches_until_explicit_reset(self):
        self.arm()
        self.core.emergency_stop()
        self.pump()
        self.core.arm()
        self.assertTrue(self.core.estop)
        self.assertFalse(self.core.armed)
        self.core.reset_estop()
        self.pump()
        self.assertFalse(self.core.estop)
        self.assertFalse(self.core.armed)

    def test_estop_cancels_pending_reset_ack(self):
        self.core.emergency_stop()
        self.pump()
        self.core.reset_estop()
        self.core.emergency_stop()
        self.pump()
        self.assertTrue(self.core.estop)

    def test_auto_blocks_manual_drive(self):
        self.arm()
        self.core.set_mode("auto")
        self.pump()
        self.assertEqual(self.core.mode, "auto")
        count = len(self.sent)
        self.core.drive(100, 100)
        self.core.servo(120)
        self.assertEqual(len(self.sent), count)

    def test_mode_transition_blocks_manual_drive_before_ack(self):
        self.arm()
        self.core.set_mode("auto")
        count = len(self.sent)
        self.core.drive(100, 100)
        self.assertEqual(len(self.sent), count)

    def test_link_loss_latches_app_fault_and_robot_watchdog(self):
        self.arm()
        self.core.drive(100, 100)
        self.pump()
        self.transport.drop_link = True
        for _ in range(12):
            self.step()
        self.assertTrue(self.core.fault)
        self.assertFalse(self.core.armed)
        self.assertFalse(self.transport.armed)
        self.assertEqual((self.transport.left, self.transport.right), (0, 0))
        self.transport.drop_link = False
        self.step()
        self.assertFalse(self.core.ready)  # never auto-rearm after RF returns

    def test_telemetry_timeout_even_when_ack_works(self):
        self.arm()
        self.clock.advance(1.1)
        self.core.tick()
        self.assertIn("telemetry", self.core.fault)

    def test_wrong_session_ack_ignored(self):
        self.core.arm()
        ack = dict(v=1, t="ack", s="ffffffffffff", seq=self.core.seq, cmd="arm", status="ok")
        self.core.receive(ack)
        self.assertFalse(self.core.armed)

    def test_wrong_command_ack_ignored(self):
        self.core.arm()
        self.core.receive(dict(v=1, t="ack", s=self.core.session, seq=self.core.seq,
                               cmd="heartbeat", status="ok"))
        self.assertFalse(self.core.armed)

    def test_reconnect_uses_new_session(self):
        old = self.core.session
        self.core.disconnect()
        self.core.connect()
        self.pump()
        self.assertNotEqual(old, self.core.session)
        self.assertFalse(self.core.armed)

    def test_serial_write_error_disables_control(self):
        self.arm()
        def failed(raw):
            raise OSError("USB removed")
        self.core.send_bytes = failed
        self.core.drive(100, 100)
        self.assertTrue(self.core.fault)
        self.assertFalse(self.core.armed)

    def test_disconnect_sends_stop(self):
        self.arm()
        self.core.disconnect()
        self.assertEqual(self.sent[-1]["cmd"], "stop")
        self.assertFalse(self.core.connected)

    def test_bad_sensor_in_simulator_stops_motors(self):
        self.arm()
        self.core.drive(100, 100)
        self.transport.sensor_ok = False
        self.pump()
        self.assertEqual((self.transport.left, self.transport.right), (0, 0))

    def test_drive_lease_expires_while_heartbeat_continues(self):
        self.arm()
        self.core.drive(100, 100)
        self.pump()
        self.clock.advance(0.35)
        self.core._command("heartbeat")
        self.pump()
        self.assertTrue(self.transport.armed)
        self.assertEqual((self.transport.left, self.transport.right), (0, 0))

    def test_invalid_sensor_prevents_arm(self):
        self.transport.sensor_ok = False
        self.clock.advance(.11)
        self.pump()
        count = len(self.sent)
        self.core.arm()
        self.assertEqual(len(self.sent), count)
        self.assertFalse(self.core.armed)

    def test_sensor_fault_telemetry_requests_stop(self):
        self.arm()
        m = dict(self.core.telemetry)
        m.update(sensor_ok=False, distance_cm=None, armed=True)
        self.core.receive(m)
        self.assertFalse(self.core.armed)
        self.assertEqual(self.sent[-1]["cmd"], "stop")


if __name__ == "__main__":
    unittest.main(verbosity=2)
