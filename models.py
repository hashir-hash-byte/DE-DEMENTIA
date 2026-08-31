from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, Text
from sqlalchemy.sql import func
from database.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(10), nullable=False)  # CAREGIVER or PATIENT
    created_at = Column(TIMESTAMP, server_default=func.now())


class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    caregiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    title = Column(String(100), nullable=False)
    scheduled_time = Column(String(5), nullable=False)  # "HH:MM"
    duration = Column(Integer, nullable=False)
    category = Column(String(50))
    status = Column(String(20), nullable=False, default="PENDING")
    confidence = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())


class TaskEvent(Base):
    __tablename__ = "task_events"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    points = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class GameResult(Base):
    __tablename__ = "game_results"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    game_type = Column(String(20), nullable=False, default="MEMORY")
    score = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class SimulationState(Base):
    __tablename__ = "simulation_state"
    id = Column(Integer, primary_key=True)
    simulation_datetime = Column(TIMESTAMP, nullable=False)

class CognitiveSession(Base):
    __tablename__ = "cognitive_sessions"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    round_type = Column(String(20), nullable=False)
    difficulty = Column(Integer, nullable=False, default=5)
    correct_set = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="IN_PROGRESS")
    created_at = Column(TIMESTAMP, server_default=func.now())


class CognitiveScore(Base):
    __tablename__ = "cognitive_scores"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("cognitive_sessions.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    round_type = Column(String(20), nullable=False)
    correct_answers = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    score = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

class PatientBaseline(Base):
    __tablename__ = "patient_baselines"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    round_type = Column(String(20), nullable=False)
    baseline_score = Column(Integer, nullable=False)  # kept simple as int, rounded
    last_score = Column(Integer, nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    alert_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())