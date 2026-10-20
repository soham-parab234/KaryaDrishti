"""Early-Warning Alerts API routes.

Conforms to LMIS Master R&D Section 11 & 14:
- GET /api/alerts: Query early-warning alerts with filters by district, severity, or alert type.
- POST /api/alerts/evaluate: Run rule-based alert evaluation across current observations.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.alerts import EarlyWarningAlert
from backend.app.schemas.alerts import (
    EarlyWarningAlertItem,
    AlertEvaluationResponse,
    AlertTriageRequest,
)
from backend.app.services.alerts_service import evaluate_and_generate_alerts

router = APIRouter(prefix="/alerts", tags=["Early Warning Alerts"])


@router.get(
    "",
    response_model=list[EarlyWarningAlertItem],
    summary="List active early-warning alerts ranked by severity",
)
def list_alerts(
    district_code: str | None = Query(None, description="Filter by district (e.g. 'MH_PUN')"),
    nco_code: str | None = Query(None, description="Filter by NCO code (e.g. '7421.0301')"),
    alert_type: str | None = Query(None, description="Filter by type (SHORTAGE_RISK, OVERSUPPLY_RISK, etc.)"),
    severity: str | None = Query(None, description="Filter by severity (CRITICAL, WARNING, INFO)"),
    db: Session = Depends(get_db),
):
    """Retrieve early-warning alerts ranked by severity (CRITICAL first, then WARNING, then INFO)."""
    # Auto-evaluate if table is empty
    count = db.query(EarlyWarningAlert).count()
    if count == 0:
        evaluate_and_generate_alerts(db)

    q = db.query(EarlyWarningAlert)
    if district_code:
        q = q.filter(EarlyWarningAlert.district_code == district_code)
    if nco_code:
        q = q.filter(EarlyWarningAlert.nco_code == nco_code)
    if alert_type:
        q = q.filter(EarlyWarningAlert.alert_type == alert_type)
    if severity:
        q = q.filter(EarlyWarningAlert.severity == severity)

    alerts = q.all()
    # Sort CRITICAL -> WARNING -> INFO
    sev_rank = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    alerts.sort(key=lambda a: (sev_rank.get(a.severity, 3), -(a.absolute_gap or 0)))

    return [
        EarlyWarningAlertItem(
            alert_id=a.alert_id,
            nco_code=a.nco_code,
            canonical_title=a.canonical_title,
            district_code=a.district_code,
            reporting_period=a.reporting_period,
            alert_type=a.alert_type,
            severity=a.severity,
            title=a.title,
            trigger_rule=a.trigger_rule,
            evidence_summary=a.evidence_summary,
            review_action_recommended=a.review_action_recommended,
            observed_demand=a.observed_demand,
            estimated_supply=a.estimated_supply,
            absolute_gap=a.absolute_gap,
            gap_rate_pct=a.gap_rate_pct,
            threshold_type=a.threshold_type,
            triage_status=getattr(a, "triage_status", "NEW") or "NEW",
            triage_note=getattr(a, "triage_note", None),
            data_status=a.data_status,
            limitations=a.limitations,
            created_at=a.created_at.isoformat() if a.created_at else "",
        )
        for a in alerts
    ]


@router.patch(
    "/{alert_id}/triage",
    response_model=EarlyWarningAlertItem,
    summary="Update planning triage status for an active early-warning alert",
)
def update_alert_triage(
    alert_id: str,
    req: AlertTriageRequest,
    db: Session = Depends(get_db),
):
    """Update triage status (ACKNOWLEDGED, ESCALATED, RESOLVED) and record an audit event."""
    from fastapi import HTTPException, status
    from backend.app.services.audit_service import record_audit_event

    alert = db.query(EarlyWarningAlert).filter(EarlyWarningAlert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID '{alert_id}' not found.",
        )

    old_status = alert.triage_status
    alert.triage_status = req.triage_status
    if req.triage_note:
        alert.triage_note = req.triage_note

    db.commit()
    db.refresh(alert)

    # Record cryptographic audit trail event
    record_audit_event(
        db=db,
        event_type="ALERT_TRIAGE",
        entity_type="ALERT",
        entity_id=alert.alert_id,
        action_summary=f"Alert {alert.alert_id} triage changed from {old_status} to {req.triage_status}",
        actor=req.actor,
        details={
            "nco_code": alert.nco_code,
            "district_code": alert.district_code,
            "alert_type": alert.alert_type,
            "old_status": old_status,
            "new_status": req.triage_status,
            "triage_note": req.triage_note,
        },
    )

    return EarlyWarningAlertItem(
        alert_id=alert.alert_id,
        nco_code=alert.nco_code,
        canonical_title=alert.canonical_title,
        district_code=alert.district_code,
        reporting_period=alert.reporting_period,
        alert_type=alert.alert_type,
        severity=alert.severity,
        title=alert.title,
        trigger_rule=alert.trigger_rule,
        evidence_summary=alert.evidence_summary,
        review_action_recommended=alert.review_action_recommended,
        observed_demand=alert.observed_demand,
        estimated_supply=alert.estimated_supply,
        absolute_gap=alert.absolute_gap,
        gap_rate_pct=alert.gap_rate_pct,
        threshold_type=alert.threshold_type,
        triage_status=alert.triage_status,
        triage_note=alert.triage_note,
        data_status=alert.data_status,
        limitations=alert.limitations,
        created_at=alert.created_at.isoformat() if alert.created_at else "",
    )


@router.post(
    "/evaluate",
    response_model=AlertEvaluationResponse,
    summary="Re-evaluate alert rules across current labour market observations",
)
def evaluate_alerts(db: Session = Depends(get_db)):
    """Trigger rule-based evaluation and update active alerts in database."""
    return evaluate_and_generate_alerts(db)
