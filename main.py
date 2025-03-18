from fastapi import FastAPI
from routes.domain_routes import router as domain_router
from routes.auth_routes import router as auth_router  # Import auth routes
from database.connection import engine, Base
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Base.metadata.create_all(bind=engine)

app.include_router(auth_router, prefix="/auth", tags=["auth"])

app.include_router(domain_router, prefix="/domains", tags=["domains"])

@app.get("/")
async def root():
    return {"message": "Hello World"}
