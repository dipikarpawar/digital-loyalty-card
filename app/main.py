from fastapi import FastAPI
from auth import router as auth_router
from customers import router as customer_router
from loyalty_cards import router as loyalty_card_router

app = FastAPI(title="Digital Loyalty Card API")

# Include auth routes
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(customer_router, prefix="/customer", tags=["Customer"])
app.include_router(loyalty_card_router, prefix="/loyaltyCard", tags=["Loyalty_card"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
