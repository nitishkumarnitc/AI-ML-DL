# Transfer Learning using PyTorch

*CampusX — "Practical Deep Learning using PyTorch" (Video 12/14) · [YouTube](https://www.youtube.com/watch?v=aPu6a5htRXM) · 53:17 · [Primary Colab notebook](https://colab.research.google.com/drive/196F8ZuAdbeS9_96v3dLpf9oCpMLEuRwB) · [Bonus Colab notebook](https://colab.research.google.com/drive/1AWdxO9qNBpzdQlt-xSznFmr5k9e-uUTz)*

This video introduces transfer learning: instead of training a CNN from scratch, it takes a pretrained **VGG16** (trained on ImageNet) and adapts it to the 10-class Fashion-MNIST task by freezing the convolutional backbone and training only a new classifier head. A supplementary bonus notebook (not transfer learning) revisits Optuna-tuned CNNs with data augmentation.

## Chapters
- 0:00 Intro/Recap
- 2:50 Plan of Action
- 4:28 What is Transfer Learning
- 10:08 Why does Transfer learning work?
- 15:12 Workflow
- 25:21 Code Demo
- 53:08 Outro

## What is transfer learning

Transfer learning means reusing a model's weights learned on a large source task/dataset — here, VGG16 on ImageNet (1.2M images, 1000 classes) — as a starting point for a new, usually smaller, target task (here, 10-class Fashion-MNIST), instead of training from random initialization.

**Why it works**: the early/middle convolutional layers of an image classifier learn increasingly generic visual features (edges, textures, shapes) that transfer across visually-related domains. Only the final task-specific layers need to be relearned for a new label set.

**Two common workflows**:
- **Feature extraction** (used in this notebook): freeze the pretrained backbone entirely (`requires_grad=False`) and train only a new classifier head — cheap, fast, and good when the target dataset is small.
- **Fine-tuning**: unfreeze some or all of the backbone and train it (usually with a small learning rate) alongside the new head — more compute, often better accuracy when the target dataset is larger or more different from the source domain.

## Code demo — transfer learning with VGG16

Uses the small 6,000-row Fashion-MNIST sample (`fmnist_small.csv`), and adapts it to a pretrained **VGG16** (trained on ImageNet, 3-channel 224x224 inputs) instead of training a CNN from scratch.

A pretrained model's *input contract* (channel count, spatial size, normalization statistics) is fixed by how it was originally trained. Feeding it differently-shaped or differently-scaled data without adapting it silently degrades accuracy rather than throwing an error — hence the fake-RGB conversion and the resize/crop/normalize pipeline below, which map Fashion-MNIST's 28x28 grayscale images onto VGG16's expected 224x224x3 ImageNet-normalized input.

```python
from torchvision.transforms import transforms
custom_transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),                                    # VGG16 expects 224x224 input
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])  # ImageNet's channel mean/std -- must match what VGG16 was trained with
])

class CustomDataset(Dataset):
    def __init__(self, features, labels, transform):
        self.features = features; self.labels = labels; self.transform = transform
    def __len__(self):
        return len(self.features)
    def __getitem__(self, index):
        image = self.features[index].reshape(28, 28).astype(np.uint8)
        image = np.stack([image]*3, axis=-1)      # grayscale (28,28) -> fake-RGB (28,28,3) by repeating the channel 3x -- VGG16 needs 3 input channels
        image = Image.fromarray(image)
        image = self.transform(image)             # resize/crop/normalize to VGG16's expected input
        return image, torch.tensor(self.labels[index], dtype=torch.long)

import torchvision.models as models
vgg16 = models.vgg16(pretrained=True)             # downloads ImageNet-pretrained weights (~528MB)

for param in vgg16.features.parameters():
    param.requires_grad = False                  # FREEZE the convolutional feature-extractor -- only the new head will be trained

vgg16.classifier = nn.Sequential(                 # REPLACE the original 1000-class ImageNet head with a new 10-class head
    nn.Linear(25088, 1024), nn.ReLU(), nn.Dropout(0.5),
    nn.Linear(1024, 512), nn.ReLU(), nn.Dropout(0.5),
    nn.Linear(512, 10)
)
vgg16 = vgg16.to(device)

optimizer = optim.Adam(vgg16.classifier.parameters(), lr=0.0001)   # optimizer only receives classifier params -- frozen features are never updated regardless
criterion = nn.CrossEntropyLoss()

for epoch in range(epochs):                        # epochs = 10
    for batch_features, batch_labels in train_loader:
        ...
        loss.backward(); optimizer.step()
        break        # <-- see bug note below
```

> **Note:** This notebook has two bugs worth flagging rather than silently reproducing.
>
> 1. There's a stray, unconditional `break` right after the first batch of every epoch, so each "epoch" actually trains on only **one 32-sample batch**, not the full training set. The printed per-epoch losses (0.0153 → 0.0116) are real but reflect training on a tiny fraction of the data, not a meaningful 10-epoch run. Removing the `break` gives a genuine full-dataset training loop.
> 2. The training-accuracy evaluation cell at the very end calls `model(batch_features)`, but `model` was never defined in this notebook — the model here is `vgg16`. That cell would raise a `NameError` if run. The test-accuracy cell above it correctly uses `vgg16(batch_features)`.
>
> The pattern to take away — freeze the backbone, replace the head, train only the head — is the lesson here, not the specific loss numbers, which don't reflect a full training run because of bug #1.

## Bonus notebook — dynamic CNN + Optuna + data augmentation (supplementary)

This is a separate, more advanced exercise combining ideas from Videos 10 and 11, and is **not** transfer learning. It builds a `DynamicCNN` class parametrized over `num_conv_layers`, `num_filters`, `kernel_size`, `num_fc_layers`, `fc_layer_size`, and `dropout_rate` — the same "build the architecture from hyperparameters" pattern as Video 10's `MyNN` — plus `torchvision.transforms` data augmentation applied to the training set only (`RandomRotation(10)`, `RandomHorizontalFlip(p=0.5)`, `RandomAffine(0, translate=(0.1,0.1))`; augmentation is deliberately *not* applied to the test set).

The architecture is tuned via Optuna with a `MedianPruner` over 50 trials. Unlike Video 10, the optimizer selection here is correctly wired: `optimizer = optim.SGD/Adam/RMSprop(...)` is actually assigned, not discarded.

The best trial found ~0.922 test accuracy (`num_conv_layers=3, num_filters=64, kernel_size=5, optimizer='Adam', lr≈0.000256`) — the best result across the whole course's Fashion-MNIST experiments:

| Experiment | Test accuracy |
|---|---|
| Video 7 MLP | 0.83 |
| Video 9 regularized MLP | 0.88 |
| Video 10 Optuna-MLP | 0.89 |
| Video 11 plain CNN | 0.926 |
| This bonus tuned+augmented CNN | 0.922 |

This roughly matches Video 11's already-strong CNN, with the main value being a demonstrably correct Optuna wiring to contrast against Video 10's bug.

## Key takeaways

- Transfer learning reuses a pretrained model's weights (VGG16 on ImageNet) as a starting point for a new, smaller target task (10-class Fashion-MNIST) instead of training from scratch.
- It works because early/middle convolutional layers learn generic visual features (edges, textures, shapes) that transfer across domains; only the final layers need to be relearned.
- Feature extraction (freeze backbone, train only a new head) is cheap and works well for small target datasets; fine-tuning (unfreeze backbone, train with a small LR) costs more but can do better on larger/more-different target datasets.
- A pretrained model's input contract — channel count, spatial size, normalization stats — must be matched exactly (here: grayscale-to-fake-RGB, resize to 224x224, ImageNet mean/std normalization), or accuracy silently degrades without an error.
- This notebook's training loop has a bug: an unconditional `break` limits every "epoch" to a single batch, so the reported losses don't reflect a real 10-epoch run — the takeaway is the freeze-backbone/replace-head/train-head pattern, not those numbers.
- The supplementary bonus notebook (not transfer learning) shows a correctly-wired Optuna search over a dynamic CNN with train-only data augmentation, reaching ~0.922 test accuracy — on par with Video 11's plain CNN and the strongest result in the course's Fashion-MNIST series.
