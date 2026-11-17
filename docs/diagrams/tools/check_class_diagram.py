#!/usr/bin/env python3
"""Validate factual content and layout of the uncompressed class diagram."""

from __future__ import annotations

import ast
import html
import math
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DIAGRAM_PATH = REPOSITORY_ROOT / "docs/diagrams/class-diagram.drawio"
BACKEND_PATH = REPOSITORY_ROOT / "backend"

PATTERN_COLOURS = {
    "Strategy": ("#F8B4B4", "#B42318"),
    "Template Method": ("#FFE066", "#B08800"),
    "Observer": ("#8FE3A6", "#1E7B3C"),
}
MODULE_COLOURS = {
    "identity": ("#EAF2FF", "#345F9A"),
    "catalog": ("#E9F7F0", "#277450"),
    "planning": ("#FFF3E2", "#A96B17"),
    "execution": ("#FDEDF0", "#A84960"),
    "engagement": ("#F0EBFC", "#7051A1"),
    "reminders": ("#E6F6F8", "#287987"),
    "neutral": ("#F9FAFC", "#52606D"),
}
REQUIRED_GLOBAL_NAMES = {
    "AchievementCode",
    "AchievementEvaluator",
    "CalorieEstimate",
    "ChallengeParticipationService",
    "ChallengeProgressEvaluator",
    "LeaderboardQueryService",
    "PointsLedgerHandler",
    "ProgramCompletionEvaluation",
    "ReportAccess",
    "ReportQueryService",
    "StatisticsQueryService",
    "award_program_completion_bonus",
    "evaluate_program_completion",
}
REQUIRED_PAGE_04_NAMES = {
    "ChallengeAdmin",
    "ChallengeJoinView",
    "CompletedSessionCreateView",
    "LeaderboardView",
    "ProgramRecommendationView",
    "ScheduledSessionListCreateView",
    "StatisticsOverviewView",
    "UserAdmin",
    "WeightChartView",
    "WorkoutAdmin",
    "average_activity_report",
    "workout_popularity_report",
}
REQUIRED_MODEL_FIELDS = {
    "Achievement": {"code", "name", "rule_code", "is_archived"},
    "Challenge": {"start_at", "end_at", "goal_kind", "goal_value", "is_archived"},
    "Profile": {"gender", "height_cm", "weight_kg"},
    "User": {"email", "public_alias", "leaderboard_opt_in", "is_active"},
    "UserAchievement": {"name_snapshot", "rule_code_snapshot", "unlocked_at"},
}
REQUIRED_SERVICE_ENTITY_DEPENDENCIES = {
    ("ProgramSelectionService", "ProgramTemplate"),
    ("ProgramSelectionService", "UserProgram"),
    ("ProgramPlanningService", "ScheduledSession"),
    ("ReminderService", "Notification"),
    ("WorkoutCompletionService", "CompletedSession"),
    ("WorkoutCompletionService", "ExerciseResult"),
    ("WorkoutCompletionService", "ScheduledSession"),
    ("ChallengeParticipationService", "ChallengeParticipation"),
}
LEGEND_PHRASES = {
    "Роль GoF (заливка й товста рамка класу)",
    "Strategy — взаємозамінний вибір шаблону програми",
    "Template Method — спільний алгоритм перевірки результатів вправ",
    "Observer — реакції на завершення тренування",
    "Модуль (блідий фон блоку)",
    "Зв'язки",
    "association",
    "dependency",
    "inheritance/realization",
    "composition",
    "Кратності позначено біля кінців ребер",
}
CLASS_NAME_EXCEPTIONS = {"APIView", "AbstractBaseUser", "PermissionsMixin"}
FIELD_CALLS = {"ForeignKey", "OneToOneField", "ManyToManyField"}
MAX_BENDS = 3
MAX_EMPTY_HEIGHT_FRACTION = 0.55
MAX_EMPTY_HEIGHT_PIXELS = 60
TOP_TEXT_PADDING = 8
BOTTOM_TEXT_PADDING = 12
SEPARATOR_HEIGHT = 14
CLASS_LINE_HEIGHT = 1.3
ESTIMATED_CHARACTER_WIDTH = 0.6
HORIZONTAL_TEXT_PADDING = 16
TIGHT_CONTAINER_IDS = {
    "overview-gof",
    "overview-reminders",
    "cp-planning",
    "cp-reminders",
    "ee-observer-container",
    "ee-policy-container",
    "sg-completion",
}
PROHIBITED_NOTE_FRAGMENTS = {
    "Domain dependencies:",
    "Required handlers",
    "module containers",
    "Context ranks",
    "Completion policy",
    "WorkoutCompletionService dispatches",
    "unmanaged permission-only model",
}


