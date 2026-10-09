"""Locations of portable app data: everything lives next to the executable."""
import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def models_dir() -> Path:
    return app_dir() / "models"


def settings_path() -> Path:
    return app_dir() / "settings.json"
