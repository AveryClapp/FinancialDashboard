from fastapi import FastAPI
from cb_app import router

app = FastAPI(
    title="My Crypto Dashboard",
    version="0.1.0"
)

# Mount all of your endpoints under the router
app.include_router(router)
