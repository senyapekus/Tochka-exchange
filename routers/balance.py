from fastapi import APIRouter, HTTPException, Query, Header
from models import Body_deposit_api_v1_balance_deposit_post, Body_withdraw_api_v1_balance_withdraw_post, Ok
from temp_database import balances_db, users_db
from typing import Dict, Optional

router = APIRouter(prefix="/api/v1/balance", tags=["balance"])

# TODO: Автоматом прокидывать заголовок Authorization при вызове методов

def get_authorization_header(authorization: Optional[str]) -> str:
    if authorization is None:
        raise HTTPException(status_code=401, detail="Authorization is required")
    
    if not authorization.startswith("key-"):
        raise HTTPException(status_code=400, detail="Invalid API key format. Expected 'key-<uuid>'")
    
    return f"TOKEN {authorization}"

@router.get("/", response_model=Dict[str, int])
def get_balances(authorization: Optional[str] = Query(None)):
    auth_header = get_authorization_header(authorization)
    
    api_key = auth_header.replace("TOKEN ", "")
    user_id = next((user.id for user in users_db.values() if user.api_key == api_key), None)

    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")
    
    return balances_db.get(user_id, {})
    

@router.post("/deposit", response_model=Ok)
def deposit(request: Body_deposit_api_v1_balance_deposit_post, authorization: Optional[str] = Query(None)):
    auth_header = get_authorization_header(authorization)
    
    api_key = auth_header.replace("TOKEN ", "")
    user_id = next((user.id for user in users_db.values() if user.api_key == api_key), None)

    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_id not in balances_db:
        balances_db[user_id] = {}

    balances_db[user_id][request.ticker] = balances_db[user_id].get(request.ticker, 0) + request.amount
    
    return Ok()

@router.post("/withdraw", response_model=Ok)
def withdraw(request: Body_withdraw_api_v1_balance_withdraw_post, authorization: Optional[str] = Query(None)):
    auth_header = get_authorization_header(authorization)
    
    api_key = auth_header.replace("TOKEN ", "")
    user_id = next((user.id for user in users_db.values() if user.api_key == api_key), None)

    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_id not in balances_db or balances_db[user_id].get(request.ticker, 0) < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    balances_db[user_id][request.ticker] -= request.amount
    
    return Ok()
