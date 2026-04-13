# Blotto-Game

Two-player Colonel Blotto simulation project with:

- reusable strategy simulation in `blotto.py`
- scalable dataset and metric generation in `generate_dataset.py`
- runtime and metric plotting in `plot.py`

## Strategies

The simulator currently includes 9 strategies:

- `uniform`: spreads troops as evenly as possible across all battlefields
- `weighted_value`: allocates troops in proportion to battlefield values
- `top_heavy`: strongly favors the highest-value battlefield while reducing investment elsewhere
- `random_partition`: splits troops randomly across battlefields for a high-variance baseline
- `balanced_priority`: mixes even coverage with value-aware allocation
- `winner_take_most`: heavily commits to a small number of key battlefields
- `anti_top_heavy`: avoids overinvesting in the single most valuable battlefield
- `noisy_weighted`: follows battlefield value with controlled randomness
- `defensive_spread`: guarantees baseline coverage before reinforcing strong positions

## Scenarios

The generator runs multiple testing scenarios by default:

- `small`
- `baseline`
- `medium`
- `large`
- `wide`
- `high_value`

Each scenario varies troop count, battlefield count, battlefield values, and number of matches per strategy pairing.

## Run

Generate the dataset and metrics:

```powershell
python generate_dataset.py
```

Generate only selected scenarios:

```powershell
python generate_dataset.py --scenarios baseline large wide
```

Override the number of matches per pairing for scalability tests:

```powershell
python generate_dataset.py --matches-per-pairing 500
```

Create the plots:

```powershell
python plot.py
```

## Plot Outputs

The plotting script now generates both scenario-level and strategy-level views, including:

- `runtime_by_scenario`
- `draws_and_ties`
- `best_matchups`
- `efficiency_metrics`
- `strategy_performance`
- `strategy_style`
- `strategy_unused_battlefields`
- `match_competitiveness`
- `average_score_margin`
- `ranked_strategy_performance`
- `strategy_margin_overview`
- `strategy_by_scenario`

These plots help compare:

- runtime and scenario difficulty
- draw frequency and score volatility
- allocation style through entropy and HHI
- overall strategy performance across all registered strategies
- how strategy performance changes from one scenario to another

Outputs are saved under `outputs/`.
