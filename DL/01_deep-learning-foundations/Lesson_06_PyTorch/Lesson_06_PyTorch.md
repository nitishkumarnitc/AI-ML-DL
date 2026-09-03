# Deep Learning with Keras and TensorFlow — Lesson 06: PyTorch

> Study notes expanded from the instructor slide deck *"Lesson 06 – PyTorch"* (46 slides). Terse bullet points have been turned into explanatory prose, with clarifying examples and runnable code so the document stands on its own.

## Learning Objectives

By the end of this lesson, you should be able to:

- **Identify** the applications of PyTorch libraries in enhancing computer vision and natural language processing (NLP) tasks.
- **Optimize** neural network models for image and sequence processing by selecting effective activation functions.
- **Implement** pooling and normalization techniques to improve the accuracy and efficiency of deep learning models.
- **Employ** loss functions and optimizer modules to refine the training process and enhance model performance.

These objectives map directly onto the four pillars of PyTorch that the rest of the lesson explores: the **tensor** data structure, the **`nn`** module (layers, activations, pooling, normalization), the **loss function** modules, and the **`optim`** module.

## Business Scenario

XYZ Inc. is building a **real-time fraud detection system** on top of PyTorch. The scenario ties every technical topic in this lesson to a concrete business need:

- They use PyTorch's **tensor** class as the core data structure for manipulating transaction data (numeric features, embeddings, sequences of events, etc.).
- They rely on **Autograd** (automatic differentiation), **Optim** (optimizers), and **NN** (neural network layers) modules for training and iterating on models quickly.
- Because fraud detection involves **huge transaction volumes**, they use **data parallelism across multiple GPUs** so training scales horizontally instead of being bottlenecked by a single device.
- Fraud datasets are almost always **imbalanced** (fraudulent transactions are rare compared to legitimate ones), so they lean on techniques such as **dropout** and **batch normalization** to keep the model from overfitting to the majority class and to keep training numerically stable.

The takeaway: PyTorch isn't just an academic tool — its combination of flexible tensors, automatic differentiation, GPU scaling, and regularization primitives is exactly what production systems like fraud detection need.

## Introduction to PyTorch

### What Is PyTorch?

**PyTorch** is an open-source deep learning framework originally developed by Facebook's (Meta's) AI Research lab. It is widely used for:

- **Computer vision** (image classification, object detection, segmentation)
- **Natural language processing** (text classification, translation, transformers)
- **Reinforcement learning** (training agents through reward-based feedback)

At its core, PyTorch gives you two things every deep learning framework needs: a tensor library that runs efficiently on CPU/GPU, and an automatic differentiation engine (**Autograd**) that computes gradients for you so you don't have to derive backpropagation by hand.

### Why PyTorch? (Key Strengths)

The slides call out four features that make PyTorch a powerful and versatile tool for developing and deploying machine learning models:

1. **Pythonic nature** — PyTorch code reads like ordinary Python. Model classes are plain Python classes, loops are plain Python `for` loops, and debugging can be done with standard tools like `pdb` or even `print()` statements, because there's no separate "graph compilation" step hiding what's happening.
2. **Stronger community support for research** — Because PyTorch exposes low-level operations naturally and its dynamic graph makes experimentation easy, most cutting-edge research papers (especially in NLP and CV) publish PyTorch implementations first.
3. **Dynamic computation graphs** — PyTorch builds the computation graph *as the code executes* (define-by-run), rather than requiring you to fully specify the graph before running any data through it. This means you can use native Python control flow (`if`, `for`, `while`) inside your model and the graph will adapt automatically, which is invaluable for variable-length sequences (e.g., RNNs over sentences of different lengths).
4. **Seamless integration with Python libraries** — Tensors interoperate cleanly with NumPy arrays, and PyTorch code slots naturally into the broader Python data-science stack (pandas, Matplotlib, scikit-learn, etc.).

### PyTorch vs. Keras

| Feature | PyTorch | Keras |
|---|---|---|
| **Computation graphs** | Dynamic (define-by-run) and flexible | Static (define-and-run) but less flexible |
| **Ease of use** | Pythonic, intuitive, and readable | High-level API, user-friendly, and beginner-friendly |
| **Flexibility** | High flexibility for custom models and prototyping | Flexible for quick prototyping and standard workflows |
| **Production deployment** | Improves with TorchServe | Has basic deployment capabilities |

