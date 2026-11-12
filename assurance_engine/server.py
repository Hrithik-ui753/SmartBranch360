"""SmartBranch360 REST API Server (Python FastAPI).

Exposes network validation, configuration assurance, security audit,
and fault detection as RESTful API services.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .validator import NetworkPlanValidator
from .parser import CiscoConfigParser
from .comparator import ConfigurationAssuranceEngine
from .security_audit import SecurityAuditor
from .fault_detector import FaultDetector
from .reporter import AssuranceReportGenerator

app = FastAPI(
    title="SmartBranch360 Network Assurance API",
    version="2.0.0",
    description="REST API for branch network validation, compliance auditing, and automated fault diagnosis."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
PLAN_PATH = BASE_DIR / "network_plan.yaml"
SHOW_DIR = BASE_DIR / "sample_show_outputs"


class FaultTestRequest(BaseModel):
    scenario_id: str
    custom_snippet: Optional[str] = None


def get_loaded_context():
    validator = NetworkPlanValidator(PLAN_PATH)
    validator.validate_all()
    parser = CiscoConfigParser()
    devices = parser.parse_directory(SHOW_DIR)
    return validator, devices


@app.get("/api/health")
def api_health():
    """Health check endpoint."""
    return {"status": "ok", "service": "SmartBranch360 Assurance Engine", "version": "2.0.0"}


@app.get("/api/network/overview")
def api_network_overview():
    """Returns high-level network topology metadata, VLANs, and device counts."""
    validator, devices = get_loaded_context()
    plan = validator.plan
    return {
        "site": plan.get("site", "SmartBranch360"),
        "total_vlans": len(plan.get("vlans", [])),
        "total_devices": len(plan.get("devices", {})),
        "total_trunks": len(plan.get("trunks", [])),
        "vlans": plan.get("vlans", []),
        "devices": plan.get("devices", {}),
        "trunks": plan.get("trunks", []),
        "security_policy": plan.get("security", {}),
        "parsed_cisco_devices": list(devices.keys())
    }


@app.get("/api/network/devices")
def api_network_devices():
    """Returns parsed Cisco device configurations, interfaces, and operational state."""
    _, devices = get_loaded_context()
    output = {}
    for name, dev in devices.items():
        output[name] = {
            "hostname": dev.hostname,
            "type": dev.device_type,
            "version": dev.version,
            "ssh_version": dev.ssh_version,
            "service_password_encryption": dev.service_password_encryption,
            "has_enable_secret": dev.has_enable_secret,
            "vty_access_class": dev.vty_access_class,
            "vty_transport_input": dev.vty_transport_input,
            "interfaces": {
                if_name: {
                    "ip": iface.ip_address,
                    "mask": iface.subnet_mask,
                    "vlan_id": iface.vlan_id,
                    "nat": iface.nat_type,
                    "status": iface.oper_status or ("down" if iface.admin_down else "up"),
                    "mode": iface.switchport_mode,
                    "access_vlan": iface.access_vlan,
                    "allowed_vlans": iface.allowed_vlans
                }
                for if_name, iface in dev.interfaces.items()
            },
            "dhcp_pools": {
                p_name: {
                    "network": pool.network,
                    "mask": pool.netmask,
                    "gateway": pool.default_router,
                    "dns": pool.dns_server
                }
                for p_name, pool in dev.dhcp_pools.items()
            },
            "dhcp_bindings": dev.dhcp_bindings,
            "nat_statistics": dev.nat_statistics,
            "vlans": dev.vlans
        }
    return output


@app.post("/api/validate/plan")
def api_validate_plan():
    """Runs network plan validation checks against network_plan.yaml."""
    validator = NetworkPlanValidator(PLAN_PATH)
    findings = validator.validate_all()
    return {
        "total": len(findings),
        "passed": sum(1 for f in findings if f.status == "PASS"),
        "failed": sum(1 for f in findings if f.status == "FAIL"),
        "warnings": sum(1 for f in findings if f.status == "WARNING"),
        "findings": [
            {
                "status": f.status,
                "code": f.code,
                "category": f.category,
                "message": f.message,
                "remediation": f.remediation
            }
            for f in findings
        ]
    }


@app.post("/api/validate/config")
def api_validate_config():
    """Runs closed-loop configuration assurance comparing plan against saved Cisco outputs."""
    validator, devices = get_loaded_context()
    comparator = ConfigurationAssuranceEngine(validator.plan, devices)
    findings = comparator.verify_all()
    return {
        "total": len(findings),
        "passed": sum(1 for f in findings if f.status == "PASS"),
        "failed": sum(1 for f in findings if f.status == "FAIL"),
        "warnings": sum(1 for f in findings if f.status == "WARNING"),
        "findings": [
            {
                "status": f.status,
                "code": f.code,
                "category": f.category,
                "message": f.message,
                "remediation": f.remediation
            }
            for f in findings
        ]
    }


@app.post("/api/security/audit")
def api_security_audit():
    """Runs security posture audit across guest isolation, SSH, and AAA hygiene."""
    _, devices = get_loaded_context()
    auditor = SecurityAuditor(devices)
    findings = auditor.audit_all()
    return {
        "total": len(findings),
        "passed": sum(1 for f in findings if f.status == "PASS"),
        "failed": sum(1 for f in findings if f.status == "FAIL"),
        "warnings": sum(1 for f in findings if f.status == "WARNING"),
        "findings": [
            {
                "status": f.status,
                "code": f.code,
                "category": f.category,
                "message": f.message,
                "remediation": f.remediation
            }
            for f in findings
        ]
    }


@app.post("/api/faults/test")
def api_faults_test(req: FaultTestRequest):
    """Diagnoses a specific fault scenario or benchmark."""
    _, devices = get_loaded_context()
    detector = FaultDetector(devices)
    try:
        report = detector.test_fault_scenario(req.scenario_id, req.custom_snippet)
        return {
            "id": report.id,
            "title": report.title,
            "affected_device": report.affected_device,
            "status": report.status,
            "explanation": report.problem_explanation,
            "impact": report.potential_impact,
            "evidence": report.detected_evidence,
            "remediation": report.corrective_action,
            "expected_result": report.expected_result_after_fix,
            "raw_snippet": report.raw_snippet
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/reports/latest")
def api_reports_latest():
    """Generates and returns the latest consolidated network assurance report."""
    validator, devices = get_loaded_context()
    plan_findings = validator.validate_all()
    comparator = ConfigurationAssuranceEngine(validator.plan, devices)
    assure_findings = comparator.verify_all()
    auditor = SecurityAuditor(devices)
    sec_findings = auditor.audit_all()
    detector = FaultDetector(devices)
    faults = detector.run_all_benchmarks(SHOW_DIR / "faults")

    reporter = AssuranceReportGenerator(
        site_name=validator.plan.get("site", "SmartBranch360"),
        plan_findings=plan_findings,
        assurance_findings=assure_findings,
        security_findings=sec_findings,
        fault_reports=faults,
        device_summary={name: {"type": d.device_type} for name, d in devices.items()}
    )

    import json
    return json.loads(reporter.generate_json())


def start_server(host: str = "127.0.0.1", port: int = 8000):
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_server()

