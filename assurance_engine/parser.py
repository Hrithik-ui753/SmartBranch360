"""Cisco Configuration and CLI Show-Output Parser for SmartBranch360.

Parses Cisco IOS running-configs and operational show command outputs into
strongly-typed, queryable data structures.
"""

from dataclasses import dataclass, field
import ipaddress
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union


@dataclass
class InterfaceConfig:
    """Represents a Cisco interface or subinterface."""
    name: str
    ip_address: Optional[str] = None
    subnet_mask: Optional[str] = None
    vlan_id: Optional[int] = None
    encapsulation: Optional[str] = None
    is_subinterface: bool = False
    admin_down: bool = False
    oper_status: Optional[str] = None
    nat_type: Optional[str] = None  # inside, outside, None
    access_group_in: Optional[str] = None
    access_group_out: Optional[str] = None
    switchport_mode: Optional[str] = None  # access, trunk, None
    access_vlan: Optional[int] = None
    allowed_vlans: List[int] = field(default_factory=list)
    description: Optional[str] = None
    portfast: bool = False


@dataclass
class DhcpPoolConfig:
    """Represents a Cisco DHCP pool definition."""
    name: str
    network: Optional[str] = None
    netmask: Optional[str] = None
    default_router: Optional[str] = None
    dns_server: Optional[str] = None
    lease_days: Optional[int] = None


@dataclass
class AclRule:
    """Represents a parsed Access Control List rule."""
    line_number: Optional[int] = None
    action: str = ""  # permit or deny
    protocol: str = "ip"  # ip, tcp, udp, icmp, etc.
    src: str = ""
    src_wildcard: Optional[str] = None
    dst: str = ""
    dst_wildcard: Optional[str] = None
    src_port: Optional[str] = None
    dst_port: Optional[str] = None
    matches: int = 0
    raw: str = ""


@dataclass
class AclConfig:
    """Represents an Access Control List."""
    name: str
    acl_type: str = "standard"  # standard or extended
    rules: List[AclRule] = field(default_factory=list)


@dataclass
class ParsedCiscoDevice:
    """Consolidated parsed configuration and operational state for a Cisco device."""
    hostname: str = "Unknown"
    device_type: str = "unknown"  # router, switch, isp
    version: Optional[str] = None
    domain_name: Optional[str] = None
    ssh_version: Optional[int] = None
    service_password_encryption: bool = False
    has_enable_secret: bool = False
    usernames: List[str] = field(default_factory=list)
    interfaces: Dict[str, InterfaceConfig] = field(default_factory=dict)
    dhcp_pools: Dict[str, DhcpPoolConfig] = field(default_factory=dict)
    dhcp_excluded: List[Tuple[str, str]] = field(default_factory=list)
    acls: Dict[str, AclConfig] = field(default_factory=dict)
    static_routes: List[Dict[str, str]] = field(default_factory=list)
    nat_rules: List[Dict[str, Any]] = field(default_factory=list)
    vlans: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    trunks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    vty_access_class: Optional[str] = None
    vty_transport_input: List[str] = field(default_factory=list)
    vty_login_local: bool = False
    nat_statistics: Dict[str, Any] = field(default_factory=dict)
    nat_translations_count: int = 0
    dhcp_bindings: List[Dict[str, str]] = field(default_factory=list)
    raw_outputs: Dict[str, str] = field(default_factory=dict)


