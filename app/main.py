import uvicorn
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from app.routers.public import router as public_router
from app.routers.balance import router as balance_router
from app.routers.balance import admin_balance_router as admin_balance_router
from app.routers.order import router as order_router
from app.routers.admin import router as admin_router
from app.routers.user import router as user_router

app = FastAPI(redirect_slashes=False)

app.include_router(public_router)
app.include_router(balance_router)
app.include_router(order_router)
app.include_router(admin_router)
app.include_router(admin_balance_router)
app.include_router(user_router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Tochka-exchange API",
        version="1.0.0",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Enter your API key in the format: `TOKEN <api_key>`",
        }
    }
    for path, methods in openapi_schema["paths"].items():
        if path.startswith("/api/v1/balance") or path.startswith("/api/v1/order") or path.startswith("/api/v1/admin"):
            for method in methods.values():
                method["security"] = [{"ApiKeyAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
