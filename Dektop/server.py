import time
import serial
import serial.tools.list_ports

# Names of keywords to look for in port descriptions to identify Silabs CP210x devices
KEYWORDS = ("silicon", "silabs", "cp210")

# Global configuration
BAUD = 9600
READ_TIMEOUT = 10.0  # seconds to read responses after sending each command
COMMANDS = ["<PING>", "<SET_T:1000>"]  # list of commands to send, without terminators


# Find serial ports that match KEYWORDS in their description or manufacturer fields
def find_silabs_ports():
    ports = serial.tools.list_ports.comports()
    matches = []
    for p in ports:
        text = " ".join(filter(None, [p.manufacturer, p.description, p.hwid, p.product, p.name]))
        if any(k in text.lower() for k in KEYWORDS):
            matches.append(p)
    return matches


# Open all ports which match the criteria
def open_ports(ports, baud):
    opened = []
    for p in ports:
        try:
            ser = serial.Serial(p.device, baudrate=baud, timeout=1)
            print(f"Opened: {p.device} — {p.description or 'no description'}")
            opened.append((p, ser))
        except Exception as e:
            print(f"Failed to open {p.device}: {e}")
    return opened


# Send commands to each opened port and print responses for a short time after each command
def send_commands_and_print(opened_ports, commands, read_timeout=2.0):
    if not opened_ports:
        return

    for p, ser in opened_ports:
        dev = p.device
        try:
            for cmd in commands:
                data = (cmd + "\r\n").encode("utf-8")
                ser.write(data)
                ser.flush()
                print(f"Sent to {dev}: {cmd}")

                # Read responses for a short window after sending
                end_time = time.time() + read_timeout
                while time.time() < end_time:
                    line = ser.readline()
                    if line:
                        text = line.decode("utf-8")
                        text = text.strip()
                        print(f"{dev} -> {text}")
                    else:
                        # small sleep to avoid tight loop
                        time.sleep(0.05)
        except Exception as e:
            print(f"Error communicating with {dev}: {e}")


def main():
    matches = find_silabs_ports()
    if not matches:
        print("No matching devices found.")
        return

    print(f"Found {len(matches)} device(s):")
    for p in matches:
        print(f" - {p.device}: {p.description or p.hwid or 'unknown'}")

    opened = open_ports(matches, BAUD)
    commands = COMMANDS

    try:
        send_commands_and_print(opened, commands, read_timeout=READ_TIMEOUT)
    finally:
        for p, ser in opened:
            try:
                ser.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()