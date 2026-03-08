"""
=============================================================================
MODULE 5: TRIAGE ENGINE — The Orchestrator
=============================================================================

PURPOSE:
    This is the top-level orchestrator that ties the full pipeline together.
    It simulates the complete customer self-service triage flow:

    Customer reports symptoms
        → Device system report is pulled
        → Logs are parsed for abnormalities
        → Findings are cross-referenced with symptoms (triangulation)
        → Root cause is identified with confidence level
        → Diagnostics Passport is generated
        → Customer gets clear next steps
        → Genius gets actionable repair plan with pre-ordered parts

ARCHITECTURE OVERVIEW:

    ┌──────────────────┐     ┌──────────────────┐
    │  Customer Input   │     │  Device System    │
    │  (symptoms, desc) │     │  Report (logs,    │
    │                   │     │  sensors, health) │
    └────────┬──────────┘     └────────┬──────────┘
             │                         │
             │    ┌────────────────┐   │
             └───→│  LOG PARSER    │←──┘
                  │  (Module 2)    │
                  │  Extracts      │
                  │  findings      │
                  └───────┬────────┘
                          │
                  ┌───────▼────────┐
                  │  LOG ANALYZER  │
                  │  (Module 3)    │
                  │  Triangulates  │
                  │  root cause    │
                  └───────┬────────┘
                          │
                  ┌───────▼────────┐
                  │  PASSPORT GEN  │
                  │  (Module 4)    │
                  │  Creates the   │
                  │  passport doc  │
                  └───────┬────────┘
                          │
             ┌────────────┼────────────┐
             ▼                         ▼
    ┌────────────────┐      ┌────────────────────┐
    │  Customer View  │      │  Genius View        │
    │  (plain lang,   │      │  (technical, parts, │
    │  next steps)    │      │  repair plan)       │
    └─────────────────┘      └─────────────────────┘

=============================================================================
"""

from system_report_simulator import DeviceReportSimulator, DeviceSystemReport
from log_parser import LogParser, Finding
from log_analyzer import LogAnalyzer, CustomerSymptom, RootCauseAnalysis
from diagnostics_passport import PassportGenerator, DiagnosticsPassport
from typing import List, Tuple


