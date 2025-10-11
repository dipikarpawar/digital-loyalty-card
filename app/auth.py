from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
from database import vendors_collection
from datetime import datetime, timedelta
from bson import ObjectId
from dotenv import load_dotenv
from typing import Optional
import jwt
import os


load_dotenv()

router = APIRouter()

security = HTTPBearer()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = os.getenv("JWT_SECRET", "mysecretkey123")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM","HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES",60))


# Vendor registration request model
class VendorRegisterRequest(BaseModel):
    name: str = Field(..., example="John Doe")
    email: EmailStr
    password: str = Field(..., min_length=6)
    business_name: str = Field(..., example="John's Cafe")


# Vendor login request model
class VendorLoginRequest(BaseModel):
    email: EmailStr
    password: str

# Vendor update request model
class VendorUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, example="John Doe")
    business_name: Optional[str] = Field(None, example="John's Cafe")


def get_current_vendor(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        vendor_id = payload.get("vendor_id")
        if not vendor_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Fetch vendor from DB
    vendor = vendors_collection.find_one({"_id": ObjectId(vendor_id)})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    return vendor


@router.post("/register")
async def register_vendor(vendor: VendorRegisterRequest):
    # Check if vendor already exists
    if vendors_collection.find_one({"email": vendor.email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password
    hashed_password = pwd_context.hash(vendor.password)

    # Insert into database
    vendor_doc = {
        "name": vendor.name,
        "email": vendor.email,
        "password_hash": hashed_password,
        "business_name": vendor.business_name,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = vendors_collection.insert_one(vendor_doc)
    vendor_id = str(result.inserted_id)

    return {"message": "Vendor registered successfully", "vendor_id": vendor_id}


@router.post("/login")
async def login_vendor(credentials: VendorLoginRequest):
    vendor = vendors_collection.find_one({"email": credentials.email})
    if not vendor:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    if not pwd_context.verify(credentials.password, vendor["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create JWT token
    payload = {
        "vendor_id": str(vendor["_id"]),
        "email": vendor["email"],
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return {"access_token": token}


@router.get("/me")
async def get_vendor_profile(current_vendor: dict = Depends(get_current_vendor)):
    # Return selected fields only
    return {
        "vendor_id": str(current_vendor["_id"]),
        "name": current_vendor["name"],
        "email": current_vendor["email"],
        "business_name": current_vendor["business_name"],
        "created_at": current_vendor["created_at"],
        "updated_at": current_vendor["updated_at"]
    }


@router.put("/me")
async def update_vendor_profile(update_data: VendorUpdateRequest, current_vendor: dict = Depends(get_current_vendor)):
    update_fields = update_data.dict(exclude_unset=True)
    
    if not update_fields:
        return {"message": "No fields to update"}
    
    update_fields["updated_at"] = datetime.utcnow()
    
    vendors_collection.update_one(
        {"_id": current_vendor["_id"]},
        {"$set": update_fields}
    )
    
    vendor = vendors_collection.find_one({"_id": current_vendor["_id"]})
    
    return {
        "vendor_id": str(vendor["_id"]),
        "name": vendor.get("name"),
        "email": vendor.get("email"),
        "business_name": vendor.get("business_name"),
        "created_at": vendor.get("created_at"),
        "updated_at": vendor.get("updated_at")
    }