# Implementation guide

## A. Place and connect devices
Place R1 (2911), SW1 and SW2 (2960), AP1, one Server-PT, four employee PCs, two guest clients, one management PC, and ISP router (2911). Add an ISP-side test server if desired.

Cable:
- R1 G0/0 <-> SW1 G0/1
- R1 G0/1 <-> ISP G0/0
- SW1 F0/24 <-> SW2 F0/24
- SW1 F0/5 <-> SRV1
- SW1 F0/6 <-> Management PC
- SW2 F0/1-4 <-> employee PCs
- SW2 F0/5-6 <-> guest wired clients
- SW2 F0/7 <-> AP1

Use copper straight-through or Packet Tracer automatic cable selection. If an interface name differs, adapt the config.

## B. Configure switches first
Paste the matching file from `configs/` into each switch CLI. If `crypto key generate rsa modulus 1024` is rejected, try `crypto key generate rsa` and answer the prompts. If the switch does not support SSH in your Packet Tracer version, use a supported IOS switch model; do not weaken the intended final security requirement.

## C. Configure router and ISP
Paste `configs/ISP-router.txt` into ISP and `configs/R1-router.txt` into R1. Confirm router interfaces are up. Some IOS images ask for confirmation when generating RSA keys.

## D. Configure server
On SRV1 Desktop > IP Configuration:
- IP address: 10.10.30.10
- Mask: 255.255.255.0
- Default gateway: 10.10.30.1
- DNS server: 10.10.30.10

On Services > DNS, turn DNS On and create a record:
- Name: `intranet.smartbranch.local`
- Address: `10.10.30.10`

Optionally enable HTTP on the server for a browser test.

## E. Configure endpoints
- Employee PCs: Desktop > IP Configuration > DHCP.
- Guest clients: DHCP (wired ports or wireless AP).
- Management PC: static 10.10.99.10 /24, gateway 10.10.99.1, DNS 10.10.30.10.
- AP: use a management IP only if you deliberately place it in VLAN 99. In this baseline it is a guest-facing bridge on access VLAN 20; configure SSID `SmartBranch-Guest` and WPA2-PSK. Use a strong lab-only key and connect guest laptops to that SSID.

## F. Verification commands
On router:
- `show ip interface brief`
- `show ip route`
- `show ip dhcp binding`
- `show access-lists`
- `show ip nat translations`
- `show ip nat statistics`

On switches:
- `show vlan brief`
- `show interfaces trunk`
- `show ip interface brief`
- `show running-config`

Save relevant command output as `.txt` files for the Python checker.

## G. Notes on DNS and Internet simulation
Employee DNS points to the internal server. Configure the server DNS service with the intranet record. Guest DNS points to 8.8.8.8; Packet Tracer does not guarantee reachability to real public DNS. For a fully self-contained demo, you may instead create a DNS service on the ISP-side test server and use its simulated address, but that changes the stated guest DNS setting and should be documented.

The ISP-side server at 198.51.100.10 is a simulated Internet destination. A successful ping to it demonstrates routing and NAT inside the lab, not access to the real Internet.
