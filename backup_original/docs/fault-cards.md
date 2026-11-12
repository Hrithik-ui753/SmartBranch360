# SmartBranch 360 fault cards

Inject one fault at a time. Record symptom, evidence, root cause, fix and retest.

## F1 - Missing VLAN on trunk
- Inject: Remove VLAN 20 from the allowed VLAN list on SW1 F0/24.
- Symptom: Guest devices behind SW2 cannot reach their gateway.
- Evidence: `show interfaces trunk`; VLAN 20 absent from allowed/active list.
- Root cause: Guest VLAN is not carried across the inter-switch trunk.
- Fix: `switchport trunk allowed vlan 10,20,30,99`.
- Retest: Guest obtains DHCP and pings 10.10.20.1.

## F2 - Incorrect employee default gateway
- Inject: Change an employee PC gateway to 10.10.20.1.
- Symptom: Local VLAN communication may work, but off-subnet server/internet access fails.
- Evidence: PC IP Configuration shows wrong gateway.
- Root cause: Host points to the guest router subinterface.
- Fix: Set gateway to 10.10.10.1 or renew DHCP after correcting the pool.
- Retest: Ping server and ISP-side test server.

## F3 - DHCP pool network error
- Inject: Change the EMPLOYEE pool network to 10.10.20.0/24.
- Symptom: Employee PCs fail to receive a correct 10.10.10.x lease.
- Evidence: `show running-config | section dhcp` and `show ip dhcp binding`.
- Root cause: DHCP scope does not match employee VLAN subnet.
- Fix: `network 10.10.10.0 255.255.255.0`.
- Retest: Renew employee PC DHCP lease.

## F4 - Guest ACL blocks DNS or external traffic
- Inject: Add an incorrect deny statement that blocks all guest traffic, or place a broad deny before the permit.
- Symptom: Guest cannot reach simulated Internet destination.
- Evidence: `show access-lists` hit counters and ACL order.
- Root cause: ACL order or wildcard mask is incorrect.
- Fix: Keep denies for internal VLANs first, followed by `permit ip 10.10.20.0 0.0.0.255 any`.
- Retest: Guest cannot reach internal subnets but can reach 198.51.100.10.

## F5 - NAT configuration missing
- Inject: Remove the NAT overload statement.
- Symptom: Branch clients reach local networks but not the ISP-side test server.
- Evidence: `show ip nat translations` remains empty after outbound test; inspect NAT config.
- Root cause: PAT rule is missing or incorrect.
- Fix: `ip nat inside source list 1 interface GigabitEthernet0/1 overload`.
- Retest: Ping 198.51.100.10 and inspect NAT translations.

## F6 - Wrong server gateway
- Inject: Set server gateway to 10.10.30.254.
- Symptom: Local VLAN clients may reach the server, but replies to remote subnets fail.
- Evidence: Server IP Configuration.
- Root cause: Incorrect default gateway.
- Fix: Set gateway to 10.10.30.1.
- Retest: Employee PC pings server and opens its HTTP page if enabled.

## F7 - SSH access policy misconfigured
- Inject: Remove or alter `access-class SSH-MGMT in` on a VTY line.
- Symptom: Non-management host may be able to attempt SSH.
- Evidence: `show running-config` VTY section; test from management and employee PCs.
- Root cause: VTY access restriction missing or incorrect.
- Fix: Apply `access-class SSH-MGMT in` and retain `transport input ssh`.
- Retest: SSH succeeds only from 10.10.99.0/24.
