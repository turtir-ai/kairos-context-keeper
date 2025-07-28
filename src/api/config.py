from fastapi import APIRouter, HTTPException
import toml
from pathlib import Path

router = APIRouter()

CONFIG_FILE = Path("kairos.toml")

@router.get("/config")
async def get_config():
    try:
        with open(CONFIG_FILE, "r") as file:
            config = toml.load(file)
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read configuration: {str(e)}")

@router.post("/config")
async def update_config(updated_config: dict):
    try:
        with open(CONFIG_FILE, "r") as file:
            existing_config = toml.load(file)
        
        # Update existing config with new values
        existing_config.update(updated_config)
        
        with open(CONFIG_FILE, "w") as file:
            toml.dump(existing_config, file)
        return {"detail": "Configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")
