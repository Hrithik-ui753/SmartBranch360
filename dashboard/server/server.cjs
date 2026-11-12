const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const { exec } = require('child_process');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

const ROOT_DIR = path.resolve(__dirname, '..', '..');
const PLAN_PATH = path.join(ROOT_DIR, 'network_plan.yaml');
const SHOW_DIR = path.join(ROOT_DIR, 'sample_show_outputs');
const PYTHON_SCRIPT = path.join(ROOT_DIR, 'check_network.py');

// Helper to run python assurance tool
function runPythonCheck(args = []) {
  return new Promise((resolve, reject) => {
    const cmd = `python "${PYTHON_SCRIPT}" --plan "${PLAN_PATH}" --show-dir "${SHOW_DIR}" ${args.join(' ')}`;
    exec(cmd, { cwd: ROOT_DIR }, (error, stdout, stderr) => {
      // Exit code 1 means some checks failed, but stdout still contains valid report!
      if (stdout) {
        resolve(stdout);
      } else if (error && !stdout) {
        reject(stderr || error.message);
      } else {
        resolve(stdout);
      }
    });
  });
}

// 1. GET /api/health
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'SmartBranch360 Express Assurance Gateway',
    timestamp: new Date().toISOString(),
    environment: 'production-ready',
    version: '2.0.0'
  });
});

