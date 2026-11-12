"""Unit tests for Cisco Configuration Parser."""

from assurance_engine.parser import CiscoConfigParser


def test_parse_r1_running_config():
    parser = CiscoConfigParser()
    sample_r1 = """
    hostname R1
    version 15.1
    service password-encryption
    ip domain-name smartbranch.local
    ip ssh version 2
    !
    ip dhcp pool EMPLOYEE
     network 10.10.10.0 255.255.255.0
     default-router 10.10.10.1
     dns-server 10.10.30.10
    !
    interface GigabitEthernet0/0.10
     encapsulation dot1Q 10
     ip address 10.10.10.1 255.255.255.0
     ip nat inside
    !
    interface GigabitEthernet0/1
     ip address 203.0.113.2 255.255.255.252
     ip nat outside
    !
    ip nat inside source list 1 interface GigabitEthernet0/1 overload
    ip route 0.0.0.0 0.0.0.0 203.0.113.1
    line vty 0 4
     access-class SSH-MGMT in
     login local
     transport input ssh
    """
    dev = parser.parse_text(sample_r1, default_hostname="R1")
    assert dev.hostname == "R1"
    assert dev.ssh_version == 2
    assert dev.service_password_encryption is True
    assert "GigabitEthernet0/0.10" in dev.interfaces
    sub10 = dev.interfaces["GigabitEthernet0/0.10"]
    assert sub10.vlan_id == 10
    assert sub10.ip_address == "10.10.10.1"
    assert sub10.nat_type == "inside"

    wan = dev.interfaces["GigabitEthernet0/1"]
    assert wan.ip_address == "203.0.113.2"
    assert wan.nat_type == "outside"

    assert len(dev.nat_rules) == 1
    assert dev.nat_rules[0]["overload"] is True
    assert "EMPLOYEE" in dev.dhcp_pools
    assert dev.dhcp_pools["EMPLOYEE"].default_router == "10.10.10.1"
    assert dev.vty_access_class == "SSH-MGMT"
    assert "ssh" in dev.vty_transport_input


def test_parse_switch_vlan_brief():
    parser = CiscoConfigParser()
    sample_vlan = """
    SW1#show vlan brief
    VLAN Name                             Status    Ports
    ---- -------------------------------- --------- -------------------------------
    1    default                          active    Fa0/1
    10   EMPLOYEE                         active    
    20   GUEST                            active    
    30   SERVER                           active    Fa0/5
    99   MANAGEMENT                       active    Fa0/6
    """
    dev = parser.parse_text(sample_vlan, default_hostname="SW1")
    assert 10 in dev.vlans
    assert dev.vlans[10]["name"] == "EMPLOYEE"
    assert 30 in dev.vlans
    assert "Fa0/5" in dev.vlans[30]["ports"]
    assert dev.device_type == "switch"


def test_parse_switch_trunk():
    parser = CiscoConfigParser()
    sample_trunk = """
    SW1#show interfaces trunk
    Port        Mode             Encapsulation  Status        Native vlan
    Fa0/24      on               802.1q         trunking      1
    Gi0/1       on               802.1q         trunking      1

    Port        Vlans allowed on trunk
    Fa0/24      10,20,30,99
    Gi0/1       10,20,30,99
    """
    dev = parser.parse_text(sample_trunk, default_hostname="SW1")
    assert "FastEthernet0/24" in dev.trunks
    assert dev.trunks["FastEthernet0/24"]["allowed_vlans"] == [10, 20, 30, 99]
    assert "GigabitEthernet0/1" in dev.trunks
    assert dev.trunks["GigabitEthernet0/1"]["allowed_vlans"] == [10, 20, 30, 99]

