# Optimizing the Neural Network

*CampusX — "Practical Deep Learning using PyTorch" (Video 9/14) · [YouTube](https://www.youtube.com/watch?v=7smLlJ8oj4o) · 28:44 · [Colab notebook](https://colab.research.google.com/drive/1YDVmsVD8zkdDh5lqumA_HtIh_WqH10FC)*

This video picks up the overfitting gap left open at the end of Video 8 and closes it by layering three regularization techniques — Batch Normalization, Dropout, and weight decay — onto the exact same GPU-trained Fashion-MNIST pipeline. No chapter markers are available for this video (Colab-only, no notes PDF in the description).

## Three orthogonal knobs for the same overfitting problem

Rather than three unrelated tricks, it helps to think of these as three independent levers on the same underlying issue — a model that fits the training set too aggressively:

1. **Normalization** — `nn.BatchNorm1d` keeps activation distributions stable layer-to-layer as weights update.
2. **Stochastic regularization** — `nn.Dropout` forces the network to avoid relying on any single neuron.
3. **Weight-magnitude regularization** — `weight_decay` on the optimizer discourages any single weight from growing large.

All three are added on top of the identical `MyNN` architecture and training loop used in Video 8 (dataset, `DataLoader`, `criterion = nn.CrossEntropyLoss()`, and GPU device handling are all unchanged).

```python
class MyNN(nn.Module):
    def __init__(self, num_features):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(num_features, 128),
            nn.BatchNorm1d(128),          # NEW: normalizes activations per mini-batch -> faster, more stable training
            nn.ReLU(),
            nn.Dropout(p=0.3),            # NEW: randomly zeroes 30% of activations during training -> reduces overfitting
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(p=0.3),
            nn.Linear(64, 10)
        )
    def forward(self, x):
        return self.model(x)

optimizer = optim.SGD(model.parameters(), lr=0.1, weight_decay=1e-4)   # NEW: weight_decay = L2 regularization, penalizes large weights
```

Everything else (dataset, `DataLoader`, training loop, `criterion = nn.CrossEntropyLoss()`, GPU device handling) is identical to Video 8.

## The three techniques, explained

1. **`nn.BatchNorm1d`** — normalizes each mini-batch's activations (per feature) to zero mean/unit variance, then applies a learnable scale and shift. This speeds up and stabilizes training by keeping activation distributions consistent layer-to-layer as weights update ("internal covariate shift"). It's placed after `Linear`, before the activation, in this notebook. It behaves differently in `train()` vs `eval()` mode (uses batch statistics vs. running statistics) — this is exactly why `model.eval()` matters at evaluation time.
2. **`nn.Dropout(p=0.3)`** — during training, randomly zeroes each activation with probability 0.3 (and rescales the rest), forcing the network to not rely on any single neuron/feature combination — a strong, simple anti-overfitting technique. It's automatically disabled in `model.eval()` mode (all units active, no scaling needed).
3. **`weight_decay` on the optimizer** — adds an L2 penalty (`weight_decay * weight`) to every gradient update, shrinking weights toward zero each step unless the loss gradient opposes it. This discourages any single weight from growing large, a classical regularizer against overfitting, independent of BatchNorm/Dropout.

## Results comparison

Same 60k Fashion-MNIST split, same 100 epochs, run on GPU:

| | Video 8 (no regularization) | Video 9 (BatchNorm + Dropout + weight_decay) |
|---|---|---|
| Train accuracy | 0.9796 | 0.9325 |
| Test accuracy | 0.8869 | 0.8833 |
| Train/test gap | ~9.3 pts | ~4.9 pts |

> **Note:** Test accuracy is essentially unchanged, but the train/test gap shrinks substantially — this is the textbook signature of successful regularization: the model is no longer memorizing the training set as aggressively, even though raw test accuracy doesn't move much on this particular dataset/architecture.

## Key takeaways

- Regularization doesn't necessarily raise test accuracy — its signature is a shrinking train/test gap, which is exactly what happened here (~9.3 pts down to ~4.9 pts) while test accuracy stayed flat (0.8869 → 0.8833).
- `nn.BatchNorm1d` normalizes each mini-batch's activations to zero mean/unit variance (plus a learnable scale/shift), stabilizing training against internal covariate shift; it uses batch statistics in `train()` mode and running statistics in `eval()` mode.
- `nn.Dropout(p=0.3)` randomly zeroes 30% of activations during training to prevent reliance on any single neuron, and is automatically disabled during evaluation.
- `weight_decay` on the optimizer applies L2 regularization, shrinking weights toward zero on every update independently of BatchNorm and Dropout.
- Both BatchNorm and Dropout change behavior between training and evaluation modes, which is why calling `model.eval()` before evaluation (and `model.train()` before resuming training) is essential once these layers are in the network.
- Architecture, data, and training loop are otherwise identical to Video 8 — this video isolates the effect of the regularization stack alone.
