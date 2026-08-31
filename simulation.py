from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from database.database import get_db
from models import SimulationState, Task
from tasks import activate_due_tasks

router = APIRouter()

class SetTimeRequest(BaseModel):
    simulation_datetime: str  # "2026-08-31 06:59:00"

class AdvanceRequest(BaseModel):
    minutes: int

@router.get("/simulation/time")
def get_time(db: Session = Depends(get_db)):
    state = db.query(SimulationState).first()
    return {"simulation_time": state.simulation_datetime.strftime("%Y-%m-%d %H:%M:%S")}

@router.put("/simulation/time")
def set_time(payload: SetTimeRequest, db: Session = Depends(get_db)):
    state = db.query(SimulationState).first()
    state.simulation_datetime = datetime.strptime(payload.simulation_datetime, "%Y-%m-%d %H:%M:%S")
    db.commit()
    activate_due_tasks(db)
    return {"simulation_time": state.simulation_datetime.strftime("%Y-%m-%d %H:%M:%S")}

@router.post("/simulation/advance")
def advance_time(payload: AdvanceRequest, db: Session = Depends(get_db)):
    state = db.query(SimulationState).first()
    state.simulation_datetime += timedelta(minutes=payload.minutes)
    db.commit()
    activate_due_tasks(db)
    return {"simulation_time": state.simulation_datetime.strftime("%Y-%m-%d %H:%M:%S")}

@router.post("/simulation/next-task")
def next_task(db: Session = Depends(get_db)):
    state = db.query(SimulationState).first()
    next_pending = db.query(Task).filter(Task.status == "PENDING").order_by(Task.scheduled_time).first()
    if not next_pending:
        raise HTTPException(status_code=404, detail="No pending tasks")

    hour, minute = map(int, next_pending.scheduled_time.split(":"))
    state.simulation_datetime = state.simulation_datetime.replace(hour=hour, minute=minute, second=0)
    db.commit()
    activate_due_tasks(db)
    return {"simulation_time": state.simulation_datetime.strftime("%Y-%m-%d %H:%M:%S")}