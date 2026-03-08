"""
=============================================================================
MODULE 3: LOG ANALYZER — Root Cause Triangulation Engine
=============================================================================

PURPOSE:
    This is the "brain" of the diagnostics assistant. It takes the parsed
    findings (from Module 2) and the customer's self-reported symptoms,
    then TRIANGULATES to the most likely root cause.

THE KEY INSIGHT:
    Generic triage: "Customer says battery dies fast" → recommend battery test.
    OUR approach: "Customer says battery dies fast" + device logs show
    thermal events + crash logs implicate display controller
    → Root cause is likely a display flex cable issue causing power drain,
      NOT the battery itself.

    This is what cuts MTTR. Instead of the Genius running battery tests
    first (finding nothing wrong), the passport points them directly at
    the display hardware.

HOW IT WORKS:
    1. Takes findings + customer symptoms as input
    2. Runs correlation rules to find patterns across subsystems
    3. Identifies root cause vs. downstream symptoms
    4. Produces a RootCauseAnalysis with confidence level
    5. Maps root cause to specific repair action + parts needed

=============================================================================
"""

from dataclasses import dataclass, field
from typing import List, Optional
from log_parser import Finding


# ---------------------------------------------------------------------------
# Customer Symptom: What the user told us during self-service triage
# ---------------------------------------------------------------------------

@dataclass
class CustomerSymptom:
    """
    A symptom reported by the customer during the self-service chat.

    Example:
        CustomerSymptom(
            description="My phone screen flickers when I open the camera",
            category="display",
            keywords=["flicker", "screen", "camera"]
        )
    """
    description: str        # What the customer said (natural language)
    category: str           # Mapped category: battery, display, connectivity, etc.
    keywords: List[str]     # Extracted keywords for matching


# ---------------------------------------------------------------------------
# Root Cause Analysis: The output of the triangulation
# ---------------------------------------------------------------------------

@dataclass
class RootCauseAnalysis:
    """
    The triangulated root cause and recommended repair path.

    This is what makes the Diagnostics Passport PERSONALIZED rather than
    generic. Instead of "run battery test," it says "replace display
    assembly — evidence: flicker events + thermal correlation + crash
    logs pointing to display controller."
    """
    root_cause: str                 # The identified root cause
    confidence: str                 # "high", "medium", "low"
    confidence_pct: int             # 0-100% confidence score
    evidence_chain: List[str]       # How we got here (step by step)
    affected_subsystems: List[str]  # Which subsystems are involved
    primary_repair: str             # The recommended repair action
    parts_needed: List[str]         # Specific parts to pre-order
    estimated_repair_minutes: int   # How long the repair should take
    secondary_actions: List[str]    # Additional steps after primary repair
    can_self_resolve: bool          # Can the customer fix this themselves?
    self_resolve_steps: List[str]   # If yes, what steps to take
    genius_notes: str               # Notes specifically for the Genius tech


# ---------------------------------------------------------------------------
# Correlation Rule: A pattern that links symptoms + findings to a root cause
# ---------------------------------------------------------------------------

@dataclass
class CorrelationRule:
    """
    A rule that matches a combination of findings and symptoms
    to a specific root cause.

    Each rule encodes expert diagnostic knowledge:
    "IF these findings appear together AND the customer reports this,
     THEN the root cause is probably X."
    """
    name: str
    description: str
    required_finding_codes: List[str]     # Must ALL be present
    optional_finding_codes: List[str]     # Boost confidence if present
    symptom_keywords: List[str]           # Customer symptom keywords
    root_cause: str
    primary_repair: str
    parts: List[str]
    repair_minutes: int
    base_confidence: int                  # Starting confidence %
    confidence_boost_per_optional: int    # Added for each optional match
    can_self_resolve: bool
    self_resolve_steps: List[str]
    genius_notes: str


# ---------------------------------------------------------------------------
# The Correlation Rules Knowledge Base
# ---------------------------------------------------------------------------
# These rules encode the diagnostic expertise that currently lives only
# in experienced Genius technicians' heads. By codifying it, we make
# every diagnosis as good as the best Genius.

