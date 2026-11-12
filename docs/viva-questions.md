# SmartBranch360: Viva & Technical Interview Questions & Answers

This guide contains 15 in-depth technical questions and comprehensive answers designed for university project evaluation, viva voce exams, and technical portfolio interviews.

---

### Q1: What is the fundamental architecture of SmartBranch360, and what are its key components?
**Answer:**
SmartBranch360 is an enterprise branch office network architecture modeled in Cisco Packet Tracer. It consists of:
1. **Edge Router (R1 - Cisco 2911):** Acts as the default gateway for four departmental VLANs using Router-on-a-Stick, runs Cisco IOS DHCP pools for dynamic client provisioning, performs Port Address Translation (PAT) overload for outbound simulated Internet access, and filters traffic via extended ACLs.
2. **Distribution/Core Switch (SW1 - Cisco 2960):** Handles 802.1Q trunking to R1 and SW2, and provides access ports for the internal corporate server (VLAN 30) and the Management PC (VLAN 99).
3. **Access Switch (SW2 - Cisco 2960):** Provides access ports for employee workstations (VLAN 10), guest wired ports (VLAN 20), and the Wireless Access Point (VLAN 20).
4. **Simulated ISP Router (ISP - Cisco 2911):** Connects to R1 via point-to-point WAN `203.0.113.0/30` and provides simulated cloud destination `198.51.100.10` to test NAT and routing.
5. **Python Assurance Engine & Web Dashboard:** An automated toolchain that parses Cisco configurations, verifies design intent, audits zero-trust security compliance, and exposes a REST API and React interface.

---

### Q2: What is "Router-on-a-Stick" (ROAS), and why was it chosen over Layer 3 switching in this branch?
**Answer:**
Router-on-a-Stick is a network design where a single physical router interface (e.g., `GigabitEthernet0/0`) is configured with multiple logical subinterfaces using IEEE 802.1Q encapsulation (`encapsulation dot1Q <vlan-id>`). Each subinterface is assigned an IP address that serves as the default gateway for its respective VLAN.
**Why it was chosen:**
- Cisco Catalyst 2960 switches are Layer 2 only switches that cannot route IP traffic.
- Using ROAS avoids requiring costly Layer 3 switches at a small/medium branch office while still allowing controlled inter-VLAN routing and centralizing security ACL enforcement on R1.

---

### Q3: Explain how 802.1Q trunking works between SW1, SW2, and R1.
**Answer:**
IEEE 802.1Q is the industry-standard VLAN tagging protocol. When an Ethernet frame travels across an access link, it has no VLAN tag. When it traverses a trunk link (such as SW2 `Fa0/24` to SW1 `Fa0/24`, or SW1 `Gi0/1` to R1 `Gi0/0`), the switch inserts a 4-byte 802.1Q tag into the Ethernet header containing a 12-bit VLAN Identifier (VID).
In SmartBranch360, trunks are explicitly pruned using:
```cisco
switchport trunk allowed vlan 10,20,30,99
```
This ensures that only traffic belonging to Employee (10), Guest (20), Server (30), and Management (99) VLANs can cross the trunk, reducing broadcast domain spillover.

---

### Q4: How does Port Address Translation (PAT / NAT Overload) function on R1?
**Answer:**
PAT allows multiple internal endpoints with private RFC 1918 addresses (`10.10.0.0/16`) to share a single public IP address (`203.0.113.2` on `GigabitEthernet0/1`).
1. When an employee PC (e.g., `10.10.10.21:49182`) sends a packet to the outside test server (`198.51.100.10:80`), R1 replaces the private source IP with its outside WAN interface IP (`203.0.113.2`) and assigns a unique Layer 4 source port number.
2. R1 stores this state in its NAT translation table (`show ip nat translations`).
3. When the return packet arrives from `198.51.100.10`, R1 checks the destination port, maps it back to `10.10.10.21`, and forwards it to the employee workstation.
4. Overload is configured using:
```cisco
access-list 1 permit 10.10.0.0 0.0.255.255
ip nat inside source list 1 interface GigabitEthernet0/1 overload
```

