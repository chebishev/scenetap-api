import os
import secrets

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header
from mijiaAPI import mijiaAPI, mijiaDevice
from devices import PropertySwitchDevice, find_state_property
from pydantic import BaseModel

load_dotenv()
API_KEY = os.environ.get("SCENETAP_API_KEY")

if not API_KEY:
    raise RuntimeError("SCENETAP_API_KEY environment variable is not set")


def verify_api_key(x_api_key: str = Header()):
    if not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )


app = FastAPI(dependencies=[Depends(verify_api_key)])
api = mijiaAPI()


class DeviceStateRequest(BaseModel):
    state: bool


@app.get("/")
def read_root():
    return {"message": "SceneTap API is running"}


@app.get("/scenes")
def get_scenes():
    scenes = api.get_scenes_list()

    return {
        "items": [
            {
                "scene_id": scene["scene_id"],
                "name": scene["name"],
            }
            for scene in scenes
            if scene.get("enable") is True
        ]
    }


@app.get("/devices")
def get_devices():
    items = []

    for item in api.get_devices_list():
        if not item.get("isOnline"):
            continue

        state_property = find_state_property(api, item)

        if state_property is None:
            continue

        device = PropertySwitchDevice(
            api=api,
            did=item["did"],
            siid=state_property["siid"],
            piid=state_property["piid"],
        )

        items.append(
            {
                "did": item["did"],
                "name": item["name"],
                "model": item["model"],
                "state": device.get_state(),
            }
        )

    return {"items": items}


@app.post("/scenes/{scene_id}/run")
def run_scene(scene_id: str):
    scenes = api.get_scenes_list()

    scene = next(
        (
            item
            for item in scenes
            if str(item.get("scene_id")) == scene_id and item.get("enable") is True
        ),
        None,
    )

    if scene is None:
        raise HTTPException(
            status_code=404,
            detail="Scene not found or disabled",
        )

    home_id = scene.get("home_id")

    if home_id is None:
        raise HTTPException(
            status_code=500,
            detail="Scene has no home_id",
        )

    try:
        success = api.run_scene(
            scene_id=scene_id,
            home_id=str(home_id),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    if not success:
        raise HTTPException(
            status_code=502,
            detail="Scene execution failed",
        )

    return {
        "scene_id": scene_id,
        "name": scene.get("name"),
        "command_accepted": True,
    }


@app.post("/devices/{did}/state")
def set_device_state(did: str, request: DeviceStateRequest):
    devices = api.get_devices_list()

    print("SET_DEVICE_STATE reached", flush=True)
    print("Requested DID:", repr(did), flush=True)
    print("Devices count:", len(devices), flush=True)

    for item in devices:
        print(
            "Item DID:",
            repr(item.get("did")),
            "| Online:",
            repr(item.get("isOnline")),
            flush=True,
        )

        if item["did"] != did or not item.get("isOnline"):
            continue

        state_property = find_state_property(api, item)

        if state_property is None:
            raise HTTPException(
                status_code=400,
                detail="Device does not support state control",
            )

        device = PropertySwitchDevice(
            api=api,
            did=item["did"],
            siid=state_property["siid"],
            piid=state_property["piid"],
        )

        try:
            device.set_state(request.state)
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc))

        return {
            "did": did,
            "state": request.state,
            "command_accepted": True,
        }

    raise HTTPException(
        status_code=404,
        detail="Device not found or offline",
    )
