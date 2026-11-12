# SmartBranch360: Secure Enterprise Branch Office Network & Automated Assurance Platform

**Comprehensive Technical Project Report & Portfolio Specification**

---

## 1. Executive Abstract

Modern enterprise networking demands both robust infrastructure design and automated assurance. **SmartBranch360** is an enterprise-grade branch-office network architecture developed in Cisco Packet Tracer, paired with a custom **Python 3.12 Network Assurance & Security Engine** and a **React/TypeScript Web Dashboard**.

SmartBranch360 provides secure departmental segmentation across four dedicated IEEE 802.1Q Virtual Local Area Networks (VLANs: Employee, Guest, Server, Management). Inter-VLAN routing is performed via a Cisco 2911 router-on-a-stick topology, while outward simulated Internet connectivity is established via Port Address Translation (PAT). Security is strictly enforced through zero-trust access control lists (ACLs) isolating guest traffic from corporate servers and management infrastructure, combined with Cisco SSH version 2 perimeter restrictions.

To bridge the gap between design intent and operational reality, the platform features an automated closed-loop assurance engine that parses Cisco IOS CLI command outputs (`show running-config`, `show ip interface brief`, `show vlan brief`, `show interfaces trunk`, `show ip route`, `show ip nat statistics`, `show access-lists`, `show ip dhcp binding`), validates them against a single source-of-truth YAML specification, audits security posture, automatically diagnoses five standard branch failure scenarios, and exposes results via a RESTful API and responsive dashboard.

---

## 2. Problem Statement & Motivation

Traditional enterprise branch office networks suffer from several critical operational and security vulnerabilities:
1. **Flat Network Architectures:** Unsegmented networks expose sensitive corporate assets, payroll servers, and network management equipment to guest and untrusted endpoints.
2. **Configuration Drift:** Manual device configuration leads to inconsistencies between documented designs and actual router/switch configs (e.g., VLAN trunk pruning errors, incorrect subnet masks, missing NAT overload statements).
3. **Lack of Automated Verification:** Network engineers historically rely on manual `ping` or `traceroute` spot-checks, which cannot systematically prove compliance with zero-trust security policies or detect subtle syntax errors.
4. **Vulnerable Management Protocols:** Legacy networks frequently leave Telnet or unencrypted HTTP management active on VTY lines, exposing administrative credentials to eavesdropping and lateral movement.

SmartBranch360 solves these challenges by combining defense-in-depth network architecture with programmatic, continuous configuration assurance.

---

## 3. Project Objectives

- **Architectural Segmentation:** Design and deploy 4 distinct VLANs isolating Employee workstations, Guest laptops, Corporate Servers, and Administrative PC management.
- **Dynamic Addressing & Routing:** Implement on-router Cisco IOS DHCP scopes for dynamic client provisioning and high-performance inter-VLAN routing using 802.1Q subinterfaces.
- **Internet Edge & NAT/PAT:** Configure point-to-point WAN connectivity to an upstream ISP and implement Port Address Translation (PAT) overload for private IPv4 conservation.
- **Defense-in-Depth Security:** Enforce extended inbound ACLs preventing guest lateral movement, eliminate Telnet in favor of SSH version 2, and restrict VTY administration strictly to the Management VLAN.
- **Closed-Loop Python Assurance:** Develop a modular Python tool to validate YAML blueprints, parse Cisco CLI outputs, compare actual state to intent, and calculate an overall network health score.
- **Automated Fault Diagnosis:** Automate the detection and remediation generation for 5 common enterprise failure modes.
- **Full-Stack Visualization:** Deliver a responsive React/Node.js web dashboard and REST API providing interactive topology visualization and audit reporting.

---

## 4. System Architecture & Network Topology

### 4.1 Topology Diagram

