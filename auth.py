from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database.database import get_db
from models import User

router = APIRouter()

# ---- Request/Response Schemas ----

class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str  # "CAREGIVER" or "PATIENT"

class LoginRequest(BaseModel):
    username: str
    password: str

# ---- Endpoints ----

@router.post("/auth/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if payload.role not in ["CAREGIVER", "PATIENT"]:
        raise HTTPException(status_code=400, detail="Role must be CAREGIVER or PATIENT")

    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = User(
        username=payload.username,
        password_hash=payload.password,  # stored as plain text for Level 1
        role=payload.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "Registration successful", "user_id": new_user.id, "role": new_user.role}


@router.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()

    if not user or user.password_hash != payload.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {"message": "Login successful", "user_id": user.id, "role": user.role}