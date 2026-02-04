from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import reports

app = FastAPI(
    title="BionicPRO Reports API",
    description="API для получения отчётов по клиентам и телеметрии протезов из OLAP-хранилища",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports.router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/")
def root():
    return {
        "service": "BionicPRO Reports API",
        "version": "1.0.0",
        "docs": "/docs",
    }
