# Dataset & DataLoader Class in PyTorch

*Video 6 of "Practical Deep Learning using PyTorch" (CampusX) — [watch on YouTube](https://www.youtube.com/watch?v=RH6DeE3bY6I) · 51:42 · [Notebook A: Dataset/DataLoader demo (synthetic data)](https://colab.research.google.com/drive/1P7Nn_nZ2wVKERZxcf4V0JeTD8_BIPC6G) · [Notebook B: Breast Cancer pipeline rebuilt with Dataset/DataLoader](https://colab.research.google.com/drive/1RLSpxfu5hvjIcARxih0HelGlGr8xrEuw) · [Notes PDF](https://drive.google.com/file/d/1fILm74_ytGv5O06ZZEutD6cyd1mvL-Yj/view)*

This video introduces PyTorch's `Dataset` and `DataLoader` classes as the standard way to handle mini-batching, shuffling, and data loading — replacing the manual batching code from Video 5. It walks through a first-principles demo on synthetic data, then rebuilds the Breast Cancer training pipeline to use mini-batch gradient descent via `DataLoader`, and closes with notes on transforms, samplers, `collate_fn`, and the key `DataLoader` constructor parameters.

## Chapters
- 0:00 Intro
- 2:38 Recap
- 4:23 Problems in last code
- 7:02 A Simple Solution
- 9:23 Problem w current approach
- 13:00 Dataset and Dataloader Classes Explained
- 25:30 Code Demo / Example
- 33:30 A note about data transformations
- 38:28 A note about Samplers
- 41:36 A note about collate function
- 45:07 DataLoader important parameters
- 47:28 Improving existing code
- 51:25 Outro

## Recap: why mini-batching matters

The training loop built in earlier videos passes the entire dataset through the model in one shot each epoch. This has two problems:

1. **Memory inefficient** — the whole dataset (and all its intermediate activations) has to fit in memory/GPU at once.
2. **Worse convergence** — full-batch gradient descent lacks the noise that comes from per-batch gradient estimates, which in practice helps models converge better and faster.

The fix is to train on **batches of data** instead of the full dataset at once (mini-batch gradient descent).

## Problems with a hand-rolled batching approach

Writing your own batching/slicing logic on top of raw tensors runs into several issues:

1. No standard interface for data.
2. No easy way to apply transformations.
3. Shuffling and sampling isn't handled for you.
4. Batch management & parallelization has to be written by hand.

PyTorch's `Dataset` and `DataLoader` classes exist to solve exactly these problems: `Dataset` gives every dataset a standard interface, and `DataLoader` takes care of batching, shuffling, sampling, transforms, and parallel loading on top of it.

## Notebook A — Dataset & DataLoader from first principles (synthetic toy data)

```python
from sklearn.datasets import make_classification
import torch

X, y = make_classification(n_samples=10, n_features=2, n_informative=2,
                            n_redundant=0, n_classes=2, random_state=42)
X = torch.tensor(X, dtype=torch.float32)
y = torch.tensor(y, dtype=torch.long)

from torch.utils.data import Dataset, DataLoader

class CustomDataset(Dataset):
    def __init__(self, features, labels):
        self.features = features
        self.labels = labels
    def __len__(self):
        return self.features.shape[0]
    def __getitem__(self, index):
        return self.features[index], self.labels[index]

dataset = CustomDataset(X, y)
len(dataset)      # 10
dataset[2]        # (tensor([-2.8954, 1.9769]), tensor(0)) -- __getitem__ in action

dataloader = DataLoader(dataset, batch_size=2, shuffle=False)
for batch_features, batch_labels in dataloader:
    print(batch_features)
    print(batch_labels)
# Yields 5 batches of 2 samples each, in original order (shuffle=False)
```

This is the minimal contract every PyTorch `Dataset` must implement: `__init__` (store the data), `__len__` (total sample count — lets `DataLoader` know how many batches to make), and `__getitem__` (return one `(features, label)` pair by index — lets `DataLoader` randomly access samples for shuffling/batching). `DataLoader` wraps any `Dataset` and handles batching, shuffling, and (optionally) multiprocess loading via `num_workers`, without the user writing any indexing/slicing logic by hand.

## Notebook B — Breast Cancer pipeline rebuilt with Dataset/DataLoader + mini-batch training

```python
train_dataset = CustomDataset(X_train_tensor, y_train_tensor)
test_dataset = CustomDataset(X_test_tensor, y_test_tensor)

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=32, shuffle=True)

model = MySimpleNN(X_train_tensor.shape[1])   # same nn.Module from Video 5
optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
loss_function = nn.BCELoss()

for epoch in range(epochs):
    for batch_features, batch_labels in train_loader:      # <-- the key change: now looping over MINI-BATCHES, not the whole dataset at once
        y_pred = model(batch_features)
        loss = loss_function(y_pred, batch_labels.view(-1, 1))
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    print(f'Epoch: {epoch + 1}, Loss: {loss.item()}')   # loss of the LAST batch in the epoch, not an average

# Evaluation over the test_loader, batch by batch
model.eval()
accuracy_list = []
with torch.no_grad():
    for batch_features, batch_labels in test_loader:
        y_pred = model(batch_features)
        y_pred = (y_pred > 0.8).float()
        batch_accuracy = (y_pred.view(-1) == batch_labels).float().mean().item()
        accuracy_list.append(batch_accuracy)
overall_accuracy = sum(accuracy_list) / len(accuracy_list)
```

The structural change from Video 5 to Video 6 is the addition of an inner `for batch_features, batch_labels in train_loader:` loop inside the epoch loop. This is what makes training scale to datasets too large to fit in memory/GPU at once (the "memory inefficient" problem from the recap), and mini-batch gradient descent also tends to converge better/faster than full-batch training (the "better convergence" point) because of the regularizing noise from per-batch gradient estimates.

> **Note:** the printed loss each epoch (`loss.item()`) is the loss of the *last* batch processed in that epoch, not an average over all batches — worth keeping in mind when reading the per-epoch loss curve.

## Data transformations

`Dataset.__getitem__` is the natural place to apply per-sample transforms — for example `torchvision.transforms.Compose([...])` for images (normalization, augmentation) — so each sample is transformed lazily on access rather than all up front.

## Samplers

`DataLoader`'s `shuffle=True` is really sugar for a `RandomSampler` under the hood. A custom `Sampler` (or `WeightedRandomSampler`) lets you control the order or weighting with which samples are drawn — for example, to oversample a minority class.

## The `collate_fn`

`collate_fn` is the function `DataLoader` uses to merge a list of `__getitem__` outputs into one batch tensor. The default works fine for fixed-size samples, but a custom `collate_fn` is needed for variable-length data — for example, padding variable-length sequences to the max length in a batch, which becomes directly relevant later for the RNN/LSTM text data in Videos 13/14.

## Key `DataLoader` parameters

- `batch_size`
- `shuffle`
- `num_workers` — parallel data-loading processes
- `pin_memory` — faster host-to-GPU transfer
- `drop_last` — drop a final incomplete batch
- `collate_fn`

## Key takeaways

- Manual batching code (from Video 5) is memory-inefficient and converges worse than mini-batch training; PyTorch's `Dataset`/`DataLoader` pair is the standard fix.
- A `Dataset` subclass only needs `__init__`, `__len__`, and `__getitem__`; `DataLoader` wraps it to handle batching, shuffling, and parallel loading.
- Moving from full-batch to mini-batch training only requires adding an inner `for batch_features, batch_labels in train_loader:` loop inside the epoch loop — the rest of the training step (forward pass, loss, `zero_grad`/`backward`/`step`) is unchanged.
- Watch out for reading per-epoch printed loss as an average — as written, it's the loss of only the last batch in that epoch.
- `__getitem__` is the right place for per-sample transforms (e.g. `torchvision.transforms.Compose`), applied lazily on access.
- `shuffle=True` is sugar for a `RandomSampler`; custom `Sampler`/`WeightedRandomSampler` and a custom `collate_fn` (for variable-length data, e.g. padding) give finer control when needed.
