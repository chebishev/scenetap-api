class PropertySwitchDevice:
    def __init__(self, api, did, siid, piid):
        self.api = api
        self.did = did
        self.siid = siid
        self.piid = piid

    def get_state(self) -> bool:
        result = self.api.get_devices_prop(
            {
                "did": self.did,
                "siid": self.siid,
                "piid": self.piid,
            }
        )

        if result.get("code") != 0:
            raise RuntimeError(f"Failed to read device state: {result}")

        value = result.get("value")

        if not isinstance(value, bool):
            raise RuntimeError(f"Unexpected device state: {result}")

        return value

    def set_state(self, state: bool) -> dict:
        result = self.api.set_devices_prop(
            {
                "did": self.did,
                "siid": self.siid,
                "piid": self.piid,
                "value": state,
            }
        )

        if result.get("code") != 0:
            raise RuntimeError(f"Failed to set device state: {result}")

        return result


    def turn_on(self) -> dict:
        return self.set_state(True)

    def turn_off(self) -> dict:
        return self.set_state(False)


from mijiaAPI import get_device_info
from mijiaAPI.devices import DevProp


def find_state_property(api, item):
    
    dev_info = get_device_info(
        item["spec_type"],
        cache_path=api.auth_data_path.parent,
    )

    for prop_data in dev_info.get("properties", []):
        prop = DevProp(prop_data)

        expected_name = (
            "on-2"
            if item["model"] == "chuangmi.plug.m1"
            else "on"
        )

        if prop.name == expected_name:
            if prop.type == "bool" and prop.rw == "rw":
                return prop.method

    return None