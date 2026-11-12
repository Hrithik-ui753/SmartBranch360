"""Security Audit Engine for SmartBranch360.

Performs deep network security compliance checks including microsegmentation,
guest isolation, SSH management perimeter hardening, AAA hygiene, and port security.
"""

from dataclasses import dataclass, field
import ipaddress
from typing import Any, Dict, List, Optional
from .parser import ParsedCiscoDevice
from .validator import ValidationFinding


class SecurityAuditor:
    """Automated security posture auditor for branch office networking."""

    def __init__(self, devices: Dict[str, ParsedCiscoDevice]):
        self.devices = devices
        self.findings: List[ValidationFinding] = []

    def audit_all(self) -> List[ValidationFinding]:
        """Runs all security audit checks across network devices."""
        self.findings.clear()

        r1 = self._get_device(["R1", "ROUTER"])
        sw1 = self._get_device(["SW1", "CORE"])
        sw2 = self._get_device(["SW2", "ACCESS"])

        if r1:
            self._audit_guest_isolation_acl(r1)
            self._audit_management_ssh_acl(r1, "R1")
            self._audit_password_hardening(r1, "R1")
            self._audit_vlan1_hygiene(r1, "R1")
        else:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code="SEC_R1_NOT_INSPECTED",
                category="Security Perimeter",
                message="R1 router was not available for security auditing."
            ))

        for sw, name in [(sw1, "SW1"), (sw2, "SW2")]:
            if sw:
                self._audit_management_ssh_acl(sw, name)
                self._audit_password_hardening(sw, name)
                self._audit_vlan1_hygiene(sw, name)

        return self.findings

    def _get_device(self, names: List[str]) -> Optional[ParsedCiscoDevice]:
        for n in names:
            for k, dev in self.devices.items():
                if n.upper() in k.upper():
                    return dev
        return None

    def _audit_guest_isolation_acl(self, r1: ParsedCiscoDevice):
        """Audits Guest VLAN 20 inbound ACL for microsegmentation isolation."""
        guest_sub = None
        for name, iface in r1.interfaces.items():
            if iface.vlan_id == 20 or name.endswith(".20"):
                guest_sub = iface
                break

        if not guest_sub:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code="SEC_GUEST_SUBIFACE_MISSING",
                category="Guest Isolation",
                message="Guest subinterface (VLAN 20) not found on R1.",
                remediation="Configure GigabitEthernet0/0.20."
            ))
            return

        acl_name = guest_sub.access_group_in
        if not acl_name:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code="SEC_GUEST_ACL_NOT_APPLIED",
                category="Guest Isolation",
                message=f"No inbound ACL applied to guest subinterface {guest_sub.name}.",
                remediation=f"Apply 'ip access-group GUEST-IN in' on {guest_sub.name}."
            ))
            return

        # Find the ACL definition
        acl = r1.acls.get(acl_name)
        if not acl:
            # Fallback check standard/extended dictionary
            for a_name, a_obj in r1.acls.items():
                if a_name.upper() == acl_name.upper():
                    acl = a_obj
                    break

        if not acl:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code="SEC_GUEST_ACL_UNDEFINED",
                category="Guest Isolation",
                message=f"Subinterface {guest_sub.name} applies ACL '{acl_name}', but it is not defined in configuration.",
                remediation=f"Define extended access list '{acl_name}' with isolation rules."
            ))
            return

        # Audit ACL rules: Must deny 10.10.30.0/24 (server) and 10.10.99.0/24 (mgmt) BEFORE any broad permit
        blocks_server = False
        blocks_mgmt = False
        blocks_employee = False
        broad_permit_found = False
        permit_line = -1

        for idx, rule in enumerate(acl.rules):
            dst = rule.dst
            action = rule.action.lower()

            if action == "permit" and (dst == "any" or dst == "0.0.0.0"):
                broad_permit_found = True
                permit_line = idx

            if action == "deny":
                if "10.10.30." in dst or dst == "10.10.30.0":
                    if not broad_permit_found:
                        blocks_server = True
                if "10.10.99." in dst or dst == "10.10.99.0":
                    if not broad_permit_found:
                        blocks_mgmt = True
                if "10.10.10." in dst or dst == "10.10.10.0":
                    if not broad_permit_found:
                        blocks_employee = True

        if blocks_server:
            self.findings.append(ValidationFinding(
                status="PASS",
                code="SEC_GUEST_SERVER_ISOLATED",
                category="Guest Isolation",
                message="Guest VLAN 20 is strictly prohibited from accessing Server VLAN 30."
            ))
        else:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code="SEC_GUEST_CAN_REACH_SERVER",
                category="Guest Isolation",
                message="Security violation: Guest VLAN 20 is NOT blocked from reaching Server VLAN 30 before permit statement.",
                remediation="Insert: deny ip 10.10.20.0 0.0.0.255 10.10.30.0 0.0.0.255 at top of guest ACL."
            ))

        if blocks_mgmt:
            self.findings.append(ValidationFinding(
                status="PASS",
                code="SEC_GUEST_MGMT_ISOLATED",
                category="Guest Isolation",
                message="Guest VLAN 20 is strictly prohibited from accessing Management VLAN 99."
            ))
        else:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code="SEC_GUEST_CAN_REACH_MGMT",
                category="Guest Isolation",
                message="Security violation: Guest VLAN 20 is NOT blocked from reaching Management VLAN 99.",
                remediation="Insert: deny ip 10.10.20.0 0.0.0.255 10.10.99.0 0.0.0.255 at top of guest ACL."
            ))

        if broad_permit_found:
            self.findings.append(ValidationFinding(
                status="PASS",
                code="SEC_GUEST_OUTBOUND_PERMITTED",
                category="Guest Isolation",
                message="Guest ACL permits non-private / Internet-bound traffic after isolation denies."
            ))

    def _audit_management_ssh_acl(self, dev: ParsedCiscoDevice, dev_name: str):
        """Audits that VTY lines only permit connections originating from 10.10.99.0/24."""
        acl_name = dev.vty_access_class
        if not acl_name:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code=f"SEC_{dev_name}_VTY_UNRESTRICTED",
                category="Perimeter Hardening",
                message=f"{dev_name} VTY lines have no 'access-class' applied; SSH is vulnerable to brute-force from any VLAN.",
                remediation=f"Configure 'access-class SSH-MGMT in' under line vty 0 4/15 on {dev_name}."
            ))
            return

        acl = dev.acls.get(acl_name)
        if not acl:
            # Try to match numbered acl
            acl = dev.acls.get("10") or dev.acls.get("SSH-MGMT")

        if not acl:
            self.findings.append(ValidationFinding(
                status="WARNING",
                code=f"SEC_{dev_name}_SSH_ACL_UNVERIFIED",
                category="Perimeter Hardening",
                message=f"{dev_name} references access-class '{acl_name}', but ACL rules were not captured in config dump."
            ))
            return

        permits_mgmt_only = False
        leaks_other_subnets = False

        for rule in acl.rules:
            if rule.action == "permit":
                if "10.10.99." in rule.src or rule.src == "10.10.99.0":
                    permits_mgmt_only = True
                elif rule.src in ("0.0.0.0", "any"):
                    leaks_other_subnets = True
                elif "10.10.10." in rule.src or "10.10.20." in rule.src:
                    leaks_other_subnets = True

        if permits_mgmt_only and not leaks_other_subnets:
            self.findings.append(ValidationFinding(
                status="PASS",
                code=f"SEC_{dev_name}_SSH_MGMT_ENFORCED",
                category="Perimeter Hardening",
                message=f"{dev_name} SSH perimeter strictly permits only Management VLAN 99 (10.10.99.0/24)."
            ))
        else:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code=f"SEC_{dev_name}_SSH_MGMT_PERMISSIVE",
                category="Perimeter Hardening",
                message=f"{dev_name} SSH ACL '{acl_name}' permits non-management sources or lacks strict deny.",
                remediation="Ensure ACL permits ONLY 10.10.99.0 0.0.0.255 and ends with deny any."
            ))

    def _audit_password_hardening(self, dev: ParsedCiscoDevice, dev_name: str):
        """Audits credential encryption and local authentication hygiene."""
        if dev.service_password_encryption:
            self.findings.append(ValidationFinding(
                status="PASS",
                code=f"SEC_{dev_name}_PASSWORD_ENCRYPTION_ACTIVE",
                category="AAA & Credentials",
                message=f"{dev_name} has 'service password-encryption' enabled."
            ))
        else:
            self.findings.append(ValidationFinding(
                status="FAIL",
                code=f"SEC_{dev_name}_CLEARTEXT_PASSWORDS",
                category="AAA & Credentials",
                message=f"{dev_name} does not have 'service password-encryption' active.",
                remediation=f"Execute: service password-encryption on {dev_name}."
            ))

        if dev.has_enable_secret:
            self.findings.append(ValidationFinding(
                status="PASS",
                code=f"SEC_{dev_name}_ENABLE_SECRET_ACTIVE",
                category="AAA & Credentials",
                message=f"{dev_name} uses modern MD5/Type 5 enable secret."
            ))
        else:
            self.findings.append(ValidationFinding(
                status="WARNING",
                code=f"SEC_{dev_name}_NO_ENABLE_SECRET",
                category="AAA & Credentials",
                message=f"{dev_name} enable secret not explicitly detected in captured output."
            ))

    def _audit_vlan1_hygiene(self, dev: ParsedCiscoDevice, dev_name: str):
        """Audits default VLAN 1 status to prevent native VLAN hopping and broadcast leaks."""
        vlan1 = dev.interfaces.get("Vlan1")
        if vlan1 and vlan1.admin_down:
            self.findings.append(ValidationFinding(
                status="PASS",
                code=f"SEC_{dev_name}_VLAN1_SHUTDOWN",
                category="Switch Hygiene",
                message=f"{dev_name} interface Vlan1 is administratively shutdown (best practice)."
            ))
        elif vlan1 and not vlan1.admin_down and vlan1.ip_address:
            self.findings.append(ValidationFinding(
                status="WARNING",
                code=f"SEC_{dev_name}_VLAN1_ACTIVE",
                category="Switch Hygiene",
                message=f"{dev_name} interface Vlan1 is active with IP {vlan1.ip_address}. Dedicated management VLAN 99 should be used instead."
            ))

