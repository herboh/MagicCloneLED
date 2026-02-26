#!/usr/bin/env python3
"""MagicHome bulb auto-provisioner.

Connects to bulbs that have reverted to AP mode (LEDnetXXXXXX SSIDs),
configures WiFi credentials via AT commands over UDP, and sends them
back to the home network.

Requires root (interface management).

Usage:
    sudo python provisioner.py provision [--ssid LEDnetXXXXXX]
    sudo python provisioner.py watch [--interval 30]
    sudo python provisioner.py scan
"""

import argparse
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("provisioner")

IFACE = "wlp9s0"
BULB_IP = "10.10.123.3"
LOCAL_IP = "10.10.123.4"
AT_PORT = 48899
LED_PORT = 5577
DISCOVERY_MSG = b"HF-A11ASSISTHREAD"
CONFIG_PATH = Path(__file__).parent.parent / "config.json"

# How long to wait for the bulb to join the home network
LAN_PROBE_TIMEOUT = 60
LAN_PROBE_INTERVAL = 3


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def run(cmd, check=True, capture=True, timeout=15):
    """Run a shell command, log it, return stdout."""
    log.debug("$ %s", cmd)
    r = subprocess.run(
        cmd, shell=True, check=check,
        capture_output=capture, text=True, timeout=timeout,
    )
    if r.stdout and r.stdout.strip():
        log.debug("  → %s", r.stdout.strip()[:200])
    return r


# ---------------------------------------------------------------------------
# WiFi interface helpers
# ---------------------------------------------------------------------------

def iface_up():
    run(f"ip link set {IFACE} up")


def iface_down():
    run(f"ip link set {IFACE} down", check=False)


def iface_flush():
    run(f"ip addr flush dev {IFACE}", check=False)


def iface_set_ip():
    iface_flush()
    run(f"ip addr add {LOCAL_IP}/24 dev {IFACE}")


def kill_wpa():
    run(f"pkill -f 'wpa_supplicant.*{IFACE}'", check=False)


