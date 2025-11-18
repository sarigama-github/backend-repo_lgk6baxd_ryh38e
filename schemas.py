"""
Database Schemas for Rural Healthcare Coordination Platform

Each Pydantic model represents a collection in MongoDB.
Collection name is the lowercase of the class name.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import datetime

# RBAC roles
Role = Literal["patient", "doctor", "hospital", "government", "admin"]

class User(BaseModel):
    """
    Users collection schema
    Collection: "user"
    """
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    phone: str = Field(..., description="Phone number")
    role: Role = Field(..., description="Role-based access control role")
    language: Optional[str] = Field("en", description="Preferred locale (en, te, hi, ta, ur)")
    # Patient-specific
    address: Optional[str] = Field(None, description="Address")
    # Doctor-specific
    qualifications: Optional[List[str]] = Field(default=None, description="List of degrees/certifications")
    registration_number: Optional[str] = Field(default=None, description="Medical council registration number")
    specialization: Optional[str] = Field(default=None, description="Primary specialization")
    years_experience: Optional[int] = Field(default=None, ge=0, description="Years of experience")
    online_status: Optional[bool] = Field(default=False, description="Doctor available for online consultation")
    is_active: bool = Field(True, description="Account active status")

class Appointment(BaseModel):
    """
    Appointments collection schema
    Collection: "appointment"
    """
    patient_id: str = Field(..., description="Reference to user (patient)")
    doctor_id: str = Field(..., description="Reference to user (doctor)")
    type: Literal["telemedicine", "physical"] = Field(..., description="Mode of appointment")
    scheduled_time: datetime = Field(..., description="Scheduled datetime")
    symptoms: Optional[str] = Field(None, description="Brief symptoms")
    status: Literal["requested", "confirmed", "completed", "cancelled"] = Field("requested")
    offline_temp_id: Optional[str] = Field(None, description="Temporary ID used in offline queue")

class Medicine(BaseModel):
    """
    Medicines master catalog
    Collection: "medicine"
    """
    name: str
    generic_name: Optional[str] = None
    manufacturer: Optional[str] = None
    dosage_form: Optional[str] = None  # e.g., tablet, syrup
    strength: Optional[str] = None     # e.g., 500mg
    interactions: Optional[List[str]] = Field(default=None, description="Known interaction codes/notes")

class Stock(BaseModel):
    """
    Inventory for facilities
    Collection: "stock"
    """
    facility_id: str = Field(..., description="Hospital/PHC/Clinic identifier")
    medicine_id: str = Field(..., description="Reference to medicine")
    quantity: int = Field(..., ge=0)
    threshold: int = Field(0, ge=0, description="Low-stock threshold")
    location: Optional[str] = Field(None, description="Rack/room info")

class HealthRecord(BaseModel):
    """
    Patient health records
    Collection: "healthrecord"
    """
    patient_id: str
    doctor_id: Optional[str] = None
    visit_date: datetime
    vitals: Optional[dict] = Field(default=None, description="BP, HR, Temp, SpO2, etc.")
    diagnosis: Optional[str] = None
    prescription: Optional[List[dict]] = Field(default=None, description="List of prescribed medicines")
    attachments: Optional[List[str]] = Field(default=None, description="URLs to lab reports, images")
    privacy_level: Literal["patient", "doctor", "facility", "government"] = Field("patient")

class ConsultationLog(BaseModel):
    """
    Teleconsultation audit logs
    Collection: "consultationlog"
    """
    appointment_id: str
    doctor_id: str
    patient_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    notes: Optional[str] = None
    warnings: Optional[List[str]] = Field(default=None, description="Drug interaction or safety warnings")
