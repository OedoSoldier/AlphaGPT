import math

import torch

from .config import ModelConfig


class AStockBacktest:
    def __init__(self, trade_cost_rate=None):
        self.trade_cost_rate = (
            ModelConfig.TRADE_COST_RATE if trade_cost_rate is None else trade_cost_rate
        )

    def evaluate(self, factors, raw_data, target_ret):
        tradable = raw_data.get("tradable_mask")
        if tradable is None:
            tradable = torch.ones_like(target_ret)
        tradable = tradable.float()

        signal = torch.tanh(torch.nan_to_num(factors, nan=0.0))
        position = (signal > 0).float() * tradable

        prev_pos = torch.roll(position, 1, dims=1)
        prev_pos[:, 0] = 0.0
        turnover = torch.abs(position - prev_pos)

        net_pnl = position * target_ret - turnover * self.trade_cost_rate
        net_pnl = torch.nan_to_num(net_pnl, nan=0.0, posinf=0.0, neginf=0.0)

        mean = net_pnl.mean(dim=1)
        std = net_pnl.std(dim=1) + 1e-6
        sharpe = mean / std * math.sqrt(252)
        cum_ret = net_pnl.sum(dim=1)
        turnover_penalty = turnover.mean(dim=1) * 0.5
        score = sharpe + cum_ret - turnover_penalty

        activity = position.sum(dim=1)
        score = torch.where(
            activity < 20,
            torch.tensor(-5.0, device=score.device),
            score,
        )
        final_fitness = torch.nanmedian(score)
        annualized_ret = mean.mean().item() * 252
        return final_fitness, annualized_ret


MemeBacktest = AStockBacktest
