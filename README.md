# Blotto-Game

Two-player Colonel Blotto simulation project with:

- reusable strategy simulation in `blotto.py`
- scalable dataset and metric generation in `generate_dataset.py`
- runtime and metric plotting in `plot.py`

## Scenarios

The generator now runs multiple testing scenarios by default:

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

Outputs are saved under `outputs/`.
