from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import random
from database.database import get_db
from models import GameResult

router = APIRouter()

FRUIT_POOL = ["apple", "banana", "orange", "grape", "watermelon", "strawberry", "mango", "pineapple"]

# In-memory session store for Level 1 (simple, no extra table needed)
active_sessions = {}
session_counter = {"value": 0}

class GameStartRequest(BaseModel):
    patient_id: int
    game_type: str = "MEMORY"

class GameResultRequest(BaseModel):
    session_id: int
    selected_fruits: List[str]

@router.post("/games/start")
def start_game(payload: GameStartRequest):
    session_counter["value"] += 1
    session_id = session_counter["value"]

    correct_fruits = random.sample(FRUIT_POOL, 5)
    active_sessions[session_id] = {
        "patient_id": payload.patient_id,
        "correct_fruits": correct_fruits
    }

    # Show all 8 so frontend can present the "which did you see" step
    display_fruits = correct_fruits + [f for f in FRUIT_POOL if f not in correct_fruits]
    random.shuffle(display_fruits)

    return {
        "session_id": session_id,
        "game_type": "MEMORY",
        "fruits": correct_fruits,
        "all_fruits": display_fruits
    }


@router.post("/games/result")
def submit_result(payload: GameResultRequest, db: Session = Depends(get_db)):
    session = active_sessions.get(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Game session not found")

    correct_fruits = set(session["correct_fruits"])
    selected = set(payload.selected_fruits)

    correct_answers = len(correct_fruits & selected)
    total_questions = len(correct_fruits)
    score = int((correct_answers / total_questions) * 100)

    result = GameResult(
        patient_id=session["patient_id"],
        game_type="MEMORY",
        score=score,
        correct_answers=correct_answers,
        total_questions=total_questions
    )
    db.add(result)
    db.commit()

    del active_sessions[payload.session_id]

    return {
        "correct_answers": correct_answers,
        "total_questions": total_questions,
        "score": score,
        "memory_score": score,
        "recognition_score": score,
        "attention_score": score
    }


@router.get("/patients/{patient_id}/games")
def get_game_history(patient_id: int, db: Session = Depends(get_db)):
    results = db.query(GameResult).filter(GameResult.patient_id == patient_id).all()
    return [
        {
            "game_type": r.game_type,
            "score": r.score,
            "correct_answers": r.correct_answers,
            "total_questions": r.total_questions,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for r in results
    ]


@router.get("/patients/{patient_id}/cognitive-report")
def cognitive_report(patient_id: int, db: Session = Depends(get_db)):
    results = db.query(GameResult).filter(GameResult.patient_id == patient_id).all()
    if not results:
        return {"memory": 0, "recognition": 0, "attention": 0, "overall": 0}

    avg_score = sum(r.score for r in results) / len(results)
    return {
        "memory": round(avg_score),
        "recognition": round(avg_score),
        "attention": round(avg_score),
        "overall": round(avg_score)
    }