# Hyperparameter Tuning the ANN using Optuna

*CampusX — "Practical Deep Learning using PyTorch" (Video 10/14) · [YouTube](https://www.youtube.com/watch?v=Y3s-wBBLj_o) · 56:13 · [Colab notebook](https://colab.research.google.com/drive/1DvwpHIQhpBxX1g1YLm4gdaJHiDw5OVbK)*

This video generalizes the Video 9 architecture into a **parametrized** `MyNN` (variable depth, width, and dropout) and then uses **Optuna** to search the hyperparameter space automatically instead of tuning by hand.

## Chapters
- 0:00 Recap
- 8:07 Plan of Action
- 10:31 Optuna Code
- 13:42 Code Demo
- 15:19 Initiating hyperparameter tuning for an ANN using Optuna
- 36:10 Initiating 10 trials for ANN hyperparameter tuning
- 49:02 Results of hyperparameter tuning showed 89.7% accuracy with specific parameters
- 50:45 Achieved best accuracy through hyperparameter tuning and experimentation tracking

## A parametrized network and the Optuna objective function

```python
class MyNN(nn.Module):
    def __init__(self, input_dim, output_dim, num_hidden_layers, neurons_per_layer, dropout_rate):
        super().__init__()
        layers = []
        for i in range(num_hidden_layers):
            layers.append(nn.Linear(input_dim, neurons_per_layer))
            layers.append(nn.BatchNorm1d(neurons_per_layer))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout_rate))
            input_dim = neurons_per_layer            # next layer's input = this layer's output width
        layers.append(nn.Linear(neurons_per_layer, output_dim))
        self.model = nn.Sequential(*layers)          # *layers unpacks the list into nn.Sequential's args

    def forward(self, x):
        return self.model(x)

def objective(trial):
    num_hidden_layers = trial.suggest_int("num_hidden_layers", 1, 5)
    neurons_per_layer = trial.suggest_int("neurons_per_layer", 8, 128, step=8)
    epochs = trial.suggest_int("epochs", 10, 50, step=10)
    learning_rate = trial.suggest_float("learning_rate", 1e-5, 1e-1, log=True)   # log=True -> sampled log-uniformly, standard for LR search
    dropout_rate = trial.suggest_float("dropout_rate", 0.1, 0.5, step=0.1)
    batch_size = trial.suggest_categorical("batch_size", [16, 32, 64, 128])
    optimizer_name = trial.suggest_categorical("optimizer", ['Adam', 'SGD', 'RMSprop'])
    weight_decay = trial.suggest_float("weight_decay", 1e-5, 1e-3, log=True)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, pin_memory=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, pin_memory=True)

    model = MyNN(784, 10, num_hidden_layers, neurons_per_layer, dropout_rate).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(model.parameters(), lr=0.1, weight_decay=1e-4)

    if optimizer_name == 'Adam':
        optim.Adam(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    elif optimizer_name == 'SGD':
        optim.SGD(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    else:
        optim.RMSprop(model.parameters(), lr=learning_rate, weight_decay=weight_decay)

    # ... standard training loop using `optimizer` ...
    # ... evaluation on test_loader ...
    return accuracy       # Optuna maximizes/minimizes whatever this function returns

!pip install optuna
import optuna
study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=10)

study.best_value    # 0.8908333333333334
study.best_params   # {'num_hidden_layers': 4, 'neurons_per_layer': 88, 'epochs': 20, 'learning_rate': 0.0003, 'dropout_rate': 0.2, 'batch_size': 128, 'optimizer': 'RMSprop', 'weight_decay': 0.00045}
```

> **Note:** There is a real bug in `objective()` above. The tuned optimizer is constructed (`optim.Adam(...)` / `optim.SGD(...)` / `optim.RMSprop(...)`) but its result is never assigned back to the `optimizer` variable. The training loop below still uses the original `optimizer = optim.SGD(model.parameters(), lr=0.1, weight_decay=1e-4)` created two lines earlier, regardless of what `trial.suggest_categorical("optimizer", ...)` picked. So `optimizer_name`, `learning_rate`, and the sampled `weight_decay` have no actual effect on training in this run — every trial silently trains with plain SGD, lr=0.1, weight_decay=1e-4. The parameters that *did* genuinely drive the accuracy differences across trials are `num_hidden_layers`, `neurons_per_layer`, `epochs`, `dropout_rate`, and `batch_size`. The fix is simply to assign rather than just call: `optimizer = optim.Adam(...)`, etc. It's a useful real-world lesson: Optuna will happily "optimize" a hyperparameter that your code doesn't actually use, and the results will still look plausible — always sanity-check that suggested values are wired into the actual training call.

## Optuna concepts

- **`trial.suggest_*`** defines the search space per hyperparameter: `suggest_int` and `suggest_float` (with `log=True` for scale-spanning params like learning rate) for numeric ranges, and `suggest_categorical` for discrete choices.
- **`study.optimize(objective, n_trials=N)`** runs the objective function `N` times, each time with a newly sampled `trial`. Optuna's default sampler — TPE (Tree-structured Parzen Estimator) — uses the results of earlier trials to sample more promising regions in later trials. In the run above, trial 0's poor result at a very low `learning_rate` narrows the search away from that region in later trials, though because of the bug described above, this specific run's learning-rate sampling is actually irrelevant to the outcome.
- **`study.best_value`** and **`study.best_params`** report the best objective value seen across all trials and the hyperparameter dictionary that produced it.
- This is "black-box" hyperparameter optimization: it treats the entire train-and-evaluate pipeline as a function to be maximized over a hyperparameter space, without needing gradients with respect to the hyperparameters themselves.

## Key takeaways

- Making `MyNN` parametrized (depth, width, dropout all passed as constructor arguments) is what makes it searchable — Optuna can only tune what's exposed as a variable.
- `trial.suggest_int`, `trial.suggest_float` (optionally `log=True`), and `trial.suggest_categorical` together define the full search space for a trial.
- `study.optimize(objective, n_trials=10)` ran 10 trials, and the best one reached `study.best_value` of **0.8908333333333334** with `study.best_params` = `{'num_hidden_layers': 4, 'neurons_per_layer': 88, 'epochs': 20, 'learning_rate': 0.0003, 'dropout_rate': 0.2, 'batch_size': 128, 'optimizer': 'RMSprop', 'weight_decay': 0.00045}`.
- Because the tuned optimizer was never assigned back to `optimizer` in the objective function, the accuracy differences across trials in this run were actually driven only by `num_hidden_layers`, `neurons_per_layer`, `epochs`, `dropout_rate`, and `batch_size` — not by `optimizer`, `learning_rate`, or `weight_decay`, despite those being sampled and reported in `best_params`.
- The general lesson: always verify that a hyperparameter suggested by `trial.suggest_*` is actually wired into the code path it's meant to control, since Optuna cannot detect that a sampled value went unused and will still report a plausible-looking "best" configuration.
- Optuna's default TPE sampler is adaptive — it uses outcomes from earlier trials to bias sampling toward more promising regions in subsequent trials, rather than sampling the space uniformly at random.
