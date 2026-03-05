"""Tests for wireframe data models."""

from intention_graph.wireframe_models import (
    InterfaceSpec,
    InterfacePlan,
    AssetEntry,
    AssetTable,
    WireframeElement,
    WireframeInterface,
    WireframeSpec,
)


# ── InterfaceSpec / InterfacePlan ─────────────────────────────────────────────


def test_interface_spec_defaults():
    spec = InterfaceSpec(index=1, id="main_menu", name="主菜单")
    assert spec.type == "page"
    assert spec.belongs_to is None
    assert spec.navigation_from == []
    assert spec.navigation_to == []
    assert spec.dimensions["width"] == 1080


def test_interface_spec_popup():
    spec = InterfaceSpec(
        index=3, id="pause", name="暂停", type="popup",
        belongs_to="gameplay",
        navigation_from=["gameplay"],
        navigation_to=["gameplay", "main_menu"],
    )
    assert spec.type == "popup"
    assert spec.belongs_to == "gameplay"
    assert len(spec.navigation_to) == 2


def test_interface_plan_creation():
    plan = InterfacePlan(
        game_title="Flappy Bird", art_style="pixel",
        total_interfaces=3, entry_interface="start",
        interfaces=[
            InterfaceSpec(index=1, id="start", name="开始"),
            InterfaceSpec(index=2, id="gameplay", name="游戏"),
            InterfaceSpec(index=3, id="game_over", name="结束"),
        ],
    )
    assert plan.total_interfaces == 3
    assert len(plan.interfaces) == 3
    assert plan.entry_interface == "start"


def test_interface_plan_serialization():
    plan = InterfacePlan(
        game_title="Test", art_style="flat",
        interfaces=[],
    )
    d = plan.model_dump()
    assert d["game_title"] == "Test"
    assert isinstance(d["interfaces"], list)

    # Round-trip
    plan2 = InterfacePlan.model_validate(d)
    assert plan2.game_title == "Test"


# ── AssetEntry / AssetTable ──────────────────────────────────────────────────


def test_asset_entry_defaults():
    entry = AssetEntry(id="bg_main")
    assert entry.type == "image"
    assert entry.implementation == "image"
    assert entry.format == "png"


def test_asset_entry_css_button():
    entry = AssetEntry(
        id="btn_start", type="image", category="ui",
        implementation="css", default_label="开始游戏",
    )
    assert entry.implementation == "css"
    assert entry.default_label == "开始游戏"


def test_asset_table_creation():
    table = AssetTable(
        meta={"gameTitle": "Test", "artDirection": "pixel"},
        assets=[
            AssetEntry(id="bg_main", category="background"),
            AssetEntry(id="bgm_game", type="audio", category="music", format="mp3"),
        ],
    )
    assert len(table.assets) == 2
    assert table.schema_version == "asset-table-1.1"


def test_asset_table_serialization():
    table = AssetTable(meta={"gameTitle": "Test"})
    d = table.model_dump()
    assert d["schema_version"] == "asset-table-1.1"

    table2 = AssetTable.model_validate(d)
    assert table2.meta["gameTitle"] == "Test"


# ── WireframeElement / WireframeInterface / WireframeSpec ─────────────────────


def test_wireframe_element_button():
    elem = WireframeElement(
        id="btn_start", type="button",
        inner_text="开始游戏",
        rect={"x": 340, "y": 900, "width": 400, "height": 80, "z_index": 2},
        style={"background-color": "#FF6B35", "color": "#FFFFFF"},
        event="click",
        target_interface_id="gameplay",
    )
    assert elem.type == "button"
    assert elem.event == "click"
    assert elem.target_interface_id == "gameplay"
    assert elem.asset_id is None


def test_wireframe_element_image():
    elem = WireframeElement(
        id="bg_main", type="image", asset_id="bg_main_menu",
        rect={"x": 0, "y": 0, "width": 1080, "height": 1920, "z_index": 0},
    )
    assert elem.asset_id == "bg_main_menu"
    assert elem.inner_text is None


def test_wireframe_element_defaults():
    elem = WireframeElement(
        id="test", type="text",
        rect={"x": 0, "y": 0, "width": 100, "height": 50, "z_index": 0},
    )
    assert elem.element_class == "editable"
    assert elem.style == {}
    assert elem.event is None


def test_wireframe_interface_creation():
    iface = WireframeInterface(
        interface_id="main_menu",
        interface_name="主菜单",
        module_id="menu_flow",
        children=["gameplay"],
        elements=[
            WireframeElement(
                id="title", type="text", inner_text="Game Title",
                rect={"x": 240, "y": 300, "width": 600, "height": 120, "z_index": 1},
            ),
        ],
    )
    assert iface.interface_id == "main_menu"
    assert len(iface.elements) == 1
    assert iface.bg_music_asset_id is None


def test_wireframe_spec_creation():
    spec = WireframeSpec(
        project={"title": "Test", "global_resolution": {"width": 1080, "height": 1920}},
        asset_library={"bg_main": {"type": "image", "path": "assets/bg.png", "label": "背景"}},
        interfaces=[
            WireframeInterface(
                interface_id="main",
                interface_name="Main",
                elements=[],
            ),
        ],
    )
    assert spec.project["title"] == "Test"
    assert len(spec.interfaces) == 1
    assert "bg_main" in spec.asset_library


def test_wireframe_spec_empty():
    spec = WireframeSpec(
        project={"title": "Empty", "global_resolution": {"width": 1080, "height": 1920}},
    )
    assert spec.interfaces == []
    assert spec.modules == []
    assert spec.module_connections == []
    assert spec.asset_library == {}


def test_wireframe_spec_serialization():
    spec = WireframeSpec(
        project={"title": "Test", "global_resolution": {"width": 1080, "height": 1920}},
        interfaces=[
            WireframeInterface(
                interface_id="main", interface_name="Main",
                elements=[
                    WireframeElement(
                        id="btn", type="button", inner_text="Click",
                        rect={"x": 0, "y": 0, "width": 100, "height": 50, "z_index": 0},
                        event="click", target_interface_id="next",
                    ),
                ],
            ),
        ],
    )
    d = spec.model_dump()
    assert d["interfaces"][0]["elements"][0]["event"] == "click"

    # Round-trip
    spec2 = WireframeSpec.model_validate(d)
    assert spec2.interfaces[0].elements[0].target_interface_id == "next"