CORRELATION_RULES = [

    # --- BATTERY ROOT CAUSES ---

    CorrelationRule(
        name="battery_end_of_life",
        description="Battery has reached end of service life",
        required_finding_codes=["BAT_HEALTH_CRITICAL"],
        optional_finding_codes=[
            "BAT_SHUTDOWNS_CRITICAL", "BAT_SHUTDOWNS_WARNING",
            "BAT_THERMAL_CRITICAL", "BAT_THERMAL_WARNING",
            "SYS_THERMAL_CRITICAL",
        ],
        symptom_keywords=["battery", "dies", "drain", "shutdown", "charge",
                          "won't hold", "percentage", "drops"],
        root_cause="Battery has degraded below service threshold and cannot "
                   "deliver reliable power. High cycle count and thermal "
                   "history confirm natural end-of-life degradation.",
        primary_repair="Battery replacement",
        parts=["Battery unit (model-specific)"],
        repair_minutes=30,
        base_confidence=85,
        confidence_boost_per_optional=3,
        can_self_resolve=False,
        self_resolve_steps=[],
        genius_notes="Battery is below 80% — straightforward replacement. "
                     "Check for thermal damage to adhesive strips. If "
                     "unexpected shutdowns > 5, run post-replacement power "
                     "calibration cycle."
    ),

    CorrelationRule(
        name="battery_thermal_cascade",
        description="Thermal issues causing battery and system instability",
        required_finding_codes=["BAT_THERMAL_CRITICAL", "SYS_THERMAL_CRITICAL"],
        optional_finding_codes=[
            "BAT_HEALTH_CRITICAL", "BAT_HEALTH_WARNING",
            "BAT_SHUTDOWNS_CRITICAL", "SYS_CRASHES_CRITICAL",
        ],
        symptom_keywords=["hot", "overheating", "warm", "thermal",
                          "slow", "laggy", "shutdown"],
        root_cause="Sustained thermal stress is causing cascading failures. "
                   "Battery degradation may be a SYMPTOM of the thermal issue, "
                   "not the root cause. Check for: blocked thermal pathways, "
                   "failing thermal paste, or abnormal CPU load patterns.",
        primary_repair="Thermal system inspection + battery replacement",
        parts=["Battery unit", "Thermal paste/pads (if applicable)"],
        repair_minutes=45,
        base_confidence=75,
        confidence_boost_per_optional=5,
        can_self_resolve=False,
        self_resolve_steps=[],
        genius_notes="IMPORTANT: Do NOT just replace the battery. The thermal "
                     "events suggest a root cause upstream. Inspect thermal "
                     "pathways first. Check for swollen battery pushing against "
                     "thermal interface. If crash logs show thermalmonitord, "
                     "this is a board-level thermal management issue."
    ),

    # --- DISPLAY ROOT CAUSES ---

    CorrelationRule(
        name="display_intermittent_flex",
        description="Intermittent display issues caused by flex cable",
        required_finding_codes=["DISP_FLICKER_CRITICAL"],
        optional_finding_codes=[
            "DISP_REFRESH_CRITICAL", "DISP_REFRESH_WARNING",
            "DISP_TOUCH_CRITICAL", "DISP_TOUCH_WARNING",
            "DISP_TRUETONE_FAIL",
        ],
        symptom_keywords=["flicker", "screen", "flash", "blink",
                          "intermittent", "sometimes", "randomly"],
        root_cause="Display flex cable connection is degrading, causing "
                   "intermittent signal loss between the display panel and "
                   "the logic board. This is the #1 cause of repeat visits "
                   "because point-in-time tests often pass when the "
                   "connection happens to be good.",
        primary_repair="Display assembly replacement",
        parts=["Display assembly (model-specific)", "Display adhesive kit"],
        repair_minutes=45,
        base_confidence=80,
        confidence_boost_per_optional=4,
        can_self_resolve=False,
        self_resolve_steps=[],
        genius_notes="Continuous monitoring captured flicker events that "
                     "in-store AST may miss. DO NOT run a point-in-time "
                     "display test and mark as 'pass' — see the monitoring "
                     "log with timestamps of captured events. Replace full "
                     "display assembly; flex cable is not separately serviceable."
    ),

    CorrelationRule(
        name="display_touch_controller",
        description="Touch controller hardware failure",
        required_finding_codes=["DISP_TOUCH_CRITICAL"],
        optional_finding_codes=[
            "DISP_REFRESH_CRITICAL", "DISP_FLICKER_CRITICAL",
            "DISP_DEAD_PIXELS",
        ],
        symptom_keywords=["touch", "unresponsive", "ghost", "phantom",
                          "typing", "delay", "lag", "tap"],
        root_cause="Touch digitizer or touch controller IC is failing. "
                   "Elevated touch latency confirms hardware-level issue "
                   "rather than software lag.",
        primary_repair="Display assembly replacement",
        parts=["Display assembly (model-specific)", "Display adhesive kit"],
        repair_minutes=45,
        base_confidence=80,
        confidence_boost_per_optional=5,
        can_self_resolve=False,
        self_resolve_steps=[],
        genius_notes="Touch latency measured at device level confirms "
                     "digitizer issue. Not a software problem. Replace "
                     "display assembly. After replacement, run touch "
                     "calibration and verify True Tone transfer."
    ),

    # --- CONNECTIVITY ROOT CAUSES ---

    CorrelationRule(
        name="connectivity_multi_radio_failure",
        description="Multiple wireless radios failing simultaneously",
        required_finding_codes=["WIFI_DROPS_CRITICAL"],
        optional_finding_codes=[
            "BT_DROPS_CRITICAL", "BT_DROPS_WARNING",
            "CELL_DROPS_CRITICAL", "CELL_DROPS_WARNING",
            "CONN_USER_TROUBLESHOOTING",
        ],
        symptom_keywords=["wifi", "bluetooth", "connection", "drops",
                          "disconnects", "signal", "internet", "cellular"],
        root_cause="Multiple wireless radios are failing simultaneously, "
                   "which points to a shared component: the antenna flex "
                   "cable or the logic board's wireless chipset. Individual "
                   "radio failure would suggest module-specific issues, but "
                   "correlated failure across Wi-Fi + Bluetooth + Cellular "
                   "indicates a common upstream cause.",
        primary_repair="Antenna flex cable inspection and replacement",
        parts=["Antenna flex cable assembly", "RF shield gaskets"],
        repair_minutes=60,
        base_confidence=70,
        confidence_boost_per_optional=5,
        can_self_resolve=False,
        self_resolve_steps=[],
        genius_notes="Multiple radios dropping together = shared component. "
                     "Start with antenna flex cable inspection (most common). "
                     "If flex cable looks good, escalate to logic board "
                     "wireless chipset diagnosis. Customer has been toggling "
                     "airplane mode frequently — confirms persistent issue. "
                     "Crash logs implicating wifi/bluetooth daemons support "
                     "hardware rather than software cause."
    ),

    CorrelationRule(
        name="connectivity_wifi_only",
        description="Wi-Fi specific module issue",
        required_finding_codes=["WIFI_DROPS_WARNING"],
        optional_finding_codes=["CONN_USER_TROUBLESHOOTING"],
        symptom_keywords=["wifi", "internet", "connection", "drops",
                          "slow", "disconnects"],
        root_cause="Wi-Fi module experiencing intermittent failures. "
                   "With Bluetooth and Cellular functioning normally, "
                   "this is likely a Wi-Fi specific issue — could be "
                   "software (network settings) or hardware (Wi-Fi antenna).",
        primary_repair="Network settings reset → if unresolved, Wi-Fi antenna inspection",
        parts=[],  # Try software fix first
        repair_minutes=15,
        base_confidence=65,
        confidence_boost_per_optional=5,
        can_self_resolve=True,
        self_resolve_steps=[
            "Go to Settings → General → Transfer or Reset iPhone → Reset → Reset Network Settings",
            "Reconnect to your Wi-Fi network",
            "If issue persists after 48 hours, the diagnostic passport will auto-update and recommend in-store visit",
        ],
        genius_notes="Try network settings reset first (customer may have "
                     "already been guided through this in self-service). "
                     "If Wi-Fi drops persist post-reset, inspect Wi-Fi "
                     "antenna connection points. Check for physical damage "
                     "near antenna band locations."
    ),

    # --- CAMERA ROOT CAUSES ---

    CorrelationRule(
        name="camera_module_failure",
        description="Rear camera module hardware failure",
        required_finding_codes=["CAM_REAR_FAIL"],
        optional_finding_codes=[
            "CAM_AF_FAIL", "CAM_OIS_FAIL", "CAM_LENS_OBSTRUCT",
        ],
        symptom_keywords=["camera", "photo", "blurry", "black", "focus",
                          "shaky", "won't open", "crash"],
        root_cause="Rear camera module hardware failure. Multiple camera "
                   "subsystems (autofocus, OIS, image sensor) are affected, "
                   "indicating the camera module itself needs replacement "
                   "rather than a software issue.",
        primary_repair="Rear camera module replacement",
        parts=["Rear camera module (model-specific)"],
        repair_minutes=40,
        base_confidence=90,
        confidence_boost_per_optional=2,
        can_self_resolve=False,
        self_resolve_steps=[],
        genius_notes="Camera module, AF, and OIS all failing together = "
                     "full module replacement. If lens obstruction is also "
                     "flagged, inspect for debris that may have entered "
                     "during a prior repair (common post-repair complaint). "
                     "Verify front camera unaffected to rule out logic board."
    ),

    # --- SOFTWARE ROOT CAUSES ---

    CorrelationRule(
        name="software_instability",
        description="Software-level instability resolvable without hardware repair",
        required_finding_codes=["SYS_CRASHES_CRITICAL"],
        optional_finding_codes=[
            "SW_OS_OUTDATED", "STOR_HIGH_USAGE", "STOR_CRITICALLY_LOW",
            "SYS_THERMAL_WARNING", "SW_LONG_UPTIME",
        ],
        symptom_keywords=["crash", "freeze", "slow", "restart", "lag",
                          "app", "unresponsive", "stuck"],
        root_cause="System instability driven by software factors: "
                   "outdated OS, storage pressure, and/or accumulated "
                   "cache corruption. No hardware faults detected in "
                   "crash logs — all crashes are in software processes "
                   "without hardware correlation.",
        primary_repair="Software remediation (no hardware repair needed)",
        parts=[],
        repair_minutes=15,
        base_confidence=70,
        confidence_boost_per_optional=5,
        can_self_resolve=True,
        self_resolve_steps=[
            "Update to the latest iOS version (Settings → General → Software Update)",
            "Free up storage: delete unused apps, offload photos to iCloud",
            "Restart your device (hold power + volume down, slide to power off)",
            "If crashes persist after 48 hours: Settings → General → Transfer or Reset → Erase All Content (backup first!)",
        ],
        genius_notes="IMPORTANT: Crash logs show NO hardware correlation. "
                     "This is a software case — do NOT recommend hardware "
                     "repair. Guide through OS update + storage cleanup. "
                     "If customer has already tried self-service steps and "
                     "crashes persist, a clean iOS install via DFU mode "
                     "is the next step before considering hardware."
    ),

    # --- STORAGE ROOT CAUSE ---

    CorrelationRule(
        name="storage_performance_impact",
        description="Storage exhaustion causing system-wide symptoms",
        required_finding_codes=["STOR_CRITICALLY_LOW"],
        optional_finding_codes=[
            "STOR_OTHER_BLOAT", "SYS_CRASHES_WARNING",
            "DISP_REFRESH_WARNING", "SW_LONG_UPTIME",
        ],
        symptom_keywords=["slow", "storage", "full", "space", "photo",
                          "update", "can't download", "crash"],
        root_cause="Device storage is critically low, causing cascading "
                   "performance issues. The system needs minimum free space "
                   "for virtual memory, caching, and OS operations. "
                   "Symptoms like app crashes, slow UI, and failed updates "
                   "are all DOWNSTREAM of the storage issue.",
        primary_repair="Storage optimization (no hardware repair needed)",
        parts=[],
        repair_minutes=10,
        base_confidence=85,
        confidence_boost_per_optional=3,
        can_self_resolve=True,
        self_resolve_steps=[
            "Review storage: Settings → General → iPhone Storage",
            "Enable 'Offload Unused Apps' to auto-remove rarely used apps",
            "Move photos to iCloud: Settings → Photos → iCloud Photos",
            "Delete old messages: Settings → Messages → Keep Messages → 1 Year",
            "Clear Safari data: Settings → Safari → Clear History and Website Data",
        ],
        genius_notes="This is a STORAGE case, not hardware. Customer may "
                     "have come in thinking their phone is 'broken' — the "
                     "root cause is full storage. Walk through cleanup. "
                     "If 'Other' storage is bloated (>15GB), a backup + "
                     "restore may be needed to reclaim cached data."
    ),

    # --- MULTI-FAILURE COMPLEX CASE ---

    CorrelationRule(
        name="multi_subsystem_board_level",
        description="Multiple subsystem failures suggesting logic board issue",
        required_finding_codes=["BAT_HEALTH_CRITICAL", "DISP_FLICKER_CRITICAL"],
        optional_finding_codes=[
            "WIFI_DROPS_CRITICAL", "BT_DROPS_CRITICAL",
            "SYS_CRASHES_CRITICAL", "SYS_THERMAL_CRITICAL",
            "DISP_TOUCH_CRITICAL", "DISP_REFRESH_CRITICAL",
            "SENS_PROX_FAIL", "BAT_SHUTDOWNS_CRITICAL",
        ],
        symptom_keywords=["multiple", "everything", "broken", "many",
                          "issues", "problems"],
        root_cause="Multiple unrelated subsystems are failing simultaneously "
                   "(battery + display + connectivity + sensors). This pattern "
                   "is consistent with a logic board level issue where "
                   "shared power management or data bus circuits are "
                   "degrading, causing downstream failures across subsystems.",
        primary_repair="Logic board diagnostic and potential replacement",
        parts=["Logic board (model-specific)", "Battery unit",
               "Display assembly"],
        repair_minutes=90,
        base_confidence=65,
        confidence_boost_per_optional=4,
        can_self_resolve=False,
        self_resolve_steps=[],
        genius_notes="COMPLEX CASE — multiple subsystem failures suggest "
                     "board-level issue. Do NOT replace individual components "
                     "one at a time (this is what causes repeat visits). "
                     "Run full AST board-level diagnostics first. Check for "
                     "corrosion on logic board connectors. If board-level "
                     "fault confirmed, discuss whole-unit replacement vs. "
                     "board repair with customer based on AppleCare status "
                     "and device age."
    ),
]


