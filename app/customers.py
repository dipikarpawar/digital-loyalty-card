from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from database import customers_collection
import qrcode, os

from auth import get_current_vendor


router = APIRouter()


# Customer register request model
class CustomerRegisterRequest(BaseModel):
    name: str = Field(..., example="Alice Smith")
    email: Optional[EmailStr] = Field(None, example="alice@example.com")
    phone: Optional[str] = Field(None, example="+1234567890")


# Customer update request model
class CustomerUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, example="Alice Smith Updated")
    email: Optional[EmailStr] = Field(None, example="alice_new@example.com")
    phone: Optional[str] = Field(None, example="+9876543210")


# Customer response model
class CustomerResponse(BaseModel):
    customer_id: str
    vendor_id: str
    name: str
    email: Optional[EmailStr]
    phone: Optional[str]
    qr_code: str
    created_at: datetime


# POST /customer/register
@router.post("/register", response_model=CustomerResponse)
async def register_customer(customer: CustomerRegisterRequest, current_vendor: dict = Depends(get_current_vendor)):
    # Prepare customer document
    customer_doc = {
        "vendor_id": current_vendor["_id"],   # FK reference to vendors
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "qr_code": None,   # placeholder until we generate QR
        "created_at": datetime.utcnow()
    }

    # Insert into DB
    result = customers_collection.insert_one(customer_doc)
    customer_id = str(result.inserted_id)

    # Generate QR code (content = customer_id + vendor_id)
    qr_content = f"{customer_id}:{str(current_vendor['_id'])}"
    qr = qrcode.make(qr_content)

    # Save QR Code in local folder
    qr_dir = "qrcodes"
    os.makedirs(qr_dir, exist_ok=True)
    qr_path = os.path.join(qr_dir, f"customer_{customer_id}.png")
    qr.save(qr_path)

    # Update customer with QR code path
    customers_collection.update_one(
        {"_id": ObjectId(customer_id)},
        {"$set": {"qr_code": qr_path}}
    )

    # Return response
    return CustomerResponse(
        customer_id=customer_id,
        vendor_id=str(current_vendor["_id"]),
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        qr_code=qr_path,
        created_at=customer_doc["created_at"]
    )


# GET /customer/all
@router.get("/all", response_model=List[CustomerResponse])
async def list_customers(current_vendor: dict = Depends(get_current_vendor)):
    # Fetch all customers for this vendor
    customers_cursor = customers_collection.find({"vendor_id": current_vendor["_id"]})
    customers = []

    for customer in customers_cursor:
        customers.append(
            CustomerResponse(
                customer_id=str(customer["_id"]),
                vendor_id=str(customer["vendor_id"]),
                name=customer.get("name"),
                email=customer.get("email"),
                phone=customer.get("phone"),
                qr_code=customer.get("qr_code"),
                created_at=customer.get("created_at")
            )
        )
    
    return customers


# GET /customer/134323
@router.get('/{id}')
@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: str = Path(..., description="ID of the customer"), current_vendor: dict = Depends(get_current_vendor)):
    # Convert string ID to ObjectId
    try:
        cust_obj_id = ObjectId(customer_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid customer ID")

    # Fetch customer from DB
    customer = customers_collection.find_one({"_id": cust_obj_id})

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Check vendor ownership
    if customer["vendor_id"] != current_vendor["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this customer")

    # Return customer response
    return CustomerResponse(
        customer_id=str(customer["_id"]),
        vendor_id=str(customer["vendor_id"]),
        name=customer.get("name"),
        email=customer.get("email"),
        phone=customer.get("phone"),
        qr_code=customer.get("qr_code"),
        created_at=customer.get("created_at")
    )


# PUT /customer/134323
@router.put("/{customer_id}")
async def update_customer(customer_id: str, updates: CustomerUpdateRequest, current_vendor: dict = Depends(get_current_vendor)):
    # Convert ID
    try:
        cust_obj_id = ObjectId(customer_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid customer ID")

    # Find customer
    customer = customers_collection.find_one({"_id": cust_obj_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Vendor ownership check
    if customer["vendor_id"] != current_vendor["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to update this customer")

    update_fields = updates.dict(exclude_unset=True)

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Perform update
    customers_collection.update_one(
        {"_id": cust_obj_id},
        {"$set": update_fields}
    )

    # Fetch updated customer
    updated_customer = customers_collection.find_one({"_id": cust_obj_id})

    return CustomerResponse(
        customer_id=str(updated_customer["_id"]),
        vendor_id=str(updated_customer["vendor_id"]),
        name=updated_customer.get("name"),
        email=updated_customer.get("email"),
        phone=updated_customer.get("phone"),
        qr_code=updated_customer.get("qr_code"),
        created_at=updated_customer.get("created_at")
    )


# DELETE /customer/134323
@router.delete("/{customer_id}")
async def delete_customer(customer_id: str, current_vendor: dict = Depends(get_current_vendor)):
    # Convert ID
    try:
        cust_obj_id = ObjectId(customer_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid customer ID")

    # Find customer
    customer = customers_collection.find_one({"_id": cust_obj_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Vendor ownership check
    if customer["vendor_id"] != current_vendor["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this customer")

    # Delete QR code file if exists
    qr_path = customer.get("qr_code")
    if qr_path and os.path.exists(qr_path):
        os.remove(qr_path)

    # Delete customer from DB
    customers_collection.delete_one({"_id": cust_obj_id})

    return {"message": f"Customer {customer_id} deleted successfully"}