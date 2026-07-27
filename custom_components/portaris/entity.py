"""Helpers de device_info compartilhados pelas plataformas."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def door_device_info(door: dict) -> DeviceInfo:
    """Cada porta do Portaris vira um dispositivo no Home Assistant."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"door_{door['id']}")},
        name=door["name"],
        manufacturer="Portaris",
        model="Porta",
        suggested_area=door.get("location"),
    )


def reader_device_info(reader: dict) -> DeviceInfo:
    """Cada leitor (DP Core Board) vira um dispositivo no Home Assistant."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"reader_{reader['id']}")},
        name=reader["serialNumber"],
        manufacturer="Portaris",
        model="DP Core Board",
    )