# ---------------------------------------------------------------------------
# The Log Analyzer Engine
# ---------------------------------------------------------------------------

class LogAnalyzer:
    """
    Triangulates root cause from device findings + customer symptoms.

    This is the personalization layer. It doesn't just ask "what hurts?"
    — it cross-references what the customer says with what the device's
    own logs reveal, finding patterns that neither source shows alone.

    USAGE:
        analyzer = LogAnalyzer()

        symptoms = [
            CustomerSymptom(
                description="My screen flickers randomly",
                category="display",
                keywords=["screen", "flicker", "randomly"]
            )
        ]

        analysis = analyzer.analyze(findings, symptoms)
        print(analysis.root_cause)
        print(analysis.primary_repair)
        print(analysis.parts_needed)
    """

    def analyze(self, findings: List[Finding],
                symptoms: List[CustomerSymptom]) -> RootCauseAnalysis:
        """
        Run the triangulation engine.

        Args:
            findings: Parsed findings from LogParser
            symptoms: Customer-reported symptoms from self-service chat

        Returns:
            RootCauseAnalysis with root cause, repair path, and parts
        """
        # Step 1: Score each correlation rule against the evidence
        scored_rules = self._score_rules(findings, symptoms)

        # Step 2: Pick the highest-confidence match
        if not scored_rules:
            return self._no_match_fallback(findings, symptoms)

        best_rule, confidence = scored_rules[0]

        # Step 3: Build the evidence chain (how we got here)
        evidence_chain = self._build_evidence_chain(
            best_rule, findings, symptoms
        )

        # Step 4: Determine affected subsystems
        affected = list(set(f.subsystem for f in findings
                            if f.severity in ("critical", "warning")))

        # Step 5: Assemble the analysis
        return RootCauseAnalysis(
            root_cause=best_rule.root_cause,
            confidence="high" if confidence >= 80 else
                       "medium" if confidence >= 60 else "low",
            confidence_pct=min(confidence, 99),
            evidence_chain=evidence_chain,
            affected_subsystems=affected,
            primary_repair=best_rule.primary_repair,
            parts_needed=best_rule.parts,
            estimated_repair_minutes=best_rule.repair_minutes,
            secondary_actions=self._get_secondary_actions(findings, best_rule),
            can_self_resolve=best_rule.can_self_resolve,
            self_resolve_steps=best_rule.self_resolve_steps,
            genius_notes=best_rule.genius_notes,
        )

    def _score_rules(self, findings, symptoms):
        """
        Score each correlation rule against current findings and symptoms.
        Returns list of (rule, confidence_score) sorted by score descending.
        """
        finding_codes = set(f.code for f in findings)
        symptom_keywords = set()
        for s in symptoms:
            symptom_keywords.update(k.lower() for k in s.keywords)

        scored = []

        for rule in CORRELATION_RULES:
            # Check required findings — ALL must be present
            required_met = all(code in finding_codes
                               for code in rule.required_finding_codes)
            if not required_met:
                continue

            # Start with base confidence
            confidence = rule.base_confidence

            # Boost for each optional finding present
            for opt_code in rule.optional_finding_codes:
                if opt_code in finding_codes:
                    confidence += rule.confidence_boost_per_optional

            # Boost for symptom keyword matches
            keyword_matches = symptom_keywords & set(
                k.lower() for k in rule.symptom_keywords
            )
            if keyword_matches:
                # More keyword matches = more confidence
                keyword_boost = min(len(keyword_matches) * 3, 15)
                confidence += keyword_boost

            scored.append((rule, confidence))

        # Sort by confidence descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _build_evidence_chain(self, rule, findings, symptoms):
        """
        Build a human-readable evidence chain explaining how we
        arrived at this root cause. This is key for transparency.
        """
        chain = []

        # Step 1: What the customer reported
        if symptoms:
            descriptions = [s.description for s in symptoms]
            chain.append(
                f"Customer reported: {'; '.join(descriptions)}"
            )

        # Step 2: What the device logs confirmed
        finding_codes = set(f.code for f in findings)
        matched_required = [
            f for f in findings
            if f.code in rule.required_finding_codes
        ]
        for f in matched_required:
            chain.append(
                f"Device confirmed [{f.severity.upper()}]: {f.title} — {f.detail}"
            )

        # Step 3: Corroborating evidence
        matched_optional = [
            f for f in findings
            if f.code in rule.optional_finding_codes
        ]
        if matched_optional:
            chain.append("Corroborating evidence from device logs:")
            for f in matched_optional:
                chain.append(f"  + {f.title}: {f.detail}")

        # Step 4: The triangulation logic
        chain.append(
            f"Root cause triangulation: {rule.description}"
        )

        return chain

    def _get_secondary_actions(self, findings, primary_rule):
        """
        Identify any additional actions beyond the primary repair.
        """
        actions = []

        finding_codes = set(f.code for f in findings)

        # If OS is outdated, always recommend update
        if "SW_OS_OUTDATED" in finding_codes:
            actions.append("Update iOS to latest version after repair")

        # If storage is high, recommend cleanup
        if "STOR_HIGH_USAGE" in finding_codes or "STOR_CRITICALLY_LOW" in finding_codes:
            actions.append("Guide customer through storage optimization")

        # If there were thermal events, recommend charging habit review
        if "BAT_THERMAL_CRITICAL" in finding_codes or "BAT_THERMAL_WARNING" in finding_codes:
            actions.append("Advise on charging best practices (avoid prolonged overnight charging)")

        return actions

    def _no_match_fallback(self, findings, symptoms):
        """
        When no correlation rule matches confidently,
        provide a general analysis based on findings alone.
        """
        critical = [f for f in findings if f.severity == "critical"]
        warnings = [f for f in findings if f.severity == "warning"]
        affected = list(set(f.subsystem for f in findings
                            if f.severity in ("critical", "warning")))

        if critical:
            detail = "; ".join(f.title for f in critical)
            return RootCauseAnalysis(
                root_cause=f"Multiple issues detected but no definitive root "
                           f"cause pattern identified. Critical findings: {detail}. "
                           f"In-store diagnostic with full AST required.",
                confidence="low",
                confidence_pct=40,
                evidence_chain=[
                    f"Customer symptoms noted but could not be triangulated "
                    f"to a specific root cause from device data alone.",
                    f"Critical findings: {detail}",
                    f"Recommend full in-store AST diagnostic."
                ],
                affected_subsystems=affected,
                primary_repair="Full in-store AST diagnostic required",
                parts_needed=[],
                estimated_repair_minutes=20,
                secondary_actions=[],
                can_self_resolve=False,
                self_resolve_steps=[],
                genius_notes=f"Pre-triage could not definitively identify root "
                             f"cause. Critical findings were: {detail}. "
                             f"Run full AST suite. Self-service diagnostic "
                             f"data is attached for reference."
            )
        else:
            return RootCauseAnalysis(
                root_cause="No significant hardware issues detected. "
                           "Issue may be environmental or usage-related.",
                confidence="medium",
                confidence_pct=55,
                evidence_chain=[
                    "Device diagnostics returned no critical findings.",
                    "Customer-reported symptoms may be intermittent — "
                    "recommend monitoring mode for 48 hours."
                ],
                affected_subsystems=affected,
                primary_repair="Enable monitoring mode for 48-hour data collection",
                parts_needed=[],
                estimated_repair_minutes=0,
                secondary_actions=["Set up continuous monitoring for intermittent issues"],
                can_self_resolve=True,
                self_resolve_steps=[
                    "Your device diagnostics look mostly healthy.",
                    "We've enabled monitoring mode to watch for the issue you described.",
                    "If the problem recurs, we'll capture it automatically and update your diagnostic report.",
                    "You'll receive a notification if we detect the issue."
                ],
                genius_notes="Customer reports symptoms but device diagnostics "
                             "are clean. This is a classic intermittent-issue "
                             "case. Monitoring mode has been enabled to capture "
                             "evidence over time rather than dismissing the customer."
            )