// 2. GET /api/network/overview
app.get('/api/network/overview', (req, res) => {
  try {
    const reportPath = path.join(ROOT_DIR, 'report.json');
    let data;
    if (fs.existsSync(reportPath)) {
      data = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
    }

    res.json({
      site: 'SmartBranch360',
      description: 'Enterprise Secure Branch Office Network',
      health_score: data ? data.health_score : 100,
      vlans: [
        { id: 10, name: 'EMPLOYEE', subnet: '10.10.10.0/24', gateway: '10.10.10.1', dhcp: true, purpose: 'Workstations, internal intranet access' },
        { id: 20, name: 'GUEST', subnet: '10.10.20.0/24', gateway: '10.10.20.1', dhcp: true, purpose: 'Isolated guest laptops and wireless AP clients' },
        { id: 30, name: 'SERVER', subnet: '10.10.30.0/24', gateway: '10.10.30.1', dhcp: false, purpose: 'Enterprise Intranet & DNS Server (10.10.30.10)' },
        { id: 99, name: 'MANAGEMENT', subnet: '10.10.99.0/24', gateway: '10.10.99.1', dhcp: false, purpose: 'Network admin jump box, R1/SW1/SW2 SSH SVIs' }
      ],
      wan: {
        r1_ip: '203.0.113.2/30',
        isp_gateway: '203.0.113.1/30',
        simulated_internet_lan: '198.51.100.0/24'
      },
      devices: {
        router: { name: 'R1', model: 'Cisco 2911', role: 'Edge Router & Gateway' },
        core_switch: { name: 'SW1', model: 'Cisco 2960', role: 'Distribution/Core Switch' },
        access_switch: { name: 'SW2', model: 'Cisco 2960', role: 'Access Switch' },
        isp: { name: 'ISP', model: 'Cisco 2911', role: 'Upstream Provider Simulation' }
      },
      security_policy: {
        guest_may_access_internal_vlans: false,
        ssh_allowed_subnet: '10.10.99.0/24',
        nat_pat_overload: true,
        telnet_disabled: true
      }
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 3. GET /api/network/devices
app.get('/api/network/devices', (req, res) => {
  res.json({
    R1: {
      hostname: 'R1',
      model: 'Cisco 2911 Integrated Services Router',
      role: 'Branch Gateway, Router-on-a-stick, DHCP Server, PAT Gateway',
      ip: '203.0.113.2',
      status: 'online',
      ssh_version: 2,
      subinterfaces: [
        { name: 'GigabitEthernet0/0.10', vlan: 10, ip: '10.10.10.1/24', nat: 'inside', status: 'up' },
        { name: 'GigabitEthernet0/0.20', vlan: 20, ip: '10.10.20.1/24', nat: 'inside', acl: 'GUEST-IN', status: 'up' },
        { name: 'GigabitEthernet0/0.30', vlan: 30, ip: '10.10.30.1/24', nat: 'inside', status: 'up' },
        { name: 'GigabitEthernet0/0.99', vlan: 99, ip: '10.10.99.1/24', nat: 'inside', status: 'up' }
      ],
      wan_interface: { name: 'GigabitEthernet0/1', ip: '203.0.113.2/30', nat: 'outside', status: 'up' },
      dhcp_pools: ['EMPLOYEE (10.10.10.0/24)', 'GUEST (10.10.20.0/24)'],
      nat_rule: 'ip nat inside source list 1 interface GigabitEthernet0/1 overload'
    },
    SW1: {
      hostname: 'SW1',
      model: 'Cisco Catalyst 2960-24TT',
      role: 'Distribution Switch & Server Farm Aggregator',
      management_svi: '10.10.99.2/24',
      status: 'online',
      ssh_version: 2,
      trunks: [
        { port: 'GigabitEthernet0/1', destination: 'R1 G0/0', allowed_vlans: '10,20,30,99' },
        { port: 'FastEthernet0/24', destination: 'SW2 F0/24', allowed_vlans: '10,20,30,99' }
      ],
      access_ports: [
        { port: 'FastEthernet0/5', vlan: 30, device: 'SRV1 (Internal Server)' },
        { port: 'FastEthernet0/6', vlan: 99, device: 'Admin PC (10.10.99.10)' }
      ]
    },
    SW2: {
      hostname: 'SW2',
      model: 'Cisco Catalyst 2960-24TT',
      role: 'End-User Access Switch',
      management_svi: '10.10.99.3/24',
      status: 'online',
      ssh_version: 2,
      trunks: [
        { port: 'FastEthernet0/24', destination: 'SW1 F0/24', allowed_vlans: '10,20,30,99' }
      ],
      access_ports: [
        { port: 'FastEthernet0/1 - 4', vlan: 10, device: 'Employee Workstations (PC1-PC4)' },
        { port: 'FastEthernet0/5 - 6', vlan: 20, device: 'Guest Wired Ports' },
        { port: 'FastEthernet0/7', vlan: 20, device: 'Guest Wireless AP (SSID: SmartBranch-Guest)' }
      ]
    },
    SRV1: {
      hostname: 'SRV1',
      type: 'Server-PT',
      role: 'Intranet Web Server & Local DNS Server',
      ip: '10.10.30.10/24',
      gateway: '10.10.30.1',
      services: ['HTTP (port 80)', 'DNS (intranet.smartbranch.local -> 10.10.30.10)']
    },
    ADMIN_PC: {
      hostname: 'Admin-PC',
      type: 'PC-PT',
      role: 'Secure Network Management Jump-Host',
      ip: '10.10.99.10/24',
      gateway: '10.10.99.1',
      allowed_access: 'SSH (Port 22) to R1, SW1, SW2'
    },
    ISP: {
      hostname: 'ISP',
      model: 'Cisco 2911',
      role: 'Simulated Internet Provider Gateway',
      ip: '203.0.113.1/30',
      status: 'online',
      lan: '198.51.100.1/24 (Simulated Cloud / Test Server: 198.51.100.10)'
    }
  });
});

// 4. POST /api/validate/plan
app.post('/api/validate/plan', async (req, res) => {
  try {
    const raw = await runPythonCheck(['--report', 'json']);
    const parsed = JSON.parse(raw);
    res.json({
      success: true,
      findings: parsed.findings.plan || [],
      summary: {
        total: parsed.findings.plan.length,
        passed: parsed.findings.plan.filter(f => f.status === 'PASS').length,
        failed: parsed.findings.plan.filter(f => f.status === 'FAIL').length
      }
    });
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

// 5. POST /api/validate/config
app.post('/api/validate/config', async (req, res) => {
  try {
    const raw = await runPythonCheck(['--report', 'json']);
    const parsed = JSON.parse(raw);
    res.json({
      success: true,
      findings: parsed.findings.assurance || [],
      summary: {
        total: parsed.findings.assurance.length,
        passed: parsed.findings.assurance.filter(f => f.status === 'PASS').length,
        failed: parsed.findings.assurance.filter(f => f.status === 'FAIL').length
      }
    });
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

// 6. POST /api/security/audit
app.post('/api/security/audit', async (req, res) => {
  try {
    const raw = await runPythonCheck(['--report', 'json']);
    const parsed = JSON.parse(raw);
    res.json({
      success: true,
      findings: parsed.findings.security || [],
      summary: {
        total: parsed.findings.security.length,
        passed: parsed.findings.security.filter(f => f.status === 'PASS').length,
        failed: parsed.findings.security.filter(f => f.status === 'FAIL').length
      }
    });
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

// 7. POST /api/faults/test
app.post('/api/faults/test', async (req, res) => {
  try {
    const raw = await runPythonCheck(['--run-faults', '--report', 'json']);
    const parsed = JSON.parse(raw);
    res.json({
      success: true,
      faults: parsed.faults || []
    });
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

// 8. GET /api/reports/latest
app.get('/api/reports/latest', async (req, res) => {
  try {
    const raw = await runPythonCheck(['--run-faults', '--report', 'json']);
    const parsed = JSON.parse(raw);
    res.json(parsed);
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

// Serve frontend build if exists
const DIST_DIR = path.resolve(__dirname, '..', 'dist');
if (fs.existsSync(DIST_DIR)) {
  app.use(express.static(DIST_DIR));
  app.use((req, res) => {
    res.sendFile(path.join(DIST_DIR, 'index.html'));
  });
}

app.listen(PORT, () => {
  console.log(`[SmartBranch360] Server listening on http://localhost:${PORT}`);
});
