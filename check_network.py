#!/usr/bin/env python3
"""SmartBranch360 Network Assurance & Security Engine CLI.

Author: SmartBranch360 Automation Team
Version: 2.0.0
"""

import argparse
from pathlib import Path
import sys

# Ensure local imports work regardless of working directory
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from assurance_engine.validator import NetworkPlanValidator
from assurance_engine.parser import CiscoConfigParser
from assurance_engine.comparator import ConfigurationAssuranceEngine
from assurance_engine.security_audit import SecurityAuditor
from assurance_engine.fault_detector import FaultDetector
from assurance_engine.reporter import AssuranceReportGenerator


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SmartBranch360: Professional Cisco Network Assurance & Security Audit Tool"
    )
    parser.add_argument(
        "--plan",
        default="network_plan.yaml",
        help="Path to network_plan.yaml (default: network_plan.yaml)"
    )
    parser.add_argument(
        "--show-dir",
        default="sample_show_outputs",
        help="Directory containing Cisco show outputs and configs (default: sample_show_outputs)"
    )
    parser.add_argument(
        "--report",
        choices=["term", "terminal", "html", "json"],
        default="terminal",
        help="Report format: terminal (default), html, or json"
    )
    parser.add_argument(
        "--output-file",
        help="Optional path to write HTML or JSON report file"
    )
    parser.add_argument(
        "--run-faults",
        action="store_true",
        help="Run the automated 5-fault diagnostic benchmark suite"
    )

    args = parser.parse_args()

    # Step 1: Validate Plan
    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"[ERROR] Plan file not found: {plan_path}", file=sys.stderr)
        return 2

    try:
        validator = NetworkPlanValidator(plan_path)
        plan_findings = validator.validate_all()
    except Exception as exc:
        print(f"[ERROR] Failed to parse network plan: {exc}", file=sys.stderr)
        return 2

    # Step 2: Parse Cisco Show Outputs & Configs
    cisco_parser = CiscoConfigParser()
    show_dir = Path(args.show_dir)
    devices = {}
    if show_dir.exists() and show_dir.is_dir():
        devices = cisco_parser.parse_directory(show_dir)

    # Step 3: Run Configuration Assurance
    assurance_findings = []
    if devices:
        comparator = ConfigurationAssuranceEngine(validator.plan, devices)
        assurance_findings = comparator.verify_all()

    # Step 4: Run Security Audit
    security_findings = []
    if devices:
        auditor = SecurityAuditor(devices)
        security_findings = auditor.audit_all()

    # Step 5: Run Fault Detection
    fault_detector = FaultDetector(devices)
    fault_reports = []
    if args.run_faults:
        faults_dir = show_dir / "faults"
        fault_reports = fault_detector.run_all_benchmarks(faults_dir)
    else:
        # Detect active network faults
        active_faults = fault_detector.analyze_active_network()
        if active_faults:
            fault_reports.extend(active_faults)

    # Step 6: Generate Device Summaries
    device_summary = {}
    for name, dev in devices.items():
        device_summary[name] = {
            "hostname": dev.hostname,
            "type": dev.device_type,
            "ssh_version": dev.ssh_version,
            "interfaces": list(dev.interfaces.keys()),
            "dhcp_pools": list(dev.dhcp_pools.keys()),
            "vlans": list(dev.vlans.keys())
        }

    # Step 7: Generate Report
    site_name = validator.plan.get("site", "SmartBranch360")
    reporter = AssuranceReportGenerator(
        site_name=site_name,
        plan_findings=plan_findings,
        assurance_findings=assurance_findings,
        security_findings=security_findings,
        fault_reports=fault_reports,
        device_summary=device_summary
    )

    fmt = args.report.lower()
    if fmt in ("term", "terminal"):
        output = reporter.generate_terminal()
        print(output)
    elif fmt == "html":
        output = reporter.generate_html()
        if args.output_file:
            Path(args.output_file).write_text(output, encoding="utf-8")
            print(f"[SUCCESS] HTML report saved to: {args.output_file}")
        else:
            print(output)
    elif fmt == "json":
        output = reporter.generate_json()
        if args.output_file:
            Path(args.output_file).write_text(output, encoding="utf-8")
            print(f"[SUCCESS] JSON report saved to: {args.output_file}")
        else:
            print(output)

    # Return code: 1 if failures exist, 0 otherwise
    return 1 if reporter.fail_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())

