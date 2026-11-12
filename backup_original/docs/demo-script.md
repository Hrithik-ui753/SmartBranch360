# 5-10 minute demonstration script

## 0:00-1:00 - Problem and architecture
Introduce SmartBranch 360. Explain the four VLANs and why guest traffic must be isolated.

## 1:00-2:00 - Topology and IP plan
Show Packet Tracer topology, device labels, VLAN table and trunk links.

## 2:00-4:00 - Normal operation
Show an employee PC receiving DHCP, pinging the internal server, resolving the intranet DNS record and reaching the ISP-side test server. Show guest DHCP and guest Internet-simulation access.

## 4:00-5:30 - Security
Show guest ping to server/management failing. Show SSH success from management PC and failed SSH attempt from employee or guest PC.

## 5:30-7:30 - Inject and diagnose fault
Remove VLAN 20 from one trunk. Demonstrate guest connectivity failure. Run the Python checker against the plan and/or show-output evidence. Explain that the checker detects plan-level missing VLAN declarations; live diagnosis is confirmed using Cisco show commands.

## 7:30-9:00 - Fix and verify
Restore VLAN 20 on trunk. Renew guest DHCP and ping gateway. Show successful recovery.

## 9:00-10:00 - Conclusion
Summarize segmentation, DHCP, routing, NAT, ACL security and Python-based assurance. Mention limitations: simulated Internet and lightweight text-based validation.
