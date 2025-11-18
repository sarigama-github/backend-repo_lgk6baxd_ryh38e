import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta

from database import db, create_document, get_documents
from schemas import Appointment, Medicine, Stock, User, HealthRecord, ConsultationLog

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

@app.get("/api/appointments")
async def list_appointments(patient_id: Optional[str] = None, doctor_id: Optional[str] = None, limit: int = 50):
    try:
        filt: Dict[str, Any] = {}
        if patient_id:
            filt["patient_id"] = patient_id
        if doctor_id:
            filt["doctor_id"] = doctor_id
        items = list(db["appointment"].find(filt).sort("created_at", -1).limit(limit))
        for it in items:
            it["_id"] = str(it["_id"])
        return {"items": items}
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

# ------------------ Medicines & Stock ------------------

@app.get("/api/medicines/search")
async def search_medicines(q: Optional[str] = None, limit: int = 20):
    try:
        filter_q = {}
        if q:
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

@app.post("/api/stock", status_code=201)
async def create_stock(stock: Stock):
    try:
        inserted_id = create_document("stock", stock)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stock")
async def list_stock(facility_id: Optional[str] = None, medicine_id: Optional[str] = None, limit: int = 100):
    try:
        filt: Dict[str, Any] = {}
        if facility_id:
            filt["facility_id"] = facility_id
        if medicine_id:
            filt["medicine_id"] = medicine_id
        items = list(db["stock"].find(filt).limit(limit))
        for it in items:
            it["_id"] = str(it["_id"])  # stringify
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
        for s in stocks:
            if "_id" in s:
                s["_id"] = str(s["_id"])  # stringify _id
        return {"stocks": stocks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/stock/{stock_id}")
async def update_stock(stock_id: str, data: Dict[str, Any]):
    try:
        from bson import ObjectId
        result = db["stock"].update_one({"_id": ObjectId(stock_id)}, {"$set": {**data, "updated_at": datetime.utcnow()}})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Stock not found")
        doc = db["stock"].find_one({"_id": ObjectId(stock_id)})
        doc["_id"] = str(doc["_id"])
        return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------ Users & RBAC ------------------

@app.post("/api/users", status_code=201)
async def create_user(user: User):
    try:
        inserted_id = create_document("user", user)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users")
async def list_users(role: Optional[str] = None, limit: int = 100):
    try:
        filt: Dict[str, Any] = {}
        if role:
            filt["role"] = role
        items = list(db["user"].find(filt).limit(limit))
        for it in items:
            it["_id"] = str(it["_id"])  # stringify
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AvailabilityPayload(BaseModel):
    online_status: bool

@app.patch("/api/doctors/{user_id}/availability")
async def update_doctor_availability(user_id: str, payload: AvailabilityPayload):
    try:
        from bson import ObjectId
        result = db["user"].update_one({"_id": ObjectId(user_id)}, {"$set": {"online_status": payload.online_status, "updated_at": datetime.utcnow()}})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        doc = db["user"].find_one({"_id": ObjectId(user_id)})
        doc["_id"] = str(doc["_id"])  # stringify
        return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------ Health Records & Consultations ------------------

@app.post("/api/records", status_code=201)
async def create_health_record(rec: HealthRecord):
    try:
        inserted_id = create_document("healthrecord", rec)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/records")
async def list_health_records(patient_id: Optional[str] = None, doctor_id: Optional[str] = None, limit: int = 50):
    try:
        filt: Dict[str, Any] = {}
        if patient_id:
            filt["patient_id"] = patient_id
        if doctor_id:
            filt["doctor_id"] = doctor_id
        items = list(db["healthrecord"].find(filt).sort("visit_date", -1).limit(limit))
        for it in items:
            it["_id"] = str(it["_id"])  # stringify
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/consultations/logs", status_code=201)
async def create_consultation_log(log: ConsultationLog):
    try:
        inserted_id = create_document("consultationlog", log)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------ Analytics ------------------

@app.get("/api/analytics/summary")
async def analytics_summary(days: int = 7):
    try:
        now = datetime.utcnow()
        since = now - timedelta(days=days)
        # Appointments by day
        pipeline = [
            {"$match": {"created_at": {"$gte": since}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        appt_series = list(db["appointment"].aggregate(pipeline))
        # Users by role
        role_pipeline = [
            {"$group": {"_id": "$role", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        users_by_role = list(db["user"].aggregate(role_pipeline))
        for x in users_by_role:
            x["role"] = x.pop("_id")
        for x in appt_series:
            x["date"] = x.pop("_id")
        return {"appointments": appt_series, "users_by_role": users_by_role}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
