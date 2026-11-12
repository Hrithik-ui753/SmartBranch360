"""Unit tests for Security Audit Engine."""

from assurance_engine.parser import CiscoConfigParser
from assurance_engine.security_audit import SecurityAuditor


def test_guest_isolation_failure_when_no_acl():
    r1_text = """
    hostname R1
    interface GigabitEthernet0/0.20
     encapsulation dot1Q 20
     ip address 10.10.20.1 255.255.255.0
    """
    parser = CiscoConfigParser()
    r1 = parser.parse_text(r1_text, "R1")
    auditor = SecurityAuditor({"R1": r1})
    findings = auditor.audit_all()
    no_acl = [f for f in findings if f.code == "SEC_GUEST_ACL_NOT_APPLIED"]
    assert len(no_acl) == 1
    assert no_acl[0].status == "FAIL"


def test_guest_isolation_failure_when_acl_missing_deny_server():
    r1_text = """
    hostname R1
    interface GigabitEthernet0/0.20
     encapsulation dot1Q 20
     ip address 10.10.20.1 255.255.255.0
     ip access-group GUEST-IN in
    !
    ip access-list extended GUEST-IN
     permit ip 10.10.20.0 0.0.0.255 any
    """
    parser = CiscoConfigParser()
    r1 = parser.parse_text(r1_text, "R1")
    auditor = SecurityAuditor({"R1": r1})
    findings = auditor.audit_all()
    leak_server = [f for f in findings if f.code == "SEC_GUEST_CAN_REACH_SERVER"]
    assert len(leak_server) == 1
    assert leak_server[0].status == "FAIL"


def test_ssh_perimeter_violation_when_open():
    r1_text = """
    hostname R1
    line vty 0 4
     login local
     transport input ssh
    """
    parser = CiscoConfigParser()
    r1 = parser.parse_text(r1_text, "R1")
    auditor = SecurityAuditor({"R1": r1})
    findings = auditor.audit_all()
    unrestricted = [f for f in findings if f.code == "SEC_R1_VTY_UNRESTRICTED"]
    assert len(unrestricted) == 1
    assert unrestricted[0].status == "FAIL"

