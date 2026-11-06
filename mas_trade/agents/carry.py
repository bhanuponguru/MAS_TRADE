"""Carry hypothesis (Koijen, Moskowitz, Pedersen, Vrugt 2018; BIS WP 1087; He, Manela, Ross, von Wachter): a perpetual's
funding is a transfer from longs to shorts, so expected return = carry + expected price change.

RankCarry is rung 0 of the carry ladder: long low-funding, short high-funding coins by rank, with the trailing mean
funding over `days` as the (backward-looking) carry forecast. Later rungs replace it by a forecast of the next funding
from the premium index and a separate crowding term.
"""
from .base import RankAgent


class RankCarry(RankAgent):
    name = "RankCarry"

    def __init__(self, days=14.0, **kw):
        super().__init__(**kw)
        self.days = days

    def signal(self, ctx):
        return -ctx.F[-ctx.bars(self.days):].mean(0)      # longs pay funding when it is positive: long low, short high
