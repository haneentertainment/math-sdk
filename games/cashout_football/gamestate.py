"""Handles the state and output for a single simulation round"""

from game_override import GameStateOverride
import random
import math

from src.events.event_constants import EventConstants

class GameState(GameStateOverride):
    """Handle all game-logic and event updates for a given simulation number."""

    # ── ENUMS & CONSTANTS ────────────────────────────────────────
    ZONES = [
        "DEEP_L",
        "DEEP_MID",
        "DEEP_R",
        "SHORT_L",
        "SHORT_MID",
        "SHORT_R",
        "SCRAMBLE",
    ]

    OUTCOMES = [
        "SACKED",
        "INCOMPLETE",
        "INTERCEPTION",
        "FUMBLE",
        "SHORT_GAIN",
        "MEDIUM_GAIN",
        "LONG_GAIN",
        "BIG_PLAY",
        "BREAKAWAY",
        "TOUCHDOWN",
    ]

    MULTIPLIERS = {
        "DEEP_MID": {
            "SACKED": 0, "INCOMPLETE": 0, "INTERCEPTION": 0, "FUMBLE": 0.1,
            "SHORT_GAIN": 0.1, "MEDIUM_GAIN": 0.5, "LONG_GAIN": 2,
            "BIG_PLAY": 25, "BREAKAWAY": 500, "TOUCHDOWN": 50000,
        },
        "DEEP_L": {
            "SACKED": 0, "INCOMPLETE": 0, "INTERCEPTION": 0, "FUMBLE": 0.1,
            "SHORT_GAIN": 0.1, "MEDIUM_GAIN": 2, "LONG_GAIN": 10,
            "BIG_PLAY": 25, "BREAKAWAY": 500, "TOUCHDOWN": 10000,
        },
        "DEEP_R": {
            "SACKED": 0, "INCOMPLETE": 0, "INTERCEPTION": 0, "FUMBLE": 0.1,
            "SHORT_GAIN": 0.1, "MEDIUM_GAIN": 2, "LONG_GAIN": 10,
            "BIG_PLAY": 25, "BREAKAWAY": 500, "TOUCHDOWN": 10000,
        },
        "SHORT_MID": {
            "SACKED": 0, "INCOMPLETE": 0, "INTERCEPTION": 0, "FUMBLE": 0.8,
            "SHORT_GAIN": 0.8, "MEDIUM_GAIN": 1.5, "LONG_GAIN": 5,
            "BIG_PLAY": 25, "BREAKAWAY": 500, "TOUCHDOWN": 5000,
        },
        "SHORT_L": {
            "SACKED": 0, "INCOMPLETE": 0.2, "INTERCEPTION": 0.2, "FUMBLE": 0.2,
            "SHORT_GAIN": 2, "MEDIUM_GAIN": 4, "LONG_GAIN": 10,
            "BIG_PLAY": 25, "BREAKAWAY": 130, "TOUCHDOWN": 1000,
        },
        "SHORT_R": {
            "SACKED": 0, "INCOMPLETE": 0.2, "INTERCEPTION": 0.2, "FUMBLE": 0.2,
            "SHORT_GAIN": 2, "MEDIUM_GAIN": 4, "LONG_GAIN": 10,
            "BIG_PLAY": 25, "BREAKAWAY": 130, "TOUCHDOWN": 1000,
        },
        "SCRAMBLE": {
            "SACKED": 0, "INCOMPLETE": 0.5, "INTERCEPTION": 0.5, "FUMBLE": 0.5,
            "SHORT_GAIN": 1.1, "MEDIUM_GAIN": 2, "LONG_GAIN": 5,
            "BIG_PLAY": 10, "BREAKAWAY": 40, "TOUCHDOWN": 150,
        },
    }

    YARD_RANGES = {
        "SACKED": (-10, -1),
        "INCOMPLETE": (0, 0),
        "INTERCEPTION": (0, 0),
        "FUMBLE": (1, 20),
        "SHORT_GAIN": (1, 5),
        "MEDIUM_GAIN": (6, 15),
        "LONG_GAIN": (16, 30),
        "BIG_PLAY": (31, 50),
        "BREAKAWAY": (51, 75),
        "TOUCHDOWN": (20, 75),
    }

    # ── FIELD ────────────────────────────────────────────────────
    # Top-down coordinate system:
    #   x = downfield (positive toward opponent end zone)
    #   y = lateral (negative = left, positive = right)
    #   Origin (0,0) = center of line of scrimmage
    FIELD_HALF_WIDTH = 26.67

    # ── ZONE CONFIGS ─────────────────────────────────────────────
    ZONE_CONFIG = {
        "DEEP_L":    {"depth_min": 20, "depth_max": 50, "lat_min": -25, "lat_max": -8},
        "DEEP_MID":  {"depth_min": 20, "depth_max": 50, "lat_min": -8,  "lat_max": 8},
        "DEEP_R":    {"depth_min": 20, "depth_max": 50, "lat_min": 8,   "lat_max": 25},
        "SHORT_L":   {"depth_min": 3,  "depth_max": 18, "lat_min": -25, "lat_max": -5},
        "SHORT_MID": {"depth_min": 3,  "depth_max": 18, "lat_min": -8,  "lat_max": 8},
        "SHORT_R":   {"depth_min": 3,  "depth_max": 18, "lat_min": 5,   "lat_max": 25},
        "SCRAMBLE":  {"depth_min": 0,  "depth_max": 0,  "lat_min": 0,   "lat_max": 0},
    }

    # ── HELPERS ──────────────────────────────────────────────────
    def rand(self):
        return random.random()

    def rand_between(self, min_val, max_val):
        return min_val + self.rand() * (max_val - min_val)

    def rand_int(self, min_val, max_val):
        return round(self.rand_between(min_val, max_val))

    def clamp_y(self, y):
        return max(-self.FIELD_HALF_WIDTH, min(self.FIELD_HALF_WIDTH, y))

    def jitter(self, value, amount):
        return value + self.rand_between(-amount, amount)

    def round_pos(self, pos):
        return {"x": round(pos["x"] * 10) / 10, "y": round(self.clamp_y(pos["y"]) * 10) / 10}

    def lerp(self, a, b, t):
        return {"x": a["x"] + (b["x"] - a["x"]) * t, "y": a["y"] + (b["y"] - a["y"]) * t}

    NUM_FRAMES = 9

    def build_path(self, waypoints):
        """Given {frame_index: position} dict, linearly interpolate to fill NUM_FRAMES frames."""
        path = [None] * self.NUM_FRAMES
        for idx, pos in waypoints.items():
            path[idx] = {"x": pos["x"], "y": pos["y"]}

        set_indices = sorted(waypoints.keys())

        # Fill before first keyframe
        for i in range(set_indices[0]):
            path[i] = {"x": path[set_indices[0]]["x"], "y": path[set_indices[0]]["y"]}

        # Fill after last keyframe
        for i in range(set_indices[-1] + 1, self.NUM_FRAMES):
            path[i] = {"x": path[set_indices[-1]]["x"], "y": path[set_indices[-1]]["y"]}

        # Interpolate between keyframes
        for k in range(len(set_indices) - 1):
            a_idx = set_indices[k]
            b_idx = set_indices[k + 1]
            for i in range(a_idx + 1, b_idx):
                t = (i - a_idx) / (b_idx - a_idx)
                path[i] = self.lerp(path[a_idx], path[b_idx], t)

        return path

    # ── STARTING POSITIONS (PRE-SNAP) ────────────────────────────
    def get_start_positions(self):
        return {
            "QB":   {"x": -5,   "y": 0},
            "C":    {"x": 0,    "y": 0},
            "LG":   {"x": 0,    "y": -2},
            "RG":   {"x": 0,    "y": 2},
            "LT":   {"x": 0,    "y": -4.5},
            "RT":   {"x": 0,    "y": 4.5},
            "WR1":  {"x": 0,    "y": -23},
            "WR2":  {"x": 0,    "y": 23},
            "SLOT": {"x": 0,    "y": -12},
            "TE":   {"x": 0,    "y": 6.5},
            "RB":   {"x": -7,   "y": 1.5},
            "LDE":  {"x": 1,    "y": -5},
            "LDT":  {"x": 1,    "y": -1.5},
            "RDT":  {"x": 1,    "y": 1.5},
            "RDE":  {"x": 1,    "y": 5},
            "LOLB": {"x": 3,    "y": -8},
            "MLB":  {"x": 4,    "y": 0},
            "ROLB": {"x": 3,    "y": 8},
            "CB1":  {"x": 1,    "y": -24},
            "CB2":  {"x": 1,    "y": 24},
            "FS":   {"x": 15,   "y": -5},
            "SS":   {"x": 12,   "y": 5},
        }

    # ── WHICH PLAYERS ARE INVOLVED PER ZONE ──────────────────────
    ZONE_PRIMARY_RECEIVER = {
        "DEEP_L": "WR1", "DEEP_MID": "SLOT", "DEEP_R": "WR2",
        "SHORT_L": "WR1", "SHORT_MID": "SLOT", "SHORT_R": "TE",
        "SCRAMBLE": "QB",
    }

    ZONE_PRIMARY_DEFENDER = {
        "DEEP_L": "CB1", "DEEP_MID": "FS", "DEEP_R": "CB2",
        "SHORT_L": "CB1", "SHORT_MID": "MLB", "SHORT_R": "SS",
        "SCRAMBLE": "LDE",
    }

    COVERAGE_MAP = {
        "CB1": "WR1", "CB2": "WR2", "SS": "TE", "FS": "SLOT",
        "LOLB": None, "MLB": None, "ROLB": None,
    }

    # ── OUTCOME GENERATOR ────────────────────────────────────────
    def generate_outcome(self, zone):
        valid_outcomes = list(self.OUTCOMES)
        if zone == "SCRAMBLE":
            valid_outcomes = [o for o in valid_outcomes if o not in ("INCOMPLETE", "INTERCEPTION")]
        index = math.floor(self.rand() * len(valid_outcomes))
        outcome = valid_outcomes[index]
        return {"outcome": outcome, "multiplier": self.MULTIPLIERS[zone][outcome]}

    def generate_yards(self, outcome):
        min_val, max_val = self.YARD_RANGES[outcome]
        if min_val == max_val:
            return min_val
        return self.rand_int(min_val, max_val)
    
    # ── POSITION GENERATION (9 keyframes per player) ──────────────
    # Frame timing:
    #   0: Pre-snap lineup
    #   1: Snap / initial burst
    #   2: Routes developing / pass rush starting
    #   3: Routes breaking / QB scanning
    #   4: Ball release (throw) or scramble break
    #   5: Ball in air / players reacting
    #   6: Catch point / ball arrival
    #   7: YAC / tackle / play continuing
    #   8: Final position

    def generate_positions(self, zone, outcome, yards):
        start = self.get_start_positions()
        paths = {}

        primary_wr = self.ZONE_PRIMARY_RECEIVER[zone]
        primary_def = self.ZONE_PRIMARY_DEFENDER[zone]
        is_scramble = zone == "SCRAMBLE"
        is_sack = outcome == "SACKED"
        is_catch = outcome in ("SHORT_GAIN", "MEDIUM_GAIN", "LONG_GAIN", "BIG_PLAY", "BREAKAWAY", "TOUCHDOWN")
        is_int = outcome == "INTERCEPTION"
        is_fumble = outcome == "FUMBLE"
        is_big_gain = outcome in ("BIG_PLAY", "BREAKAWAY", "TOUCHDOWN")

        # Where the receiver is heading
        target_point = None
        ball_landing = None

        if not is_scramble:
            cfg = self.ZONE_CONFIG[zone]
            target_point = {
                "x": self.rand_between(cfg["depth_min"], cfg["depth_max"]),
                "y": self.clamp_y(self.rand_between(cfg["lat_min"], cfg["lat_max"])),
            }
            is_accurate = is_catch or is_fumble
            miss_radius = self.rand_between(0, 1.5) if is_accurate else self.rand_between(3, 10)
            miss_angle = self.rand() * 2 * math.pi
            ball_landing = {
                "x": target_point["x"] + math.cos(miss_angle) * miss_radius,
                "y": self.clamp_y(target_point["y"] + math.sin(miss_angle) * miss_radius),
            }

        # ── QB PATH ──
        qb = start["QB"]
        if is_scramble:
            scramble_dir = self.rand_between(-15, 15)
            qb_end = {"x": qb["x"] + yards, "y": self.clamp_y(scramble_dir)}
            if is_sack:
                paths["QB"] = self.build_path({
                    0: qb,
                    1: {"x": qb["x"] - 1, "y": self.jitter(0, 0.5)},
                    2: {"x": qb["x"] - 2, "y": self.jitter(0, 1)},
                    3: {"x": qb["x"] - 1, "y": scramble_dir * 0.2},
                    4: {"x": qb["x"], "y": scramble_dir * 0.3},
                    5: {"x": qb["x"] + yards * 0.3, "y": scramble_dir * 0.5},
                    6: {"x": qb["x"] + yards * 0.6, "y": scramble_dir * 0.7},
                    7: qb_end,
                    8: qb_end,
                })
            else:
                paths["QB"] = self.build_path({
                    0: qb,
                    1: {"x": qb["x"] - 1, "y": self.jitter(0, 0.5)},
                    2: {"x": qb["x"] - 2, "y": self.jitter(0, 1)},
                    3: {"x": qb["x"] - 1, "y": scramble_dir * 0.15},
                    4: {"x": qb["x"] + yards * 0.1, "y": scramble_dir * 0.3},
                    5: {"x": qb["x"] + yards * 0.3, "y": scramble_dir * 0.5},
                    6: {"x": qb["x"] + yards * 0.55, "y": scramble_dir * 0.7},
                    7: {"x": qb["x"] + yards * 0.8, "y": scramble_dir * 0.9},
                    8: qb_end,
                })
        elif is_sack:
            sack_end = {"x": qb["x"] + yards, "y": self.jitter(0, 3)}
            paths["QB"] = self.build_path({
                0: qb,
                1: {"x": qb["x"] - 1, "y": self.jitter(0, 0.3)},
                2: {"x": qb["x"] - 3, "y": self.jitter(0, 1)},
                3: {"x": qb["x"] - 4, "y": self.jitter(0, 1.5)},
                4: {"x": qb["x"] - 3, "y": self.jitter(0, 2)},
                5: {"x": qb["x"] - 2, "y": self.jitter(0, 2)},
                6: sack_end,
                7: sack_end,
                8: sack_end,
            })
        else:
            drop_depth = self.rand_between(2, 5)
            pocket_drift = self.jitter(0, 1.5)
            qb_throw = {"x": qb["x"] - drop_depth, "y": pocket_drift}
            qb_after = {"x": qb_throw["x"] + self.rand_between(0, 2), "y": self.jitter(pocket_drift, 1)}
            paths["QB"] = self.build_path({
                0: qb,
                1: {"x": qb["x"] - 1, "y": self.jitter(0, 0.3)},
                2: {"x": qb["x"] - drop_depth * 0.6, "y": pocket_drift * 0.3},
                3: {"x": qb["x"] - drop_depth * 0.9, "y": pocket_drift * 0.7},
                4: qb_throw,
                5: qb_after,
                8: {"x": qb_after["x"] + self.rand_between(-1, 1), "y": self.jitter(qb_after["y"], 0.5)},
            })

        # ── PRIMARY RECEIVER (pass plays) ──
        if not is_scramble:
            wr_s = start[primary_wr]
            release_pt = {
                "x": wr_s["x"] + self.rand_between(2, 5),
                "y": wr_s["y"] + (target_point["y"] - wr_s["y"]) * 0.15,
            }
            route_mid = {
                "x": wr_s["x"] + (target_point["x"] - wr_s["x"]) * 0.5 + self.rand_between(-2, 2),
                "y": self.clamp_y(wr_s["y"] + (target_point["y"] - wr_s["y"]) * 0.4 + self.rand_between(-1, 1)),
            }
            route_break = {
                "x": target_point["x"] * 0.85,
                "y": self.clamp_y(target_point["y"] + self.rand_between(-1, 1)),
            }

            if is_catch:
                yac = max(0, yards - target_point["x"])
                catch_pt = {"x": target_point["x"], "y": target_point["y"]}
                if is_big_gain:
                    run_angle = self.rand_between(-0.3, 0.3)
                    final = {
                        "x": target_point["x"] + yac,
                        "y": self.clamp_y(target_point["y"] + yac * math.sin(run_angle)),
                    }
                    paths[primary_wr] = self.build_path({
                        0: wr_s,
                        1: release_pt,
                        2: {"x": release_pt["x"] + 3, "y": self.clamp_y(release_pt["y"] + (route_mid["y"] - release_pt["y"]) * 0.5)},
                        3: route_mid,
                        4: route_break,
                        5: {"x": target_point["x"] * 0.95, "y": self.clamp_y(target_point["y"])},
                        6: catch_pt,
                        7: self.lerp(catch_pt, final, 0.5),
                        8: final,
                    })
                else:
                    final = {
                        "x": target_point["x"] + yac,
                        "y": self.clamp_y(target_point["y"] + self.rand_between(-2, 2)),
                    }
                    paths[primary_wr] = self.build_path({
                        0: wr_s,
                        1: release_pt,
                        3: route_mid,
                        4: route_break,
                        6: catch_pt,
                        7: final,
                        8: final,
                    })
            elif is_fumble:
                fumble_pt = {
                    "x": target_point["x"] + self.rand_between(1, 4),
                    "y": self.clamp_y(target_point["y"] + self.rand_between(-2, 2)),
                }
                paths[primary_wr] = self.build_path({
                    0: wr_s,
                    1: release_pt,
                    3: route_mid,
                    4: route_break,
                    6: target_point,
                    7: fumble_pt,
                    8: {"x": fumble_pt["x"] + self.rand_between(-1, 2), "y": self.clamp_y(fumble_pt["y"] + self.rand_between(-2, 2))},
                })
            elif is_int:
                paths[primary_wr] = self.build_path({
                    0: wr_s,
                    1: release_pt,
                    3: route_mid,
                    4: route_break,
                    6: target_point,
                    7: {"x": target_point["x"] + self.rand_between(1, 3), "y": self.clamp_y(target_point["y"] + self.rand_between(-2, 2))},
                    8: {"x": target_point["x"] + self.rand_between(2, 5), "y": self.clamp_y(target_point["y"] + self.rand_between(-3, 3))},
                })
            elif is_sack:
                paths[primary_wr] = self.build_path({
                    0: wr_s,
                    1: release_pt,
                    3: route_mid,
                    5: target_point,
                    6: {"x": target_point["x"] + self.rand_between(-1, 2), "y": self.clamp_y(target_point["y"] + self.rand_between(-2, 2))},
                    8: {"x": target_point["x"] + self.rand_between(-2, 3), "y": self.clamp_y(target_point["y"] + self.rand_between(-3, 3))},
                })
            else:
                # INCOMPLETE
                paths[primary_wr] = self.build_path({
                    0: wr_s,
                    1: release_pt,
                    3: route_mid,
                    4: route_break,
                    6: target_point,
                    7: {"x": target_point["x"] + self.rand_between(0, 3), "y": self.clamp_y(target_point["y"] + self.rand_between(-2, 2))},
                    8: {"x": target_point["x"] + self.rand_between(1, 5), "y": self.clamp_y(target_point["y"] + self.rand_between(-3, 3))},
                })

        # ── PRIMARY DEFENDER ──
        if is_scramble:
            qb_path = paths["QB"]
            if is_sack:
                paths[primary_def] = self.build_path({
                    0: start[primary_def],
                    2: self.lerp(start[primary_def], qb_path[4], 0.3),
                    4: self.lerp(start[primary_def], qb_path[5], 0.6),
                    6: {"x": qb_path[7]["x"] + self.rand_between(-1, 1), "y": qb_path[7]["y"] + self.rand_between(-1, 1)},
                    7: qb_path[7],
                    8: qb_path[8],
                })
            elif is_big_gain:
                # QB breaks free — defender trails far behind
                chase_lag = self.rand_between(5, 15)
                paths[primary_def] = self.build_path({
                    0: start[primary_def],
                    2: self.lerp(start[primary_def], qb_path[3], 0.3),
                    4: self.lerp(start[primary_def], qb_path[4], 0.5),
                    6: {"x": qb_path[6]["x"] - chase_lag * 0.6, "y": qb_path[6]["y"] + self.rand_between(-3, 3)},
                    8: {"x": qb_path[8]["x"] - chase_lag, "y": qb_path[8]["y"] + self.rand_between(-5, 5)},
                })
            elif is_fumble:
                paths[primary_def] = self.build_path({
                    0: start[primary_def],
                    2: self.lerp(start[primary_def], qb_path[4], 0.3),
                    4: self.lerp(start[primary_def], qb_path[5], 0.5),
                    6: {"x": qb_path[6]["x"] + self.rand_between(-2, 2), "y": qb_path[6]["y"] + self.rand_between(-2, 2)},
                    7: {"x": qb_path[7]["x"] + self.rand_between(-1, 1), "y": qb_path[7]["y"] + self.rand_between(-1, 1)},
                    8: qb_path[8],
                })
            else:
                # Short/medium scramble — sometimes tackled, sometimes runner just stops
                runner_stops = self.rand() < 0.35
                closeness = self.rand_between(4, 10) if runner_stops else self.rand_between(1, 3)
                paths[primary_def] = self.build_path({
                    0: start[primary_def],
                    2: self.lerp(start[primary_def], qb_path[3], 0.3),
                    4: self.lerp(start[primary_def], qb_path[5], 0.5),
                    6: {"x": qb_path[6]["x"] + self.rand_between(-2, 2), "y": qb_path[6]["y"] + self.rand_between(-3, 3)},
                    8: {"x": qb_path[8]["x"] + self.rand_between(-closeness, closeness),
                        "y": qb_path[8]["y"] + self.rand_between(-closeness, closeness)},
                })
        elif is_sack:
            # Sack on a pass play — primary defender just covers the receiver
            wr_path = paths[primary_wr]
            closeness = self.rand_between(1, 4)
            paths[primary_def] = self.build_path({
                0: start[primary_def],
                2: self.lerp(start[primary_def], wr_path[2], 0.3),
                4: self.lerp(start[primary_def], wr_path[4], 0.5),
                6: {"x": wr_path[6]["x"] + self.rand_between(-closeness, closeness),
                    "y": wr_path[6]["y"] + self.rand_between(-closeness, closeness)},
                8: {"x": wr_path[8]["x"] + self.rand_between(-closeness, closeness),
                    "y": wr_path[8]["y"] + self.rand_between(-closeness, closeness)},
            })
        elif is_int:
            paths[primary_def] = self.build_path({
                0: start[primary_def],
                2: self.lerp(start[primary_def], target_point, 0.25),
                4: self.lerp(start[primary_def], ball_landing, 0.5),
                6: ball_landing,
                7: {"x": ball_landing["x"] + self.rand_between(1, 5), "y": self.clamp_y(ball_landing["y"] + self.rand_between(-3, 3))},
                8: {"x": ball_landing["x"] + self.rand_between(3, 8), "y": self.clamp_y(ball_landing["y"] + self.rand_between(-5, 5))},
            })
        else:
            # Pass play with receiver
            wr_path = paths[primary_wr]
            if is_catch and is_big_gain:
                # Beaten badly — trails far behind
                trail = self.rand_between(5, 15)
                paths[primary_def] = self.build_path({
                    0: start[primary_def],
                    2: self.lerp(start[primary_def], wr_path[2], 0.3),
                    4: self.lerp(start[primary_def], wr_path[4], 0.5),
                    6: {"x": wr_path[6]["x"] - trail * 0.5, "y": wr_path[6]["y"] + self.rand_between(-3, 3)},
                    8: {"x": wr_path[8]["x"] - trail, "y": wr_path[8]["y"] + self.rand_between(-5, 5)},
                })
            elif is_catch:
                # In coverage — sometimes tackles, sometimes runner just goes down
                runner_stops = self.rand() < 0.35
                closeness = self.rand_between(4, 8) if runner_stops else self.rand_between(1, 3)
                paths[primary_def] = self.build_path({
                    0: start[primary_def],
                    2: self.lerp(start[primary_def], wr_path[3], 0.3),
                    4: self.lerp(start[primary_def], wr_path[5], 0.5),
                    6: {"x": wr_path[6]["x"] + self.rand_between(-2, 2), "y": wr_path[6]["y"] + self.rand_between(-2, 2)},
                    7: {"x": wr_path[7]["x"] + self.rand_between(-closeness, closeness),
                        "y": wr_path[7]["y"] + self.rand_between(-closeness, closeness)},
                    8: {"x": wr_path[8]["x"] + self.rand_between(-closeness, closeness),
                        "y": wr_path[8]["y"] + self.rand_between(-closeness, closeness)},
                })
            elif is_fumble:
                paths[primary_def] = self.build_path({
                    0: start[primary_def],
                    2: self.lerp(start[primary_def], wr_path[3], 0.3),
                    4: self.lerp(start[primary_def], wr_path[5], 0.5),
                    6: {"x": wr_path[6]["x"] + self.rand_between(-1, 1), "y": wr_path[6]["y"] + self.rand_between(-1, 1)},
                    7: wr_path[7],
                    8: {"x": wr_path[8]["x"] + self.rand_between(-1, 2), "y": wr_path[8]["y"] + self.rand_between(-1, 2)},
                })
            else:
                # Incomplete — tight coverage
                closeness = self.rand_between(0.5, 3)
                paths[primary_def] = self.build_path({
                    0: start[primary_def],
                    2: self.lerp(start[primary_def], wr_path[3], 0.3),
                    4: self.lerp(start[primary_def], wr_path[5], 0.5),
                    6: {"x": wr_path[6]["x"] + self.rand_between(-closeness, closeness),
                        "y": wr_path[6]["y"] + self.rand_between(-closeness, closeness)},
                    8: {"x": wr_path[8]["x"] + self.rand_between(-closeness, closeness),
                        "y": wr_path[8]["y"] + self.rand_between(-closeness, closeness)},
                })

        # ── O-LINE ──
        o_line = ["C", "LG", "RG", "LT", "RT"]
        for pid in o_line:
            s = start[pid]
            if is_scramble:
                paths[pid] = self.build_path({
                    0: s,
                    1: {"x": s["x"] + 0.5, "y": self.jitter(s["y"], 0.3)},
                    3: {"x": s["x"] + self.rand_between(1, 3), "y": self.jitter(s["y"], 1)},
                    5: {"x": s["x"] + self.rand_between(2, 5), "y": self.jitter(s["y"], 1.5)},
                    8: {"x": s["x"] + self.rand_between(3, 7), "y": self.jitter(s["y"], 2)},
                })
            elif is_sack:
                paths[pid] = self.build_path({
                    0: s,
                    1: {"x": s["x"] + 0.3, "y": self.jitter(s["y"], 0.2)},
                    3: {"x": s["x"] + self.rand_between(0, 0.5), "y": self.jitter(s["y"], 0.5)},
                    5: {"x": s["x"] + self.rand_between(-1, 0), "y": self.jitter(s["y"], 0.5)},
                    8: {"x": s["x"] + self.rand_between(-2, 0), "y": self.jitter(s["y"], 1)},
                })
            else:
                paths[pid] = self.build_path({
                    0: s,
                    1: {"x": s["x"] + 0.3, "y": self.jitter(s["y"], 0.2)},
                    3: {"x": s["x"] + self.rand_between(0.5, 1.5), "y": self.jitter(s["y"], 0.5)},
                    5: {"x": s["x"] + self.rand_between(1, 2), "y": self.jitter(s["y"], 0.5)},
                    8: {"x": s["x"] + self.rand_between(1, 3), "y": self.jitter(s["y"], 0.5)},
                })

        # ── D-LINE ──
        d_line = ["LDE", "LDT", "RDT", "RDE"]
        for pid in d_line:
            if pid in paths:
                continue
            s = start[pid]
            qb_path = paths["QB"]
            if is_scramble:
                paths[pid] = self.build_path({
                    0: s,
                    2: {"x": s["x"] + self.rand_between(-2, -1), "y": self.jitter(s["y"], 1)},
                    4: self.lerp(s, qb_path[4], 0.4),
                    6: {"x": qb_path[6]["x"] + self.rand_between(-3, 5), "y": qb_path[6]["y"] + self.rand_between(-4, 4)},
                    8: {"x": qb_path[8]["x"] + self.rand_between(-5, 5), "y": qb_path[8]["y"] + self.rand_between(-5, 5)},
                })
            elif is_sack:
                paths[pid] = self.build_path({
                    0: s,
                    2: {"x": s["x"] + self.rand_between(-1, -0.5), "y": self.jitter(s["y"], 1)},
                    4: self.lerp(s, qb_path[4], 0.5),
                    6: {"x": qb_path[6]["x"] + self.rand_between(-2, 2), "y": qb_path[6]["y"] + self.rand_between(-3, 3)},
                    8: {"x": qb_path[8]["x"] + self.rand_between(-2, 2), "y": qb_path[8]["y"] + self.rand_between(-3, 3)},
                })
            else:
                paths[pid] = self.build_path({
                    0: s,
                    2: {"x": s["x"] - self.rand_between(0.5, 1.5), "y": self.jitter(s["y"], 1)},
                    4: {"x": s["x"] - self.rand_between(1, 3), "y": self.jitter(s["y"], 1.5)},
                    6: {"x": s["x"] - self.rand_between(2, 4), "y": self.jitter(s["y"], 2)},
                    8: {"x": s["x"] - self.rand_between(2, 5), "y": self.jitter(s["y"], 2)},
                })

        # ── NON-PRIMARY RECEIVERS (decoy routes) ──
        receivers = ["WR1", "WR2", "SLOT", "TE"]
        for pid in receivers:
            if pid in paths:
                continue
            s = start[pid]
            depth = self.rand_between(5, 25)
            drift = self.rand_between(-8, 8)
            route_end = {"x": s["x"] + depth, "y": self.clamp_y(s["y"] + drift)}
            paths[pid] = self.build_path({
                0: s,
                1: {"x": s["x"] + self.rand_between(1, 3), "y": s["y"] + drift * 0.05},
                3: {"x": s["x"] + depth * 0.4, "y": self.clamp_y(s["y"] + drift * 0.3)},
                5: {"x": s["x"] + depth * 0.7, "y": self.clamp_y(s["y"] + drift * 0.6)},
                7: route_end,
                8: {"x": route_end["x"] + self.rand_between(0, 3), "y": self.clamp_y(route_end["y"] + self.rand_between(-2, 2))},
            })

        # ── RB ──
        if "RB" not in paths:
            s = start["RB"]
            if is_scramble:
                qb_path = paths["QB"]
                paths["RB"] = self.build_path({
                    0: s,
                    2: {"x": s["x"] + self.rand_between(0, 2), "y": self.jitter(s["y"], 1)},
                    4: self.lerp(s, qb_path[4], 0.4),
                    6: {"x": qb_path[6]["x"] + self.rand_between(-2, 4), "y": qb_path[6]["y"] + self.rand_between(-3, 3)},
                    8: {"x": qb_path[8]["x"] + self.rand_between(-3, 5), "y": qb_path[8]["y"] + self.rand_between(-4, 4)},
                })
            else:
                paths["RB"] = self.build_path({
                    0: s,
                    2: {"x": s["x"] + self.rand_between(0, 2), "y": self.jitter(s["y"], 1)},
                    4: {"x": s["x"] + self.rand_between(1, 4), "y": self.jitter(s["y"], 2)},
                    6: {"x": s["x"] + self.rand_between(2, 6), "y": self.jitter(s["y"], 3)},
                    8: {"x": s["x"] + self.rand_between(3, 8), "y": self.jitter(s["y"], 4)},
                })

        # ── NON-PRIMARY SECONDARY & LBs ──
        secondary = ["LOLB", "MLB", "ROLB", "CB1", "CB2", "FS", "SS"]
        for pid in secondary:
            if pid in paths:
                continue
            s = start[pid]

            if is_scramble:
                qb_path = paths["QB"]
                if is_big_gain:
                    lag = self.rand_between(3, 10)
                    paths[pid] = self.build_path({
                        0: s,
                        2: {"x": s["x"] + self.rand_between(0, 3), "y": self.jitter(s["y"], 2)},
                        4: self.lerp(s, qb_path[4], 0.35),
                        6: {"x": qb_path[6]["x"] - lag * 0.5, "y": qb_path[6]["y"] + self.rand_between(-5, 5)},
                        8: {"x": qb_path[8]["x"] - lag, "y": qb_path[8]["y"] + self.rand_between(-6, 6)},
                    })
                else:
                    spread = self.rand_between(2, 6)
                    paths[pid] = self.build_path({
                        0: s,
                        2: self.lerp(s, qb_path[3], 0.25),
                        4: self.lerp(s, qb_path[5], 0.45),
                        6: {"x": qb_path[6]["x"] + self.rand_between(-spread, spread),
                            "y": qb_path[6]["y"] + self.rand_between(-spread, spread)},
                        8: {"x": qb_path[8]["x"] + self.rand_between(-spread, spread),
                            "y": qb_path[8]["y"] + self.rand_between(-spread, spread)},
                    })
            else:
                covered_wr = self.COVERAGE_MAP.get(pid)
                if covered_wr and covered_wr in paths:
                    wr_path = paths[covered_wr]
                    paths[pid] = self.build_path({
                        0: s,
                        2: self.lerp(s, wr_path[2], 0.3),
                        4: self.lerp(s, wr_path[4], 0.5),
                        6: {"x": wr_path[6]["x"] + self.rand_between(-3, 3), "y": wr_path[6]["y"] + self.rand_between(-3, 3)},
                        8: {"x": wr_path[8]["x"] + self.rand_between(-3, 3), "y": wr_path[8]["y"] + self.rand_between(-3, 3)},
                    })
                else:
                    paths[pid] = self.build_path({
                        0: s,
                        2: {"x": s["x"] + self.rand_between(0, 3), "y": self.jitter(s["y"], 2)},
                        4: {"x": s["x"] + self.rand_between(1, 5), "y": self.jitter(s["y"], 3)},
                        6: {"x": s["x"] + self.rand_between(2, 7), "y": self.jitter(s["y"], 4)},
                        8: {"x": s["x"] + self.rand_between(3, 10), "y": self.jitter(s["y"], 5)},
                    })

        # ── BUILD RESULT ──
        positions = {}
        offense = {"QB", "C", "LG", "RG", "LT", "RT", "WR1", "WR2", "SLOT", "TE", "RB"}
        all_players = [
            "QB", "C", "LG", "RG", "LT", "RT", "WR1", "WR2", "SLOT", "TE", "RB",
            "LDE", "LDT", "RDT", "RDE", "LOLB", "MLB", "ROLB", "CB1", "CB2", "FS", "SS",
        ]

        for pid in all_players:
            positions[pid] = {
                "team": "offense" if pid in offense else "defense",
                "positions": [self.round_pos(p) for p in paths[pid]],
            }

        return {"positions": positions, "target_point": target_point, "ball_landing": ball_landing}


    # ── BALL POSITION GENERATOR (9 keyframes) ─────────────────────
    # Frames 0-3: ball with QB
    # Frame 4: release point
    # Frames 5-6: ball in air (pass) or with runner (scramble)
    # Frames 7-8: with catcher / on ground / with interceptor

    def generate_ball_positions(self, zone, outcome, positions, target_point, ball_landing):
        qb_pos = positions["QB"]["positions"]
        is_scramble = zone == "SCRAMBLE"
        is_sack = outcome == "SACKED"
        is_catch = outcome in ("SHORT_GAIN", "MEDIUM_GAIN", "LONG_GAIN", "BIG_PLAY", "BREAKAWAY", "TOUCHDOWN")
        is_fumble = outcome == "FUMBLE"
        is_int = outcome == "INTERCEPTION"

        if is_scramble or is_sack:
            # Ball stays with QB the entire play
            return [{"x": p["x"], "y": p["y"]} for p in qb_pos]

        # Pass plays: ball with QB until throw, then in air, then at target
        primary_wr = self.ZONE_PRIMARY_RECEIVER[zone]
        wr_pos = positions[primary_wr]["positions"]
        ball = []

        # Frames 0-4: ball with QB (through release)
        for i in range(5):
            ball.append({"x": qb_pos[i]["x"], "y": qb_pos[i]["y"]})

        # Frame 5: in air — midway to landing
        if ball_landing:
            ball.append({
                "x": (qb_pos[4]["x"] + ball_landing["x"]) / 2,
                "y": (qb_pos[4]["y"] + ball_landing["y"]) / 2,
            })
            # Frame 6: arrives at target
            ball.append({"x": ball_landing["x"], "y": ball_landing["y"]})
        else:
            ball.append({"x": qb_pos[5]["x"], "y": qb_pos[5]["y"]})
            ball.append({"x": qb_pos[6]["x"], "y": qb_pos[6]["y"]})

        # Frames 7-8: with receiver / defender / on ground
        if is_catch:
            ball.append({"x": wr_pos[7]["x"], "y": wr_pos[7]["y"]})
            ball.append({"x": wr_pos[8]["x"], "y": wr_pos[8]["y"]})
        elif is_fumble:
            ball.append({"x": wr_pos[7]["x"], "y": wr_pos[7]["y"]})
            ball.append({
                "x": wr_pos[8]["x"] + self.rand_between(-2, 2),
                "y": wr_pos[8]["y"] + self.rand_between(-2, 2),
            })
        elif is_int:
            primary_def = self.ZONE_PRIMARY_DEFENDER[zone]
            def_pos = positions[primary_def]["positions"]
            ball.append({"x": def_pos[7]["x"], "y": def_pos[7]["y"]})
            ball.append({"x": def_pos[8]["x"], "y": def_pos[8]["y"]})
        else:
            # Incomplete — ball on ground at landing
            if ball_landing:
                ball.append({"x": ball_landing["x"], "y": ball_landing["y"]})
                ball.append({"x": ball_landing["x"], "y": ball_landing["y"]})
            else:
                ball.append(ball[-1])
                ball.append(ball[-1])

        return ball

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()

            zone = self.get_current_betmode().get_name()

            def play_once(base_bet, win_data):
                result_data = self.generate_outcome(zone)
                outcome = result_data["outcome"]
                multiplier = result_data["multiplier"]
                yards = self.generate_yards(outcome)
                pos_result = self.generate_positions(zone, outcome, yards)
                positions = pos_result["positions"]
                target_point = pos_result["target_point"]
                ball_landing = pos_result["ball_landing"]

                ball = self.generate_ball_positions(zone, outcome, positions, target_point, ball_landing)

                result = {
                    "index": len(self.book.events),
                    "type": EventConstants.WIN_DATA.value,
                    "data": {
                        "zone": zone,
                        "outcome": outcome,
                        "multiplier": multiplier,
                        "yards": yards,
                        "target_point": target_point,
                        "ball_landing": ball_landing,
                        "ball": {
                            "positions": [self.round_pos(p) for p in ball],
                        },
                        "players": positions,
                    },
                }
                win_data["totalWin"] = base_bet * multiplier
                self.win_manager.update_spinwin(win_data["totalWin"])
                self.win_manager.update_gametype_wins(self.gametype)
                win_data["wins"].append(result)
                self.book.add_event(result)

            play_once(base_bet=1.0, win_data={"totalWin": 0, "wins": []})

            self.evaluate_finalwin()

        self.imprint_wins()

    def run_freespin(self):
        pass