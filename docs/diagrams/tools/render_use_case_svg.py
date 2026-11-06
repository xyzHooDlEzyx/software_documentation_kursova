"""Generate the UML Use Case diagram (SVG + draw.io) from one data model.

Usage: python3 docs/diagrams/tools/render_use_case_svg.py

Layout rule: every actor stands next to the column of use cases it uses, so
association lines fan out over empty space and never cross ellipses or each
other. Only the Python standard library is used.
"""

import math
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]

WIDTH, HEIGHT = 1100, 1660
BOUNDARY = (170, 40, 770, 1400)  # x, y, w, h
FONT = "DejaVu Sans, Arial, Helvetica, sans-serif"

COL_USER = 335  # centre x of the Guest/User column
COL_SIDE = 735  # centre x of the Administrator / supporting column
UC_W, UC_H = 220, 58

# id, label (\n = line break), centre x, centre y, width, height
USE_CASES = [
    ("UC-001", "Реєстрація", COL_USER, 140),
    ("UC-020", "Відновлення пароля", COL_USER, 230),
    ("UC-016", "Вхід / вихід", COL_USER, 330),
    ("UC-002", "Оновлення профілю", COL_USER, 418),
    ("UC-003", "Бібліотека тренувань", COL_USER, 545),
    ("UC-004", "Персональна програма", COL_USER, 633),
    ("UC-005", "Планування занять", COL_USER, 721),
    ("UC-006", "Завершення заняття", COL_USER, 850),
    ("UC-008", "Історія занять", COL_USER, 938),
    ("UC-009", "Прогрес і статистика", COL_USER, 1026),
    ("UC-011", "Участь у челенджі", COL_USER, 1155),
    ("UC-012", "Рейтинг", COL_USER, 1243),
    ("UC-010", "Нагадування", COL_USER, 1372),
    ("UC-007", "Результати вправ", COL_SIDE, 850),
    ("UC-013", "Нарахування\nдосягнень", COL_SIDE, 1155),
    ("UC-014", "Керування каталогом\nвправ і тренувань", COL_SIDE, 140),
    ("UC-017", "Каталог шаблонів\nпрограм", COL_SIDE, 235),
    ("UC-015", "Звіти\nадміністратора", COL_SIDE, 330),
    ("UC-018", "Деактивація\nакаунта", COL_SIDE, 425),
    ("UC-019", "Остаточне видалення\nакаунта (після MVP)", COL_SIDE, 520),
]

# Groups are drawn behind ellipses: id, title, x, y, w, h, fill
GROUPS = [
    ("account", "Акаунт і профіль", 205, 75, 260, 390, "#EEF4FF"),
    ("programs", "Каталог і програми", 205, 480, 260, 287, "#ECFDF3"),
    ("execution", "Виконання і прогрес", 205, 785, 650, 287, "#F4F3FF"),
    ("social", "Соціальні функції", 205, 1090, 650, 200, "#FFF1F3"),
    ("reminders", "Нагадування", 205, 1307, 260, 111, "#ECFDFF"),
    ("admin", "Адміністрування (Django Admin)", 605, 75, 260, 495, "#F2F4F7"),
]

# id, label, x (centre), y (feet), side the lines leave from
ACTORS = [
    ("guest", "Гість", 85, 285),
    ("user", "Користувач", 85, 900),
    ("admin", "Адміністратор", 1010, 380),
    ("system", "Система\n(планувальник)", 560, 1600),
]

ASSOCIATIONS = [
    ("guest", "UC-001"),
    ("guest", "UC-020"),
    ("guest", "UC-016"),
    ("user", "UC-016"),
    ("user", "UC-002"),
    ("user", "UC-003"),
    ("user", "UC-004"),
    ("user", "UC-005"),
    ("user", "UC-006"),
    ("user", "UC-008"),
    ("user", "UC-009"),
    ("user", "UC-011"),
    ("user", "UC-012"),
    ("user", "UC-010"),
    ("admin", "UC-014"),
    ("admin", "UC-017"),
    ("admin", "UC-015"),
    ("admin", "UC-018"),
    ("admin", "UC-019"),
    ("system", "UC-010"),
    ("system", "UC-013"),
]

# source, target, stereotype, source side, target side.
# Arrow points from source to target (UML).
RELATIONS = [
    ("UC-020", "UC-016", "«extend»", "bottom", "top"),
    ("UC-006", "UC-007", "«include»", "right", "left"),
    ("UC-013", "UC-006", "«extend»\n[поріг досягнуто]", "left", "right"),
]

# Which side of an ellipse an actor's association attaches to.
ACTOR_SIDE = {"guest": "left", "user": "left", "admin": "right", "system": None}

