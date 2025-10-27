from dataclasses import dataclass


@dataclass
class RunConfig:
    results_folder: str = '/content/drive/MyDrive/charts/results/'
    cash: float = 100
    mcap: bool = True
    after_ath: bool = False
    min_start_minutes_to_wait: int = 240
    randomize_start_margin: bool = True
    df_end_margin: int = -1
    max_start_margin: int = 100
