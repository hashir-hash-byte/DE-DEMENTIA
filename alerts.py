from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from models import Task, PatientBaseline, Alert

router = APIRouter()


def check_and_create_alerts(db: Session, patient_id: int):
    """Rule-based alert checks. Called after task/game updates."""
    new_alerts = []

    # Rule 1: 2 or more tasks with confidence below 3 (low activity completion confidence)
    low_conf_tasks = db.query(Task).filter(
        Task.patient_id == patient_id,
        Task.confidence < 3,
        Task.status.in_(["ACTIVE", "IN_PROGRESS", "MISSED"])
    ).count()

    if low_conf_tasks >= 2:
        msg = f"{low_conf_tasks} activities have low completion confidence today"
        exists = db.query(Alert).filter(
            Alert.patient_id == patient_id,
            Alert.alert_type == "LOW_TASK_CONFIDENCE",
            Alert.message == msg
        ).first()
        if not exists:
            new_alerts.append(Alert(patient_id=patient_id, alert_type="LOW_TASK_CONFIDENCE", message=msg))

    # Rule 2: cognitive performance below personal baseline
    baselines = db.query(PatientBaseline).filter(PatientBaseline.patient_id == patient_id).all()
    for b in baselines:
        if b.last_score < b.baseline_score - 15:
            msg = f"{b.round_type.capitalize()} performance below recent personal baseline"
            exists = db.query(Alert).filter(
                Alert.patient_id == patient_id,
                Alert.alert_type == "COGNITIVE_DEVIATION",
                Alert.message == msg
            ).first()
            if not exists:
                new_alerts.append(Alert(patient_id=patient_id, alert_type="COGNITIVE_DEVIATION", message=msg))

    for a in new_alerts:
        db.add(a)
    if new_alerts:
        db.commit()

    return new_alerts


@router.get("/patients/{patient_id}/alerts")
def get_alerts(patient_id: int, db: Session = Depends(get_db)):
    check_and_create_alerts(db, patient_id)  # refresh alerts on each view (simple polling approach)
    alerts = db.query(Alert).filter(Alert.patient_id == patient_id).order_by(Alert.created_at.desc()).all()
    return [
        {
            "alert_type": a.alert_type,
            "message": a.message,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for a in alerts
    ]