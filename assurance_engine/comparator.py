"""Configuration Assurance Engine for SmartBranch360.

Performs closed-loop intent assurance by comparing intended YAML state against
actual parsed Cisco device configurations and operational states.
"""

from dataclasses import dataclass, field
import ipaddress
from typing import Any, Dict, List, Optional
from .parser import ParsedCiscoDevice
from .validator import ValidationFinding


class ConfigurationAssuranceEngine:
    """Closed-loop intent validation and configuration assurance engine."""

    def __init__(self, plan: Dict[str, Any], devices: Dict[str, ParsedCiscoDevice]):
        self.plan = plan
        self.devices = devices
        self.findings: List[ValidationFinding] = []

    def verify_all(self) -> List[ValidationFinding]:
        """Runs the complete suite of configuration assurance checks."""
        self.findings.clear()

        # Find R1 router
        r1 = self._find_device(["R1", "ROUTER", "GW"])
        sw1 = self._find_device(["SW1", "CORE"])
        sw2 = self._find_device(["SW2", "ACCESS"])

        self._verify_router_subinterfaces(r1)
        self._verify_dhcp_architecture(r1)
        self._verify_nat_pat_configuration(r1)
        self._verify_routing_infrastructure(r1)
        self._verify_device_ssh_hardening(r1, "R1")
        self._verify_switch_vlans_and_trunks(sw1, sw2)
        self._verify_switch_management_svi(sw1, "SW1", "10.10.99.2")
        self._verify_switch_management_svi(sw2, "SW2", "10.10.99.3")
        self._verify_device_ssh_hardening(sw1, "SW1")
        self._verify_device_ssh_hardening(sw2, "SW2")

        return self.findings

    def _find_device(self, candidate_names: List[str]) -> Optional[ParsedCiscoDevice]:
        """Looks up a parsed device matching any candidate name."""
        for cand in candidate_names:
            for name, dev in self.devices.items():
                if cand.upper() in name.upper():
                    return dev
        return None

    def _verify_router_subinterfaces(self, r1: Optional[ParsedCiscoDevice]):
        """Verifies that R1 router-on-a-stick subinterfaces match the plan."""
        if not r1:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code="ASSURE_R1_MISSING",
                category="Router Interfaces",
                message="R1 router configuration or show-output files were not provided for assurance check.",
                remediation="Capture and provide R1 configuration files in sample_show_outputs."
            ))
            return

        vlans = {v["id"]: v for v in self.plan.get("vlans", []) if isinstance(v, dict)}

        # Find subinterfaces on R1
        subifaces = {name: iface for name, iface in r1.interfaces.items() if iface.is_subinterface}

        for vid, vlan_data in vlans.items():
            expected_gw = vlan_data.get("gateway")
            expected_net = ipaddress.ip_network(vlan_data.get("subnet"))
            expected_mask = str(expected_net.netmask)

            # Find matching subinterface by VLAN tag or name ending in .vid
            matching_sub = None
            for if_name, iface in subifaces.items():
                if iface.vlan_id == vid or if_name.endswith(f".{vid}"):
                    matching_sub = iface
                    break

            if not matching_sub:
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code=f"ASSURE_SUBIFACE_MISSING_VLAN_{vid}",
                    category="Router Interfaces",
                    message=f"R1 is missing Router-on-a-Stick subinterface for VLAN {vid} ({vlan_data.get('name')}).",
                    remediation=f"Configure interface GigabitEthernet0/0.{vid} with encapsulation dot1Q {vid}."
                ))
                continue

            # Check 802.1Q encapsulation
            if matching_sub.encapsulation != "dot1Q" or matching_sub.vlan_id != vid:
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code=f"ASSURE_ENCAPSULATION_ERROR_VLAN_{vid}",
                    category="Router Interfaces",
                    message=f"Subinterface {matching_sub.name} encapsulation tag mismatch: expected dot1Q {vid}, got {matching_sub.vlan_id}.",
                    remediation=f"Execute: encapsulation dot1Q {vid} under {matching_sub.name}."
                ))
            else:
                self.findings.append(ValidationFinding(
                    status="PASS",
                    code=f"ASSURE_ENCAPSULATION_VALID_VLAN_{vid}",
                    category="Router Interfaces",
                    message=f"Subinterface {matching_sub.name} 802.1Q dot1Q encapsulation verified for VLAN {vid}."
                ))

            # Check Gateway IP
            if not matching_sub.ip_address:
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code=f"ASSURE_GATEWAY_IP_MISSING_VLAN_{vid}",
                    category="Router Interfaces",
                    message=f"Subinterface {matching_sub.name} has no IP address assigned; expected gateway {expected_gw}.",
                    remediation=f"Configure: ip address {expected_gw} {expected_mask} on {matching_sub.name}."
                ))
            elif matching_sub.ip_address != expected_gw:
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code=f"ASSURE_GATEWAY_IP_MISMATCH_VLAN_{vid}",
                    category="Router Interfaces",
                    message=f"Subinterface {matching_sub.name} IP {matching_sub.ip_address} does not match planned gateway {expected_gw}.",
                    remediation=f"Update IP on {matching_sub.name} to {expected_gw} {expected_mask}."
                ))
            else:
                self.findings.append(ValidationFinding(
                    status="PASS",
                    code=f"ASSURE_GATEWAY_IP_VALID_VLAN_{vid}",
                    category="Router Interfaces",
                    message=f"Subinterface {matching_sub.name} gateway IP {matching_sub.ip_address} matches plan."
                ))

            # Check Subnet Mask
            if matching_sub.subnet_mask and matching_sub.subnet_mask != expected_mask:
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code=f"ASSURE_SUBNET_MASK_MISMATCH_VLAN_{vid}",
                    category="Router Interfaces",
                    message=f"Subinterface {matching_sub.name} subnet mask {matching_sub.subnet_mask} does not match planned mask {expected_mask}."
                ))

            # Check Interface Admin Status
            if matching_sub.admin_down:
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code=f"ASSURE_SUBIFACE_ADMIN_DOWN_VLAN_{vid}",
                    category="Router Interfaces",
                    message=f"Subinterface {matching_sub.name} is administratively down.",
                    remediation=f"Issue 'no shutdown' on {matching_sub.name} and base interface."
                ))

    def _verify_dhcp_architecture(self, r1: Optional[ParsedCiscoDevice]):
        """Assures DHCP scopes on R1 match the planned VLANs requiring DHCP."""
        if not r1:
            return

        vlans_needing_dhcp = [v for v in self.plan.get("vlans", []) if v.get("dhcp")]

        for vlan in vlans_needing_dhcp:
            vid = vlan.get("id")
            vname = vlan.get("name", "").upper()
            expected_gw = vlan.get("gateway")
            expected_net = ipaddress.ip_network(vlan.get("subnet"))

            # Find matching DHCP pool by name or network
            pool = None
            for p_name, p_data in r1.dhcp_pools.items():
                if p_name.upper() == vname or (p_data.network and p_data.network == str(expected_net.network_address)):
                    pool = p_data
                    break

            if not pool:
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code=f"ASSURE_DHCP_POOL_MISSING_VLAN_{vid}",
                    category="DHCP Architecture",
                    message=f"R1 is missing required DHCP pool for VLAN {vid} ({vname}).",
                    remediation=f"Create pool: ip dhcp pool {vname}\n network {expected_net.network_address} {expected_net.netmask}\n default-router {expected_gw}"
                ))
                continue

            # Verify network and mask
            if pool.network != str(expected_net.network_address) or pool.netmask != str(expected_net.netmask):
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code=f"ASSURE_DHCP_SCOPE_NETWORK_MISMATCH_VLAN_{vid}",
                    category="DHCP Architecture",
                    message=f"DHCP pool '{pool.name}' network {pool.network}/{pool.netmask} does not match {expected_net}.",
                    remediation=f"Correct network statement under ip dhcp pool {pool.name}."
                ))
            else:
                self.findings.append(ValidationFinding(
                    status="PASS",
                    code=f"ASSURE_DHCP_SCOPE_VALID_VLAN_{vid}",
                    category="DHCP Architecture",
                    message=f"DHCP pool '{pool.name}' network scope {pool.network}/{pool.netmask} is correct."
                ))

            # Verify default-router
            if pool.default_router != expected_gw:
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code=f"ASSURE_DHCP_DEFAULT_ROUTER_MISMATCH_VLAN_{vid}",
                    category="DHCP Architecture",
                    message=f"DHCP pool '{pool.name}' default-router {pool.default_router} does not match gateway {expected_gw}.",
                    remediation=f"Set 'default-router {expected_gw}' under ip dhcp pool {pool.name}."
                ))
            else:
                self.findings.append(ValidationFinding(
                    status="PASS",
                    code=f"ASSURE_DHCP_DEFAULT_ROUTER_VALID_VLAN_{vid}",
                    category="DHCP Architecture",
                    message=f"DHCP pool '{pool.name}' default-router correctly points to gateway {expected_gw}."
                ))

            # Verify DNS server assignment
            if vid == 10 and pool.dns_server != "10.10.30.10":
                self.findings.append(ValidationFinding(
                    status="WARNING",
                    code="ASSURE_EMPLOYEE_DNS_MISMATCH",
                    category="DHCP Architecture",
                    message=f"EMPLOYEE DHCP pool DNS is {pool.dns_server}; recommended internal DNS is 10.10.30.10."
                ))

    def _verify_nat_pat_configuration(self, r1: Optional[ParsedCiscoDevice]):
        """Assures Port Address Translation (NAT overload) is properly configured."""
        if not r1:
            return

        # Check NAT Overload Rule
        if not r1.nat_rules:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code="ASSURE_NAT_OVERLOAD_MISSING",
                category="NAT / PAT",
                message="R1 is missing dynamic NAT overload (PAT) translation rule.",
                remediation="Configure: ip nat inside source list 1 interface GigabitEthernet0/1 overload"
            ))
        else:
            has_overload = any(r.get("overload") for r in r1.nat_rules)
            if has_overload:
                self.findings.append(ValidationFinding(
                    status="PASS",
                    code="ASSURE_NAT_OVERLOAD_ACTIVE",
                    category="NAT / PAT",
                    message="R1 has dynamic PAT overload rule configured on WAN interface."
                ))
            else:
                self.findings.append(ValidationFinding(
                    status="WARNING",
                    code="ASSURE_NAT_NO_OVERLOAD_FLAG",
                    category="NAT / PAT",
                    message="NAT rule present on R1 but missing 'overload' keyword for PAT multiplexing."
                ))

        # Check NAT Outside interface
        wan_iface = r1.interfaces.get("GigabitEthernet0/1")
        if not wan_iface:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code="ASSURE_WAN_IFACE_MISSING",
                category="NAT / PAT",
                message="R1 is missing WAN interface GigabitEthernet0/1."
            ))
        else:
            if wan_iface.nat_type != "outside":
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code="ASSURE_WAN_NAT_OUTSIDE_MISSING",
                    category="NAT / PAT",
                    message="WAN interface GigabitEthernet0/1 is missing 'ip nat outside'.",
                    remediation="Issue: ip nat outside on interface GigabitEthernet0/1."
                ))
            else:
                self.findings.append(ValidationFinding(
                    status="PASS",
                    code="ASSURE_WAN_NAT_OUTSIDE_VALID",
                    category="NAT / PAT",
                    message="WAN interface GigabitEthernet0/1 has 'ip nat outside' active."
                ))

        # Check NAT Inside on Branch subinterfaces
        inside_subifaces = [iface for name, iface in r1.interfaces.items() if iface.is_subinterface]
        missing_inside = [iface.name for iface in inside_subifaces if iface.nat_type != "inside"]
        if missing_inside:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code="ASSURE_NAT_INSIDE_MISSING",
                category="NAT / PAT",
                message=f"Internal subinterface(s) missing 'ip nat inside': {', '.join(missing_inside)}.",
                remediation="Apply 'ip nat inside' on all router-on-a-stick subinterfaces."
            ))
        elif inside_subifaces:
            self.findings.append(ValidationFinding(
                status="PASS",
                code="ASSURE_NAT_INSIDE_VALID",
                category="NAT / PAT",
                message=f"All {len(inside_subifaces)} branch subinterfaces have 'ip nat inside' enabled."
            ))

    def _verify_routing_infrastructure(self, r1: Optional[ParsedCiscoDevice]):
        """Assures default routing to simulated ISP is established."""
        if not r1:
            return

        has_default_route = False
        expected_isp_next_hop = "203.0.113.1"

        for route in r1.static_routes:
            if route.get("network") == "0.0.0.0" and route.get("netmask") == "0.0.0.0":
                has_default_route = True
                if route.get("nexthop") == expected_isp_next_hop:
                    self.findings.append(ValidationFinding(
                        status="PASS",
                        code="ASSURE_DEFAULT_ROUTE_VALID",
                        category="Routing",
                        message=f"Default gateway route 0.0.0.0/0 via ISP {expected_isp_next_hop} verified."
                    ))
                else:
                    self.findings.append(ValidationFinding(
                        status="WARNING",
                        code="ASSURE_DEFAULT_ROUTE_NEXTHOP_DIFF",
                        category="Routing",
                        message=f"Default route points to {route.get('nexthop')}, expected ISP {expected_isp_next_hop}."
                    ))

        if not has_default_route:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code="ASSURE_DEFAULT_ROUTE_MISSING",
                category="Routing",
                message="R1 is missing static default route 0.0.0.0 0.0.0.0 pointing to ISP gateway.",
                remediation=f"Configure: ip route 0.0.0.0 0.0.0.0 {expected_isp_next_hop} on R1."
            ))

    def _verify_switch_vlans_and_trunks(self, sw1: Optional[ParsedCiscoDevice], sw2: Optional[ParsedCiscoDevice]):
        """Assures switches carry all four VLANs and trunk links permit them."""
        defined_vlans = {v["id"] for v in self.plan.get("vlans", []) if isinstance(v, dict)}

        for sw, name in [(sw1, "SW1"), (sw2, "SW2")]:
            if not sw:
                self.findings.append(ValidationFinding(
                    status="WARNING",
                    code=f"ASSURE_{name}_NOT_FOUND",
                    category="Switching",
                    message=f"{name} configuration or show output was not provided for inspection."
                ))
                continue

            # Verify VLAN database on switch
            missing_vlans = defined_vlans - set(sw.vlans.keys())
            if missing_vlans:
                self.findings.append(ValidationFinding(
                    status="FAIL",
                    code=f"ASSURE_{name}_MISSING_VLANS",
                    category="Switching",
                    message=f"{name} VLAN database is missing required VLAN(s): {sorted(list(missing_vlans))}.",
                    remediation=f"Create missing VLANs on {name}: vlan {','.join(map(str, missing_vlans))}."
                ))
            else:
                self.findings.append(ValidationFinding(
                    status="PASS",
                    code=f"ASSURE_{name}_VLANS_COMPLETE",
                    category="Switching",
                    message=f"{name} VLAN database contains all required branch VLANs (10, 20, 30, 99)."
                ))

            # Verify trunks on switch
            for t_name, trunk in sw.trunks.items():
                allowed = set(trunk.get("allowed_vlans", []))
                if not allowed:
                    continue
                missing_allowed = defined_vlans - allowed
                if missing_allowed:
                    self.findings.append(ValidationFinding(
                        status="FAIL",
                        code=f"ASSURE_{name}_TRUNK_RESTRICTED_{t_name}",
                        category="Switching",
                        message=f"{name} trunk port {t_name} is blocking required VLAN(s): {sorted(list(missing_allowed))}.",
                        remediation=f"Issue: switchport trunk allowed vlan 10,20,30,99 on {t_name}."
                    ))
                else:
                    self.findings.append(ValidationFinding(
                        status="PASS",
                        code=f"ASSURE_{name}_TRUNK_VALID_{t_name}",
                        category="Switching",
                        message=f"{name} trunk {t_name} correctly allows all branch VLANs."
                    ))

    def _verify_switch_management_svi(self, sw: Optional[ParsedCiscoDevice], sw_name: str, expected_ip: str):
        """Verifies switch management SVI interface Vlan99 configuration."""
        if not sw:
            return

        vlan99_if = sw.interfaces.get("Vlan99")
        if not vlan99_if:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code=f"ASSURE_{sw_name}_SVI_MISSING",
                category="Switch Management",
                message=f"{sw_name} is missing interface Vlan99 management SVI.",
                remediation=f"Configure: interface Vlan99\n ip address {expected_ip} 255.255.255.0\n no shutdown"
            ))
            return

        if vlan99_if.ip_address != expected_ip:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code=f"ASSURE_{sw_name}_SVI_IP_MISMATCH",
                category="Switch Management",
                message=f"{sw_name} SVI Vlan99 IP is {vlan99_if.ip_address}; expected {expected_ip}."
            ))
        else:
            self.findings.append(ValidationFinding(
                status="PASS",
                code=f"ASSURE_{sw_name}_SVI_IP_VALID",
                category="Switch Management",
                message=f"{sw_name} SVI Vlan99 IP {expected_ip} correctly configured."
            ))

        if vlan99_if.admin_down:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code=f"ASSURE_{sw_name}_SVI_DOWN",
                category="Switch Management",
                message=f"{sw_name} interface Vlan99 is shutdown.",
                remediation=f"Issue 'no shutdown' under interface Vlan99 on {sw_name}."
            ))

    def _verify_device_ssh_hardening(self, dev: Optional[ParsedCiscoDevice], dev_name: str):
        """Assures SSH version 2, local login, and management access restriction."""
        if not dev:
            return

        # SSH Version 2
        if dev.ssh_version == 2:
            self.findings.append(ValidationFinding(
                status="PASS",
                code=f"ASSURE_{dev_name}_SSH_V2",
                category="SSH Hardening",
                message=f"{dev_name} has Cisco SSH version 2 strictly enabled."
            ))
        else:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code=f"ASSURE_{dev_name}_SSH_NOT_V2",
                category="SSH Hardening",
                message=f"{dev_name} does not enforce SSH version 2 (detected: {dev.ssh_version or 'v1/disabled'}).",
                remediation=f"Configure: ip ssh version 2 on {dev_name}."
            ))

        # VTY Transport Input (Telnet disabled)
        if "ssh" in dev.vty_transport_input and "telnet" not in dev.vty_transport_input and "all" not in dev.vty_transport_input:
            self.findings.append(ValidationFinding(
                status="PASS",
                code=f"ASSURE_{dev_name}_VTY_SSH_ONLY",
                category="SSH Hardening",
                message=f"{dev_name} VTY lines enforce SSH only (Telnet completely disabled)."
            ))
        else:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code=f"ASSURE_{dev_name}_TELNET_NOT_DISABLED",
                category="SSH Hardening",
                message=f"{dev_name} VTY lines do not enforce 'transport input ssh' (insecure telnet allowed or transport input unconfigured).",
                remediation=f"Configure: line vty 0 4 (or 15) -> transport input ssh on {dev_name}."
            ))

        # VTY Access Class (Management Subnet Restriction)
        if dev.vty_access_class:
            self.findings.append(ValidationFinding(
                status="PASS",
                code=f"ASSURE_{dev_name}_VTY_ACCESS_CLASS",
                category="SSH Hardening",
                message=f"{dev_name} VTY lines restricted by access-class '{dev.vty_access_class}' in."
            ))
        else:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code=f"ASSURE_{dev_name}_VTY_NO_ACCESS_CLASS",
                category="SSH Hardening",
                message=f"{dev_name} VTY lines lack an access-class restriction; any subnet can attempt SSH.",
                remediation=f"Apply 'access-class SSH-MGMT in' under line vty on {dev_name}."
            ))

