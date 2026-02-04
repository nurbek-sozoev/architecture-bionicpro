from fastapi import FastAPI

from app.routers import reports

app = FastAPI(
    title="BionicPRO Reports API",
    description="API для получения отчётов по клиентам и телеметрии протезов из OLAP-хранилища",
    version="1.0.0",
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
