# PyTorch NN Module

*Video 5 of "Practical Deep Learning using PyTorch" (CampusX) · [YouTube](https://www.youtube.com/watch?v=CAgWNxlmYsc) · 39:27 · [Notebook A — nn.Module demo](https://colab.research.google.com/drive/1j9JVaahEDkzwmR0GR3OE7-khODnUgPeL) · [Notebook B — full training pipeline](https://colab.research.google.com/drive/1uWcLqI3RYI_E3u6H4Y-SftA7QS__Dv-3) · [Notes PDF](https://drive.google.com/file/d/130QErzy76HcLM4PncZJDx2HPF2QrB1AJ/view)*

This video takes the manual tensor/autograd training pipeline built in Videos 1-4 and rebuilds it using `torch.nn` and `torch.optim` — PyTorch's built-in building blocks for layers, activations, loss functions, and optimizers. The core idea: the training loop's shape stays identical, but hand-written weight tensors, loss math, and gradient-descent updates are replaced by library primitives.

## Chapters

This video has no manually-defined chapter markers on YouTube (unlike Videos 1-4). The notes below follow the presenter's own "Plan of Action" slide instead:

1. Revision
2. Improvements
3. The nn module
4. The torch.optim module

## The `nn` module

`torch.nn` is a core PyTorch library that provides a wide array of classes and functions for building neural networks efficiently. It abstracts away the complexity of creating and training networks by offering pre-built layers, loss functions, activation functions, and other utilities, letting you focus on designing and experimenting with model architectures instead of hand-rolling the math.

Key components of `torch.nn`:

1. **Modules (Layers)** — `nn.Module` is the base class for all neural network modules; custom models and layers subclass it. Common layers include `nn.Linear` (fully connected), `nn.Conv2d` (convolutional), `nn.LSTM` (recurrent), and many others.
2. **Activation Functions** — `nn.ReLU`, `nn.Sigmoid`, `nn.Tanh` introduce non-linearities.
3. **Loss Functions** — `nn.CrossEntropyLoss`, `nn.MSELoss`, `nn.NLLLoss` quantify the difference between predictions and targets.
4. **Container Modules** — `nn.Sequential` stacks layers in order.
5. **Regularization and Dropout** — `nn.Dropout`, `nn.BatchNorm2d` help prevent overfitting and improve generalization.

The "Improvements" this video makes over the previous videos' pipeline are, in order: building the network using the `nn` module, using a built-in activation function, using a built-in loss function, and using a built-in optimizer.

## The `torch.optim` module

`torch.optim` provides ready-made optimization algorithms so you don't have to hand-write the parameter-update step. The standard pattern — confirmed by the actual optimizer usage in Notebook B — is `torch.optim.SGD(model.parameters(), lr=...)`, with `torch.optim.Adam` typically introduced as the more commonly used adaptive optimizer. Both follow the same 3-line pattern:

```
optimizer.zero_grad()
loss.backward()
optimizer.step()
```

This replaces the manual `-= lr * grad` update and the manual `.grad.zero_()` calls used in Video 4.

## Notebook A — `nn.Module` basics

A small demo (not the full training pipeline) showing how to define a model as an `nn.Module` subclass:

```python
import torch
import torch.nn as nn

class Model(nn.Module):
    def __init__(self, num_features):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(num_features, 3),
            nn.ReLU(),
            nn.Linear(3, 1),
            nn.Sigmoid()
        )
    def forward(self, features):
        return self.network(features)

features = torch.rand(10, 5)
model = Model(features.shape[1])
model(features)                 # calling model(x) invokes forward() via nn.Module's __call__ -- prefer this over model.forward(x) directly
model.linear2.weight            # inspect a layer's learnable weight (Parameter, requires_grad=True)

!pip install torchinfo
from torchinfo import summary
summary(model, input_size=(10, 5))
# Model: Linear(5->3): 18 params, ReLU, Linear(3->1): 4 params, Sigmoid -> Total 22 params
```

> **Note:** the model here is named `Model` with an `nn.Sequential` attribute called `network`, but `model.linear2.weight` implies the notebook also has (or uses, in a slightly different version) named layers `linear1`/`linear2` rather than `network[0]`/`network[2]`. Both common `nn.Module` styles — named submodules vs. `nn.Sequential` — are demonstrated across the video; when addressing a layer inside an `nn.Sequential`, use `model.network[0].weight`.

## Notebook B — full training pipeline with `nn.Module` + `torch.optim`

Same Breast Cancer dataset pipeline as Video 4, now rebuilt properly:

```python
import torch.nn as nn

# tensors now created as float32 explicitly (Video 4 used float64 by default, then had to work around dtype mismatches)
X_train_tensor = torch.from_numpy(X_train.astype(np.float32))
y_train_tensor = torch.from_numpy(y_train.astype(np.float32))

class MySimpleNN(nn.Module):
    def __init__(self, num_features):
        super().__init__()
        self.linear = nn.Linear(num_features, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, features):
        out = self.linear(features)
        out = self.sigmoid(out)
        return out

learning_rate = 0.1
epochs = 25
loss_function = nn.BCELoss()                                    # built-in loss, replaces the hand-written BCE from Video 3/4

model = MySimpleNN(X_train_tensor.shape[1])
optimizer = torch.optim.SGD(model.parameters(), lr=learning_rate)   # built-in optimizer, replaces manual weight -= lr*grad

for epoch in range(epochs):
    y_pred = model(X_train_tensor)
    loss = loss_function(y_pred, y_train_tensor.view(-1, 1))    # .view(-1,1) reshapes labels to match prediction shape [N,1]

    optimizer.zero_grad()     # clear old gradients (equivalent to the two .grad.zero_() calls in Video 4)
    loss.backward()
    optimizer.step()          # applies the update (equivalent to the manual `with torch.no_grad(): weights -= lr*grad`)

    print(f'Epoch: {epoch + 1}, Loss: {loss.item()}')
# Loss falls from 0.8196 -> 0.1750 over 25 epochs -- much smoother/lower than Video 4's raw version

with torch.no_grad():
    y_pred = model.forward(X_test_tensor)
    y_pred = (y_pred > 0.5).float()          # note: 0.5 threshold here (Video 4 used an unusual 0.9)
    accuracy = (y_pred == y_test_tensor).float().mean()
    print(f'Accuracy: {accuracy.item()}')    # 0.5526
```

> **Note:** these accuracy numbers (0.64 in Video 4 at a 0.9 threshold, 0.55 here at a 0.5 threshold) are lower than a well-tuned model would get on this dataset. That's expected — this video's own "Improvements" chapter and Videos 6-9 later in the playlist address exactly this gap, with proper batching/`DataLoader`, GPU training, and hyperparameter tuning. Treat these numbers as the pedagogical baseline the rest of the course improves on, not as a target to reproduce.

## Key takeaways

- `torch.nn` supplies the building blocks — `nn.Module` (base class for models/layers), `nn.Linear`, activation functions (`nn.ReLU`, `nn.Sigmoid`, `nn.Tanh`), loss functions (`nn.BCELoss`, `nn.CrossEntropyLoss`, `nn.MSELoss`), container modules (`nn.Sequential`), and regularization layers (`nn.Dropout`, `nn.BatchNorm2d`).
- A custom model subclasses `nn.Module`, defines its layers in `__init__` (after calling `super().__init__()`), and defines the forward pass in `forward()`. Call the model as `model(features)` rather than `model.forward(features)` directly, since `__call__` is what wires up `nn.Module`'s internals.
- `torch.optim` (e.g. `torch.optim.SGD(model.parameters(), lr=...)`) replaces manual gradient-descent updates with the standard `optimizer.zero_grad()` → `loss.backward()` → `optimizer.step()` pattern.
- The conceptual delta from Video 4 to Video 5: `nn.Module` + `nn.Linear`/`nn.Sigmoid` replace hand-rolled weight tensors, `nn.BCELoss` replaces the hand-written loss function, and `torch.optim.SGD` replaces the manual weight update — but the training loop's shape (forward → loss → backward → step → zero_grad) is unchanged. `nn` and `optim` are ergonomics layered on top of the same autograd mechanics introduced in Video 3.
- Two equivalent ways to structure a model are shown: named submodules (`self.linear`, `self.sigmoid`) accessed directly, versus an `nn.Sequential` container accessed by index (`model.network[0].weight`).
- Tensors should be created as `float32` explicitly (as done in Notebook B) to avoid the dtype mismatches that came up in Video 4, which defaulted to `float64`.