@dataclass(frozen=True)
class Rectangle:
    cell_id: str
    name: str
    kind: str
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def overlaps(self, other: "Rectangle") -> bool:
        return (
            self.x < other.right
            and other.x < self.right
            and self.y < other.bottom
            and other.y < self.bottom
        )


@dataclass(frozen=True)
class BackendFacts:
    definitions: set[str]
    enum_members: dict[str, set[str]]
    model_fields: dict[str, set[str]]


def call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def backend_facts() -> BackendFacts:
    definitions: set[str] = set()
    enum_members: dict[str, set[str]] = {}
    model_fields: dict[str, set[str]] = {}
    for path in BACKEND_PATH.rglob("*.py"):
        relative_parts = path.relative_to(BACKEND_PATH).parts
        if any(part in {".venv", "migrations", "tests", "__pycache__"} for part in relative_parts):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                definitions.add(node.name)
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            bases = {call_name(base) for base in node.bases}
            if "TextChoices" in bases:
                enum_members[node.name] = {
                    target.id
                    for statement in node.body
                    if isinstance(statement, ast.Assign)
                    for target in statement.targets
                    if isinstance(target, ast.Name) and target.id.isupper()
                }
            if "Model" not in bases and "AbstractBaseUser" not in bases:
                continue
            fields = {"id", "pk"}
            for statement in node.body:
                if isinstance(statement, ast.Assign) and isinstance(statement.value, ast.Call):
                    assigned_name = call_name(statement.value.func)
                    if assigned_name.endswith("Field") or assigned_name in FIELD_CALLS:
                        for target in statement.targets:
                            if isinstance(target, ast.Name):
                                fields.add(target.id)
                if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if any(call_name(decorator) == "property" for decorator in statement.decorator_list):
                        fields.add(statement.name)
            model_fields[node.name] = fields
    return BackendFacts(definitions, enum_members, model_fields)


def style_properties(style: str) -> dict[str, str]:
    return {
        key: value
        for item in style.split(";")
        if "=" in item
        for key, value in [item.split("=", 1)]
    }


def html_lines(value: str) -> list[str]:
    normalized = re.sub(r"<hr\s*/?>", "<br>", value or "", flags=re.I)
    parts = re.split(r"<br\s*/?>", normalized, flags=re.I)
    return [html.unescape(re.sub(r"<[^>]+>", "", part)).strip() for part in parts]


def first_line(value: str) -> str:
    return next((line for line in html_lines(value) if line), "")


def stereotype(value: str) -> str:
    match = re.search(r"«([^»]+)»", html.unescape(value or ""))
    return match.group(1).strip() if match else ""


def detail_lines(value: str) -> list[str]:
    if not re.search(r"<hr\s*/?>", value or "", flags=re.I):
        return []
    details = re.split(r"<hr\s*/?>", value, maxsplit=1, flags=re.I)[1]
    return [line for line in html_lines(details) if line]


def rectangle(cell: ET.Element) -> Rectangle | None:
    geometry = cell.find("mxGeometry")
    if geometry is None:
        return None
    required = ("x", "y", "width", "height")
    if any(geometry.get(key) is None for key in required):
        return None
    return Rectangle(
        cell.get("id", "<missing-id>"),
        first_line(cell.get("value", "")),
        cell.get("data-kind", ""),
        float(geometry.get("x", "0")),
        float(geometry.get("y", "0")),
        float(geometry.get("width", "0")),
        float(geometry.get("height", "0")),
    )


