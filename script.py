from flask import Flask, jsonify, render_template, request
import requests
import threading
import time
import datetime
import logging

# Vorschlag chatgpt 17.5.2024
# Configuration constants
POWER_SWITCH_URL = "http://192.168.0.2"  # Example LAN address of your power switch
POWER_THRESHOLD = 132.0  # Watts threshold for automatic toggling
CONSECUTIVE_COUNT = 3  # Number of consecutive measurements above threshold to trigger toggling
CHECK_INTERVAL = 30  # Interval in seconds to check power switch status
LOG_FILE_PATH = "/home/wilde/bin/ebike_lader/Daten/akku_1.dat"  # Path to the log file
DEFAULT_CHARGETARGET = 80
DEFAULT_W0 = 0.0

# Global variables
above_thresh_count = 0  # Counter for consecutive measurements above threshold

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def read_last_line(file_path):
    """Read the last line of a file efficiently."""
    try:
        with open(file_path, 'rb') as f:
            f.seek(-2, 2)  # Jump to the second last byte.
            while f.read(1) != b'\n':  # Until EOL is found...
                f.seek(-2, 1)  # ...jump back the read byte plus one more.
            last_line = f.readline().decode().strip()
            f.close()
        return last_line
    except Exception as e:
        logger.error(f"Error reading last line from log file: {e}")
        return None

def read_chargetarget():
    """Read the charge target from the log file."""
    last_line = read_last_line(LOG_FILE_PATH)
    if last_line:
        try:
            return int(last_line.split(";")[3])
        except (IndexError, ValueError) as e:
            logger.error(f"Error parsing chargetarget from log file: {e}")
    return DEFAULT_CHARGETARGET  # Default value if reading fails

def read_W0():
    """Read the W0 value from the log file."""
    last_line = read_last_line(LOG_FILE_PATH)
    if last_line:
        try:
            return float(last_line.split(";")[4])
        except (IndexError, ValueError) as e:
            logger.error(f"Error parsing W0 from log file: {e}")
    return DEFAULT_W0  # Default value if reading fails

def write_log_entry(power, wcharged, chargetarget, W0):
    """Write a log entry to the log file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp}; {power}; {wcharged}; {chargetarget}; {W0}\n"
    try:
        with open(LOG_FILE_PATH, "a") as f:
            f.write(log_entry)
            f.close()
    except IOError as e:
        logger.error(f"Error writing to log file: {e}")

def check_and_toggle():
    """Background thread to periodically check power and toggle switch."""
    global above_thresh_count
    while True:
        with app.app_context():
            status = get_status()
            power = status.get('power', 0)  # Assuming 'power' is the key for power measurement in status

            if power > POWER_THRESHOLD:
                logger.info("Power exceeds threshold.")
                chargetarget = status["ChargeTarget"]
                if chargetarget == 80:
                    above_thresh_count += 1
                    if above_thresh_count >= CONSECUTIVE_COUNT:
                        logger.info("Threshold count exceeded, switching off.")
                        switch_off()
                        above_thresh_count = 0
                else:
                    above_thresh_count = 0

            if status.get('relay'):
                W0 = read_W0()
                write_log_entry(power, status["Wcharged"], status["ChargeTarget"], W0)

        time.sleep(CHECK_INTERVAL)

def get_status():
    """Get the current status from the power switch."""
    global above_thresh_count
    try:
        response = requests.get(f"{POWER_SWITCH_URL}/report")
        response.raise_for_status()
        status = response.json()
    except requests.RequestException as e:
        logger.error(f"Error getting status from power switch: {e}")
        return {}

    W0 = read_W0()
    status["Wcharged"] = (status['energy_since_boot'] - W0) / 3600.0
    status["above_thresh_count"] = above_thresh_count
    status["ChargeTarget"] = read_chargetarget()
    if status.get('relay'):
        power = status.get('power', 0)  # Assuming 'power' is the key for power measurement in status
        if power > 107.0:
            status["Ladung"] = power * 4.4 - 471.2
        else:
            status["Ladung"] = 0.0

    logger.debug(f"Status: {status}")
    return status

def get_energy_charged_since_last_full_charge():
    energy_charged = 0.0
    energy_total = 0.0
    i = 0
    with open("/home/wilde/bin/ebike/akku_1.dat","r") as f:
        next(f)
        for line in f:
            i = i+1
            date = line.split(";")[0]
            charge_target = int(line.split(";")[3])
            power = float(line.split(";")[1])
            energy_charged_old = energy_charged
            energy_charged = float(line.split(";")[2])
            if charge_target == 80:
                if energy_charged < energy_charged_old:
                    energy_total = energy_total + energy_charged_old
            if charge_target == 100:
                if power < 10:
                    energy_total = 0
        energy_total = energy_total + energy_charged
    f.close()
    return energy_total

@app.route('/')
def index():
    status = get_status()
    return render_template('index.html', status=status)

@app.route('/switch_on80', methods=['GET', 'POST'])
def switch_on80():
    try:
        status = get_status()
        if not status.get('relay'):
            response = requests.get(f"{POWER_SWITCH_URL}/relay?state=1")
            response.raise_for_status()
            time.sleep(3)
            status = get_status()
            e80 = get_energy_charged_since_last_full_charge()
            if e80 > 6000.0:
                W0 = status["energy_since_boot"]
                write_log_entry(status['power'], 0, 100, W0)
                logger.info("Set chargetarget to 100.")
            else:   
                W0 = status["energy_since_boot"]
                write_log_entry(status['power'], 0, 80, W0)
                logger.info("Set chargetarget to 80.")
            return render_template('index.html', status=status)
    except requests.RequestException as e:
        logger.error(f"Error switching on to 80%: {e}")
        return jsonify({"error": "Failed to switch on to 80%"}), 500

@app.route('/switch_on100', methods=['GET', 'POST'])
def switch_on100():
    try:
        status = get_status()
        if not status.get('relay'):
            response = requests.get(f"{POWER_SWITCH_URL}/relay?state=1")
            response.raise_for_status()
            time.sleep(3)
            status = get_status()
            W0 = status["energy_since_boot"]
            write_log_entry(status['power'], 0, 100, W0)
            logger.info("Set chargetarget to 100.")
            return render_template('index.html', status=status)
    except requests.RequestException as e:
        logger.error(f"Error switching on to 100%: {e}")
        return jsonify({"error": "Failed to switch on to 100%"}), 500

@app.route('/switch_off', methods=['GET', 'POST'])
def switch_off():
    try:
        response = requests.get(f"{POWER_SWITCH_URL}/relay?state=0")
        response.raise_for_status()
        time.sleep(3)
        status = get_status()
        logger.info("Switched off.")
        return render_template('index.html', status=status)
    except requests.RequestException as e:
        logger.error(f"Error switching off: {e}")
        return jsonify({"error": "Failed to switch off"}), 500

@app.route('/update', methods=['POST', 'GET'])
def update():
    status = get_status()
    return render_template('index.html', status=status)

if __name__ == '__main__':
    # Start the background thread for checking and toggling
    check_thread = threading.Thread(target=check_and_toggle)
    check_thread.daemon = True
    check_thread.start()

    # Run the Flask web server
    app.run(debug=True, host='0.0.0.0')