---

### Q5: Explain the guest isolation security policy and why ACL `GUEST-IN` is applied inbound on `GigabitEthernet0/0.20`.
**Answer:**
The guest isolation policy mandates that guests can access external/Internet services, but must be strictly blocked from corporate assets (Server VLAN 30 and Management VLAN 99).
ACL `GUEST-IN` is an extended IP access list:
```cisco
ip access-list extended GUEST-IN
 deny ip 10.10.20.0 0.0.0.255 10.10.10.0 0.0.0.255
 deny ip 10.10.20.0 0.0.0.255 10.10.30.0 0.0.0.255
 deny ip 10.10.20.0 0.0.0.255 10.10.99.0 0.0.0.255
 permit ip 10.10.20.0 0.0.0.255 any
```
**Why inbound:**
Applying `ip access-group GUEST-IN in` on subinterface `G0/0.20` causes R1 to inspect incoming packets as soon as they enter the router. If a guest tries to reach `10.10.30.10`, R1 drops the packet immediately before wasting CPU cycles doing a routing lookup, adhering to Cisco best practices.

---

### Q6: Why can guests still obtain DHCP leases from R1 if the guest ACL is applied inbound on the guest subinterface?
**Answer:**
When a guest client sends a `DHCPDISCOVER`, it broadcasts to Layer 2 destination `FFFF.FFFF.FFFF` and Layer 3 destination `255.255.255.255:67` with source `0.0.0.0:68`.
The local Cisco IOS DHCP process on R1 intercepts and processes this broadcast locally on the subinterface before transit ACL processing drops it. Furthermore, the ACL only denies packets with source `10.10.20.0/24` destined for internal subnets; DHCP discover packets from `0.0.0.0` or local subnet broadcast are handled directly by the router's DHCP daemon.

---

### Q7: Why are low IP addresses excluded from the DHCP pools on R1?
**Answer:**
R1 uses:
```cisco
ip dhcp excluded-address 10.10.10.1 10.10.10.20
ip dhcp excluded-address 10.10.20.1 10.10.20.20
```
This reserves `.1` through `.20` in each subnet for static infrastructure (default gateways `.1`, network printers, access points, and static servers), ensuring that the DHCP server does not issue these addresses to client workstations, which would cause an IP address conflict (ARP collision).

---

### Q8: What security hardening measures were implemented on the Cisco VTY lines?
**Answer:**
Four distinct hardening controls were implemented across R1, SW1, and SW2:
1. **Telnet Disabled:** Configured with `transport input ssh`, preventing unencrypted plaintext Telnet sessions.
2. **SSH Version 2 Enforced:** Configured with `ip ssh version 2` using an RSA key modulus of 1024 bits.
3. **Local AAA Authentication:** Configured with `login local` and strong secret hashes (`username ... secret ...`).
4. **Management Perimeter ACL:** Configured with `access-class SSH-MGMT in`, where ACL `SSH-MGMT` permits only `10.10.99.0/24` (the Admin PC subnet) and denies all other sources.

---

### Q9: Why is interface `Vlan1` shutdown on switches and routers?
**Answer:**
`Vlan1` is the factory-default management VLAN on Cisco Catalyst switches. If left active and unconfigured, attackers can exploit VLAN hopping attacks (double-tagging or switch spoofing). By creating a dedicated, non-default Management VLAN (`VLAN 99`) and issuing `shutdown` on `interface Vlan1`, the default attack surface is completely neutralized.

---

### Q10: How does the Python Network Assurance Engine work?
**Answer:**
The assurance engine operates using a **closed-loop intent-verification model**:
1. It reads `network_plan.yaml` as the **Source of Truth** (intended state).
2. It parses saved Cisco CLI command outputs (`show running-config`, `show ip interface brief`, `show vlan brief`, `show interfaces trunk`, `show access-lists`, etc.) using regular expressions and tokenizer logic into typed Python dataclasses (`ParsedCiscoDevice`).
3. The `ConfigurationAssuranceEngine` compares the actual state against the intended state (e.g. checking if subinterfaces exist, gateway IPs match, PAT rules are active, trunk allowed lists contain all VLANs).
4. The `SecurityAuditor` validates ACL rule ordering and perimeter isolation.
5. It computes a weighted Network Health Score (0-100%) and generates Terminal, HTML5, or JSON reports.

