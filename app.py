import os
import secrets

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header
from mijiaAPI import mijiaAPI, mijiaDevice
from devices import PropertySwitchDevice, find_state_property
from pydantic import BaseModel
from threading import Thread, Lock
from mijiaAPI.errors import LoginError

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


app = FastAPI(
    title="Scene Tap API",
    description="Minimal FastAPI backend for Xiaomi Home scenes and devices that are online and expose a `toggle` action.",
    version="1.0.0",
    contact={
        "name": "Atanas Chebishev",
        "url": "https://chebishev.github.io/",
        "email": "atanas.chebishev@gmail.com",
    },
    license_info={
        "name": "MIT License",
        "identifier": "MIT",
    },
    dependencies=[Depends(verify_api_key)])

api = mijiaAPI()
login_lock = Lock()
login_state = {
    "status": "idle",
    "content": None,
    "error": None,
}


class DeviceStateRequest(BaseModel):
    state: bool


@app.post("/login/qr", tags=["Get QR login URL"])
def start_qr_login():
    """
    Retrieve and convert the URL that will be used for QR login ot the Zepp app
    """
    with login_lock:
        if login_state["status"] == "waiting_for_scan":
            return {
                "status": login_state["status"],
                "content": login_state["content"],
            }

        login_state.update({
            "status": "starting",
            "content": None,
            "error": None,
        })

    try:
        login_data = api._get_qr_login_data()

        if login_data.get("refreshed"):
            login_state.update({
                "status": "authenticated",
                "content": None,
                "error": None,
            })
            return {"status": "authenticated"}

        login_url = login_data["loginUrl"]

        # Convert QR Code link to normal link in order to be generated QR on the watch
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

        parsed = urlparse(login_data["qr"])
        query = parse_qs(parsed.query)

        content = urlunparse((
            "https",
            "eu.account.xiaomi.com",
            "/longPolling/login",
            "",
            urlencode({
                "ticket": query["ticket"][0],
                "dc": query["dc"][0],
                "sid": query["sid"][0],
                "ts": query["ts"][0],
            }),
            "",
        ))

        login_state.update({
            "status": "waiting_for_scan",
            "content": content,
            "error": None,
        })

        def complete_login():
            try:
                api._complete_qr_login(login_data)
                login_state.update({
                    "status": "authenticated",
                    "content": None,
                    "error": None,
                })
            except Exception as exc:
                login_state.update({
                    "status": "failed",
                    "content": None,
                    "error": type(exc).__name__,
                })

        Thread(target=complete_login, daemon=True).start()

        return {
            "status": "waiting_for_scan",
            "content": content,
        }

    except Exception as exc:
        login_state.update({
            "status": "failed",
            "content": None,
            "error": type(exc).__name__,
        })
        raise HTTPException(
            status_code=502,
            detail="Could not start Xiaomi QR login",
        )


@app.get("/login/status", tags=["Check login status"])
def get_login_status():
    """
    Check if the account is already logged in"
    """
    return {
        "status": login_state["status"],
        "error": login_state["error"],
    }

@app.get("/scenes", tags=["Get all the manual scenes"])
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


@app.get("/devices", tags=['Get all online devices, that can be switched on/off'])
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


@app.post("/scenes/{scene_id}/run", tags=["Run scene by id"])
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


@app.post("/devices/{did}/state", tags=["Change device state by id"])
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
