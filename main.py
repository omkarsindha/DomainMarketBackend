from fastapi import FastAPI
from routes.domain_routes import router as domain_router
from routes.auth_routes import router as auth_router  # Import auth routes
from database.connection import engine, Base
app = FastAPI()

Base.metadata.create_all(bind=engine)

# Include authentication routes
app.include_router(auth_router, prefix="/auth", tags=["auth"])

# Include domain routes
app.include_router(domain_router, prefix="/domains", tags=["domains"])

@app.get("/")
async def root():
    return {"message": "Hello World"}
