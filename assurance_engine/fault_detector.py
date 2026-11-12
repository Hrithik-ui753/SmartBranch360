"""Fault Detection and Automated Diagnosis Engine for SmartBranch360.

Identifies, explains, diagnoses, and provides automated remediation plans for
enterprise branch network failure scenarios.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from .parser import CiscoConfigParser, ParsedCiscoDevice
from .validator import ValidationFinding


@dataclass
class FaultScenarioReport:
    """Detailed diagnosis card for a specific network fault scenario."""
    id: str
    title: str
    affected_device: str
    status: str  # DETECTED, RESOLVED, NORMAL
    problem_explanation: str
    potential_impact: str
    detected_evidence: str
    corrective_action: str
    expected_result_after_fix: str
    raw_snippet: Optional[str] = None


class FaultDetector:
    """Analyzes configurations and operational outputs to pinpoint network anomalies."""

    def __init__(self, devices: Dict[str, ParsedCiscoDevice]):
        self.devices = devices
        self.parser = CiscoConfigParser()

    def analyze_active_network(self) -> List[FaultScenarioReport]:
        """Scans the currently loaded devices for the standard 5 enterprise faults."""
        reports: List[FaultScenarioReport] = []

        r1 = self._get_dev(["R1", "ROUTER"])
        sw1 = self._get_dev(["SW1", "CORE"])
        sw2 = self._get_dev(["SW2", "ACCESS"])

        # Check Fault 1: Incorrect VLAN assignment / Trunk prune
        f1 = self._check_fault_vlan_trunk(sw1, sw2)
        if f1:
            reports.append(f1)

        # Check Fault 2: Missing DHCP Pool
        f2 = self._check_fault_missing_dhcp(r1)
        if f2:
            reports.append(f2)

        # Check Fault 3: Incorrect Gateway Address
        f3 = self._check_fault_incorrect_gateway(r1)
        if f3:
            reports.append(f3)

        # Check Fault 4: Missing NAT/PAT configuration
        f4 = self._check_fault_missing_nat(r1)
        if f4:
            reports.append(f4)

        # Check Fault 5: Incorrect Guest ACL configuration
        f5 = self._check_fault_guest_acl(r1)
        if f5:
            reports.append(f5)

        return reports

    def test_fault_scenario(self, scenario_id: str, custom_text: Optional[str] = None) -> FaultScenarioReport:
        """Evaluates a specific fault scenario against synthetic or file evidence."""
        scenario_map = {
            "F1": self._scenario_f1_trunk,
            "F2": self._scenario_f2_dhcp,
            "F3": self._scenario_f3_gateway,
            "F4": self._scenario_f4_nat,
            "F5": self._scenario_f5_acl
        }

        handler = scenario_map.get(scenario_id.upper())
        if not handler:
            raise ValueError(f"Unknown fault scenario '{scenario_id}'. Available: F1, F2, F3, F4, F5.")
        return handler(custom_text)

    def run_all_benchmarks(self, faults_dir: Optional[Path] = None) -> List[FaultScenarioReport]:
        """Runs the complete suite of 5 fault benchmark demonstrations."""
        results = []
        for fid in ["F1", "F2", "F3", "F4", "F5"]:
            custom_content = None
            if faults_dir and faults_dir.exists():
                candidates = list(faults_dir.glob(f"*{fid.lower()}*.txt"))
                if candidates:
                    custom_content = candidates[0].read_text(encoding="utf-8")
            results.append(self.test_fault_scenario(fid, custom_content))
        return results

    def _get_dev(self, names: List[str]) -> Optional[ParsedCiscoDevice]:
        for n in names:
            for k, dev in self.devices.items():
                if n.upper() in k.upper():
                    return dev
        return None

    # --- Live Scans ---

    def _check_fault_vlan_trunk(self, sw1: Optional[ParsedCiscoDevice], sw2: Optional[ParsedCiscoDevice]) -> Optional[FaultScenarioReport]:
        for sw, name in [(sw1, "SW1"), (sw2, "SW2")]:
            if not sw:
                continue
            for port, trunk in sw.trunks.items():
                allowed = trunk.get("allowed_vlans", [])
                if allowed and 20 not in allowed:
                    return FaultScenarioReport(
                        id="F1",
                        title="VLAN 20 Missing from Inter-Switch Trunk Link",
                        affected_device=name,
                        status="DETECTED",
                        problem_explanation="VLAN 20 (Guest) is not in the allowed VLAN list on inter-switch trunk port.",
                        potential_impact="Guest laptops connected to SW2 or the wireless AP cannot communicate across the trunk to R1, failing DHCP and internet access.",
                        detected_evidence=f"{name} interface {port} allowed VLAN list: {allowed} (VLAN 20 absent).",
                        corrective_action=f"Enter {name} config: interface {port} -> switchport trunk allowed vlan add 20 (or 10,20,30,99).",
                        expected_result_after_fix="Trunk carries VLAN 20 frames; guest endpoints obtain DHCP leases and ping default gateway 10.10.20.1."
                    )
        return None

    def _check_fault_missing_dhcp(self, r1: Optional[ParsedCiscoDevice]) -> Optional[FaultScenarioReport]:
        if not r1:
            return None
        has_emp = any(p.upper() == "EMPLOYEE" or p_obj.network == "10.10.10.0" for p, p_obj in r1.dhcp_pools.items())
        has_gst = any(p.upper() == "GUEST" or p_obj.network == "10.10.20.0" for p, p_obj in r1.dhcp_pools.items())

        if not has_emp or not has_gst:
            missing = "EMPLOYEE" if not has_emp else "GUEST"
            return FaultScenarioReport(
                id="F2",
                title=f"Missing DHCP Pool Scope ({missing})",
                affected_device="R1",
                status="DETECTED",
                problem_explanation=f"R1 lacks the DHCP pool configuration for the {missing} department.",
                potential_impact="Client devices in this VLAN fail automatic IP provisioning, receive APIPA 169.254.x.x addresses, and suffer complete loss of connectivity.",
                detected_evidence=f"Configured DHCP pools: {list(r1.dhcp_pools.keys())} - scope for {missing} is missing.",
                corrective_action=f"Configure pool: ip dhcp pool {missing}\n network 10.10.x.0 255.255.255.0\n default-router 10.10.x.1\n dns-server 10.10.30.10",
                expected_result_after_fix=f"DHCP DORA handshake succeeds; hosts receive valid 10.10.x.x leases."
            )
        return None

    def _check_fault_incorrect_gateway(self, r1: Optional[ParsedCiscoDevice]) -> Optional[FaultScenarioReport]:
        if not r1:
            return None
        sub10 = r1.interfaces.get("GigabitEthernet0/0.10")
        if sub10 and sub10.ip_address and sub10.ip_address != "10.10.10.1":
            return FaultScenarioReport(
                id="F3",
                title="Incorrect Gateway IP Address on Router Subinterface",
                affected_device="R1",
                status="DETECTED",
                problem_explanation=f"Subinterface GigabitEthernet0/0.10 IP is configured as {sub10.ip_address} instead of planned 10.10.10.1.",
                potential_impact="Default router mismatch causes all off-subnet routing (to Server VLAN, Management, and WAN) to silently fail for employee PCs.",
                detected_evidence=f"GigabitEthernet0/0.10 ip address {sub10.ip_address} {sub10.subnet_mask}.",
                corrective_action="interface GigabitEthernet0/0.10\n ip address 10.10.10.1 255.255.255.0",
                expected_result_after_fix="Subinterface IP aligns with DHCP default-router; employee PCs successfully ping gateway and remote subnets."
            )
        return None

    def _check_fault_missing_nat(self, r1: Optional[ParsedCiscoDevice]) -> Optional[FaultScenarioReport]:
        if not r1:
            return None
        if not r1.nat_rules:
            return FaultScenarioReport(
                id="F4",
                title="Missing NAT / PAT Overload Configuration",
                affected_device="R1",
                status="DETECTED",
                problem_explanation="R1 has no 'ip nat inside source list ... overload' command configured.",
                potential_impact="Private RFC1918 addresses (10.10.0.0/16) are transmitted un-translated across WAN, causing ISP edge router to drop all outbound branch traffic.",
                detected_evidence="No NAT rules or active translations in running-config.",
                corrective_action="ip nat inside source list 1 interface GigabitEthernet0/1 overload\naccess-list 1 permit 10.10.0.0 0.0.255.255",
                expected_result_after_fix="Outbound packets are translated to 203.0.113.2 with unique Layer 4 port numbers; ping to 198.51.100.10 succeeds."
            )
        return None

    def _check_fault_guest_acl(self, r1: Optional[ParsedCiscoDevice]) -> Optional[FaultScenarioReport]:
        if not r1:
            return None
        sub20 = r1.interfaces.get("GigabitEthernet0/0.20")
        if sub20:
            acl_name = sub20.access_group_in
            if not acl_name:
                return FaultScenarioReport(
                    id="F5",
                    title="Missing Guest Isolation ACL on Router Subinterface",
                    affected_device="R1",
                    status="DETECTED",
                    problem_explanation="Subinterface GigabitEthernet0/0.20 has no inbound access-group applied.",
                    potential_impact="Guest users can freely access sensitive servers (VLAN 30) and management switches (VLAN 99), violating enterprise zero-trust policy.",
                    detected_evidence="GigabitEthernet0/0.20 lacks 'ip access-group ... in'.",
                    corrective_action="interface GigabitEthernet0/0.20\n ip access-group GUEST-IN in",
                    expected_result_after_fix="Guest traffic to 10.10.30.0/24 and 10.10.99.0/24 is filtered; outbound Internet traffic remains permitted."
                )
        return None

    # --- Benchmark Handlers for Standalone Proof ---

    def _scenario_f1_trunk(self, text: Optional[str] = None) -> FaultScenarioReport:
        content = text or """
        interface FastEthernet0/24
         switchport mode trunk
         switchport trunk allowed vlan 10,30,99
        """
        dev = self.parser.parse_text(content, default_hostname="SW1")
        trunk = dev.trunks.get("FastEthernet0/24") or list(dev.trunks.values())[0] if dev.trunks else {}
        allowed = trunk.get("allowed_vlans", [10, 30, 99])
        is_missing_20 = 20 not in allowed

        return FaultScenarioReport(
            id="F1",
            title="Incorrect VLAN Assignment: VLAN 20 Missing on Trunk",
            affected_device="SW1 (FastEthernet0/24)",
            status="DETECTED" if is_missing_20 else "NORMAL",
            problem_explanation="VLAN 20 was excluded from the allowed trunk VLAN list on SW1 port FastEthernet0/24 connecting to SW2.",
            potential_impact="Guest endpoints and wireless AP clients connected to SW2 are partitioned from R1; DHCP requests fail and clients receive 169.254.x.x.",
            detected_evidence=f"switchport trunk allowed vlan {','.join(map(str, allowed))} (VLAN 20 not allowed).",
            corrective_action="SW1(config)# interface FastEthernet0/24\nSW1(config-if)# switchport trunk allowed vlan 10,20,30,99",
            expected_result_after_fix="Trunk encapsulation carries 802.1Q tag 20; guest clients receive 10.10.20.x IP leases and ping gateway 10.10.20.1.",
            raw_snippet=content.strip()
        )

    def _scenario_f2_dhcp(self, text: Optional[str] = None) -> FaultScenarioReport:
        content = text or """
        ip dhcp pool GUEST
         network 10.10.20.0 255.255.255.0
         default-router 10.10.20.1
        """
        dev = self.parser.parse_text(content, default_hostname="R1")
        has_employee_pool = "EMPLOYEE" in dev.dhcp_pools

        return FaultScenarioReport(
            id="F2",
            title="Missing DHCP Configuration: EMPLOYEE Pool Absent",
            affected_device="R1 Router",
            status="DETECTED" if not has_employee_pool else "NORMAL",
            problem_explanation="The DHCP pool for VLAN 10 (EMPLOYEE) is missing from R1 configuration.",
            potential_impact="Employee desktop PCs fail to acquire network settings via DHCP DORA and cannot reach the internal server or internet.",
            detected_evidence=f"DHCP pools defined on R1: {list(dev.dhcp_pools.keys())} (EMPLOYEE missing).",
            corrective_action="R1(config)# ip dhcp pool EMPLOYEE\nR1(dhcp-config)# network 10.10.10.0 255.255.255.0\nR1(dhcp-config)# default-router 10.10.10.1\nR1(dhcp-config)# dns-server 10.10.30.10",
            expected_result_after_fix="R1 DHCP daemon responds to DHCPDISCOVER with DHCPOFFER in 10.10.10.0/24 range.",
            raw_snippet=content.strip()
        )

    def _scenario_f3_gateway(self, text: Optional[str] = None) -> FaultScenarioReport:
        content = text or """
        interface GigabitEthernet0/0.10
         encapsulation dot1Q 10
         ip address 10.10.10.254 255.255.255.0
        """
        dev = self.parser.parse_text(content, default_hostname="R1")
        sub10 = dev.interfaces.get("GigabitEthernet0/0.10")
        current_ip = sub10.ip_address if sub10 else "10.10.10.254"

        return FaultScenarioReport(
            id="F3",
            title="Incorrect Gateway Address on Subinterface",
            affected_device="R1 (GigabitEthernet0/0.10)",
            status="DETECTED" if current_ip != "10.10.10.1" else "NORMAL",
            problem_explanation=f"Subinterface GigabitEthernet0/0.10 is configured with IP {current_ip}, but the network plan and DHCP specify 10.10.10.1.",
            potential_impact="Employee PCs sending packets to 10.10.10.1 fail ARP resolution; inter-VLAN routing and internet connectivity break.",
            detected_evidence=f"ip address {current_ip} 255.255.255.0 on GigabitEthernet0/0.10.",
            corrective_action="R1(config)# interface GigabitEthernet0/0.10\nR1(config-subif)# ip address 10.10.10.1 255.255.255.0",
            expected_result_after_fix="Subinterface IP becomes 10.10.10.1; hosts successfully ping gateway and route packets.",
            raw_snippet=content.strip()
        )

    def _scenario_f4_nat(self, text: Optional[str] = None) -> FaultScenarioReport:
        content = text or """
        interface GigabitEthernet0/1
         ip address 203.0.113.2 255.255.255.252
        """
        dev = self.parser.parse_text(content, default_hostname="R1")
        has_nat = bool(dev.nat_rules)

        return FaultScenarioReport(
            id="F4",
            title="Missing NAT / PAT Translation Configuration",
            affected_device="R1 Router",
            status="DETECTED" if not has_nat else "NORMAL",
            problem_explanation="R1 has no dynamic PAT overload statement linking internal branch subnets to WAN interface GigabitEthernet0/1.",
            potential_impact="Internal 10.10.0.0/16 packets exit to ISP without translation; ISP drops RFC 1918 private source packets.",
            detected_evidence="No 'ip nat inside source list ... overload' detected in configuration.",
            corrective_action="R1(config)# ip access-list standard 1\nR1(config-std-nacl)# permit 10.10.0.0 0.0.255.255\nR1(config)# ip nat inside source list 1 interface GigabitEthernet0/1 overload",
            expected_result_after_fix="Dynamic translations recorded in 'show ip nat translations'; outbound ping to 198.51.100.10 succeeds.",
            raw_snippet=content.strip()
        )

    def _scenario_f5_acl(self, text: Optional[str] = None) -> FaultScenarioReport:
        content = text or """
        ip access-list extended GUEST-IN
         permit ip 10.10.20.0 0.0.0.255 any
        """
        dev = self.parser.parse_text(content, default_hostname="R1")
        acl = dev.acls.get("GUEST-IN")
        rules = acl.rules if acl else []
        has_deny_server = any("10.10.30." in r.dst and r.action == "deny" for r in rules)

        return FaultScenarioReport(
            id="F5",
            title="Incorrect Guest ACL: Internal Subnet Denials Missing",
            affected_device="R1 (ip access-list extended GUEST-IN)",
            status="DETECTED" if not has_deny_server else "NORMAL",
            problem_explanation="The Guest ACL contains a broad 'permit any' without preceding 'deny' rules for Server VLAN (10.10.30.0/24) and Management VLAN (10.10.99.0/24).",
            potential_impact="Severe security breach: Guests can access internal company server and switch management interfaces directly.",
            detected_evidence="ACL GUEST-IN permits 10.10.20.0/24 to any without blocking 10.10.30.0/24 or 10.10.99.0/24.",
            corrective_action="R1(config)# ip access-list extended GUEST-IN\nR1(config-ext-nacl)# 10 deny ip 10.10.20.0 0.0.0.255 10.10.30.0 0.0.0.255\nR1(config-ext-nacl)# 20 deny ip 10.10.20.0 0.0.0.255 10.10.99.0 0.0.0.255\nR1(config-ext-nacl)# 30 permit ip 10.10.20.0 0.0.0.255 any",
            expected_result_after_fix="Guest ping to 10.10.30.10 is Destination Host Unreachable; ping to 198.51.100.10 (Internet) succeeds.",
            raw_snippet=content.strip()
        )

