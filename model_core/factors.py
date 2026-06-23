import torch
import torch.nn as nn

from .vocab import FEATURE_NAMES


class RMSNormFactor(nn.Module):
    """RMSNorm for factor normalization."""

    def __init__(self, d_model, eps=1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(d_model))

    def forward(self, x):
        rms = torch.sqrt(torch.mean(x ** 2, dim=-1, keepdim=True) + self.eps)
        return (x / rms) * self.weight


class AStockIndicators:
    @staticmethod
    def delay(x, periods):
        if periods == 0:
            return x
        out = torch.roll(x, periods, dims=1)
        out[:, :periods] = 0.0
        return out

    @staticmethod
    def moving_mean(x, window):
        if window <= 1:
            return x
        pad = torch.zeros((x.shape[0], window - 1), device=x.device, dtype=x.dtype)
        x_pad = torch.cat([pad, x], dim=1)
        return x_pad.unfold(1, window, 1).mean(dim=-1)

    @staticmethod
    def kline_pressure(close, open_, high, low):
        range_hl = high - low + 1e-9
        body = close - open_
        return torch.tanh((body / range_hl) * 2.0)


class FeatureEngineer:
    INPUT_DIM = len(FEATURE_NAMES)

    @staticmethod
    def robust_norm(t):
        t = torch.nan_to_num(t, nan=0.0, posinf=0.0, neginf=0.0)
        median = torch.nanmedian(t, dim=1, keepdim=True)[0]
        mad = torch.nanmedian(torch.abs(t - median), dim=1, keepdim=True)[0] + 1e-6
        norm = (t - median) / mad
        return torch.clamp(torch.nan_to_num(norm), -5.0, 5.0)

    @staticmethod
    def compute_features(raw_dict):
        c = raw_dict["close"]
        o = raw_dict["open"]
        h = raw_dict["high"]
        l = raw_dict["low"]
        v = raw_dict["volume"]
        amount = raw_dict["amount"]

        prev_close = AStockIndicators.delay(c, 1)
        ret = torch.log((c + 1e-9) / (prev_close + 1e-9))
        ret[:, 0] = 0.0

        close_5 = AStockIndicators.delay(c, 5)
        ret5 = torch.log((c + 1e-9) / (close_5 + 1e-9))
        ret5[:, :5] = 0.0

        vol_ma20 = AStockIndicators.moving_mean(v, 20)
        vol_chg = v / (vol_ma20 + 1.0) - 1.0

        pressure = AStockIndicators.kline_pressure(c, o, h, l)

        ma20 = AStockIndicators.moving_mean(c, 20)
        ma_dev = c / (ma20 + 1e-9) - 1.0

        amount_strength = torch.log1p(torch.clamp(amount, min=0.0))

        features = torch.stack(
            [
                FeatureEngineer.robust_norm(ret),
                FeatureEngineer.robust_norm(ret5),
                FeatureEngineer.robust_norm(vol_chg),
                pressure,
                FeatureEngineer.robust_norm(ma_dev),
                FeatureEngineer.robust_norm(amount_strength),
            ],
            dim=1,
        )
        return torch.nan_to_num(features, nan=0.0, posinf=5.0, neginf=-5.0)


class AdvancedFactorEngineer:
    """Compatibility wrapper for older research code."""

    def __init__(self):
        self.rms_norm = RMSNormFactor(1)

    def compute_advanced_features(self, raw_dict):
        return FeatureEngineer.compute_features(raw_dict)


MemeIndicators = AStockIndicators
