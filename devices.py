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


from mijiaAPI import mijiaDevice


def find_state_property(api, item):
    device = mijiaDevice(api, dev_name=item["name"])

    if item["model"] == "chuangmi.plug.m1":
        prop = device.prop_list.get("on-2")
    else:
        prop = device.prop_list.get("on")

    if prop is None:
        return None

    if prop.type != "bool" or prop.rw != "rw":
        return None

    return prop.method