import os
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
import tuya_service

load_dotenv()

app = FastAPI(title="Home Automation API Gateway", version="1.0.0")

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(key: str = Security(API_KEY_HEADER)):
    expected = os.environ.get("API_KEY")
    if not expected or key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return key


# ---------- Models ----------

class TuyaControlRequest(BaseModel):
    device_id: str
    power: Optional[bool] = None
    brightness: Optional[int] = None  # 0-100


# ---------- Routes ----------

@app.get("/health")
def health():
    return {"status": "ok", "service": "HomeAPI"}


@app.post("/api/tuya/control")
def tuya_control(req: TuyaControlRequest, _=Depends(verify_api_key)):
    try:
        result = tuya_service.control_device(req.device_id, req.power, req.brightness)
        return {"success": True, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.get("/api/tuya/status/{device_id}")
def tuya_status(device_id: str, _=Depends(verify_api_key)):
    try:
        result = tuya_service.get_device_status(device_id)
        return {"success": True, "device_id": device_id, "status": result.get("result", [])}
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.get("/api/tuya/cmd")
def tuya_cmd(device_id: str, power: Optional[bool] = None, brightness: Optional[int] = None, key: str = "", _=None):
    # GET endpoint for Garmin watch (query params, API key in URL)
    expected = os.environ.get("API_KEY")
    if not expected or key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    try:
        result = tuya_service.control_device(device_id, power, brightness)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/tuya/scene/{scene_name}")
def tuya_scene(scene_name: str, _=Depends(verify_api_key)):
    # Placeholder for future scene support
    return {"success": False, "detail": f"Scene '{scene_name}' not implemented yet"}