# id, text, x, y, w, h
NOTES = [
    (
        "note_completion",
        "E01: факти, kcal, бали\nта snapshots — атомарно",
        620,
        905,
        215,
        52,
    ),
    (
        "note_reports",
        "UC-015: R02 популярні тренування,\nR03 середня активність",
        605,
        590,
        260,
        52,
    ),
    (
        "note_system",
        "Часовий тригер, не обліковий\nзапис користувача",
        700,
        1335,
        215,
        50,
    ),
]

ACTOR_BODY = {"head_r": 13, "height": 92}


def uc_index():
    return {uc[0]: uc for uc in USE_CASES}


def uc_size(uc_id):
    label = uc_index()[uc_id][1]
    return (UC_W, UC_H + (14 if "\n" in label else 0))


def actor_anchor(actor_id, toward):
    """Point on the actor's torso facing the target point."""
    for a_id, _, x, y in ACTORS:
        if a_id == actor_id:
            mid_y = y - ACTOR_BODY["height"] * 0.55
            if actor_id == "system":
                return (x, y - ACTOR_BODY["height"] - 4)
            side = 1 if toward[0] > x else -1
            return (x + side * 18, mid_y)
    raise KeyError(actor_id)


def side_point(uc_id, side):
    _, _, cx, cy = uc_index()[uc_id]
    w, h = uc_size(uc_id)
    return {
        "left": (cx - w / 2, cy),
        "right": (cx + w / 2, cy),
        "top": (cx, cy - h / 2),
        "bottom": (cx, cy + h / 2),
    }[side]


def association_points(actor_id, uc_id):
    _, _, cx, cy = uc_index()[uc_id]
    side = ACTOR_SIDE[actor_id]
    if side is None:
        a = actor_anchor(actor_id, (cx, cy))
        return a, ellipse_point(uc_id, a)
    p = side_point(uc_id, side)
    return actor_anchor(actor_id, p), p


def ellipse_point(uc_id, toward):
    _, _, cx, cy = uc_index()[uc_id]
    w, h = uc_size(uc_id)
    rx, ry = w / 2, h / 2
    dx, dy = toward[0] - cx, toward[1] - cy
    if dx == 0 and dy == 0:
        return (cx, cy)
    t = 1 / math.sqrt((dx / rx) ** 2 + (dy / ry) ** 2)
    return (cx + dx * t, cy + dy * t)


# ---------------------------------------------------------------- SVG output


def svg_text(x, y, text, *, size=13, weight="normal", anchor="middle", fill="#101828"):
    lines = text.split("\n")
    first = y - (len(lines) - 1) * (size + 3) / 2
    out = []
    for i, line in enumerate(lines):
        out.append(
            f'<text x="{x:.1f}" y="{first + i * (size + 3):.1f}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}" '
            f'dominant-baseline="middle" fill="{fill}">{escape(line)}</text>'
        )
    return "\n".join(out)


def svg_actor(actor_id, label, x, y):
    h = ACTOR_BODY["height"]
    r = ACTOR_BODY["head_r"]
    top = y - h
    neck = top + 2 * r
    hip = y - 32
    parts = [
        f'<g id="actor-{actor_id}" stroke="#101828" stroke-width="2" fill="none">',
        f'<circle cx="{x}" cy="{top + r}" r="{r}" fill="#FFFFFF"/>',
        f'<line x1="{x}" y1="{neck}" x2="{x}" y2="{hip}"/>',
        f'<line x1="{x - 22}" y1="{neck + 16}" x2="{x + 22}" y2="{neck + 16}"/>',
        f'<line x1="{x}" y1="{hip}" x2="{x - 17}" y2="{y}"/>',
        f'<line x1="{x}" y1="{hip}" x2="{x + 17}" y2="{y}"/>',
        "</g>",
    ]
    if actor_id == "system":
        parts.append(svg_text(x + 75, y - 50, label, size=14, weight="bold", anchor="start"))
    else:
        parts.append(svg_text(x, y + 22, label, size=14, weight="bold"))
    return "\n".join(parts)


def svg_arrow(x1, y1, x2, y2, label):
    ang = math.atan2(y2 - y1, x2 - x1)
    size = 11
    left = (x2 - size * math.cos(ang - 0.45), y2 - size * math.sin(ang - 0.45))
    right = (x2 - size * math.cos(ang + 0.45), y2 - size * math.sin(ang + 0.45))
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    lines = label.split("\n")
    box_w = max(len(s) for s in lines) * 7.2 + 12
    box_h = len(lines) * 16 + 6
    # Vertical arrows get the label beside the line, others centred on it.
    if abs(x2 - x1) < 20:
        lx, ly = mx + box_w / 2 + 8, my
    else:
        lx, ly = mx, my - box_h / 2 - 4
    return "\n".join(
        [
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            'stroke="#344054" stroke-width="1.8" stroke-dasharray="7 5"/>',
            f'<polyline points="{left[0]:.1f},{left[1]:.1f} {x2:.1f},{y2:.1f} '
            f'{right[0]:.1f},{right[1]:.1f}" fill="none" stroke="#344054" stroke-width="1.8"/>',
            f'<rect x="{lx - box_w / 2:.1f}" y="{ly - box_h / 2:.1f}" width="{box_w:.1f}" '
            f'height="{box_h:.1f}" fill="#FFFFFF" opacity="0.92" rx="3"/>',
            svg_text(lx, ly, label, size=12, weight="bold", fill="#344054"),
        ]
    )


