from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database.database import get_db
from models import Patient

router = APIRouter()

class PatientCreateRequest(BaseModel):
    name: str
    age: int
    caregiver_id: int

@router.post("/patients")
def create_patient(payload: PatientCreateRequest, db: Session = Depends(get_db)):
    new_patient = Patient(
        name=payload.name,
        age=payload.age,
        caregiver_id=payload.caregiver_id
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    return {
        "id": new_patient.id,
        "name": new_patient.name,
        "age": new_patient.age,
        "caregiver_id": new_patient.caregiver_id
    }


@router.get("/patients")
def get_all_patients(db: Session = Depends(get_db)):
    patients = db.query(Patient).all()
    return [
        {"id": p.id, "name": p.name, "age": p.age, "caregiver_id": p.caregiver_id}
        for p in patients
    ]


@router.get("/patients/{patient_id}")
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "id": patient.id,
        "name": patient.name,
        "age": patient.age,
        "caregiver_id": patient.caregiver_id
    }
from models import Task, TaskEvent

@router.get("/patients/{patient_id}/report")
def get_report(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    tasks = db.query(Task).filter(Task.patient_id == patient_id).all()

    task_list = []
    for t in tasks:
        events = db.query(TaskEvent).filter(TaskEvent.task_id == t.id).all()
        task_list.append({
            "id": t.id,
            "title": t.title,
            "status": t.status,
            "confidence": t.confidence,
            "events": [{"event_type": e.event_type, "points": e.points} for e in events]
        })

    summary = {
        "completed": sum(1 for t in tasks if t.status == "COMPLETED"),
        "active": sum(1 for t in tasks if t.status == "ACTIVE"),
        "pending": sum(1 for t in tasks if t.status == "PENDING"),
        "missed": sum(1 for t in tasks if t.status == "MISSED"),
    }

    return {
        "patient": {"id": patient.id, "name": patient.name},
        "tasks": task_list,
        "summary": summary
    }


@router.get("/patients/{patient_id}/dashboard")
def get_dashboard(patient_id: int, db: Session = Depends(get_db)):
    from models import SimulationState
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    state = db.query(SimulationState).first()
    tasks = db.query(Task).filter(Task.patient_id == patient_id).all()

    active_task = next((t for t in tasks if t.status in ["ACTIVE", "IN_PROGRESS"]), None)

    return {
        "patient": {"id": patient.id, "name": patient.name},
        "simulation_time": state.simulation_datetime.strftime("%H:%M"),
        "active_task": {
            "id": active_task.id, "title": active_task.title,
            "status": active_task.status, "confidence": active_task.confidence
        } if active_task else None,
        "tasks": [
            {"id": t.id, "title": t.title, "status": t.status, "confidence": t.confidence}
            for t in tasks
        ]
    }