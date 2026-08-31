from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database.database import get_db
# tasks.py — additions

from models import Task, TaskEvent  # TaskEvent added to existing import

def activate_due_tasks(db):
    from models import SimulationState
    state = db.query(SimulationState).first()
    sim_time = state.simulation_datetime.strftime("%H:%M")

    due_tasks = db.query(Task).filter(
        Task.status == "PENDING",
        Task.scheduled_time <= sim_time
    ).all()

    for task in due_tasks:
        task.status = "ACTIVE"
        task.confidence = min(10, task.confidence + 5)
        db.add(TaskEvent(task_id=task.id, event_type="TASK_ACTIVATED", points=5))

    db.commit()

router = APIRouter()

class TaskCreateRequest(BaseModel):
    patient_id: int
    title: str
    scheduled_time: str  # "HH:MM"
    duration: int
    category: Optional[str] = None

@router.post("/tasks")
def create_task(payload: TaskCreateRequest, db: Session = Depends(get_db)):
    new_task = Task(
        patient_id=payload.patient_id,
        title=payload.title,
        scheduled_time=payload.scheduled_time,
        duration=payload.duration,
        category=payload.category,
        status="PENDING",
        confidence=0
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return {
        "id": new_task.id,
        "patient_id": new_task.patient_id,
        "title": new_task.title,
        "scheduled_time": new_task.scheduled_time,
        "duration": new_task.duration,
        "category": new_task.category,
        "status": new_task.status,
        "confidence": new_task.confidence
    }


@router.get("/patients/{patient_id}/tasks")
def get_patient_tasks(patient_id: int, db: Session = Depends(get_db)):
    tasks = db.query(Task).filter(Task.patient_id == patient_id).all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "scheduled_time": t.scheduled_time,
            "status": t.status,
            "confidence": t.confidence
        }
        for t in tasks
    ]


@router.get("/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "id": task.id,
        "patient_id": task.patient_id,
        "title": task.title,
        "scheduled_time": task.scheduled_time,
        "duration": task.duration,
        "category": task.category,
        "status": task.status,
        "confidence": task.confidence
    }
class AnswerRequest(BaseModel):
    question: str
    answer: str

class ConfirmRequest(BaseModel):
    confirmed: bool

@router.post("/tasks/{task_id}/open")
def open_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.confidence = min(10, task.confidence + 1)
    task.status = "IN_PROGRESS"
    db.add(TaskEvent(task_id=task.id, event_type="PATIENT_OPENED", points=1))
    db.commit()

    return {"task_id": task.id, "confidence": task.confidence, "status": task.status}


@router.post("/tasks/{task_id}/answer")
def answer_task(task_id: int, payload: AnswerRequest, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Level 1: any non-empty answer to "location" counts as correct (demo simplification)
    if payload.question == "location" and payload.answer:
        task.confidence = min(10, task.confidence + 2)
        db.add(TaskEvent(task_id=task.id, event_type="LOCATION_CONFIRMED", points=2))
        db.commit()

    return {"task_id": task.id, "confidence": task.confidence, "status": task.status}


@router.post("/tasks/{task_id}/confirm")
def confirm_task(task_id: int, payload: ConfirmRequest, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if payload.confirmed:
        task.confidence = min(10, task.confidence + 2)
        task.status = "COMPLETED"
        db.add(TaskEvent(task_id=task.id, event_type="PATIENT_CONFIRMED", points=2))
        db.commit()
        return {"task_id": task.id, "confidence": task.confidence, "status": task.status}

    db.commit()
    return {"task_id": task.id, "confidence": task.confidence, "status": task.status, "message": "Not confirmed yet"}