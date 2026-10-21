from fastapi import FastAPI, HTTPException
from mijiaAPI import mijiaAPI, mijiaDevice
from devices import PropertySwitchDevice, find_state_property
from pydantic import BaseModel

app = FastAPI()
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

        items.append({
            "did": item["did"],
            "name": item["name"],
            "model": item["model"],
            "state": device.get_state(),
        })

    return {"items": items}


@app.post("/devices/{did}/state")
def set_device_state(did: str, request: DeviceStateRequest):
    devices = api.get_devices_list()

    print("SET_DEVICE_STATE reached", flush=True)
    print("Requested DID:", repr(did), flush=True)
    print("Devices count:", len(devices), flush=True)

    for item in devices:
        print(
            "Item DID:", repr(item.get("did")),
            "| Online:", repr(item.get("isOnline")),
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
    
@app.get("/debug/devices")
def debug_devices():
    devices = api.get_devices_list()

    return [
        {
            "did": repr(item.get("did")),
            "did_type": type(item.get("did")).__name__,
            "name": item.get("name"),
            "isOnline": item.get("isOnline"),
        }
        for item in devices
    ]
    