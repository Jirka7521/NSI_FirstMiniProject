import os
import sys
import time
import unittest
from unittest import mock

# Ensure the local Dektop folder is on sys.path so `import server` works
HERE = os.path.dirname(__file__)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import server


class MockPort:
    def __init__(self, device):
        self.device = device
        self.manufacturer = "Silabs"
        self.description = "CP210x USB to UART Bridge"
        self.hwid = "HWID"
        self.product = "CP210x"
        self.name = device


class MockSerial:
    def __init__(self, device, baudrate=None, timeout=None):
        self.device = device
        self.baudrate = baudrate
        self.timeout = timeout
        self._responses = []
        self.written = []
        self.closed = False

    def write(self, data):
        self.written.append(data)
        try:
            s = data.decode('utf-8')
        except Exception:
            s = ''
        # Prepare a response depending on the command written
        if "<SET_RGB:" in s:
            # emulate device acknowledging color set
            self._responses.append(b"<RGB_OK>\n")
        elif "<PING>" in s:
            self._responses.append(b"<PONG>\n")
        elif "<SET_T:1000>" in s:
            # Return a temperature that maps to red
            self._responses.append(b"<DATA:30>\n")
        else:
            self._responses.append(b"")

    def flush(self):
        pass

    def readline(self):
        if self._responses:
            return self._responses.pop(0)
        time.sleep(0.01)
        return b""

    def close(self):
        self.closed = True


class ServerTest(unittest.TestCase):
    @mock.patch('serial.tools.list_ports.comports')
    @mock.patch('serial.Serial')
    def test_startup_and_sequence(self, mock_serial_class, mock_comports):
        # Mock found ports
        mock_comports.return_value = [MockPort('COM3')]

        created = {}

        def _new_serial(device, baudrate=None, timeout=None):
            inst = MockSerial(device, baudrate, timeout)
            created['inst'] = inst
            return inst

        mock_serial_class.side_effect = _new_serial

        # Run main which should call startup test, ping and set sequence
        server.main()

        inst = created.get('inst')
        self.assertIsNotNone(inst, "Serial instance was not created")

        written_texts = [w.decode('utf-8') for w in inst.written]

        # Verify startup color sequence sent (we expect SET_RGB commands)
        self.assertTrue(any("<SET_RGB:" in s for s in written_texts),
                f"Expected <SET_RGB: in writes: {written_texts}")

        # Verify ping and set commands sent later
        self.assertTrue(any("<PING>" in s for s in written_texts), f"PING missing: {written_texts}")
        self.assertTrue(any("<SET_T:1000>" in s for s in written_texts), f"SET_T missing: {written_texts}")

        # Also verify color mapping for returned temperature
        color = server.compute_color_from_temp(30.0)
        self.assertEqual(color, [255, 0, 0])


if __name__ == '__main__':
    unittest.main()