def connect_to_ap(ssid):
    """Connect to an open AP using wpa_supplicant."""
    # Full teardown first — scan may have left stale state
    kill_wpa()
    iface_flush()
    iface_down()
    time.sleep(1)
    iface_up()
    time.sleep(1)

    conf = (
        f"ctrl_interface=/var/run/wpa_supplicant\n"
        f"network={{\n"
        f"  ssid=\"{ssid}\"\n"
        f"  key_mgmt=NONE\n"
        f"  scan_ssid=1\n"
        f"}}\n"
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".conf", prefix="wpa_", delete=False
    ) as f:
        f.write(conf)
        conf_path = f.name

    try:
        log.info("Connecting to AP %s ...", ssid)
        proc = subprocess.Popen(
            ["wpa_supplicant", "-i", IFACE, "-c", conf_path, "-B",
             "-D", "nl80211,wext"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        proc.wait(timeout=5)
        if proc.returncode != 0:
            raise RuntimeError(
                f"wpa_supplicant failed: {proc.stderr.read()}"
            )

        # Wait for association (up to 20s — open APs can be slow)
        for attempt in range(20):
            time.sleep(1)
            r = run(f"wpa_cli -i {IFACE} status", check=False)
            stdout = r.stdout or ""
            # Extract wpa_state for logging
            for line in stdout.splitlines():
                if line.startswith("wpa_state="):
                    state = line.split("=", 1)[1]
                    log.info("  attempt %d: wpa_state=%s", attempt + 1, state)
                    break
            if "wpa_state=COMPLETED" in stdout:
                log.info("Associated with %s", ssid)
                iface_set_ip()
                time.sleep(0.5)
                return True

        log.error("Failed to associate with %s after 20s", ssid)
        return False
    finally:
        os.unlink(conf_path)


def disconnect():
    """Tear down WiFi connection."""
    kill_wpa()
    iface_flush()
    iface_down()


# ---------------------------------------------------------------------------
# AT command protocol (UDP 48899)
# ---------------------------------------------------------------------------

def at_send(msg, timeout=3):
    """Send a message to the bulb's AT command interface, return response."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(msg.encode() if isinstance(msg, str) else msg, (BULB_IP, AT_PORT))
        data, _ = sock.recvfrom(1024)
        resp = data.decode(errors="replace").strip()
        log.debug("AT send %r → %r", msg if isinstance(msg, str) else msg.decode(), resp)
        return resp
    except socket.timeout:
        log.warning("AT command timed out: %r", msg if isinstance(msg, str) else msg.decode())
        return None
    finally:
        sock.close()


def at_cmd(cmd, timeout=3):
    """Send an AT command string (auto-appends \\r if needed)."""
    if not cmd.endswith("\r"):
        cmd += "\r"
    return at_send(cmd, timeout)


def discover():
    """Send HF-A11ASSISTHREAD discovery, parse IP,MAC,MODEL response."""
    resp = at_send(DISCOVERY_MSG, timeout=5)
    if not resp:
        return None
    parts = resp.split(",")
    if len(parts) >= 3:
        return {"ip": parts[0], "mac": parts[1], "model": parts[2]}
    log.warning("Unexpected discovery response: %r", resp)
    return None


# ---------------------------------------------------------------------------
# Scanning for LEDnet* SSIDs
# ---------------------------------------------------------------------------

def scan_for_bulbs():
    """Scan for LEDnet* SSIDs using wpa_supplicant/wpa_cli."""
    kill_wpa()
    iface_up()
    time.sleep(0.5)

    # Need a minimal wpa_supplicant running for wpa_cli scan
    conf = "ctrl_interface=/var/run/wpa_supplicant\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".conf", prefix="wpa_scan_", delete=False
    ) as f:
        f.write(conf)
        conf_path = f.name

    try:
        proc = subprocess.Popen(
            ["wpa_supplicant", "-i", IFACE, "-c", conf_path, "-B"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        proc.wait(timeout=5)
        time.sleep(1)

        run(f"wpa_cli -i {IFACE} scan", check=False)
        time.sleep(5)  # scanning takes a few seconds
        r = run(f"wpa_cli -i {IFACE} scan_results", check=False)
        results = r.stdout or ""

        ssids = []
        for line in results.splitlines():
            cols = line.split("\t")
            if len(cols) >= 5:
                ssid = cols[4]
                if ssid.startswith("LEDnet"):
                    ssids.append(ssid)
                    log.info("Found bulb AP: %s (signal: %s)", ssid, cols[2])

        return ssids
    finally:
        kill_wpa()
        os.unlink(conf_path)


# ---------------------------------------------------------------------------
# Provisioning flow
# ---------------------------------------------------------------------------

def provision_bulb(ssid, config):
    """Full provisioning flow for a single bulb AP."""
    wifi = config["wifi"]
    mac_to_name = config.get("mac_to_name", {})
    bulbs = config.get("bulbs", {})

    log.info("=" * 50)
    log.info("Provisioning bulb on AP: %s", ssid)
    log.info("=" * 50)

    # Step 1: Connect to AP
    if not connect_to_ap(ssid):
        log.error("Could not connect to %s, skipping", ssid)
        disconnect()
        return False

    try:
        # Step 2: Discover bulb
        log.info("Sending discovery probe...")
        info = discover()
        if not info:
            log.error("Discovery failed — no response from %s:%d", BULB_IP, AT_PORT)
            return False

        mac = info["mac"].replace(":", "").upper()
        mac_pretty = ":".join(mac[i:i+2] for i in range(0, 12, 2))
        log.info("Discovered: IP=%s  MAC=%s  Model=%s", info["ip"], mac_pretty, info["model"])

        name = mac_to_name.get(mac, mac_to_name.get(mac_pretty, None))
        if name:
            log.info("Identified as: %s", name)
        else:
            log.info("Unknown MAC %s — not in mac_to_name mapping", mac_pretty)

        # Step 3: Firmware version
        fw = at_cmd("AT+LVER")
        if fw:
            log.info("Firmware: %s", fw)

        # Step 4: Configure WiFi
        log.info("Setting SSID: %s", wifi["ssid"])
        resp = at_cmd(f"AT+WSSSID={wifi['ssid']}")
        if resp is None:
            log.error("Failed to set SSID")
            return False
        log.info("  → %s", resp)

        log.info("Setting WiFi credentials...")
        resp = at_cmd(f"AT+WSKEY={wifi['auth']},{wifi['encryption']},{wifi['password']}")
        if resp is None:
            log.error("Failed to set WiFi key")
            return False
        log.info("  → %s", resp)

        # Step 5: Disable cloud
        log.info("Disabling cloud connection...")
        resp = at_cmd("AT+SOCKB=NONE")
        if resp:
            log.info("  → %s", resp)

        # Step 6: Switch to STA mode
        log.info("Switching to STA mode...")
        resp = at_cmd("AT+WMODE=STA")
        if resp:
            log.info("  → %s", resp)

        # Step 7: Reboot
        log.info("Rebooting bulb...")
        at_cmd("AT+Z")
        log.info("Reboot command sent")

    finally:
        disconnect()

    # Step 8: Wait for bulb on LAN
    expected_ip = bulbs.get(name) if name else None
    if expected_ip:
        log.info("Waiting for %s to appear at %s ...", name or mac_pretty, expected_ip)
        if probe_lan(expected_ip):
            log.info("SUCCESS: %s (%s) back online at %s", name, mac_pretty, expected_ip)
            return True
        else:
            log.warning(
                "Bulb did not appear at %s within %ds. "
                "It may have gotten a different IP via DHCP.",
                expected_ip, LAN_PROBE_TIMEOUT,
            )
            return False
    else:
        log.info(
            "No expected IP for MAC %s. "
            "Check your router's DHCP leases to find the bulb.",
            mac_pretty,
        )
        return True


def probe_lan(ip, timeout=LAN_PROBE_TIMEOUT, interval=LAN_PROBE_INTERVAL):
    """Try to TCP-connect to bulb on port 5577 until timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((ip, LED_PORT))
            sock.close()
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            pass
        finally:
            sock.close()
        remaining = int(deadline - time.time())
        if remaining > 0:
            log.debug("  probe %s — not yet, %ds remaining", ip, remaining)
            time.sleep(interval)
    return False


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def cmd_scan(args):
    """Scan for LEDnet* APs and print results."""
    ssids = scan_for_bulbs()
    if ssids:
        print(f"\nFound {len(ssids)} bulb AP(s):")
        for s in ssids:
            print(f"  • {s}")
    else:
        print("\nNo LEDnet* APs found.")
    disconnect()


def cmd_provision(args):
    """Connect to a bulb AP and provision it."""
    config = load_config()

    if config["wifi"]["ssid"] == "CHANGE_ME":
        log.error("WiFi credentials not configured in config.json")
        sys.exit(1)

    if args.ssid:
        ssid = args.ssid
    else:
        log.info("Scanning for bulb APs...")
        ssids = scan_for_bulbs()
        disconnect()
        if not ssids:
            log.error("No LEDnet* APs found. Is a bulb in AP mode?")
            sys.exit(1)
        if len(ssids) == 1:
            ssid = ssids[0]
        else:
            print(f"\nFound {len(ssids)} bulb APs:")
            for i, s in enumerate(ssids):
                print(f"  [{i}] {s}")
            choice = input("Which one? [0]: ").strip()
            idx = int(choice) if choice else 0
            ssid = ssids[idx]

    provision_bulb(ssid, config)


def cmd_watch(args):
    """Continuously scan for bulb APs and provision them."""
    config = load_config()
    interval = args.interval

    if config["wifi"]["ssid"] == "CHANGE_ME":
        log.error("WiFi credentials not configured in config.json")
        sys.exit(1)

    log.info("Watch mode — scanning every %ds (Ctrl+C to stop)", interval)

    # Track recently provisioned SSIDs to avoid reprovisioning
    # during the window where the bulb is rebooting
    recently_provisioned = {}  # ssid → timestamp
    cooldown = 300  # 5 min cooldown after provisioning

    while True:
        try:
            ssids = scan_for_bulbs()
            disconnect()

            now = time.time()
            for ssid in ssids:
                last = recently_provisioned.get(ssid, 0)
                if now - last < cooldown:
                    log.info(
                        "Skipping %s — provisioned %ds ago (cooldown %ds)",
                        ssid, int(now - last), cooldown,
                    )
                    continue

                config = load_config()  # reload in case creds changed
                success = provision_bulb(ssid, config)
                if success:
                    recently_provisioned[ssid] = time.time()

            # Clean up old entries
            recently_provisioned = {
                s: t for s, t in recently_provisioned.items()
                if time.time() - t < cooldown
            }

        except KeyboardInterrupt:
            log.info("Interrupted — shutting down")
            disconnect()
            break
        except Exception:
            log.exception("Error during watch cycle")
            disconnect()

        time.sleep(interval)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if os.geteuid() != 0:
        log.error("Must run as root (need interface management)")
        sys.exit(1)

    # Clean shutdown on signals
    def handle_sig(sig, frame):
        log.info("Signal %d — cleaning up", sig)
        disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    parser = argparse.ArgumentParser(description="MagicHome bulb provisioner")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("scan", help="Scan for LEDnet* APs")

    p_prov = sub.add_parser("provision", help="Provision a bulb in AP mode")
    p_prov.add_argument("--ssid", help="Specific LEDnet SSID (skip scan)")

    p_watch = sub.add_parser("watch", help="Watch for bulb APs and auto-provision")
    p_watch.add_argument("--interval", type=int, default=30, help="Scan interval in seconds")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "provision":
        cmd_provision(args)
    elif args.command == "watch":
        cmd_watch(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
