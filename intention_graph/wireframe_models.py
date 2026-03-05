"""Wireframe data models — matches WIREFRAME_GENERATION_GUIDE.md JSON schemas.

Three-stage pipeline data:
- InterfacePlan (Stage 1): screen inventory + navigation
- AssetTable (Stage 2): asset manifest
- WireframeSpec (Stage 3): per-screen element layouts
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Stage 1: Interface Plan ──────────────────────────────────────────────────


class InterfaceSpec(BaseModel):
    """A single screen/popup in the interface plan."""

    index: int
    id: str
    name: str
    type: str = "page"  # "page" | "popup"
    dimensions: dict = Field(
        default_factory=lambda: {"width": 1080, "height": 1920}
    )
    description: str = ""
    belongs_to: str | None = None
    navigation_from: list[str] = Field(default_factory=list)
    navigation_to: list[str] = Field(default_factory=list)


class InterfacePlan(BaseModel):
    """Stage 1 output: screen list + navigation graph."""

    game_title: str
    art_style: str = ""
    global_resolution: dict = Field(
        default_factory=lambda: {"width": 1080, "height": 1920}
    )
    total_interfaces: int = 0
    entry_interface: str = ""
    interfaces: list[InterfaceSpec] = Field(default_factory=list)


# ── Stage 2: Asset Table ─────────────────────────────────────────────────────


class AssetEntry(BaseModel):
    """A single asset in the asset table."""

    id: str
    type: str = "image"  # "image" | "audio"
    category: str = ""  # "background" | "character" | "ui" | "music" | "sfx"
    usage: str = ""
    description: str = ""
    implementation: str = "image"  # "image" | "css" | "text"
    dimensions: dict | None = None
    default_label: str = ""
    format: str = "png"
    path: str = ""


class AssetTable(BaseModel):
    """Stage 2 output: asset manifest."""

    schema_version: str = "asset-table-1.1"
    meta: dict = Field(default_factory=dict)
    assets: list[AssetEntry] = Field(default_factory=list)


# ── Stage 3: Wireframe Spec ──────────────────────────────────────────────────


class WireframeElement(BaseModel):
    """A single UI element on a screen."""

    id: str
    type: str  # "image" | "text" | "button" | "css"
    asset_id: str | None = None
    inner_text: str | None = None
    rect: dict  # {"x", "y", "width", "height", "z_index"}
    style: dict = Field(default_factory=dict)
    event: str | None = None  # "click" | None
    target_interface_id: str | None = None
    element_class: str = "editable"


class WireframeInterface(BaseModel):
    """A single screen with its element layout."""

    interface_id: str
    interface_name: str
    module_id: str = ""
    type: str = "page"  # "page" | "popup"
    parents: list[str] = Field(default_factory=list)
    children: list[str] = Field(default_factory=list)
    dimensions: dict = Field(
        default_factory=lambda: {"width": 1080, "height": 1920}
    )
    elements: list[WireframeElement] = Field(default_factory=list)
    bg_music_asset_id: str | None = None


class WireframeSpec(BaseModel):
    """Stage 3 output: complete wireframe specification."""

    project: dict  # {"title": str, "global_resolution": dict}
    asset_library: dict = Field(default_factory=dict)
    modules: list[dict] = Field(default_factory=list)
    module_connections: list[dict] = Field(default_factory=list)
    interfaces: list[WireframeInterface] = Field(default_factory=list)
