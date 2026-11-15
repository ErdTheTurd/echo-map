#!/usr/bin/env python3
"""
Compute a living-room floor plan and specular reflection paths (image-source
method), then write assets/hero-plan.svg with exact coordinates.

Room is a rectangle in meters. First-order images mirror the source across one
wall; second-order images mirror across two walls. Bounce points are found by
walking from the final image back to the listener, intersecting each wall.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

# --- Room geometry (meters) -------------------------------------------------
ROOM_W = 5.2
ROOM_H = 3.8
WALL_THICK_M = 0.12

# Source (speaker) and listener in room coordinates (meters from SW corner)
SOURCE = (1.15, 1.05)
LISTENER = (4.05, 2.85)

DOOR = {"center": 1.55, "width": 0.85}  # west wall, along +y from SW
WINDOW = {"center": 2.60, "width": 1.80}  # north wall, along +x from NW-ish

# Furniture (x, y, w, h) in meters — SW origin, +y north
SOFA = (0.35, 2.55, 2.40, 0.85)
COFFEE = (1.05, 1.55, 1.10, 0.55)
RUG = (0.70, 1.20, 2.40, 1.60)
BOOKSHELF = (4.55, 0.25, 0.40, 1.60)

# --- SVG layout -------------------------------------------------------------
VIEW_W = 1200
VIEW_H = 800
SCALE = 118.0  # px per meter
OX = (VIEW_W - ROOM_W * SCALE) / 2 + 40
OY = (VIEW_H - ROOM_H * SCALE) / 2 - 10

GRID = 24
HAIR = "rgba(220, 228, 236, 0.11)"
HAIR_DIM = "rgba(220, 228, 236, 0.09)"
HAIR_FURN = "rgba(220, 228, 236, 0.10)"
DIRECT = "#FFFFFF"
ORDER1 = "#5AC8C8"
ORDER2 = "#E8B04B"
MARKER = "rgba(230, 236, 242, 0.55)"
LABEL = "rgba(220, 228, 236, 0.38)"


def m2px(x: float, y: float) -> tuple[float, float]:
    """Room meters (origin SW, +x east, +y north) → SVG pixels (y down)."""
    return (OX + x * SCALE, OY + (ROOM_H - y) * SCALE)


def f(n: float) -> str:
    return f"{n:.2f}"


def mirror(pt: tuple[float, float], wall: str) -> tuple[float, float]:
    x, y = pt
    if wall == "west":
        return (-x, y)
    if wall == "east":
        return (2 * ROOM_W - x, y)
    if wall == "south":
        return (x, -y)
    if wall == "north":
        return (x, 2 * ROOM_H - y)
    raise ValueError(wall)


def wall_hit(
    p0: tuple[float, float],
    p1: tuple[float, float],
    wall: str,
) -> tuple[float, float] | None:
    """Intersection of line segment p0→p1 with a room wall (extended as segment)."""
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    eps = 1e-9
    if wall == "west":
        if abs(dx) < eps:
            return None
        t = (0.0 - x0) / dx
        y = y0 + t * dy
        if -eps <= t <= 1 + eps and -1e-6 <= y <= ROOM_H + 1e-6:
            return (0.0, max(0.0, min(ROOM_H, y)))
    elif wall == "east":
        if abs(dx) < eps:
            return None
        t = (ROOM_W - x0) / dx
        y = y0 + t * dy
        if -eps <= t <= 1 + eps and -1e-6 <= y <= ROOM_H + 1e-6:
            return (ROOM_W, max(0.0, min(ROOM_H, y)))
    elif wall == "south":
        if abs(dy) < eps:
            return None
        t = (0.0 - y0) / dy
        x = x0 + t * dx
        if -eps <= t <= 1 + eps and -1e-6 <= x <= ROOM_W + 1e-6:
            return (max(0.0, min(ROOM_W, x)), 0.0)
    elif wall == "north":
        if abs(dy) < eps:
            return None
        t = (ROOM_H - y0) / dy
        x = x0 + t * dx
        if -eps <= t <= 1 + eps and -1e-6 <= x <= ROOM_W + 1e-6:
            return (max(0.0, min(ROOM_W, x)), ROOM_H)
    return None


def unfold_path(
    src: tuple[float, float],
    lst: tuple[float, float],
    walls: list[str],
) -> list[tuple[float, float]] | None:
    """
    Polyline [src, bounce..., listener] for an ordered wall sequence via
    successive image sources. Bounce i is the hit of images[i]→next on walls[i-1].
    """
    if not walls:
        return [src, lst]

    images = [src]
    p = src
    for w in walls:
        p = mirror(p, w)
        images.append(p)

    path_rev = [lst]
    point = lst
    for i in range(len(walls), 0, -1):
        hit = wall_hit(images[i], point, walls[i - 1])
        if hit is None:
            return None
        path_rev.append(hit)
        point = hit
    path_rev.append(src)
    return list(reversed(path_rev))


def path_d(pts: list[tuple[float, float]]) -> str:
    parts = []
    for i, (x, y) in enumerate(pts):
        px, py = m2px(x, y)
        cmd = "M" if i == 0 else "L"
        parts.append(f"{cmd} {f(px)} {f(py)}")
    return " ".join(parts)


def tick_at(pt: tuple[float, float], wall: str, length_px: float = 5.0) -> str:
    x, y = m2px(*pt)
    half = length_px / 2
    if wall in ("west", "east"):
        return f"M {f(x - half)} {f(y)} L {f(x + half)} {f(y)}"
    return f"M {f(x)} {f(y - half)} L {f(x)} {f(y + half)}"


def dim_line(
    a: tuple[float, float],
    b: tuple[float, float],
    offset_px: float,
    label: str,
    horizontal: bool,
) -> tuple[str, dict]:
    ax, ay = m2px(*a)
    bx, by = m2px(*b)
    tick = 4.0
    if horizontal:
        ay = by = ay + offset_px
        d = (
            f"M {f(ax)} {f(ay - tick)} L {f(ax)} {f(ay + tick)} "
            f"M {f(ax)} {f(ay)} L {f(bx)} {f(by)} "
            f"M {f(bx)} {f(by - tick)} L {f(bx)} {f(by + tick)}"
        )
        tx, ty = (ax + bx) / 2, ay - 6
    else:
        ax = bx = ax + offset_px
        d = (
            f"M {f(ax - tick)} {f(ay)} L {f(ax + tick)} {f(ay)} "
            f"M {f(ax)} {f(ay)} L {f(bx)} {f(by)} "
            f"M {f(bx - tick)} {f(by)} L {f(bx + tick)} {f(by)}"
        )
        tx, ty = ax + 8, (ay + by) / 2
    return d, {"x": f(tx), "y": f(ty), "label": label}


def rect_path(x: float, y: float, w: float, h: float) -> str:
    p = [m2px(x, y), m2px(x + w, y), m2px(x + w, y + h), m2px(x, y + h)]
    return (
        f"M {f(p[0][0])} {f(p[0][1])} "
        f"L {f(p[1][0])} {f(p[1][1])} "
        f"L {f(p[2][0])} {f(p[2][1])} "
        f"L {f(p[3][0])} {f(p[3][1])} Z"
    )


def wall_outline() -> str:
    t = WALL_THICK_M
    ox0, oy0 = m2px(-t, -t)
    ox1, oy1 = m2px(ROOM_W + t, -t)
    ox2, oy2 = m2px(ROOM_W + t, ROOM_H + t)
    ox3, oy3 = m2px(-t, ROOM_H + t)
    ix0, iy0 = m2px(0, 0)
    ix1, iy1 = m2px(ROOM_W, 0)
    ix2, iy2 = m2px(ROOM_W, ROOM_H)
    ix3, iy3 = m2px(0, ROOM_H)
    outer = (
        f"M {f(ox0)} {f(oy0)} L {f(ox1)} {f(oy1)} "
        f"L {f(ox2)} {f(oy2)} L {f(ox3)} {f(oy3)} Z"
    )
    inner = (
        f"M {f(ix0)} {f(iy0)} L {f(ix1)} {f(iy1)} "
        f"L {f(ix2)} {f(iy2)} L {f(ix3)} {f(iy3)} Z"
    )
    return outer + " " + inner


def door_geometry() -> tuple[str, str]:
    c = DOOR["center"]
    half = DOOR["width"] / 2
    y0, y1 = c - half, c + half
    hinge = (0.0, y0)
    hx, hy = m2px(*hinge)
    r = DOOR["width"] * SCALE
    start = m2px(0.0, y0 + DOOR["width"])  # along wall (north)
    end = m2px(DOOR["width"], y0)  # into room (east)
    leaf_closed = f"M {f(hx)} {f(hy)} L {f(start[0])} {f(start[1])}"
    leaf_open = f"M {f(hx)} {f(hy)} L {f(end[0])} {f(end[1])}"
    # 90° arc: north → east is clockwise in SVG (y-down)
    arc = (
        f"M {f(start[0])} {f(start[1])} "
        f"A {f(r)} {f(r)} 0 0 1 {f(end[0])} {f(end[1])}"
    )
    t = WALL_THICK_M
    a0, a1 = m2px(-t, y0), m2px(0, y0)
    b0, b1 = m2px(-t, y1), m2px(0, y1)
    opening = (
        f"M {f(a0[0])} {f(a0[1])} L {f(a1[0])} {f(a1[1])} "
        f"M {f(b0[0])} {f(b0[1])} L {f(b1[0])} {f(b1[1])}"
    )
    return opening + " " + leaf_closed + " " + leaf_open, arc


def window_geometry() -> str:
    c = WINDOW["center"]
    half = WINDOW["width"] / 2
    x0, x1 = c - half, c + half
    t = WALL_THICK_M
    lines = []
    for frac in (0.25, 0.5, 0.75):
        yy = ROOM_H + t * frac
        p0, p1 = m2px(x0, yy), m2px(x1, yy)
        lines.append(f"M {f(p0[0])} {f(p0[1])} L {f(p1[0])} {f(p1[1])}")
    for x in (x0, x1):
        p0, p1 = m2px(x, ROOM_H), m2px(x, ROOM_H + t)
        lines.append(f"M {f(p0[0])} {f(p0[1])} L {f(p1[0])} {f(p1[1])}")
    return " ".join(lines)


def build_reflections() -> list[dict]:
    paths: list[dict] = []
    paths.append(
        {
            "order": 0,
            "walls": [],
            "pts": [SOURCE, LISTENER],
            "color": DIRECT,
            "cls": "ray ray--direct",
            "width": 1.35,
            "opacity": "0.85",
        }
    )
    for wall in ("north", "east", "south", "west"):
        pts = unfold_path(SOURCE, LISTENER, [wall])
        if pts and len(pts) == 3:
            paths.append(
                {
                    "order": 1,
                    "walls": [wall],
                    "pts": pts,
                    "color": ORDER1,
                    "cls": "ray ray--order1",
                    "width": 1.2,
                    "opacity": "0.72",
                }
            )
    # Ordered pairs that land on-wall for this source/listener (image-source).
    for pair in (
        ["west", "north"],
        ["north", "east"],
        ["south", "east"],
        ["west", "south"],
    ):
        pts = unfold_path(SOURCE, LISTENER, pair)
        if pts and len(pts) == 4:
            paths.append(
                {
                    "order": 2,
                    "walls": pair,
                    "pts": pts,
                    "color": ORDER2,
                    "cls": "ray ray--order2",
                    "width": 1.05,
                    "opacity": "0.55",
                }
            )
    return paths


def make_svg() -> ET.Element:
    svg = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": f"0 0 {VIEW_W} {VIEW_H}",
            "width": str(VIEW_W),
            "height": str(VIEW_H),
            "role": "img",
            "aria-label": (
                "Technical floor plan of a living room with computed "
                "specular reflection paths"
            ),
        },
    )
    title = ET.SubElement(svg, "title")
    title.text = "Living room floor plan with image-source reflection paths"

    grid = ET.SubElement(
        svg,
        "g",
        {
            "class": "grid",
            "stroke": "rgba(220,228,236,0.04)",
            "stroke-width": "1",
            "fill": "none",
        },
    )
    for x in range(0, VIEW_W + 1, GRID):
        ET.SubElement(
            grid, "line", {"x1": str(x), "y1": "0", "x2": str(x), "y2": str(VIEW_H)}
        )
    for y in range(0, VIEW_H + 1, GRID):
        ET.SubElement(
            grid, "line", {"x1": "0", "y1": str(y), "x2": str(VIEW_W), "y2": str(y)}
        )

    plan = ET.SubElement(svg, "g", {"class": "plan"})

    ET.SubElement(
        plan,
        "path",
        {
            "class": "walls",
            "d": wall_outline(),
            "fill": "none",
            "stroke": HAIR,
            "stroke-width": "1",
            "stroke-linejoin": "miter",
        },
    )

    door_d, arc_d = door_geometry()
    ET.SubElement(
        plan,
        "path",
        {
            "class": "door",
            "d": door_d,
            "fill": "none",
            "stroke": HAIR,
            "stroke-width": "1",
        },
    )
    ET.SubElement(
        plan,
        "path",
        {
            "class": "door-swing",
            "d": arc_d,
            "fill": "none",
            "stroke": HAIR_DIM,
            "stroke-width": "1",
            "stroke-dasharray": "3 3",
        },
    )
    ET.SubElement(
        plan,
        "path",
        {
            "class": "window",
            "d": window_geometry(),
            "fill": "none",
            "stroke": HAIR,
            "stroke-width": "1",
        },
    )

    furn = ET.SubElement(
        plan,
        "g",
        {
            "class": "furniture",
            "fill": "none",
            "stroke": HAIR_FURN,
            "stroke-width": "1",
        },
    )
    ET.SubElement(
        furn, "path", {"d": rect_path(*RUG), "stroke-dasharray": "4 3", "class": "rug"}
    )
    ET.SubElement(furn, "path", {"d": rect_path(*SOFA), "class": "sofa"})
    sx, sy, sw, sh = SOFA
    ET.SubElement(
        furn, "path", {"d": rect_path(sx, sy + sh - 0.22, sw, 0.22), "class": "sofa-back"}
    )
    ET.SubElement(furn, "path", {"d": rect_path(*COFFEE), "class": "coffee-table"})
    ET.SubElement(furn, "path", {"d": rect_path(*BOOKSHELF), "class": "bookshelf"})
    bx, by, bw, bh = BOOKSHELF
    for i in range(1, 4):
        yy = by + bh * i / 4
        p0, p1 = m2px(bx, yy), m2px(bx + bw, yy)
        ET.SubElement(
            furn,
            "line",
            {
                "x1": f(p0[0]),
                "y1": f(p0[1]),
                "x2": f(p1[0]),
                "y2": f(p1[1]),
                "class": "shelf",
            },
        )

    dims = ET.SubElement(
        plan,
        "g",
        {"class": "dims", "fill": "none", "stroke": HAIR_DIM, "stroke-width": "1"},
    )
    d_w, lab_w = dim_line((0, 0), (ROOM_W, 0), 28, f"{ROOM_W:.1f} m", True)
    ET.SubElement(dims, "path", {"d": d_w})
    d_h, lab_h = dim_line((ROOM_W, 0), (ROOM_W, ROOM_H), 28, f"{ROOM_H:.1f} m", False)
    ET.SubElement(dims, "path", {"d": d_h})

    labels = ET.SubElement(
        plan,
        "g",
        {
            "class": "dim-labels",
            "fill": LABEL,
            "font-family": "ui-monospace, 'SF Mono', Menlo, Consolas, monospace",
            "font-size": "10",
            "letter-spacing": "0.02em",
        },
    )
    tw = ET.SubElement(
        labels, "text", {"x": lab_w["x"], "y": lab_w["y"], "text-anchor": "middle"}
    )
    tw.text = lab_w["label"]
    th = ET.SubElement(
        labels,
        "text",
        {
            "x": lab_h["x"],
            "y": lab_h["y"],
            "text-anchor": "start",
            "dominant-baseline": "middle",
        },
    )
    th.text = lab_h["label"]

    rays_g = ET.SubElement(svg, "g", {"class": "rays"})
    ticks_g = ET.SubElement(
        svg, "g", {"class": "bounce-ticks", "fill": "none", "stroke-width": "1"}
    )
    for ray in build_reflections():
        ET.SubElement(
            rays_g,
            "path",
            {
                "class": ray["cls"],
                "d": path_d(ray["pts"]),
                "fill": "none",
                "stroke": ray["color"],
                "stroke-width": str(ray["width"]),
                "stroke-linecap": "round",
                "stroke-linejoin": "round",
                "opacity": ray["opacity"],
                "pathLength": "1",
            },
        )
        for i, wall in enumerate(ray["walls"]):
            bounce = ray["pts"][i + 1]
            ET.SubElement(
                ticks_g,
                "path",
                {"d": tick_at(bounce, wall), "stroke": ray["color"], "opacity": "0.7"},
            )

    markers = ET.SubElement(svg, "g", {"class": "markers"})
    sx, sy = m2px(*SOURCE)
    lx, ly = m2px(*LISTENER)
    s = 4.5
    ET.SubElement(
        markers,
        "rect",
        {
            "x": f(sx - s),
            "y": f(sy - s),
            "width": f(s * 2),
            "height": f(s * 2),
            "fill": "none",
            "stroke": MARKER,
            "stroke-width": "1.2",
        },
    )
    ET.SubElement(
        markers,
        "circle",
        {"cx": f(sx), "cy": f(sy), "r": "2", "fill": DIRECT, "opacity": "0.9"},
    )
    src_lab = ET.SubElement(
        markers,
        "text",
        {
            "x": f(sx + 10),
            "y": f(sy + 3),
            "fill": LABEL,
            "font-family": "ui-monospace, 'SF Mono', Menlo, Consolas, monospace",
            "font-size": "9",
        },
    )
    src_lab.text = "src"
    ET.SubElement(
        markers,
        "circle",
        {
            "cx": f(lx),
            "cy": f(ly),
            "r": "6",
            "fill": "none",
            "stroke": MARKER,
            "stroke-width": "1",
        },
    )
    ET.SubElement(
        markers,
        "circle",
        {"cx": f(lx), "cy": f(ly), "r": "2.2", "fill": ORDER1, "opacity": "0.95"},
    )
    lst_lab = ET.SubElement(
        markers,
        "text",
        {
            "x": f(lx + 10),
            "y": f(ly + 3),
            "fill": LABEL,
            "font-family": "ui-monospace, 'SF Mono', Menlo, Consolas, monospace",
            "font-size": "9",
        },
    )
    lst_lab.text = "lst"

    return svg


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "assets" / "hero-plan.svg"
    out.parent.mkdir(parents=True, exist_ok=True)

    svg = make_svg()
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(svg, encoding="unicode") + "\n"
    out.write_text(xml, encoding="utf-8")
    ET.parse(out)

    reflections = build_reflections()
    print(f"Wrote {out}")
    print(f"  room {ROOM_W} m × {ROOM_H} m")
    n0 = sum(1 for r in reflections if r["order"] == 0)
    n1 = sum(1 for r in reflections if r["order"] == 1)
    n2 = sum(1 for r in reflections if r["order"] == 2)
    print(f"  paths: {n0} direct, {n1} first-order, {n2} second-order")
    for r in reflections:
        walls = ",".join(r["walls"]) or "direct"
        coords = " → ".join(f"({p[0]:.2f},{p[1]:.2f})" for p in r["pts"])
        print(f"    order {r['order']} [{walls}]: {coords}")


if __name__ == "__main__":
    main()