# ---------------------------------------------------------------------------
# Quick Test: Full pipeline from report → findings → analysis
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from system_report_simulator import DeviceReportSimulator
    from log_parser import LogParser

    sim = DeviceReportSimulator()
    parser = LogParser()
    analyzer = LogAnalyzer()

    # Test scenario: Display intermittent + customer says "screen flickers"
    print("=" * 70)
    print("SCENARIO: Display Intermittent Issue")
    print("  Customer says: 'My screen flickers randomly, especially")
    print("  when I open the camera app'")
    print("=" * 70)

    report = sim.generate("display_intermittent")
    findings = parser.parse(report)
    symptoms = [
        CustomerSymptom(
            description="My screen flickers randomly, especially when I open the camera app",
            category="display",
            keywords=["screen", "flicker", "randomly", "camera"]
        )
    ]

    analysis = analyzer.analyze(findings, symptoms)

    print(f"\n  ROOT CAUSE: {analysis.root_cause[:100]}...")
    print(f"  CONFIDENCE: {analysis.confidence} ({analysis.confidence_pct}%)")
    print(f"  REPAIR:     {analysis.primary_repair}")
    print(f"  PARTS:      {', '.join(analysis.parts_needed) or 'None'}")
    print(f"  EST. TIME:  {analysis.estimated_repair_minutes} min")
    print(f"  SELF-FIX:   {'Yes' if analysis.can_self_resolve else 'No'}")

    print(f"\n  EVIDENCE CHAIN:")
    for step in analysis.evidence_chain:
        print(f"    → {step[:90]}")

    print(f"\n  GENIUS NOTES:")
    print(f"    {analysis.genius_notes[:200]}")
