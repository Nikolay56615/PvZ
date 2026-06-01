from pathlib import Path

from build123d import *
from ocp_vscode import show


MM = 1.0

NAME = "wifi_relay_node"
EXPORT_DIR = Path(__file__).resolve().parent

WALL = 2.4 * MM
BOTTOM = 3.0 * MM
LID_TOP = 3.0 * MM
LIP_DEPTH = 6.0 * MM
LIP_CLEARANCE = 0.35 * MM
CORNER_RADIUS = 5.0 * MM
LIP_WALL = 2.0 * MM

INNER_LENGTH = 100.0 * MM
INNER_WIDTH = 55.0 * MM
INNER_HEIGHT = 30.0 * MM

LORA_ANTENNA_HOLE_DIAMETER = 10.0 * MM
LORA_ANTENNA_HOLE_CENTER = (0.0 * MM, BOTTOM + INNER_HEIGHT / 2)

USB_C_HOLE_WIDTH = 10.0 * MM
USB_C_HOLE_HEIGHT = 5.0 * MM
USB_C_HOLE_CENTER_Z = BOTTOM + USB_C_HOLE_HEIGHT / 2 + 1.0 * MM

BOSS_OUTER_DIAMETER = 6.0 * MM
BOSS_INNER_DIAMETER = 2.5 * MM
BOSS_HOLE_DEPTH = 14.0 * MM
BOSS_INSET = 2.5 * MM
BOSS_HEIGHT = INNER_HEIGHT
LID_SCREW_CLEARANCE = 3.4 * MM
BOSS_LID_CLEARANCE = 0.15 * MM
BOSS_LID_POCKET_DEPTH = 1.0 * MM


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


def boss_corners(z_center: float) -> tuple:
    bx = INNER_LENGTH / 2 - BOSS_INSET
    by = INNER_WIDTH / 2 - BOSS_INSET
    return (
        (bx, by, z_center),
        (bx, -by, z_center),
        (-bx, by, z_center),
        (-bx, -by, z_center),
    )


def boss_corners_xy() -> tuple:
    bx = INNER_LENGTH / 2 - BOSS_INSET
    by = INNER_WIDTH / 2 - BOSS_INSET
    return (
        (bx, by),
        (bx, -by),
        (-bx, by),
        (-bx, -by),
    )


def boss_relief_radius() -> float:
    return BOSS_OUTER_DIAMETER / 2 + LIP_CLEARANCE


def boss_patch_size() -> float:
    return BOSS_OUTER_DIAMETER + 2 * (LIP_CLEARANCE + WALL)


def boss_patch_round() -> float:
    return min(lip_inner_radius(), boss_patch_size() / 2 - 0.1 * MM)


def boss_patch_overlap_x() -> float:
    bx = INNER_LENGTH / 2 - BOSS_INSET
    return max(lip_inner_length() / 2 - bx, 0.0) + 0.25 * MM


def boss_patch_overlap_y() -> float:
    by = INNER_WIDTH / 2 - BOSS_INSET
    return max(lip_inner_width() / 2 - by, 0.0) + 0.25 * MM


def build_base() -> Part:
    wall_cut_depth = WALL + 2.0 * MM

    with BuildPart() as base:
        with BuildSketch():
            RectangleRounded(outer_length(), outer_width(), CORNER_RADIUS)
        extrude(amount=base_height())

        with BuildSketch(Plane.XY.offset(BOTTOM)):
            RectangleRounded(INNER_LENGTH, INNER_WIDTH, inner_corner_radius())
        extrude(amount=INNER_HEIGHT + 0.1 * MM, mode=Mode.SUBTRACT)

        with BuildPart(mode=Mode.SUBTRACT):
            with Locations(Location(
                (-INNER_LENGTH / 2 - WALL / 2,
                 LORA_ANTENNA_HOLE_CENTER[0],
                 LORA_ANTENNA_HOLE_CENTER[1]),
                (0, 90, 0),
            )):
                Cylinder(
                    radius=LORA_ANTENNA_HOLE_DIAMETER / 2,
                    height=wall_cut_depth,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )

        with BuildPart(mode=Mode.SUBTRACT):
            with Locations((INNER_LENGTH / 2 + WALL / 2, 0.0, USB_C_HOLE_CENTER_Z)):
                Box(
                    wall_cut_depth,
                    USB_C_HOLE_WIDTH,
                    USB_C_HOLE_HEIGHT,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )

        # Винтовые стойки по углам.
        with Locations(*boss_corners(BOTTOM + BOSS_HEIGHT / 2)):
            Cylinder(
                radius=BOSS_OUTER_DIAMETER / 2,
                height=BOSS_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )

        with BuildPart(mode=Mode.SUBTRACT):
            with Locations(*boss_corners(BOTTOM + BOSS_HEIGHT + 0.5 * MM - BOSS_HOLE_DEPTH / 2)):
                Cylinder(
                    radius=BOSS_INNER_DIAMETER / 2,
                    height=BOSS_HOLE_DEPTH + 1.0 * MM,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )

    return base.part