```
                              +--------------------------+
                              |   Simulated ISP Router   |
                              |      (Cisco 2911)        |
                              | G0/0: 203.0.113.1/30     |
                              | G0/1: 198.51.100.1/24    |
                              +-------------+------------+
                                            |
                                 WAN Link   |  203.0.113.0/30
                                            |
                              +-------------+------------+
                              |    R1 Branch Gateway     |
                              |      (Cisco 2911)        |
                              | G0/1: 203.0.113.2/30     |
                              | G0/0: Router-on-a-Stick  |
                              +-------------+------------+
                                            |
                              802.1Q Trunk  |  Allowed: 10,20,30,99
                               (G0/0-G0/1)  |
                              +-------------+------------+
                              |     SW1 Core Switch      |
                              |  (Cisco Catalyst 2960)   |
                              | SVI Vlan99: 10.10.99.2   |
                              +------+-------------+-----+
                                     |             |
                        FastEth0/5   |             |  FastEth0/6
                         (VLAN 30)   |             |   (VLAN 99)
                                     |             |
                         +-----------+--+       +--+-----------+
                         | SRV1 Server  |       | Admin Jump PC|
                         | 10.10.30.10  |       | 10.10.99.10  |
                         +--------------+       +--------------+
                                     |
                       802.1Q Trunk  |  Fa0/24 - Fa0/24
                                     |
                              +------+-------------------+
                              |    SW2 Access Switch     |
                              |  (Cisco Catalyst 2960)   |
                              | SVI Vlan99: 10.10.99.3   |
                              +------+-------------+-----+
                                     |             |
                       FastEth0/1-4  |             |  FastEth0/7
                         (VLAN 10)   |             |   (VLAN 20)
                                     |             |
                         +-----------+--+       +--+-----------+
                         | Employee PCs |       | Wireless AP1 |
                         | (DHCP Pool)  |       | & Guest PCs  |
                         +--------------+       +--------------+
```

### 4.2 Hardware & Device Allocation

| Device | Model | Role | Management / Physical Addressing |
|---|---|---|---|
| **R1** | Cisco 2911 ISR | Branch Gateway, Inter-VLAN Router, DHCP Server, PAT | WAN: 203.0.113.2/30, Subinterfaces: .10, .20, .30, .99 |
| **SW1** | Cisco Catalyst 2960-24TT | Distribution Switch, Server Farm Aggregation | SVI Vlan99: 10.10.99.2/24, Default-Gateway: 10.10.99.1 |
| **SW2** | Cisco Catalyst 2960-24TT | Access Switch, End-User Workstation & AP Ports | SVI Vlan99: 10.10.99.3/24, Default-Gateway: 10.10.99.1 |
| **ISP** | Cisco 2911 ISR | Simulated Cloud Provider Gateway | WAN: 203.0.113.1/30, Simulated Internet LAN: 198.51.100.1/24 |
| **SRV1** | Server-PT | Enterprise DNS & Intranet Web Portal | Static: 10.10.30.10/24, Gateway: 10.10.30.1 |
| **Admin PC** | PC-PT | Authorized Network Administration Jump Host | Static: 10.10.99.10/24, Gateway: 10.10.99.1 |
| **AP1** | WAP-PT | 802.11n Wireless Access Point (SSID: SmartBranch-Guest) | Bridged on SW2 Fa0/7 in Access VLAN 20 |

---

## 5. IP Addressing & Subnet Architecture (IPAM)

The IP address allocation follows RFC 1918 private addressing guidelines, organized as contiguous `/24` subnets carved from `10.10.0.0/16`:

| VLAN ID | Department / Scope | Subnet Prefix | Netmask | Default Gateway | Usable Range | Static Reservations | DHCP Pool Range |
|---|---|---|---|---|---|---|---|
| **10** | EMPLOYEE | `10.10.10.0/24` | `255.255.255.0` | `10.10.10.1` | .1 - .254 | .1 - .20 (Excluded) | .21 - .254 |
| **20** | GUEST | `10.10.20.0/24` | `255.255.255.0` | `10.10.20.1` | .1 - .254 | .1 - .20 (Excluded) | .21 - .254 |
| **30** | SERVER | `10.10.30.0/24` | `255.255.255.0` | `10.10.30.1` | .1 - .254 | `10.10.30.10` (SRV1) | None (Static) |
| **99** | MANAGEMENT | `10.10.99.0/24` | `255.255.255.0` | `10.10.99.1` | .1 - .254 | .2 (SW1), .3 (SW2), .10 (Admin) | None (Static) |
| **WAN** | Point-to-Point WAN | `203.0.113.0/30` | `255.255.255.252` | `203.0.113.1` | .1 - .2 | .1 (ISP), .2 (R1) | Point-to-Point |

