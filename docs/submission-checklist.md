# SmartBranch360: Final Project Submission Checklist

Use this checklist prior to final submission, academic evaluation, or portfolio publishing.

---

## 1. Network Design & Configuration Checklist
- [x] **Cisco Packet Tracer Binary:** Topology fully designed and saved (`SmartBranch360_Final.pkt`).
- [x] **Router Configuration (R1):**
  - [x] Router-on-a-Stick subinterfaces configured on `G0/0.10`, `G0/0.20`, `G0/0.30`, `G0/0.99`.
  - [x] 802.1Q dot1Q encapsulation verified for all four VLANs.
  - [x] Gateways assigned: `.10.1`, `.20.1`, `.30.1`, `.99.1`.
  - [x] Cisco IOS DHCP pools configured for `EMPLOYEE` and `GUEST`.
  - [x] DHCP excluded addresses configured (`.1` through `.20`).
  - [x] Point-to-Point WAN configured on `G0/1` (`203.0.113.2/30`).
  - [x] Dynamic PAT overload configured on `G0/1` using standard ACL 1.
  - [x] Extended ACL `GUEST-IN` applied inbound on `G0/0.20` blocking Server (30) and Management (99).
  - [x] Cisco SSH version 2 enabled; RSA modulus generated.
  - [x] VTY lines secured with `access-class SSH-MGMT in` and `transport input ssh`.
- [x] **Core Switch Configuration (SW1):**
  - [x] VLANs 10, 20, 30, and 99 created and named.
  - [x] Trunk on `G0/1` to R1 allowing VLANs `10,20,30,99`.
  - [x] Trunk on `Fa0/24` to SW2 allowing VLANs `10,20,30,99`.
  - [x] Access port `Fa0/5` assigned to VLAN 30 (Server).
  - [x] Access port `Fa0/6` assigned to VLAN 99 (Admin PC).
  - [x] Management SVI `Vlan99` configured (`10.10.99.2/24`) with default-gateway `10.10.99.1`.
  - [x] SSH v2 and VTY access-class restriction configured.
- [x] **Access Switch Configuration (SW2):**
  - [x] VLANs 10, 20, 30, and 99 created and named.
  - [x] Trunk on `Fa0/24` to SW1 allowing VLANs `10,20,30,99`.
  - [x] Access ports `Fa0/1 - 4` assigned to VLAN 10 (Employee PCs).
  - [x] Access ports `Fa0/5 - 6` assigned to VLAN 20 (Guest Wired).
  - [x] Access port `Fa0/7` assigned to VLAN 20 (Wireless AP).
  - [x] Management SVI `Vlan99` configured (`10.10.99.3/24`) with default-gateway `10.10.99.1`.
  - [x] SSH v2 and VTY access-class restriction configured.
- [x] **Simulated ISP Router Configuration:**
  - [x] WAN interface `G0/0` configured (`203.0.113.1/30`).
  - [x] Test cloud LAN configured on `G0/1` (`198.51.100.1/24`).

---

## 2. Python Assurance Tool & Tests
- [x] `network_plan.yaml` validated with zero errors.
- [x] All 7 core Cisco show outputs captured in `sample_show_outputs/`.
- [x] Python modules implemented in `assurance_engine/`:
  - [x] `validator.py` (Plan schema, VLAN range, overlap, IPAM duplicate checks)
  - [x] `parser.py` (Cisco running-config and show command tokenizer/parser)
  - [x] `comparator.py` (Closed-loop configuration assurance comparator)
  - [x] `security_audit.py` (Guest isolation, SSH perimeter, AAA hygiene)
  - [x] `fault_detector.py` (Five enterprise failure scenarios & benchmark runner)
  - [x] `reporter.py` (Terminal ANSI, HTML5, and JSON report generator)
  - [x] `server.py` (FastAPI REST backend)
- [x] CLI entrypoint `check_network.py` supports `--plan`, `--show-dir`, `--report`, and `--run-faults`.
- [x] Full automated test suite passing via `pytest` (21/21 tests passed).
- [x] HTML report (`report.html`) and JSON report (`report.json`) generated.

---

## 3. Web Dashboard & REST API
- [x] React + TypeScript + Node.js Express dashboard built in `dashboard/`.
- [x] REST API endpoints responding on `http://localhost:5000/api/...`.
- [x] Production build generated in `dashboard/dist/`.
- [x] All 10 dashboard pages implemented and interactive:
  1. Overview
  2. Network Topology
  3. Device Inventory
  4. VLAN Management
  5. IP Address Management
  6. Security Audit
  7. Configuration Validation
  8. Fault Detection
  9. Assurance Reports
  10. Project Documentation

---

## 4. Documentation & Deliverables
- [x] `README.md` complete with architecture, quickstart, and CLI guide.
- [x] `docs/PROJECT_REPORT.md` comprehensive technical project report.
- [x] `docs/fault-cards.md` five standardized fault scenario cards.
- [x] `docs/demo-script.md` 5-minute timed presentation script.
- [x] `docs/viva-questions.md` 15+ high-impact technical interview questions.
- [x] `docs/test-plan.md` test matrix and evidence checklist.
- [x] `requirements.txt` and `.env.example` verified.

