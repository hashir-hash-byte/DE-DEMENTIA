from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import random
from database.database import get_db
from models import CognitiveSession, CognitiveScore, PatientBaseline

router = APIRouter()

FRUIT_POOL = ["apple", "banana", "orange", "grape", "watermelon", "strawberry", "mango", "pineapple"]


# ---------- Baseline helper ----------

def update_baseline(db: Session, patient_id: int, round_type: str, new_score: int):
    baseline = db.query(PatientBaseline).filter(
        PatientBaseline.patient_id == patient_id,
        PatientBaseline.round_type == round_type
    ).first()

    if not baseline:
        baseline = PatientBaseline(
            patient_id=patient_id,
            round_type=round_type,
            baseline_score=new_score,
            last_score=new_score
        )
        db.add(baseline)
    else:
        baseline.baseline_score = round(baseline.baseline_score * 0.7 + new_score * 0.3)
        baseline.last_score = new_score

    db.commit()
    return baseline


# ---------- MEMORY round ----------

class GameStartRequest(BaseModel):
    patient_id: int
    round_type: str = "MEMORY"
    difficulty: Optional[int] = 5

class GameResultRequest(BaseModel):
    session_id: int
    selected_fruits: List[str]
    response_time_ms: Optional[int] = None


@router.post("/games/start")
def start_game(payload: GameStartRequest, db: Session = Depends(get_db)):
    if payload.round_type != "MEMORY":
        raise HTTPException(status_code=400, detail="Use /games/attention/start or /games/recognition/start for those rounds")

    num_objects = payload.difficulty or 5
    correct_fruits = random.sample(FRUIT_POOL, min(num_objects, len(FRUIT_POOL)))

    session = CognitiveSession(
        patient_id=payload.patient_id,
        round_type="MEMORY",
        difficulty=num_objects,
        correct_set=",".join(correct_fruits),
        status="IN_PROGRESS"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    display_fruits = list(correct_fruits) + [f for f in FRUIT_POOL if f not in correct_fruits]
    random.shuffle(display_fruits)

    return {
        "session_id": session.id,
        "round_type": "MEMORY",
        "fruits": correct_fruits,
        "all_fruits": display_fruits
    }


@router.post("/games/result")
def submit_result(payload: GameResultRequest, db: Session = Depends(get_db)):
    session = db.query(CognitiveSession).filter(CognitiveSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Game session not found")
    if session.status == "COMPLETED":
        raise HTTPException(status_code=400, detail="Session already submitted")

    correct_fruits = set(session.correct_set.split(","))
    selected = set(payload.selected_fruits)

    correct_answers = len(correct_fruits & selected)
    total_questions = len(correct_fruits)
    score = int((correct_answers / total_questions) * 100) if total_questions > 0 else 0

    result = CognitiveScore(
        session_id=session.id,
        patient_id=session.patient_id,
        round_type=session.round_type,
        correct_answers=correct_answers,
        total_questions=total_questions,
        score=score,
        response_time_ms=payload.response_time_ms
    )
    db.add(result)
    session.status = "COMPLETED"
    update_baseline(db, session.patient_id, session.round_type, score)
    db.commit()

    return {
        "round_type": session.round_type,
        "correct_answers": correct_answers,
        "total_questions": total_questions,
        "score": score
    }


# ---------- ATTENTION round ----------

class AttentionStartRequest(BaseModel):
    patient_id: int
    difficulty: Optional[int] = 8

class AttentionResultRequest(BaseModel):
    session_id: int
    correct_taps: int
    false_taps: int
    missed_targets: int
    response_time_ms: Optional[int] = None


@router.post("/games/attention/start")
def start_attention_game(payload: AttentionStartRequest, db: Session = Depends(get_db)):
    sequence_length = payload.difficulty or 8
    target_fruit = random.choice(FRUIT_POOL)

    num_targets = max(2, sequence_length // 3)
    sequence = [target_fruit] * num_targets
    distractors = [f for f in FRUIT_POOL if f != target_fruit]
    while len(sequence) < sequence_length:
        sequence.append(random.choice(distractors))
    random.shuffle(sequence)

    session = CognitiveSession(
        patient_id=payload.patient_id,
        round_type="ATTENTION",
        difficulty=sequence_length,
        correct_set=target_fruit,
        status="IN_PROGRESS"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "round_type": "ATTENTION",
        "target_fruit": target_fruit,
        "sequence": sequence
    }


@router.post("/games/attention/result")
def submit_attention_result(payload: AttentionResultRequest, db: Session = Depends(get_db)):
    session = db.query(CognitiveSession).filter(CognitiveSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Game session not found")
    if session.round_type != "ATTENTION":
        raise HTTPException(status_code=400, detail="Session is not an attention round")
    if session.status == "COMPLETED":
        raise HTTPException(status_code=400, detail="Session already submitted")

    total_targets = payload.correct_taps + payload.missed_targets
    score = int((payload.correct_taps / total_targets) * 100) if total_targets > 0 else 0

    result = CognitiveScore(
        session_id=session.id,
        patient_id=session.patient_id,
        round_type="ATTENTION",
        correct_answers=payload.correct_taps,
        total_questions=total_targets,
        score=score,
        response_time_ms=payload.response_time_ms
    )
    db.add(result)
    session.status = "COMPLETED"
    update_baseline(db, session.patient_id, session.round_type, score)
    db.commit()

    return {
        "round_type": "ATTENTION",
        "correct_taps": payload.correct_taps,
        "false_taps": payload.false_taps,
        "missed_targets": payload.missed_targets,
        "score": score
    }


# ---------- RECOGNITION round ----------

class RecognitionStartRequest(BaseModel):
    patient_id: int
    difficulty: Optional[int] = 5

class RecognitionResultRequest(BaseModel):
    session_id: int
    selected_fruits: List[str]
    response_time_ms: Optional[int] = None


@router.post("/games/recognition/start")
def start_recognition_game(payload: RecognitionStartRequest, db: Session = Depends(get_db)):
    num_seen = payload.difficulty or 5
    seen_fruits = random.sample(FRUIT_POOL, min(num_seen, len(FRUIT_POOL)))

    session = CognitiveSession(
        patient_id=payload.patient_id,
        round_type="RECOGNITION",
        difficulty=num_seen,
        correct_set=",".join(seen_fruits),
        status="IN_PROGRESS"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    new_fruits = [f for f in FRUIT_POOL if f not in seen_fruits]
    mixed_set = seen_fruits + new_fruits
    random.shuffle(mixed_set)

    return {
        "session_id": session.id,
        "round_type": "RECOGNITION",
        "seen_fruits": seen_fruits,
        "mixed_set": mixed_set
    }


@router.post("/games/recognition/result")
def submit_recognition_result(payload: RecognitionResultRequest, db: Session = Depends(get_db)):
    session = db.query(CognitiveSession).filter(CognitiveSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Game session not found")
    if session.round_type != "RECOGNITION":
        raise HTTPException(status_code=400, detail="Session is not a recognition round")
    if session.status == "COMPLETED":
        raise HTTPException(status_code=400, detail="Session already submitted")

    seen_fruits = set(session.correct_set.split(","))
    selected = set(payload.selected_fruits)

    correct_answers = len(seen_fruits & selected)
    total_questions = len(seen_fruits)
    score = int((correct_answers / total_questions) * 100) if total_questions > 0 else 0

    result = CognitiveScore(
        session_id=session.id,
        patient_id=session.patient_id,
        round_type="RECOGNITION",
        correct_answers=correct_answers,
        total_questions=total_questions,
        score=score,
        response_time_ms=payload.response_time_ms
    )
    db.add(result)
    session.status = "COMPLETED"
    update_baseline(db, session.patient_id, session.round_type, score)
    db.commit()

    return {
        "round_type": "RECOGNITION",
        "correct_answers": correct_answers,
        "total_questions": total_questions,
        "score": score
    }


# ---------- History, profile, recommendation ----------

@router.get("/patients/{patient_id}/games")
def get_game_history(patient_id: int, db: Session = Depends(get_db)):
    results = db.query(CognitiveScore).filter(CognitiveScore.patient_id == patient_id).all()
    return [
        {
            "round_type": r.round_type,
            "score": r.score,
            "correct_answers": r.correct_answers,
            "total_questions": r.total_questions,
            "response_time_ms": r.response_time_ms,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for r in results
    ]


@router.get("/patients/{patient_id}/cognitive/profile")
def cognitive_profile(patient_id: int, db: Session = Depends(get_db)):
    baselines = db.query(PatientBaseline).filter(PatientBaseline.patient_id == patient_id).all()

    profile = {"memory": 0, "attention": 0, "recognition": 0}
    deviations = []

    for b in baselines:
        key = b.round_type.lower()
        if key in profile:
            profile[key] = b.baseline_score
            if b.last_score < b.baseline_score - 15:
                deviations.append(f"{b.round_type.capitalize()} performance below recent personal baseline")

    overall = round(sum(profile.values()) / 3) if any(profile.values()) else 0

    return {**profile, "overall": overall, "observations": deviations}


@router.get("/patients/{patient_id}/cognitive/recommendation")
def cognitive_recommendation(patient_id: int, db: Session = Depends(get_db)):
    baselines = db.query(PatientBaseline).filter(PatientBaseline.patient_id == patient_id).all()

    if not baselines:
        return {"next_round": "MEMORY", "difficulty": 5, "reason": "No prior sessions - starting baseline"}

    weakest = min(baselines, key=lambda b: b.baseline_score)

    if weakest.baseline_score >= 85:
        difficulty = 9
    elif weakest.baseline_score >= 40:
        difficulty = 7
    else:
        difficulty = 5

    return {
        "next_round": weakest.round_type,
        "difficulty": difficulty,
        "reason": f"{weakest.round_type.capitalize()} is the weakest recent dimension"
    }