---

## 6. Detailed Technical Explanations

### 6.1 Router-on-a-Stick (802.1Q Subinterfaces)
Because the Cisco 2911 router has a limited number of physical GigabitEthernet ports, trunking over physical port `GigabitEthernet0/0` is employed. Physical port `G0/0` is enabled with `no shutdown` and no IP address. Four virtual subinterfaces (`G0/0.10`, `G0/0.20`, `G0/0.30`, `G0/0.99`) are created:
- Each subinterface is assigned IEEE 802.1Q encapsulation with the respective VLAN ID:
  ```cisco
  interface GigabitEthernet0/0.10
   encapsulation dot1Q 10
   ip address 10.10.10.1 255.255.255.0
   ip nat inside
  ```
- This architecture enables R1 to act as the default gateway for all branch subnets while conserving physical ports.

### 6.2 Port Address Translation (PAT / NAT Overload)
Branch devices use private RFC 1918 addresses (`10.10.0.0/16`) which are unroutable on the global public Internet.
- **Inside Interfaces:** Configured on all four subinterfaces (`G0/0.10`, `G0/0.20`, `G0/0.30`, `G0/0.99`).
- **Outside Interface:** Configured on WAN port `GigabitEthernet0/1`.
- **NAT Overload Rule:** Standard access-list 1 permits `10.10.0.0 0.0.255.255`, and R1 translates outbound connections onto the single WAN IP `203.0.113.2` using Layer 4 TCP/UDP ports:
  ```cisco
  access-list 1 permit 10.10.0.0 0.0.255.255
  ip nat inside source list 1 interface GigabitEthernet0/1 overload
  ```

### 6.3 Access Control Lists & Zero-Trust Guest Isolation
To maintain strict enterprise security, Guest users connected to VLAN 20 (wired or via wireless AP) must not reach internal confidential assets.
- An extended access list named `GUEST-IN` is applied inbound on `GigabitEthernet0/0.20`:
  ```cisco
  ip access-list extended GUEST-IN
   deny ip 10.10.20.0 0.0.0.255 10.10.10.0 0.0.0.255
   deny ip 10.10.20.0 0.0.0.255 10.10.30.0 0.0.0.255
   deny ip 10.10.20.0 0.0.0.255 10.10.99.0 0.0.0.255
   permit ip 10.10.20.0 0.0.0.255 any
  ```
- **Execution Order:** Denies to Employee, Server, and Management subnets are evaluated first. If traffic is bound for the outside Internet, it matches the final `permit any` rule.
- Applying this inbound ensures unauthorized packets are dropped immediately at ingress, saving router CPU and routing table lookup time.

### 6.4 SSH Version 2 Management Perimeter Hardening
To prevent eavesdropping and credential compromise:
- Insecure Telnet is completely eliminated across R1, SW1, and SW2:
  ```cisco
  ip ssh version 2
  line vty 0 4
   access-class SSH-MGMT in
   login local
   transport input ssh
  ```
- Access-list `SSH-MGMT` permits connections **only** from `10.10.99.0/24` (Admin PC subnet) and terminates with an implicit `deny any`. Any SSH connection attempted from Employee (VLAN 10) or Guest (VLAN 20) is immediately rejected.

---

## 7. Python Network Assurance Engine Architecture

The Python assurance engine (`assurance_engine/`) is structured into five decoupled modules:

