"""Pydantic models for Bitwarden ESO migration inventory."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class InventoryEntry(BaseModel):
    """Inventory entry describing a single SOPS secret file."""

    sops_path: str
    namespace: str
    app: str
    purpose: str
    item_name: str
    fields: List[str] = Field(default_factory=list)
    ks_path: Optional[str] = None
    helmrelease_path: Optional[str] = None
    secret_id: Optional[str] = None


class Inventory(BaseModel):
    """Inventory containing all discovered entries."""

    version: int = 1
    root: str
    project_id: Optional[str] = None
    org_id: Optional[str] = None
    entries: List[InventoryEntry] = Field(default_factory=list)
