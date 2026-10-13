# pip install tabulate matplotlib requests
import subprocess
import re
import socket
import requests
from tabulate import tabulate
import matplotlib.pyplot as plt

def get_hostname(ip):
    """Attempts to resolve the human-readable device name via DNS/NetBIOS."""
    try:
        # Try standard reverse DNS lookup
        hostname = socket.gethostbyaddr(ip)[0]
        return hostname.split('.')[0] # Get short name
    except Exception:
        pass
    
    try:
        # Fallback: Try Windows nbtstat command for local Windows machine names
        output = subprocess.check_output(f"nbtstat -A {ip}", shell=True, stderr=subprocess.STDOUT).decode('utf-8', errors='ignore')
        for line in output.splitlines():
            if "<00>" in line and "UNIQUE" in line:
                parts = line.split()
                if len(parts) > 0:
                    return parts[0]
    except Exception:
        pass
        
    return "Unknown Device"

def get_arp_devices():
    """Reads local ARP cache and filters out virtual/multicast addresses."""
    print("[*] Scanning local network and gathering device details...")
    try:
        output = subprocess.check_output("arp -a", shell=True).decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[-] Error running ARP command: {e}")
        return []

    devices = []
    pattern = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+([0-9a-fA-F:-]{12,17})")
    
    seen_ips = set()
    for line in output.splitlines():
        match = pattern.search(line)
        if match:
            ip = match.group(1)
            mac = match.group(2).replace('-', ':').lower()
            
            # Filter out multicast, broadcast, and typical virtual machine gateway IPs
            if ip.endswith('.255') or ip.startswith('224.') or ip.startswith('192.168.15.') or ip.startswith('192.168.74.'):
                continue
                
            if ip not in seen_ips:
                seen_ips.add(ip)
                devices.append({"ip": ip, "mac": mac})
                
    return devices

def get_vendor(mac):
    """Fetches hardware manufacturer/vendor using MAC prefix."""
    try:
        response = requests.get(f"https://api.macvendors.com/{mac}", timeout=1.5)
        if response.status_code == 200:
            return response.text
    except Exception:
        pass
    return "Local / Unknown"

def main():
    devices = get_arp_devices()
    
    if not devices:
        print("[-] No active devices found.")
        return

    print(f"[+] Processing {len(devices)} active physical devices on your network...\n")
    
    table_data = []
    vendors_count = {}

    for idx, dev in enumerate(devices, start=1):
        ip = dev["ip"]
        mac = dev["mac"]
        
        # Get custom device name & manufacturer vendor
        hostname = get_hostname(ip)
        vendor = get_vendor(mac)
        
        # Aggregate vendors for the chart
        vendors_count[vendor] = vendors_count.get(vendor, 0) + 1
        table_data.append([idx, hostname, ip, mac, vendor])

    # 1. Display Table with Names
    headers = ["No.", "Device Name", "IP Address", "MAC Address", "Manufacturer"]
    print("\n" + "="*80)
    print("CONNECTED WI-FI DEVICES & NAMES")
    print("="*80)
    print(tabulate(table_data, headers=headers, tablefmt="fancy_grid"))

    # 2. Display Chart
    print("\n[*] Generating device distribution chart...")
    vendors = list(vendors_count.keys())
    counts = list(vendors_count.values())

    plt.figure(figsize=(9, 5))
    plt.bar(vendors, counts, color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'])
    plt.xlabel("Device Manufacturer / Type", fontweight='bold')
    plt.ylabel("Number of Devices", fontweight='bold')
    plt.title(f"Network Device Breakdown (Total Active: {len(devices)})", fontsize=12, fontweight='bold')
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()