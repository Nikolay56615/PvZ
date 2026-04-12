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

HW390_SLOT_LENGTH = 4.2 * MM
HW390_SLOT_WIDTH = 23.5 * MM
HW390_SLOT_CENTER_Y = -20.0 * MM
HW390_SLOT_CENTER_Z = BOTTOM + INNER_HEIGHT / 2

DS18B20_HOLE_DIAMETER = 9.0 * MM
DS18B20_HOLE_CENTER_Y = 20.0 * MM
DS18B20_HOLE_CENTER_Z = BOTTOM + INNER_HEIGHT / 2

GPS_ANTENNA_RECESS_SIZE = 30.0 * MM
GPS_BAY_PUSH = 10.0 * MM
GPS_BAY_FILLET = 2.0 * MM
GPS_ANTENNA_RECESS_CENTER_Y = 20.0 * MM
GPS_ANTENNA_RECESS_CENTER_Z = BOTTOM + INNER_HEIGHT / 2

LORA_ANTENNA_HOLE_DIAMETER = 10.0 * MM
LORA_ANTENNA_HOLE_CENTER_Y = -20.0 * MM
LORA_ANTENNA_HOLE_CENTER_Z = BOTTOM + INNER_HEIGHT / 2

BOSS_OUTER_DIAMETER = 7.0 * MM
BOSS_INNER_DIAMETER = 2.5 * MM
BOSS_HOLE_DEPTH = 20.0 * MM
BOSS_INSET = 3.0 * MM
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
    return (bx, by, z_center), (bx, -by, z_center), (-bx, by, z_center), (-bx, -by, z_center)


def boss_relief_radius() -> float:
    return BOSS_OUTER_DIAMETER / 2 + LIP_CLEARANCE


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
            with Locations((-INNER_LENGTH / 2 - WALL / 2, HW390_SLOT_CENTER_Y, HW390_SLOT_CENTER_Z)):
                Box(
                    wall_cut_depth,
                    HW390_SLOT_LENGTH,
                    HW390_SLOT_WIDTH,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )

        with BuildPart(mode=Mode.SUBTRACT):
            with Locations(Location(
                (-INNER_LENGTH / 2 - WALL / 2, DS18B20_HOLE_CENTER_Y, DS18B20_HOLE_CENTER_Z),
                (0, 90, 0),
            )):
                Cylinder(
                    radius=DS18B20_HOLE_DIAMETER / 2,
                    height=wall_cut_depth,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )

        with BuildPart(mode=Mode.SUBTRACT):
            with Locations(Location(
                (INNER_LENGTH / 2 + WALL / 2, LORA_ANTENNA_HOLE_CENTER_Y, LORA_ANTENNA_HOLE_CENTER_Z),
                (0, 90, 0),
            )):
                Cylinder(
                    radius=LORA_ANTENNA_HOLE_DIAMETER / 2,
                    height=wall_cut_depth,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )

        gps_outer_x = outer_length() / 2
        gps_patch_center_x = gps_outer_x - GPS_BAY_PUSH + GPS_ANTENNA_RECESS_SIZE / 2
        gps_patch_center = (gps_patch_center_x, GPS_ANTENNA_RECESS_CENTER_Y)

        with BuildSketch(Plane.XY.offset(BOTTOM)) as gps_bay_profile:
            with Locations(gps_patch_center):
                RectangleRounded(
                    GPS_ANTENNA_RECESS_SIZE,
                    GPS_ANTENNA_RECESS_SIZE,
                    GPS_BAY_FILLET,
                )
                RectangleRounded(
                    GPS_ANTENNA_RECESS_SIZE - 2 * WALL,
                    GPS_ANTENNA_RECESS_SIZE - 2 * WALL,
                    max(GPS_BAY_FILLET - WALL, 0.5 * MM),
                    mode=Mode.SUBTRACT,
                )

            RectangleRounded(
                outer_length(),
                outer_width(),
                CORNER_RADIUS,
                mode=Mode.INTERSECT,
            )

        if len(gps_bay_profile.sketch.faces()) > 0:
            extrude(
                to_extrude=gps_bay_profile.sketch,
                amount=INNER_HEIGHT,
                mode=Mode.ADD,
            )

        with BuildPart(mode=Mode.SUBTRACT):
            with Locations((
                outer_length() / 2 - WALL / 2,
                GPS_ANTENNA_RECESS_CENTER_Y,
                BOTTOM + INNER_HEIGHT / 2,
            )):
                Box(
                    WALL + 0.2 * MM,
                    GPS_ANTENNA_RECESS_SIZE - 2 * WALL,
                    INNER_HEIGHT,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )

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

    with BuildPart() as lid:
        with BuildSketch():
            RectangleRounded(outer_length(), outer_width(), CORNER_RADIUS)
        extrude(amount=LID_TOP)

        with BuildSketch(Plane.XY.offset(-LIP_DEPTH)):
            RectangleRounded(lip_outer_length(), lip_outer_width(), lip_outer_radius())
            RectangleRounded(lip_inner_length(), lip_inner_width(), lip_inner_radius(), mode=Mode.SUBTRACT)
        extrude(amount=LIP_DEPTH)

        with BuildPart(mode=Mode.SUBTRACT):
            with Locations(*boss_corners(-LIP_DEPTH / 2)):
                Cylinder(
                    radius=relief_r,
                    height=LIP_DEPTH + 1.0 * MM,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
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

    lid_preview = lid.moved(Location((0, 0, base_height() + 4 * MM)))
    show(base, lid_preview, names=["base", "lid"], alphas=[1.0, 0.6])


if __name__ == "__main__":
    main()
