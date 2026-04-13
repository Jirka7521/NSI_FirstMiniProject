import time
import re
import serial
import serial.tools.list_ports

# Names of keywords to look for in port descriptions to identify Silabs CP210x devices
KEYWORDS = ("silicon", "silabs", "cp210")

# Global configuration
BAUD = 9600
READ_TIMEOUT = 1.0  # seconds to read responses after sending each command
# All commands that the program sends to devices. Keep the original index usage
# so existing references remain stable: index 0 = PING, index 1 = SET_T:1000
COMMANDS_SEND = [
    "<PING>",
    "<SET_T:1000>",
    "<KEEP_ALIVE>",
    "<SET_T:0>",
    "<SET_RGB:{r},{g},{b}>",
]
# Expected/received message patterns (kept as examples/templates)
COMMANDS_RECIEVED = [
    "<DATA:{value}>",
]
KEEP_ALIVE_INTERVAL = 15.0  # send <KEEP_ALIVE> every 15 seconds
RECONNECT_SCAN_INTERVAL = 5.0  # scan for new devices every 5 seconds
STARTUP_COLOR_TEST = False  # perform startup LED color test when a device is opened
TEMP_REQUEST_INTERVAL = 5.0  # seconds between temperature requests per device
# Sequence of RGB colors for startup test (kept for STARTUP_HOLD_SECS each)
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

# Read lines from the serial port for a certain time after sending a command, and return the last line decoded as UTF-8 (with fallback) or None if no response
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

# Send the initial command (e.g. <PING>) to the device and print the response
def send_initial_command(ser):
    try:
        data = (COMMANDS_SEND[0] + "\n").encode("utf-8")
        ser.write(data)
        ser.flush()
        print(f"Sent: {COMMANDS_SEND[0]}")
        print(read_response(ser))
    except Exception as e:
        print(f"Error sending initial command: {e}")

# Perform a startup sequence of RGB set commands to test the LEDs, holding each color for a configured time. This is optional and can be enabled with STARTUP_COLOR_TEST.
def perform_startup_color_sequence(ser):
    """Send a sequence of RGB set commands to the device, holding each for STARTUP_HOLD_SECS."""
    try:
        for rgb in STARTUP_COLOR_SEQUENCE:
            cmd = COMMANDS_SEND[4].format(r=rgb[0], g=rgb[1], b=rgb[2])
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

# Process temperature command: if source is a serial port, send the command and parse response; if source is numeric, compute color directly. Returns RGB color as list of integers or None on failure.
def process_temperature(source):
    if hasattr(source, "write") and hasattr(source, "readline"):
        ser = source
        try:
            data = (COMMANDS_SEND[1] + "\n").encode("utf-8")
            ser.write(data)
            ser.flush()
            print(f"Sent: {COMMANDS_SEND[1]}")
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
    if not s:
        return None
    m = re.search(r"<DATA:\s*([+-]?\d+(?:\.\d+)?)\s*>", s)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None

# Compute RGB color based on temperature thresholds. This is a simple mapping where cooler temperatures are blue and warmer temperatures are red, with intermediate colors in between.
def compute_color_from_temp(temp):
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
    # Persistent manager: maintain opened ports, send KEEP_ALIVE every KEEP_ALIVE_INTERVAL
    opened = {}  # device -> {'port': PortInfo, 'ser': Serial, 'next_keepalive': float}
    last_scan = READ_TIMEOUT

    try:
        while True:
            try:
                now = time.monotonic()

                # Scan for new ports periodically
                if now - last_scan >= RECONNECT_SCAN_INTERVAL:
                    ports = find_silabs_ports()
                    # Add new ports
                    for p in ports:
                        dev = p.device
                        if dev not in opened:
                            try:
                                ser = serial.Serial(dev, baudrate=BAUD, timeout=1)
                                print(f"Opened: {dev} — {p.description or 'no description'}")
                                # Perform startup sequence and initial ping
                                if STARTUP_COLOR_TEST:
                                    perform_startup_color_sequence(ser)
                                send_initial_command(ser)
                                opened[dev] = {
                                    'port': p,
                                    'ser': ser,
                                    'next_keepalive': now + KEEP_ALIVE_INTERVAL,
                                    'next_temp': now + TEMP_REQUEST_INTERVAL,
                                }
                            except Exception as e:
                                print(f"Failed to open {dev}: {e}")
                    # Remove ports that disappeared
                    current_devices = {p.device for p in serial.tools.list_ports.comports()}
                    to_remove = [dev for dev in opened.keys() if dev not in current_devices]
                    for dev in to_remove:
                        try:
                            print(f"Port disappeared, closing: {dev}")
                            opened[dev]['ser'].close()
                        except Exception:
                            pass
                        del opened[dev]

                    last_scan = now

                # Handle keep-alive for opened ports
                for dev, info in list(opened.items()):
                    ser = info['ser']
                    try:
                        if now >= info['next_keepalive']:
                            cmd = COMMANDS_SEND[2]
                            ser.write((cmd + "\n").encode('utf-8'))
                            ser.flush()
                            print(f"Sent: {cmd} to {dev}")
                            # read any response briefly
                            resp = read_response(ser)
                            if resp:
                                print(f"{dev} -> {resp}")
                            info['next_keepalive'] = now + KEEP_ALIVE_INTERVAL
                        # Periodic temperature request and color refresh
                        if now >= info.get('next_temp', 0):
                            try:
                                tcmd = COMMANDS_SEND[3]  # request immediate temperature
                                ser.write((tcmd + "\n").encode('utf-8'))
                                ser.flush()
                                print(f"Sent: {tcmd} to {dev}")
                                resp = read_response(ser)
                                if resp:
                                    print(f"{dev} -> {resp}")
                                    temp = parse_data(resp)
                                    if temp is not None:
                                        color = compute_color_from_temp(temp)
                                        # send color update
                                        rgb_cmd = COMMANDS_SEND[4].format(r=color[0], g=color[1], b=color[2])
                                        ser.write((rgb_cmd + "\n").encode('utf-8'))
                                        ser.flush()
                                        print(f"Sent: {rgb_cmd} to {dev}")
                                    else:
                                        print(f"Temperature response unparsed: {resp}")
                                else:
                                    print(f"No temperature response from {dev}")
                            except Exception as e:
                                print(f"Error requesting temperature from {dev}: {e}")
                            finally:
                                info['next_temp'] = now + TEMP_REQUEST_INTERVAL
                    except (serial.SerialException, OSError) as e:
                        print(f"Serial error on {dev}: {e}; closing and will attempt reconnect")
                        try:
                            ser.close()
                        except Exception:
                            pass
                        del opened[dev]
                    except Exception as e:
                        print(f"Unexpected error for {dev}: {e}")

                time.sleep(0.25)

            except KeyboardInterrupt:
                print("Exiting, closing ports")
                break
            except Exception as e:
                # Log error, close any open ports and retry after a pause
                print(f"Top-level unexpected error: {e}. Will close ports and retry in {RECONNECT_SCAN_INTERVAL}s")
                for dev in list(opened.keys()):
                    try:
                        opened[dev]['ser'].close()
                    except Exception:
                        pass
                    del opened[dev]
                time.sleep(RECONNECT_SCAN_INTERVAL)
    finally:
        for dev, info in opened.items():
            try:
                info['ser'].close()
            except Exception:
                pass


if __name__ == "__main__":
    main()