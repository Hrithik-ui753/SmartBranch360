#!/usr/bin/env python3
"""SmartBranch 360 configuration-plan and Cisco show-output checker."""
import argparse
import ipaddress
import re
from pathlib import Path
import sys

try:
    import yaml
except ImportError:
    print("Missing dependency: PyYAML. Install with: python -m pip install -r requirements.txt")
    sys.exit(2)


def load_plan(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_plan(plan):
    findings = []
    vlans = plan.get("vlans", [])
    ids, subnets = set(), []
    for vlan in vlans:
        vid, name = vlan.get("id"), vlan.get("name")
        try:
            if vid in ids:
                findings.append(("ERROR", f"Duplicate VLAN ID {vid}"))
            ids.add(vid)
            net = ipaddress.ip_network(vlan["subnet"], strict=True)
            gw = ipaddress.ip_address(vlan["gateway"])
            if gw not in net or gw in (net.network_address, net.broadcast_address):
                findings.append(("ERROR", f"VLAN {vid} gateway {gw} is not a usable host in {net}"))
            for other_id, other_net in subnets:
                if net.overlaps(other_net):
                    findings.append(("ERROR", f"VLAN {vid} subnet {net} overlaps VLAN {other_id} subnet {other_net}"))
            subnets.append((vid, net))
            if not (1 <= int(vid) <= 4094):
                findings.append(("ERROR", f"VLAN ID {vid} is outside valid range 1-4094"))
            if not name:
                findings.append(("WARNING", f"VLAN {vid} has no name"))
        except (KeyError, ValueError) as exc:
            findings.append(("ERROR", f"Invalid VLAN entry {vlan}: {exc}"))

    for device, data in plan.get("devices", {}).items():
        try:
            ip = ipaddress.ip_address(data["ip"])
            matching = [v for v in vlans if v.get("id") == data.get("vlan")]
            if not matching:
                findings.append(("ERROR", f"{device} references undefined VLAN {data.get('vlan')}"))
                continue
            net = ipaddress.ip_network(matching[0]["subnet"])
            if ip not in net or ip in (net.network_address, net.broadcast_address):
                findings.append(("ERROR", f"{device} IP {ip} is not a usable address in VLAN {data['vlan']} ({net})"))
            if ip == ipaddress.ip_address(matching[0]["gateway"]):
                findings.append(("ERROR", f"{device} IP duplicates its VLAN gateway {ip}"))
        except (KeyError, ValueError) as exc:
            findings.append(("ERROR", f"Invalid device entry {device}: {exc}"))

    defined = {v.get("id") for v in vlans}
    for trunk in plan.get("trunks", []):
        missing = defined - set(trunk.get("allowed_vlans", []))
        if missing:
            findings.append(("ERROR", f"{trunk.get('device')} {trunk.get('interface')} missing VLAN(s) {sorted(missing)} on allowed trunk list"))

    security = plan.get("security", {})
    if security.get("guest_may_access_internal_vlans") is not False:
        findings.append(("ERROR", "Guest isolation policy is not set to false"))
    try:
        ipaddress.ip_network(security["ssh_allowed_subnet"], strict=True)
    except (KeyError, ValueError):
        findings.append(("ERROR", "SSH allowed subnet is missing or invalid"))

    return findings


def inspect_show_outputs(directory):
    findings = []
    if not directory:
        return findings
    path = Path(directory)
    if not path.exists():
        return [("WARNING", f"Show-output directory does not exist: {path}")]
    files = list(path.glob("*.txt"))
    if not files:
        findings.append(("WARNING", f"No .txt show-output files found in {path}"))
    for file in files:
        content = file.read_text(encoding="utf-8", errors="ignore")
        lower = content.lower()
        if "show vlan brief" in file.name.lower() or "vlan" in file.name.lower():
            for vid in ("10", "20", "30", "99"):
                # A simple presence check; verify the actual VLAN table manually too.
                if not re.search(rf"(?m)^\s*{vid}\s+", content):
                    findings.append(("WARNING", f"{file.name}: VLAN {vid} not found in captured output (check show vlan brief)"))
        if "trunk" in file.name.lower() and "trunking" not in lower and "allowed" not in lower:
            findings.append(("WARNING", f"{file.name}: output does not clearly show trunk status/allowed VLANs"))
        if "ip interface brief" in file.name.lower() or "interfaces" in file.name.lower():
            if "administratively down" in lower:
                findings.append(("ERROR", f"{file.name}: at least one interface is administratively down"))
    return findings


def main():
    parser = argparse.ArgumentParser(description="Validate SmartBranch 360 plan and selected show outputs.")
    parser.add_argument("--plan", required=True, help="Path to network_plan.yaml")
    parser.add_argument("--show-dir", help="Optional directory containing saved Cisco show-command output .txt files")
    args = parser.parse_args()

    try:
        plan = load_plan(args.plan)
    except Exception as exc:
        print(f"[ERROR] Could not read plan: {exc}")
        return 2

    findings = validate_plan(plan) + inspect_show_outputs(args.show_dir)
    print("=" * 60)
    print("SMARTBRANCH 360 - NETWORK ASSURANCE REPORT")
    print(f"Site: {plan.get('site', 'Unknown')}")
    print("=" * 60)
    if not findings:
        print("[PASS] No plan issues detected by the checker.")
    else:
        for severity, message in findings:
            print(f"[{severity}] {message}")
    errors = sum(1 for level, _ in findings if level == "ERROR")
    warnings = sum(1 for level, _ in findings if level == "WARNING")
    print("-" * 60)
    print(f"Summary: {errors} error(s), {warnings} warning(s)")
    print("Note: This is a lightweight assurance aid, not a replacement for live testing.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
