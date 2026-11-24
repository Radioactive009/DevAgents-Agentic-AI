"""
IronForge Gym & Training Web Application.
"""
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="IronForge Gym API")

class BookingRequest(BaseModel):
    trainer_name: str
    client_name: str
    phone: str

TRAINERS = [
    {"name": "Marcus Vance", "specialty": "Olympic Strength"},
    {"name": "Elena Rostova", "specialty": "Boxing & HIIT"},
    {"name": "David Chen", "specialty": "Mobility & Rehab"},
]
BOOKINGS = []

@app.get("/api/trainers")
def get_trainers():
    return TRAINERS

@app.post("/api/book")
def book_trainer(req: BookingRequest):
    if not req.client_name.strip():
        return {"status": "error", "message": "Client name required"}
    BOOKINGS.append(req.model_dump())
    return {"status": "confirmed", "trainer": req.trainer_name}
