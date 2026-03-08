"""
=============================================================================
MODULE 2: LOG PARSER
=============================================================================

PURPOSE:
    Takes the raw DeviceSystemReport and extracts structured "findings" —
    things that are abnormal, degraded, or failing.

    Think of this as the "lab technician" that reads the blood work
    and flags what's outside normal range.

WHAT IT DOES:
    1. Checks every subsystem against known-good thresholds
    2. Produces a list of "findings" — each one is a specific abnormality
    3. Each finding has a severity (critical / warning / info)
    4. Each finding includes the raw evidence (the actual numbers)

WHY THIS IS SEPARATE FROM ANALYSIS:
    Parsing = "what do the numbers say?"
    Analysis = "what does it mean when you combine them?"

    Keeping these separate means we can:
    - Update thresholds without touching analysis logic
    - Test parsing accuracy independently
    - Show customers exactly what was checked (transparency)

=============================================================================
"""

from dataclasses import dataclass
from typing import List
from system_report_simulator import DeviceSystemReport


# ---------------------------------------------------------------------------
# Finding: A single abnormality detected in the device report
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """
    One thing the parser found that's outside normal range.

    Example:
        Finding(
            subsystem="battery",
            code="BAT_HEALTH_LOW",
            severity="critical",
            title="Battery Health Below Service Threshold",
            detail="Battery at 74% (threshold: 80%). 847 charge cycles.",
            evidence={"health_pct": 74.0, "cycle_count": 847, "threshold": 80}
        )
    """
    subsystem: str      # Which part of the device: battery, storage, display, etc.
    code: str           # Machine-readable code for downstream logic
    severity: str       # "critical", "warning", or "info"
    title: str          # Human-readable one-liner
    detail: str         # Explanation with specific numbers
    evidence: dict      # Raw data that triggered this finding


# ---------------------------------------------------------------------------
# Thresholds: What's "normal" vs "abnormal" for each metric
# ---------------------------------------------------------------------------

# These thresholds are based on Apple's published service guidelines
# and patterns from our user research.

THRESHOLDS = {
    # Battery
    "battery_health_critical":          80.0,   # Below this = Apple recommends service
    "battery_health_warning":           85.0,   # Degraded but not critical
    "battery_cycles_high":              500,    # High cycle count
    "battery_temp_warning":             35.0,   # Celsius — running warm
    "battery_temp_critical":            40.0,   # Celsius — thermal throttling risk
    "battery_shutdowns_warning":        2,      # Unexpected shutdowns in 30 days
    "battery_shutdowns_critical":       5,

    # Storage
    "storage_pct_used_warning":         85.0,   # Percentage
    "storage_pct_used_critical":        95.0,
    "storage_available_gb_critical":    5.0,    # Less than 5GB = performance impact

    # Connectivity
    "wifi_signal_poor":                 -70,    # dBm — weak signal
    "wifi_signal_very_poor":            -80,    # dBm — barely usable
    "wifi_drops_warning":               5,      # Drops in 7 days
    "wifi_drops_critical":              10,
    "bluetooth_drops_warning":          3,
    "bluetooth_drops_critical":         8,
    "cellular_drops_warning":           3,
    "cellular_drops_critical":          7,
    "airplane_toggles_concern":         10,     # Frequent toggling = user troubleshooting

    # Display
    "touch_latency_warning":            15.0,   # ms — normal is 5-15
    "touch_latency_critical":           20.0,   # ms — noticeably laggy
    "refresh_anomalies_warning":        5,
    "refresh_anomalies_critical":       10,
    "flicker_events_warning":           3,
    "flicker_events_critical":          7,

    # Crash Logs
    "crashes_warning":                  2,      # In recent history
    "crashes_critical":                 4,
    "thermal_events_warning":           5,
    "thermal_events_critical":          10,
}


# ---------------------------------------------------------------------------
# The Log Parser
# ---------------------------------------------------------------------------

