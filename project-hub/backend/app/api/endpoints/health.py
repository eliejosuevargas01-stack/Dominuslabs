from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings
import os

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: Session = Depends(get_db)):
    """
    Advanced Enterprise Healthcheck (Liveness / Readiness Probe)
    Checks Database connection and File System write access.
    """
    health_status = {
        "status": "ok",
        "database": "unknown",
        "filesystem": "unknown",
        "version": "1.0.0" # Assuming a static version for now
    }

    # 1. Check Database connection
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "healthy"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["database"] = f"unhealthy: {str(e)}"

    # 2. Check File System Write Access
    try:
        test_file_path = os.path.join(settings.UPLOAD_DIR, ".healthcheck")
        with open(test_file_path, "w") as f:
            f.write("ok")
        os.remove(test_file_path)
        health_status["filesystem"] = "healthy"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["filesystem"] = f"unhealthy: {str(e)}"

    if health_status["status"] != "ok":
        # Raise 503 so that Load Balancers (ELB) or Kubernetes can take action (Self-Healing)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=health_status)

    return health_status
