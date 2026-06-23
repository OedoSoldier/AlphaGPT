import torch
import os
from .vocab import FORMULA_VOCAB

class ModelConfig:
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "astock_quant")
    DB_URL = (
        f"postgresql://{os.getenv('DB_USER','postgres')}:"
        f"{os.getenv('DB_PASSWORD','password')}@{os.getenv('DB_HOST','localhost')}:"
        f"{DB_PORT}/{DB_NAME}"
    )
    BATCH_SIZE = 8192
    TRAIN_STEPS = 1000
    MAX_FORMULA_LEN = 12
    TRADE_COST_RATE = float(os.getenv("ASTOCK_TRADE_COST_RATE", "0.001"))
    INPUT_DIM = FORMULA_VOCAB.feature_count
