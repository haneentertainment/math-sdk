"""Main file for generating results for sample lines-pay game."""

from gamestate import GameState
from game_config import GameConfig
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

if __name__ == "__main__":

    num_threads = 10
    rust_threads = 20
    batching_size = 50000
    compression = True
    profiling = False

    num_sim_args = {
        "DEEP_L": int(1e6),
        "DEEP_MID": int(1e6),
        "DEEP_R": int(1e6),
        "SHORT_L": int(1e6),
        "SHORT_MID": int(1e6),
        "SHORT_R": int(1e6),
        "SCRAMBLE": int(1e6),
    }

    run_conditions = {
        "run_sims": True,
    }
    target_modes = list(num_sim_args.keys())

    config = GameConfig()
    gamestate = GameState(config)

    if run_conditions["run_sims"]:
        create_books(
            gamestate,
            config,
            num_sim_args,
            batching_size,
            num_threads,
            compression,
            profiling,
        )

    generate_configs(gamestate)