```
                          network_plan.yaml
                                 |
                                 v
                     +-----------------------+
                     | NetworkPlanValidator  |
                     +-----------+-----------+
                                 |
  Cisco Show Outputs             | Validated Plan
          |                      v
          v          +-----------------------+
  +---------------+  | ConfigurationAssurance |
  | CiscoParser   |->|        Engine         |
  +---------------+  +-----------+-----------+
          |                      |
          +--------------------->|
          |                      v
          |          +-----------------------+
          +--------->|    SecurityAuditor    |
          |          +-----------+-----------+
          |                      |
          v                      v
  +---------------+  +-----------------------+
  | FaultDetector |  |   ReportGenerator     |
  +---------------+  +-----------+-----------+
                                 |
                     +-----------+-----------+
                     | Terminal | HTML | JSON|
                     +-----------------------+
```

### Module Breakdown:
1. **NetworkPlanValidator (`validator.py`):** Enforces schema integrity, valid 802.1Q ranges (1-4094), RFC subnet parsing, gateway usability, duplicate IP detection, and security policy prerequisites.
2. **CiscoConfigParser (`parser.py`):** Ingests Cisco IOS running-configs and operational outputs (`show ip interface brief`, `show vlan brief`, `show interfaces trunk`, `show ip route`, `show ip nat statistics`, `show access-lists`, `show ip dhcp binding`) and transforms them into strongly-typed object representations.
3. **ConfigurationAssuranceEngine (`comparator.py`):** Closed-loop comparator that verifies actual device state against planned state. Enforces strict zero-false-positive assurance rules.
4. **SecurityAuditor (`security_audit.py`):** Deep inspection of guest microsegmentation, VTY access perimeter ACLs, transport input SSH enforcement, and AAA credential encryption.
5. **FaultDetector (`fault_detector.py`):** Automated diagnosis and corrective action generator for five standard enterprise failure modes.
6. **ReportGenerator (`reporter.py`):** Computes the weighted Network Health Score (0-100%) and formats terminal ANSI, self-contained HTML5, and structured JSON output.

---

## 8. Five Standard Enterprise Fault Scenarios

| Fault ID | Fault Name | Affected Device | Root Cause & Detection | Remediation CLI Action |
|---|---|---|---|---|
| **F1** | Trunk VLAN Pruning | SW1 (Fa0/24) | VLAN 20 omitted from `allowed vlan` list on trunk link. Guest packets partitioned between switches. | `SW1(config-if)# switchport trunk allowed vlan 10,20,30,99` |
| **F2** | Missing DHCP Pool | R1 Router | Scope `EMPLOYEE` omitted from DHCP pool table. Workstations receive APIPA `169.254.x.x`. | `R1(config)# ip dhcp pool EMPLOYEE`<br>`R1(dhcp-config)# network 10.10.10.0 255.255.255.0`<br>`R1(dhcp-config)# default-router 10.10.10.1` |
| **F3** | Subinterface Gateway Error | R1 (Gi0/0.10) | Gateway IP set to `10.10.10.254` instead of `10.10.10.1`. ARP fails for default route. | `R1(config-subif)# ip address 10.10.10.1 255.255.255.0` |
| **F4** | Missing NAT / PAT Overload | R1 Router | `ip nat inside source ... overload` missing. Outbound private RFC 1918 traffic dropped by ISP. | `R1(config)# ip nat inside source list 1 interface GigabitEthernet0/1 overload` |
| **F5** | Broken Guest ACL | R1 (ACL GUEST-IN) | Missing deny statements for Server & Mgmt before permit any. Guest can access confidential server. | `R1(config-ext-nacl)# 10 deny ip 10.10.20.0 0.0.0.255 10.10.30.0 0.0.0.255`<br>`R1(config-ext-nacl)# 20 deny ip 10.10.20.0 0.0.0.255 10.10.99.0 0.0.0.255`<br>`R1(config-ext-nacl)# 30 permit ip 10.10.20.0 0.0.0.255 any` |

---

## 9. Verification & Automated Test Results

Automated regression test suite executed via `pytest`:

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.2.0
rootdir: D:\CN\SmartBranch360
testpaths: tests
collected 21 items

