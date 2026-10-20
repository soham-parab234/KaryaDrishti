"""LMIS Labour Market Intelligence AI Assistant Service.

Provides grounded decision-support analysis for labour & skilling authorities.
Adheres strictly to LMIS Master R&D and AI Handoff guardrails:
1. One configurable external provider (Google Gemini) via server-side API key.
2. Grounded strictly in LMIS database models (Demand, Supply, Gaps, Forecasts, Alerts, Recommendations).
3. Read-only service: cannot modify or approve data.
4. Deterministic, comprehensive rule-based fallback when no credentials are provided or on provider error.
5. Explicit distinction between empirical data, synthetic demonstration data, and planned connectors.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional, Any
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.config import settings
from backend.app.models.occupation import NcoOccupation
from backend.app.models.analytics import (
    DemandObservation,
    QualifiedSupplyEstimate,
    TrainingCapacityOutcome,
)
from backend.app.models.alerts import EarlyWarningAlert
from backend.app.models.recommendations import PolicyRecommendation
from backend.app.models.forecasting import ForecastRun, ForecastPoint
from backend.app.schemas.ai import AiEvidenceItem, AiQueryRequest, AiQueryResponse

logger = logging.getLogger(__name__)

STANDARD_LIMITATIONS = [
    "Documented demand reflects captured employer signals/postings, not total macroeconomic vacancies.",
    "Qualified supply estimates represent certified/trained labor pools, NOT raw worker registrations (e.g. e-Shram).",
    "Training capacity reflects sanctioned institutional seats, NOT immediately available qualified workers.",
    "Data provenance: Maharashtra Pilot Baseline consists of calibrated synthetic demonstration data; live government portal connectors (NCS, e-Shram, SIDH) remain planned integrations.",
]


def extract_district_code(query: str, explicit_district: Optional[str] = None) -> Optional[str]:
    """Identify district filter from explicit parameter or query text."""
    if explicit_district:
        if explicit_district in ("MH_PUN", "Pune", "pune"):
            return "MH_PUN"
        if explicit_district in ("MH_NSK", "Nashik", "nashik"):
            return "MH_NSK"
        return explicit_district

    query_lower = query.lower()
    if "pune" in query_lower or "mh_pun" in query_lower:
        return "MH_PUN"
    if "nashik" in query_lower or "mh_nsk" in query_lower:
        return "MH_NSK"
    return None


def retrieve_grounded_evidence(
    db: Session,
    query: str,
    district_code: Optional[str] = None,
    occupation_code: Optional[str] = None,
) -> tuple[list[AiEvidenceItem], list[dict[str, Any]], list[str]]:
    """Retrieve verified database records relevant to the user query."""
    district = extract_district_code(query, district_code)
    query_lower = query.lower()
    sources_used: list[str] = ["NcoOccupation"]

    # 1. Query occupations
    occ_query = db.query(NcoOccupation)
    if occupation_code:
        occ_query = occ_query.filter(NcoOccupation.nco_code == occupation_code)
    occupations = occ_query.all()

    # Determine matched occupations based on keywords if specific occupation not supplied
    matched_occs: list[NcoOccupation] = []
    if occupation_code:
        matched_occs = list(occupations)
    else:
        for occ in occupations:
            title_lower = occ.canonical_title.lower()
            code = occ.nco_code
            if (
                code in query_lower
                or (
                    "solar" in query_lower
                    and ("solar" in title_lower or "7421" in code)
                )
                or (
                    ("mechanic" in query_lower or "machinery" in query_lower)
                    and ("machinery" in title_lower or "7233" in code)
                )
                or (
                    ("it" in query_lower or "computer" in query_lower)
                    and ("technology" in title_lower or "3511" in code)
                )
                or (
                    "weld" in query_lower
                    and ("weld" in title_lower or "7212" in code)
                )
                or (
                    "nurse" in query_lower
                    and ("nurse" in title_lower or "3221" in code)
                )
            ):
                matched_occs.append(occ)

        # Default fallback: if no keyword match, inspect top occupations
        if not matched_occs:
            matched_occs = occupations[:4]

    matched_codes = [occ.nco_code for occ in matched_occs]

    # 2. Query demand observations
    sources_used.append("DemandObservation")
    demand_q = db.query(DemandObservation).filter(
        DemandObservation.nco_code.in_(matched_codes)
    )
    if district:
        demand_q = demand_q.filter(DemandObservation.district_code == district)
    demands = demand_q.all()

    # 3. Query qualified supply estimates
    sources_used.append("QualifiedSupplyEstimate")
    supply_q = db.query(QualifiedSupplyEstimate).filter(
        QualifiedSupplyEstimate.nco_code.in_(matched_codes)
    )
    if district:
        supply_q = supply_q.filter(
            QualifiedSupplyEstimate.district_code == district
        )
    supplies = supply_q.all()

    # 4. Query training capacity
    sources_used.append("TrainingCapacityOutcome")
    capacity_q = db.query(TrainingCapacityOutcome).filter(
        TrainingCapacityOutcome.nco_code.in_(matched_codes)
    )
    if district:
        capacity_q = capacity_q.filter(
            TrainingCapacityOutcome.district_code == district
        )
    capacities = capacity_q.all()

    # Index by (nco_code, district_code, reporting_period) with multi-record aggregation
    demand_groups: dict[tuple[str, str, str], list[DemandObservation]] = {}
    for d in demands:
        key = (d.nco_code, d.district_code, d.reporting_period)
        demand_groups.setdefault(key, []).append(d)

    supply_map = {
        (s.nco_code, s.district_code, s.reporting_period): s for s in supplies
    }
    capacity_map = {
        (c.nco_code, c.district_code, c.reporting_period): c for c in capacities
    }
    occ_title_map = {occ.nco_code: occ.canonical_title for occ in occupations}

    evidence_items: list[AiEvidenceItem] = []
    unique_keys = set(demand_groups.keys()) | set(supply_map.keys())

    for nco_code, dist_code, period in sorted(unique_keys):
        d_recs = demand_groups.get((nco_code, dist_code, period), [])
        s_rec = supply_map.get((nco_code, dist_code, period))
        c_rec = capacity_map.get((nco_code, dist_code, period))

        if d_recs:
            total_demand = sum(r.demand_value for r in d_recs)
            d_val = float(total_demand)
            has_imported = any(r.data_status in ("IMPORTED", "REAL_PUBLIC_DATA") for r in d_recs)
            has_baseline = any(r.data_status == "PILOT_BASELINE" for r in d_recs)
            if has_imported and has_baseline:
                status_label = "HYBRID_ESTIMATE"
            elif has_imported:
                status_label = "IMPORTED"
            else:
                status_label = "SYNTHETIC DEMO"
        else:
            d_val = None
            status_label = "SYNTHETIC DEMO"

        s_val = float(s_rec.supply_value) if s_rec else None

        abs_gap: Optional[float] = None
        gap_rate: Optional[float] = None
        risk: Optional[str] = "INSUFFICIENT_DATA"

        if d_val is not None and s_val is not None:
            abs_gap = round(d_val - s_val, 1)
            if d_val > 0:
                gap_rate = round((abs_gap / d_val) * 100.0, 1)
            if abs_gap > 100 or (gap_rate and gap_rate > 20.0):
                risk = "CRITICAL_SHORTAGE"
            elif abs_gap > 0:
                risk = "MODERATE_SHORTAGE"
            elif abs_gap < -100:
                risk = "POTENTIAL_OVERSUPPLY"
            else:
                risk = "BALANCED"

        t_seats = c_rec.sanctioned_seats if c_rec else None
        p_rate = (
            float(c_rec.placement_rate_pct)
            if (c_rec and c_rec.placement_rate_pct is not None)
            else None
        )

        evidence_items.append(
            AiEvidenceItem(
                nco_code=nco_code,
                canonical_title=occ_title_map.get(
                    nco_code, "Unclassified Occupation"
                ),
                district_code=dist_code,
                reporting_period=period,
                demand_value=d_val,
                supply_value=s_val,
                absolute_gap=abs_gap,
                gap_rate_pct=gap_rate,
                training_seats=t_seats,
                placement_rate_pct=p_rate,
                risk_level=risk,
                data_status=status_label,
            )
        )

    # 5. Supplementary context: Forecasts, Alerts and Recommendations
    sources_used.extend(["ForecastRun", "ForecastPoint", "EarlyWarningAlert", "PolicyRecommendation"])
    
    # Query latest forecast runs
    forecast_q = db.query(ForecastRun).filter(
        ForecastRun.nco_code.in_(matched_codes)
    )
    if district:
        forecast_q = forecast_q.filter(ForecastRun.district_code == district)
    latest_runs = forecast_q.order_by(desc(ForecastRun.created_at)).limit(4).all()

    extra_context: list[dict[str, Any]] = []
    for run in latest_runs:
        pts = (
            db.query(ForecastPoint)
            .filter(ForecastPoint.forecast_run_id == run.id)
            .order_by(ForecastPoint.step_ahead)
            .all()
        )
        if pts:
            extra_context.append(
                {
                    "type": "FORECAST",
                    "nco_code": run.nco_code,
                    "district_code": run.district_code,
                    "target_metric": run.target_metric,
                    "selected_model": run.selected_model_name,
                    "horizon_periods": run.horizon_periods,
                    "data_status": run.data_status,
                    "points": [
                        {
                            "period": p.period,
                            "step": p.step_ahead,
                            "forecast_value": p.forecast_value,
                            "lower_bound": p.lower_bound,
                            "upper_bound": p.upper_bound,
                        }
                        for p in pts
                    ],
                }
            )

    alert_q = db.query(EarlyWarningAlert).filter(
        EarlyWarningAlert.nco_code.in_(matched_codes)
    )
    if district:
        alert_q = alert_q.filter(EarlyWarningAlert.district_code == district)
    alerts = alert_q.limit(5).all()

    rec_q = db.query(PolicyRecommendation).filter(
        PolicyRecommendation.nco_code.in_(matched_codes)
    )
    if district:
        rec_q = rec_q.filter(PolicyRecommendation.district_code == district)
    recommendations = rec_q.limit(5).all()

    for a in alerts:
        extra_context.append(
            {
                "type": "ALERT",
                "nco_code": a.nco_code,
                "district_code": a.district_code,
                "severity": a.severity,
                "title": a.title,
                "trigger_rule": a.trigger_rule,
                "review_action": a.review_action_recommended,
                "triage_status": a.triage_status,
            }
        )
    for r in recommendations:
        extra_context.append(
            {
                "type": "RECOMMENDATION",
                "nco_code": r.nco_code,
                "district_code": r.district_code,
                "action_title": r.action_title,
                "priority": r.priority,
                "proposed_seat_adjustment": r.proposed_seat_adjustment,
                "rationale": r.rationale,
            }
        )

    return evidence_items, extra_context, sources_used


def generate_rule_based_response(
    query: str,
    evidence: list[AiEvidenceItem],
    extra_context: list[dict[str, Any]],
    district_code: Optional[str] = None,
) -> str:
    """Deterministic, grounded rule-based LMIS intelligence response."""
    district_name = (
        "Pune (MH_PUN)"
        if district_code == "MH_PUN"
        else (
            "Nashik (MH_NSK)"
            if district_code == "MH_NSK"
            else "Maharashtra Pilot (Pune & Nashik)"
        )
    )

    if not evidence:
        return (
            f"### LMIS Analytical Intelligence Briefing\n\n"
            f"**Geographic Scope:** {district_name}\n\n"
            f"No specific empirical or baseline records matching query '{query}' were found in the current dataset. "
            f"Please verify the occupation code (e.g., Solar PV 7421.0301, Machinist 7233.0100) or check whether "
            f"new job postings require import via the Data Ingestion portal."
        )

    # Sort evidence by absolute gap descending (highest shortages first)
    shortages = [e for e in evidence if e.absolute_gap and e.absolute_gap > 0]
    surpluses = [e for e in evidence if e.absolute_gap and e.absolute_gap < 0]

    lines: list[str] = [
        f"### LMIS Labour Market Intelligence Briefing",
        f"**Geographic Scope:** {district_name} | **Evaluation Cycle:** 2026-10",
        f"**Engine Status:** Grounded Deterministic Intelligence (Rule-Based Fallback)",
        "",
        "#### 1. Key Analytical Findings",
    ]

    for item in evidence[:5]:
        gap_sign = "+" if (item.absolute_gap and item.absolute_gap > 0) else ""
        gap_str = (
            f"{gap_sign}{int(item.absolute_gap)}"
            if item.absolute_gap is not None
            else "N/A"
        )
        rate_str = (
            f"{item.gap_rate_pct}%" if item.gap_rate_pct is not None else "N/A"
        )
        lines.append(
            f"- **{item.canonical_title}** (`{item.nco_code}`, {item.district_code}): "
            f"Observed Demand: **{int(item.demand_value or 0)}**, "
            f"Qualified Supply: **{int(item.supply_value or 0)}** → "
            f"Gap: **{gap_str}** ({rate_str} gap rate). "
            f"Status: `{item.risk_level}` [{item.data_status}]."
        )

    if shortages:
        top_shortage = sorted(
            shortages, key=lambda x: x.absolute_gap or 0, reverse=True
        )[0]
        lines.append("")
        lines.append(
            f"**Primary Deficit:** `{top_shortage.canonical_title}` in {top_shortage.district_code} "
            f"exhibits a documented shortage of **{int(top_shortage.absolute_gap or 0)}** workers "
            f"({top_shortage.gap_rate_pct}% gap rate). Sanctioned training seats: "
            f"{top_shortage.training_seats or 'N/A'} (placement rate: {top_shortage.placement_rate_pct or 'N/A'}%)."
        )

    if surpluses:
        top_surplus = sorted(surpluses, key=lambda x: x.absolute_gap or 0)[0]
        lines.append(
            f"**Surplus Observation:** `{top_surplus.canonical_title}` in {top_surplus.district_code} "
            f"exhibits a localized potential oversupply of **{abs(int(top_surplus.absolute_gap or 0))}** workers, "
            f"suggesting high institutional turnout relative to captured hiring signals."
        )

    # 2. Demand Forecast Projections
    forecasts = [c for c in extra_context if c.get("type") == "FORECAST"]
    occ_map = {item.nco_code: item.canonical_title for item in evidence}
    if forecasts:
        lines.append("")
        lines.append("#### 2. Demand Forecast Projections (Next Horizon)")
        for f in forecasts[:3]:
            pts = f.get("points", [])
            if pts:
                first_pt = pts[0]
                last_pt = pts[-1]
                title = occ_map.get(f.get("nco_code"), f.get("nco_code"))
                ci_str = (
                    f"95% Analytical Interval: [{int(last_pt.get('lower_bound') or 0)} – {int(last_pt.get('upper_bound') or 0)}]"
                    if last_pt.get("lower_bound") is not None
                    else "Deterministic Projection"
                )
                lines.append(
                    f"- **{title}** ({f.get('district_code')}): "
                    f"Selected Model: `{f.get('selected_model')}`. "
                    f"Horizon: {f.get('horizon_periods')} periods. "
                    f"Period {first_pt.get('period')}: **{int(first_pt.get('forecast_value', 0))}** → "
                    f"Period {last_pt.get('period')}: **{int(last_pt.get('forecast_value', 0))}** ({ci_str}). "
                    f"Provenance: `[{f.get('data_status', 'SYNTHETIC DEMO')}]`."
                )

    # 3. Active Early-Warning Alerts
    alerts = [c for c in extra_context if c.get("type") == "ALERT"]
    if alerts:
        lines.append("")
        lines.append("#### 3. Early-Warning & Risk Signals")
        for a in alerts[:3]:
            lines.append(
                f"- **[{a.get('severity')}] {a.get('title')}** ({a.get('district_code')}): "
                f"{a.get('review_action')} (Triage: `{a.get('triage_status', 'NEW')}`)."
            )

    # 4. Policy & Training Interventions
    recs = [c for c in extra_context if c.get("type") == "RECOMMENDATION"]
    if recs:
        lines.append("")
        lines.append("#### 4. Recommended Policy Actions")
        for r in recs[:3]:
            seat_adj = (
                f"(Proposed Seat Adjustment: +{r.get('proposed_seat_adjustment')})"
                if r.get("proposed_seat_adjustment")
                else ""
            )
            lines.append(
                f"- **[{r.get('priority')} Priority] {r.get('action_title')}** {seat_adj}: "
                f"{r.get('rationale')}"
            )

    lines.append("")
    lines.append("#### 5. Methodological Distinction")
    lines.append(
        "- **Training Capacity vs. Qualified Supply:** Institutional sanctioned seats measure training "
        "infrastructure capacity, whereas qualified supply accounts for actual course completion, "
        "certification pass rates, and regional entry dynamics."
    )

    return "\n".join(lines)


def is_configured_api_key(key: str) -> bool:
    """Check if API key is populated and not an unconfigured placeholder."""
    clean = key.strip()
    if not clean:
        return False
    if clean.lower() in (
        "your_gemini_api_key_here",
        "your_api_key_here",
        "<your_api_key>",
        "placeholder",
        "none",
    ):
        return False
    return True


async def call_gemini_provider(
    query: str,
    evidence: list[AiEvidenceItem],
    extra_context: list[dict[str, Any]],
    district_code: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Call Google Gemini API using server-side key. Returns (answer, error_msg)."""
    api_key = settings.GEMINI_API_KEY.strip()
    if not is_configured_api_key(api_key):
        return None, "NO_CREDENTIALS"

    model_name = settings.GEMINI_MODEL.strip() or "gemini-3.8-flash"
    timeout_seconds = getattr(settings, "GEMINI_TIMEOUT_SECONDS", 25.0)

    # Use x-goog-api-key header for security so the API key is NEVER exposed in the URL or query params
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    # Prepare grounding JSON payload for Gemini prompt
    evidence_json = [item.model_dump() for item in evidence]
    district_label = (
        district_code
        if district_code
        else "All Monitored Pilot Districts (Pune MH_PUN & Nashik MH_NSK)"
    )

    system_instruction = (
        "You are the senior Labour Market Intelligence Analyst for India's Labour Market Intelligence System (LMIS). "
        "Your responses guide state skilling directors, ITI administrators, and planning officers.\n\n"
        "STRICT GROUNDING RULES:\n"
        "1. Base all statements, figures, and conclusions EXCLUSIVELY on the verified LMIS data provided below.\n"
        "2. NEVER invent job numbers, wage figures, or training counts not present in the data.\n"
        "3. Explicitly distinguish between 'Sanctioned Training Seats' (capacity) and 'Qualified Supply' (available workers).\n"
        "4. Note that Maharashtra Pilot Baseline figures are calibrated synthetic demonstration data.\n"
        "5. Be concise, structured, and professional. Use markdown formatting with bullet points."
    )

    prompt = (
        f"{system_instruction}\n\n"
        f"--- VERIFIED LMIS DATABASE CONTEXT ---\n"
        f"Geographic Scope: {district_label}\n"
        f"Retrieved Records:\n{json.dumps(evidence_json, indent=2)}\n\n"
        f"Alerts and Recommendations Context:\n{json.dumps(extra_context, indent=2)}\n\n"
        f"--- USER QUERY ---\n"
        f"{query}\n\n"
        f"Please provide an executive intelligence briefing answering the user query grounded directly in the records above."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1024,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(
                url,
                json=payload,
                headers=headers,
            )

            # If configured model returns 404 (e.g. deprecated model in env), retry with gemini-3.8-flash
            if resp.status_code == 404 and model_name != "gemini-3.8-flash":
                logger.info(
                    "Configured model %s returned 404; retrying with gemini-3.8-flash",
                    model_name,
                )
                retry_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"
                resp = await client.post(
                    retry_url,
                    json=payload,
                    headers=headers,
                )

            if resp.status_code != 200:
                logger.warning(
                    "Gemini API returned HTTP status code %d for model %s",
                    resp.status_code,
                    model_name,
                )
                return (
                    None,
                    f"PROVIDER_HTTP_{resp.status_code}",
                )

            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts and "text" in parts[0]:
                    return parts[0]["text"].strip(), None

            return None, "EMPTY_PROVIDER_RESPONSE"

    except httpx.TimeoutException:
        logger.warning(
            "Gemini API request timed out after %.1f seconds.",
            timeout_seconds,
        )
        return None, "PROVIDER_TIMEOUT"
    except Exception as exc:
        logger.warning("Gemini API connection error: %s", type(exc).__name__)
        return None, f"NETWORK_ERROR: {type(exc).__name__}"


async def process_ai_query(db: Session, request: AiQueryRequest) -> AiQueryResponse:
    """Execute grounded intelligence query with single-provider integration and rule-based fallback."""
    query_text = request.query.strip()
    district = extract_district_code(query_text, request.district_code)

    # 1. Read-only retrieval of verified database records
    evidence, extra_context, sources_used = retrieve_grounded_evidence(
        db=db,
        query=query_text,
        district_code=district,
        occupation_code=request.occupation_code,
    )

    # 2. Attempt single configurable provider (Google Gemini) or configured rule-based mode
    answer_text: Optional[str] = None
    provider_err: Optional[str] = None
    mode = "RULE_BASED_FALLBACK"
    provider_desc = "Deterministic Rule-Based LMIS Engine"
    status = "SUCCESS"

    provider_setting = (settings.AI_PROVIDER or "gemini").strip().lower()

    if provider_setting in ("rule_based", "rule-based", "fallback", "none"):
        answer_text = generate_rule_based_response(
            query=query_text,
            evidence=evidence,
            extra_context=extra_context,
            district_code=district,
        )
        provider_desc = "Deterministic Rule-Based LMIS Engine (Configured Mode)"
    elif is_configured_api_key(settings.GEMINI_API_KEY):
        answer_text, provider_err = await call_gemini_provider(
            query=query_text,
            evidence=evidence,
            extra_context=extra_context,
            district_code=district,
        )
        if answer_text:
            mode = "PROVIDER_LLM"
            provider_desc = f"Google Gemini ({settings.GEMINI_MODEL or 'gemini-3.8-flash'})"

    # 3. Fallback execution if provider unavailable, not configured, or returned an error
    if not answer_text:
        answer_text = generate_rule_based_response(
            query=query_text,
            evidence=evidence,
            extra_context=extra_context,
            district_code=district,
        )
        if provider_err and provider_err != "NO_CREDENTIALS":
            status = "DEGRADED_FALLBACK"
            provider_desc = (
                f"Deterministic Rule-Based Fallback (Provider issue: {provider_err})"
            )
        elif not is_configured_api_key(settings.GEMINI_API_KEY):
            provider_desc = "Deterministic Rule-Based Engine (No GEMINI_API_KEY configured)"

    limitations = list(STANDARD_LIMITATIONS)
    if not evidence:
        status = "INSUFFICIENT_DATA"
        limitations.append(
            "Insufficient evidence: no exact occupation or district observations matched query parameters."
        )

    return AiQueryResponse(
        query=query_text,
        answer=answer_text,
        mode=mode,
        provider=provider_desc,
        status=status,
        evidence=evidence,
        limitations=limitations,
        sources_used=sources_used,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
