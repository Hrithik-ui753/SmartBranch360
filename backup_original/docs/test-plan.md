# Test plan and expected results

| ID | Source | Test | Expected result |
|---|---|---|---|
| T1 | Employee PC | Obtain DHCP lease | 10.10.10.x/24, gateway 10.10.10.1 |
| T2 | Employee PC | Ping 10.10.10.1 | Success |
| T3 | Employee PC | Ping 10.10.30.10 | Success |
| T4 | Employee PC | Resolve intranet.smartbranch.local | Resolves to 10.10.30.10 |
| T5 | Employee PC | Ping 198.51.100.10 | Success when ISP-side test server is configured |
| T6 | Guest client | Obtain DHCP lease | 10.10.20.x/24, gateway 10.10.20.1 |
| T7 | Guest client | Ping 10.10.20.1 | Success |
| T8 | Guest client | Ping 10.10.30.10 | Blocked |
| T9 | Guest client | Ping 10.10.99.2 or 10.10.99.3 | Blocked |
| T10 | Guest client | Ping 198.51.100.10 | Success when simulated Internet test server is configured |
| T11 | Management PC | SSH to R1, SW1 and SW2 | Allowed with local credentials |
| T12 | Employee/Guest PC | SSH to R1, SW1 or SW2 | Denied |

## Evidence to capture
1. Packet Tracer topology screenshot with device labels.
2. `show vlan brief` and `show interfaces trunk` on both switches.
3. `show ip interface brief`, `show ip route`, DHCP bindings and NAT translations on R1.
4. Employee DHCP lease and successful server/internet tests.
5. Guest blocked-server test and successful simulated Internet test.
6. Successful SSH from management PC and failed SSH from a non-management PC.
7. Python checker report before and after fixing an intentionally introduced fault.

A ping failure alone is not enough to prove an ACL is working if the destination service is down. Confirm the destination is reachable from an authorized VLAN first.
