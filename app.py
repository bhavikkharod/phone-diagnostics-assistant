"""
=============================================================================
APPLECARE SELF-SERVICE DIAGNOSTICS ASSISTANT
Interactive Prototype UI
=============================================================================

Run with:  streamlit run app.py

This prototype demonstrates the end-to-end flow:
  1. Customer self-service triage (symptom input + device diagnostics)
  2. Diagnostics Passport generation (customer view)
  3. Genius Bar handoff (technician view with repair plan)
  4. MTTR impact dashboard

=============================================================================
"""

import streamlit as st
import time
import sys
import os

# Add prototype directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from system_report_simulator import DeviceReportSimulator
from log_parser import LogParser
from log_analyzer import LogAnalyzer, CustomerSymptom
from diagnostics_passport import PassportGenerator


# ---------------------------------------------------------------------------
# Page Config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AppleCare Diagnostics Assistant",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Custom CSS — Apple-inspired design
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    /* Global */
    .stApp {
        background-color: #fafafa;
    }

    /* Header styling */
    .apple-header {
        text-align: center;
        padding: 1.5rem 0 1rem 0;
        border-bottom: 1px solid #e5e5e5;
        margin-bottom: 2rem;
    }
    .apple-header h1 {
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
        font-weight: 600;
        font-size: 1.8rem;
        color: #1d1d1f;
        margin: 0;
    }
    .apple-header p {
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
        color: #6e6e73;
        font-size: 1rem;
        margin-top: 0.3rem;
    }

    /* Card styling */
    .diagnostic-card {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        margin-bottom: 1rem;
        border: 1px solid #e8e8ed;
    }
    .diagnostic-card h3 {
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
        font-weight: 600;
        color: #1d1d1f;
        margin-top: 0;
        font-size: 1.1rem;
    }

    /* Status badges */
    .badge-pass {
        display: inline-block;
        background: #e8f5e9;
        color: #2e7d32;
        padding: 3px 12px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        margin: 2px 4px;
    }
    .badge-fail {
        display: inline-block;
        background: #ffebee;
        color: #c62828;
        padding: 3px 12px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        margin: 2px 4px;
    }
    .badge-warn {
        display: inline-block;
        background: #fff3e0;
        color: #e65100;
        padding: 3px 12px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        margin: 2px 4px;
    }
    .badge-info {
        display: inline-block;
        background: #e3f2fd;
        color: #1565c0;
        padding: 3px 12px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        margin: 2px 4px;
    }

    /* Finding items */
    .finding-critical {
        background: #fff5f5;
        border-left: 4px solid #c62828;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    .finding-warning {
        background: #fffbf0;
        border-left: 4px solid #e65100;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    .finding-info {
        background: #f0f7ff;
        border-left: 4px solid #1565c0;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    .finding-title {
        font-weight: 600;
        font-size: 0.92rem;
        color: #1d1d1f;
    }
    .finding-detail {
        font-size: 0.84rem;
        color: #6e6e73;
        margin-top: 0.25rem;
    }

    /* Confidence meter */
    .confidence-bar {
        height: 8px;
        border-radius: 4px;
        background: #e8e8ed;
        margin-top: 0.5rem;
    }
    .confidence-fill-high {
        height: 100%;
        border-radius: 4px;
        background: linear-gradient(90deg, #34c759, #30d158);
    }
    .confidence-fill-medium {
        height: 100%;
        border-radius: 4px;
        background: linear-gradient(90deg, #ff9f0a, #ffcc00);
    }
    .confidence-fill-low {
        height: 100%;
        border-radius: 4px;
        background: linear-gradient(90deg, #ff3b30, #ff6961);
    }

    /* Passport ID */
    .passport-id {
        font-family: 'SF Mono', 'Menlo', monospace;
        font-size: 0.78rem;
        color: #8e8e93;
        background: #f2f2f7;
        padding: 4px 10px;
        border-radius: 6px;
        display: inline-block;
    }

    /* Genius notes box */
    .genius-notes {
        background: #1d1d1f;
        color: #f5f5f7;
        padding: 1.2rem;
        border-radius: 12px;
        font-family: 'SF Mono', 'Menlo', monospace;
        font-size: 0.84rem;
        line-height: 1.5;
        margin-top: 0.5rem;
    }

    /* Evidence chain */
    .evidence-step {
        padding: 0.5rem 0 0.5rem 1.5rem;
        border-left: 2px solid #007aff;
        margin-left: 0.5rem;
        font-size: 0.88rem;
        color: #1d1d1f;
    }
    .evidence-step:last-child {
        border-left: 2px solid #34c759;
    }

    /* Metric cards */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 1px 8px rgba(0,0,0,0.05);
        border: 1px solid #e8e8ed;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #007aff;
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
    }
    .metric-value-green {
        font-size: 2rem;
        font-weight: 700;
        color: #34c759;
    }
    .metric-value-red {
        font-size: 2rem;
        font-weight: 700;
        color: #ff3b30;
    }
    .metric-label {
        font-size: 0.82rem;
        color: #8e8e93;
        margin-top: 0.25rem;
    }

    /* Pipeline step */
    .pipeline-step {
        display: flex;
        align-items: center;
        padding: 0.6rem 0;
    }
    .step-number {
        background: #007aff;
        color: white;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 0.82rem;
        margin-right: 0.75rem;
        flex-shrink: 0;
    }
    .step-done {
        background: #34c759;
    }

    /* Repair box */
    .repair-box {
        background: linear-gradient(135deg, #007aff, #5856d6);
        color: white;
        padding: 1.5rem;
        border-radius: 16px;
        margin-top: 1rem;
    }
    .repair-box h4 {
        color: white;
        margin: 0 0 0.5rem 0;
        font-size: 1.05rem;
    }
    .repair-box p {
        color: rgba(255,255,255,0.9);
        margin: 0.25rem 0;
        font-size: 0.9rem;
    }

    /* Self-resolve box */
    .self-resolve-box {
        background: linear-gradient(135deg, #34c759, #30d158);
        color: white;
        padding: 1.5rem;
        border-radius: 16px;
        margin-top: 1rem;
    }
    .self-resolve-box h4 {
        color: white;
        margin: 0 0 0.5rem 0;
    }
    .self-resolve-box p {
        color: rgba(255,255,255,0.9);
        margin: 0.25rem 0;
        font-size: 0.9rem;
    }

    /* CTA Button */
    .cta-button {
        display: block;
        background: #007aff;
        color: white !important;
        text-align: center;
        padding: 14px 24px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 1rem;
        margin-top: 1rem;
        text-decoration: none;
        transition: background 0.2s;
    }
    .cta-button:hover {
        background: #0056cc;
    }

    /* Subsystem grid */
    .subsystem-row {
        display: flex;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid #f2f2f7;
    }
    .subsystem-row:last-child {
        border-bottom: none;
    }
    .subsystem-name {
        flex: 1;
        font-size: 0.92rem;
        color: #1d1d1f;
    }

    /* Tab-like view switcher */
    div[data-testid="stHorizontalBlock"] > div {
        padding: 0 0.25rem;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: #f5f5f7;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Initialize Engine Components
# ---------------------------------------------------------------------------

@st.cache_resource
def get_engine():
    return {
        "simulator": DeviceReportSimulator(),
        "parser": LogParser(),
        "analyzer": LogAnalyzer(),
        "passport_gen": PassportGenerator(),
    }

engine = get_engine()


# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------

if "stage" not in st.session_state:
    st.session_state.stage = "intake"        # intake → running → results
if "passport" not in st.session_state:
    st.session_state.passport = None
if "report" not in st.session_state:
    st.session_state.report = None
if "findings" not in st.session_state:
    st.session_state.findings = None
if "analysis" not in st.session_state:
    st.session_state.analysis = None


# ---------------------------------------------------------------------------
# Sidebar: Scenario Selector & Navigation
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### AppleCare Diagnostics")
    st.markdown("**Self-Service Pre-Triage Prototype**")
    st.markdown("---")

    st.markdown("#### Quick Demo Scenarios")
    st.caption("Select a pre-built scenario to see the system in action, or use 'Custom' to enter your own symptoms.")

    scenario = st.selectbox(
        "Choose a scenario:",
        [
            "-- Select --",
            "Display: Intermittent Flicker (repeat visit case)",
            "Battery: Degradation + Thermal Cascade",
            "Connectivity: Multi-Radio Failure",
            "Camera: Module Hardware Failure",
            "Software: Instability (self-resolvable)",
            "Storage: Full Storage Mimicking Hardware Failure",
            "Complex: Multi-Subsystem Board-Level",
            "Custom: Enter Your Own Symptoms",
        ],
        key="scenario_select"
    )

    st.markdown("---")
    st.markdown("#### View Mode")
    view_mode = st.radio(
        "Perspective:",
        ["Customer View", "Genius Bar View", "Side-by-Side"],
        key="view_mode",
        help="Customer: What the user sees. Genius: What the tech sees. Side-by-Side: Both."
    )

    st.markdown("---")
    st.markdown("#### About This Prototype")
    st.caption(
        "This prototype demonstrates Solutions A1 (AI Diagnostic Chat) "
        "and C1 (Diagnostic Passport) from the Opportunity Solution Tree. "
        "It shows how pre-triage diagnostics + device system reports "
        "triangulate to root cause, cutting Genius Bar MTTR."
    )


# ---------------------------------------------------------------------------
# Scenario Configurations
# ---------------------------------------------------------------------------

SCENARIOS = {
    "Display: Intermittent Flicker (repeat visit case)": {
        "profile": "display_intermittent",
        "model": "iPhone 15 Pro Max",
        "symptom_text": "My screen flickers randomly, especially when I open the camera. I've been to the Genius Bar twice and they keep telling me diagnostics pass.",
        "category": "display",
        "keywords": ["screen", "flicker", "randomly", "camera", "intermittent"],
        "customer_name": "Mike",
        "story": "Mike's iPhone 15 Pro screen flickers randomly, especially when using the camera. He's been to the store **twice** and both times diagnostics 'passed.' He's about to switch to Samsung.",
    },
    "Battery: Degradation + Thermal Cascade": {
        "profile": "battery_degraded",
        "model": "iPhone 14 Pro",
        "symptom_text": "My phone dies at 40% battery and gets really hot when charging. I already went to the Genius Bar once and they told me to monitor it.",
        "category": "battery",
        "keywords": ["dies", "battery", "hot", "charging", "40%", "shutdown"],
        "customer_name": "Sarah",
        "story": "Sarah's iPhone 14 Pro has been dying at 40% battery and gets very hot during charging. She's visited the Genius Bar once before and was told to 'monitor it.'",
    },
    "Connectivity: Multi-Radio Failure": {
        "profile": "connectivity_issues",
        "model": "iPhone 15",
        "symptom_text": "My Wi-Fi, Bluetooth, and cellular keep dropping constantly. I toggle airplane mode 20+ times a day trying to fix it.",
        "category": "connectivity",
        "keywords": ["wifi", "bluetooth", "cellular", "drops", "connection", "airplane"],
        "customer_name": "Priya",
        "story": "Priya's iPhone keeps dropping Wi-Fi, Bluetooth, and cellular connections. She's been toggling airplane mode 20+ times a day. She lives 2 hours from the nearest Apple Store.",
    },
    "Camera: Module Hardware Failure": {
        "profile": "camera_malfunction",
        "model": "iPhone 15 Pro Max",
        "symptom_text": "My camera shows a black screen and photos are blurry with spots. Phone is only 6 months old.",
        "category": "camera",
        "keywords": ["camera", "black", "blurry", "photo", "spots"],
        "customer_name": "Alex",
        "story": "Alex's iPhone 15 Pro Max camera shows a black screen when opened. Photos are blurry and there are spots. The phone is 6 months old with AppleCare+.",
    },
    "Software: Instability (self-resolvable)": {
        "profile": "software_unstable",
        "model": "iPhone 14",
        "symptom_text": "My phone keeps crashing and restarting. Apps close randomly and everything is very slow. I think my phone is broken.",
        "category": "software",
        "keywords": ["crash", "restart", "slow", "freeze", "app", "closes", "broken"],
        "customer_name": "Tom",
        "story": "Tom's iPhone keeps crashing — Safari closes randomly, the phone restarts on its own, and everything feels slow. He hasn't updated iOS in over a year and his storage is almost full.",
    },
    "Storage: Full Storage Mimicking Hardware Failure": {
        "profile": "storage_full",
        "model": "iPhone 13",
        "symptom_text": "My phone is broken. I can't take photos, apps keep crashing, and it won't let me update anything.",
        "category": "storage",
        "keywords": ["photo", "crash", "update", "broken", "slow"],
        "customer_name": "June",
        "story": "June's iPhone is 'broken' — she can't take photos, apps crash, and it won't update. She's ready to buy a new phone. The real issue: 2.2 GB free on a 64GB phone.",
    },
    "Complex: Multi-Subsystem Board-Level": {
        "profile": "multi_failure",
        "model": "iPhone 14",
        "symptom_text": "Everything is going wrong. Battery dies fast and phone gets hot. Screen flickers and doesn't respond to touch sometimes. Wi-Fi and Bluetooth keep disconnecting.",
        "category": "multiple",
        "keywords": ["battery", "dies", "hot", "screen", "flicker", "touch", "wifi", "bluetooth", "disconnects", "multiple", "everything"],
        "customer_name": "David",
        "story": "David's iPhone 14 has everything going wrong: battery dies fast, screen flickers, Wi-Fi drops, and Bluetooth won't connect. He's been to the store **3 times**, each time they replaced one thing and sent him home.",
    },
}


# ---------------------------------------------------------------------------
# Helper: Run the diagnostic pipeline
# ---------------------------------------------------------------------------

def run_pipeline(profile, model, symptom_text, category, keywords):
    """Execute the full diagnostic pipeline and store results."""
    report = engine["simulator"].generate(profile, model)
    findings = engine["parser"].parse(report)
    symptoms = [CustomerSymptom(
        description=symptom_text,
        category=category,
        keywords=keywords,
    )]
    analysis = engine["analyzer"].analyze(findings, symptoms)
    passport = engine["passport_gen"].generate(report, findings, analysis, symptoms)

    st.session_state.report = report
    st.session_state.findings = findings
    st.session_state.analysis = analysis
    st.session_state.passport = passport
    st.session_state.stage = "results"


# ---------------------------------------------------------------------------
# Helper: Render subsystem status badges
# ---------------------------------------------------------------------------

def render_subsystem_status(passport):
    """Render the subsystem check grid."""
    icon_map = {
        "battery": "Battery",
        "storage": "Storage",
        "connectivity": "Connectivity",
        "display": "Display",
        "sensors": "Sensors",
        "camera": "Camera",
        "system": "System",
        "software": "Software",
    }
    for subsystem in passport.all_subsystems_checked:
        name = icon_map.get(subsystem, subsystem.title())
        if subsystem in passport.subsystems_flagged:
            is_crit = any(f["subsystem"] == subsystem for f in passport.critical_findings)
            if is_crit:
                st.markdown(f'<div class="subsystem-row"><span class="subsystem-name">{name}</span><span class="badge-fail">FAIL</span></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="subsystem-row"><span class="subsystem-name">{name}</span><span class="badge-warn">WARN</span></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="subsystem-row"><span class="subsystem-name">{name}</span><span class="badge-pass">PASS</span></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helper: Render findings list
# ---------------------------------------------------------------------------

def render_findings(passport, show_detail=False):
    """Render diagnostic findings."""
    for f in passport.critical_findings:
        detail_html = f'<div class="finding-detail">{f["detail"]}</div>' if show_detail else ""
        st.markdown(
            f'<div class="finding-critical">'
            f'<div class="finding-title">CRITICAL: {f["title"]}</div>'
            f'{detail_html}</div>',
            unsafe_allow_html=True
        )
    for f in passport.warning_findings:
        detail_html = f'<div class="finding-detail">{f["detail"]}</div>' if show_detail else ""
        st.markdown(
            f'<div class="finding-warning">'
            f'<div class="finding-title">WARNING: {f["title"]}</div>'
            f'{detail_html}</div>',
            unsafe_allow_html=True
        )
    for f in passport.info_findings:
        detail_html = f'<div class="finding-detail">{f["detail"]}</div>' if show_detail else ""
        st.markdown(
            f'<div class="finding-info">'
            f'<div class="finding-title">INFO: {f["title"]}</div>'
            f'{detail_html}</div>',
            unsafe_allow_html=True
        )


# ---------------------------------------------------------------------------
# Helper: Render confidence meter
# ---------------------------------------------------------------------------

def render_confidence(passport):
    """Render the confidence meter."""
    pct = passport.confidence_pct
    level = passport.confidence
    fill_class = {
        "high": "confidence-fill-high",
        "medium": "confidence-fill-medium",
        "low": "confidence-fill-low",
    }.get(level, "confidence-fill-medium")

    color = {"high": "#34c759", "medium": "#ff9f0a", "low": "#ff3b30"}.get(level, "#ff9f0a")
    st.markdown(f"**Diagnostic Confidence:** {level.upper()} ({pct}%)")
    st.markdown(
        f'<div class="confidence-bar">'
        f'<div class="{fill_class}" style="width: {pct}%"></div>'
        f'</div>',
        unsafe_allow_html=True
    )


# ---------------------------------------------------------------------------
# CUSTOMER VIEW
# ---------------------------------------------------------------------------

def render_customer_view(passport):
    """Render the customer-facing Diagnostics Passport."""

    st.markdown(
        '<div class="apple-header">'
        '<h1>Diagnostics Passport</h1>'
        '<p>Your Device Health Report</p>'
        '</div>',
        unsafe_allow_html=True
    )

    # Device info card
    st.markdown('<div class="diagnostic-card">', unsafe_allow_html=True)
    st.markdown("#### Your Device")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Model:** {passport.device_model}")
        st.markdown(f"**iOS:** {passport.os_version}")
    with col2:
        ac_map = {"active": "Active (covered)", "expired": "Expired", "none": "Not enrolled"}
        st.markdown(f"**AppleCare:** {ac_map.get(passport.applecare_status, passport.applecare_status)}")
        st.markdown(f'<span class="passport-id">{passport.passport_id}</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # What you told us
    st.markdown('<div class="diagnostic-card">', unsafe_allow_html=True)
    st.markdown("#### What You Told Us")
    for s in passport.customer_symptoms:
        st.markdown(f'> *"{s}"*')
    st.markdown('</div>', unsafe_allow_html=True)

    # What we checked
    st.markdown('<div class="diagnostic-card">', unsafe_allow_html=True)
    st.markdown("#### What We Checked")
    render_subsystem_status(passport)
    st.markdown('</div>', unsafe_allow_html=True)

    # What we found
    st.markdown('<div class="diagnostic-card">', unsafe_allow_html=True)
    st.markdown("#### What We Found")
    if passport.critical_findings or passport.warning_findings:
        render_findings(passport, show_detail=False)
    else:
        st.success("Everything looks good!")
    st.markdown('</div>', unsafe_allow_html=True)

    # Recommendation
    st.markdown('<div class="diagnostic-card">', unsafe_allow_html=True)
    st.markdown("#### Our Recommendation")
    render_confidence(passport)

    if passport.can_self_resolve:
        steps_html = "".join(f"<p>{i}. {s}</p>" for i, s in enumerate(passport.self_resolve_steps, 1))
        st.markdown(
            f'<div class="self-resolve-box">'
            f'<h4>You can likely resolve this yourself</h4>'
            f'{steps_html}'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown("")
        st.info("If the issue persists after following these steps, your passport will update automatically and we'll recommend a Genius Bar visit.")
    else:
        parts_text = f"Parts identified: {', '.join(passport.parts_needed)}" if passport.parts_needed else ""
        time_text = f"Estimated repair time: ~{passport.estimated_repair_minutes} min" if passport.estimated_repair_minutes else ""
        pre_order_text = "Parts will be pre-staged at your store." if passport.pre_order_parts else ""

        st.markdown(
            f'<div class="repair-box">'
            f'<h4>{passport.recommended_repair}</h4>'
            f'<p>{parts_text}</p>'
            f'<p>{time_text}</p>'
            f'<p>{pre_order_text}</p>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown("")
        if passport.appointment_recommendation == "urgent":
            st.markdown(
                '<div class="cta-button">Book Genius Bar Appointment</div>',
                unsafe_allow_html=True
            )
        elif passport.appointment_recommendation == "recommended":
            st.markdown(
                '<div class="cta-button">Schedule Genius Bar Visit</div>',
                unsafe_allow_html=True
            )

    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# GENIUS VIEW
# ---------------------------------------------------------------------------

def render_genius_view(passport):
    """Render the Genius-facing Diagnostics Passport."""

    st.markdown(
        '<div class="apple-header">'
        '<h1>Genius Diagnostics Passport</h1>'
        '<p>Internal | Pre-Triage Complete</p>'
        '</div>',
        unsafe_allow_html=True
    )

    # Quick reference
    st.markdown('<div class="diagnostic-card">', unsafe_allow_html=True)
    st.markdown("#### Quick Reference")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Passport:** `{passport.passport_id}`")
        st.markdown(f"**Device:** {passport.device_model}")
    with col2:
        st.markdown(f"**Serial:** `{passport.serial_number}`")
        st.markdown(f"**iOS:** {passport.os_version}")
    with col3:
        st.markdown(f"**Age:** {passport.device_age_months} months")
        ac_badge = {
            "active": '<span class="badge-pass">APPLECARE ACTIVE</span>',
            "expired": '<span class="badge-warn">APPLECARE EXPIRED</span>',
            "none": '<span class="badge-fail">NO APPLECARE</span>',
        }
        st.markdown(ac_badge.get(passport.applecare_status, ""), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Customer symptoms
    st.markdown('<div class="diagnostic-card">', unsafe_allow_html=True)
    st.markdown("#### Customer-Reported Symptoms")
    for s in passport.customer_symptoms:
        st.markdown(f"> {s}")
    st.markdown('</div>', unsafe_allow_html=True)

    # Root cause analysis — the key section
    st.markdown('<div class="diagnostic-card">', unsafe_allow_html=True)
    st.markdown("#### Root Cause Analysis")
    render_confidence(passport)
    st.markdown("")
    st.markdown(passport.root_cause)
    st.markdown('</div>', unsafe_allow_html=True)

    # Evidence chain
    st.markdown('<div class="diagnostic-card">', unsafe_allow_html=True)
    st.markdown("#### Evidence Chain")
    st.caption("How the system arrived at this root cause:")
    for step in passport.evidence_chain:
        st.markdown(
            f'<div class="evidence-step">{step}</div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # All findings with detail
    st.markdown('<div class="diagnostic-card">', unsafe_allow_html=True)
    summary = passport.findings_summary
    st.markdown(f"#### Diagnostic Findings &nbsp;&nbsp;"
                f'<span class="badge-fail">{summary["critical"]} Critical</span>'
                f'<span class="badge-warn">{summary["warning"]} Warning</span>'
                f'<span class="badge-info">{summary["info"]} Info</span>',
                unsafe_allow_html=True)
    render_findings(passport, show_detail=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Repair recommendation
    st.markdown('<div class="diagnostic-card">', unsafe_allow_html=True)
    st.markdown("#### Repair Recommendation")

    rcol1, rcol2, rcol3 = st.columns(3)
    with rcol1:
        st.markdown(f"**Action:** {passport.recommended_repair}")
    with rcol2:
        if passport.parts_needed:
            st.markdown(f"**Parts:** {', '.join(passport.parts_needed)}")
        else:
            st.markdown("**Parts:** None required")
    with rcol3:
        st.markdown(f"**Est. Time:** {passport.estimated_repair_minutes} min")
        if passport.pre_order_parts:
            st.markdown('<span class="badge-pass">PARTS PRE-ORDERED</span>', unsafe_allow_html=True)

    if passport.secondary_actions:
        st.markdown("**Additional Actions:**")
        for a in passport.secondary_actions:
            st.markdown(f"- {a}")

    st.markdown('</div>', unsafe_allow_html=True)

    # Genius notes
    st.markdown('<div class="diagnostic-card">', unsafe_allow_html=True)
    st.markdown("#### Technician Notes")
    st.markdown(
        f'<div class="genius-notes">{passport.genius_notes}</div>',
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# MTTR IMPACT DASHBOARD
# ---------------------------------------------------------------------------

def render_mttr_dashboard(passport):
    """Render the MTTR impact comparison."""

    st.markdown("---")
    st.markdown("### MTTR Impact: Before vs. After")
    st.caption("Comparison of Genius Bar workflow with and without the Diagnostics Passport")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            '<div class="metric-card">'
            '<div class="metric-value-red">13-20 min</div>'
            '<div class="metric-label">WITHOUT Passport<br>Pre-repair time</div>'
            '</div>',
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            '<div class="metric-card">'
            '<div class="metric-value-green">3-4 min</div>'
            '<div class="metric-label">WITH Passport<br>Pre-repair time</div>'
            '</div>',
            unsafe_allow_html=True
        )

    with col3:
        is_deflection = passport.can_self_resolve if passport else False
        if is_deflection:
            st.markdown(
                '<div class="metric-card">'
                '<div class="metric-value-green">DEFLECTED</div>'
                '<div class="metric-label">Visit Outcome<br>Self-resolved, no appointment</div>'
                '</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div class="metric-card">'
                '<div class="metric-value">~70-80%</div>'
                '<div class="metric-label">MTTR Reduction<br>Pre-repair phase</div>'
                '</div>',
                unsafe_allow_html=True
            )

    with col4:
        if passport and passport.pre_order_parts:
            st.markdown(
                '<div class="metric-card">'
                '<div class="metric-value-green">PRE-STAGED</div>'
                '<div class="metric-label">Parts Status<br>Ready at store</div>'
                '</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div class="metric-card">'
                '<div class="metric-value">N/A</div>'
                '<div class="metric-label">Parts Status<br>No parts needed</div>'
                '</div>',
                unsafe_allow_html=True
            )

    # Before/After workflow comparison
    st.markdown("")
    b_col, a_col = st.columns(2)

    with b_col:
        st.markdown("**Without Diagnostics Passport**")
        st.markdown("""
        1. Customer checks in at store *(1 min)*
        2. Genius asks: "What's the problem?" *(2-3 min)*
        3. Genius runs AST diagnostic suite *(5-10 min)*
        4. Genius interprets results *(3-5 min)*
        5. Genius checks parts availability *(2-3 min)*
        6. Repair begins or customer told to come back

        **Total pre-repair: 13-20 minutes**
        **Risk: Intermittent issues missed by AST**
        """)

    with a_col:
        st.markdown("**With Diagnostics Passport**")
        st.markdown("""
        1. Customer checks in — Genius reads passport *(1 min)*
        2. Genius confirms with targeted inspection *(2-3 min)*
        3. Parts already pre-staged at store
        4. Repair begins immediately

        **Total pre-repair: 3-4 minutes**
        **Intermittent issues captured via monitoring**
        """)


# ---------------------------------------------------------------------------
# MAIN APPLICATION FLOW
# ---------------------------------------------------------------------------

# Header
st.markdown(
    '<div class="apple-header">'
    '<h1>AppleCare Self-Service Diagnostics</h1>'
    '<p>AI-Powered Pre-Triage Prototype</p>'
    '</div>',
    unsafe_allow_html=True
)

# --- Stage: Intake ---
if scenario == "-- Select --" and st.session_state.stage == "intake":
    st.markdown("")
    st.info("Select a demo scenario from the sidebar to get started, or choose 'Custom' to enter your own symptoms.")

    # Show available scenarios as cards
    st.markdown("### Demo Scenarios")
    for name, config in SCENARIOS.items():
        with st.expander(f"{name}"):
            st.markdown(config["story"])

elif scenario == "Custom: Enter Your Own Symptoms" and st.session_state.stage != "results":
    st.markdown("### Describe Your Issue")

    custom_symptom = st.text_area(
        "What's happening with your device?",
        placeholder="Example: My screen flickers randomly when I open the camera...",
        height=100,
    )

    col1, col2 = st.columns(2)
    with col1:
        custom_category = st.selectbox(
            "Primary issue area:",
            ["display", "battery", "connectivity", "camera",
             "software", "storage", "other"]
        )
    with col2:
        custom_profile = st.selectbox(
            "Simulated device condition:",
            list(engine["simulator"].PROFILES.keys()),
            help="Since this is a prototype, select which device condition to simulate."
        )

    if st.button("Run Diagnostics", type="primary", use_container_width=True):
        if custom_symptom:
            # Extract simple keywords
            keywords = [w.lower().strip(".,!?") for w in custom_symptom.split()
                        if len(w) > 3]
            with st.spinner("Running diagnostic pipeline..."):
                time.sleep(1.5)  # Brief pause for demo effect
                run_pipeline(
                    profile=custom_profile,
                    model=None,
                    symptom_text=custom_symptom,
                    category=custom_category,
                    keywords=keywords,
                )
                st.rerun()
        else:
            st.warning("Please describe your issue first.")

elif scenario != "-- Select --" and scenario != "Custom: Enter Your Own Symptoms":
    config = SCENARIOS.get(scenario)
    if config and st.session_state.stage != "results":
        # Show the scenario story
        st.markdown(f"### Scenario: {scenario.split(':')[0]} Issue")
        st.markdown(config["story"])
        st.markdown(f'**Customer says:** *"{config["symptom_text"]}"*')
        st.markdown("")

        if st.button("Run Self-Service Diagnostics", type="primary", use_container_width=True):
            with st.spinner("Running diagnostic pipeline..."):
                time.sleep(1.5)
                run_pipeline(
                    profile=config["profile"],
                    model=config.get("model"),
                    symptom_text=config["symptom_text"],
                    category=config["category"],
                    keywords=config["keywords"],
                )
                st.rerun()

# --- Stage: Results ---
if st.session_state.stage == "results" and st.session_state.passport:
    passport = st.session_state.passport

    # Reset button
    if st.button("Start New Diagnostic", type="secondary"):
        st.session_state.stage = "intake"
        st.session_state.passport = None
        st.session_state.report = None
        st.session_state.findings = None
        st.session_state.analysis = None
        st.rerun()

    # Render based on view mode
    if view_mode == "Customer View":
        render_customer_view(passport)
        render_mttr_dashboard(passport)

    elif view_mode == "Genius Bar View":
        render_genius_view(passport)
        render_mttr_dashboard(passport)

    elif view_mode == "Side-by-Side":
        customer_col, genius_col = st.columns(2)
        with customer_col:
            st.markdown("## Customer View")
            render_customer_view(passport)
        with genius_col:
            st.markdown("## Genius Bar View")
            render_genius_view(passport)

        render_mttr_dashboard(passport)
