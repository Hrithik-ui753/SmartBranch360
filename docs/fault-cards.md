# SmartBranch360: Enterprise Fault Cards & Diagnostic Guide

This document contains standardized diagnosis cards for five critical branch network failure scenarios.
Use these cards to demonstrate fault injection, automated detection, root cause analysis, and corrective remediation.

---

## Fault Scenario Card F1: Trunk VLAN Pruning (VLAN 20 Missing)

- **Scenario ID:** `F1`
- **Fault Name:** Missing VLAN on Inter-Switch Trunk Link
- **Affected Device:** `SW1 (Distribution Switch)`
- **Affected Interface:** `FastEthernet0/24` (Trunk to SW2)
- **Fault Description:** VLAN 20 (Guest) is omitted from the allowed trunk VLAN list on SW1.
- **Fault Injection Command:**
  ```cisco
  SW1# configure terminal
  SW1(config)# interface FastEthernet0/24
  SW1(config-if)# switchport trunk allowed vlan 10,30,99
  SW1(config-if)# end
  ```
- **Observed Symptoms:**
  - Guest laptops connected to SW2 or the wireless AP fail to obtain an IP lease via DHCP.
  - Guest devices fall back to APIPA address `169.254.x.x`.
  - Statically configured guest devices cannot ping default gateway `10.10.20.1`.
- **Cisco CLI Evidence:**
  - `SW1# show interfaces trunk` -> Port `Fa0/24` lists allowed VLANs as `10,30,99` (VLAN 20 absent).
- **Automated Detection Code:** `ASSURE_SW1_TRUNK_RESTRICTED_FastEthernet0/24`
- **Root Cause:** IEEE 802.1Q tagged frames with VID 20 are dropped at ingress/egress on the inter-switch trunk.
- **Corrective CLI Action:**
  ```cisco
  SW1# configure terminal
  SW1(config)# interface FastEthernet0/24
  SW1(config-if)# switchport trunk allowed vlan 10,20,30,99
  SW1(config-if)# end
  SW1# write memory
  ```
- **Expected Result After Fix:**
  - `show interfaces trunk` displays `10,20,30,99`.
  - Guest client executes `ipconfig /renew` and receives IP in `10.10.20.0/24`.
  - Ping to `10.10.20.1` succeeds with 0% packet loss.

---

## Fault Scenario Card F2: Missing DHCP Pool Configuration

- **Scenario ID:** `F2`
- **Fault Name:** Missing DHCP Pool Scope for Employee VLAN
- **Affected Device:** `R1 (Branch Gateway Router)`
- **Fault Description:** The DHCP pool definition for VLAN 10 (`EMPLOYEE`) is omitted from the router running-config.
- **Fault Injection Command:**
  ```cisco
  R1# configure terminal
  R1(config)# no ip dhcp pool EMPLOYEE
  R1(config)# end
  ```
- **Observed Symptoms:**
  - Employee workstations set to DHCP fail to acquire an IP address.
  - Workstations assign APIPA addresses (`169.254.x.x`).
  - Employees cannot access corporate server `10.10.30.10` or resolve intranet DNS.
- **Cisco CLI Evidence:**
  - `R1# show running-config | section dhcp` -> Only `ip dhcp pool GUEST` is listed.
  - `R1# show ip dhcp binding` -> No active bindings in `10.10.10.0/24`.
- **Automated Detection Code:** `ASSURE_DHCP_POOL_MISSING_VLAN_10`
- **Root Cause:** R1 DHCP daemon ignores `DHCPDISCOVER` broadcasts arriving on subinterface `G0/0.10` because no matching pool exists.
- **Corrective CLI Action:**
  ```cisco
  R1# configure terminal
  R1(config)# ip dhcp pool EMPLOYEE
  R1(dhcp-config)# network 10.10.10.0 255.255.255.0
  R1(dhcp-config)# default-router 10.10.10.1
  R1(dhcp-config)# dns-server 10.10.30.10
  R1(dhcp-config)# end
  R1# write memory
  ```
- **Expected Result After Fix:**
  - Workstation command prompt: `ipconfig /renew` receives IP `10.10.10.21`, mask `255.255.255.0`, gateway `10.10.10.1`.
  - Browser loads `http://intranet.smartbranch.local`.

---

## Fault Scenario Card F3: Incorrect Gateway Address on Router Subinterface

- **Scenario ID:** `F3`
- **Fault Name:** Default Gateway IP Address Mismatch on Subinterface
- **Affected Device:** `R1 (Subinterface GigabitEthernet0/0.10)`
- **Fault Description:** Subinterface `G0/0.10` is erroneously assigned IP `10.10.10.254` instead of `10.10.10.1`.
- **Fault Injection Command:**
  ```cisco
  R1# configure terminal
  R1(config)# interface GigabitEthernet0/0.10
  R1(config-subif)# ip address 10.10.10.254 255.255.255.0
  R1(config-subif)# end
  ```
- **Observed Symptoms:**
  - Local intra-VLAN traffic works, but all inter-VLAN routing (to Server VLAN 30, Management VLAN 99, and WAN) fails.
  - Employee PC cannot ping its configured default gateway `10.10.10.1`.