class TriageEngine:
    """
    The main orchestrator for the self-service diagnostics system.

    USAGE:
        engine = TriageEngine()

        # Run a complete triage
        passport = engine.run_triage(
            device_profile="battery_degraded",
            customer_description="My phone dies at 40% and gets really hot",
            symptom_category="battery",
            symptom_keywords=["dies", "battery", "hot", "percentage"]
        )

        # Or run with multiple symptoms
        passport = engine.run_triage_multi(
            device_profile="multi_failure",
            symptoms=[
                ("Screen flickers randomly", "display",
                 ["screen", "flicker", "randomly"]),
                ("Battery dies fast", "battery",
                 ["battery", "dies", "drain"]),
                ("Wi-Fi keeps dropping", "connectivity",
                 ["wifi", "drops", "connection"]),
            ]
        )
    """

    def __init__(self):
        self.simulator = DeviceReportSimulator()
        self.parser = LogParser()
        self.analyzer = LogAnalyzer()
        self.passport_gen = PassportGenerator()

    def run_triage(self,
                   device_profile: str,
                   customer_description: str,
                   symptom_category: str,
                   symptom_keywords: List[str],
                   device_model: str = None,
                   show_output: bool = True
                   ) -> Tuple[DiagnosticsPassport, DeviceSystemReport,
                              List[Finding], RootCauseAnalysis]:
        """
        Run the complete triage pipeline for a single symptom.

        Returns:
            Tuple of (passport, report, findings, analysis)
        """
        symptoms = [
            CustomerSymptom(
                description=customer_description,
                category=symptom_category,
                keywords=symptom_keywords,
            )
        ]
        return self._execute_pipeline(device_profile, symptoms,
                                      device_model, show_output)

    def run_triage_multi(self,
                         device_profile: str,
                         symptoms: List[Tuple[str, str, List[str]]],
                         device_model: str = None,
                         show_output: bool = True
                         ) -> Tuple[DiagnosticsPassport, DeviceSystemReport,
                                    List[Finding], RootCauseAnalysis]:
        """
        Run triage with multiple customer-reported symptoms.

        Args:
            symptoms: List of (description, category, keywords) tuples
        """
        customer_symptoms = [
            CustomerSymptom(
                description=desc,
                category=cat,
                keywords=kw,
            )
            for desc, cat, kw in symptoms
        ]
        return self._execute_pipeline(device_profile, customer_symptoms,
                                      device_model, show_output)

    def _execute_pipeline(self, device_profile, symptoms,
                          device_model, show_output):
        """Execute the full diagnostic pipeline."""

        if show_output:
            print("\n" + "=" * 70)
            print(" APPLECARE SELF-SERVICE DIAGNOSTICS")
            print(" Running pre-triage diagnostic pipeline...")
            print("=" * 70)

        # Step 1: Get device system report
        if show_output:
            print("\n  [1/4] Pulling device system report...")
        report = self.simulator.generate(device_profile, device_model)
        if show_output:
            print(f"        Device: {report.device_model}")
            print(f"        Serial: {report.serial_number}")
            print(f"        OS: {report.os_version}")

        # Step 2: Parse logs for findings
        if show_output:
            print("\n  [2/4] Analyzing device logs and sensor data...")
        findings = self.parser.parse(report)
        if show_output:
            critical = sum(1 for f in findings if f.severity == "critical")
            warnings = sum(1 for f in findings if f.severity == "warning")
            infos = sum(1 for f in findings if f.severity == "info")
            print(f"        Found: {critical} critical, "
                  f"{warnings} warnings, {infos} info")

        # Step 3: Triangulate root cause
        if show_output:
            print("\n  [3/4] Cross-referencing symptoms with device data...")
            print(f"        Symptoms: {len(symptoms)} reported")
            print(f"        Running {len(findings)} findings through "
                  f"correlation engine...")
        analysis = self.analyzer.analyze(findings, symptoms)
        if show_output:
            print(f"        Root cause identified: "
                  f"{analysis.confidence} confidence "
                  f"({analysis.confidence_pct}%)")

        # Step 4: Generate passport
        if show_output:
            print("\n  [4/4] Generating Diagnostics Passport...")
        passport = self.passport_gen.generate(
            report, findings, analysis, symptoms
        )
        if show_output:
            print(f"        Passport ID: {passport.passport_id}")
            if passport.pre_order_parts:
                print(f"        Parts pre-order: REQUESTED")
            print(f"        Appointment: {passport.appointment_recommendation}")
            print("\n  Pipeline complete.")

        # Display passport views
        if show_output:
            print("\n\n")
            print("=" * 70)
            print(" CUSTOMER VIEW")
            print(" (What the customer sees on their Apple Support app)")
            print("=" * 70)
            self.passport_gen.print_customer_view(passport)

            print("\n")
            print("=" * 70)
            print(" GENIUS VIEW")
            print(" (What the Genius sees when customer checks in)")
            print("=" * 70)
            self.passport_gen.print_genius_view(passport)

        return passport, report, findings, analysis


# ---------------------------------------------------------------------------
# DEMO SCENARIOS
# ---------------------------------------------------------------------------
# These demonstrate the key value propositions of the diagnostic system.
# Each scenario shows how the system handles a different type of case.