def relation_points(relation):
    source, target, _, s_side, t_side = relation
    return side_point(source, s_side), side_point(target, t_side)


def render_svg():
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="{FONT}">',
        "<title>UML Use Case: фітнес-додаток (варіант 4)</title>",
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#FFFFFF"/>',
    ]
    bx, by, bw, bh = BOUNDARY
    out.append(
        f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="none" '
        'stroke="#101828" stroke-width="2"/>'
    )
    out.append(svg_text(bx + 14, by + 18, "Фітнес-додаток", size=16, weight="bold", anchor="start"))

    for _, title, x, y, w, h, fill in GROUPS:
        out.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" '
            'stroke="#98A2B3" stroke-dasharray="6 4"/>'
        )
        out.append(svg_text(x + 10, y + 14, title, size=12, weight="bold", anchor="start", fill="#475467"))

    for actor_id, uc_id in ASSOCIATIONS:
        a, p = association_points(actor_id, uc_id)
        out.append(
            f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{p[0]:.1f}" y2="{p[1]:.1f}" '
            'stroke="#667085" stroke-width="1.3"/>'
        )

    for uc_id, label, cx, cy in USE_CASES:
        w, h = uc_size(uc_id)
        out.append(
            f'<ellipse id="{uc_id}" cx="{cx}" cy="{cy}" rx="{w / 2}" ry="{h / 2}" '
            'fill="#FFFFFF" stroke="#344054" stroke-width="1.8"/>'
        )
        out.append(svg_text(cx, cy, f"{uc_id}\n{label}", size=12, weight="bold"))

    for relation in RELATIONS:
        (x1, y1), (x2, y2) = relation_points(relation)
        out.append(svg_arrow(x1, y1, x2, y2, relation[2]))

    for _, text, x, y, w, h in NOTES:
        fold = 12
        out.append(
            f'<path d="M{x},{y} h{w - fold} l{fold},{fold} v{h - fold} h{-w} z" '
            'fill="#FFFBE8" stroke="#B54708" stroke-width="1"/>'
        )
        out.append(svg_text(x + w / 2, y + h / 2, text, size=11, fill="#4B3B0A"))

    for actor_id, label, x, y in ACTORS:
        out.append(svg_actor(actor_id, label, x, y))

    lx, ly = 30, HEIGHT - 70
    out.append(
        f'<line x1="{lx}" y1="{ly}" x2="{lx + 50}" y2="{ly}" stroke="#667085" stroke-width="1.3"/>'
    )
    out.append(svg_text(lx + 60, ly, "асоціація актора з прецедентом", size=11, anchor="start", fill="#475467"))
    out.append(
        f'<line x1="{lx}" y1="{ly + 22}" x2="{lx + 50}" y2="{ly + 22}" stroke="#344054" '
        'stroke-width="1.8" stroke-dasharray="7 5"/>'
    )
    out.append(svg_text(lx + 60, ly + 22, "«include» / «extend»", size=11, anchor="start", fill="#475467"))
    out.append("</svg>")
    (ROOT / "use-case-diagram.svg").write_text("\n".join(out) + "\n", encoding="utf-8")


# ------------------------------------------------------------ draw.io output


def style(**kw):
    return ";".join(f"{k}={v}" for k, v in kw.items()) + ";"


