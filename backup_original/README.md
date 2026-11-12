# SmartBranch 360
Secure branch-office network built with Cisco Packet Tracer and a Python assurance checker.

## What is included
- `configs/R1-router.txt`: router-on-a-stick, DHCP, NAT/PAT, guest isolation, SSH restriction
- `configs/SW1-core-switch.txt`: VLANs, trunks, server and management access ports, SSH
- `configs/SW2-access-switch.txt`: VLANs, trunk, employee/guest/AP access ports, SSH
- `configs/ISP-router.txt`: simulated ISP gateway and test network
- `network_plan.yaml`: source-of-truth VLAN/IP/device plan
- `assurance_tool/check_network.py`: validates the plan and selected Cisco `show` outputs
- `docs/`: test plan, fault cards, demo script and implementation notes

## Important Packet Tracer assumptions
Device models and IOS feature support vary. These configs assume:
- R1 is a Cisco 2911 with `G0/0` facing SW1 and `G0/1` facing the ISP.
- SW1 and SW2 are Cisco 2960 switches.
- SW1 `G0/1` connects to R1 `G0/0`; SW1 `F0/24` connects to SW2 `F0/24`.
- SW1 `F0/5` = server; SW1 `F0/6` = management PC.
- SW2 `F0/1-4` = employee PCs; `F0/5-6` = guest wired clients; `F0/7` = AP.
- WAN lab network is documentation range `203.0.113.0/30`. This is not a real public Internet connection.
- The simulated ISP has a test network `198.51.100.0/24`; add a test server there if you want to prove outbound reachability.

Adjust interface names if your selected device differs. Apply configurations in small sections and verify each phase.

## Build order
1. Place devices and cable them according to `docs/implementation-guide.md`.
2. Configure SW1 and SW2.
3. Configure R1 and ISP router.
4. Configure server static IP and DNS service.
5. Set PCs to DHCP; set management PC to static IP.
6. Apply the test plan and fault cards.
7. Run the Python checker against `network_plan.yaml` and saved `show` outputs.

## Run the Python tool
Python 3.9+:
```bash
cd assurance_tool
python -m pip install -r requirements.txt
python check_network.py --plan ../network_plan.yaml
```
To inspect command output files:
```bash
python check_network.py --plan ../network_plan.yaml --show-dir ../sample_show_outputs
```

## Limitation
The `.pkt` topology must be assembled and saved in Cisco Packet Tracer. This package provides the design, device configurations, validation tool and evidence checklist; it does not fabricate a Packet Tracer binary.
