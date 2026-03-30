from src.config.config import Config, BetMode
from src.config.distributions import Distribution


class GameConfig(Config):
    def __init__(self):
        super().__init__()
        self.rtp = 0.96
        self.game_id = "cashout_football"
        self.provider_name = "hane-entertainment"
        self.provider_number = 1 
        self.game_name = "Cashout Football"
        self.output_regular_json = True  # if True, outputs .json if compression = False. If False, outputs .jsonl
        if self.game_id != "cashout_football":
            self.construct_paths()
        self.working_name = "cashout_football"
        
        # Win information
        self.min_denomination = 0.1
        self.wincap = 50000
        
        # Game Details
        self.num_reels = 0
        self.num_rows = [0] * self.num_reels
        self.reels = 0
        self.row = 0
        self.paytable = {}  # Symbol information assumes ('kind','name') format

        # Define special Symbols properties - list all possible symbol states during game-play
        self.include_padding = False

        # Static game files
        self.bet_modes = [
            BetMode(
                name = "DEEP_L",
                cost = 1.0,
                rtp = self.rtp,
                max_win = 10000,
                auto_close_disabled = False,
                is_feature = True,
                is_buybonus = False,
                distributions = [
                    Distribution(
                        criteria = "basegame",
                        quota = 1,
                        conditions = {
                            "reel_weights": {},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                ],
            ),
            BetMode(
                name = "DEEP_MID",
                cost = 1.0,
                rtp = self.rtp,
                max_win = self.wincap,
                auto_close_disabled = False,
                is_feature = True,
                is_buybonus = False,
                distributions = [
                    Distribution(
                        criteria = "basegame",
                        quota = 1,
                        conditions = {
                            "reel_weights": {},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                ],
            ),
            BetMode(
                name = "DEEP_R",
                cost = 1.0,
                rtp = self.rtp,
                max_win = 10000,
                auto_close_disabled = False,
                is_feature = True,
                is_buybonus = False,
                distributions = [
                    Distribution(
                        criteria = "basegame",
                        quota = 1,
                        conditions = {
                            "reel_weights": {},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                ],
            ),
            BetMode(
                name = "SHORT_L",
                cost = 1.0,
                rtp = self.rtp,
                max_win = 1000,
                auto_close_disabled = False,
                is_feature = True,
                is_buybonus = False,
                distributions = [
                    Distribution(
                        criteria = "basegame",
                        quota = 1,
                        conditions = {
                            "reel_weights": {},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                ],
            ),
            BetMode(
                name = "SHORT_MID",
                cost = 1.0,
                rtp = self.rtp,
                max_win = 5000,
                auto_close_disabled = False,
                is_feature = True,
                is_buybonus = False,
                distributions = [
                    Distribution(
                        criteria = "basegame",
                        quota = 1,
                        conditions = {
                            "reel_weights": {},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                ],
            ),
            BetMode(
                name = "SHORT_R",
                cost = 1.0,
                rtp = self.rtp,
                max_win = 1000,
                auto_close_disabled = False,
                is_feature = True,
                is_buybonus = False,
                distributions = [
                    Distribution(
                        criteria = "basegame",
                        quota = 1,
                        conditions = {
                            "reel_weights": {},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                ],
            ),
            BetMode(
                name = "SCRAMBLE",
                cost = 1.0,
                rtp = self.rtp,
                max_win = 150,
                auto_close_disabled = False,
                is_feature = True,
                is_buybonus = False,
                distributions = [
                    Distribution(
                        criteria = "basegame",
                        quota = 1,
                        conditions = {
                            "reel_weights": {},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                ],
            ),
        ]