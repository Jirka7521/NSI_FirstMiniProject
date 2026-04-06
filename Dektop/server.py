import time
import re
import serial
import serial.tools.list_ports

# Names of keywords to look for in port descriptions to identify Silabs CP210x devices
KEYWORDS = ("silicon", "silabs", "cp210")

# Global configuration
BAUD = 9600
READ_TIMEOUT = 10.0  # seconds to read responses after sending each command
COMMANDS = ["<PING>", "<SET_T:1000>"]  # list of commands to send, without terminators
# Sequence of RGB colors for startup test (kept for 2 seconds each)
STARTUP_COLOR_SEQUENCE = [
    [0, 0, 255],   # blue
    [0, 255, 255], # azure
    [0, 255, 0],   # green
    [255, 255, 0], # yellow
    [255, 0, 0],   # red
]
STARTUP_HOLD_SECS = 2.0


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
            # first perform a startup LED color sequence, then normal sequence
            perform_startup_color_sequence(ser)
            send_initial_command(ser)
            color = process_temperature(ser)
            if color is not None:
                print(f"Device {dev} color: {color}")
        except Exception as e:
            print(f"Error communicating with {dev}: {e}")

def read_response(ser):
    end_time = time.time() + READ_TIMEOUT
    while time.time() < end_time:
        line = ser.readline()
        if line:
            try:
                text = line.decode("utf-8")
            except UnicodeDecodeError:
                # Fall back to latin-1 which maps bytes directly to unicode codepoints
                text = line.decode("latin-1", errors="replace")
            except Exception:
                text = repr(line)
            return text.strip()
    return None

def send_initial_command(ser):
    try:
        data = (COMMANDS[0] + "\n").encode("utf-8")
        ser.write(data)
        ser.flush()
        print(f"Sent: {COMMANDS[0]}")
        print(read_response(ser))
    except Exception as e:
        print(f"Error sending initial command: {e}")
    
def perform_startup_color_sequence(ser):
    """Send a sequence of RGB set commands to the device, holding each for STARTUP_HOLD_SECS."""
    try:
        for rgb in STARTUP_COLOR_SEQUENCE:
            cmd = f"<SET_RGB:{rgb[0]},{rgb[1]},{rgb[2]}>"
            data = (cmd + "\n").encode("utf-8")
            ser.write(data)
            ser.flush()
            print(f"Sent: {cmd}")
            # Read any immediate response
            print(read_response(ser))
            # keep the color for the configured hold time
            time.sleep(STARTUP_HOLD_SECS)
    except Exception as e:
        print(f"Error during startup color sequence: {e}")
def process_temperature(source):
    if hasattr(source, "write") and hasattr(source, "readline"):
        ser = source
        try:
            data = (COMMANDS[1] + "\n").encode("utf-8")
            ser.write(data)
            ser.flush()
            print(f"Sent: {COMMANDS[1]}")
            response = read_response(ser)
            if response is None:
                print("No response for temperature command")
                return None
            temp = parse_data(response)
            if temp is None:
                print(f"Response (unparsed): {response}")
                return None
            color = compute_color_from_temp(temp)
            print(f"Parsed temperature: {temp} -> color {color}")
            return color
        except Exception as e:
            print(f"Error during process_temperature(serial): {e}")
            return None

    # Otherwise treat source as numeric temperature
    try:
        temp = float(source)
    except Exception:
        return None
    return compute_color_from_temp(temp)

# Process temperature value and return corresponding RGB color as a list of integers [R, G, B]
def parse_data(s):
    """Parse a string of the form <DATA:X> and return float(X) or None."""
    if not s:
        return None
    m = re.search(r"<DATA:\s*([+-]?\d+(?:\.\d+)?)\s*>", s)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def compute_color_from_temp(temp):
    """Return RGB color for given temperature (float)."""
    color = [0, 0, 0]
    if temp < 18:
        color = [0, 0, 255]  # blue
    elif temp < 22:
        color = [0, 255, 255]  # Azure
    elif temp < 25:
        color = [0, 255, 0]  # green
    elif temp < 28:
        color = [255, 255, 0]  # yellow
    else:
        color = [255, 0, 0]  # red
    return color

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