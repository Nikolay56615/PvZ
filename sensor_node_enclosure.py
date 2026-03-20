from pathlib import Path

from build123d import *
from ocp_vscode import show


MM = 1.0

NAME = "sensor_node_field"
EXPORT_DIR = Path(__file__).resolve().parent

WALL = 2.4 * MM
BOTTOM = 3.0 * MM
LID_TOP = 3.0 * MM
LIP_DEPTH = 6.0 * MM
LIP_CLEARANCE = 0.35 * MM
CORNER_RADIUS = 6.0 * MM
LIP_WALL = 2.0 * MM

INNER_LENGTH = 180.0 * MM
INNER_WIDTH = 100.0 * MM
INNER_HEIGHT = 50.0 * MM


def outer_length() -> float:
    return INNER_LENGTH + 2 * WALL


def outer_width() -> float:
    return INNER_WIDTH + 2 * WALL


def base_height() -> float:
    return INNER_HEIGHT + BOTTOM


def inner_corner_radius() -> float:
    return max(CORNER_RADIUS - WALL, 0.5 * MM)


def lip_outer_length() -> float:
    return INNER_LENGTH - 2 * LIP_CLEARANCE


def lip_outer_width() -> float:
    return INNER_WIDTH - 2 * LIP_CLEARANCE


def lip_outer_radius() -> float:
    return max(inner_corner_radius() - LIP_CLEARANCE, 0.5 * MM)


def lip_inner_length() -> float:
    return lip_outer_length() - 2 * LIP_WALL


def lip_inner_width() -> float:
    return lip_outer_width() - 2 * LIP_WALL


def lip_inner_radius() -> float:
    return max(lip_outer_radius() - LIP_WALL, 0.5 * MM)


def build_base() -> Part:
    with BuildPart() as base:
        with BuildSketch():
            RectangleRounded(outer_length(), outer_width(), CORNER_RADIUS)
        extrude(amount=base_height())

        with BuildSketch(Plane.XY.offset(BOTTOM)):
            RectangleRounded(INNER_LENGTH, INNER_WIDTH, inner_corner_radius())
        extrude(amount=INNER_HEIGHT + 0.1 * MM, mode=Mode.SUBTRACT)

    return base.part


def build_lid() -> Part:
    with BuildPart() as lid:
        with BuildSketch():
            RectangleRounded(outer_length(), outer_width(), CORNER_RADIUS)
        extrude(amount=LID_TOP)

        with BuildSketch(Plane.XY.offset(-LIP_DEPTH)):
            RectangleRounded(lip_outer_length(), lip_outer_width(), lip_outer_radius())
            RectangleRounded(lip_inner_length(), lip_inner_width(), lip_inner_radius(), mode=Mode.SUBTRACT)
        extrude(amount=LIP_DEPTH)

    return lid.part


def export_parts(base: Part, lid: Part) -> None:
    export_stl(base, str(EXPORT_DIR / f"{NAME}_base.stl"))
    export_stl(lid, str(EXPORT_DIR / f"{NAME}_lid.stl"))


def main() -> None:
    base = build_base()
    lid = build_lid()
    export_parts(base, lid)

    lid_preview = lid.moved(Location((0, 0, base_height() + 4 * MM)))
    show(base, lid_preview, names=["base", "lid"], alphas=[1.0, 0.6])


if __name__ == "__main__":
    main()
