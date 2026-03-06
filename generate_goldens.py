#!/usr/bin/env python3
"""Generate golden samples for 10 new games from templates."""
import json, os

GAMES = [
    {
        "dir": "breakout", "prompt": "做一个打砖块",
        "title": "打砖块", "style": "霓虹复古风格，黑色背景，彩色砖块",
        "colors": {"primary": "#00BCD4", "secondary": "#FF4081", "bg": "#1A1A2E"},
        "gameplay_desc": "顶部是彩色砖块阵列。底部有一个可左右移动的挡板。球在屏幕中弹跳，碰到砖块消除得分。顶部显示得分、关卡和生命数。",
        "gameplay_extra": [
            {"id": "paddle", "type": "css", "rect": {"x": 390, "y": 1600, "width": 300, "height": 30, "z_index": 2},
             "style": {"background-color": "#00BCD4", "border-radius": "15px"}},
            {"id": "ball", "type": "css", "rect": {"x": 520, "y": 1550, "width": 40, "height": 40, "z_index": 2},
             "style": {"background-color": "#FFFFFF", "border-radius": "20px"}},
            {"id": "bricks_area", "type": "css", "rect": {"x": 40, "y": 200, "width": 1000, "height": 600, "z_index": 1},
             "style": {"background-color": "rgba(255,255,255,0.05)", "border-radius": "8px"}},
        ],
    },
    {
        "dir": "minesweeper", "prompt": "做一个扫雷",
        "title": "扫雷", "style": "经典Windows风格，灰色方块，简约图标",
        "colors": {"primary": "#607D8B", "secondary": "#FF5722", "bg": "#BDBDBD"},
        "gameplay_desc": "顶部显示剩余地雷数和计时器。主区域是9x9网格，每格可点击翻开或长按插旗。数字显示周围地雷数。",
        "gameplay_extra": [
            {"id": "mine_count", "type": "text", "inner_text": "💣 10", "rect": {"x": 40, "y": 60, "width": 200, "height": 60, "z_index": 1},
             "style": {"color": "#F44336", "font-size": "40px", "font-weight": "bold"}},
            {"id": "timer", "type": "text", "inner_text": "⏱ 000", "rect": {"x": 840, "y": 60, "width": 200, "height": 60, "z_index": 1},
             "style": {"color": "#333333", "font-size": "40px", "font-weight": "bold", "text-align": "right"}},
            {"id": "grid_bg", "type": "css", "rect": {"x": 40, "y": 200, "width": 1000, "height": 1000, "z_index": 1},
             "style": {"background-color": "#9E9E9E", "border-radius": "4px", "border": "3px solid #757575"}},
        ],
    },
    {
        "dir": "piano_tiles", "prompt": "做一个别踩白块",
        "title": "别踩白块", "style": "极简黑白风格，钢琴键盘元素",
        "colors": {"primary": "#212121", "secondary": "#F44336", "bg": "#FFFFFF"},
        "gameplay_desc": "4列黑白方块从上方滚动下来。玩家需要点击黑色方块，不能点到白色方块。顶部显示得分和速度。",
        "gameplay_extra": [
            {"id": "lane_dividers", "type": "css", "rect": {"x": 0, "y": 160, "width": 1080, "height": 1600, "z_index": 1},
             "style": {"background-color": "#FFFFFF", "border-left": "2px solid #E0E0E0", "border-right": "2px solid #E0E0E0"}},
            {"id": "black_tile_1", "type": "css", "rect": {"x": 0, "y": 560, "width": 270, "height": 400, "z_index": 2},
             "style": {"background-color": "#212121"}},
            {"id": "black_tile_2", "type": "css", "rect": {"x": 540, "y": 960, "width": 270, "height": 400, "z_index": 2},
             "style": {"background-color": "#212121"}},
        ],
    },
    {
        "dir": "fruit_ninja", "prompt": "做一个切水果",
        "title": "切水果", "style": "鲜艳水果风格，木质背景，刀光特效",
        "colors": {"primary": "#FF9800", "secondary": "#4CAF50", "bg": "#3E2723"},
        "gameplay_desc": "水果从屏幕底部抛上来，玩家滑动切割得分。炸弹不能切。顶部显示得分和生命数（3颗心）。有连击特效。",
        "gameplay_extra": [
            {"id": "fruit_1", "type": "image", "asset_id": "fruit_apple", "rect": {"x": 300, "y": 800, "width": 160, "height": 160, "z_index": 2},
             "style": {"opacity": 1}},
            {"id": "fruit_2", "type": "image", "asset_id": "fruit_orange", "rect": {"x": 600, "y": 600, "width": 140, "height": 140, "z_index": 2},
             "style": {"opacity": 1}},
            {"id": "lives", "type": "text", "inner_text": "❤❤❤", "rect": {"x": 840, "y": 60, "width": 200, "height": 60, "z_index": 1},
             "style": {"color": "#F44336", "font-size": "36px", "text-align": "right"}},
        ],
    },
    {
        "dir": "whack_mole", "prompt": "做一个打地鼠",
        "title": "打地鼠", "style": "卡通农场风格，绿色草地，可爱地鼠",
        "colors": {"primary": "#8BC34A", "secondary": "#795548", "bg": "#4CAF50"},
        "gameplay_desc": "9个地洞排成3x3网格。地鼠随机从洞里冒出，玩家点击地鼠得分。顶部显示得分和倒计时（60秒）。",
        "gameplay_extra": [
            {"id": "mole_1", "type": "image", "asset_id": "mole", "rect": {"x": 140, "y": 500, "width": 200, "height": 200, "z_index": 2},
             "style": {"opacity": 1}},
            {"id": "timer", "type": "text", "inner_text": "⏱ 60s", "rect": {"x": 840, "y": 60, "width": 200, "height": 60, "z_index": 1},
             "style": {"color": "#FFFFFF", "font-size": "36px", "font-weight": "bold", "text-align": "right"}},
            {"id": "holes_grid", "type": "css", "rect": {"x": 90, "y": 400, "width": 900, "height": 1100, "z_index": 1},
             "style": {"background-color": "rgba(0,0,0,0.1)", "border-radius": "16px"}},
        ],
    },
    {
        "dir": "match3", "prompt": "做一个消消乐",
        "title": "消消乐", "style": "糖果色彩，圆润方块，梦幻背景",
        "colors": {"primary": "#E91E63", "secondary": "#9C27B0", "bg": "#FCE4EC"},
        "gameplay_desc": "8x8彩色方块网格。玩家交换相邻方块，三个以上同色连线消除得分。顶部显示得分、目标分数和剩余步数。",
        "gameplay_extra": [
            {"id": "moves_left", "type": "text", "inner_text": "步数: 30", "rect": {"x": 40, "y": 60, "width": 200, "height": 60, "z_index": 1},
             "style": {"color": "#E91E63", "font-size": "36px", "font-weight": "bold"}},
            {"id": "target", "type": "text", "inner_text": "目标: 5000", "rect": {"x": 780, "y": 60, "width": 260, "height": 60, "z_index": 1},
             "style": {"color": "#9C27B0", "font-size": "32px", "text-align": "right"}},
            {"id": "grid_bg", "type": "css", "rect": {"x": 40, "y": 240, "width": 1000, "height": 1000, "z_index": 1},
             "style": {"background-color": "rgba(255,255,255,0.5)", "border-radius": "16px"}},
        ],
    },
    {
        "dir": "space_shooter", "prompt": "做一个飞机大战",
        "title": "飞机大战", "style": "像素太空风格，深蓝背景，星星闪烁",
        "colors": {"primary": "#03A9F4", "secondary": "#FF5722", "bg": "#0D1B2A"},
        "gameplay_desc": "玩家飞机在底部，可左右移动并自动射击。敌机从顶部飞入，有不同类型。道具随机掉落。顶部显示得分和生命数。",
        "gameplay_extra": [
            {"id": "player_ship", "type": "image", "asset_id": "ship_player", "rect": {"x": 460, "y": 1500, "width": 160, "height": 180, "z_index": 2},
             "style": {"opacity": 1}},
            {"id": "enemy_1", "type": "image", "asset_id": "ship_enemy", "rect": {"x": 300, "y": 300, "width": 120, "height": 120, "z_index": 2},
             "style": {"opacity": 1}},
            {"id": "lives", "type": "text", "inner_text": "❤❤❤", "rect": {"x": 840, "y": 60, "width": 200, "height": 60, "z_index": 1},
             "style": {"color": "#F44336", "font-size": "36px", "text-align": "right"}},
        ],
    },
    {
        "dir": "sokoban", "prompt": "做一个推箱子",
        "title": "推箱子", "style": "像素复古风格，俯视角，简约配色",
        "colors": {"primary": "#FF9800", "secondary": "#4CAF50", "bg": "#37474F"},
        "gameplay_desc": "俯视角关卡地图。玩家角色推箱子到目标位置。顶部显示当前关卡和步数。有撤销按钮和重置按钮。",
        "gameplay_extra": [
            {"id": "level_label", "type": "text", "inner_text": "第 1 关", "rect": {"x": 40, "y": 60, "width": 200, "height": 60, "z_index": 1},
             "style": {"color": "#FFFFFF", "font-size": "36px", "font-weight": "bold"}},
            {"id": "steps", "type": "text", "inner_text": "步数: 0", "rect": {"x": 780, "y": 60, "width": 260, "height": 60, "z_index": 1},
             "style": {"color": "#FFD700", "font-size": "32px", "text-align": "right"}},
            {"id": "btn_undo", "type": "button", "inner_text": "撤销", "rect": {"x": 40, "y": 1760, "width": 200, "height": 80, "z_index": 3},
             "style": {"background-color": "#FF9800", "color": "#FFFFFF", "font-size": "28px", "border-radius": "12px", "text-align": "center"},
             "event": "click"},
        ],
    },
    {
        "dir": "pinball", "prompt": "做一个弹球",
        "title": "弹球", "style": "霓虹街机风格，深色背景，发光特效",
        "colors": {"primary": "#7C4DFF", "secondary": "#FF4081", "bg": "#121212"},
        "gameplay_desc": "弹球台占据主要区域。底部两个翻板按钮控制左右翻板。球在台上弹跳碰撞得分。顶部显示得分和球数。",
        "gameplay_extra": [
            {"id": "flipper_left", "type": "css", "rect": {"x": 200, "y": 1550, "width": 250, "height": 30, "z_index": 2},
             "style": {"background-color": "#7C4DFF", "border-radius": "15px"}},
            {"id": "flipper_right", "type": "css", "rect": {"x": 630, "y": 1550, "width": 250, "height": 30, "z_index": 2},
             "style": {"background-color": "#7C4DFF", "border-radius": "15px"}},
            {"id": "ball", "type": "css", "rect": {"x": 520, "y": 800, "width": 40, "height": 40, "z_index": 3},
             "style": {"background-color": "#FFFFFF", "border-radius": "20px"}},
        ],
    },
    {
        "dir": "circle_pin", "prompt": "做一个见缝插针",
        "title": "见缝插针", "style": "极简黑白风格，几何图形，干净线条",
        "colors": {"primary": "#333333", "secondary": "#F44336", "bg": "#FAFAFA"},
        "gameplay_desc": "屏幕中央一个旋转的大圆，上面已插有若干针。底部显示待插入的针。玩家点击屏幕将针插入圆中，不能碰到已有的针。顶部显示当前关卡和进度。",
        "gameplay_extra": [
            {"id": "circle", "type": "css", "rect": {"x": 340, "y": 500, "width": 400, "height": 400, "z_index": 1},
             "style": {"background-color": "#333333", "border-radius": "200px"}},
            {"id": "needle_queue", "type": "text", "inner_text": "|||||||", "rect": {"x": 390, "y": 1200, "width": 300, "height": 60, "z_index": 1},
             "style": {"color": "#333333", "font-size": "48px", "text-align": "center"}},
            {"id": "level_progress", "type": "text", "inner_text": "3/10", "rect": {"x": 840, "y": 60, "width": 200, "height": 60, "z_index": 1},
             "style": {"color": "#999999", "font-size": "32px", "text-align": "right"}},
        ],
    },
]