def build_lid() -> Part:
    relief_r = boss_relief_radius()
    patch_size = boss_patch_size()
    patch_round = boss_patch_round()
    overlap_x = boss_patch_overlap_x()
    overlap_y = boss_patch_overlap_y()

    with BuildPart() as lid:
        with BuildSketch():
            RectangleRounded(outer_length(), outer_width(), CORNER_RADIUS)
        extrude(amount=LID_TOP)

        # Губа крышки обходит угловые стойки.
        with BuildSketch(Plane.XY.offset(-LIP_DEPTH)):
            RectangleRounded(
                lip_outer_length(),
                lip_outer_width(),
                lip_outer_radius(),
            )
            RectangleRounded(
                lip_inner_length(),
                lip_inner_width(),
                lip_inner_radius(),
                mode=Mode.SUBTRACT,
            )
        extrude(amount=LIP_DEPTH)

        with BuildPart(mode=Mode.SUBTRACT):
            with Locations(*boss_corners(-LIP_DEPTH / 2)):
                Cylinder(
                    radius=relief_r,
                    height=LIP_DEPTH + 1.0 * MM,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )

        # Восстанавливаем материал губы вокруг вырезов под стойки.
        for x, y in boss_corners_xy():
            sx = 1 if x > 0 else -1
            sy = 1 if y > 0 else -1

            with BuildSketch(Plane.XY.offset(-LIP_DEPTH)) as boss_patch:
                with Locations((x, y)):
                    RectangleRounded(
                        patch_size,
                        patch_size,
                        patch_round,
                    )
                    Circle(relief_r, mode=Mode.SUBTRACT)

                RectangleRounded(
                    INNER_LENGTH,
                    INNER_WIDTH,
                    inner_corner_radius(),
                    mode=Mode.INTERSECT,
                )

                with Locations((
                    x - sx * (patch_size / 2 - overlap_x / 2),
                    y - sy * (patch_size / 2 - overlap_y / 2),
                )):
                    Rectangle(
                        patch_size + overlap_x,
                        patch_size + overlap_y,
                        mode=Mode.INTERSECT,
                    )

            if len(boss_patch.sketch.faces()) > 0:
                extrude(
                    to_extrude=boss_patch.sketch,
                    amount=LIP_DEPTH,
                    mode=Mode.ADD,
                )

        with BuildPart(mode=Mode.SUBTRACT):
            with Locations(*boss_corners(BOSS_LID_POCKET_DEPTH / 2)):
                Cylinder(
                    radius=BOSS_OUTER_DIAMETER / 2 + BOSS_LID_CLEARANCE,
                    height=BOSS_LID_POCKET_DEPTH,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )

        with BuildPart(mode=Mode.SUBTRACT):
            with Locations(*boss_corners((LID_TOP + BOSS_LID_POCKET_DEPTH) / 2)):
                Cylinder(
                    radius=LID_SCREW_CLEARANCE / 2,
                    height=LID_TOP + BOSS_LID_POCKET_DEPTH + 1.0 * MM,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )

    return lid.part


def export_parts(base: Part, lid: Part) -> None:
    export_stl(base, str(EXPORT_DIR / f"{NAME}_base.stl"))
    export_stl(lid, str(EXPORT_DIR / f"{NAME}_lid.stl"))


def main() -> None:
    base = build_base()
    lid = build_lid()
    export_parts(base, lid)

    lid_preview = lid.moved(Location((0, 0, base_height() + 4.0 * MM)))
    show(base, lid_preview, names=["base", "lid"], alphas=[1.0, 0.6])


if __name__ == "__main__":
    main()