---

### Q11: What is the difference between "Network Validation" and "Live Telemetry Monitoring"?
**Answer:**
- **Network Validation (Assurance):** Compares network configuration and operational state against declarative business rules and architectural invariants (e.g. "Do all trunks carry VLAN 20?", "Is Telnet disabled?"). It verifies whether the network is configured to deliver its intended service correctly.
- **Live Telemetry Monitoring:** Continuously tracks dynamic metrics such as interface bandwidth utilization, packet drop rates, and link uptime.
- In SmartBranch360, the tool is an **offline assurance engine** that validates imported Packet Tracer configurations, guaranteeing zero false positives without claiming impossible real-time packet capture.

---

### Q12: Walk through Fault Scenario F1: Trunk VLAN Pruning.
**Answer:**
- **Problem:** VLAN 20 was omitted from the allowed VLAN list on SW1 port `FastEthernet0/24` connecting to SW2.
- **Symptom:** Guest devices connected to SW2 or the wireless AP fail to receive a DHCP address and cannot reach their gateway `10.10.20.1`.
- **Evidence:** `show interfaces trunk` on SW1 shows allowed VLANs as `10,30,99` (VLAN 20 missing).
- **Remediation:**
  ```cisco
  SW1(config)# interface FastEthernet0/24
  SW1(config-if)# switchport trunk allowed vlan 10,20,30,99
  ```
- **Verification:** Guest clients renew their lease and successfully ping `10.10.20.1`.

---

### Q13: Walk through Fault Scenario F4: Missing NAT/PAT Overload.
**Answer:**
- **Problem:** The `ip nat inside source list 1 interface GigabitEthernet0/1 overload` statement is missing on R1.
- **Symptom:** Internal clients can ping each other and R1 gateways, but cannot reach the simulated Internet server (`198.51.100.10`).
- **Evidence:** `show ip nat translations` remains empty even while pinging outbound; running-config lacks the PAT command.
- **Remediation:**
  ```cisco
  R1(config)# ip access-list standard 1
  R1(config-std-nacl)# permit 10.10.0.0 0.0.255.255
  R1(config)# ip nat inside source list 1 interface GigabitEthernet0/1 overload
  ```
- **Verification:** Dynamic translations appear in `show ip nat translations`, and pings to `198.51.100.10` succeed.

---

### Q14: How does DNS resolution work in this network architecture?
**Answer:**
- Employee workstations obtain DHCP leases that specify DNS server `10.10.30.10` (the internal Server SRV1).
- SRV1 runs the DNS service with a static A record: `intranet.smartbranch.local -> 10.10.30.10`.
- When an employee types `http://intranet.smartbranch.local` in their browser, their PC queries SRV1, receives `10.10.30.10`, and loads the intranet portal.
- Guest clients receive external DNS `8.8.8.8` via their DHCP pool, preventing them from querying the internal DNS directory.

---

### Q15: If this branch network were migrated to real Cisco hardware, what changes would be required?
**Answer:**
1. **Public IP Range:** The WAN subnet `203.0.113.0/30` (RFC 5737 documentation prefix) would be replaced by a routable public IP block assigned by the ISP.
2. **Next-Generation Firewall / Security Appliance:** The Cisco 2911 router-on-a-stick model would typically be replaced or augmented by a Cisco Catalyst 8000 or Firepower/Meraki MX appliance with stateful deep-packet inspection (DPI) and intrusion prevention (IPS).
3. **Live Automation:** The Python assurance tool would use Netmiko, Scrapli, or RESTCONF/NETCONF with YANG data models to query running configurations directly from devices over secure management interfaces, rather than reading saved text files.

