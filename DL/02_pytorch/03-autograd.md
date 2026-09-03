# PyTorch Autograd

*Video 3 of "Practical Deep Learning using PyTorch" (CampusX) · [YouTube](https://www.youtube.com/watch?v=BECZ0UB5AR0) · 54:18 · [Official Colab notebook](https://colab.research.google.com/drive/1022HrY0cW-DNMj3vG2n6-OjmRXtE8lh2)*

This video introduces Autograd, PyTorch's automatic differentiation engine, building up from manual derivative calculations to letting PyTorch compute gradients on its own — first for simple scalar functions, then for a chained function, then for a full logistic regression loss, and finally for a vector input. It closes with the practical mechanics every training loop needs: clearing accumulated gradients and the three ways to stop gradient tracking.

## Chapters

Only three chapters are manually marked on the video:

- 0:00 Intro
- 1:00 Why is Autograd Important?
- 13:49 What is Autograd?

## What Autograd is

Autograd is PyTorch's reverse-mode automatic differentiation engine. Every operation performed on a tensor with `requires_grad=True` is recorded into a dynamic computation graph — the result of each operation carries a `grad_fn` pointing back to how it was produced. Calling `.backward()` on the final output walks that graph backward, applying the chain rule at each step to populate `.grad` on every leaf tensor. This is exactly the mechanism that makes `loss.backward()` followed by an optimizer step work for training any PyTorch model (the subject of Video 4).

## Manual differentiation warm-up

Before reaching for autograd, the video first computes a derivative by hand, to have a baseline to check autograd against:

```python
def dy_dx(x):
    return 2*x
dy_dx(3)   # 6   (dy/dx of y = x^2 at x=3)
```

## Autograd basics — `requires_grad`, `.backward()`, `.grad`

The same derivative, computed by letting PyTorch track the operation and differentiate automatically:

```python
import torch
x = torch.tensor(3.0, requires_grad=True)
y = x**2                      # tensor(9., grad_fn=<PowBackward0>)
y.backward()                  # computes dy/dx via the autograd graph
x.grad                        # tensor(6.)
```

## Chained functions

Autograd's real value shows up once functions are composed. The video first works out the derivative of a chained function by hand with the chain rule, then reproduces it with autograd:

```python
import math
def dz_dx(x):
    return 2 * x * math.cos(x**2)
dz_dx(4)   # -7.661275842587077

x = torch.tensor(4.0, requires_grad=True)
y = x ** 2
z = torch.sin(y)
z.backward()
x.grad     # tensor(-7.6613)  -- matches manual derivative
```

> **Note:** Calling `.grad` on `y` (a non-leaf tensor) raises a `UserWarning`. Gradients are only retained on leaf tensors — those created directly with `requires_grad=True`, rather than derived from an operation — unless `.retain_grad()` is explicitly called on the intermediate tensor.

## Worked example — logistic regression on one data point

This is the core pedagogical example of the video: computing the gradient of a binary cross-entropy loss with respect to a weight `w` and bias `b`, first entirely by hand via the explicit chain rule (`dL/dy_pred * dy_pred/dz * dz/dw`), then letting autograd do the same work automatically.

Manual computation:

```python
x = torch.tensor(6.7); y = torch.tensor(0.0)     # input feature, true label
w = torch.tensor(1.0); b = torch.tensor(0.0)      # weight, bias

def binary_cross_entropy_loss(prediction, target):
    epsilon = 1e-8
    prediction = torch.clamp(prediction, epsilon, 1 - epsilon)
    return -(target * torch.log(prediction) + (1 - target) * torch.log(1 - prediction))

z = w * x + b
y_pred = torch.sigmoid(z)
loss = binary_cross_entropy_loss(y_pred, y)   # tensor(6.7012)

dloss_dy_pred = (y_pred - y) / (y_pred * (1 - y_pred))
dy_pred_dz = y_pred * (1 - y_pred)
dz_dw = x
dz_db = 1
dL_dw = dloss_dy_pred * dy_pred_dz * dz_dw     # 6.6918 (manual)
dL_db = dloss_dy_pred * dy_pred_dz * dz_db     # 0.9988 (manual)
```

Same computation with autograd doing the chain rule automatically:

```python
w = torch.tensor(1.0, requires_grad=True)
b = torch.tensor(0.0, requires_grad=True)
z = w*x + b
y_pred = torch.sigmoid(z)
loss = binary_cross_entropy_loss(y_pred, y)
loss.backward()
print(w.grad)   # tensor(6.6918) -- matches manual dL_dw
print(b.grad)   # tensor(0.9988) -- matches manual dL_db
```

The gradients from `w.grad` and `b.grad` match the manually derived `dL_dw` and `dL_db` exactly. Autograd reproduces precisely what manual chain-rule differentiation gives, but it scales to arbitrarily deep computation graphs without ever requiring a gradient to be hand-derived.

## Vector input

Autograd works the same way when the input is a vector rather than a scalar:

```python
x = torch.tensor([1.0, 2.0, 3.0], requires_grad=True)
y = (x**2).mean()
y.backward()
x.grad     # tensor([0.6667, 1.3333, 2.0000])   == 2x/3 elementwise
```

## Clearing accumulated gradients

Gradients accumulate on a tensor across successive `.backward()` calls, so they must be zeroed out before the next backward pass — otherwise each new call adds to whatever is already stored in `.grad`:

```python
x = torch.tensor(2.0, requires_grad=True)
y = x ** 2
y.backward()
x.grad          # tensor(4.)
x.grad.zero_()  # tensor(0.) -- must zero grads before the next backward() call, else they accumulate
```

## Stopping gradient tracking

There are three ways to stop autograd from tracking operations on a tensor:

```python
# option 1 - requires_grad_(False)   -- mutates the tensor in place, permanently disables tracking
x.requires_grad_(False)

# option 2 - detach()   -- returns a new tensor sharing data but detached from the graph
z = x.detach()

# option 3 - torch.no_grad()   -- context manager, disables tracking for the enclosed block only
# (standard usage, e.g. during evaluation/inference: `with torch.no_grad(): ...`)
```

## Key takeaways

- Autograd is reverse-mode automatic differentiation: ops on `requires_grad=True` tensors build a dynamic computation graph (`grad_fn`), and `.backward()` walks it backward applying the chain rule.
- `.grad` is populated only on leaf tensors (those created directly with `requires_grad=True`) — reading `.grad` on an intermediate, non-leaf tensor raises a `UserWarning` unless `.retain_grad()` was called.
- Across scalar, chained, logistic-regression, and vector examples, autograd's computed gradients matched the manually derived ones exactly — it automates the chain rule rather than approximating it.
- Gradients accumulate across `.backward()` calls, so `.grad` must be zeroed (e.g. `x.grad.zero_()`) before each new backward pass.
- Gradient tracking can be disabled three ways: `requires_grad_(False)` (permanent, in-place), `.detach()` (returns an untracked copy), or the `torch.no_grad()` context manager (scoped, standard for evaluation/inference).
- This `.backward()` + `.grad` mechanism is the same one that powers `loss.backward()` and the optimizer step in a full PyTorch training loop, covered in Video 4.