**How to read this table:** Keras (running on top of TensorFlow) optimizes for getting a standard model up and running with the fewest lines of code — great for beginners and for well-understood architectures. PyTorch optimizes for **transparency and control**: because the graph is built dynamically at runtime, you can insert custom logic, inspect intermediate tensors mid-forward-pass, and build architectures that don't fit neatly into a `Sequential` stack (e.g., models with loops, branching, or recursive structures). This is also the main **PyTorch vs. TensorFlow** distinction that shows up repeatedly in interviews: TensorFlow 1.x used static graphs (build once, run many times, harder to debug but easier to optimize/deploy), while PyTorch's dynamic-graph, eager-execution style made it the go-to framework for research from day one. (TensorFlow 2.x adopted eager execution too, narrowing this historical gap, but PyTorch retained the reputation for research-friendliness and Keras retained the reputation for ease of use.)

### Industrial Use Cases of PyTorch and Keras

| PyTorch | Keras |
|---|---|
| Research and development | Rapid prototyping |
| Natural language processing | Business and enterprise applications |
| Computer vision | Image classification |
| Production and deployment | Time series analysis |
| Custom AI solutions | Scalable ML pipelines |

In practice, many companies use **both**: Keras/TensorFlow for standardized production pipelines with lots of tooling (TFX, TensorFlow Serving, TensorFlow Lite for mobile), and PyTorch for research teams that need to prototype new architectures quickly and later productionize the winners with **TorchServe** or by exporting to **ONNX**/**TorchScript**.

### Trends and Future Directions of PyTorch

- **Increased production use** — Tools like **PyTorch Lightning** (a higher-level training framework that removes training-loop boilerplate) and **TorchServe** (a model-serving framework) have closed the gap that once made PyTorch feel research-only. More companies now run PyTorch models in production.
- **Research dominance** — PyTorch remains the top choice for research and innovation, especially in NLP and computer vision, largely thanks to its dynamic computation graph (easy to experiment with novel architectures) and its large, active open-source community (most new papers ship PyTorch code).

### Characteristics of PyTorch

- **Strong GPU support** for optimized performance — tensors can be moved to a GPU with a single `.to('cuda')` call, and most operations are automatically GPU-accelerated.
- **Dynamic neural network development** with a **define-by-run** paradigm — the graph is constructed on the fly during the forward pass, so architectures can change between iterations (useful for things like variable-depth or conditional networks).
- **Seamless Python integration** to enhance usability — no separate "graph language"; everything is native Python plus tensors.

### The PyTorch Ecosystem

The PyTorch ecosystem is a collection of official and community libraries built on top of the core `torch` package, each specializing in a data modality or research area:

| Library | Purpose |
|---|---|
| **torchvision** | Provides datasets (e.g., MNIST, CIFAR-10, ImageNet), pretrained model architectures (ResNet, VGG, etc.), and common image transformations for computer vision applications. |
| **torchtext** | Offers data processing utilities and popular datasets for natural language processing (NLP), such as tokenization helpers and text dataset loaders. |
| **PyTorch Geometric (PyG)** | Enables learning on graphs and other irregular structures — used for applications like social network analysis and knowledge-graph completion (Graph Neural Networks). |
| **torchaudio** | Offers methods for audio processing and access to popular audio datasets, useful for speech recognition and audio classification. |

Think of these as the PyTorch equivalents of domain-specific "starter kits" — instead of writing your own MNIST loader or your own convolution-based image augmentation pipeline from scratch, `torchvision` already ships them, ready to import.

## Installation of PyTorch

The basic installation via `pip` pulls in the core library plus the two most commonly paired ecosystem packages (vision and audio):

```bash
pip install torch torchvision torchaudio
```

If you have an NVIDIA GPU and want CUDA-accelerated tensor operations, you install a build that's linked against a specific CUDA toolkit version. Two equivalent approaches:

```bash
# Using pip, with CUDA 11.7 wheels
pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu117
```

```bash
# Using conda, with CUDA toolkit 11.3
conda install pytorch torchvision torchaudio cudatoolkit=11.3 -c pytorch
```

**Why does the CUDA version matter?** PyTorch ships pre-compiled binaries for specific CUDA toolkit versions. If your installed PyTorch build doesn't match the CUDA driver/toolkit on your machine, `torch.cuda.is_available()` will return `False` (or you'll get runtime errors), and every tensor operation will silently fall back to CPU — which can be 10-50x slower for large models. Always check the [official PyTorch install matrix](https://pytorch.org/get-started/locally/) for the combination that matches your hardware.

## PyTorch Tensors

A **tensor** is PyTorch's fundamental data structure — a multidimensional array composed of elements of a single data type. If you've used NumPy, a PyTorch tensor is conceptually the same as an `ndarray`, but with two superpowers added on top:

1. It can live on a **GPU** (`tensor.to('cuda')`) and get hardware-accelerated operations.
2. It can track its own **computation history** for automatic differentiation (`requires_grad=True`), which is what powers Autograd (see below).

```python
import torch

# Create a tensor with random values, shape (2, 3)
x = torch.rand(2, 3)
print(x)
# tensor([[0.1234, 0.9876, 0.4562],
#         [0.7890, 0.2345, 0.6789]])
```

Other common ways to create tensors that are useful to know even though they weren't explicitly listed in the slide:

```python
torch.zeros(3, 3)          # a 3x3 tensor of zeros
torch.ones(2, 4)           # a 2x4 tensor of ones
torch.tensor([1, 2, 3])    # a tensor built directly from a Python list
torch.from_numpy(np_array) # convert a NumPy array to a tensor (shares memory!)
x.shape                    # inspect the shape, e.g. torch.Size([2, 3])
x.dtype                    # inspect the element data type, e.g. torch.float32
```

Because tensors are the common currency of every PyTorch operation — inputs, weights, gradients, and outputs are all tensors — understanding tensor creation, shape manipulation (`.view()`, `.reshape()`, `.squeeze()`, `.unsqueeze()`), and device placement (`.to(device)`) is the foundation for everything else in this lesson.

### Autograd: Automatic Differentiation (Expanded)

The business scenario explicitly calls out the **Autograd** module, so it's worth expanding on even though the slide deck only mentions it in passing. When a tensor is created with `requires_grad=True`, PyTorch automatically builds a computation graph behind the scenes as operations are applied to it. Calling `.backward()` on a final scalar output (like a loss value) walks that graph backward and computes the gradient of the output with respect to every tensor that fed into it — without you writing a single line of calculus.

```python
import torch

x = torch.tensor(2.0, requires_grad=True)
y = x ** 2 + 3 * x + 1        # y = x^2 + 3x + 1
y.backward()                  # compute dy/dx
print(x.grad)                 # tensor(7.)  because dy/dx = 2x + 3 = 2*2 + 3 = 7
```

This is the mechanism that makes `loss.backward()` in the training loop (seen later in this lesson) actually work: PyTorch already knows, from the forward pass, exactly which operations produced the loss, so it can compute gradients for every weight in the network in a single call.

## Modules in PyTorch

`torch.nn` is PyTorch's neural network library. Everything you build — layers, activation functions, loss functions, entire models — is a **module** (an instance of, or subclass of, `nn.Module`). The slides group these modules into eight functional categories.

### Basic Layer Modules

These are the fundamental building blocks for creating neural networks:

- **Linear Layers (`nn.Linear`)** — Fully connected ("dense") linear layers. Every input feature connects to every output neuron via a learned weight, plus a bias term. This is the workhorse layer for MLPs and for the final classification head of most networks.
- **Convolutional Layers (`nn.Conv1d`, `nn.Conv2d`, `nn.Conv3d`)** — Layers that apply a convolution operation over incoming data, typically used in image processing. Instead of connecting every input pixel to every output neuron (which would be enormous and ignore spatial structure), a convolution slides a small learnable filter (kernel) across the image, detecting local patterns like edges or textures.
- **Recurrent Layers (`nn.LSTM`, `nn.GRU`, `nn.RNN`)** — Layers designed for sequential data processing (text, time series, audio). They maintain a hidden state that gets updated at each time step, letting the network "remember" information from earlier in the sequence.

### Activation Functions

Activation functions introduce non-linearity, without which a stack of linear layers would collapse into a single linear transformation no matter how "deep" the network looked:

- **ReLU (`nn.ReLU`)** — A common activation function that outputs the input directly if it is positive; otherwise, it outputs zero (i.e., `max(0, x)`). It's popular because it's cheap to compute and helps mitigate the vanishing-gradient problem compared to older activations.
- **Sigmoid (`nn.Sigmoid`)** — Squashes values into the range (0, 1); commonly used for binary classification output layers or gates.
- **Tanh (`nn.Tanh`)** — Squashes values into the range (-1, 1); zero-centered, which can help optimization compared to sigmoid.
- **LeakyReLU, ELU, and others** — Variants of ReLU designed to avoid the "dying ReLU" problem, where a neuron that only ever outputs zero stops learning entirely, by allowing a small non-zero gradient when the input is negative.

### Pooling Layers

Pooling layers reduce the spatial dimensions of the input, which decreases computational complexity and helps control overfitting by discarding fine-grained positional detail while keeping the dominant features:

- **Max Pooling (`nn.MaxPool1d`, `nn.MaxPool2d`)** — Applies a max filter to subregions of the input, keeping only the strongest activation in each region. This makes the network somewhat robust to small translations of features in the image.
- **Average Pooling (`nn.AvgPool1d`, `nn.AvgPool2d`)** — Computes the average of elements in a region of the input instead of the max, producing a smoother downsampled representation.

### Normalization Layers

Normalization layers stabilize the learning process by normalizing the input at each layer, which lets you use higher learning rates and trains faster/more reliably:

- **Batch Normalization (`nn.BatchNorm1d`, `nn.BatchNorm2d`)** — Normalizes the input to have zero mean and unit variance **across the batch** (i.e., using statistics computed over all examples in the current mini-batch). This is one of the regularization tools XYZ Inc. plans to use to fight overfitting and stabilize training on imbalanced fraud data.
- **Layer Normalization (`nn.LayerNorm`)** — Normalizes input across the **features** instead of the batch, meaning it works even with a batch size of 1 and is commonly used in transformer architectures.

### Dropout Layers

- **Dropout (`nn.Dropout`)** — A regularization technique that prevents overfitting by randomly dropping (zeroing) units during the training process. Concretely, `nn.Dropout(p=0.5)` randomly zeroes 50% of the elements of the input tensor on every forward pass during training, forcing the network to not rely too heavily on any single neuron. Dropout is automatically disabled during evaluation (once you call `model.eval()`).

### Utility and Container Modules

These are used to organize or combine other modules, facilitating model construction and management:

- **Sequential (`nn.Sequential`)** — A simple sequential container that chains multiple modules together, running the output of one directly into the input of the next. Great for simple, linear-stack architectures.
- **ModuleList (`nn.ModuleList`)** — Holds submodules in a list. Unlike a plain Python list, using `ModuleList` ensures PyTorch correctly registers all the submodules' parameters (so they show up in `model.parameters()` and get optimized).
- **ModuleDict (`nn.ModuleDict`)** — Holds submodules in a dictionary, useful when you want to select between named sub-networks (e.g., different "heads" of a multi-task model).

### Loss Function Modules

Loss modules measure how well the model's predictions match the target data — the number that `.backward()` will differentiate to compute gradients:

- **MSELoss (`nn.MSELoss`)** — Mean Squared Error. Measures the mean squared error between the target and output; typically used for regression tasks.
- **CrossEntropyLoss (`nn.CrossEntropyLoss`)** — Computes cross-entropy loss between the target and output logits; the standard choice for multi-class classification (as used in both worked examples in this lesson).

### Optimizer Modules

Optimizers are methods used to update the weights of the network during training based on the gradients that Autograd computed:

- **SGD (`optim.SGD`)** — Stochastic Gradient Descent, the classic optimizer; updates weights by taking a step in the direction opposite the gradient, scaled by a learning rate.
- **Adam (`optim.Adam`)** — Adaptive Moment Estimation; combines momentum with per-parameter adaptive learning rates, and is the most commonly used default optimizer in modern deep learning because it converges quickly with minimal tuning.
- **Adagrad (`optim.Adagrad`)** — Adapts the learning rate per parameter based on the historical sum of squared gradients, which is useful for sparse data but can cause the learning rate to shrink too aggressively over long training runs.

## Example: Building a Deep Learning Model with the Fashion-MNIST Dataset

The **Fashion-MNIST** dataset contains 10 classes of fashion articles (t-shirts, trousers, sneakers, bags, etc.) as 28×28 grayscale pixel images — a slightly harder drop-in replacement for the classic MNIST digit dataset. The lesson walks through the full standard PyTorch modeling workflow, in six steps:

| Step | What it does |
|---|---|
| **01. Import libraries** | Gather the required libraries (`torch`, `nn`, `optim`, `torchvision`). |
| **02. Load and explore the dataset** | Initiate the dataset, preprocess it, and understand its structure and characteristics. |
| **03. Define the model architecture** | Establish the structure of the neural network, including layers, neurons, and activation functions. |
| **04. Compile and train the model** | Set up the model's learning process (loss + optimizer) and train it on the dataset. |
| **05/06. Evaluate the model** | Assess the performance of the trained model on a separate test dataset. |

### Step 1 — Import the Library

```python
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
from torchvision import datasets, transforms
```

### Step 2 — Load and Explore the Dataset

```python
# Data preprocessing: normalization
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,))
])

# Loading the dataset
train_dataset = datasets.FashionMNIST(root='./data', train=True, download=True,
                                       transform=transform)
test_dataset = datasets.FashionMNIST(root='./data', train=False, download=True,
                                      transform=transform)

train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=32, shuffle=True)
test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=32, shuffle=False)

# Printing the shape of the datasets
print(f'Training data: {len(train_dataset)} samples')
print(f'Testing data: {len(test_dataset)} samples')
```

A few things worth calling out that the raw slide doesn't spell out:

- `transforms.ToTensor()` converts a PIL image (or NumPy array) into a PyTorch tensor and rescales pixel values from `[0, 255]` to `[0.0, 1.0]`.
- `transforms.Normalize((0.5,), (0.5,))` then rescales that `[0, 1]` range to roughly `[-1, 1]` using `(x - mean) / std`, which typically helps the network train faster/more stably.
- `DataLoader` wraps a dataset and handles batching, shuffling, and (optionally) multi-process data loading — you never manually slice the dataset into batches.
- `shuffle=True` on the training loader (but `False` on the test loader) is intentional: shuffling training data each epoch prevents the model from learning spurious patterns tied to data order, while evaluation order doesn't matter for correctness.

### Step 3 — Define the Model Architecture

A simple CNN with one convolutional layer, one max-pooling layer, and two fully connected layers:

```python
class CNN(nn.Module):
    def __init__(self):
        super(CNN, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, 3, 1)      # 1 input channel, 32 output channels, 3x3 kernel
        self.pool = nn.MaxPool2d(2, 2)            # 2x2 pooling
        self.fc1 = nn.Linear(13*13*32, 100)       # Flattened dimensions after pooling
        self.fc2 = nn.Linear(100, 10)             # 10 classes for FashionMNIST

    def forward(self, x):
        x = self.conv1(x)
        x = nn.ReLU()(x)
        x = self.pool(x)
        x = x.view(-1, 13*13*32)                  # Flatten
        x = self.fc1(x)
        x = nn.ReLU()(x)
        x = self.fc2(x)
        return nn.Softmax(dim=1)(x)

model = CNN()
```

**Understanding `nn.Module` and `forward()`:** Every PyTorch model subclasses `nn.Module`. The `__init__` method is where you declare the layers (as attributes, so PyTorch can track their parameters), and `forward()` defines how data flows through those layers when the model is called — i.e., `model(x)` internally calls `model.forward(x)`. This split is what enables the "dynamic graph": the actual sequence of operations only gets fixed once `forward()` runs on a real batch of data.

**Where do the numbers `13*13*32` come from?** Starting from a 28×28 image: a 3×3 convolution with no padding shrinks each spatial dimension by 2 (28 → 26), giving a 26×26×32 feature map. A 2×2 max pool with stride 2 then halves each spatial dimension (26 → 13), giving 13×13×32 — which is exactly the flattened size fed into `fc1`. Getting this arithmetic right is one of the most common sources of shape-mismatch bugs when building CNNs by hand.

### Step 4 — Compile and Train the Model

The model is compiled and trained for 10 epochs using the Adam optimizer and cross-entropy loss:

```python
# Setting up the loss and optimizer
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# Training the model for 10 epochs
num_epochs = 10
for epoch in range(num_epochs):
    model.train()
    running_loss = 0.0
    for images, labels in train_loader:
        optimizer.zero_grad()             # Zero the parameter gradients
        outputs = model(images)           # Forward pass
        loss = criterion(outputs, labels)
        loss.backward()                   # Backward pass (Autograd computes gradients)
        optimizer.step()                  # Update weights
        running_loss += loss.item()
    print(f"Epoch {epoch+1}/{num_epochs}, Loss: {running_loss/len(train_loader)}")
```

**The PyTorch training loop, step by step.** Unlike Keras's one-line `model.fit(...)`, PyTorch requires you to write the training loop explicitly. This is exactly the trade-off from the "PyTorch vs. Keras" table above: more boilerplate, but complete visibility and control over every step. The five moves inside the inner loop, always in this order, are worth memorizing:

1. `optimizer.zero_grad()` — clear gradients left over from the previous batch (PyTorch accumulates gradients by default, so forgetting this line is a classic bug that silently corrupts training).
2. `outputs = model(images)` — the forward pass, producing predictions.
3. `loss = criterion(outputs, labels)` — compute how wrong the predictions are.
4. `loss.backward()` — the backward pass; Autograd computes `d(loss)/d(weight)` for every weight in the network.
5. `optimizer.step()` — the optimizer nudges every weight in the direction that reduces the loss, using the gradients just computed.

`model.train()` puts layers like `Dropout` and `BatchNorm` into "training mode" (dropout active, batch norm uses batch statistics); its counterpart `model.eval()` (used below) switches them into "inference mode."

### Step 5 — Evaluate the Model

```python
# Evaluating the model
model.eval()
correct = 0
total = 0
with torch.no_grad():
    for images, labels in test_loader:
        outputs = model(images)
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

accuracy = 100 * correct / total
print(f"Model accuracy on test set: {accuracy}%")
```

`torch.no_grad()` disables gradient tracking for everything inside the block. Since we're not calling `.backward()` during evaluation, tracking gradients would just waste memory and compute — this context manager is standard practice for any inference/evaluation code. `torch.max(outputs.data, 1)` returns the index of the highest-probability class along dimension 1 (the class dimension), which is the model's predicted label.

## Example: MNIST Digit Classifier

The second worked example repeats the same six-step workflow on the classic **MNIST** dataset (handwritten digits 0–9), but this time with a fully connected network (a multi-layer perceptron) instead of a CNN, giving a nice side-by-side contrast in architecture choice:

| Step | What it does |
|---|---|
| **01. Import and load the dataset** | Load the dataset, import the required libraries, normalize pixel values, and reshape images. |
| **02. Visualize the data** | Visualize the seventh image from a batch of the MNIST training dataset. |
| **03. Define the model** | Define a fully connected neural network (dense network / multi-layer perceptron). |
| **04. Compile the model** | Specify the optimizer and loss function. |
| **05. Fit the model** | Train the model with specified epochs and batch sizes on the training data. |
| **06. Evaluate and predict** | Evaluate model performance and use the trained model to make predictions on new data. |

### Step 1 — Import and Load the Dataset

```python
import torch
import torchvision.transforms as transforms
from torchvision.datasets import MNIST
from torch.utils.data import DataLoader

# Define transformation: Convert image to tensor and normalize
transform = transforms.Compose([transforms.ToTensor(),
                                 transforms.Normalize((0.5,), (0.5,))])

# Download and load the dataset
train_dataset = MNIST(root='./data', train=True, transform=transform, download=True)
test_dataset = MNIST(root='./data', train=False, transform=transform)

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)
```

### Step 2 — Visualize the Data

```python
import matplotlib.pyplot as plt

dataiter = iter(train_loader)
images, labels = next(dataiter)
plt.imshow(images[6].numpy().squeeze(), cmap='gray')
plt.show()
print(labels[6])
```

`.squeeze()` removes the channel dimension (MNIST images are single-channel, so the tensor shape is `[1, 28, 28]`); Matplotlib's `imshow` expects a 2D array for a grayscale image, hence the squeeze down to `[28, 28]`.

### Step 3 — Define the Model

A simple 3-layer fully connected network:

```python
import torch.nn as nn
import torch.nn.functional as F

class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.fc1 = nn.Linear(28*28, 128)
        self.fc2 = nn.Linear(128, 128)
        self.fc3 = nn.Linear(128, 10)

    def forward(self, x):
        x = x.view(-1, 28*28)     # Flatten the 28x28 image into a 784-length vector
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x

model = Net()
```

Notice the small but important stylistic difference from the Fashion-MNIST CNN above: this example uses the **functional** API (`torch.nn.functional as F`, then `F.relu(...)`) instead of instantiating `nn.ReLU()` as a layer object. Both are valid; `nn.ReLU()` is preferred when you want the activation registered as part of a `Sequential` container or need to track it as a module, while `F.relu()` is a lighter-weight, stateless function call — a common style choice you'll see across different PyTorch codebases.

Also note this network returns raw **logits** (no softmax applied), unlike the Fashion-MNIST example which applied `nn.Softmax` inside `forward()`. This works because `nn.CrossEntropyLoss` expects raw logits and applies `log_softmax` internally for numerical stability — applying softmax yourself before passing to `CrossEntropyLoss` is a subtle, common bug that hurts training (loss magnitudes end up wrong), even though the Fashion-MNIST slide example does exactly that.

### Step 4 — Compile the Model

```python
import torch.optim as optim

criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)
```

### Step 5 — Fit the Model

```python
epochs = 10
for epoch in range(epochs):
    running_loss = 0.0
    for i, (images, labels) in enumerate(train_loader, 1):  # enumerate to get batch number
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()

    # Print average loss for the epoch
    print(f"Epoch [{epoch+1}/{epochs}], Loss: {running_loss/i:.4f}")
```

This is the same five-step training loop pattern from the Fashion-MNIST example (`zero_grad → forward → loss → backward → step`) — worth noticing how consistent this structure is across virtually every PyTorch training script you'll encounter, regardless of the model architecture.

### Step 6 — Evaluate and Predict

```python
correct = 0
total = 0
with torch.no_grad():
    for images, labels in test_loader:
        outputs = model(images)
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

print(f'Test Accuracy: {100 * correct / total}%')
```

```python
# Predicting a single image
dataiter = iter(train_loader)
images, labels = next(dataiter)
outputs = model(images[1:2])
_, predicted = torch.max(outputs.data, 1)
plt.imshow(images[1].numpy().squeeze(), cmap='gray')
plt.title(f"Predicted Label: {predicted.item()}")
plt.show()
```

`images[1:2]` (rather than `images[1]`) preserves the batch dimension, keeping the tensor shape `[1, 1, 28, 28]` instead of collapsing it to `[1, 28, 28]` — the model always expects a batch dimension as its first axis, even for a single example.

## Key Takeaways

- **PyTorch** is an open-source deep learning framework renowned for its capabilities in computer vision, natural language processing, and reinforcement learning.
- PyTorch provides libraries tailored to various applications: **torchvision** for computer vision, **torchtext** for natural language processing, **PyTorch Geometric** for graph-based learning, and **torchaudio** for audio processing.
- PyTorch offers a variety of specialized modules for building and optimizing neural networks, such as basic layers, activation functions, pooling, and normalization layers.
- The standard PyTorch workflow is: import libraries → load/preprocess data with `Dataset`/`DataLoader` → define a model as an `nn.Module` subclass → set up a loss function and optimizer → run an explicit training loop (`zero_grad → forward → loss → backward → step`) → evaluate with `model.eval()` and `torch.no_grad()`.

## Knowledge Check (From the Slide Deck)

**1. What is the primary purpose of Convolutional Layers (`nn.Conv1d`, `nn.Conv2d`, and `nn.Conv3d`) in PyTorch?**

- **A.** To output the input directly if it is positive and zero if otherwise
- **B.** To apply a convolution operation over incoming data, typically used in image processing
- **C.** To connect every neuron in one layer to every neuron in the next layer
- **D.** To create a feedback loop in the data, allowing for memory over time

**Correct answer: B.** Convolutional layers apply filters to incoming data to detect features, primarily used in image and video processing tasks. (A describes ReLU, C describes a Linear/fully-connected layer, D describes a recurrent layer.)

**2. What is the purpose of the Optim module in PyTorch?**

- **A.** To perform automatic differentiation
- **B.** To create computational graphs
- **C.** To distribute tasks on multiple CPUs or GPUs
- **D.** To implement optimization algorithms for building neural networks

**Correct answer: D.** The `optim` module implements optimization algorithms (SGD, Adam, Adagrad, etc.) that update network weights based on gradients. (A describes Autograd, B describes the dynamic-graph engine generally, C describes data/model parallelism utilities.)

## 📝 Practice Questions

1. **(MCQ)** Which PyTorch module is responsible for automatic differentiation — computing gradients of a loss with respect to model parameters?
   - **A.** `torch.nn`
   - **B.** `torch.optim`
   - **C.** `torch.autograd`
   - **D.** `torchvision`

2. **(MCQ)** In the standard PyTorch training loop, which line must be called *before* `loss.backward()` to avoid incorrectly accumulating gradients from the previous batch?
   - **A.** `optimizer.step()`
   - **B.** `optimizer.zero_grad()`
   - **C.** `model.eval()`
   - **D.** `torch.no_grad()`

3. **(Short answer)** Explain the difference between a "static" (define-and-run) computation graph and a "dynamic" (define-by-run) computation graph, and state which paradigm PyTorch uses.

4. **(MCQ)** Which layer normalizes its input using statistics computed across the **batch** dimension, rather than across features?
   - **A.** `nn.LayerNorm`
   - **B.** `nn.BatchNorm2d`
   - **C.** `nn.Dropout`
   - **D.** `nn.MaxPool2d`

5. **(Short answer)** Why does `nn.CrossEntropyLoss` expect raw logits as input rather than probabilities that have already been passed through a softmax function?

6. **(MCQ)** What does calling `model.eval()` do that `model.train()` does not?
   - **A.** It deletes the model's learned weights
   - **B.** It disables gradient computation for all tensors permanently
   - **C.** It switches layers like Dropout and BatchNorm into inference behavior (e.g., dropout is turned off)
   - **D.** It recompiles the model into a static graph

7. **(Short answer)** In the Fashion-MNIST CNN example, a 28×28 input image passes through a `nn.Conv2d(1, 32, 3, 1)` layer followed by a `nn.MaxPool2d(2, 2)` layer, then gets flattened to a size of `13*13*32` before the first linear layer. Explain how the spatial dimensions changed from 28 to 13.

8. **(MCQ)** Which of the following is NOT one of the four PyTorch libraries mentioned in the lesson's ecosystem overview?
   - **A.** torchvision
   - **B.** torchtext
   - **C.** torchserve
   - **D.** torchaudio

9. **(Short answer)** Why is `torch.no_grad()` used when evaluating a model on a test set, and what would happen (performance-wise) if you forgot to use it?

10. **(MCQ)** Which optimizer combines momentum with per-parameter adaptive learning rates and is the most commonly used default optimizer in modern deep learning?
    - **A.** `optim.SGD`
    - **B.** `optim.Adagrad`
    - **C.** `optim.Adam`
    - **D.** `optim.RMSprop`

11. **(Short answer)** XYZ Inc.'s fraud detection dataset is heavily imbalanced (fraud is rare). Name two regularization/stabilization techniques mentioned in this lesson that help address overfitting and training instability, and briefly explain what each one does.

12. **(MCQ)** Which statement best distinguishes PyTorch from Keras, based on the comparison table in this lesson?
    - **A.** PyTorch cannot run on a GPU, while Keras can
    - **B.** PyTorch uses dynamic, define-by-run computation graphs, while Keras (via TensorFlow) traditionally uses static, define-and-run graphs
    - **C.** Keras cannot be used for image classification
    - **D.** PyTorch has no way to save or deploy trained models

13. **(Short answer)** What is the purpose of `DataLoader` in a PyTorch data pipeline, and why is `shuffle=True` typically used for the training loader but `shuffle=False` for the test loader?

14. **(MCQ)** In a `Dataset`/`DataLoader` pipeline using `transforms.Normalize((0.5,), (0.5,))` after `transforms.ToTensor()`, what is the approximate resulting range of pixel values?
    - **A.** [0, 255]
    - **B.** [0, 1]
    - **C.** [-1, 1]
    - **D.** [-255, 255]

### Answers

1. **C — `torch.autograd`.** Autograd tracks operations performed on tensors with `requires_grad=True` and computes gradients automatically when `.backward()` is called; `nn` holds layers/losses, `optim` holds weight-update algorithms, and `torchvision` provides vision datasets/models.
2. **B — `optimizer.zero_grad()`.** PyTorch accumulates gradients by default across calls to `.backward()`, so gradients from the previous batch must be cleared before computing new ones, or they'll be added together and corrupt the update.
3. A **static graph** is fully defined and compiled before any data is run through it (define-and-run), which can be more optimizable but harder to debug and less flexible for variable structures. A **dynamic graph** is built on the fly as operations actually execute on real tensors (define-by-run), so the graph can change every iteration and standard Python control flow (`if`/`for`) works naturally inside the model. **PyTorch uses the dynamic (define-by-run) paradigm.**
4. **B — `nn.BatchNorm2d`.** Batch normalization computes mean/variance across the current mini-batch; `nn.LayerNorm` normalizes across features instead, `nn.Dropout` randomly zeroes elements (no normalization), and `nn.MaxPool2d` downsamples spatially (no normalization).
5. `nn.CrossEntropyLoss` internally applies `log_softmax` to the raw logits before computing the loss, in a way that's numerically more stable than first computing softmax probabilities and then taking their log separately. Applying softmax yourself beforehand effectively double-applies the normalization, which distorts gradient magnitudes and hurts training.
6. **C.** `model.eval()` switches layers such as `Dropout` (turns dropout off) and `BatchNorm` (uses running statistics instead of batch statistics) into inference mode; it does not delete weights, does not itself disable gradients (that's what `torch.no_grad()` is for), and does not recompile anything into a static graph.
7. A 3×3 convolution with stride 1 and no padding reduces each spatial dimension by `(kernel_size - 1) = 2`, so 28 → 26. A subsequent 2×2 max pool with stride 2 halves each spatial dimension, so 26 → 13. With 32 output channels from the convolution, the flattened feature map size is `13 * 13 * 32`.
8. **C — torchserve.** TorchServe is a model-*serving* framework mentioned separately under production trends, not one of the four data-modality ecosystem libraries (torchvision, torchtext, PyTorch Geometric, torchaudio) covered in the ecosystem slides.
9. `torch.no_grad()` disables gradient/computation-graph tracking for the operations inside its block. During evaluation you never call `.backward()`, so tracking gradients would be pure overhead — it wastes memory (storing intermediate activations needed only for backprop) and slows down the forward pass unnecessarily. Forgetting it doesn't produce incorrect predictions, but it does waste memory/compute and can even cause out-of-memory errors on large models or large batches.
10. **C — `optim.Adam`.** Adam combines momentum (from SGD with momentum) with per-parameter adaptive learning rates (similar in spirit to Adagrad/RMSprop), converges quickly with minimal hyperparameter tuning, and is the most widely used default optimizer.
11. Two valid techniques from the lesson: **Dropout** (`nn.Dropout`), which randomly zeroes a fraction of activations during training so the network can't over-rely on any single neuron/feature, reducing overfitting; and **Batch Normalization** (`nn.BatchNorm1d`/`2d`), which normalizes layer inputs to zero mean/unit variance across the batch, stabilizing and speeding up training. (Data parallelism across GPUs, also mentioned in the business scenario, addresses scale rather than overfitting directly.)
12. **B.** The comparison table's central distinction is dynamic/define-by-run (PyTorch) vs. static/define-and-run (Keras/TensorFlow historically); both frameworks fully support GPU training, both support image classification, and PyTorch does support deployment via tools like TorchServe.
13. `DataLoader` wraps a `Dataset` and automatically handles batching, (optional) shuffling, and iteration, so you don't have to manually slice data into batches. `shuffle=True` on the training loader ensures the model sees data in a different order each epoch, preventing it from learning spurious patterns tied to the original ordering of examples; `shuffle=False` on the test loader is used because evaluation results don't depend on order, and keeping a fixed order makes evaluation reproducible/comparable across runs.
14. **C — [-1, 1] (approximately).** `ToTensor()` first scales pixel values from [0, 255] to [0, 1]; `Normalize((0.5,), (0.5,))` then applies `(x - 0.5) / 0.5`, mapping [0, 1] to roughly [-1, 1].
