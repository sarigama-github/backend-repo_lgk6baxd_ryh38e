import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

from database import db, create_document, get_documents
from schemas import Appointment, Medicine, Stock

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Rural Health Platform Backend Running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

# ------------------ Core API ------------------

class AppointmentSyncPayload(BaseModel):
    appointments: List[Appointment]

@app.post("/api/appointments", status_code=201)
async def create_appointment(appt: Appointment):
    try:
        inserted_id = create_document("appointment", appt)
        return {"id": inserted_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/appointments/bulk_sync")
async def bulk_sync(payload: AppointmentSyncPayload):
    inserted = []
    errors = []
    for a in payload.appointments:
        try:
            inserted_id = create_document("appointment", a)
            inserted.append({"offline_temp_id": a.offline_temp_id, "id": inserted_id})
        except Exception as e:
            errors.append({"offline_temp_id": a.offline_temp_id, "error": str(e)})
    return {"inserted": inserted, "errors": errors}

@app.get("/api/medicines/search")
async def search_medicines(q: Optional[str] = None, limit: int = 20):
    try:
        filter_q = {}
        if q:
            # Basic case-insensitive regex search on name or generic_name
            filter_q = {"$or": [
                {"name": {"$regex": q, "$options": "i"}},
                {"generic_name": {"$regex": q, "$options": "i"}}
            ]}
        items = list(db["medicine"].find(filter_q).limit(limit))
        for it in items:
            it["_id"] = str(it["_id"])  # stringify ObjectId
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stock/check")
async def check_stock(medicine_id: Optional[str] = None, facility_id: Optional[str] = None):
    try:
        filt = {}
        if medicine_id:
            filt["medicine_id"] = medicine_id
        if facility_id:
            filt["facility_id"] = facility_id
        stocks = get_documents("stock", filt)
        # stringify _id
        for s in stocks:
            if "_id" in s:
                s["_id"] = str(s["_id"])
        return {"stocks": stocks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
