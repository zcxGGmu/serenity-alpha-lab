from __future__ import annotations

import json

from serenity_alpha_lab.stock_universe import StockUniverseEntry, load_stock_universe, match_universe_candidates


def test_load_stock_universe_normalizes_entries(tmp_path):
    path = tmp_path / "stock_universe.json"
    path.write_text(
        json.dumps(
            [
                {
                    "ticker": " mu ",
                    "name": "Micron Technology",
                    "market": "US",
                    "sector": "Semiconductors",
                    "themes": ["memory", "HBM"],
                    "aliases": ["存储芯片", "DRAM"],
                }
            ]
        ),
        encoding="utf-8",
    )

    entries = load_stock_universe(path)

    assert entries == [
        StockUniverseEntry(
            ticker="MU",
            name="Micron Technology",
            market="US",
            sector="Semiconductors",
            themes=["memory", "HBM"],
            aliases=["存储芯片", "DRAM"],
        )
    ]


def test_match_universe_candidates_prefers_theme_matches_before_alias_only_matches():
    entries = [
        StockUniverseEntry(
            ticker="MU",
            name="Micron Technology",
            market="US",
            sector="Semiconductors",
            themes=["memory", "HBM"],
            aliases=["存储芯片", "DRAM"],
        ),
        StockUniverseEntry(
            ticker="GIGADEVICE",
            name="兆易创新",
            market="CN",
            sector="Semiconductors",
            themes=["memory", "NOR flash", "MCU"],
            aliases=["存储芯片", "兆易创新"],
        ),
        StockUniverseEntry(
            ticker="TSLA",
            name="Tesla",
            market="US",
            sector="Automobiles",
            themes=["robotics"],
            aliases=["机器人"],
        ),
    ]

    candidates = match_universe_candidates(
        "存储芯片",
        canonical_theme="memory",
        aliases=["storage", "dram", "nand", "hbm"],
        universe=entries,
        limit=4,
    )

    assert candidates == ["MU", "GIGADEVICE"]