class CiscoConfigParser:
    """Parses Cisco IOS configurations and show outputs."""

    def __init__(self):
        pass

    def parse_text(self, text: str, default_hostname: Optional[str] = None) -> ParsedCiscoDevice:
        """Parses a multi-command dump or running-config string."""
        device = ParsedCiscoDevice()
        if default_hostname:
            device.hostname = default_hostname

        # Split commands into blocks
        lines = [line.rstrip() for line in text.splitlines()]
        self._parse_running_config(lines, device)
        self._parse_show_interfaces_brief(text, device)
        self._parse_show_vlan_brief(text, device)
        self._parse_show_interfaces_trunk(text, device)
        self._parse_show_ip_route(text, device)
        self._parse_show_access_lists(text, device)
        self._parse_show_nat_stats(text, device)
        self._parse_show_dhcp_binding(text, device)

        # Infer device type if not clear
        if "SW" in device.hostname or "Switch" in device.hostname or device.vlans:
            device.device_type = "switch"
        elif "ISP" in device.hostname:
            device.device_type = "isp"
        else:
            device.device_type = "router"

        return device

    def parse_directory(self, directory_path: Union[str, Path]) -> Dict[str, ParsedCiscoDevice]:
        """Parses all Cisco output text files in a directory grouped by device."""
        dir_path = Path(directory_path)
        if not dir_path.exists() or not dir_path.is_dir():
            return {}

        devices: Dict[str, ParsedCiscoDevice] = {}

        for file_path in dir_path.glob("*.txt"):
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            # Determine target device from filename or prompt (e.g. R1-..., SW1-...)
            fname = file_path.name
            dev_name = "Unknown"
            for prefix in ("R1", "SW1", "SW2", "ISP"):
                if fname.upper().startswith(prefix):
                    dev_name = prefix
                    break

            # If not detected from prefix, look for Cisco prompt e.g. "R1#" or "hostname X"
            if dev_name == "Unknown":
                m_prompt = re.search(r"^([A-Za-z0-9_-]+)[>#]", content, re.MULTILINE)
                if m_prompt:
                    dev_name = m_prompt.group(1).upper()
                else:
                    m_host = re.search(r"^hostname\s+([A-Za-z0-9_-]+)", content, re.MULTILINE | re.IGNORECASE)
                    if m_host:
                        dev_name = m_host.group(1).upper()

            if dev_name not in devices:
                devices[dev_name] = ParsedCiscoDevice(hostname=dev_name)

            dev = devices[dev_name]
            dev.raw_outputs[fname] = content

            # Parse file contents into device state
            lines = [l.rstrip() for l in content.splitlines()]
            self._parse_running_config(lines, dev)
            self._parse_show_interfaces_brief(content, dev)
            self._parse_show_vlan_brief(content, dev)
            self._parse_show_interfaces_trunk(content, dev)
            self._parse_show_ip_route(content, dev)
            self._parse_show_access_lists(content, dev)
            self._parse_show_nat_stats(content, dev)
            self._parse_show_dhcp_binding(content, dev)

        # Set device types
        for name, dev in devices.items():
            if "SW" in name:
                dev.device_type = "switch"
            elif "ISP" in name:
                dev.device_type = "isp"
            else:
                dev.device_type = "router"

        return devices

    def _parse_running_config(self, lines: List[str], dev: ParsedCiscoDevice):
        """Parses Cisco IOS running-config blocks."""
        current_iface: Optional[InterfaceConfig] = None
        current_dhcp: Optional[DhcpPoolConfig] = None
        current_acl: Optional[AclConfig] = None
        in_vty = False

        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("Building configuration"):
                continue
            if line == "!" or line.startswith("!") or line.lower() in ("exit", "end"):
                current_iface = None
                current_dhcp = None
                current_acl = None
                in_vty = False
                continue

            # Hostname
            m_host = re.match(r"^hostname\s+([A-Za-z0-9_-]+)", line, re.IGNORECASE)
            if m_host:
                dev.hostname = m_host.group(1)
                continue

            # Version
            m_ver = re.match(r"^version\s+([0-9.]+)", line, re.IGNORECASE)
            if m_ver:
                dev.version = m_ver.group(1)
                continue

            # Domain name
            m_dom = re.match(r"^ip\s+domain-name\s+([A-Za-z0-9_.-]+)", line, re.IGNORECASE)
            if m_dom:
                dev.domain_name = m_dom.group(1)
                continue

            # SSH Version
            m_ssh = re.match(r"^ip\s+ssh\s+version\s+(\d+)", line, re.IGNORECASE)
            if m_ssh:
                dev.ssh_version = int(m_ssh.group(1))
                continue

            # Password Encryption
            if re.match(r"^service\s+password-encryption", line, re.IGNORECASE):
                dev.service_password_encryption = True
                continue

            # Enable Secret
            if re.match(r"^enable\s+secret\s+", line, re.IGNORECASE):
                dev.has_enable_secret = True
                continue

            # Username
            m_user = re.match(r"^username\s+([A-Za-z0-9_.-]+)", line, re.IGNORECASE)
            if m_user:
                dev.usernames.append(m_user.group(1))
                continue

            # DHCP Excluded Address
            m_dhcp_ex = re.match(r"^ip\s+dhcp\s+excluded-address\s+([0-9.]+)(?:\s+([0-9.]+))?", line, re.IGNORECASE)
            if m_dhcp_ex:
                start_ip = m_dhcp_ex.group(1)
                end_ip = m_dhcp_ex.group(2) or start_ip
                dev.dhcp_excluded.append((start_ip, end_ip))
                continue

            # NAT Overload rule
            m_nat = re.match(r"^ip\s+nat\s+inside\s+source\s+list\s+(\d+|[A-Za-z0-9_-]+)\s+interface\s+([A-Za-z0-9_/-]+)\s*(overload)?", line, re.IGNORECASE)
            if m_nat:
                dev.nat_rules.append({
                    "acl": m_nat.group(1),
                    "outside_interface": m_nat.group(2),
                    "overload": bool(m_nat.group(3))
                })
                continue

            # Static Route
            m_route = re.match(r"^ip\s+route\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+|[A-Za-z0-9_/-]+)", line, re.IGNORECASE)
            if m_route:
                dev.static_routes.append({
                    "network": m_route.group(1),
                    "netmask": m_route.group(2),
                    "nexthop": m_route.group(3)
                })
                continue

            # Standard Numbered ACL
            m_std_acl = re.match(r"^access-list\s+(\d+)\s+(permit|deny)\s+([0-9.]+)\s+([0-9.]+)", line, re.IGNORECASE)
            if m_std_acl:
                acl_id = m_std_acl.group(1)
                if acl_id not in dev.acls:
                    dev.acls[acl_id] = AclConfig(name=acl_id, acl_type="standard")
                dev.acls[acl_id].rules.append(AclRule(
                    action=m_std_acl.group(2).lower(),
                    protocol="ip",
                    src=m_std_acl.group(3),
                    src_wildcard=m_std_acl.group(4),
                    raw=line
                ))
                continue

            # Named Standard / Extended ACL start
            m_named_acl = re.match(r"^ip\s+access-list\s+(standard|extended)\s+([A-Za-z0-9_-]+)", line, re.IGNORECASE)
            if m_named_acl:
                acl_type = m_named_acl.group(1).lower()
                acl_name = m_named_acl.group(2)
                current_acl = AclConfig(name=acl_name, acl_type=acl_type)
                dev.acls[acl_name] = current_acl
                current_iface = None
                current_dhcp = None
                in_vty = False
                continue

            # Inside Named ACL
            if current_acl and (line.startswith("permit") or line.startswith("deny")):
                rule = self._parse_acl_line(line, current_acl.acl_type)
                if rule:
                    current_acl.rules.append(rule)
                continue

            # Interface block start
            m_iface = re.match(r"^interface\s+([A-Za-z0-9_./-]+)", line, re.IGNORECASE)
            if m_iface:
                if_name = self._normalize_interface_name(m_iface.group(1))
                current_iface = InterfaceConfig(
                    name=if_name,
                    is_subinterface="." in if_name
                )
                dev.interfaces[if_name] = current_iface
                current_dhcp = None
                current_acl = None
                in_vty = False
                continue

            # Reset interface context on top-level configuration command
            if line.startswith(("line ", "ip route", "ip access-list", "vlan ", "ip dhcp pool", "interface ")):
                current_iface = None

            # Inside Interface
            if current_iface:
                if re.match(r"^shutdown", line, re.IGNORECASE):
                    current_iface.admin_down = True
                elif re.match(r"^no\s+shutdown", line, re.IGNORECASE):
                    current_iface.admin_down = False
                elif m_ip := re.match(r"^ip\s+address\s+([0-9.]+)\s+([0-9.]+)", line, re.IGNORECASE):
                    current_iface.ip_address = m_ip.group(1)
                    current_iface.subnet_mask = m_ip.group(2)
                elif m_encap := re.match(r"^encapsulation\s+dot1Q\s+(\d+)", line, re.IGNORECASE):
                    current_iface.encapsulation = "dot1Q"
                    current_iface.vlan_id = int(m_encap.group(1))
                elif re.match(r"^ip\s+nat\s+inside", line, re.IGNORECASE):
                    current_iface.nat_type = "inside"
                elif re.match(r"^ip\s+nat\s+outside", line, re.IGNORECASE):
                    current_iface.nat_type = "outside"
                elif m_acl_in := re.match(r"^ip\s+access-group\s+([A-Za-z0-9_-]+)\s+in", line, re.IGNORECASE):
                    current_iface.access_group_in = m_acl_in.group(1)
                elif m_acl_out := re.match(r"^ip\s+access-group\s+([A-Za-z0-9_-]+)\s+out", line, re.IGNORECASE):
                    current_iface.access_group_out = m_acl_out.group(1)
                elif m_sw_mode := re.match(r"^switchport\s+mode\s+(access|trunk)", line, re.IGNORECASE):
                    current_iface.switchport_mode = m_sw_mode.group(1).lower()
                elif m_sw_acc := re.match(r"^switchport\s+access\s+vlan\s+(\d+)", line, re.IGNORECASE):
                    current_iface.access_vlan = int(m_sw_acc.group(1))
                elif m_sw_trunk := re.match(r"^switchport\s+trunk\s+allowed\s+vlan\s+([0-9,-]+)", line, re.IGNORECASE):
                    current_iface.allowed_vlans = self._parse_vlan_range(m_sw_trunk.group(1))
                elif m_desc := re.match(r"^description\s+(.+)", line, re.IGNORECASE):
                    current_iface.description = m_desc.group(1).strip()
                elif re.match(r"^spanning-tree\s+portfast", line, re.IGNORECASE):
                    current_iface.portfast = True
                continue

            # DHCP Pool block start
            m_pool = re.match(r"^ip\s+dhcp\s+pool\s+([A-Za-z0-9_-]+)", line, re.IGNORECASE)
            if m_pool:
                pool_name = m_pool.group(1)
                current_dhcp = DhcpPoolConfig(name=pool_name)
                dev.dhcp_pools[pool_name] = current_dhcp
                current_iface = None
                current_acl = None
                in_vty = False
                continue

            # Inside DHCP Pool
            if current_dhcp:
                if m_net := re.match(r"^network\s+([0-9.]+)\s+([0-9.]+)", line, re.IGNORECASE):
                    current_dhcp.network = m_net.group(1)
                    current_dhcp.netmask = m_net.group(2)
                elif m_gw := re.match(r"^default-router\s+([0-9.]+)", line, re.IGNORECASE):
                    current_dhcp.default_router = m_gw.group(1)
                elif m_dns := re.match(r"^dns-server\s+([0-9.]+)", line, re.IGNORECASE):
                    current_dhcp.dns_server = m_dns.group(1)
                continue

            # Switch VLAN declaration
            m_vlan = re.match(r"^vlan\s+(\d+)", line, re.IGNORECASE)
            if m_vlan:
                vid = int(m_vlan.group(1))
                if vid not in dev.vlans:
                    dev.vlans[vid] = {"id": vid, "name": f"VLAN{vid}", "status": "active", "ports": []}
                continue
            if line.startswith("name ") and dev.vlans:
                last_vlan_id = max(dev.vlans.keys())
                dev.vlans[last_vlan_id]["name"] = line.split("name ", 1)[1].strip()
                continue

            # Line VTY
            if re.match(r"^line\s+vty\s+", line, re.IGNORECASE):
                in_vty = True
                current_iface = None
                current_dhcp = None
                current_acl = None
                continue

            if in_vty:
                if m_acc := re.match(r"^access-class\s+([A-Za-z0-9_-]+)\s+in", line, re.IGNORECASE):
                    dev.vty_access_class = m_acc.group(1)
                elif m_trans := re.match(r"^transport\s+input\s+(.+)", line, re.IGNORECASE):
                    dev.vty_transport_input = [x.strip() for x in m_trans.group(1).split()]
                elif re.match(r"^login\s+local", line, re.IGNORECASE):
                    dev.vty_login_local = True

    def _parse_acl_line(self, line: str, acl_type: str) -> Optional[AclRule]:
        """Parses an individual permit/deny rule line."""
        parts = line.split()
        if not parts:
            return None
        action = parts[0].lower()
        if action not in ("permit", "deny"):
            return None

        rule = AclRule(action=action, raw=line)

        if acl_type == "standard":
            # standard: permit|deny <src> [<src-wildcard>] or host <src> or any
            if len(parts) >= 2:
                if parts[1].lower() == "any":
                    rule.src = "0.0.0.0"
                    rule.src_wildcard = "255.255.255.255"
                elif parts[1].lower() == "host" and len(parts) >= 3:
                    rule.src = parts[2]
                    rule.src_wildcard = "0.0.0.0"
                else:
                    rule.src = parts[1]
                    rule.src_wildcard = parts[2] if len(parts) >= 3 else "0.0.0.0"
            return rule

        # extended: permit|deny <proto> <src> <src_wildcard> <dst> <dst_wildcard>
        if len(parts) >= 3:
            rule.protocol = parts[1].lower()
            idx = 2
            # parse src
            if parts[idx].lower() == "any":
                rule.src = "0.0.0.0"
                rule.src_wildcard = "255.255.255.255"
                idx += 1
            elif parts[idx].lower() == "host":
                rule.src = parts[idx + 1]
                rule.src_wildcard = "0.0.0.0"
                idx += 2
            elif len(parts) > idx + 1 and self._is_ip(parts[idx]):
                rule.src = parts[idx]
                rule.src_wildcard = parts[idx + 1]
                idx += 2
            else:
                rule.src = parts[idx]
                idx += 1

            # parse dst
            if idx < len(parts):
                if parts[idx].lower() == "any":
                    rule.dst = "0.0.0.0"
                    rule.dst_wildcard = "255.255.255.255"
                elif parts[idx].lower() == "host" and idx + 1 < len(parts):
                    rule.dst = parts[idx + 1]
                    rule.dst_wildcard = "0.0.0.0"
                elif idx + 1 < len(parts) and self._is_ip(parts[idx]):
                    rule.dst = parts[idx]
                    rule.dst_wildcard = parts[idx + 1]
                else:
                    rule.dst = parts[idx]

        return rule

    def _parse_show_interfaces_brief(self, text: str, dev: ParsedCiscoDevice):
        """Parses output of 'show ip interface brief'."""
        pattern = re.compile(
            r"^(GigabitEthernet[0-9./-]+|FastEthernet[0-9./-]+|Vlan[0-9]+)\s+([0-9.]+|unassigned)\s+\w+\s+\w+\s+(up|down|administratively down)\s+(up|down)",
            re.MULTILINE | re.IGNORECASE
        )
        for match in pattern.finditer(text):
            if_name = self._normalize_interface_name(match.group(1))
            ip_addr = match.group(2)
            status = match.group(3).lower()
            proto = match.group(4).lower()

            if if_name not in dev.interfaces:
                dev.interfaces[if_name] = InterfaceConfig(
                    name=if_name,
                    is_subinterface="." in if_name
                )
            iface = dev.interfaces[if_name]
            if ip_addr != "unassigned":
                iface.ip_address = ip_addr
            if "administratively down" in status:
                iface.admin_down = True
            iface.oper_status = "up" if (status == "up" and proto == "up") else "down"

    def _parse_show_vlan_brief(self, text: str, dev: ParsedCiscoDevice):
        """Parses output of 'show vlan brief'."""
        lines = text.splitlines()
        vlan_header_found = False
        for line in lines:
            if "VLAN Name" in line or "VLAN" in line and "Status" in line:
                vlan_header_found = True
                continue
            if not vlan_header_found or not line.strip() or line.startswith("----"):
                continue

            m = re.match(r"^(\d+)\s+([A-Za-z0-9_-]+)\s+(active|act/unsup|suspend)(?:\s+(.*))?", line.strip())
            if m:
                vid = int(m.group(1))
                vname = m.group(2)
                vstatus = m.group(3)
                ports_raw = m.group(4) or ""
                ports = [p.strip() for p in ports_raw.split(",") if p.strip()]

                dev.vlans[vid] = {
                    "id": vid,
                    "name": vname,
                    "status": vstatus,
                    "ports": ports
                }

    def _parse_show_interfaces_trunk(self, text: str, dev: ParsedCiscoDevice):
        """Parses output of 'show interfaces trunk'."""
        lines = text.splitlines()
        section = None
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            if "Port" in line_str and "Mode" in line_str and "Status" in line_str:
                section = "status"
                continue
            if "Vlans allowed on trunk" in line_str:
                section = "allowed"
                continue
            if "Vlans allowed and active" in line_str or "Vlans in spanning tree" in line_str:
                section = "other"
                continue

            if section == "status" and not line_str.startswith("Port"):
                parts = line_str.split()
                if len(parts) >= 4:
                    port = self._normalize_interface_name(parts[0])
                    dev.trunks[port] = {
                        "port": port,
                        "mode": parts[1],
                        "encapsulation": parts[2],
                        "status": parts[3],
                        "native_vlan": int(parts[4]) if len(parts) >= 5 and parts[4].isdigit() else 1,
                        "allowed_vlans": []
                    }
            elif section == "allowed" and not line_str.startswith("Port"):
                parts = line_str.split()
                if len(parts) >= 2:
                    port = self._normalize_interface_name(parts[0])
                    allowed_str = parts[1]
                    vlans = self._parse_vlan_range(allowed_str)
                    if port in dev.trunks:
                        dev.trunks[port]["allowed_vlans"] = vlans
                    else:
                        dev.trunks[port] = {"port": port, "allowed_vlans": vlans}

    def _parse_show_ip_route(self, text: str, dev: ParsedCiscoDevice):
        """Parses 'show ip route' output."""
        m_gw = re.search(r"Gateway of last resort is\s+([0-9.]+)\s+to network\s+([0-9.]+)", text)
        if m_gw:
            dev.static_routes.append({
                "network": m_gw.group(2),
                "netmask": "0.0.0.0",
                "nexthop": m_gw.group(1),
                "default_route": True
            })

    def _parse_show_access_lists(self, text: str, dev: ParsedCiscoDevice):
        """Parses match counts and rule lines from 'show access-lists'."""
        lines = text.splitlines()
        current_acl = None
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            m_header = re.match(r"^(Standard|Extended)\s+IP\s+access\s+list\s+([A-Za-z0-9_-]+)", line_str, re.IGNORECASE)
            if m_header:
                acl_type = m_header.group(1).lower()
                acl_name = m_header.group(2)
                if acl_name not in dev.acls:
                    dev.acls[acl_name] = AclConfig(name=acl_name, acl_type=acl_type)
                current_acl = dev.acls[acl_name]
                continue

            if current_acl:
                m_rule = re.match(r"^(\d+)?\s*(permit|deny)\s+(.+?)(?:\s+\((\d+)\s+matches\))?$", line_str, re.IGNORECASE)
                if m_rule:
                    seq = int(m_rule.group(1)) if m_rule.group(1) else None
                    action = m_rule.group(2).lower()
                    rest = m_rule.group(3)
                    matches = int(m_rule.group(4)) if m_rule.group(4) else 0

                    rule = self._parse_acl_line(f"{action} {rest}", current_acl.acl_type)
                    if rule:
                        rule.line_number = seq
                        rule.matches = matches
                        current_acl.rules.append(rule)

    def _parse_show_nat_stats(self, text: str, dev: ParsedCiscoDevice):
        """Parses 'show ip nat statistics' and 'show ip nat translations'."""
        m_act = re.search(r"Total active translations:\s+(\d+)", text)
        if m_act:
            dev.nat_statistics["active_translations"] = int(m_act.group(1))
            dev.nat_translations_count = int(m_act.group(1))

        m_hits = re.search(r"Hits:\s+(\d+)\s+Misses:\s+(\d+)", text)
        if m_hits:
            dev.nat_statistics["hits"] = int(m_hits.group(1))
            dev.nat_statistics["misses"] = int(m_hits.group(2))

        m_out = re.search(r"Outside interfaces:\s*\n\s+([A-Za-z0-9_./-]+)", text)
        if m_out:
            dev.nat_statistics["outside_interface"] = self._normalize_interface_name(m_out.group(1).strip())

        # Count translations from show ip nat translations table if present
        trans_lines = re.findall(r"^(icmp|tcp|udp)\s+[0-9.:]+\s+[0-9.:]+", text, re.MULTILINE | re.IGNORECASE)
        if trans_lines and dev.nat_translations_count == 0:
            dev.nat_translations_count = len(trans_lines)

    def _parse_show_dhcp_binding(self, text: str, dev: ParsedCiscoDevice):
        """Parses 'show ip dhcp binding' leases."""
        pattern = re.compile(r"^([0-9.]+)\s+([0-9a-fA-F.]+)\s+([^\n]+?)\s+(Automatic|Manual)", re.MULTILINE)
        for m in pattern.finditer(text):
            dev.dhcp_bindings.append({
                "ip": m.group(1),
                "hardware_address": m.group(2),
                "lease_expiration": m.group(3).strip(),
                "type": m.group(4)
            })

    def _parse_vlan_range(self, range_str: str) -> List[int]:
        """Converts strings like '10,20,30,99' or '10-12,20' into a sorted list of VLAN IDs."""
        vlans = set()
        for part in range_str.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                bounds = part.split("-")
                if len(bounds) == 2 and bounds[0].isdigit() and bounds[1].isdigit():
                    for v in range(int(bounds[0]), int(bounds[1]) + 1):
                        vlans.add(v)
            elif part.isdigit():
                vlans.add(int(part))
        return sorted(list(vlans))

    def _normalize_interface_name(self, name: str) -> str:
        """Standardizes Cisco interface names (e.g. Gi0/0 -> GigabitEthernet0/0)."""
        name = name.strip()
        name = re.sub(r"^Gi(?:gabitEthernet)?", "GigabitEthernet", name, flags=re.IGNORECASE)
        name = re.sub(r"^Fa(?:stEthernet)?", "FastEthernet", name, flags=re.IGNORECASE)
        name = re.sub(r"^Te(?:nGigabitEthernet)?", "TenGigabitEthernet", name, flags=re.IGNORECASE)
        name = re.sub(r"^Vl(?:an)?", "Vlan", name, flags=re.IGNORECASE)
        return name

    def _is_ip(self, val: str) -> bool:
        """Helper to test if string is a valid IPv4 address."""
        try:
            ipaddress.IPv4Address(val)
            return True
        except ValueError:
            return False