class LogParser:
    """
    Parses a DeviceSystemReport and extracts findings.

    USAGE:
        from system_report_simulator import DeviceReportSimulator
        from log_parser import LogParser

        report = DeviceReportSimulator().generate("battery_degraded")
        parser = LogParser()
        findings = parser.parse(report)

        for f in findings:
            print(f"[{f.severity.upper()}] {f.title}")
    """

    def parse(self, report: DeviceSystemReport) -> List[Finding]:
        """
        Parse all subsystems and return a list of findings.
        Returns findings sorted by severity (critical first).
        """
        findings = []

        # Check each subsystem
        findings.extend(self._check_battery(report))
        findings.extend(self._check_storage(report))
        findings.extend(self._check_connectivity(report))
        findings.extend(self._check_display(report))
        findings.extend(self._check_sensors(report))
        findings.extend(self._check_camera(report))
        findings.extend(self._check_crash_logs(report))
        findings.extend(self._check_software(report))

        # Sort: critical → warning → info
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        findings.sort(key=lambda f: severity_order.get(f.severity, 3))

        return findings

    # --- Battery Checks ---

    def _check_battery(self, report) -> List[Finding]:
        findings = []
        bat = report.battery

        # Health percentage
        if bat.health_percentage < THRESHOLDS["battery_health_critical"]:
            findings.append(Finding(
                subsystem="battery",
                code="BAT_HEALTH_CRITICAL",
                severity="critical",
                title="Battery Health Below Service Threshold",
                detail=(f"Battery at {bat.health_percentage}% capacity "
                        f"(Apple service threshold: 80%). "
                        f"{bat.cycle_count} charge cycles recorded. "
                        f"Battery replacement recommended."),
                evidence={
                    "health_pct": bat.health_percentage,
                    "cycle_count": bat.cycle_count,
                    "max_capacity_mah": bat.max_capacity_mah,
                    "design_capacity_mah": bat.design_capacity_mah,
                }
            ))
        elif bat.health_percentage < THRESHOLDS["battery_health_warning"]:
            findings.append(Finding(
                subsystem="battery",
                code="BAT_HEALTH_WARNING",
                severity="warning",
                title="Battery Health Degraded",
                detail=(f"Battery at {bat.health_percentage}% capacity. "
                        f"{bat.cycle_count} cycles. Approaching service threshold."),
                evidence={
                    "health_pct": bat.health_percentage,
                    "cycle_count": bat.cycle_count,
                }
            ))

        # Unexpected shutdowns
        if bat.unexpected_shutdowns >= THRESHOLDS["battery_shutdowns_critical"]:
            findings.append(Finding(
                subsystem="battery",
                code="BAT_SHUTDOWNS_CRITICAL",
                severity="critical",
                title="Frequent Unexpected Shutdowns",
                detail=(f"{bat.unexpected_shutdowns} unexpected shutdowns in "
                        f"the last 30 days. Indicates battery cannot deliver "
                        f"peak current. Immediate service recommended."),
                evidence={"shutdown_count": bat.unexpected_shutdowns}
            ))
        elif bat.unexpected_shutdowns >= THRESHOLDS["battery_shutdowns_warning"]:
            findings.append(Finding(
                subsystem="battery",
                code="BAT_SHUTDOWNS_WARNING",
                severity="warning",
                title="Unexpected Shutdowns Detected",
                detail=(f"{bat.unexpected_shutdowns} unexpected shutdowns in "
                        f"the last 30 days."),
                evidence={"shutdown_count": bat.unexpected_shutdowns}
            ))

        # Temperature
        peak_temps = bat.peak_temps_last_30_days
        if peak_temps:
            max_peak = max(peak_temps)
            high_temp_days = sum(1 for t in peak_temps
                                if t >= THRESHOLDS["battery_temp_critical"])
            if high_temp_days >= 3:
                findings.append(Finding(
                    subsystem="battery",
                    code="BAT_THERMAL_CRITICAL",
                    severity="critical",
                    title="Repeated High Battery Temperatures",
                    detail=(f"Battery exceeded {THRESHOLDS['battery_temp_critical']}°C "
                            f"on {high_temp_days} days in the last 30 days "
                            f"(peak: {max_peak}°C). Risk of thermal damage."),
                    evidence={
                        "max_peak_temp": max_peak,
                        "high_temp_days": high_temp_days,
                        "all_peaks": peak_temps,
                    }
                ))
            elif max_peak >= THRESHOLDS["battery_temp_warning"]:
                findings.append(Finding(
                    subsystem="battery",
                    code="BAT_THERMAL_WARNING",
                    severity="warning",
                    title="Elevated Battery Temperature",
                    detail=(f"Peak battery temperature: {max_peak}°C. "
                            f"Sustained heat degrades battery longevity."),
                    evidence={"max_peak_temp": max_peak}
                ))

        return findings

    # --- Storage Checks ---

    def _check_storage(self, report) -> List[Finding]:
        findings = []
        stor = report.storage
        pct_used = (stor.used_gb / stor.total_gb) * 100

        if stor.available_gb < THRESHOLDS["storage_available_gb_critical"]:
            findings.append(Finding(
                subsystem="storage",
                code="STOR_CRITICALLY_LOW",
                severity="critical",
                title="Storage Critically Low",
                detail=(f"Only {stor.available_gb:.1f} GB available out of "
                        f"{stor.total_gb:.0f} GB. Device performance will be "
                        f"severely impacted. Apps may crash, photos cannot be "
                        f"taken, updates cannot install."),
                evidence={
                    "available_gb": stor.available_gb,
                    "total_gb": stor.total_gb,
                    "pct_used": round(pct_used, 1),
                    "breakdown": {
                        "system": stor.system_gb,
                        "apps": stor.apps_gb,
                        "photos": stor.photos_gb,
                        "other": stor.other_gb,
                    }
                }
            ))
        elif pct_used >= THRESHOLDS["storage_pct_used_warning"]:
            findings.append(Finding(
                subsystem="storage",
                code="STOR_HIGH_USAGE",
                severity="warning",
                title="Storage Running Low",
                detail=(f"{pct_used:.0f}% storage used "
                        f"({stor.available_gb:.1f} GB remaining). "
                        f"May cause slowdowns and app crashes."),
                evidence={
                    "available_gb": stor.available_gb,
                    "pct_used": round(pct_used, 1),
                }
            ))

        # Check for bloated "Other" category
        if stor.other_gb > 15 and stor.total_gb <= 128:
            findings.append(Finding(
                subsystem="storage",
                code="STOR_OTHER_BLOAT",
                severity="info",
                title="Large 'Other' Storage Category",
                detail=(f"'Other' storage using {stor.other_gb:.1f} GB. "
                        f"This often includes caches, logs, and temporary "
                        f"files that can be cleared."),
                evidence={"other_gb": stor.other_gb}
            ))

        return findings

    # --- Connectivity Checks ---

    def _check_connectivity(self, report) -> List[Finding]:
        findings = []
        conn = report.connectivity

        # Wi-Fi
        if conn.wifi_drops_last_7_days >= THRESHOLDS["wifi_drops_critical"]:
            findings.append(Finding(
                subsystem="connectivity",
                code="WIFI_DROPS_CRITICAL",
                severity="critical",
                title="Severe Wi-Fi Instability",
                detail=(f"{conn.wifi_drops_last_7_days} Wi-Fi disconnections "
                        f"in the last 7 days. Signal strength: "
                        f"{conn.wifi_signal_strength_dbm} dBm. "
                        f"May indicate hardware fault in Wi-Fi module."),
                evidence={
                    "drops_7d": conn.wifi_drops_last_7_days,
                    "signal_dbm": conn.wifi_signal_strength_dbm,
                }
            ))
        elif conn.wifi_drops_last_7_days >= THRESHOLDS["wifi_drops_warning"]:
            findings.append(Finding(
                subsystem="connectivity",
                code="WIFI_DROPS_WARNING",
                severity="warning",
                title="Frequent Wi-Fi Disconnections",
                detail=(f"{conn.wifi_drops_last_7_days} Wi-Fi drops in 7 days. "
                        f"Signal: {conn.wifi_signal_strength_dbm} dBm."),
                evidence={
                    "drops_7d": conn.wifi_drops_last_7_days,
                    "signal_dbm": conn.wifi_signal_strength_dbm,
                }
            ))

        # Bluetooth
        if conn.bluetooth_drops_last_7_days >= THRESHOLDS["bluetooth_drops_critical"]:
            findings.append(Finding(
                subsystem="connectivity",
                code="BT_DROPS_CRITICAL",
                severity="critical",
                title="Severe Bluetooth Instability",
                detail=(f"{conn.bluetooth_drops_last_7_days} Bluetooth "
                        f"disconnections in 7 days. "
                        f"Possible Bluetooth module hardware fault."),
                evidence={"drops_7d": conn.bluetooth_drops_last_7_days}
            ))
        elif conn.bluetooth_drops_last_7_days >= THRESHOLDS["bluetooth_drops_warning"]:
            findings.append(Finding(
                subsystem="connectivity",
                code="BT_DROPS_WARNING",
                severity="warning",
                title="Bluetooth Connection Issues",
                detail=(f"{conn.bluetooth_drops_last_7_days} Bluetooth drops "
                        f"in 7 days."),
                evidence={"drops_7d": conn.bluetooth_drops_last_7_days}
            ))

        # Cellular
        if conn.cellular_drops_last_7_days >= THRESHOLDS["cellular_drops_critical"]:
            findings.append(Finding(
                subsystem="connectivity",
                code="CELL_DROPS_CRITICAL",
                severity="critical",
                title="Frequent Cellular Connection Loss",
                detail=(f"{conn.cellular_drops_last_7_days} cellular drops "
                        f"in 7 days. Signal: {conn.cellular_signal_bars}/4 bars. "
                        f"May indicate baseband hardware issue."),
                evidence={
                    "drops_7d": conn.cellular_drops_last_7_days,
                    "signal_bars": conn.cellular_signal_bars,
                }
            ))
        elif conn.cellular_drops_last_7_days >= THRESHOLDS["cellular_drops_warning"]:
            findings.append(Finding(
                subsystem="connectivity",
                code="CELL_DROPS_WARNING",
                severity="warning",
                title="Cellular Connection Instability",
                detail=(f"{conn.cellular_drops_last_7_days} cellular drops in 7 days."),
                evidence={"drops_7d": conn.cellular_drops_last_7_days}
            ))

        # User troubleshooting signal: frequent airplane mode toggling
        if conn.airplane_mode_toggles >= THRESHOLDS["airplane_toggles_concern"]:
            findings.append(Finding(
                subsystem="connectivity",
                code="CONN_USER_TROUBLESHOOTING",
                severity="info",
                title="User Actively Troubleshooting Connectivity",
                detail=(f"Airplane mode toggled {conn.airplane_mode_toggles} "
                        f"times recently — indicates user is aware of and "
                        f"frustrated by connectivity issues."),
                evidence={"toggles": conn.airplane_mode_toggles}
            ))

        return findings

    # --- Display Checks ---

    def _check_display(self, report) -> List[Finding]:
        findings = []
        disp = report.display

        # Touch latency
        if disp.touch_response_ms >= THRESHOLDS["touch_latency_critical"]:
            findings.append(Finding(
                subsystem="display",
                code="DISP_TOUCH_CRITICAL",
                severity="critical",
                title="Touch Response Severely Degraded",
                detail=(f"Touch latency: {disp.touch_response_ms}ms "
                        f"(normal: 5-15ms). Display hardware inspection "
                        f"required — likely digitizer or display controller."),
                evidence={"latency_ms": disp.touch_response_ms}
            ))
        elif disp.touch_response_ms >= THRESHOLDS["touch_latency_warning"]:
            findings.append(Finding(
                subsystem="display",
                code="DISP_TOUCH_WARNING",
                severity="warning",
                title="Elevated Touch Latency",
                detail=(f"Touch latency: {disp.touch_response_ms}ms "
                        f"(normal: 5-15ms). Monitor for degradation."),
                evidence={"latency_ms": disp.touch_response_ms}
            ))

        # Refresh rate anomalies
        if disp.refresh_rate_anomalies >= THRESHOLDS["refresh_anomalies_critical"]:
            findings.append(Finding(
                subsystem="display",
                code="DISP_REFRESH_CRITICAL",
                severity="critical",
                title="Frequent Display Refresh Anomalies",
                detail=(f"{disp.refresh_rate_anomalies} refresh rate anomalies "
                        f"in last 7 days. Indicates display controller or "
                        f"flex cable issue."),
                evidence={"anomaly_count": disp.refresh_rate_anomalies}
            ))
        elif disp.refresh_rate_anomalies >= THRESHOLDS["refresh_anomalies_warning"]:
            findings.append(Finding(
                subsystem="display",
                code="DISP_REFRESH_WARNING",
                severity="warning",
                title="Display Refresh Rate Irregularities",
                detail=(f"{disp.refresh_rate_anomalies} anomalies logged."),
                evidence={"anomaly_count": disp.refresh_rate_anomalies}
            ))

        # Flicker events
        if disp.flicker_events_logged >= THRESHOLDS["flicker_events_critical"]:
            findings.append(Finding(
                subsystem="display",
                code="DISP_FLICKER_CRITICAL",
                severity="critical",
                title="Display Flickering Detected",
                detail=(f"{disp.flicker_events_logged} flicker events logged. "
                        f"This is the intermittent issue pattern that is often "
                        f"missed by point-in-time diagnostics. Continuous "
                        f"monitoring has captured evidence."),
                evidence={"flicker_count": disp.flicker_events_logged}
            ))
        elif disp.flicker_events_logged >= THRESHOLDS["flicker_events_warning"]:
            findings.append(Finding(
                subsystem="display",
                code="DISP_FLICKER_WARNING",
                severity="warning",
                title="Intermittent Display Flicker",
                detail=(f"{disp.flicker_events_logged} flicker events. "
                        f"May be intermittent — captured via monitoring."),
                evidence={"flicker_count": disp.flicker_events_logged}
            ))

        # Dead pixels
        if disp.dead_pixels_detected > 0:
            findings.append(Finding(
                subsystem="display",
                code="DISP_DEAD_PIXELS",
                severity="warning",
                title="Dead Pixels Detected",
                detail=f"{disp.dead_pixels_detected} dead pixel(s) found.",
                evidence={"count": disp.dead_pixels_detected}
            ))

        # True Tone
        if not disp.true_tone_functional:
            findings.append(Finding(
                subsystem="display",
                code="DISP_TRUETONE_FAIL",
                severity="warning",
                title="True Tone Not Functioning",
                detail="True Tone display calibration is not responding. "
                       "May indicate ambient light sensor or display module issue.",
                evidence={"true_tone": False}
            ))

        return findings

    # --- Sensor Checks ---

    def _check_sensors(self, report) -> List[Finding]:
        findings = []
        sens = report.sensors

        sensor_checks = [
            (sens.accelerometer_functional, "Accelerometer", "SENS_ACCEL"),
            (sens.gyroscope_functional, "Gyroscope", "SENS_GYRO"),
            (sens.proximity_sensor_functional, "Proximity Sensor", "SENS_PROX"),
            (sens.ambient_light_sensor_functional, "Ambient Light Sensor", "SENS_ALS"),
        ]

        for is_functional, name, code in sensor_checks:
            if not is_functional:
                findings.append(Finding(
                    subsystem="sensors",
                    code=f"{code}_FAIL",
                    severity="warning",
                    title=f"{name} Not Responding",
                    detail=f"{name} failed self-test. Hardware inspection needed.",
                    evidence={name.lower().replace(" ", "_"): False}
                ))

        # Face ID (if present)
        if sens.face_id_functional is not None and not sens.face_id_functional:
            findings.append(Finding(
                subsystem="sensors",
                code="SENS_FACEID_FAIL",
                severity="critical",
                title="Face ID Not Functioning",
                detail="Face ID sensor array failed. TrueDepth camera "
                       "module inspection required.",
                evidence={"face_id": False}
            ))

        return findings

    # --- Camera Checks ---

    def _check_camera(self, report) -> List[Finding]:
        findings = []
        cam = report.camera

        if not cam.rear_camera_functional:
            findings.append(Finding(
                subsystem="camera",
                code="CAM_REAR_FAIL",
                severity="critical",
                title="Rear Camera Not Functional",
                detail="Rear camera module is not responding. "
                       "Camera module replacement likely required.",
                evidence={"rear_camera": False}
            ))

        if not cam.front_camera_functional:
            findings.append(Finding(
                subsystem="camera",
                code="CAM_FRONT_FAIL",
                severity="critical",
                title="Front Camera Not Functional",
                detail="Front-facing camera is not responding.",
                evidence={"front_camera": False}
            ))

        if not cam.autofocus_responsive:
            findings.append(Finding(
                subsystem="camera",
                code="CAM_AF_FAIL",
                severity="critical",
                title="Autofocus Not Responding",
                detail="Camera autofocus mechanism has failed. "
                       "Likely requires camera module replacement.",
                evidence={"autofocus": False}
            ))

        if not cam.image_stabilization_functional:
            findings.append(Finding(
                subsystem="camera",
                code="CAM_OIS_FAIL",
                severity="warning",
                title="Optical Image Stabilization Failure",
                detail="OIS is not functioning. Photos/video may appear shaky. "
                       "Camera module inspection required.",
                evidence={"ois": False}
            ))

        if cam.lens_obstruction_detected:
            findings.append(Finding(
                subsystem="camera",
                code="CAM_LENS_OBSTRUCT",
                severity="warning",
                title="Lens Obstruction Detected",
                detail="Camera sensor detects obstruction over the lens. "
                       "Could be debris, moisture, or crack. "
                       "Physical inspection needed.",
                evidence={"obstruction": True}
            ))

        return findings

    # --- Crash Log Checks ---

    def _check_crash_logs(self, report) -> List[Finding]:
        findings = []
        crashes = report.crash_logs
        thermal = report.thermal_events_last_30_days

        if len(crashes) >= THRESHOLDS["crashes_critical"]:
            # Analyze crash patterns
            hw_crashes = [c for c in crashes if c.related_hardware]
            sw_crashes = [c for c in crashes if not c.related_hardware]
            kernel_panics = [c for c in crashes
                            if c.crash_type == "kernel_panic"]

            detail_parts = [
                f"{len(crashes)} crash events in recent history.",
            ]
            if kernel_panics:
                detail_parts.append(
                    f"{len(kernel_panics)} kernel panic(s) — indicates "
                    f"low-level hardware or firmware instability."
                )
            if hw_crashes:
                hw_components = set(c.related_hardware for c in hw_crashes)
                detail_parts.append(
                    f"Hardware-related crashes implicate: "
                    f"{', '.join(hw_components)}."
                )

            findings.append(Finding(
                subsystem="system",
                code="SYS_CRASHES_CRITICAL",
                severity="critical",
                title="High Crash Frequency — System Instability",
                detail=" ".join(detail_parts),
                evidence={
                    "total_crashes": len(crashes),
                    "kernel_panics": len(kernel_panics),
                    "hardware_implicated": [c.related_hardware
                                            for c in hw_crashes],
                    "processes": [c.process_name for c in crashes],
                }
            ))

        elif len(crashes) >= THRESHOLDS["crashes_warning"]:
            findings.append(Finding(
                subsystem="system",
                code="SYS_CRASHES_WARNING",
                severity="warning",
                title="Elevated Crash Rate",
                detail=f"{len(crashes)} crash events logged recently.",
                evidence={"total_crashes": len(crashes)}
            ))

        # Thermal events
        if thermal >= THRESHOLDS["thermal_events_critical"]:
            findings.append(Finding(
                subsystem="system",
                code="SYS_THERMAL_CRITICAL",
                severity="critical",
                title="Excessive Thermal Events",
                detail=(f"{thermal} thermal throttling events in 30 days. "
                        f"Device is overheating frequently — risk of "
                        f"permanent component damage."),
                evidence={"thermal_events_30d": thermal}
            ))
        elif thermal >= THRESHOLDS["thermal_events_warning"]:
            findings.append(Finding(
                subsystem="system",
                code="SYS_THERMAL_WARNING",
                severity="warning",
                title="Elevated Thermal Activity",
                detail=f"{thermal} thermal events in 30 days.",
                evidence={"thermal_events_30d": thermal}
            ))

        return findings

    # --- Software / OS Checks ---

    def _check_software(self, report) -> List[Finding]:
        findings = []

        # Check for outdated OS
        current_major = "18"  # Current iOS major version
        device_major = report.os_version.replace("iOS ", "").split(".")[0]

        if device_major < current_major:
            findings.append(Finding(
                subsystem="software",
                code="SW_OS_OUTDATED",
                severity="warning",
                title="Operating System Outdated",
                detail=(f"Running {report.os_version}. Current version is "
                        f"iOS {current_major}.x. Updates may resolve software "
                        f"issues and improve stability."),
                evidence={
                    "current_os": report.os_version,
                    "latest_major": current_major,
                }
            ))

        # Long uptime without restart
        if report.uptime_hours > 168:  # 7 days
            findings.append(Finding(
                subsystem="software",
                code="SW_LONG_UPTIME",
                severity="info",
                title="Device Has Not Been Restarted Recently",
                detail=(f"Device uptime: {report.uptime_hours:.0f} hours "
                        f"({report.uptime_hours / 24:.0f} days). "
                        f"A restart may resolve some software issues."),
                evidence={"uptime_hours": report.uptime_hours}
            ))

        return findings


# ---------------------------------------------------------------------------
# Quick Test: Parse a degraded battery report
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from system_report_simulator import DeviceReportSimulator

    sim = DeviceReportSimulator()
    parser = LogParser()

    # Test each profile
    for profile in sim.PROFILES:
        report = sim.generate(profile)
        findings = parser.parse(report)

        print(f"\n{'=' * 60}")
        print(f"PROFILE: {profile}")
        print(f"{'=' * 60}")
        print(f"  Findings: {len(findings)}")

        for f in findings:
            icon = {"critical": "!!!", "warning": " ! ", "info": " i "}
            print(f"  [{icon.get(f.severity, '   ')}] {f.title}")
            print(f"        {f.detail[:80]}...")
