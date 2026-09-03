# PyTorch Training Pipeline

*CampusX — "Practical Deep Learning using PyTorch" · Video 4 · [YouTube](https://www.youtube.com/watch?v=MKxEbbKpL5Q) · 30:21 · [Official Colab notebook](https://colab.research.google.com/drive/1SzmMiRYPPM1sIwu7YpHwHEvNDhU1ylNR)*

This video builds the canonical PyTorch training loop from scratch — no `torch.nn`, no `torch.optim` — using only raw tensors and autograd. It trains a logistic-regression-style binary classifier on the Breast Cancer Wisconsin dataset to establish the five-step training pattern (forward → loss → backward → update → zero_grad) that the rest of the course builds on.

## Chapters
- 0:00 Intro
- 0:44 Plan of Attack / Revision
- 4:07 Code Flow
- 5:45 Code Demo
- 28:04 Improvements
- 30:03 Outro

## Data loading and preprocessing

The dataset is the Breast Cancer Wisconsin dataset (569 rows × 33 columns), loaded directly from a public GitHub raw CSV rather than via `sklearn`'s bundled loader.

```python
import numpy as np, pandas as pd, torch
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder

df = pd.read_csv('https://raw.githubusercontent.com/gscdit/Breast-Cancer-Detection/refs/heads/master/data.csv')
df.drop(columns=['id', 'Unnamed: 32'], inplace=True)   # drop id + a stray empty trailing column

X_train, X_test, y_train, y_test = train_test_split(df.iloc[:, 1:], df.iloc[:, 0], test_size=0.2)

scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)     # fit + transform on train
X_test = scaler.transform(X_test)           # transform ONLY (no fit) on test -- avoids leakage

encoder = LabelEncoder()
y_train = encoder.fit_transform(y_train)    # 'M'/'B' -> 1/0
y_test = encoder.transform(y_test)

# NumPy -> PyTorch tensors
X_train_tensor = torch.from_numpy(X_train)
X_test_tensor  = torch.from_numpy(X_test)
y_train_tensor = torch.from_numpy(y_train)
y_test_tensor  = torch.from_numpy(y_test)
# X_train_tensor.shape -> torch.Size([455, 30]); y_train_tensor.shape -> torch.Size([455])
```

The `id` column and a stray empty trailing column (`Unnamed: 32`, an artifact of the CSV's trailing comma) are dropped before the split. `StandardScaler` is fit only on the training set and then just applied (`.transform`) to the test set, which avoids data leakage from test statistics into training. The `LabelEncoder` converts the diagnosis labels ('M'/'B') into 1/0.

## The model — written from scratch

No `torch.nn` is used here — that abstraction is introduced in Video 5. The model is a plain Python class holding raw tensors for its weights and bias, both with `requires_grad=True` so autograd can track them.

```python
class MySimpleNN():
    def __init__(self, X):
        self.weights = torch.rand(X.shape[1], 1, dtype=torch.float64, requires_grad=True)
        self.bias = torch.zeros(1, dtype=torch.float64, requires_grad=True)

    def forward(self, X):
        z = torch.matmul(X, self.weights) + self.bias
        y_pred = torch.sigmoid(z)
        return y_pred

    def loss_function(self, y_pred, y):
        epsilon = 1e-7
        y_pred = torch.clamp(y_pred, epsilon, 1 - epsilon)   # avoid log(0)
        loss = -(y * torch.log(y_pred) + (1 - y) * torch.log(1 - y_pred)).mean()
        return loss
```

`forward` computes a linear combination followed by a sigmoid, giving a logistic-regression-style prediction. `loss_function` implements binary cross-entropy by hand, clamping predictions away from exactly 0 or 1 first so `log(0)` never occurs.

## The training loop — the canonical pattern

This loop is the pattern the whole course is built around: forward pass, loss computation, backward pass, parameter update, and gradient reset — repeated every epoch.

```python
learning_rate = 0.1
epochs = 25

model = MySimpleNN(X_train_tensor)

for epoch in range(epochs):
    y_pred = model.forward(X_train_tensor)                 # 1. forward pass
    loss = model.loss_function(y_pred, y_train_tensor)     # 2. compute loss
    loss.backward()                                        # 3. backward pass (autograd)

    with torch.no_grad():                                  # 4. parameter update (no grad tracking on the update itself)
        model.weights -= learning_rate * model.weights.grad
        model.bias -= learning_rate * model.bias.grad

    model.weights.grad.zero_()                             # 5. zero gradients before next iteration
    model.bias.grad.zero_()

    print(f'Epoch: {epoch + 1}, Loss: {loss.item()}')
# Loss falls from 3.87 -> 0.749 over 25 epochs
```

The weight/bias update is wrapped in `torch.no_grad()` because the update itself is an in-place tensor operation that should not be tracked by autograd. Gradients are explicitly zeroed after each update — otherwise PyTorch would accumulate them across epochs instead of computing fresh gradients each time. Over 25 epochs, loss drops from 3.87 to 0.749.

## Evaluation

```python
with torch.no_grad():
    y_pred = model.forward(X_test_tensor)
    y_pred = (y_pred > 0.9).float()          # threshold at 0.9 (unusually high threshold; discussed as an "improvement" candidate)
    accuracy = (y_pred == y_test_tensor).float().mean()
    print(f'Accuracy: {accuracy.item()}')    # 0.6379 -- deliberately mediocre baseline, to motivate Video 5's improvements (nn.Module, nn.Linear, optim)
```

> **Note:** The classification threshold here is set unusually high at 0.9 rather than the conventional 0.5. This is called out explicitly in the video as a candidate for improvement, not a mistake to silently work around.

The resulting accuracy — 0.6379 — is deliberately mediocre. This baseline is intentionally left unoptimized: it exists to motivate the improvements covered in Video 5.

## Improvements (foreshadowed, not implemented here)

The "Improvements" chapter (28:04) is discussed verbally rather than coded. It foreshadows replacing the manually-managed `weights`/`bias` tensors with `torch.nn.Linear`, and replacing the manual gradient-descent update step with `torch.optim` — exactly the content of Video 5.

## Key takeaways

- The five-step PyTorch training loop — forward pass → compute loss → backward pass → update parameters → zero gradients — is the pattern every later video in this course reuses, just with progressively more abstraction.
- Parameter updates must happen inside `torch.no_grad()`, since the update is an in-place operation that shouldn't itself be tracked by autograd.
- Gradients accumulate by default in PyTorch, so `.grad.zero_()` must be called explicitly after each update or gradients from previous epochs will corrupt the next step.
- `StandardScaler` should be fit only on training data and merely applied (`.transform`) to test data, to avoid leaking test-set statistics into training.
- Binary cross-entropy implemented by hand needs predictions clamped away from 0 and 1 (`torch.clamp(y_pred, epsilon, 1-epsilon)`) to avoid `log(0)`.
- The 0.6379 test accuracy and the unusually high 0.9 decision threshold are intentional weaknesses in this "from scratch" baseline, meant to be fixed in Video 5 by introducing `nn.Module`, `nn.Linear`, and `torch.optim`.