def anchor(rect: Rectangle, x_ratio: float, y_ratio: float) -> tuple[float, float]:
    return (rect.x + rect.width * x_ratio, rect.y + rect.height * y_ratio)


def simplify_polyline(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for point in points:
        if result and math.isclose(point[0], result[-1][0]) and math.isclose(point[1], result[-1][1]):
            continue
        result.append(point)
        while len(result) >= 3:
            a, b, c = result[-3:]
            if not ((math.isclose(a[0], b[0]) and math.isclose(b[0], c[0])) or
                    (math.isclose(a[1], b[1]) and math.isclose(b[1], c[1]))):
                break
            result.pop(-2)
    return result


def segment_intersects_interior(start: tuple[float, float], end: tuple[float, float], rect: Rectangle) -> bool:
    """Liang-Barsky clipping against a slightly inset rectangle."""
    epsilon = 0.5
    xmin, xmax = rect.x + epsilon, rect.right - epsilon
    ymin, ymax = rect.y + epsilon, rect.bottom - epsilon
    if xmin >= xmax or ymin >= ymax:
        return False
    x0, y0 = start
    x1, y1 = end
    dx, dy = x1 - x0, y1 - y0
    p = (-dx, dx, -dy, dy)
    q = (x0 - xmin, xmax - x0, y0 - ymin, ymax - y0)
    u1, u2 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if math.isclose(pi, 0.0):
            if qi < 0:
                return False
            continue
        ratio = qi / pi
        if pi < 0:
            u1 = max(u1, ratio)
        else:
            u2 = min(u2, ratio)
        if u1 > u2:
            return False
    return u1 <= u2 and u2 >= 0 and u1 <= 1


def route_points(edge: ET.Element, boxes: dict[str, Rectangle]) -> list[tuple[float, float]]:
    source = boxes[edge.get("source", "")]
    target = boxes[edge.get("target", "")]
    style = style_properties(edge.get("style", ""))
    start = anchor(source, float(style.get("exitX", ".5")), float(style.get("exitY", ".5")))
    end = anchor(target, float(style.get("entryX", ".5")), float(style.get("entryY", ".5")))
    geometry = edge.find("mxGeometry")
    waypoints: list[tuple[float, float]] = []
    if geometry is not None:
        for point in geometry.findall("./Array[@as='points']/mxPoint"):
            if point.get("x") is not None and point.get("y") is not None:
                waypoints.append((float(point.get("x", "0")), float(point.get("y", "0"))))
    return simplify_polyline([start, *waypoints, end])


def estimated_content_height(cell: ET.Element, rect: Rectangle) -> float:
    style = style_properties(cell.get("style", ""))
    font_size = float(style.get("fontSize", "12"))
    spacing = float(style.get("spacing", "0" if rect.kind == "edge-label" else "8"))
    usable_width = max(20.0, rect.width - 2 * spacing)
    characters_per_line = max(8, int(usable_width / (font_size * ESTIMATED_CHARACTER_WIDTH)))
    value = cell.get("value", "")
    sections = re.split(r"<hr\s*/?>", value, maxsplit=1, flags=re.I)

    if rect.kind == "class":
        header_lines = [line for line in html_lines(sections[0]) if line]
        title_size_match = re.search(r"<b[^>]*font-size:(\d+(?:\.\d+)?)px", sections[0], flags=re.I)
        stereotype_size_match = re.search(r"<i[^>]*font-size:(\d+(?:\.\d+)?)px", sections[0], flags=re.I)
        title_size = float(title_size_match.group(1)) if title_size_match else font_size
        stereotype_size = float(stereotype_size_match.group(1)) if stereotype_size_match else font_size
        header_height = 0.0
        for index, line in enumerate(header_lines):
            line_size = title_size if index == 0 else stereotype_size
            chars_per_line = max(8, int(usable_width / (line_size * ESTIMATED_CHARACTER_WIDTH)))
            header_height += max(1, math.ceil(len(line) / chars_per_line)) * CLASS_LINE_HEIGHT * line_size
        detail_count = 0
        if len(sections) == 2:
            detail_count = sum(
                max(1, math.ceil(len(line) / characters_per_line))
                for line in html_lines(sections[1])
                if line
            )
        return (
            TOP_TEXT_PADDING
            + header_height
            + (SEPARATOR_HEIGHT if len(sections) == 2 else 0)
            + detail_count * CLASS_LINE_HEIGHT * font_size
            + BOTTOM_TEXT_PADDING
        )

    def wrapped_line_count(section: str) -> int:
        return sum(
            max(1, math.ceil(len(line) / characters_per_line))
            for line in html_lines(section)
            if line
        )

    # draw.io renders the class name and stereotype as header lines, then gives
    # the horizontal separator its own vertical slot before attributes/methods.
    rendered_lines = sum(wrapped_line_count(section) for section in sections)
    line_height = font_size * 1.25
    separator = SEPARATOR_HEIGHT if len(sections) == 2 else 0
    top_padding = 2 if rect.kind == "edge-label" else TOP_TEXT_PADDING
    bottom_padding = 2 if rect.kind == "edge-label" else BOTTOM_TEXT_PADDING
    return top_padding + rendered_lines * line_height + separator + bottom_padding


def estimated_content_width(cell: ET.Element) -> float:
    style = style_properties(cell.get("style", ""))
    font_size = float(style.get("fontSize", "12"))
    value = cell.get("value", "")
    sections = re.split(r"<hr\s*/?>", value, maxsplit=1, flags=re.I)
    title_size_match = re.search(r"<b[^>]*font-size:(\d+(?:\.\d+)?)px", sections[0], flags=re.I)
    stereotype_size_match = re.search(r"<i[^>]*font-size:(\d+(?:\.\d+)?)px", sections[0], flags=re.I)
    title_size = float(title_size_match.group(1)) if title_size_match else font_size
    stereotype_size = float(stereotype_size_match.group(1)) if stereotype_size_match else font_size
    candidates: list[float] = []
    header_lines = [line for line in html_lines(sections[0]) if line]
    for index, line in enumerate(header_lines):
        line_size = title_size if index == 0 else stereotype_size
        candidates.append(len(line) * line_size * ESTIMATED_CHARACTER_WIDTH)
    if len(sections) == 2:
        candidates.extend(
            len(line) * font_size * ESTIMATED_CHARACTER_WIDTH
            for line in html_lines(sections[1])
            if line
        )
    return max(candidates, default=0.0) + HORIZONTAL_TEXT_PADDING


def check() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    summaries: list[str] = []
    facts = backend_facts()
    try:
        document = ET.parse(DIAGRAM_PATH).getroot()
    except (OSError, ET.ParseError) as error:
        return [f"Cannot parse {DIAGRAM_PATH}: {error}"], summaries
    if document.get("compressed", "false").lower() == "true":
        errors.append("The draw.io file must remain uncompressed XML.")

    pages = document.findall("diagram")
    global_names: set[str] = set()
    shown_fields: dict[str, set[str]] = {}
    canonical_legend: tuple[object, ...] | None = None
    for page in pages:
        page_name = page.get("name", page.get("id", "<unnamed>"))
        model_root = page.find("./mxGraphModel/root")
        if model_root is None:
            errors.append(f"[{page_name}] missing mxGraphModel/root")
            continue
        cells = model_root.findall("mxCell")
        ids = [cell.get("id") for cell in cells]
        duplicates = {item for item in ids if ids.count(item) > 1}
        for duplicate in sorted(str(item) for item in duplicates):
            errors.append(f"[{page_name}] duplicate cell id: {duplicate}")
        existing_ids = {item for item in ids if item}
        boxes = {
            rect.cell_id: rect
            for cell in cells
            if cell.get("vertex") == "1" and (rect := rectangle(cell)) is not None
        }
        model = page.find("mxGraphModel")
        page_width = float(model.get("pageWidth", "0")) if model is not None else 0.0
        page_height = float(model.get("pageHeight", "0")) if model is not None else 0.0
        for rect in boxes.values():
            if rect.x < 0 or rect.y < 0 or rect.right > page_width or rect.bottom > page_height:
                errors.append(f"[{page_name}] box {rect.cell_id} falls outside the page bounds")

        class_count = enum_count = attribute_count = 0
        for cell in cells:
            if cell.get("vertex") != "1":
                continue
            kind = cell.get("data-kind", "")
            value = cell.get("value", "")
            name = first_line(value)
            rect = boxes.get(cell.get("id", ""))
            if kind == "class":
                class_count += 1
                global_names.add(name)
                if name not in facts.definitions and name not in CLASS_NAME_EXCEPTIONS:
                    errors.append(f"[{page_name}] unknown backend class/def in {cell.get('id')}: {name}")
                if stereotype(value) == "enum":
                    enum_count += 1
                    shown = set(detail_lines(value))
                    expected = facts.enum_members.get(name)
                    if expected is None:
                        errors.append(f"[{page_name}] enum box {name} is not a backend TextChoices class")
                    elif shown != expected:
                        errors.append(f"[{page_name}] enum {name} members mismatch: shown={sorted(shown)}, code={sorted(expected)}")
                if name in facts.model_fields:
                    for line in detail_lines(value):
                        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:", line)
                        if not match:
                            continue
                        attribute_count += 1
                        field_name = match.group(1)
                        shown_fields.setdefault(name, set()).add(field_name)
                        if field_name not in facts.model_fields[name]:
                            errors.append(f"[{page_name}] {name}.{field_name} is not a Django field/property")
                if rect is not None:
                    content_height = estimated_content_height(cell, rect)
                    if content_height > rect.height:
                        errors.append(
                            f"[{page_name}] class box {cell.get('id')} may clip wrapped text "
                            f"({content_height:.0f}px content in {rect.height:.0f}px box)"
                        )
                    empty_height = max(0.0, rect.height - content_height)
                    empty_fraction = empty_height / rect.height
                    if empty_fraction > MAX_EMPTY_HEIGHT_FRACTION and empty_height > MAX_EMPTY_HEIGHT_PIXELS:
                        errors.append(
                            f"[{page_name}] class box {cell.get('id')} is {empty_fraction:.0%} empty vertically "
                            f"({empty_height:.0f}px)"
                        )
                    content_width = estimated_content_width(cell)
                    if content_width > rect.width:
                        errors.append(
                            f"[{page_name}] class box {cell.get('id')} may clip horizontal text "
                            f"({content_width:.0f}px content in {rect.width:.0f}px box)"
                        )

            if kind in {"legend", "note", "title", "edge-label"} and rect is not None:
                content_height = estimated_content_height(cell, rect)
                if content_height > rect.height:
                    errors.append(
                        f"[{page_name}] {kind} box {cell.get('id')} may clip wrapped text "
                        f"({content_height:.0f}px content in {rect.height:.0f}px box)"
                    )

            if cell.get("data-legend-child") == "1":
                continue

            properties = style_properties(cell.get("style", ""))
            fill = properties.get("fillColor", "").upper()
            stroke = properties.get("strokeColor", "").upper()
            declared_pattern = cell.get("data-pattern")
            for pattern, (expected_fill, expected_stroke) in PATTERN_COLOURS.items():
                if (fill in {expected_fill, expected_stroke} or stroke in {expected_fill, expected_stroke}) and declared_pattern != pattern:
                    errors.append(f"[{page_name}] {cell.get('id')} uses {pattern} colour without participant role")
            if declared_pattern in PATTERN_COLOURS:
                if (fill, stroke) != PATTERN_COLOURS[declared_pattern]:
                    errors.append(f"[{page_name}] {cell.get('id')} has wrong {declared_pattern} colours")
                stroke_width = float(properties.get("strokeWidth", "0"))
                if not 2.5 <= stroke_width <= 3.0:
                    errors.append(f"[{page_name}] {cell.get('id')} must use a 2.5–3 px pattern border")
                if declared_pattern not in stereotype(value):
                    errors.append(f"[{page_name}] {cell.get('id')} lacks explicit {declared_pattern} stereotype tag")
            elif declared_pattern:
                errors.append(f"[{page_name}] {cell.get('id')} declares unknown pattern {declared_pattern}")

            declared_module = cell.get("data-module")
            if kind == "class":
                if declared_module not in MODULE_COLOURS:
                    errors.append(f"[{page_name}] {cell.get('id')} lacks a known data-module")
                elif not declared_pattern:
                    expected_stroke = MODULE_COLOURS[declared_module][1]
                    if fill != "#FFFFFF" or stroke != expected_stroke:
                        errors.append(
                            f"[{page_name}] {cell.get('id')} must be a white class box with {declared_module} border"
                        )
            if kind == "container":
                if declared_module not in MODULE_COLOURS:
                    errors.append(f"[{page_name}] {cell.get('id')} lacks a known container module")
                else:
                    expected_fill, expected_stroke = MODULE_COLOURS[declared_module]
                    if (fill, stroke) != (expected_fill, expected_stroke):
                        errors.append(f"[{page_name}] {cell.get('id')} has wrong module tint")
                    if properties.get("rounded") != "1":
                        errors.append(f"[{page_name}] {cell.get('id')} module container must be rounded")

        legends = [cell for cell in cells if cell.get("vertex") == "1" and cell.get("data-kind") == "legend"]
        if not legends:
            errors.append(f"[{page_name}] missing «Легенда» box")
        if len(legends) != 1:
            errors.append(f"[{page_name}] expected exactly one legend, found {len(legends)}")
        for legend in legends:
            legend_id = legend.get("id", "")
            legend_children = [cell for cell in cells if cell.get("parent") == legend_id]
            legend_raw = "\n".join(
                html.unescape((child.get("value") or "") + " " + (child.get("style") or ""))
                for child in legend_children
            )
            legend_value = "\n".join(
                line
                for child in legend_children
                for line in html_lines(child.get("value", ""))
            )
            for phrase in sorted(LEGEND_PHRASES):
                if phrase not in legend_value:
                    errors.append(f"[{page_name}] legend misses: {phrase}")
            for colour in {
                colour.upper()
                for pair in (*PATTERN_COLOURS.values(), *MODULE_COLOURS.values())
                for colour in pair
                if pair != MODULE_COLOURS["neutral"]
            }:
                if colour not in legend_raw.upper():
                    errors.append(f"[{page_name}] legend misses swatch {colour}")
            legend_rect = boxes.get(legend.get("id", ""))
            if legend_rect is not None:
                child_rects = [
                    boxes[child.get("id", "")]
                    for child in legend_children
                    if child.get("vertex") == "1" and child.get("id", "") in boxes
                ]
                for child_rect in child_rects:
                    if (
                        child_rect.x < 0
                        or child_rect.y < 0
                        or child_rect.right > legend_rect.width
                        or child_rect.bottom > legend_rect.height
                    ):
                        errors.append(f"[{page_name}] legend child {child_rect.cell_id} falls outside its container")
                for index, left in enumerate(child_rects):
                    for right in child_rects[index + 1:]:
                        if left.overlaps(right):
                            errors.append(
                                f"[{page_name}] overlapping legend children: {left.cell_id} and {right.cell_id}"
                            )
                child_rect_by_id = {rect.cell_id: rect for rect in child_rects}
                for child in legend_children:
                    child_id = child.get("id", "")
                    if child.get("data-kind") == "legend-swatch":
                        swatch = child_rect_by_id.get(child_id)
                        label = child_rect_by_id.get(child_id.removesuffix("-swatch") + "-label")
                        if swatch is None or swatch.width != 16 or swatch.height != 16:
                            errors.append(f"[{page_name}] legend swatch {child_id} must be 16×16px")
                        elif label is None or not math.isclose(
                            swatch.y + swatch.height / 2,
                            label.y + label.height / 2,
                        ):
                            errors.append(f"[{page_name}] legend swatch {child_id} is not centred with its label")
                    if child.get("data-kind") == "legend-edge":
                        geometry = child.find("mxGeometry")
                        source_point = geometry.find("mxPoint[@as='sourcePoint']") if geometry is not None else None
                        target_point = geometry.find("mxPoint[@as='targetPoint']") if geometry is not None else None
                        label = child_rect_by_id.get(child_id.removesuffix("-edge") + "-label")
                        if source_point is None or target_point is None:
                            errors.append(f"[{page_name}] legend relation {child_id} lacks explicit endpoints")
                        else:
                            source_x = float(source_point.get("x", "0"))
                            source_y = float(source_point.get("y", "0"))
                            target_x = float(target_point.get("x", "0"))
                            target_y = float(target_point.get("y", "0"))
                            if not math.isclose(target_x - source_x, 48.0) or not math.isclose(source_y, target_y):
                                errors.append(f"[{page_name}] legend relation {child_id} must be a 48px horizontal edge")
                            if label is None or not math.isclose(source_y, label.y + label.height / 2):
                                errors.append(f"[{page_name}] legend relation {child_id} is not centred with its label")
                if child_rects:
                    content_left = min(rect.x for rect in child_rects)
                    content_top = min(rect.y for rect in child_rects)
                    content_right = max(rect.right for rect in child_rects)
                    content_bottom = max(rect.bottom for rect in child_rects)
                    if legend_rect.width > (content_right - content_left) + 48:
                        errors.append(f"[{page_name}] legend is more than 24px wider per side than its content")
                    if legend_rect.height > (content_bottom - content_top) + 48:
                        errors.append(f"[{page_name}] legend is more than 24px taller per side than its content")
                child_signature = []
                for child in legend_children:
                    geometry = child.find("mxGeometry")
                    points = ()
                    if geometry is not None:
                        points = tuple(
                            (point.get("as"), point.get("x"), point.get("y"))
                            for point in geometry.findall("mxPoint")
                        )
                    child_signature.append(
                        (
                            child.get("data-kind", ""),
                            child.get("value", ""),
                            child.get("style", ""),
                            child.get("vertex", ""),
                            child.get("edge", ""),
                            geometry.get("x", "") if geometry is not None else "",
                            geometry.get("y", "") if geometry is not None else "",
                            geometry.get("width", "") if geometry is not None else "",
                            geometry.get("height", "") if geometry is not None else "",
                            points,
                        )
                    )
                legend_signature = (
                    legend.get("style", ""),
                    legend_rect.width,
                    legend_rect.height,
                    tuple(child_signature),
                )
                if canonical_legend is None:
                    canonical_legend = legend_signature
                elif legend_signature != canonical_legend:
                    errors.append(f"[{page_name}] legend content/style/size differs from page 01")

        containers = [rect for rect in boxes.values() if rect.kind == "container"]
        for index, left in enumerate(containers):
            for right in containers[index + 1:]:
                if left.overlaps(right):
                    errors.append(f"[{page_name}] overlapping module containers: {left.cell_id} and {right.cell_id}")

        for legend in [rect for rect in boxes.values() if rect.kind == "legend"]:
            for other in boxes.values():
                if other.cell_id == legend.cell_id or other.kind == "title":
                    continue
                if legend.overlaps(other):
                    errors.append(f"[{page_name}] legend {legend.cell_id} overlaps {other.cell_id}")

        for note in [cell for cell in cells if cell.get("data-kind") == "note"]:
            for fragment in sorted(PROHIBITED_NOTE_FRAGMENTS):
                if fragment in (note.get("value") or ""):
                    errors.append(f"[{page_name}] stale/English note fragment in {note.get('id')}: {fragment}")

        content_boxes = [
            rect
            for rect in boxes.values()
            if rect.kind not in {"container", "title", "edge-label", "legend"}
            and not rect.kind.startswith("legend-")
        ]
        for index, left in enumerate(content_boxes):
            for right in content_boxes[index + 1:]:
                if left.overlaps(right):
                    errors.append(f"[{page_name}] overlapping boxes: {left.cell_id} and {right.cell_id}")

        label_boxes = [rect for rect in boxes.values() if rect.kind == "edge-label"]
        vertex_obstacles = [
            rect
            for rect in boxes.values()
            if rect.kind not in {"container", "title", "edge-label", "legend"}
            and not rect.kind.startswith("legend-")
        ]
        for label in label_boxes:
            for obstacle in vertex_obstacles:
                if label.overlaps(obstacle):
                    errors.append(f"[{page_name}] edge label {label.cell_id} overlaps {obstacle.cell_id}")
        for index, left in enumerate(label_boxes):
            for right in label_boxes[index + 1:]:
                if left.overlaps(right):
                    errors.append(f"[{page_name}] edge labels overlap: {left.cell_id} and {right.cell_id}")

        for container in containers:
            if container.cell_id not in TIGHT_CONTAINER_IDS:
                continue
            contained = [
                rect
                for rect in boxes.values()
                if rect.kind not in {"container", "title", "legend", "edge-label"}
                and rect.x >= container.x
                and rect.right <= container.right
                and rect.y >= container.y
                and rect.bottom <= container.bottom
            ]
            if not contained:
                errors.append(f"[{page_name}] tight container {container.cell_id} has no content")
                continue
            bottom_padding = container.bottom - max(rect.bottom for rect in contained)
            if bottom_padding < 25 or bottom_padding > 45:
                errors.append(
                    f"[{page_name}] container {container.cell_id} bottom padding is {bottom_padding:.0f}px "
                    "(expected 25–45px)"
                )

        edge_count = 0
        dependency_pairs: set[tuple[str, str]] = set()
        for edge in cells:
            if edge.get("edge") != "1":
                continue
            if edge.get("data-kind") == "legend-edge":
                continue
            edge_count += 1
            source_id, target_id = edge.get("source"), edge.get("target")
            if not source_id or source_id not in existing_ids or not target_id or target_id not in existing_ids:
                errors.append(f"[{page_name}] edge {edge.get('id')} has missing source/target")
                continue
            if source_id not in boxes or target_id not in boxes:
                errors.append(f"[{page_name}] edge {edge.get('id')} endpoint lacks geometry")
                continue
            route = route_points(edge, boxes)
            dependency_pairs.add((boxes[source_id].name, boxes[target_id].name))
            bends = max(0, len(route) - 2)
            if bends > MAX_BENDS:
                errors.append(f"[{page_name}] edge {edge.get('id')} has {bends} bends (max {MAX_BENDS})")
            for obstacle in vertex_obstacles:
                if obstacle.cell_id in {source_id, target_id}:
                    continue
                if any(segment_intersects_interior(start, end, obstacle) for start, end in zip(route, route[1:])):
                    errors.append(f"[{page_name}] edge {edge.get('id')} crosses {obstacle.cell_id}")

        if page.get("id") == "services-gof":
            names = {rect.name for rect in boxes.values() if rect.kind == "class"}
            for missing in sorted(REQUIRED_PAGE_04_NAMES - names):
                errors.append(f"[{page_name}] missing real view/admin/function: {missing}")
            for pair in sorted(REQUIRED_SERVICE_ENTITY_DEPENDENCIES - dependency_pairs):
                errors.append(f"[{page_name}] missing service → entity dependency: {pair[0]} → {pair[1]}")

        summaries.append(
            f"{page_name}: {class_count} class/function boxes, {enum_count} enums, "
            f"{attribute_count} checked model attributes, {edge_count} edges, {len(legends)} legend"
        )

    if len(pages) != 4:
        errors.append(f"Expected 4 pages, found {len(pages)}")
    for missing in sorted(REQUIRED_GLOBAL_NAMES - global_names):
        errors.append(f"Missing required class/function across diagram: {missing}")
    if "NotificationHandler" in global_names:
        errors.append("Removed class NotificationHandler is still shown")
    all_values = "\n".join(cell.get("value", "") for cell in document.findall(".//mxCell"))
    if "register(handler, required)" not in all_values:
        errors.append("Observer API register(handler, required) is not shown")
    for model_name, required_fields in REQUIRED_MODEL_FIELDS.items():
        missing_fields = required_fields - shown_fields.get(model_name, set())
        for field_name in sorted(missing_fields):
            errors.append(f"Required ERD attribute is not shown: {model_name}.{field_name}")
    return errors, summaries


def main() -> int:
    errors, summaries = check()
    if errors:
        print(f"FAIL: {len(errors)} class-diagram issue(s)")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"OK: {len(summaries)} pages validated")
    for summary in summaries:
        print(f"- {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
