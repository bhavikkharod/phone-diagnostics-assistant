# AppleCare Self-Service Diagnostics Assistant

AI-powered pre-triage diagnostics prototype that reduces Genius Bar MTTR by triangulating customer-reported symptoms with device system report data to identify root cause and generate a Diagnostics Passport.

## Architecture

```
Customer Symptoms + Device System Report
        │                    │
        ▼                    ▼
   ┌─────────────────────────────┐
   │  Log Parser (Module 2)      │  Extracts findings from device data
   └──────────────┬──────────────┘
                  ▼
   ┌─────────────────────────────┐
   │  Log Analyzer (Module 3)    │  Triangulates root cause via
   │                             │  correlation rules engine
   └──────────────┬──────────────┘
                  ▼
   ┌─────────────────────────────┐
   │  Passport Generator (Mod 4) │  Generates customer + Genius views
   └──────────────┬──────────────┘
                  ▼
        Diagnostics Passport
        (Customer View + Genius View)
```

## Modules

| Module | File | Purpose |
|---|---|---|
| Device Simulator | `system_report_simulator.py` | Generates realistic device system reports (battery, storage, sensors, crash logs) |
| Log Parser | `log_parser.py` | Checks metrics against thresholds, extracts findings with severity levels |
| Log Analyzer | `log_analyzer.py` | Cross-references findings + symptoms using correlation rules to triangulate root cause |
| Passport Generator | `diagnostics_passport.py` | Creates structured Diagnostics Passport for customer and Genius views |
| Triage Engine | `triage_engine.py` | Orchestrator that runs the full pipeline; includes 7 demo scenarios |
| Interactive UI | `app.py` | Streamlit-based interactive prototype with Customer, Genius, and Side-by-Side views |

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## CLI Demo

```bash
python3 triage_engine.py display    # Intermittent display flicker
python3 triage_engine.py battery    # Battery thermal cascade
python3 triage_engine.py software   # Self-resolvable (no repair needed)
python3 triage_engine.py complex    # Multi-subsystem board-level failure
python3 triage_engine.py all        # Run all 7 scenarios
```

## Demo Scenarios

| Scenario | Key Insight |
|---|---|
| **Display Flicker** | Captures intermittent issues that point-in-time AST misses — the #1 repeat visit driver |
| **Battery Degradation** | Identifies thermal cascade as root cause (not just battery), preventing misdiagnosis |
| **Connectivity** | Correlates multi-radio failures to shared antenna flex cable rather than individual modules |
| **Camera** | Hardware module failure with parts pre-order |
| **Software** | Deflects visit entirely — self-resolvable with OS update + storage cleanup |
| **Storage** | Identifies full storage mimicking hardware failure — saves unnecessary repair |
| **Complex** | Multiple subsystem failures pointing to logic board — prevents piecemeal repairs |
