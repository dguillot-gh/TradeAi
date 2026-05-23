import os
from fastapi import APIRouter, HTTPException
from models.schemas import LoginRequest, LoginResponse
from services.robinhood import login_to_robinhood

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    username = request.username or os.getenv("ROBINHOOD_USERNAME")
    password = request.password or os.getenv("ROBINHOOD_PASSWORD")
    
    if not username or not password:
        return LoginResponse(success=False, message="Username or password missing.")
        
    result = login_to_robinhood(username, password, request.mfa_code)
    
    if not result["success"]:
        # We assume if it failed and no mfa was provided, it might need MFA
        return LoginResponse(
            success=False, 
            message=result["message"], 
            requires_mfa=result.get("requires_mfa", False)
        )
        
    return LoginResponse(success=True, message="Successfully authenticated with Robinhood")
