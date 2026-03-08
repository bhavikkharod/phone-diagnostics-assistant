"""
=============================================================================
MODULE 4: DIAGNOSTICS PASSPORT GENERATOR
=============================================================================

PURPOSE:
    Takes the full output of the diagnostic pipeline and generates
    the Diagnostics Passport — the structured document that travels
    with the customer from self-service to the Genius Bar.

    This is the C1 solution from our Opportunity Solution Tree:
    "A structured diagnostic report generated during self-service triage
     that automatically transfers to the Genius Bar."

WHAT THE PASSPORT CONTAINS:
    1. Device identity and coverage status
    2. Customer-reported symptoms (in their own words)
    3. Self-service diagnostics results (every test, pass/warn/fail)
    4. Root cause analysis with confidence level
    5. Recommended repair and pre-ordered parts
    6. Evidence chain (how we arrived at the diagnosis)
    7. Genius-specific technical notes
    8. Estimated repair time

WHY THIS CUTS MTTR:
    Without passport: Genius spends 3-5 min on intake → 5-10 min
    running diagnostics → 5 min interpreting → decision.
    Total: 13-20 min before repair even starts.

    With passport: Genius reads passport (1 min) → confirms with
    targeted inspection (2-3 min) → begins repair.
    Total: 3-4 min to start repair. That's a 70-80% reduction
    in pre-repair time.

=============================================================================
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from system_report_simulator import DeviceSystemReport
from log_parser import Finding
from log_analyzer import RootCauseAnalysis, CustomerSymptom


# ---------------------------------------------------------------------------
# The Diagnostics Passport
# ---------------------------------------------------------------------------

@dataclass
class DiagnosticsPassport:
    """
    The complete Diagnostics Passport document.

    This travels with the customer from self-service → appointment booking
    → Genius Bar. The Genius sees it on their internal tool when the
    customer checks in.
    """
    # Passport metadata
    passport_id: str
    generated_at: str
    generated_by: str           # "self_service_diagnostic" or "in_store"

    # Device identity
    device_model: str
    serial_number: str
    os_version: str
    applecare_status: str
    device_age_months: int

    # Customer input
    customer_symptoms: List[str]

    # Diagnostic results
    findings_summary: dict      # Counts by severity
    critical_findings: List[dict]
    warning_findings: List[dict]
    info_findings: List[dict]
    all_subsystems_checked: List[str]
    subsystems_passing: List[str]
    subsystems_flagged: List[str]

    # Root cause analysis
    root_cause: str
    confidence: str
    confidence_pct: int
    evidence_chain: List[str]
    can_self_resolve: bool
    self_resolve_steps: List[str]

    # Repair recommendation (for Genius)
    recommended_repair: str
    parts_needed: List[str]
    estimated_repair_minutes: int
    secondary_actions: List[str]
    genius_notes: str

    # Appointment context
    appointment_recommendation: str  # "not_needed", "recommended", "urgent"
    pre_order_parts: bool


# ---------------------------------------------------------------------------
# Passport Generator
# ---------------------------------------------------------------------------

class PassportGenerator:
    """
    Generates a Diagnostics Passport from the diagnostic pipeline outputs.

    USAGE:
        generator = PassportGenerator()
        passport = generator.generate(
            report=device_system_report,
            findings=parsed_findings,
            analysis=root_cause_analysis,
            symptoms=customer_symptoms
        )

        # Print the customer-facing view
        generator.print_customer_view(passport)

        # Print the Genius-facing view
        generator.print_genius_view(passport)
    """

    def generate(self,
                 report: DeviceSystemReport,
                 findings: List[Finding],
                 analysis: RootCauseAnalysis,
                 symptoms: List[CustomerSymptom]) -> DiagnosticsPassport:
        """
        Generate a complete Diagnostics Passport.
        """
        # Categorize findings
        critical = [f for f in findings if f.severity == "critical"]
        warnings = [f for f in findings if f.severity == "warning"]
        infos = [f for f in findings if f.severity == "info"]

        # All subsystems we checked
        all_subsystems = [
            "battery", "storage", "connectivity",
            "display", "sensors", "camera", "system", "software"
        ]
        flagged = list(set(f.subsystem for f in findings
                           if f.severity in ("critical", "warning")))
        passing = [s for s in all_subsystems if s not in flagged]

        # Determine appointment urgency
        if critical:
            appt_rec = "urgent"
        elif warnings and not analysis.can_self_resolve:
            appt_rec = "recommended"
        elif analysis.can_self_resolve:
            appt_rec = "not_needed"
        else:
            appt_rec = "recommended"

        # Should we pre-order parts?
        pre_order = (analysis.confidence_pct >= 75
                     and len(analysis.parts_needed) > 0)

        # Generate passport ID
        passport_id = (f"DX-{report.serial_number[:6]}-"
                       f"{datetime.now().strftime('%Y%m%d%H%M')}")

        return DiagnosticsPassport(
            passport_id=passport_id,
            generated_at=datetime.now().isoformat(),
            generated_by="self_service_diagnostic",
            device_model=report.device_model,
            serial_number=report.serial_number,
            os_version=report.os_version,
            applecare_status=report.applecare_status,
            device_age_months=report.device_age_months,
            customer_symptoms=[s.description for s in symptoms],
            findings_summary={
                "critical": len(critical),
                "warning": len(warnings),
                "info": len(infos),
                "total": len(findings),
            },
            critical_findings=[
                {"subsystem": f.subsystem, "title": f.title,
                 "detail": f.detail, "code": f.code}
                for f in critical
            ],
            warning_findings=[
                {"subsystem": f.subsystem, "title": f.title,
                 "detail": f.detail, "code": f.code}
                for f in warnings
            ],
            info_findings=[
                {"subsystem": f.subsystem, "title": f.title,
                 "detail": f.detail, "code": f.code}
                for f in infos
            ],
            all_subsystems_checked=all_subsystems,
            subsystems_passing=passing,
            subsystems_flagged=flagged,
            root_cause=analysis.root_cause,
            confidence=analysis.confidence,
            confidence_pct=analysis.confidence_pct,
            evidence_chain=analysis.evidence_chain,
            can_self_resolve=analysis.can_self_resolve,
            self_resolve_steps=analysis.self_resolve_steps,
            recommended_repair=analysis.primary_repair,
            parts_needed=analysis.parts_needed,
            estimated_repair_minutes=analysis.estimated_repair_minutes,
            secondary_actions=analysis.secondary_actions,
            genius_notes=analysis.genius_notes,
            appointment_recommendation=appt_rec,
            pre_order_parts=pre_order,
        )

    # ------------------------------------------------------------------
    # CUSTOMER-FACING VIEW
    # ------------------------------------------------------------------
    # This is what the customer sees on their phone / Apple Support app.
    # It's designed to be clear, non-technical, and actionable.
    # ------------------------------------------------------------------

    def print_customer_view(self, passport: DiagnosticsPassport):
        """Print the customer-facing Diagnostics Passport view."""

        w = 62  # Width of the passport display

        print()
        print("+" + "=" * w + "+")
        print("|" + " DIAGNOSTICS PASSPORT ".center(w) + "|")
        print("|" + f" Your Device Health Report ".center(w) + "|")
        print("+" + "=" * w + "+")

        # Device info
        print("|" + "".center(w) + "|")
        print("|" + f"  Device:    {passport.device_model}".ljust(w) + "|")
        print("|" + f"  Serial:    {passport.serial_number}".ljust(w) + "|")
        print("|" + f"  iOS:       {passport.os_version}".ljust(w) + "|")

        ac_display = {
            "active": "Active (covered)",
            "expired": "Expired",
            "none": "Not enrolled"
        }
        print("|" + f"  AppleCare: {ac_display.get(passport.applecare_status, passport.applecare_status)}".ljust(w) + "|")
        print("|" + "".center(w) + "|")
        print("+" + "-" * w + "+")

        # What you told us
        print("|" + " WHAT YOU TOLD US ".center(w) + "|")
        print("+" + "-" * w + "+")
        for symptom in passport.customer_symptoms:
            # Word-wrap long symptoms
            while symptom:
                line = symptom[:w - 4]
                print("|" + f"  \"{line}\"".ljust(w) + "|")
                symptom = symptom[w - 4:]
        print("|" + "".center(w) + "|")
        print("+" + "-" * w + "+")

        # Subsystem status
        print("|" + " WHAT WE CHECKED ".center(w) + "|")
        print("+" + "-" * w + "+")

        for subsystem in passport.all_subsystems_checked:
            if subsystem in passport.subsystems_passing:
                icon = "PASS"
                print("|" + f"  [ {icon} ] {subsystem.title()}".ljust(w) + "|")
            elif subsystem in passport.subsystems_flagged:
                # Find the worst severity for this subsystem
                is_critical = any(f["subsystem"] == subsystem
                                  for f in passport.critical_findings)
                if is_critical:
                    icon = "FAIL"
                else:
                    icon = "WARN"
                print("|" + f"  [ {icon} ] {subsystem.title()}".ljust(w) + "|")

        print("|" + "".center(w) + "|")
        print("+" + "-" * w + "+")

        # What we found
        print("|" + " WHAT WE FOUND ".center(w) + "|")
        print("+" + "-" * w + "+")

        for f in passport.critical_findings:
            title = f["title"][:w - 10]
            print("|" + f"  [!!!] {title}".ljust(w) + "|")

        for f in passport.warning_findings:
            title = f["title"][:w - 10]
            print("|" + f"  [ ! ] {title}".ljust(w) + "|")

        for f in passport.info_findings:
            title = f["title"][:w - 10]
            print("|" + f"  [ i ] {title}".ljust(w) + "|")

        if not (passport.critical_findings or passport.warning_findings):
            print("|" + "  Everything looks good!".ljust(w) + "|")

        print("|" + "".center(w) + "|")
        print("+" + "-" * w + "+")

        # Recommendation
        print("|" + " OUR RECOMMENDATION ".center(w) + "|")
        print("+" + "-" * w + "+")

        if passport.can_self_resolve:
            print("|" + "  You can likely resolve this yourself:".ljust(w) + "|")
            print("|" + "".center(w) + "|")
            for i, step in enumerate(passport.self_resolve_steps, 1):
                # Word-wrap steps
                step_text = f"  {i}. {step}"
                while step_text:
                    line = step_text[:w - 2]
                    print("|" + f"  {line}".ljust(w) + "|")
                    step_text = step_text[w - 2:]

        else:
            rec = passport.recommended_repair[:w - 4]
            print("|" + f"  {rec}".ljust(w) + "|")
            if passport.parts_needed:
                print("|" + "".center(w) + "|")
                print("|" + "  Parts have been identified for your repair.".ljust(w) + "|")
            if passport.estimated_repair_minutes:
                print("|" + f"  Estimated repair time: ~{passport.estimated_repair_minutes} min".ljust(w) + "|")

        print("|" + "".center(w) + "|")

        # Appointment CTA
        if passport.appointment_recommendation == "urgent":
            print("|" + "".center(w) + "|")
            print("|" + "  >>> BOOK GENIUS BAR APPOINTMENT <<<".center(w) + "|")
            print("|" + "  Parts will be pre-staged at your store".center(w) + "|")
        elif passport.appointment_recommendation == "recommended":
            print("|" + "".center(w) + "|")
            print("|" + "  >> Book a Genius Bar appointment <<".center(w) + "|")
        else:
            print("|" + "".center(w) + "|")
            print("|" + "  Try the steps above. If the issue persists,".center(w) + "|")
            print("|" + "  your passport will update automatically.".center(w) + "|")

        print("|" + "".center(w) + "|")
        print("|" + f"  Passport ID: {passport.passport_id}".ljust(w) + "|")
        confidence_display = f"  Diagnostic confidence: {passport.confidence} ({passport.confidence_pct}%)"
        print("|" + confidence_display.ljust(w) + "|")
        print("+" + "=" * w + "+")
        print()

    # ------------------------------------------------------------------
    # GENIUS-FACING VIEW
    # ------------------------------------------------------------------
    # This is what the Genius sees on their internal tool when the
    # customer checks in. It's technical, actionable, and designed
    # to eliminate re-intake and get straight to repair.
    # ------------------------------------------------------------------

    def print_genius_view(self, passport: DiagnosticsPassport):
        """Print the Genius-facing Diagnostics Passport view."""

        w = 72

        print()
        print("+" + "=" * w + "+")
        print("|" + " GENIUS DIAGNOSTICS PASSPORT ".center(w) + "|")
        print("|" + " [INTERNAL — PRE-TRIAGE COMPLETE] ".center(w) + "|")
        print("+" + "=" * w + "+")

        # Quick reference header
        print("|" + "".center(w) + "|")
        print("|" + f"  Passport:  {passport.passport_id}".ljust(w) + "|")
        print("|" + f"  Device:    {passport.device_model} ({passport.device_age_months}mo)".ljust(w) + "|")
        print("|" + f"  Serial:    {passport.serial_number}".ljust(w) + "|")
        print("|" + f"  iOS:       {passport.os_version}".ljust(w) + "|")
        print("|" + f"  AppleCare: {passport.applecare_status.upper()}".ljust(w) + "|")
        print("|" + "".center(w) + "|")

        # Customer symptoms
        print("+" + "-" * w + "+")
        print("|" + " CUSTOMER-REPORTED SYMPTOMS ".ljust(w) + "|")
        print("+" + "-" * w + "+")
        for symptom in passport.customer_symptoms:
            while symptom:
                line = symptom[:w - 4]
                print("|" + f"  > {line}".ljust(w) + "|")
                symptom = symptom[w - 4:]
        print("|" + "".center(w) + "|")

        # Root cause (the key section)
        print("+" + "-" * w + "+")
        print("|" + " ROOT CAUSE ANALYSIS ".ljust(w) + "|")
        conf_str = f"Confidence: {passport.confidence.upper()} ({passport.confidence_pct}%)"
        print("|" + f"  {conf_str}".ljust(w) + "|")
        print("+" + "-" * w + "+")

        # Word-wrap root cause
        root = passport.root_cause
        while root:
            line = root[:w - 4]
            print("|" + f"  {line}".ljust(w) + "|")
            root = root[w - 4:]
        print("|" + "".center(w) + "|")

        # Evidence chain
        print("+" + "-" * w + "+")
        print("|" + " EVIDENCE CHAIN ".ljust(w) + "|")
        print("+" + "-" * w + "+")
        for i, step in enumerate(passport.evidence_chain, 1):
            step_text = f"  {i}. {step}"
            while step_text:
                line = step_text[:w - 2]
                print("|" + f"{line}".ljust(w) + "|")
                step_text = step_text[w - 2:]
        print("|" + "".center(w) + "|")

        # All findings detail
        print("+" + "-" * w + "+")
        print("|" + " DIAGNOSTIC FINDINGS ".ljust(w) + "|")
        summary = (f"  {passport.findings_summary['critical']} critical | "
                   f"{passport.findings_summary['warning']} warning | "
                   f"{passport.findings_summary['info']} info")
        print("|" + summary.ljust(w) + "|")
        print("+" + "-" * w + "+")

        for f in passport.critical_findings:
            title = f"  [CRITICAL] {f['title']}"[:w]
            print("|" + title.ljust(w) + "|")
            detail = f"    {f['detail']}"
            while detail:
                line = detail[:w - 2]
                print("|" + f"{line}".ljust(w) + "|")
                detail = detail[w - 2:]

        for f in passport.warning_findings:
            title = f"  [WARNING]  {f['title']}"[:w]
            print("|" + title.ljust(w) + "|")

        for f in passport.info_findings:
            title = f"  [INFO]     {f['title']}"[:w]
            print("|" + title.ljust(w) + "|")

        print("|" + "".center(w) + "|")

        # Repair recommendation
        print("+" + "-" * w + "+")
        print("|" + " REPAIR RECOMMENDATION ".ljust(w) + "|")
        print("+" + "-" * w + "+")
        print("|" + f"  Action:    {passport.recommended_repair}".ljust(w) + "|")
        if passport.parts_needed:
            parts = ", ".join(passport.parts_needed)
            print("|" + f"  Parts:     {parts[:w-14]}".ljust(w) + "|")
            if passport.pre_order_parts:
                print("|" + "  Status:    PRE-ORDER REQUESTED".ljust(w) + "|")
        print("|" + f"  Est. Time: {passport.estimated_repair_minutes} minutes".ljust(w) + "|")

        if passport.secondary_actions:
            print("|" + "".center(w) + "|")
            print("|" + "  Additional actions:".ljust(w) + "|")
            for action in passport.secondary_actions:
                act_line = f"    - {action}"[:w]
                print("|" + act_line.ljust(w) + "|")
        print("|" + "".center(w) + "|")

        # Genius notes (the personalized expert guidance)
        print("+" + "-" * w + "+")
        print("|" + " TECHNICIAN NOTES ".ljust(w) + "|")
        print("+" + "-" * w + "+")
        notes = passport.genius_notes
        while notes:
            line = notes[:w - 4]
            print("|" + f"  {line}".ljust(w) + "|")
            notes = notes[w - 4:]
        print("|" + "".center(w) + "|")

        print("+" + "=" * w + "+")
        print()


# ---------------------------------------------------------------------------
# Quick Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from system_report_simulator import DeviceReportSimulator
    from log_parser import LogParser
    from log_analyzer import LogAnalyzer, CustomerSymptom

    sim = DeviceReportSimulator()
    parser = LogParser()
    analyzer = LogAnalyzer()
    generator = PassportGenerator()

    # Scenario: Camera malfunction
    print("\n" + "=" * 70)
    print("DEMO SCENARIO: Camera module failure")
    print("Customer says: 'My camera shows a black screen and photos")
    print("are blurry. I also see some spots on my photos.'")
    print("=" * 70)

    report = sim.generate("camera_malfunction")
    findings = parser.parse(report)
    symptoms = [
        CustomerSymptom(
            description="My camera shows a black screen and photos are blurry. I also see some spots on my photos.",
            category="camera",
            keywords=["camera", "black", "blurry", "photo", "spots"]
        )
    ]
    analysis = analyzer.analyze(findings, symptoms)
    passport = generator.generate(report, findings, analysis, symptoms)

    print("\n--- CUSTOMER VIEW ---")
    generator.print_customer_view(passport)

    print("\n--- GENIUS VIEW ---")
    generator.print_genius_view(passport)