tests/test_assurance_comparator.py::test_assurance_detects_missing_subinterface PASSED
tests/test_assurance_comparator.py::test_assurance_detects_wrong_gateway_ip PASSED
tests/test_assurance_comparator.py::test_assurance_detects_missing_nat PASSED
tests/test_cisco_parser.py::test_parse_r1_running_config PASSED
tests/test_cisco_parser.py::test_parse_switch_vlan_brief PASSED
tests/test_cisco_parser.py::test_parse_switch_trunk PASSED
tests/test_cli_and_reporter.py::test_reporter_health_score_calculation PASSED
tests/test_cli_and_reporter.py::test_reporter_json_generation PASSED
tests/test_cli_and_reporter.py::test_reporter_html_generation PASSED
tests/test_fault_detector.py::test_detect_all_5_fault_benchmarks PASSED
tests/test_plan_validator.py::test_valid_plan_passes PASSED
tests/test_plan_validator.py::test_invalid_vlan_id_out_of_range PASSED
tests/test_plan_validator.py::test_duplicate_vlan_id PASSED
tests/test_plan_validator.py::test_overlapping_subnets PASSED
tests/test_plan_validator.py::test_gateway_outside_subnet PASSED
tests/test_plan_validator.py::test_duplicate_device_ip_conflict PASSED
tests/test_plan_validator.py::test_device_referencing_undefined_vlan PASSED
tests/test_plan_validator.py::test_guest_isolation_security_policy_fail PASSED
tests/test_security_audit.py::test_guest_isolation_failure_when_no_acl PASSED
tests/test_security_audit.py::test_guest_isolation_failure_when_acl_missing_deny_server PASSED
tests/test_security_audit.py::test_ssh_perimeter_violation_when_open PASSED

============================= 21 passed in 0.11s ==============================
```

---

## 10. REST API Specification

| Method | Endpoint | Description | Sample Response Key |
|---|---|---|---|
| `GET` | `/api/health` | Service health and gateway status | `{"status": "ok", "version": "2.0.0"}` |
| `GET` | `/api/network/overview` | Network topology metadata, VLANs, WAN status | `{"health_score": 100, "vlans": [...]}` |
| `GET` | `/api/network/devices` | Parsed configurations and active interfaces | `{"R1": {...}, "SW1": {...}}` |
| `POST` | `/api/validate/plan` | Validates `network_plan.yaml` against schema | `{"total": 6, "passed": 6, "failed": 0}` |
| `POST` | `/api/validate/config` | Closed-loop assurance comparing YAML to Cisco configs | `{"total": 33, "passed": 33, "failed": 0}` |
| `POST` | `/api/security/audit` | Audits guest isolation and perimeter hardening | `{"total": 15, "passed": 15, "failed": 0}` |
| `POST` | `/api/faults/test` | Runs automated 5-fault diagnostic benchmark | `{"success": true, "faults": [...]}` |
| `GET` | `/api/reports/latest` | Consolidated health score and audit payload | `{"health_score": 100, "metrics": {...}}` |

---

## 11. Limitations & Real-World Translation

1. **Simulation Environment:** The physical and data-link layers are modeled inside Cisco Packet Tracer. In physical deployments, Cisco DNA Center / Catalyst Center or Netmiko / Scrapli would connect via NETCONF or SSH to stream live telemetry.
2. **Simulated Internet:** Outbound WAN testing targets `198.51.100.10` on the simulated ISP router. This accurately exercises PAT overload and IP routing tables without exposing lab endpoints to public networks.
3. **Offline Assurance Paradigm:** Because Packet Tracer does not expose an open external TCP telemetry socket, the assurance engine operates on imported configuration and show-command outputs. This mirrors real-world offline compliance auditing and network digital twin validation.

---

## 12. Conclusion

The **SmartBranch360** project successfully demonstrates a full-lifecycle network automation and cybersecurity engineering workflow. By combining verified Cisco Packet Tracer network architectures with automated Python 3.12 configuration assurance, zero-trust security auditing, and an interactive modern web dashboard, SmartBranch360 delivers a complete, production-ready project suitable for university capstone evaluation and technical portfolio review.

