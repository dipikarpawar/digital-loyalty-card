from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from bson import ObjectId
from database import loyalty_cards_collection, customers_collection
from auth import get_current_vendor


router = APIRouter()


class LoyaltyCardCreateRequest(BaseModel):
    customer_id: str = Field(..., example="6510d3f5b12345abcd67890f")
    reward_threshold: int = Field(..., example=10)


class LoyaltyCardResponse(BaseModel):
    card_id: str
    vendor_id: str
    customer_id: str
    punches: int
    reward_threshold: int
    reward_claimed: bool
    created_at: datetime
    updated_at: datetime


@router.post('/')
async def create_loyalty_card(card: LoyaltyCardCreateRequest, current_vendor: dict = Depends(get_current_vendor)):
    try:
        cust_obj_id = ObjectId(card.customer_id)
    except:
        raise HTTPException(status_code=400, description="Invalid customer ID format")
    
    customer = customers_collection.find_one({"_id":cust_obj_id})
    if not customer:
        raise HTTPException(status_code=404, description = "Customer not found")
    
    exist_card = loyalty_cards_collection.find_one({"customer_id":cust_obj_id, "vendor_id":current_vendor["_id"]})
    if exist_card is not None:
        raise HTTPException(status_code=400, description="Card already exist")
    
    new_card = {
        "vendor_id": current_vendor["_id"],
        "customer_id": cust_obj_id,
        "punches": 0,
        "reward_threshold": card.reward_threshold,
        "reward_claimed": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = loyalty_cards_collection.insert_one(new_card)
    new_card["_id"] = result.inserted_id

    return LoyaltyCardResponse(
        card_id=str(new_card["_id"]),
        vendor_id=str(new_card["vendor_id"]),
        customer_id=str(new_card["customer_id"]),
        punches=new_card["punches"],
        reward_threshold=new_card["reward_threshold"],
        reward_claimed=new_card["reward_claimed"],
        created_at=new_card["created_at"],
        updated_at=new_card["updated_at"]
    )


@router.get("/{card_id}")
async def get_loyalty_card(card_id: str, current_vendor: dict = Depends(get_current_vendor)):
    # Convert ID
    try:
        card_obj_id = ObjectId(card_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid loyalty card ID format")

    # Find loyalty card
    card = loyalty_cards_collection.find_one({"_id": card_obj_id})
    if not card:
        raise HTTPException(status_code=404, detail="Loyalty card not found")

    # Vendor ownership check
    if card["vendor_id"] != current_vendor["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this loyalty card")

    return LoyaltyCardResponse(
        card_id=str(card["_id"]),
        vendor_id=str(card["vendor_id"]),
        customer_id=str(card["customer_id"]),
        punches=card["punches"],
        reward_threshold=card["reward_threshold"],
        reward_claimed=card["reward_claimed"],
        created_at=card["created_at"],
        updated_at=card["updated_at"]
    )


@router.get("/")
async def list_loyalty_cards(vendor_id: Optional[str] = Query(None, description="Filter by vendor_id"), current_vendor: dict = Depends(get_current_vendor)):
    # If vendor_id provided, validate and enforce ownership
    if vendor_id:
        try:
            vendor_obj_id = ObjectId(vendor_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid vendor_id format")

        if vendor_obj_id != current_vendor["_id"]:
            raise HTTPException(status_code=403, detail="Not authorized to view this vendor's cards")

        query = {"vendor_id": vendor_obj_id}
    else:
        # Default to current vendor
        query = {"vendor_id": current_vendor["_id"]}

    # Fetch cards
    cards_cursor = loyalty_cards_collection.find(query).sort("created_at", -1)
    
    cards = [
        LoyaltyCardResponse(
            card_id=str(card["_id"]),
            vendor_id=str(card["vendor_id"]),
            customer_id=str(card["customer_id"]),
            punches=card["punches"],
            reward_threshold=card["reward_threshold"],
            reward_claimed=card["reward_claimed"],
            created_at=card["created_at"],
            updated_at=card["updated_at"]
        )
        for card in cards_cursor
    ]

    return cards


@router.put("/{card_id}/punch")
async def punch_loyalty_card(card_id: str = Path(..., description="Loyalty card ID"), current_vendor: dict = Depends(get_current_vendor)):
    # Validate card_id
    try:
        card_obj_id = ObjectId(card_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid loyalty card ID format")

    # Find card
    card = loyalty_cards_collection.find_one({"_id": card_obj_id})
    if not card:
        raise HTTPException(status_code=404, detail="Loyalty card not found")

    # Ownership check
    if card["vendor_id"] != current_vendor["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to punch this card")

    # If reward already claimed, block further punches
    if card.get("reward_claimed", False):
        raise HTTPException(status_code=400, detail="Reward already claimed, cannot add more punches")

    # Increment punches
    new_punches = card["punches"] + 1

    # Update document
    loyalty_cards_collection.update_one(
        {"_id": card_obj_id},
        {
            "$set": {
                "punches": new_punches,
                "updated_at": datetime.utcnow()
            }
        }
    )

    # Fetch updated card
    updated_card = loyalty_cards_collection.find_one({"_id": card_obj_id})

    return LoyaltyCardResponse(
        card_id=str(updated_card["_id"]),
        vendor_id=str(updated_card["vendor_id"]),
        customer_id=str(updated_card["customer_id"]),
        punches=updated_card["punches"],
        reward_threshold=updated_card["reward_threshold"],
        reward_claimed=updated_card["reward_claimed"],
        created_at=updated_card["created_at"],
        updated_at=updated_card["updated_at"]
    )


@router.put("/{card_id}/redeem", response_model=LoyaltyCardResponse)
async def redeem_loyalty_card(
    card_id: str,
    current_vendor: dict = Depends(get_current_vendor)
):
    # Validate card_id
    try:
        card_obj_id = ObjectId(card_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid loyalty card ID format")

    # Find loyalty card
    card = loyalty_cards_collection.find_one({"_id": card_obj_id})
    if not card:
        raise HTTPException(status_code=404, detail="Loyalty card not found")

    # Vendor ownership check
    if card["vendor_id"] != current_vendor["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to redeem this card")

    # Already redeemed check
    if card.get("reward_claimed", False):
        raise HTTPException(status_code=400, detail="Reward already claimed for this card")

    # Check punches threshold
    if card["punches"] < card["reward_threshold"]:
        raise HTTPException(status_code=400, detail="Not enough punches to redeem reward")

    # Update reward status
    loyalty_cards_collection.update_one(
        {"_id": card_obj_id},
        {"$set": {"reward_claimed": True, "updated_at": datetime.utcnow()}}
    )

    # Fetch updated card
    updated_card = loyalty_cards_collection.find_one({"_id": card_obj_id})

    return LoyaltyCardResponse(
        card_id=str(updated_card["_id"]),
        vendor_id=str(updated_card["vendor_id"]),
        customer_id=str(updated_card["customer_id"]),
        punches=updated_card["punches"],
        reward_threshold=updated_card["reward_threshold"],
        reward_claimed=updated_card["reward_claimed"],
        created_at=updated_card["created_at"],
        updated_at=updated_card["updated_at"]
    )