#!/usr/bin/env python3
import sys
import subprocess
import os

def check_dependencies():
    """Check if required packages are installed, if not, try to install from requirements.txt"""
    try:
        import requests
        import PyQt6
    except ImportError:
        print("Required dependencies not found. Installing from requirements.txt...")
        script_dir = os.path.dirname(os.path.realpath(__file__))
        req_path = os.path.join(script_dir, "requirements.txt")
        if os.path.exists(req_path):
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_path])
                print("Dependencies installed successfully.")
            except subprocess.CalledProcessError:
                print("Failed to install dependencies. Please run 'pip install -r requirements.txt' manually.")
                sys.exit(1)
        else:
            print("requirements.txt not found. Please install dependencies manually.")
            sys.exit(1)

check_dependencies()

import argparse
import vpngate_core as vpncore

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VPN Gate CLI Connector")
    parser.add_argument("--status", action="store_true", help="Check if VPN is active")
    parser.add_argument("--stop", action="store_true", help="Disconnect and delete the VPN")
    parser.add_argument("--tcp", action="store_true", help="Show TCP servers only")
    parser.add_argument("--all", action="store_true", help="Show all servers")
    args = parser.parse_args()

    if args.stop:
        success, msg = vpncore.disconnect_vpn()
        print(msg)
        sys.exit(0 if success else 1)
    
    if args.status:
        active = vpncore.is_active()
        print(f"Status: {vpncore.CONNECTION_NAME} is {'ACTIVE' if active else 'NOT active'}")
        if active:
            stats = vpncore.get_stats()
            if stats:
                up, down, ping, loss = stats
                print(f"Down: {down:.1f} KB/s | Up: {up:.1f} KB/s")
                print(f"Ping: {ping} | Loss: {loss}")
        sys.exit(0 if active else 1)

    proto_pref = "all" if args.all else ("tcp" if args.tcp else "udp")
    print(f"Fetching servers (Preference: {proto_pref.upper()})...")
    servers = vpncore.get_servers()
    
    filtered = []
    for s in servers:
        if proto_pref == "udp" and s['has_udp']: filtered.append(s)
        elif proto_pref == "tcp" and s['has_tcp']: filtered.append(s)
        elif proto_pref == "all": filtered.append(s)
    
    filtered.sort(key=lambda x: int(x['Score']), reverse=True)
    
    print(f"{'Idx':<4} | {'Proto':<5} | {'Country':<15} | {'IP':<15} | {'Score':<10} | {'Ping':<5}")
    print("-" * 75)
    for i, s in enumerate(filtered[:20]):
        p = "UDP" if (proto_pref != "tcp" and s['has_udp']) else "TCP"
        print(f"{i:<4} | {p:<5} | {s['CountryShort']:<15} | {s['IP']:<15} | {s['Score']:<10} | {s['Ping']:<5}")

    try:
        choice = input("\nEnter Index to connect (or 'q' to quit): ")
        if choice.lower() == 'q': sys.exit(0)
        idx = int(choice)
        if 0 <= idx < len(filtered):
            success, msg = vpncore.connect_vpn(filtered[idx], force_proto=("tcp" if proto_pref == "tcp" else None))
            print(msg)
        else:
            print("Invalid index.")
    except (ValueError, KeyboardInterrupt):
        print("\nExiting.")
