import uvicorn
from fastapi import FastAPI
from routers.public import router as public_router
from routers.balance import router as balance_router

app = FastAPI()

app.include_router(public_router)
app.include_router(balance_router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