def render_drawio():
    mxfile = ET.Element("mxfile", host="app.diagrams.net")
    diagram = ET.SubElement(mxfile, "diagram", id="use-cases", name="Use Case")
    model = ET.SubElement(
        diagram,
        "mxGraphModel",
        dx="1200",
        dy="900",
        grid="1",
        gridSize="10",
        page="1",
        pageWidth=str(WIDTH),
        pageHeight=str(HEIGHT),
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")

    def vertex(cell_id, value, st, x, y, w, h):
        cell = ET.SubElement(root, "mxCell", id=cell_id, value=value, style=st, vertex="1", parent="1")
        ET.SubElement(cell, "mxGeometry", x=f"{x:.0f}", y=f"{y:.0f}", width=f"{w:.0f}", height=f"{h:.0f}", **{"as": "geometry"})

    def edge(cell_id, source, target, st, value=""):
        cell = ET.SubElement(
            root, "mxCell", id=cell_id, value=value, style=st, edge="1", parent="1", source=source, target=target
        )
        ET.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})

    bx, by, bw, bh = BOUNDARY
    vertex(
        "boundary",
        "Фітнес-додаток",
        style(rounded="0", whiteSpace="wrap", html="1", fillColor="none", strokeColor="#101828",
              strokeWidth="2", verticalAlign="top", align="left", spacingLeft="12", fontStyle="1", fontSize="16"),
        bx, by, bw, bh,
    )
    for gid, title, x, y, w, h, fill in GROUPS:
        vertex(
            f"group-{gid}",
            title,
            style(rounded="1", arcSize="6", whiteSpace="wrap", html="1", fillColor=fill, strokeColor="#98A2B3",
                  dashed="1", verticalAlign="top", align="left", spacingLeft="10", fontStyle="1",
                  fontSize="12", fontColor="#475467"),
            x, y, w, h,
        )
    for uc_id, label, cx, cy in USE_CASES:
        w, h = uc_size(uc_id)
        vertex(
            uc_id,
            f"{uc_id}<br>{escape(label).replace(chr(10), '<br>')}",
            style(ellipse="1", whiteSpace="wrap", html="1", fillColor="#FFFFFF", strokeColor="#344054",
                  strokeWidth="2", fontStyle="1", fontSize="12"),
            cx - w / 2, cy - h / 2, w, h,
        )
    for nid, text, x, y, w, h in NOTES:
        vertex(
            nid,
            escape(text).replace("\n", "<br>"),
            style(shape="note", size="12", whiteSpace="wrap", html="1", fillColor="#FFFBE8",
                  strokeColor="#B54708", fontColor="#4B3B0A", fontSize="11"),
            x, y, w, h,
        )
    for actor_id, label, x, y in ACTORS:
        h = ACTOR_BODY["height"]
        label_pos = (
            style(labelPosition="right", verticalLabelPosition="middle", align="left", verticalAlign="middle")
            if actor_id == "system"
            else style(verticalLabelPosition="bottom", verticalAlign="top")
        )
        vertex(
            f"actor-{actor_id}",
            escape(label).replace("\n", "<br>"),
            "shape=umlActor;html=1;outlineConnect=0;fillColor=#FFFFFF;strokeColor=#101828;"
            "strokeWidth=2;fontStyle=1;fontSize=14;" + label_pos,
            x - 22, y - h, 44, h,
        )
    assoc = style(endArrow="none", html="1", strokeColor="#667085", strokeWidth="1.3")
    for i, (actor_id, uc_id) in enumerate(ASSOCIATIONS):
        edge(f"assoc-{i}", f"actor-{actor_id}", uc_id, assoc)
    rel = style(endArrow="open", endFill="0", dashed="1", html="1", strokeColor="#344054", strokeWidth="1.8",
                fontStyle="1", fontSize="12", labelBackgroundColor="#FFFFFF")
    for i, (source, target, label, _, _) in enumerate(RELATIONS):
        edge(f"rel-{i}", source, target, rel, escape(label).replace("\n", "<br>"))

    ET.indent(mxfile, space="  ")
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(mxfile, encoding="unicode") + "\n"
    (ROOT / "use-case-diagram.drawio").write_text(xml, encoding="utf-8")


def check_layout():
    """Fail loudly if an association line crosses a foreign ellipse."""
    problems = []
    for actor_id, uc_id in ASSOCIATIONS:
        a, p = association_points(actor_id, uc_id)
        for other, _, ox, oy in USE_CASES:
            if other == uc_id:
                continue
            w, h = uc_size(other)
            rx, ry = w / 2 + 4, h / 2 + 4
            for step in range(1, 100):
                t = step / 100
                x = a[0] + (p[0] - a[0]) * t
                y = a[1] + (p[1] - a[1]) * t
                if ((x - ox) / rx) ** 2 + ((y - oy) / ry) ** 2 < 1:
                    problems.append(f"{actor_id}->{uc_id} crosses {other}")
                    break
    for relation in RELATIONS:
        source, target = relation[0], relation[1]
        (x1, y1), (x2, y2) = relation_points(relation)
        for other, _, ox, oy in USE_CASES:
            if other in (source, target):
                continue
            w, h = uc_size(other)
            for step in range(1, 100):
                t = step / 100
                x, y = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
                if ((x - ox) / (w / 2 + 4)) ** 2 + ((y - oy) / (h / 2 + 4)) ** 2 < 1:
                    problems.append(f"{source}->{target} crosses {other}")
                    break
    return problems


if __name__ == "__main__":
    issues = check_layout()
    if issues:
        raise SystemExit("Layout problems:\n" + "\n".join(issues))
    render_svg()
    render_drawio()
    print("Створено use-case-diagram.svg і use-case-diagram.drawio")