DEMO_SCENARIOS = {
    "battery": {
        "title": "Battery Degradation with Thermal Issues",
        "story": (
            "Sarah's iPhone 14 Pro has been dying at 40% battery and gets\n"
            "very hot during charging. She's visited the Genius Bar once\n"
            "before and was told to 'monitor it.' She's frustrated."
        ),
        "profile": "battery_degraded",
        "description": "My phone dies at 40% battery and gets really hot when charging. I already went to the Genius Bar and they said to monitor it.",
        "category": "battery",
        "keywords": ["dies", "battery", "hot", "charging", "40%", "shutdown"],
    },

    "display": {
        "title": "Intermittent Display Flicker (The Repeat Visit Killer)",
        "story": (
            "Mike's iPhone 15 Pro screen flickers randomly, especially\n"
            "when using the camera. He's been to the store TWICE and\n"
            "both times diagnostics 'passed.' He's about to switch to Samsung."
        ),
        "profile": "display_intermittent",
        "description": "My screen flickers randomly, especially when I open the camera. I've been to the Genius Bar twice and they keep telling me diagnostics pass.",
        "category": "display",
        "keywords": ["screen", "flicker", "randomly", "camera", "intermittent"],
    },

    "connectivity": {
        "title": "Multi-Radio Connectivity Failure",
        "story": (
            "Priya's iPhone keeps dropping Wi-Fi, Bluetooth, and\n"
            "cellular connections. She's been toggling airplane mode\n"
            "20+ times a day trying to fix it. She lives 2 hours from\n"
            "the nearest Apple Store."
        ),
        "profile": "connectivity_issues",
        "description": "My Wi-Fi, Bluetooth, and cellular keep dropping. I toggle airplane mode constantly but it keeps happening.",
        "category": "connectivity",
        "keywords": ["wifi", "bluetooth", "cellular", "drops", "connection", "airplane"],
    },

    "camera": {
        "title": "Camera Module Hardware Failure",
        "story": (
            "Alex's iPhone 15 Pro Max camera shows a black screen when\n"
            "opened. Photos are blurry and there seem to be spots.\n"
            "The phone is 6 months old with AppleCare+."
        ),
        "profile": "camera_malfunction",
        "description": "My camera shows a black screen and photos are blurry with spots. Phone is only 6 months old.",
        "category": "camera",
        "keywords": ["camera", "black", "blurry", "photo", "spots"],
    },

    "software": {
        "title": "Software Instability (No Hardware Repair Needed)",
        "story": (
            "Tom's iPhone keeps crashing — Safari closes randomly,\n"
            "the phone restarts on its own, and everything feels slow.\n"
            "He hasn't updated iOS in over a year and his storage is\n"
            "almost full. He thinks his phone is 'broken.'"
        ),
        "profile": "software_unstable",
        "description": "My phone keeps crashing and restarting. Apps close randomly and everything is very slow.",
        "category": "software",
        "keywords": ["crash", "restart", "slow", "freeze", "app", "closes"],
    },

    "storage": {
        "title": "Storage Exhaustion Mimicking Hardware Failure",
        "story": (
            "Grandma June's iPhone is 'broken' — she can't take photos,\n"
            "apps crash, and it won't update. She's ready to buy a new\n"
            "phone. The real issue: she has 2.2 GB free on a 64GB phone."
        ),
        "profile": "storage_full",
        "description": "My phone is broken. I can't take photos, apps keep crashing, and it won't let me update.",
        "category": "storage",
        "keywords": ["photo", "crash", "update", "broken", "slow"],
    },

    "complex": {
        "title": "Multi-Subsystem Failure (Complex Triage Case)",
        "story": (
            "David's iPhone 14 has everything going wrong: battery dies\n"
            "fast, screen flickers, Wi-Fi drops, and Bluetooth won't\n"
            "connect. He's been to the store 3 times, each time they\n"
            "replaced one thing and sent him home."
        ),
        "profile": "multi_failure",
        "symptoms": [
            ("Battery dies within hours and phone gets hot",
             "battery", ["battery", "dies", "hot"]),
            ("Screen flickers and sometimes doesn't respond to touch",
             "display", ["screen", "flicker", "touch"]),
            ("Wi-Fi and Bluetooth keep disconnecting",
             "connectivity", ["wifi", "bluetooth", "disconnects"]),
        ],
    },
}


def run_demo(scenario_name: str = None):
    """
    Run a demo scenario through the full pipeline.

    Args:
        scenario_name: One of the keys in DEMO_SCENARIOS.
                      If None, runs all scenarios.
    """
    engine = TriageEngine()

    if scenario_name:
        scenarios = {scenario_name: DEMO_SCENARIOS[scenario_name]}
    else:
        scenarios = DEMO_SCENARIOS

    for name, scenario in scenarios.items():
        print("\n\n")
        print("#" * 70)
        print(f"# DEMO SCENARIO: {scenario['title']}")
        print("#" * 70)
        print(f"\n  Story: {scenario['story']}")

        if "symptoms" in scenario:
            # Multi-symptom case
            engine.run_triage_multi(
                device_profile=scenario["profile"],
                symptoms=scenario["symptoms"],
            )
        else:
            # Single-symptom case
            engine.run_triage(
                device_profile=scenario["profile"],
                customer_description=scenario["description"],
                symptom_category=scenario["category"],
                symptom_keywords=scenario["keywords"],
            )

        print("\n" + "-" * 70)
        if sys.stdin.isatty():
            input("  Press Enter for the next scenario...")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        scenario = sys.argv[1]
        if scenario == "all":
            run_demo()
        elif scenario in DEMO_SCENARIOS:
            run_demo(scenario)
        else:
            print(f"Unknown scenario: {scenario}")
            print(f"Available: {', '.join(DEMO_SCENARIOS.keys())}, all")
    else:
        print("=" * 70)
        print(" APPLECARE SELF-SERVICE DIAGNOSTICS ASSISTANT")
        print(" Prototype Demo")
        print("=" * 70)
        print("\nAvailable demo scenarios:")
        for name, s in DEMO_SCENARIOS.items():
            print(f"  {name:15s} → {s['title']}")
        print(f"\nUsage: python triage_engine.py <scenario>")
        print(f"       python triage_engine.py all")
        print(f"\nExample: python triage_engine.py display")
