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
    
    # ── POSITION GENERATION ──────────────────────────────────────
    def generate_positions(self, zone, outcome, yards):
        start = self.get_start_positions()
        mid = {}
        end = {}

        primary_wr = self.ZONE_PRIMARY_RECEIVER[zone]
        primary_def = self.ZONE_PRIMARY_DEFENDER[zone]
        is_scramble = zone == "SCRAMBLE"
        is_sack = outcome == "SACKED"
        is_catch = outcome in ("SHORT_GAIN", "MEDIUM_GAIN", "LONG_GAIN", "BIG_PLAY", "BREAKAWAY", "TOUCHDOWN")
        is_int = outcome == "INTERCEPTION"
        is_fumble = outcome == "FUMBLE"

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

        # ── QB ──
        if is_scramble:
            drift = self.rand_between(-15, 15)
            if is_sack:
                mid["QB"] = {"x": start["QB"]["x"] - 1, "y": self.jitter(0, 2)}
                end["QB"] = {"x": start["QB"]["x"] + yards, "y": self.jitter(0, 3)}
            else:
                mid["QB"] = {"x": start["QB"]["x"] + yards * 0.4, "y": drift * 0.4}
                end["QB"] = {"x": start["QB"]["x"] + yards, "y": self.clamp_y(drift)}
        elif is_sack:
            mid["QB"] = {"x": start["QB"]["x"] - 2, "y": self.jitter(0, 2)}
            end["QB"] = {"x": start["QB"]["x"] + yards, "y": self.jitter(0, 3)}
        else:
            mid["QB"] = {"x": start["QB"]["x"] - self.rand_between(1, 3), "y": self.jitter(0, 1.5)}
            end["QB"] = {"x": start["QB"]["x"] - self.rand_between(0, 2), "y": self.jitter(0, 2)}

        # ── PRIMARY RECEIVER (pass plays) ──
        if not is_scramble:
            mid[primary_wr] = {
                "x": (start[primary_wr]["x"] + target_point["x"]) * 0.5 + self.rand_between(-2, 2),
                "y": self.clamp_y((start[primary_wr]["y"] + target_point["y"]) * 0.5 + self.rand_between(-1, 1)),
            }
            if is_catch:
                yac = max(0, yards - target_point["x"])
                end[primary_wr] = {
                    "x": target_point["x"] + yac,
                    "y": self.clamp_y(target_point["y"] + self.rand_between(-3, 3)),
                }
            elif is_fumble:
                end[primary_wr] = {
                    "x": target_point["x"] + self.rand_between(1, 5),
                    "y": self.clamp_y(target_point["y"] + self.rand_between(-3, 3)),
                }
            else:
                end[primary_wr] = {
                    "x": target_point["x"] + self.rand_between(-2, 3),
                    "y": self.clamp_y(target_point["y"] + self.rand_between(-2, 2)),
                }

        # ── PRIMARY DEFENDER ──
        if is_scramble or is_sack:
            chase_target = end["QB"]
            mid[primary_def] = self.lerp(start[primary_def], chase_target, 0.5)
            mid[primary_def]["x"] += self.rand_between(-1, 1)
            mid[primary_def]["y"] += self.rand_between(-1, 1)
            end[primary_def] = {
                "x": chase_target["x"] + self.rand_between(-1, 1),
                "y": chase_target["y"] + self.rand_between(-1, 1),
            }
        elif is_int:
            mid[primary_def] = self.lerp(start[primary_def], ball_landing, 0.5)
            end[primary_def] = {
                "x": ball_landing["x"] + self.rand_between(0, 5),
                "y": self.clamp_y(ball_landing["y"] + self.rand_between(-3, 3)),
            }
        else:
            rec_end = end[primary_wr]
            closeness = self.rand_between(2, 5) if is_catch else self.rand_between(0.5, 3)
            mid[primary_def] = self.lerp(start[primary_def], rec_end, 0.5)
            mid[primary_def]["x"] += self.rand_between(-2, 2)
            mid[primary_def]["y"] += self.rand_between(-2, 2)
            end[primary_def] = {
                "x": rec_end["x"] + self.rand_between(-closeness, closeness),
                "y": self.clamp_y(rec_end["y"] + self.rand_between(-closeness, closeness)),
            }

        # ── O-LINE (C, LG, RG, LT, RT) ──
        o_line = ["C", "LG", "RG", "LT", "RT"]
        for pid in o_line:
            if is_scramble:
                mid[pid] = {"x": start[pid]["x"] + self.rand_between(1, 3), "y": self.jitter(start[pid]["y"], 1)}
                end[pid] = {"x": start[pid]["x"] + self.rand_between(2, 6), "y": self.jitter(start[pid]["y"], 2)}
            elif is_sack:
                mid[pid] = {"x": start[pid]["x"] + self.rand_between(0, 1), "y": self.jitter(start[pid]["y"], 0.5)}
                end[pid] = {"x": start[pid]["x"] + self.rand_between(-1, 0.5), "y": self.jitter(start[pid]["y"], 1)}
            else:
                mid[pid] = {"x": start[pid]["x"] + self.rand_between(0.5, 2), "y": self.jitter(start[pid]["y"], 0.5)}
                end[pid] = {"x": start[pid]["x"] + self.rand_between(1, 3), "y": self.jitter(start[pid]["y"], 0.5)}

        # ── D-LINE (LDE, LDT, RDT, RDE) ──
        d_line = ["LDE", "LDT", "RDT", "RDE"]
        for pid in d_line:
            if pid in mid:
                continue  # skip if already set as primary defender
            if is_scramble:
                mid[pid] = self.lerp(start[pid], end["QB"], 0.4)
                mid[pid]["x"] += self.rand_between(-2, 2)
                mid[pid]["y"] += self.rand_between(-2, 2)
                end[pid] = {"x": end["QB"]["x"] + self.rand_between(-3, 5), "y": end["QB"]["y"] + self.rand_between(-5, 5)}
            elif is_sack:
                mid[pid] = self.lerp(start[pid], end["QB"], 0.5)
                end[pid] = {"x": end["QB"]["x"] + self.rand_between(-2, 2), "y": end["QB"]["y"] + self.rand_between(-3, 3)}
            else:
                # Rush then get past QB
                mid[pid] = {"x": start[pid]["x"] + self.rand_between(-2, -1), "y": self.jitter(start[pid]["y"], 1.5)}
                end[pid] = {"x": start[pid]["x"] + self.rand_between(-4, -2), "y": self.jitter(start[pid]["y"], 2)}

        # ── NON-PRIMARY RECEIVERS (decoy routes) ──
        receivers = ["WR1", "WR2", "SLOT", "TE"]
        for pid in receivers:
            if pid in mid:
                continue  # skip primary
            depth = self.rand_between(5, 25)
            drift = self.rand_between(-8, 8)
            mid[pid] = {"x": start[pid]["x"] + depth * 0.5, "y": self.clamp_y(start[pid]["y"] + drift * 0.4)}
            end[pid] = {"x": start[pid]["x"] + depth, "y": self.clamp_y(start[pid]["y"] + drift)}

        # ── RB ──
        if is_scramble:
            mid["RB"] = self.lerp(start["RB"], end["QB"], 0.4)
            mid["RB"]["x"] += self.rand_between(0, 3)
            end["RB"] = {"x": end["QB"]["x"] + self.rand_between(-2, 4), "y": end["QB"]["y"] + self.rand_between(-3, 3)}
        else:
            mid["RB"] = {"x": start["RB"]["x"] + self.rand_between(0, 3), "y": self.jitter(start["RB"]["y"], 2)}
            end["RB"] = {"x": start["RB"]["x"] + self.rand_between(2, 8), "y": self.jitter(start["RB"]["y"], 5)}

        # ── NON-PRIMARY SECONDARY & LBs ──
        secondary = ["LOLB", "MLB", "ROLB", "CB1", "CB2", "FS", "SS"]
        for pid in secondary:
            if pid in mid:
                continue  # skip primary

            if is_scramble:
                spread = self.rand_between(3, 8)
                mid[pid] = self.lerp(start[pid], end["QB"], 0.4)
                mid[pid]["x"] += self.rand_between(-2, 2)
                mid[pid]["y"] += self.rand_between(-3, 3)
                end[pid] = {
                    "x": end["QB"]["x"] + self.rand_between(-spread, spread),
                    "y": end["QB"]["y"] + self.rand_between(-spread, spread),
                }
            else:
                # Cover their assigned receiver or play zone
                covered_wr = self.COVERAGE_MAP.get(pid)
                if covered_wr and covered_wr in end:
                    rec_end = end[covered_wr]
                    mid[pid] = self.lerp(start[pid], rec_end, 0.5)
                    mid[pid]["x"] += self.rand_between(-2, 2)
                    mid[pid]["y"] += self.rand_between(-2, 2)
                    end[pid] = {"x": rec_end["x"] + self.rand_between(-3, 3), "y": rec_end["y"] + self.rand_between(-3, 3)}
                else:
                    # Zone coverage drift
                    mid[pid] = {"x": start[pid]["x"] + self.rand_between(0, 5), "y": self.jitter(start[pid]["y"], 4)}
                    end[pid] = {"x": start[pid]["x"] + self.rand_between(2, 10), "y": self.jitter(start[pid]["y"], 6)}

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
                "start": self.round_pos(start[pid]),
                "mid": self.round_pos(mid[pid]),
                "end": self.round_pos(end[pid]),
            }

        return {"positions": positions, "target_point": target_point, "ball_landing": ball_landing}


    # ── BALL POSITION GENERATOR ──────────────────────────────────
    # Where the ball is at each keyframe (top-down, no height)


    def generate_ball_positions(self, zone, _outcome, start, mid, end, _target_point, ball_landing):
        qb_start = start.get("QB", {"x": -5, "y": 0})
        is_scramble = zone == "SCRAMBLE"

        if is_scramble:
            # Ball stays with QB
            return {
                "start": {"x": qb_start["x"], "y": qb_start["y"]},
                "mid": {"x": mid["QB"]["x"], "y": mid["QB"]["y"]},
                "end": {"x": end["QB"]["x"], "y": end["QB"]["y"]},
            }

        # Pass plays: ball goes from QB → through the air → landing
        return {
            "start": {"x": qb_start["x"], "y": qb_start["y"]},
            "mid": (
                {"x": (qb_start["x"] + ball_landing["x"]) / 2, "y": (qb_start["y"] + ball_landing["y"]) / 2}
                if ball_landing
                else {"x": qb_start["x"], "y": qb_start["y"]}
            ),
            "end": (
                {"x": ball_landing["x"], "y": ball_landing["y"]}
                if ball_landing
                else {"x": qb_start["x"], "y": qb_start["y"]}
            ),
        }

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

                start_raw = self.get_start_positions()
                mid_raw = {}
                end_raw = {}
                for pid in positions:
                    mid_raw[pid] = positions[pid]["mid"]
                    end_raw[pid] = positions[pid]["end"]

                ball = self.generate_ball_positions(zone, outcome, start_raw, mid_raw, end_raw, target_point, ball_landing)

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
                            "start": self.round_pos(ball["start"]),
                            "mid": self.round_pos(ball["mid"]),
                            "end": self.round_pos(ball["end"]),
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