from dataclasses import dataclass, field


@dataclass
class RunConfig:
    results_folder: str = '/content/drive/MyDrive/charts/results/'
    cash: float = 100
    mcap: bool = True
    multi_tf: list = field(default_factory=list)  # 1m, 3m, 5m, 15m, 30m, 1h,4h
    after_ath: bool = False
    min_start_minutes_to_wait: int = 30
    randomize_start_margin: bool = True
    df_end_margin: int = -1
    max_start_margin: int = 100
    min_start_margin: int = 5
    cerebro_runonce: bool = True
