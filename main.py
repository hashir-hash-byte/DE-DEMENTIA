from fastapi import FastAPI
from auth import router as auth_router
from patients import router as patients_router
from tasks import router as tasks_router
from simulation import router as simulation_router
from games import router as games_router
from alerts import router as alerts_router

app = FastAPI(title="SIH26003 - Dementia Care Backend")

app.include_router(auth_router)
app.include_router(patients_router)
app.include_router(tasks_router)
app.include_router(simulation_router)
app.include_router(games_router)
app.include_router(alerts_router)

@app.get("/")
def root():
    return {"message": "Backend is running"}