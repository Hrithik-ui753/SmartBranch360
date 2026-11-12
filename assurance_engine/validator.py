"""Network Plan Validator Module for SmartBranch360.

Validates network_plan.yaml against architectural invariants, RFC standards,
and enterprise best practices.
"""

from dataclasses import dataclass, field
import ipaddress
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import yaml


@dataclass
class ValidationFinding:
    """Represents an individual validation finding."""
    status: str  # PASS, FAIL, WARNING
    code: str
    category: str
    message: str
    details: Optional[Dict[str, Any]] = field(default_factory=dict)
    remediation: Optional[str] = None


class NetworkPlanValidator:
    """Validates network architecture YAML blueprints."""

    REQUIRED_ROOT_KEYS = ["site", "vlans", "devices", "trunks", "security"]
    REQUIRED_VLAN_KEYS = ["id", "name", "subnet", "gateway"]

    def __init__(self, plan_path_or_dict: Any):
        if isinstance(plan_path_or_dict, (str, Path)):
            self.plan_path = Path(plan_path_or_dict)
            self.plan = self._load_file(self.plan_path)
        elif isinstance(plan_path_or_dict, dict):
            self.plan_path = None
            self.plan = plan_path_or_dict
        else:
            raise ValueError(f"Invalid input type for plan: {type(plan_path_or_dict)}")

        self.findings: List[ValidationFinding] = []

    def _load_file(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Plan file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError("YAML plan root must be a mapping (dictionary).")
        return data

    def validate_all(self) -> List[ValidationFinding]:
        """Runs the complete suite of plan validations."""
        self.findings.clear()
        self._validate_schema_and_keys()
        self._validate_vlans()
        self._validate_devices()
        self._validate_trunks()
        self._validate_security_policies()
        return self.findings

    def _validate_schema_and_keys(self):
        """Verifies presence of all required top-level configuration keys."""
        missing = [k for k in self.REQUIRED_ROOT_KEYS if k not in self.plan]
        if missing:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code="PLAN_MISSING_ROOT_KEYS",
                category="Schema",
                message=f"Missing required top-level configuration key(s): {', '.join(missing)}",
                remediation="Ensure network_plan.yaml contains site, vlans, devices, trunks, and security."
            ))
        else:
            self.findings.append(ValidationFinding(
                status="PASS",
                code="PLAN_ROOT_SCHEMA_VALID",
                category="Schema",
                message=f"Network plan root schema valid for site '{self.plan.get('site')}'."
            ))

    def _validate_vlans(self):
        """Validates VLAN IDs, subnets, gateways, and overlap detection."""
        vlans = self.plan.get("vlans")
        if not isinstance(vlans, list) or not vlans:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code="PLAN_NO_VLANS",
                category="VLAN",
                message="Plan does not define any VLANs.",
                remediation="Add at least one VLAN definition under 'vlans'."
            ))
            return

        seen_ids: Set[int] = set()
        seen_names: Set[str] = set()
        seen_gateways: Dict[ipaddress.IPv4Address, int] = {}
        subnets: List[Tuple[int, ipaddress.IPv4Network]] = []

        for idx, vlan in enumerate(vlans):
            if not isinstance(vlan, dict):
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code="PLAN_VLAN_MALFORMED",
                    category="VLAN",
                    message=f"VLAN entry #{idx + 1} is not a valid dictionary."
                ))
                continue

            # Check required keys
            missing_vlan_keys = [k for k in self.REQUIRED_VLAN_KEYS if k not in vlan]
            if missing_vlan_keys:
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code="PLAN_VLAN_MISSING_KEYS",
                    category="VLAN",
                    message=f"VLAN entry #{idx + 1} missing required keys: {', '.join(missing_vlan_keys)}",
                    details={"vlan": vlan}
                ))
                continue

            vid = vlan.get("id")
            name = vlan.get("name")
            subnet_str = vlan.get("subnet")
            gateway_str = vlan.get("gateway")

            # Validate VLAN ID range & uniqueness
            try:
                vid_int = int(vid)
                if not (1 <= vid_int <= 4094):
                    self.findings.append(ValidationFinding(
                        status="FAIL",
                        code="PLAN_VLAN_ID_OUT_OF_RANGE",
                        category="VLAN",
                        message=f"VLAN ID {vid} out of valid IEEE 802.1Q range (1-4094).",
                        remediation="Assign a standard 802.1Q VLAN ID between 1 and 4094."
                    ))
                elif vid_int in seen_ids:
                    self.findings.append(ValidationFinding(
                        status="FAIL",
                        code="PLAN_VLAN_ID_DUPLICATE",
                        category="VLAN",
                        message=f"Duplicate VLAN ID detected: {vid_int}.",
                        remediation="Ensure each VLAN has a unique numeric identifier."
                    ))
                else:
                    seen_ids.add(vid_int)

                if vid_int in (1, 1002, 1003, 1004, 1005):
                    self.findings.append(ValidationFinding(
                        status="WARNING",
                        code="PLAN_VLAN_RESERVED_OR_DEFAULT",
                        category="VLAN",
                        message=f"VLAN {vid_int} is a Cisco default or legacy reserved VLAN ID."
                    ))
            except (ValueError, TypeError):
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code="PLAN_VLAN_ID_NON_NUMERIC",
                    category="VLAN",
                    message=f"VLAN ID '{vid}' is not a valid integer."
                ))
                continue

            # Validate VLAN Name
            if not name or not str(name).strip():
                self.findings.append(ValidationFinding(
                    status="WARNING",
                    code="PLAN_VLAN_NAME_EMPTY",
                    category="VLAN",
                    message=f"VLAN {vid} does not have a descriptive name."
                ))
            else:
                norm_name = str(name).strip().upper()
                if norm_name in seen_names:
                    self.findings.append(ValidationFinding(
                        status="WARNING",
                        code="PLAN_VLAN_NAME_DUPLICATE",
                        category="VLAN",
                        message=f"VLAN name '{name}' is duplicated across definitions."
                    ))
                seen_names.add(norm_name)

            # Validate Subnet and Gateway
            try:
                net = ipaddress.ip_network(subnet_str, strict=True)
                gw = ipaddress.ip_address(gateway_str)

                # Check gateway in subnet
                if gw not in net:
                    self.findings.append(ValidationFinding(
                        status="FAIL",
                        code="PLAN_GATEWAY_OUTSIDE_SUBNET",
                        category="IPAM",
                        message=f"VLAN {vid} gateway {gw} is not inside subnet {net}.",
                        remediation=f"Change gateway for VLAN {vid} to an address inside {net}."
                    ))
                elif gw == net.network_address:
                    self.findings.append(ValidationFinding(
                        status="FAIL",
                        code="PLAN_GATEWAY_IS_NETWORK_ADDR",
                        category="IPAM",
                        message=f"VLAN {vid} gateway {gw} is the subnet network wire address.",
                        remediation="Use a usable host IP for the gateway, not the network address."
                    ))
                elif gw == net.broadcast_address:
                    self.findings.append(ValidationFinding(
                        status="FAIL",
                        code="PLAN_GATEWAY_IS_BROADCAST_ADDR",
                        category="IPAM",
                        message=f"VLAN {vid} gateway {gw} is the subnet broadcast address.",
                        remediation="Use a usable host IP for the gateway, not the broadcast address."
                    ))

                # Check duplicate gateway
                if gw in seen_gateways:
                    self.findings.append(ValidationFinding(
                        status="FAIL",
                        code="PLAN_GATEWAY_DUPLICATE",
                        category="IPAM",
                        message=f"Duplicate gateway IP {gw} shared between VLAN {vid} and VLAN {seen_gateways[gw]}.",
                        remediation="Each VLAN must have a unique default gateway IP."
                    ))
                else:
                    seen_gateways[gw] = vid_int

                # Check subnet overlaps
                for other_vid, other_net in subnets:
                    if net.overlaps(other_net):
                        self.findings.append(ValidationFinding(
                            status="FAIL",
                            code="PLAN_SUBNET_OVERLAP",
                            category="IPAM",
                            message=f"VLAN {vid} subnet {net} overlaps with VLAN {other_vid} subnet {other_net}.",
                            remediation="Redesign IP addressing to eliminate overlapping CIDR blocks."
                        ))
                subnets.append((vid_int, net))

            except ValueError as e:
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code="PLAN_IP_SYNTAX_ERROR",
                    category="IPAM",
                    message=f"VLAN {vid} has invalid IP/subnet syntax: {e}"
                ))

        if not any(f.status == "FAIL" for f in self.findings if f.category in ("VLAN", "IPAM")):
            self.findings.append(ValidationFinding(
                status="PASS",
                code="PLAN_VLANS_VALID",
                category="VLAN",
                message=f"All {len(vlans)} VLANs, subnets, and gateways validated successfully without overlaps."
            ))

    def _validate_devices(self):
        """Validates static device IP assignments against VLAN subnets and detects conflicts."""
        devices = self.plan.get("devices", {})
        vlans = {v["id"]: v for v in self.plan.get("vlans", []) if isinstance(v, dict) and "id" in v}
        assigned_ips: Dict[ipaddress.IPv4Address, str] = {}

        # Add gateways to assigned IPs to prevent collisions
        for vid, vdata in vlans.items():
            if "gateway" in vdata:
                try:
                    gw_ip = ipaddress.ip_address(vdata["gateway"])
                    assigned_ips[gw_ip] = f"VLAN {vid} Gateway"
                except ValueError:
                    pass

        if not isinstance(devices, dict):
            self.findings.append(ValidationFinding(
                status="FAIL",
                code="PLAN_DEVICES_NOT_DICT",
                category="Devices",
                message="'devices' must be a mapping of device identifiers."
            ))
            return

        for dev_name, dev_data in devices.items():
            if not isinstance(dev_data, dict):
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code="PLAN_DEVICE_INVALID_DATA",
                    category="Devices",
                    message=f"Device '{dev_name}' has invalid specification."
                ))
                continue

            target_vlan = dev_data.get("vlan")
            ip_str = dev_data.get("ip")

            if target_vlan not in vlans:
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code="PLAN_DEVICE_UNDEFINED_VLAN",
                    category="Devices",
                    message=f"Device '{dev_name}' references undefined VLAN {target_vlan}.",
                    remediation=f"Ensure VLAN {target_vlan} is declared under 'vlans'."
                ))
                continue

            if not ip_str:
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code="PLAN_DEVICE_MISSING_IP",
                    category="Devices",
                    message=f"Device '{dev_name}' is missing required 'ip' property."
                ))
                continue

            try:
                dev_ip = ipaddress.ip_address(ip_str)
                vlan_info = vlans[target_vlan]
                subnet = ipaddress.ip_network(vlan_info["subnet"])

                # Check membership in VLAN subnet
                if dev_ip not in subnet or dev_ip in (subnet.network_address, subnet.broadcast_address):
                    self.findings.append(ValidationFinding(
                        status="FAIL",
                        code="PLAN_DEVICE_IP_NOT_USABLE",
                        category="Devices",
                        message=f"Device '{dev_name}' IP {dev_ip} is not a usable host in VLAN {target_vlan} ({subnet}).",
                        remediation=f"Assign an IP address within {subnet} (excluding network/broadcast)."
                    ))

                # Check duplicate IP
                if dev_ip in assigned_ips:
                    self.findings.append(ValidationFinding(
                        status="FAIL",
                        code="PLAN_DEVICE_IP_CONFLICT",
                        category="Devices",
                        message=f"IP address conflict: {dev_ip} on '{dev_name}' collides with {assigned_ips[dev_ip]}.",
                        remediation="Assign a unique static IP address to avoid ARP/IP conflict."
                    ))
                else:
                    assigned_ips[dev_ip] = f"Device '{dev_name}'"

            except ValueError as e:
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code="PLAN_DEVICE_IP_INVALID",
                    category="Devices",
                    message=f"Device '{dev_name}' has invalid IP address '{ip_str}': {e}"
                ))

        if not any(f.status == "FAIL" for f in self.findings if f.category == "Devices"):
            self.findings.append(ValidationFinding(
                status="PASS",
                code="PLAN_DEVICES_VALID",
                category="Devices",
                message=f"All {len(devices)} static devices validated without IP conflicts."
            ))

    def _validate_trunks(self):
        """Validates trunk links and allowed VLAN pruning lists."""
        trunks = self.plan.get("trunks", [])
        if not isinstance(trunks, list):
            self.findings.append(ValidationFinding(
                status="FAIL",
                code="PLAN_TRUNKS_NOT_LIST",
                category="Trunks",
                message="'trunks' must be a list of trunk specifications."
            ))
            return

        defined_vlans = {v["id"] for v in self.plan.get("vlans", []) if isinstance(v, dict) and "id" in v}

        for idx, trunk in enumerate(trunks):
            if not isinstance(trunk, dict):
                continue
            dev = trunk.get("device", f"Trunk#{idx+1}")
            interface = trunk.get("interface", "Unknown")
            allowed = trunk.get("allowed_vlans", [])

            if not allowed:
                self.findings.append(ValidationFinding(
                    status="WARNING",
                    code="PLAN_TRUNK_NO_ALLOWED_VLANS",
                    category="Trunks",
                    message=f"Trunk on {dev} {interface} has no explicitly allowed VLANs defined."
                ))
                continue

            allowed_set = set(allowed)
            missing = defined_vlans - allowed_set
            if missing:
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code="PLAN_TRUNK_MISSING_VLANS",
                    category="Trunks",
                    message=f"Trunk {dev} ({interface}) missing critical VLAN(s): {sorted(list(missing))}.",
                    remediation=f"Add VLANs {sorted(list(missing))} to trunk allowed list."
                ))

            # Check if trunk allows undefined VLANs
            undefined = allowed_set - defined_vlans
            if undefined:
                self.findings.append(ValidationFinding(
                    status="WARNING",
                    code="PLAN_TRUNK_UNDEFINED_VLANS",
                    category="Trunks",
                    message=f"Trunk {dev} ({interface}) allows undefined VLAN(s): {sorted(list(undefined))}."
                ))

        if not any(f.status == "FAIL" for f in self.findings if f.category == "Trunks"):
            self.findings.append(ValidationFinding(
                status="PASS",
                code="PLAN_TRUNKS_VALID",
                category="Trunks",
                message=f"All {len(trunks)} trunk interfaces correctly propagate required VLANs."
            ))

    def _validate_security_policies(self):
        """Validates security baseline specifications."""
        security = self.plan.get("security", {})
        if not isinstance(security, dict):
            self.findings.append(ValidationFinding(
                status="FAIL",
                code="PLAN_SECURITY_NOT_DICT",
                category="Security",
                message="'security' section must be a mapping."
            ))
            return

        guest_iso = security.get("guest_may_access_internal_vlans")
        if guest_iso is not False:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code="PLAN_GUEST_ISOLATION_DISABLED",
                category="Security",
                message="Security policy violation: 'guest_may_access_internal_vlans' must be set to false.",
                remediation="Set 'guest_may_access_internal_vlans: false' in network_plan.yaml."
            ))
        else:
            self.findings.append(ValidationFinding(
                status="PASS",
                code="PLAN_GUEST_ISOLATION_ENFORCED",
                category="Security",
                message="Security plan strictly mandates guest-to-internal network isolation."
            ))

        ssh_sub = security.get("ssh_allowed_subnet")
        if not ssh_sub:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code="PLAN_SSH_SUBNET_MISSING",
                category="Security",
                message="Missing 'ssh_allowed_subnet' definition in security plan."
            ))
        else:
            try:
                ssh_net = ipaddress.ip_network(ssh_sub, strict=True)
                self.findings.append(ValidationFinding(
                    status="PASS",
                    code="PLAN_SSH_SUBNET_VALID",
                    category="Security",
                    message=f"Management SSH restricted to dedicated CIDR: {ssh_net}."
                ))
            except ValueError as e:
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code="PLAN_SSH_SUBNET_INVALID",
                    category="Security",
                    message=f"Invalid 'ssh_allowed_subnet' CIDR syntax: {e}"
                ))

