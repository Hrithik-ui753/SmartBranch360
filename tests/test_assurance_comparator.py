"""Unit tests for Configuration Assurance Engine."""

from assurance_engine.parser import CiscoConfigParser
from assurance_engine.comparator import ConfigurationAssuranceEngine


def test_assurance_detects_missing_subinterface():
    plan = {
        "vlans": [
            {"id": 10, "name": "EMPLOYEE", "subnet": "10.10.10.0/24", "gateway": "10.10.10.1"},
            {"id": 20, "name": "GUEST", "subnet": "10.10.20.0/24", "gateway": "10.10.20.1"}
        ]
    }
    # R1 only has VLAN 10 configured, missing VLAN 20
    r1_text = """
    hostname R1
    interface GigabitEthernet0/0.10
     encapsulation dot1Q 10
     ip address 10.10.10.1 255.255.255.0
     ip nat inside
    """
    parser = CiscoConfigParser()
    r1 = parser.parse_text(r1_text, "R1")
    comparator = ConfigurationAssuranceEngine(plan, {"R1": r1})
    findings = comparator.verify_all()
    missing_vlan20 = [f for f in findings if f.code == "ASSURE_SUBIFACE_MISSING_VLAN_20"]
    assert len(missing_vlan20) == 1
    assert missing_vlan20[0].status == "FAIL"


def test_assurance_detects_wrong_gateway_ip():
    plan = {
        "vlans": [
            {"id": 10, "name": "EMPLOYEE", "subnet": "10.10.10.0/24", "gateway": "10.10.10.1"}
        ]
    }
    r1_text = """
    hostname R1
    interface GigabitEthernet0/0.10
     encapsulation dot1Q 10
     ip address 10.10.10.254 255.255.255.0
     ip nat inside
    """
    parser = CiscoConfigParser()
    r1 = parser.parse_text(r1_text, "R1")
    comparator = ConfigurationAssuranceEngine(plan, {"R1": r1})
    findings = comparator.verify_all()
    mismatch = [f for f in findings if f.code == "ASSURE_GATEWAY_IP_MISMATCH_VLAN_10"]
    assert len(mismatch) == 1
    assert mismatch[0].status == "FAIL"


def test_assurance_detects_missing_nat():
    plan = {"vlans": []}
    r1_text = """
    hostname R1
    interface GigabitEthernet0/1
     ip address 203.0.113.2 255.255.255.252
    """
    parser = CiscoConfigParser()
    r1 = parser.parse_text(r1_text, "R1")
    comparator = ConfigurationAssuranceEngine(plan, {"R1": r1})
    findings = comparator.verify_all()
    no_nat = [f for f in findings if f.code == "ASSURE_NAT_OVERLOAD_MISSING"]
    assert len(no_nat) == 1
    assert no_nat[0].status == "FAIL"