def make_golden(g):
    d = os.path.join("intention_graph", "golden_samples", g["dir"])
    os.makedirs(d, exist_ok=True)
    c = g["colors"]

    # --- interface_plan.json ---
    plan = {
        "game_title": g["title"],
        "art_style": g["style"],
        "global_resolution": {"width": 1080, "height": 1920},
        "total_interfaces": 4,
        "entry_interface": "main_menu",
        "interfaces": [
            {"index": 1, "id": "main_menu", "name": "主菜单", "type": "page",
             "dimensions": {"width": 1080, "height": 1920},
             "description": f"游戏标题'{g['title']}'居中显示。下方有开始游戏按钮和排行榜按钮。",
             "belongs_to": None, "navigation_from": ["game_over"], "navigation_to": ["gameplay"]},
            {"index": 2, "id": "gameplay", "name": "游戏界面", "type": "page",
             "dimensions": {"width": 1080, "height": 1920},
             "description": g["gameplay_desc"],
             "belongs_to": None, "navigation_from": ["main_menu"], "navigation_to": ["game_over"]},
            {"index": 3, "id": "game_over", "name": "游戏结束", "type": "page",
             "dimensions": {"width": 1080, "height": 1920},
             "description": "显示游戏结束文字和最终得分。有重试按钮、返回主菜单按钮和排行榜按钮。",
             "belongs_to": None, "navigation_from": ["gameplay"],
             "navigation_to": ["gameplay", "main_menu", "leaderboard"]},
            {"index": 4, "id": "leaderboard", "name": "排行榜", "type": "popup",
             "dimensions": {"width": 800, "height": 1000},
             "description": "显示前5名最高分排名列表。底部有关闭按钮。",
             "belongs_to": "game_over", "navigation_from": ["game_over"], "navigation_to": []},
        ]
    }
    with open(os.path.join(d, "interface_plan.json"), "w") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    # --- wireframe.json ---
    def elem(id, type, rect, style, asset_id=None, inner_text=None, event=None, target=None):
        return {"id": id, "type": type, "asset_id": asset_id, "inner_text": inner_text,
                "rect": rect, "style": style, "event": event,
                "target_interface_id": target, "element_class": "editable"}

    bg_elem = elem("bg", "image", {"x":0,"y":0,"width":1080,"height":1920,"z_index":0}, {"opacity":1}, asset_id="bg_main")

    # Main menu
    menu_elems = [
        bg_elem,
        elem("title", "text", {"x":190,"y":400,"width":700,"height":160,"z_index":1},
             {"color": c["primary"], "font-size": "72px", "font-weight": "bold", "text-align": "center"},
             inner_text=g["title"]),
        elem("btn_play", "button", {"x":290,"y":900,"width":500,"height":120,"z_index":2},
             {"background-color": c["primary"], "color": "#FFFFFF", "font-size": "42px",
              "font-weight": "bold", "border-radius": "16px", "text-align": "center"},
             inner_text="开始游戏", event="click", target="gameplay"),
        elem("btn_leaderboard", "button", {"x":340,"y":1070,"width":400,"height":100,"z_index":2},
             {"background-color": "transparent", "color": c["primary"], "font-size": "36px",
              "border": f"3px solid {c['primary']}", "border-radius": "12px", "text-align": "center"},
             inner_text="排行榜", event="click", target="leaderboard"),
    ]

    # Gameplay
    gp_elems = [
        bg_elem,
        elem("score_display", "text", {"x":440,"y":60,"width":200,"height":60,"z_index":1},
             {"color": c["primary"], "font-size": "40px", "font-weight": "bold", "text-align": "center"},
             inner_text="得分: 0"),
    ]
    for ex in g["gameplay_extra"]:
        e = {"id": ex["id"], "type": ex["type"], "asset_id": ex.get("asset_id"),
             "inner_text": ex.get("inner_text"), "rect": ex["rect"], "style": ex["style"],
             "event": ex.get("event"), "target_interface_id": ex.get("target"),
             "element_class": "editable"}
        gp_elems.append(e)
    gp_elems.append(
        elem("tap_area", "button", {"x":0,"y":0,"width":1080,"height":1920,"z_index":5},
             {"opacity": 0}, event="click"))

    # Game over
    go_elems = [
        elem("bg", "image", {"x":0,"y":0,"width":1080,"height":1920,"z_index":0}, {"opacity":0.4}, asset_id="bg_main"),
        elem("gameover_text", "text", {"x":190,"y":550,"width":700,"height":120,"z_index":1},
             {"color": c["primary"], "font-size": "64px", "font-weight": "bold", "text-align": "center"},
             inner_text="游戏结束"),
        elem("final_score", "text", {"x":290,"y":720,"width":500,"height":80,"z_index":1},
             {"color": c["secondary"], "font-size": "40px", "text-align": "center"},
             inner_text="得分: 0"),
        elem("btn_retry", "button", {"x":290,"y":920,"width":500,"height":120,"z_index":2},
             {"background-color": c["primary"], "color": "#FFFFFF", "font-size": "42px",
              "font-weight": "bold", "border-radius": "16px", "text-align": "center"},
             inner_text="再来一次", event="click", target="gameplay"),
        elem("btn_menu", "button", {"x":290,"y":1090,"width":500,"height":100,"z_index":2},
             {"background-color": c["secondary"], "color": "#FFFFFF", "font-size": "36px",
              "border-radius": "12px", "text-align": "center"},
             inner_text="主菜单", event="click", target="main_menu"),
        elem("btn_leaderboard", "button", {"x":340,"y":1240,"width":400,"height":80,"z_index":2},
             {"background-color": "transparent", "color": c["primary"], "font-size": "32px",
              "border": f"2px solid {c['primary']}", "border-radius": "12px", "text-align": "center"},
             inner_text="排行榜", event="click", target="leaderboard"),
    ]

    # Leaderboard popup
    lb_elems = [
        elem("panel_bg", "css", {"x":0,"y":0,"width":800,"height":1000,"z_index":0},
             {"background-color": "#FFFFFF", "border-radius": "20px", "border": f"4px solid {c['primary']}"}),
        elem("title", "text", {"x":200,"y":60,"width":400,"height":80,"z_index":1},
             {"color": c["primary"], "font-size": "48px", "font-weight": "bold", "text-align": "center"},
             inner_text="排行榜"),
        elem("score_list", "text", {"x":100,"y":200,"width":600,"height":500,"z_index":1},
             {"color": "#333333", "font-size": "40px", "line-height": "1.8", "text-align": "left"},
             inner_text="1. 9999\n2. 7500\n3. 5000\n4. 2500\n5. 1000"),
        elem("btn_close", "button", {"x":250,"y":820,"width":300,"height":100,"z_index":2},
             {"background-color": c["primary"], "color": "#FFFFFF", "font-size": "36px",
              "font-weight": "bold", "border-radius": "12px", "text-align": "center"},
             inner_text="关闭", event="click"),
    ]

    wf = {
        "project": {"title": g["title"], "global_resolution": {"width": 1080, "height": 1920}},
        "asset_library": {"bg_main": {"type": "image", "path": "assets/images/bg_main.png", "label": "主背景"}},
        "modules": [
            {"module_id": "menu_flow", "module_name": "菜单流程", "description": "主菜单和排行榜",
             "color": c["primary"], "interface_ids": ["main_menu", "leaderboard"]},
            {"module_id": "gameplay_flow", "module_name": "游戏流程", "description": "核心游戏和结算",
             "color": c["secondary"], "interface_ids": ["gameplay", "game_over"]},
        ],
        "module_connections": [
            {"from": "menu_flow", "to": "gameplay_flow", "label": "开始游戏"},
            {"from": "gameplay_flow", "to": "menu_flow", "label": "返回菜单"},
        ],
        "interfaces": [
            {"interface_id": "main_menu", "interface_name": "主菜单", "module_id": "menu_flow",
             "type": "page", "parents": ["game_over"], "children": ["gameplay"],
             "dimensions": {"width": 1080, "height": 1920}, "elements": menu_elems, "bg_music_asset_id": None},
            {"interface_id": "gameplay", "interface_name": "游戏界面", "module_id": "gameplay_flow",
             "type": "page", "parents": ["main_menu"], "children": ["game_over"],
             "dimensions": {"width": 1080, "height": 1920}, "elements": gp_elems, "bg_music_asset_id": None},
            {"interface_id": "game_over", "interface_name": "游戏结束", "module_id": "gameplay_flow",
             "type": "page", "parents": ["gameplay"], "children": ["gameplay", "main_menu", "leaderboard"],
             "dimensions": {"width": 1080, "height": 1920}, "elements": go_elems, "bg_music_asset_id": None},
            {"interface_id": "leaderboard", "interface_name": "排行榜", "module_id": "menu_flow",
             "type": "popup", "parents": ["game_over"], "children": [],
             "dimensions": {"width": 800, "height": 1000}, "elements": lb_elems, "bg_music_asset_id": None},
        ],
    }
    # Add game-specific assets
    for ex in g["gameplay_extra"]:
        if ex["type"] == "image" and ex.get("asset_id"):
            wf["asset_library"][ex["asset_id"]] = {
                "type": "image", "path": f"assets/images/{ex['asset_id']}.png", "label": ex["asset_id"]}

    with open(os.path.join(d, "wireframe.json"), "w") as f:
        json.dump(wf, f, ensure_ascii=False, indent=2)

    print(f"  [{g['dir']}] plan={len(plan['interfaces'])} screens, "
          f"wf={sum(len(i['elements']) for i in wf['interfaces'])} elements")


if __name__ == "__main__":
    print("Generating 10 golden samples...")
    for g in GAMES:
        make_golden(g)
    print("Done.")
