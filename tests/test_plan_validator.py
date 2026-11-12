"""Unit tests for Network Plan Validator."""

import copy
import pytest
from assurance_engine.validator import NetworkPlanValidator


@pytest.fixture
def base_valid_plan():
    return {
        "site": "SmartBranch360",
        "vlans": [
            {"id": 10, "name": "EMPLOYEE", "subnet": "10.10.10.0/24", "gateway": "10.10.10.1", "dhcp": True},
            {"id": 20, "name": "GUEST", "subnet": "10.10.20.0/24", "gateway": "10.10.20.1", "dhcp": True},
            {"id": 30, "name": "SERVER", "subnet": "10.10.30.0/24", "gateway": "10.10.30.1", "dhcp": False},
            {"id": 99, "name": "MANAGEMENT", "subnet": "10.10.99.0/24", "gateway": "10.10.99.1", "dhcp": False}
        ],
        "devices": {
            "server": {"ip": "10.10.30.10", "vlan": 30},
            "management_pc": {"ip": "10.10.99.10", "vlan": 99},
            "sw1_management": {"ip": "10.10.99.2", "vlan": 99},
            "sw2_management": {"ip": "10.10.99.3", "vlan": 99}
        },
        "trunks": [
            {"device": "SW1", "interface": "GigabitEthernet0/1", "allowed_vlans": [10, 20, 30, 99]},
            {"device": "SW1", "interface": "FastEthernet0/24", "allowed_vlans": [10, 20, 30, 99]},
            {"device": "SW2", "interface": "FastEthernet0/24", "allowed_vlans": [10, 20, 30, 99]}
        ],
        "security": {
            "guest_may_access_internal_vlans": False,
            "ssh_allowed_subnet": "10.10.99.0/24"
        }
    }


def test_valid_plan_passes(base_valid_plan):
    validator = NetworkPlanValidator(base_valid_plan)
    findings = validator.validate_all()
    failures = [f for f in findings if f.status == "FAIL"]
    assert len(failures) == 0


def test_invalid_vlan_id_out_of_range(base_valid_plan):
    plan = copy.deepcopy(base_valid_plan)
    plan["vlans"][0]["id"] = 5000  # Outside 1-4094
    validator = NetworkPlanValidator(plan)
    findings = validator.validate_all()
    failures = [f for f in findings if f.status == "FAIL" and f.code == "PLAN_VLAN_ID_OUT_OF_RANGE"]
    assert len(failures) == 1


def test_duplicate_vlan_id(base_valid_plan):
    plan = copy.deepcopy(base_valid_plan)
    plan["vlans"][1]["id"] = 10  # Duplicate of VLAN 10
    validator = NetworkPlanValidator(plan)
    findings = validator.validate_all()
    failures = [f for f in findings if f.status == "FAIL" and f.code == "PLAN_VLAN_ID_DUPLICATE"]
    assert len(failures) == 1


def test_overlapping_subnets(base_valid_plan):
    plan = copy.deepcopy(base_valid_plan)
    plan["vlans"][1]["subnet"] = "10.10.10.0/24"  # Overlaps with VLAN 10
    validator = NetworkPlanValidator(plan)
    findings = validator.validate_all()
    failures = [f for f in findings if f.status == "FAIL" and f.code == "PLAN_SUBNET_OVERLAP"]
    assert len(failures) >= 1


def test_gateway_outside_subnet(base_valid_plan):
    plan = copy.deepcopy(base_valid_plan)
    plan["vlans"][0]["gateway"] = "192.168.1.1"  # Not inside 10.10.10.0/24
    validator = NetworkPlanValidator(plan)
    findings = validator.validate_all()
    failures = [f for f in findings if f.status == "FAIL" and f.code == "PLAN_GATEWAY_OUTSIDE_SUBNET"]
    assert len(failures) == 1


def test_duplicate_device_ip_conflict(base_valid_plan):
    plan = copy.deepcopy(base_valid_plan)
    plan["devices"]["another_server"] = {"ip": "10.10.30.10", "vlan": 30}  # Collides with server
    validator = NetworkPlanValidator(plan)
    findings = validator.validate_all()
    failures = [f for f in findings if f.status == "FAIL" and f.code == "PLAN_DEVICE_IP_CONFLICT"]
    assert len(failures) == 1


def test_device_referencing_undefined_vlan(base_valid_plan):
    plan = copy.deepcopy(base_valid_plan)
    plan["devices"]["rogue_device"] = {"ip": "172.16.1.10", "vlan": 55}
    validator = NetworkPlanValidator(plan)
    findings = validator.validate_all()
    failures = [f for f in findings if f.status == "FAIL" and f.code == "PLAN_DEVICE_UNDEFINED_VLAN"]
    assert len(failures) == 1


def test_guest_isolation_security_policy_fail(base_valid_plan):
    plan = copy.deepcopy(base_valid_plan)
    plan["security"]["guest_may_access_internal_vlans"] = True
    validator = NetworkPlanValidator(plan)
    findings = validator.validate_all()
    failures = [f for f in findings if f.status == "FAIL" and f.code == "PLAN_GUEST_ISOLATION_DISABLED"]
    assert len(failures) == 1
