# Building a CNN using PyTorch

*CampusX — "Practical Deep Learning using PyTorch" (Video 11/14) · [YouTube](https://www.youtube.com/watch?v=hkiBZLRFvO4) · 32:22 · [Colab notebook](https://colab.research.google.com/drive/1uRUPZFQwiBxEQCCiLNQCFtk7b4L_7N_E)*

This video keeps the Fashion-MNIST setup from Videos 7-10 (60k rows, GPU training) but swaps the flat-MLP architecture for a convolutional one, which requires reshaping the data back into 2D images and introduces `Conv2d`, `MaxPool2d`, and a feature-extraction/classification split.

## Chapters
- 0:00 Recap
- 3:50 Plan of Action
- 5:46 Prerequisite
- 7:10 What is CNN
- 13:36 CNN Architecture & Code Demo
- 16:17 Modifying existing code for CNN architecture in PyTorch
- 17:17 Converting 1D image data into 2D for CNN processing
- 19:03 Building a CNN architecture divided into feature extraction and classification
- 20:07 Adding layers for feature extraction in CNN architecture
- 21:59 Constructing the first convolutional layer with filters and activation functions
- 23:08 Duplicate the first layer to create a second convolutional layer
- 24:56 Building the classification stage with hidden and flattened layers in CNN
- 25:48 Understanding tensor dimensions for CNN input processing
- 28:01 Creating a CNN architecture with hidden layers and activation functions
- 29:00 Implementing dropout layers to prevent overfitting in CNN architecture
- 30:56 CNN optimizes image data performance, achieving 99.9% accuracy

## Why CNNs beat flat MLPs on images

A flattened 784-vector MLP discards all 2D spatial structure. A `Conv2d` kernel instead slides a small learnable filter across the image, so nearby pixels are processed together and the same filter (weight sharing) detects a pattern — an edge, a texture — anywhere in the image. This gives far fewer parameters per layer than a fully-connected layer of comparable receptive field, plus translation-invariant feature detection.

## Code demo

Same Fashion-MNIST setup (60k rows, GPU), but with a **shape change** and a **convolutional** architecture instead of the flat-MLP approach of Videos 7-10:

```python
class CustomDataset(Dataset):
    def __init__(self, features, labels):
        # key difference from every prior video: reshape flat 784-length rows into (1, 28, 28) image tensors
        self.features = torch.tensor(features, dtype=torch.float32).reshape(-1, 1, 28, 28)   # (N, channels=1, H=28, W=28)
        self.labels = torch.tensor(labels, dtype=torch.long)
    def __len__(self):
        return len(self.features)
    def __getitem__(self, index):
        return self.features[index], self.labels[index]

class MyNN(nn.Module):
    def __init__(self, input_features):
        super().__init__()

        self.features = nn.Sequential(              # "feature extraction" stage
            nn.Conv2d(input_features, 32, kernel_size=3, padding='same'),   # 1 -> 32 channels, 3x3 kernel, 'same' padding keeps spatial size
            nn.ReLU(),
            nn.BatchNorm2d(32),
            nn.MaxPool2d(kernel_size=2, stride=2),   # 28x28 -> 14x14

            nn.Conv2d(32, 64, kernel_size=3, padding='same'),               # 32 -> 64 channels
            nn.ReLU(),
            nn.BatchNorm2d(64),
            nn.MaxPool2d(kernel_size=2, stride=2)    # 14x14 -> 7x7
        )
        self.classifier = nn.Sequential(             # "classification" stage
            nn.Flatten(),                            # (N, 64, 7, 7) -> (N, 64*7*7=3136)
            nn.Linear(64*7*7, 128),
            nn.ReLU(),
            nn.Dropout(p=0.4),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(p=0.4),
            nn.Linear(64, 10)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

model = MyNN(1).to(device)          # input_features=1 -> grayscale channel count
criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(model.parameters(), lr=0.01, weight_decay=1e-4)

# training loop identical in shape to every previous video (forward -> loss -> zero_grad -> backward -> step)
# Loss: 0.645 -> 0.014 over 100 epochs
```

The `CustomDataset` reshape is the only data-pipeline change needed to go from MLP to CNN: the flat 784-length rows become `(1, 28, 28)` image tensors so `Conv2d` has spatial structure to work on. Everything downstream — the `Dataset`/`DataLoader` plumbing and the training loop (forward → loss → zero_grad → backward → step) — stays identical in shape to every previous video.

## CNN building blocks

- **`nn.Conv2d(in_channels, out_channels, kernel_size, padding='same')`**: `out_channels` is the number of learned filters (feature maps) produced. `padding='same'` pads the input so the output spatial size matches the input size, as opposed to `padding=0` which shrinks the map by `kernel_size - 1`.
- **`nn.MaxPool2d(kernel_size=2, stride=2)`**: downsamples each feature map by taking the max over non-overlapping 2x2 windows, halving spatial resolution. This reduces computation and adds a small amount of translation invariance.
- **Two-stage architecture (`features` + `classifier`)**: the standard CNN pattern. Convolutional/pooling layers extract spatial features and progressively reduce H/W while increasing channel depth (1 → 32 → 64), then `Flatten()` collapses the final feature map to a vector for ordinary `Linear` layers to classify.

## Tensor shape bookkeeping

This is the "Understanding tensor dimensions" chapter, and it's the part that trips people up most when building a CNN classifier head:

- Input: `(N, 1, 28, 28)`
- After conv block 1 + pool: `(N, 32, 14, 14)`
- After conv block 2 + pool: `(N, 64, 7, 7)`
- Flatten: `(N, 64*7*7 = 3136)` → classifier head

Getting `64*7*7` right — or more generally `channels * H * W` after the last pooling layer — is the most common source of shape-mismatch errors when wiring up the `Flatten()` -> `Linear` transition.

## Results

- Train accuracy: **0.99994** (essentially memorized the training set)
- Test accuracy: **0.9262** — clearly better than every MLP variant in Videos 7-10 (best MLP test accuracy was ~0.891 from Optuna tuning), despite a huge train/test gap.

## Key takeaways

- Switching from an MLP to a CNN on the same Fashion-MNIST data requires only one data-pipeline change: reshaping flat 784-vectors into `(1, 28, 28)` image tensors so `Conv2d` has spatial structure to operate on.
- Convolution's weight sharing (the same small filter slides across the whole image) gives far fewer parameters than a comparable fully-connected layer, plus translation-invariant feature detection.
- The `features` (Conv2d + ReLU + BatchNorm2d + MaxPool2d, x2) → `classifier` (Flatten + Linear layers) two-stage pattern is the standard CNN architecture shape.
- Careful tensor shape tracking through the conv/pool stack — here `(N,1,28,28)` → `(N,32,14,14)` → `(N,64,7,7)` → flattened `(N,3136)` — is essential to avoid shape mismatches at the `Flatten()` → `Linear` boundary.
- The CNN reached 0.9262 test accuracy versus ~0.891 for the best-tuned MLP from Videos 7-10, a clear jump from exploiting spatial structure instead of a flat 784-vector.
- The train/test gap (0.99994 vs 0.9262) is even larger than in the MLP videos, showing the CNN's higher capacity still needs regularization (BatchNorm2d and Dropout are already present here, but the gap persists).
