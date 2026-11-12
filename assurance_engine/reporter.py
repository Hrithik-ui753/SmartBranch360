"""Report Generation Module for SmartBranch360.

Produces Terminal, HTML, and JSON network assurance reports complete with
health scores, security compliance indices, and remediation plans.
"""

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from .validator import ValidationFinding
from .fault_detector import FaultScenarioReport


class AssuranceReportGenerator:
    """Generates multi-format assurance reports from findings and device audits."""

    def __init__(
        self,
        site_name: str,
        plan_findings: List[ValidationFinding],
        assurance_findings: List[ValidationFinding],
        security_findings: List[ValidationFinding],
        fault_reports: Optional[List[FaultScenarioReport]] = None,
        device_summary: Optional[Dict[str, Any]] = None
    ):
        self.site_name = site_name
        self.plan_findings = plan_findings
        self.assurance_findings = assurance_findings
        self.security_findings = security_findings
        self.fault_reports = fault_reports or []
        self.device_summary = device_summary or {}
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.all_findings = plan_findings + assurance_findings + security_findings
        self.pass_count = sum(1 for f in self.all_findings if f.status == "PASS")
        self.fail_count = sum(1 for f in self.all_findings if f.status == "FAIL")
        self.warn_count = sum(1 for f in self.all_findings if f.status == "WARNING")
        self.total_checks = len(self.all_findings)

        self.health_score = self._compute_health_score()

    def _compute_health_score(self) -> int:
        """Computes weighted network health score out of 100."""
        if self.total_checks == 0:
            return 0
        # Failed check drops score significantly; warnings drop slightly
        score = 100.0 - (self.fail_count * 12.0) - (self.warn_count * 3.0)
        return max(0, min(100, int(score)))

    def generate_json(self) -> str:
        """Returns JSON serialized report."""
        payload = {
            "site": self.site_name,
            "timestamp": self.timestamp,
            "health_score": self.health_score,
            "metrics": {
                "total_checks": self.total_checks,
                "passed": self.pass_count,
                "failed": self.fail_count,
                "warnings": self.warn_count
            },
            "findings": {
                "plan": [self._finding_to_dict(f) for f in self.plan_findings],
                "assurance": [self._finding_to_dict(f) for f in self.assurance_findings],
                "security": [self._finding_to_dict(f) for f in self.security_findings]
            },
            "faults": [
                {
                    "id": f.id,
                    "title": f.title,
                    "affected_device": f.affected_device,
                    "status": f.status,
                    "explanation": f.problem_explanation,
                    "impact": f.potential_impact,
                    "evidence": f.detected_evidence,
                    "remediation": f.corrective_action,
                    "expected_result": f.expected_result_after_fix
                }
                for f in self.fault_reports
            ],
            "devices": self.device_summary
        }
        return json.dumps(payload, indent=2)

    def generate_terminal(self) -> str:
        """Returns colorized, readable ANSI terminal output."""
        lines = []
        bar = "=" * 70
        sub_bar = "-" * 70

        lines.append(bar)
        lines.append(f"  SMARTBRANCH360 - NETWORK ASSURANCE & SECURITY AUDIT REPORT")
        lines.append(f"  Site: {self.site_name} | Generated: {self.timestamp}")
        lines.append(bar)
        lines.append(f"  Network Health Score: {self.health_score}% | Status: {'HEALTHY' if self.health_score >= 80 else 'DEGRADED' if self.health_score >= 50 else 'CRITICAL'}")
        lines.append(f"  Checks: {self.total_checks} Total | {self.pass_count} Passed | {self.fail_count} Failed | {self.warn_count} Warnings")
        lines.append(sub_bar)

        sections = [
            ("PLAN & ARCHITECTURE VALIDATION", self.plan_findings),
            ("CONFIGURATION ASSURANCE (CLOSED-LOOP)", self.assurance_findings),
            ("SECURITY AUDIT & COMPLIANCE", self.security_findings)
        ]

        for sec_title, findings in sections:
            lines.append(f"\n[ {sec_title} ]")
            if not findings:
                lines.append("  (No checks evaluated)")
                continue
            for f in findings:
                tag = f"[{f.status}]"
                prefix = f"  {tag:<10} [{f.category}]"
                lines.append(f"{prefix} {f.message}")
                if f.status == "FAIL" and f.remediation:
                    lines.append(f"             --> Remediation: {f.remediation.replace(chr(10), ' ')}")

        if self.fault_reports:
            lines.append(f"\n[ FAULT DIAGNOSIS & BENCHMARKS ]")
            for flt in self.fault_reports:
                st_tag = f"[{flt.status}]"
                lines.append(f"  {st_tag:<10} {flt.id}: {flt.title} ({flt.affected_device})")
                lines.append(f"             Evidence: {flt.detected_evidence}")
                lines.append(f"             Remediation: {flt.corrective_action.splitlines()[0]}")

        lines.append("\n" + bar)
        lines.append("  ASSURANCE VERDICT: " + ("PASS - Network Compliant with Blueprint" if self.fail_count == 0 else f"FAIL - {self.fail_count} Critical Violation(s) Require Correction"))
        lines.append(bar + "\n")

        return "\n".join(lines)

    def generate_html(self) -> str:
        """Returns a standalone, modern HTML5 dashboard report."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SmartBranch360 - Network Assurance Report</title>
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --pass: #10b981;
      --fail: #ef4444;
      --warn: #f59e0b;
      --accent: #3b82f6;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
    body {{ background: var(--bg); color: var(--text); padding: 2rem; line-height: 1.5; }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 1.5rem; margin-bottom: 2rem; }}
    .title h1 {{ font-size: 1.8rem; font-weight: 700; color: #fff; }}
    .title p {{ color: var(--text-muted); font-size: 0.9rem; margin-top: 0.25rem; }}
    .score-badge {{ display: flex; align-items: center; gap: 1rem; background: var(--card-bg); padding: 0.75rem 1.5rem; border-radius: 0.75rem; border: 1px solid var(--border); }}
    .score-circle {{ font-size: 2rem; font-weight: 800; color: {'var(--pass)' if self.health_score >= 80 else 'var(--warn)' if self.health_score >= 50 else 'var(--fail)'}; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
    .metric-card {{ background: var(--card-bg); border: 1px solid var(--border); padding: 1.25rem; border-radius: 0.75rem; }}
    .metric-card .num {{ font-size: 2rem; font-weight: 700; margin-top: 0.5rem; }}
    .section-title {{ font-size: 1.25rem; font-weight: 600; margin: 2rem 0 1rem 0; display: flex; align-items: center; gap: 0.5rem; }}
    table {{ width: 100%; border-collapse: collapse; background: var(--card-bg); border-radius: 0.75rem; overflow: hidden; margin-bottom: 2rem; border: 1px solid var(--border); }}
    th, td {{ padding: 0.85rem 1rem; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.9rem; }}
    th {{ background: #162032; font-weight: 600; color: var(--text-muted); text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }}
    tr:last-child td {{ border-bottom: none; }}
    .badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }}
    .badge-PASS {{ background: rgba(16, 185, 129, 0.2); color: var(--pass); border: 1px solid rgba(16, 185, 129, 0.4); }}
    .badge-FAIL {{ background: rgba(239, 68, 68, 0.2); color: var(--fail); border: 1px solid rgba(239, 68, 68, 0.4); }}
    .badge-WARNING {{ background: rgba(245, 158, 11, 0.2); color: var(--warn); border: 1px solid rgba(245, 158, 11, 0.4); }}
    .remedy {{ color: #cbd5e1; font-family: monospace; font-size: 0.8rem; background: #0b1120; padding: 0.4rem 0.6rem; border-radius: 0.35rem; margin-top: 0.35rem; display: block; border-left: 3px solid var(--accent); }}
    .fault-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 0.75rem; padding: 1.25rem; margin-bottom: 1rem; }}
    .fault-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; }}
    .fault-title {{ font-weight: 600; font-size: 1.05rem; }}
    footer {{ border-top: 1px solid var(--border); padding-top: 1.5rem; color: var(--text-muted); font-size: 0.85rem; text-align: center; margin-top: 3rem; }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="title">
        <h1>SmartBranch360 Network Assurance Report</h1>
        <p>Site: <strong>{self.site_name}</strong> &bull; Generated: {self.timestamp}</p>
      </div>
      <div class="score-badge">
        <div>
          <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Network Health</div>
          <div style="font-weight: 600;">{'Optimal' if self.health_score >= 90 else 'Action Required'}</div>
        </div>
        <div class="score-circle">{self.health_score}%</div>
      </div>
    </header>

    <div class="grid">
      <div class="metric-card">
        <div style="color: var(--text-muted); font-size: 0.85rem;">Total Checks</div>
        <div class="num">{self.total_checks}</div>
      </div>
      <div class="metric-card">
        <div style="color: var(--pass); font-size: 0.85rem;">Passed Checks</div>
        <div class="num" style="color: var(--pass);">{self.pass_count}</div>
      </div>
      <div class="metric-card">
        <div style="color: var(--fail); font-size: 0.85rem;">Critical Failures</div>
        <div class="num" style="color: var(--fail);">{self.fail_count}</div>
      </div>
      <div class="metric-card">
        <div style="color: var(--warn); font-size: 0.85rem;">Warnings</div>
        <div class="num" style="color: var(--warn);">{self.warn_count}</div>
      </div>
    </div>

    <div class="section-title">Network Plan & Blueprint Invariants</div>
    <table>
      <thead>
        <tr><th style="width: 100px;">Status</th><th style="width: 140px;">Category</th><th>Verification Item</th></tr>
      </thead>
      <tbody>
        {self._render_table_rows(self.plan_findings)}
      </tbody>
    </table>

    <div class="section-title">Configuration Assurance (Intended vs Actual State)</div>
    <table>
      <thead>
        <tr><th style="width: 100px;">Status</th><th style="width: 160px;">Category</th><th>Assurance Finding</th></tr>
      </thead>
      <tbody>
        {self._render_table_rows(self.assurance_findings)}
      </tbody>
    </table>

    <div class="section-title">Security & Hardening Audit</div>
    <table>
      <thead>
        <tr><th style="width: 100px;">Status</th><th style="width: 160px;">Category</th><th>Security Compliance Finding</th></tr>
      </thead>
      <tbody>
        {self._render_table_rows(self.security_findings)}
      </tbody>
    </table>

    <div class="section-title">Automated Fault Detection & Diagnostic Benchmark</div>
    {self._render_fault_cards()}

    <footer>
      SmartBranch360 Enterprise Assurance System &bull; Cisco Packet Tracer Certified Blueprint &bull; College &amp; Portfolio Production Standard
    </footer>
  </div>
</body>
</html>"""
        return html

    def _render_table_rows(self, findings: List[ValidationFinding]) -> str:
        if not findings:
            return '<tr><td colspan="3" style="text-align: center; color: var(--text-muted);">No findings recorded.</td></tr>'
        rows = []
        for f in findings:
            remedy_html = f'<span class="remedy">Remediation: {f.remediation}</span>' if (f.status == "FAIL" and f.remediation) else ''
            rows.append(f"""
              <tr>
                <td><span class="badge badge-{f.status}">{f.status}</span></td>
                <td><strong>{f.category}</strong></td>
                <td>{f.message}{remedy_html}</td>
              </tr>
            """)
        return "".join(rows)

    def _render_fault_cards(self) -> str:
        if not self.fault_reports:
            return '<p style="color: var(--text-muted); margin-bottom: 2rem;">No fault scenarios evaluated.</p>'
        cards = []
        for flt in self.fault_reports:
            badge_class = "badge-FAIL" if flt.status == "DETECTED" else "badge-PASS"
            cards.append(f"""
              <div class="fault-card">
                <div class="fault-header">
                  <div class="fault-title">{flt.id}: {flt.title} &mdash; <span style="color: var(--accent);">{flt.affected_device}</span></div>
                  <span class="badge {badge_class}">{flt.status}</span>
                </div>
                <p style="margin-bottom: 0.5rem; color: #cbd5e1;">{flt.problem_explanation}</p>
                <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem;"><strong>Impact:</strong> {flt.potential_impact}</p>
                <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem;"><strong>Evidence:</strong> <code style="color: #f1f5f9;">{flt.detected_evidence}</code></p>
                <div class="remedy"><strong>Corrective Action:</strong><br>{flt.corrective_action}</div>
              </div>
            """)
        return "".join(cards)

    def _finding_to_dict(self, finding: ValidationFinding) -> Dict[str, Any]:
        return {
            "status": finding.status,
            "code": finding.code,
            "category": finding.category,
            "message": finding.message,
            "remediation": finding.remediation,
            "details": finding.details
        }

