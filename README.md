# SmartBranch360: Secure Enterprise Branch Office Network & Automated Assurance Platform

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev/)
[![Node.js](https://img.shields.io/badge/Node.js-20+-green.svg)](https://nodejs.org/)
[![Cisco](https://img.shields.io/badge/Cisco-Packet%20Tracer%208.2+-049fd9.svg)](https://www.netacad.com/courses/packet-tracer)
[![Tests](https://img.shields.io/badge/Tests-21%20Passed-brightgreen.svg)]()
[![Health Score](https://img.shields.io/badge/Health%20Score-100%25-success.svg)]()

SmartBranch360 is an enterprise-grade branch-office network architecture modeled in **Cisco Packet Tracer**, integrated with a modular **Python 3.12 Network Assurance & Security Engine**, and monitored via a modern **React/TypeScript Web Dashboard** powered by an **Express / FastAPI REST API**.

---

## 📑 Table of Contents
- [1. Architecture & VLAN Segmentation](#1-architecture--vlan-segmentation)
- [2. Verified Network Specifications](#2-verified-network-specifications)
- [3. Key Features](#3-key-features)
- [4. Project Structure](#4-project-structure)
- [5. Quickstart & Installation](#5-quickstart--installation)
- [6. Python Assurance CLI Usage](#6-python-assurance-cli-usage)
- [7. Web Dashboard & REST API](#7-web-dashboard--rest-api)
- [8. Automated Fault Detection & Scenarios](#8-automated-fault-detection--scenarios)
- [9. Automated Pytest Suite](#9-automated-pytest-suite)
- [10. Documentation Index](#10-documentation-index)

---

## 1. Architecture & VLAN Segmentation

SmartBranch360 implements strict departmental segmentation across four dedicated IEEE 802.1Q VLANs:

```
                              +--------------------------+
                              |   Simulated ISP Router   |
                              |   WAN: 203.0.113.1/30    |
                              |   Cloud: 198.51.100.1/24 |
                              +-------------+------------+
                                            |
                                 WAN Link   |  203.0.113.0/30
                                            |
                              +-------------+------------+
                              |    R1 Branch Gateway     |
                              | G0/1: 203.0.113.2 (PAT)  |
                              | G0/0: Router-on-a-Stick  |
                              +-------------+------------+
                                            |
                              802.1Q Trunk  |  Allowed: 10,20,30,99
                                            |
                              +-------------+------------+
                              |     SW1 Core Switch      |
                              |  SVI Vlan99: 10.10.99.2  |
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
                              |  SVI Vlan99: 10.10.99.3   |
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

### VLAN Architecture Table

| VLAN | Department | Subnet Prefix | Netmask | Default Gateway | Allocation Mode | Security Profile |
|---|---|---|---|---|---|---|
| **10** | EMPLOYEE | `10.10.10.0/24` | `255.255.255.0` | `10.10.10.1` | DHCP (R1 Pool) | Corporate Workstations; access to Server & Internet |
| **20** | GUEST | `10.10.20.0/24` | `255.255.255.0` | `10.10.20.1` | DHCP (R1 Pool) | **Isolated**: Blocked from Server (30) & Mgmt (99); Outbound PAT allowed |
| **30** | SERVER | `10.10.30.0/24` | `255.255.255.0` | `10.10.30.1` | Static (`.10`) | Enterprise DNS & Intranet Web Portal |
| **99** | MANAGEMENT | `10.10.99.0/24` | `255.255.255.0` | `10.10.99.1` | Static (`.2, .3, .10`)| Admin Jump PC; exclusive SSH VTY access to R1, SW1, SW2 |

---

## 2. Verified Network Specifications

- **Router-on-a-Stick:** Configured on R1 `G0/0.10`, `G0/0.20`, `G0/0.30`, and `G0/0.99`.
- **Port Address Translation (PAT):** Overload configured on R1 `GigabitEthernet0/1` multiplexing `10.10.0.0/16` onto WAN IP `203.0.113.2`.
- **Zero-Trust Guest Isolation:** Extended ACL `GUEST-IN` applied inbound on `GigabitEthernet0/0.20`.
- **SSH Hardening:** Cisco SSH version 2 strictly enforced; VTY lines protected via `access-class SSH-MGMT in` and `transport input ssh` (Telnet disabled).
- **Default VLAN 1 Hardening:** Interface `Vlan1` administratively shutdown across all devices.

---

## 3. Key Features

- **Closed-Loop Assurance Engine:** Compares actual Cisco running-configs and show commands against `network_plan.yaml`.
- **Zero False-Positive Verification:** 54 independent validation assertions evaluated across schema, IPAM, switching, routing, NAT, and security.
- **Automated Fault Detection:** Identifies root causes, CLI evidence, and remediation commands for 5 standard branch failure scenarios.
- **Multi-Format Reporting:** Generates colorized Terminal ANSI output, interactive self-contained HTML5 reports, and structured JSON payloads.
- **Full-Stack Web Dashboard:** 10-page responsive React/TypeScript application with interactive SVG network topology and live fault testing.
- **Enterprise REST API:** Dual-backend support (Node.js Express on port 5000 and Python FastAPI on port 8000).

---

## 4. Project Structure

```
SmartBranch360/
├── check_network.py                 # Core CLI entry point for Network Assurance
├── network_plan.yaml               # Architectural Source of Truth specification
├── requirements.txt                # Python dependencies (PyYAML, pytest, FastAPI, etc.)
├── pytest.ini                      # Pytest configuration
├── report.html                     # Generated standalone HTML5 assurance report
├── report.json                     # Generated structured JSON assurance report
├── SmartBranch360_Final.pkt        # Cisco Packet Tracer network topology binary
│
├── assurance_engine/               # Core Python Assurance Engine
│   ├── __init__.py
│   ├── validator.py                # Network Plan Validator (schema, VLAN, IPAM)
│   ├── parser.py                   # Cisco Configuration & Show Output Parser
│   ├── comparator.py               # Closed-Loop Configuration Assurance Engine
│   ├── security_audit.py           # Zero-Trust Security & Perimeter Auditor
│   ├── fault_detector.py           # Automated Fault Detection & Diagnostic Suite
│   ├── reporter.py                 # Terminal, HTML, and JSON Report Generator
│   └── server.py                   # FastAPI REST API Backend
│
├── sample_show_outputs/            # Captured Cisco CLI show command outputs
│   ├── R1-show-running-config.txt
│   ├── R1-show-ip-interface-brief.txt
│   ├── R1-show-ip-route.txt
│   ├── R1-show-access-lists.txt
│   ├── R1-show-ip-nat-statistics.txt
│   ├── R1-show-ip-nat-translations.txt
│   ├── R1-show-ip-dhcp-binding.txt
│   ├── SW1-show-running-config.txt
│   ├── SW1-show-vlan-brief.txt
│   ├── SW1-show-interfaces-trunk.txt
│   ├── SW2-show-running-config.txt
│   ├── SW2-show-vlan-brief.txt
│   ├── SW2-show-interfaces-trunk.txt
│   ├── ISP-show-running-config.txt
│   └── faults/                     # Fault scenario configuration fixtures (F1 - F5)
│
├── configs/                        # Production Cisco IOS configuration scripts
│   ├── R1-router.txt
│   ├── SW1-core-switch.txt
│   ├── SW2-access-switch.txt
│   └── ISP-router.txt
│
├── dashboard/                      # Modern React/TypeScript & Express Web Dashboard
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx                 # 10-page responsive dashboard & interactive topology
│   │   └── index.css               # Modern enterprise dark styling system
│   ├── server/
│   │   └── server.cjs              # Node.js Express REST API Gateway
│   └── dist/                       # Production optimized build bundle
│
├── tests/                          # Automated Pytest suite (21 unit/integration tests)
│   ├── test_plan_validator.py
│   ├── test_cisco_parser.py
│   ├── test_assurance_comparator.py
│   ├── test_security_audit.py
│   ├── test_fault_detector.py
│   └── test_cli_and_reporter.py
│
└── docs/                           # Comprehensive Academic & Portfolio Documentation
    ├── PROJECT_REPORT.md           # Full technical report & architectural deep dive
    ├── fault-cards.md              # 5 standardized fault scenario diagnosis cards
    ├── demo-script.md              # 5-minute timed presentation script
    ├── viva-questions.md           # 15+ high-impact viva interview questions & answers
    ├── submission-checklist.md     # Final submission verification checklist
    ├── test-plan.md                # Test execution matrix and verification evidence
    └── implementation-guide.md     # Step-by-step device cabling and setup guide
```

---

## 5. Quickstart & Installation

### Prerequisites
- Python 3.10+ (Tested on Python 3.12)
- Node.js 18+ (Tested on Node.js 26)
- Cisco Packet Tracer 8.0+

### Step 1: Install Python Dependencies
```powershell
python -m pip install -r requirements.txt
```

### Step 2: Install Dashboard Dependencies & Build
```powershell
cd dashboard
npm install
npm run build
cd ..
```

---

## 6. Python Assurance CLI Usage

The CLI tool can be executed directly from PowerShell or Command Prompt:

```powershell
# 1. Validate the blueprint plan:
python check_network.py --plan network_plan.yaml

# 2. Run full closed-loop assurance against saved Cisco outputs:
python check_network.py --plan network_plan.yaml --show-dir sample_show_outputs

# 3. Run assurance and export interactive HTML5 report:
python check_network.py --plan network_plan.yaml --show-dir sample_show_outputs --report html --output-file report.html

# 4. Run assurance and export structured JSON:
python check_network.py --plan network_plan.yaml --show-dir sample_show_outputs --report json --output-file report.json

# 5. Run the automated 5-fault diagnostic benchmark:
python check_network.py --run-faults
```

---

## 7. Web Dashboard & REST API

### Starting the Node.js Express Server & Dashboard
```powershell
cd dashboard
npm start
```
The server will start at: **`http://localhost:5000`**

### REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check & service metadata |
| `GET` | `/api/network/overview` | Network topology, VLANs, and device counts |
| `GET` | `/api/network/devices` | Parsed configurations and active interface states |
| `POST` | `/api/validate/plan` | Validates `network_plan.yaml` against schema rules |
| `POST` | `/api/validate/config` | Closed-loop assurance comparing plan to Cisco outputs |
| `POST` | `/api/security/audit` | Audits guest microsegmentation and SSH perimeter |
| `POST` | `/api/faults/test` | Runs automated 5-fault diagnostic benchmark |
| `GET` | `/api/reports/latest` | Returns latest consolidated audit report payload |

---

## 8. Automated Fault Detection & Scenarios

The assurance tool contains built-in diagnostic engines for 5 critical enterprise failures:

1. **F1 (Trunk VLAN Pruning):** Detects if VLAN 20 is missing on trunk ports (SW1 Fa0/24), partitioning guest wireless traffic.
2. **F2 (Missing DHCP Scope):** Detects missing DHCP pools (e.g. EMPLOYEE scope omitted on R1) preventing client IP leasing.
3. **F3 (Subinterface Gateway Mismatch):** Detects when a subinterface IP (e.g. `10.10.10.254`) does not match the planned gateway (`10.10.10.1`).
4. **F4 (Missing NAT/PAT Overload):** Detects when `ip nat inside source list ... overload` is missing, causing ISP drops for outbound packets.
5. **F5 (Broken Guest Isolation ACL):** Detects when ACL `GUEST-IN` lacks deny statements for Server (30) or Management (99), preventing data breaches.

Each fault report includes: **Problem Explanation**, **Affected Device**, **Detected Evidence**, **Potential Impact**, and **Exact Cisco CLI Remediation Commands**.

---

## 9. Automated Pytest Suite

Execute the regression test suite covering all modules:

```powershell
pytest -v
```

All 21 unit and integration tests validate:
- Plan schema validity and error handling
- 802.1Q range boundaries (1-4094) and duplicate detection
- Subnet overlap and IP address conflict detection
- Cisco IOS running-config and show command parsing
- Closed-loop intent comparison
- Zero-trust security compliance
- Automated fault detection benchmark execution

---

## 10. Documentation Index

For in-depth project evaluation and viva defense, consult the dedicated guides in the `docs/` folder:
- [Technical Project Report](docs/PROJECT_REPORT.md) — Comprehensive technical report and architectural analysis.
- [Fault Cards](docs/fault-cards.md) — Detailed diagnosis cards for faults F1 through F5.
- [5-Minute Demo Script](docs/demo-script.md) — Minute-by-minute live presentation script.
- [Viva Questions & Answers](docs/viva-questions.md) — 15+ technical viva interview questions with answers.
- [Submission Checklist](docs/submission-checklist.md) — Verification checklist for project evaluation.
- [Implementation Guide](docs/implementation-guide.md) — Cabling and step-by-step setup instructions.
- [Test Plan](docs/test-plan.md) — Verification matrix and evidence checklist.
