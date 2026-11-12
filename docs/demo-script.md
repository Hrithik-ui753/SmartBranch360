# SmartBranch360: 5-Minute Project Demonstration Script

**Role:** Senior Network Automation & Cybersecurity Engineer  
**Objective:** Deliver a crisp, technical, structured live demonstration for examiners, evaluators, or interviewers.

---

## Timeline & Speaker Notes

### ⏱️ [0:00 - 1:00] Overview & Architecture
- **Speaker:**  
  *"Good morning. Today I am presenting **SmartBranch360**, a secure enterprise branch-office network design paired with a custom Python 3.12 network assurance engine and full-stack web dashboard.*  
  *In modern networks, misconfigurations and security drift cause major downtime and data breaches. SmartBranch360 solves this through three pillars:*  
  *1. Strict departmental segmentation across four IEEE 802.1Q VLANs: Employee (VLAN 10), Guest (VLAN 20), Server (VLAN 30), and Management (VLAN 99).*  
  *2. Router-on-a-stick inter-VLAN routing with dynamic PAT overload on a Cisco 2911 router.*  
  *3. A closed-loop automated assurance engine that parses Cisco CLI show outputs and audits security compliance."*
- **Action:** Display the React Dashboard **Overview** and **Network Topology** page.

---

### ⏱️ [1:00 - 2:00] Normal Network Operations
- **Speaker:**  
  *"Let's verify normal operations. On our access switch SW2, employee workstations receive dynamic IP addresses via Cisco IOS DHCP on R1.*  
  *Notice that Employee PC1 has received `10.10.10.21`, default gateway `10.10.10.1`, and primary DNS pointing to internal server `10.10.30.10`.*  
  *From Employee PC1, we ping `10.10.30.10` — successful with sub-millisecond response. In the web browser, typing `http://intranet.smartbranch.local` resolves the DNS A record and loads the branch intranet portal.*  
  *Next, when the employee sends outbound traffic to simulated Internet server `198.51.100.10`, R1 translates private address `10.10.10.21` to WAN IP `203.0.113.2` using dynamic Port Address Translation (PAT). Examining `show ip nat translations` proves active Layer 4 state translation."*
- **Action:** Show ping to server, DNS resolution in Packet Tracer, and the **IPAM** table on the dashboard.

---

### ⏱️ [2:00 - 3:00] Zero-Trust Security & Perimeter Hardening
- **Speaker:**  
  *"Now let's examine the cybersecurity controls.*  
  *First, **Guest Isolation**: Guest laptops and wireless AP clients are connected to VLAN 20. If a guest attempts to ping internal server `10.10.30.10` or management switch `10.10.99.2`, the traffic is immediately dropped with 'Destination Host Unreachable'. This is enforced by extended ACL `GUEST-IN` applied inbound on subinterface `Gi0/0.20`.*  
  *However, if the guest pings simulated Internet destination `198.51.100.10`, traffic is permitted via PAT.*  
  *Second, **SSH Perimeter Restriction**: Insecure Telnet is completely disabled. Only the dedicated Admin PC on `10.10.99.10` can open SSH sessions to R1, SW1, or SW2. An SSH attempt from an employee or guest PC is immediately rejected by VTY access-class `SSH-MGMT`."*
- **Action:** Open the **Security Audit** page on the dashboard to highlight the green PASS badges.

---

### ⏱️ [3:00 - 4:15] Python Assurance Tool & Live Fault Injection
- **Speaker:**  
  *"Rather than relying on manual spot-checks, we engineered an automated Python Network Assurance tool.*  
  *Let's demonstrate its diagnostic capability by intentionally injecting **Fault F1**: removing VLAN 20 from the allowed trunk list on SW1 port Fa0/24.*  
  *In Packet Tracer, guest clients immediately lose DHCP and cannot reach their gateway.*  
  *Now, we run our CLI assurance command:*  
  ```powershell
  python check_network.py --plan network_plan.yaml --show-dir sample_show_outputs --run-faults
  ```  
  *In under one second, the tool analyzes 54 configuration assertions across R1, SW1, and SW2. Look at the output:*  
  *It flags Fault F1: `VLAN 20 Missing on Trunk`, identifies `SW1 (FastEthernet0/24)`, shows the exact CLI evidence `switchport trunk allowed vlan 10,30,99`, and outputs the exact Cisco remediation commands to restore the link."*
- **Action:** Execute the Python script in the terminal and switch to the **Fault Detection** tab on the web dashboard.

---

### ⏱️ [4:15 - 5:00] Remediation, HTML/JSON Reporting & Conclusion
- **Speaker:**  
  *"We apply the remediation command `switchport trunk allowed vlan 10,20,30,99`. Guest clients immediately renew their lease and reach the gateway.*  
  *Re-running the assurance tool produces a **100% Network Health Score** with zero defects.*  
  *The tool also exports a comprehensive standalone HTML audit report and a structured JSON payload consumed by our React/Node.js REST API.*  
  *In conclusion, SmartBranch360 delivers an enterprise-ready, zero-trust branch network validated through programmatic closed-loop assurance. Thank you, and I am now ready for your questions."*
- **Action:** Display the HTML Report in the browser and conclude the presentation.
