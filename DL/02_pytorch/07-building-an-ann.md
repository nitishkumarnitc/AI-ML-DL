# Building an ANN using PyTorch

*[CampusX — Practical Deep Learning using PyTorch, Video 7](https://www.youtube.com/watch?v=6EJaHBJhwDs) · 39:23 · [Colab notebook](https://colab.research.google.com/drive/1REudoW3X8RNA53vf8j_pir540JyzB7uR)*

This video builds the series' first multi-class classifier: a 3-layer feedforward neural network trained on Fashion-MNIST (10 classes), moving beyond the binary, single-`Linear`-layer models used in Videos 4-6.

## Chapters
- 0:00 Intro
- 0:40 Recap & Plan of action
- 3:00 The Dataset - Fashion MNIST
- 4:10 Code Plan & Demo
- 20:00 Before Training the NN
- 31:57 What is the output

## Dataset

Fashion-MNIST, small CSV variant (`fmnist_small.csv`): 784 pixel columns + 1 label column, 10 classes.

## Full walkthrough

The "Before Training the NN" chapter (20:00) covers the dataset loading, scaling, and model-definition code below; "What is the output" (31:57) covers the `torch.max` / accuracy-evaluation block at the end.

```python
import pandas as pd
from sklearn.model_selection import train_test_split
import torch
from torch.utils.data import Dataset, DataLoader
import torch.nn as nn
import torch.optim as optim
import matplotlib.pyplot as plt

torch.manual_seed(42)
df = pd.read_csv('fmnist_small.csv')

# visualize first 16 images as a 4x4 grid
fig, axes = plt.subplots(4, 4, figsize=(10, 10))
for i, ax in enumerate(axes.flat):
    img = df.iloc[i, 1:].values.reshape(28, 28)
    ax.imshow(img)
    ax.set_title(f"Label: {df.iloc[i, 0]}")

X = df.iloc[:, 1:].values
y = df.iloc[:, 0].values
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# scale pixel values to [0,1] by dividing by 255 (min-max scaling for images -- simpler than StandardScaler here)
X_train = X_train / 255.0
X_test = X_test / 255.0

class CustomDataset(Dataset):
    def __init__(self, features, labels):
        self.features = torch.tensor(features, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.long)   # long dtype required by nn.CrossEntropyLoss
    def __len__(self):
        return len(self.features)
    def __getitem__(self, index):
        return self.features[index], self.labels[index]

train_dataset = CustomDataset(X_train, y_train)
test_dataset = CustomDataset(X_test, y_test)
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)   # no need to shuffle test data

class MyNN(nn.Module):
    def __init__(self, num_features):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(num_features, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 10)          # 10 output logits, one per class -- NO final Sigmoid/Softmax
        )
    def forward(self, x):
        return self.model(x)

epochs = 100
learning_rate = 0.1
model = MyNN(X_train.shape[1])          # 784 input features (28x28 flattened)
criterion = nn.CrossEntropyLoss()       # expects raw logits + integer class labels; applies softmax internally
optimizer = optim.SGD(model.parameters(), lr=learning_rate)

for epoch in range(epochs):
    total_epoch_loss = 0
    for batch_features, batch_labels in train_loader:
        outputs = model(batch_features)
        loss = criterion(outputs, batch_labels)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        total_epoch_loss += loss.item()
    avg_loss = total_epoch_loss / len(train_loader)
    print(f'Epoch: {epoch + 1}, Loss: {avg_loss}')
# Loss falls 1.32 -> 0.008 over 100 epochs (near-zero training loss -- flags overfitting, addressed in Video 9)

model.eval()
total = correct = 0
with torch.no_grad():
    for batch_features, batch_labels in test_loader:
        outputs = model(batch_features)
        _, predicted = torch.max(outputs, 1)     # argmax over the 10 class logits
        total += batch_labels.shape[0]
        correct += (predicted == batch_labels).sum().item()
print(correct / total)   # Test accuracy: 0.8325
```

## Key concepts

- **Multi-class classification.** This is the first video in the series to go beyond two classes (Fashion-MNIST has 10). It uses `nn.CrossEntropyLoss` instead of `nn.BCELoss`, with a final layer of raw logits and no `Sigmoid`, since `CrossEntropyLoss` internally applies `log_softmax`.
- **A deeper network.** The model is the first 3-layer MLP in the series (`784 -> 128 -> 64 -> 10`) with `ReLU` between hidden layers, deeper and wider than the single-`Linear`-layer models used in Videos 4-6.
- **`torch.max(outputs, 1)`.** This is the standard PyTorch idiom for turning class logits into a predicted class index — it takes the argmax along the class dimension.

> **Note:** Training loss drops to roughly 0.008 while test accuracy plateaus at 0.8325 — a textbook train/test gap. This overfitting signal is the natural setup for Video 9, "Optimizing the Neural Network," which covers regularization and dropout.

## Key takeaways

- This is the series' first multi-class problem (Fashion-MNIST, 10 classes), which is why the loss function switches from `nn.BCELoss` to `nn.CrossEntropyLoss` and the output layer emits raw logits rather than a sigmoid probability.
- `nn.CrossEntropyLoss` expects raw logits (no activation on the final layer) plus integer class labels (`dtype=torch.long`), since it applies `log_softmax` internally.
- The model architecture steps up in depth and width compared to earlier videos: a 3-layer MLP (`784 -> 128 -> 64 -> 10`) with `ReLU` activations between hidden layers.
- Pixel values are scaled to `[0, 1]` by simple division by 255, a lighter-weight alternative to `StandardScaler` that works well for image data.
- `torch.max(outputs, 1)` is the idiomatic way to convert logits into predicted class indices via argmax.
- After 100 epochs, training loss falls from 1.32 to 0.008 while test accuracy reaches only 0.8325 — a clear overfitting gap that motivates the regularization techniques covered in Video 9.