- **Cisco CLI Evidence:**
  - `R1# show ip interface brief` shows `GigabitEthernet0/0.10` IP is `10.10.10.254`.
  - `R1# show ip dhcp pool EMPLOYEE` still offers default-router `10.10.10.1`.
- **Automated Detection Code:** `ASSURE_GATEWAY_IP_MISMATCH_VLAN_10`
- **Root Cause:** Host points to `10.10.10.1`, which generates unanswered ARP requests because the router subinterface is listening on `.254`.
- **Corrective CLI Action:**
  ```cisco
  R1# configure terminal
  R1(config)# interface GigabitEthernet0/0.10
  R1(config-subif)# ip address 10.10.10.1 255.255.255.0
  R1(config-subif)# end
  R1# write memory
  ```
- **Expected Result After Fix:**
  - Ping from employee PC to `10.10.10.1` succeeds immediately.
  - Inter-VLAN ping to server `10.10.30.10` succeeds.

---

## Fault Scenario Card F4: Missing NAT / PAT Overload Configuration

- **Scenario ID:** `F4`
- **Fault Name:** Missing Dynamic Port Address Translation (PAT) Overload
- **Affected Device:** `R1 (Branch Gateway Router)`
- **Fault Description:** The NAT inside source list overload statement is absent from R1.
- **Fault Injection Command:**
  ```cisco
  R1# configure terminal
  R1(config)# no ip nat inside source list 1 interface GigabitEthernet0/1 overload
  R1(config)# end
  ```
- **Observed Symptoms:**
  - Internal routing between employee, server, and management subnets works normally.
  - All outbound packets sent to the ISP simulated cloud destination (`198.51.100.10`) fail.
- **Cisco CLI Evidence:**
  - `R1# show ip nat statistics` displays `Total active translations: 0`.
  - `R1# show ip nat translations` is completely blank during outbound ping attempts.
- **Automated Detection Code:** `ASSURE_NAT_OVERLOAD_MISSING`
- **Root Cause:** Private RFC 1918 addresses (`10.10.0.0/16`) are transmitted without translation across the WAN link; the simulated ISP router drops private non-routable addresses.
- **Corrective CLI Action:**
  ```cisco
  R1# configure terminal
  R1(config)# access-list 1 permit 10.10.0.0 0.0.255.255
  R1(config)# ip nat inside source list 1 interface GigabitEthernet0/1 overload
  R1(config)# end
  R1# write memory
  ```
- **Expected Result After Fix:**
  - Ping from employee or guest PC to `198.51.100.10` succeeds.
  - `R1# show ip nat translations` displays active translations with outside IP `203.0.113.2`.

---

## Fault Scenario Card F5: Broken Guest Isolation ACL

- **Scenario ID:** `F5`
- **Fault Name:** Guest ACL Missing Internal Deny Rules
- **Affected Device:** `R1 (Extended ACL GUEST-IN)`
- **Fault Description:** ACL `GUEST-IN` contains `permit ip 10.10.20.0 0.0.0.255 any` without preceding `deny` rules for Server VLAN (30) or Management VLAN (99).
- **Fault Injection Command:**
  ```cisco
  R1# configure terminal
  R1(config)# ip access-list extended GUEST-IN
  R1(config-ext-nacl)# no deny ip 10.10.20.0 0.0.0.255 10.10.30.0 0.0.0.255
  R1(config-ext-nacl)# no deny ip 10.10.20.0 0.0.0.255 10.10.99.0 0.0.0.255
  R1(config-ext-nacl)# end
  ```
- **Observed Symptoms:**
  - High severity security breach: Guest laptops can ping corporate server `10.10.30.10` and open the intranet web portal.
  - Guest laptops can probe management switches `10.10.99.2` and `10.10.99.3`.
- **Cisco CLI Evidence:**
  - `R1# show access-lists GUEST-IN` displays only `permit ip 10.10.20.0 0.0.0.255 any`.
  - Ping from Guest Laptop to `10.10.30.10` succeeds (should be blocked).
- **Automated Detection Code:** `SEC_GUEST_CAN_REACH_SERVER` and `SEC_GUEST_CAN_REACH_MGMT`
- **Root Cause:** Absence of explicit layer 3 deny statements allows inter-VLAN routing to forward guest packets to internal subnets.
- **Corrective CLI Action:**
  ```cisco
  R1# configure terminal
  R1(config)# ip access-list extended GUEST-IN
  R1(config-ext-nacl)# 10 deny ip 10.10.20.0 0.0.0.255 10.10.10.0 0.0.0.255
  R1(config-ext-nacl)# 20 deny ip 10.10.20.0 0.0.0.255 10.10.30.0 0.0.0.255
  R1(config-ext-nacl)# 30 deny ip 10.10.20.0 0.0.0.255 10.10.99.0 0.0.0.255
  R1(config-ext-nacl)# 40 permit ip 10.10.20.0 0.0.0.255 any
  R1(config-ext-nacl)# end
  R1# write memory
  ```
- **Expected Result After Fix:**
  - Guest ping to `10.10.30.10` reports `Destination Host Unreachable`.
  - Guest ping to simulated Internet `198.51.100.10` succeeds.
  - `R1# show access-lists GUEST-IN` shows match counters incrementing on deny rules.
