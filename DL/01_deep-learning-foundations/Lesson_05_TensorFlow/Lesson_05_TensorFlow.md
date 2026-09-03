# Deep Learning with Keras and TensorFlow — Lesson 05: TensorFlow

## Learning Objectives

By the end of this lesson, you will be able to:

- Install and set up TensorFlow and TFLearn for building and testing models.
- Gain hands-on experience with TensorFlow Playground to visualize and understand the impact of hyperparameters on model performance.
- Explore various applications of TensorFlow across different industries, such as healthcare and social media.
- Analyze the workflow of TFLearn, including creating input layers, configuring models, and training neural networks.
- Evaluate and improve machine learning models using TensorFlow and Keras.

---

## Business Scenario

XYZ Corporation is a technology company that specializes in developing advanced artificial intelligence (AI) applications. To stay ahead of the competition, it has decided to use **TensorFlow**, an open-source library for deep learning.

The company intends to use TensorFlow's comprehensive suite of tools to:

- Train multiple neural networks.
- Use **TensorBoard** for visualization of computational graphs.
- Use **Keras** for the easy and efficient creation of neural network models.

With these tools, XYZ Corporation can develop sophisticated AI applications and gain a competitive edge in the fast-paced technology industry. This scenario is a useful frame for the whole lesson: almost every real production deep-learning pipeline you will build combines the *low-level power* of TensorFlow with the *high-level convenience* of Keras, plus visualization tooling like TensorBoard to understand what the model is actually doing during training.

---

## 1. Introduction to TensorFlow

### 1.1 What Is TensorFlow?

TensorFlow is an **open-source, Python-compatible toolkit for numerical computation** that accelerates and improves the creation of neural networks and machine learning algorithms.

- Developed by the **Google Brain team** and released in **2015**.
- Used mainly for **classification, prediction, and creation of models**.
- One of the most popular open-source libraries for deep learning in the world today.

Although TensorFlow is best known for deep learning, at its core it is really a general-purpose library for fast numerical computation — it just happens to be extremely well suited to the matrix/vector math (multiplications, convolutions, gradients) that neural networks need. This is why it can scale from a small laptop experiment all the way up to training massive models across clusters of GPUs/TPUs.

### 1.2 What TensorFlow Provides

TensorFlow is described as an effective and adaptable machine learning library that enables researchers to build innovative ML models and quickly deploy applications. It ships as an ecosystem made of three broad pillars:

| Pillar | What it means in practice |
|---|---|
| **Libraries** | Pre-built modules (`tf.keras`, `tf.data`, `tf.linalg`, etc.) that implement common ML building blocks so you don't reinvent them. |
| **Tools** | Utilities such as TensorBoard (visualization), TensorFlow Lite (mobile/embedded deployment), and TensorFlow Serving (production serving). |
| **Community resources** | Tutorials, pretrained models, forums, and a huge base of open-source contributors that make it easier to learn and troubleshoot. |

### 1.3 Tensors — The Core Data Structure

In TensorFlow, data values are **not** stored as plain integers, floats, or strings the way they would be in ordinary Python. Instead, every piece of data is wrapped inside an object called a **tensor**.

> If you pass a Python list to TensorFlow, it will automatically be converted into a tensor.

A tensor is best thought of as a generalization of scalars, vectors, and matrices to any number of dimensions:

- A **scalar** (single number) is a rank-0 tensor.
- A **vector** (1-D array) is a rank-1 tensor.
- A **matrix** (2-D array, rows × columns) is a rank-2 tensor.
- Anything with 3 or more dimensions (e.g., a batch of RGB images: batch × height × width × channels) is a rank-N tensor.

```python
import tensorflow as tf

# A Python list is automatically converted into a tensor
example_tensor = tf.constant([[1, 2, 3], [4, 5, 6]])

print(example_tensor)
# tf.Tensor(
# [[1 2 3]
#  [4 5 6]], shape=(2, 3), dtype=int32)

print(example_tensor.shape)  # (2, 3)  -> 2 rows, 3 columns
print(example_tensor.dtype)  # int32
```

Every tensor carries a **shape** (its dimensions) and a **dtype** (the type of numbers it holds, e.g. `float32`, `int32`). Understanding tensors is foundational because every input, weight, activation, and output in a TensorFlow/Keras model is a tensor.

### 1.4 Key Features of TensorFlow

TensorFlow is a powerful AI tool that enables the creation of large-scale neural networks with complex layers. Its headline features include:

- **High-level APIs** — e.g., `tf.keras`, which let you assemble a model in a few lines of code.
- **Pre-trained models** — ready-made networks (image classifiers, language models, etc.) that can be reused or fine-tuned instead of training from scratch.
- **Model deployment** — tools such as TensorFlow Lite and TensorFlow.js let trained models run on mobile devices, browsers, and edge hardware.
- **TensorBoard** — a built-in visualization suite for inspecting training curves, computational graphs, and more.
- **Distributed computing** — native support for spreading training across multiple CPUs, GPUs, and even TPUs (Tensor Processing Units).

### 1.5 Why Is TensorFlow Necessary?

Deep learning models routinely involve millions (or billions) of parameters and require enormous amounts of matrix arithmetic. TensorFlow operates on a system of **data flow graphs**, which allows for efficient computation and parallel processing. It is essential for handling the heavy computational requirements of deep learning because it provides a comprehensive and flexible framework for **designing, training, and deploying** deep learning models — without you having to hand-write gradient calculations or low-level parallelization code yourself.

---

## 2. TensorFlow: Dataflow Graphs

### 2.1 What Is a Dataflow Graph?

TensorFlow is fundamentally a library for numerical computation that represents computations as **dataflow graphs**:

- **Nodes** represent mathematical operations (e.g., addition, matrix multiplication, an activation function).
- **Edges** represent the multidimensional data arrays (**tensors**) that flow between nodes in the graph.

Think of it like a flowchart for math: raw input data enters at one end, flows through a sequence of operations (nodes), and a result (like a prediction) comes out the other end. Because the graph is defined explicitly, TensorFlow can analyze it *before* running it — figuring out, for example, which operations don't depend on each other and can therefore run at the same time.

Dataflow is a common programming model used broadly in parallel computing, not just in deep learning. TensorFlow uses this dataflow graph representation to describe computation, and it **optimizes graph execution** by rearranging operations and leveraging parallelism wherever possible — for example, running two independent matrix multiplications on separate GPU cores simultaneously rather than one after another.

### 2.2 Benefits of Using Dataflow Graphs

| Benefit | Explanation |
|---|---|
| **Parallelism** | It is easy for the ML system to identify operations that can be executed in parallel, since dependencies between nodes are explicit in the graph. |
| **Distributed execution** | TensorFlow programs can be distributed across multiple devices — CPUs and GPUs — and even across multiple machines. |
| **Compilation** | Having an explicit graph representation helps TensorFlow generate optimized code quickly. |
| **Portability** | A model can be built in Python, saved (serialized) as a saved model, and then restored and run inside a C++ program — useful for deploying models into performance-critical or non-Python production systems. |

---

## 3. Categories of TensorFlow APIs

TensorFlow APIs can be divided into two broad groups, which trade off control for convenience:

### 3.1 Low-Level API

- Example: **TensorFlow Core**.
- Recommended for deep learning **researchers** who need fine control.
- Provides finer-grained control over the models — you build the computational graph almost operation by operation.

### 3.2 High-Level API

- Examples: **`tf.keras`**, **`tf.estimator`**.
- Makes TensorFlow easier to use *without sacrificing flexibility and performance*.
- Provides tools for building and training complex models with just a few lines of code.

In practice, most practitioners today spend the vast majority of their time in the high-level `tf.keras` API, dropping down to the low-level API only when they need custom layers, custom training loops, or very specialized operations that Keras doesn't already provide.

### 3.3 Other Notable Features

- **Built-in visualization**: TensorFlow offers built-in visualization mainly through **TensorBoard**, making it easy to analyze and visualize computational graphs, training metrics (loss/accuracy curves), and even model weight histograms.
- **Data pipeline**: TensorFlow serves as an intermediary between raw input data and models, enabling efficient preprocessing pipelines (via `tf.data`).
- **Open-source & accelerated**: As an open-source library, it enables efficient and accelerated computations (through optimized C++ kernels and hardware acceleration).
- **Scalability**: It supports pipelining and multi-GPU training, enhancing efficiency for large-scale models.

---

## 4. Advantages of TensorFlow

TensorFlow's popularity is driven by five broad advantages:

1. **Flexibility** — Python API offers flexibility to create all sorts of computations for every neural network architecture, while under the hood it includes highly efficient C++ implementations of many ML operations (so you get Python's ease of use with C++'s speed).
2. **Parallel computation** — TensorFlow utilizes parallel computation techniques to efficiently process data and accelerate the training of deep learning models, taking advantage of multi-core CPUs and GPUs.
3. **Friendly with multiple environments** — TensorFlow is compatible with a wide range of desktop and mobile software environments, including Linux, macOS, Windows, iOS, Android, and even Raspberry Pi.
4. **Open-source platform** — It is one of the most popular open-source projects on GitHub, backed by a dedicated team of developers and a growing community that continuously contributes improvements.
5. **High-level abstraction** — High-level abstractions (like `tf.keras`) simplify the process of creating deep learning models by providing:
   - Simplified model development
   - Faster prototyping
   - Increased productivity
   - Seamless experimentation

---

## 5. Applications of TensorFlow

TensorFlow can train and run deep neural networks for a wide variety of tasks, including:

1. Image recognition
2. Handwritten digit classification
3. Recurrent neural networks (sequence modeling)
4. Word embedding
5. Natural language processing (NLP)
6. Video detection

### 5.1 Companies Using TensorFlow

Many well-known companies leverage TensorFlow in production, including **Uber, SAP, DeepMind, Coca-Cola, Dropbox, Google, eBay, Intel,** and **Qualcomm**. The breadth of these companies — spanning ride-sharing, enterprise software, research labs, beverages, cloud storage, search, e-commerce, and semiconductors — illustrates how broadly applicable deep learning (and TensorFlow specifically) has become across industries, not just "tech" companies.

### 5.2 Use Cases by Industry

**Healthcare**
TensorFlow's capabilities in processing and analyzing medical images can significantly aid in diagnosing diseases with more speed and precision. For example, Google developed **DermAssist** using TensorFlow, which lets a user take a picture of their skin and receive possible diagnoses for various skin conditions.

**Social Media**
- **X (formerly Twitter)** implemented TensorFlow to rank tweets according to user preferences.
- **VSCO**, a photo-sharing app, uses TensorFlow to suggest filters for photos.
- **RankBrain**, a Google search engine component, uses TensorFlow to process and improve search results.

**Education**
TensorFlow is used to filter toxic chat messages in classrooms on virtual learning platforms. It is also used to accurately identify a student's current capabilities and help decide the most suitable course of action for their learning path going forward.

**Retail**
- Many e-commerce platforms use TensorFlow to generate personalized customer recommendations.
- Cosmetics companies use TensorFlow to power augmented reality experiences that let customers virtually "try on" makeup on their own faces.

### Assisted Practice (Notebooks referenced in this lesson)

- **5.02_Introduction to Tensors** — explore tensor creation, shapes, and basic operations.
- **5.03_Hands-on with TensorFlow: Part A** — practical TensorFlow exercises.
- **5.04_Training DNN Using TensorFlow** — train a deep neural network using TensorFlow.

*Note: refer to the Reference Material section to download the notebook files corresponding to each topic.*

---

## 6. Installation of TensorFlow

### 6.1 Prerequisites

Before installing TensorFlow, make sure your system meets these requirements:

- Ubuntu 18.04 or higher
- macOS 10.15 or higher
- Windows 10 or higher
- Python 3.8 or higher

### 6.2 Setting Up the System (GPU Support on Windows)

For GPU-accelerated TensorFlow on Windows, the general workflow (using Anaconda) is:

1. **Install TensorFlow** using the official version-compatibility matrix at `https://www.tensorflow.org/install/source#gpu`. This page lists every TensorFlow version alongside the compatible cuDNN, CUDA, and Python versions — matching these correctly is one of the most common sources of installation failures, so always check this table first.
2. **Install CUDA** from `https://developer.nvidia.com/cuda-toolkit-archive`, choosing the CUDA Toolkit version required by the TensorFlow version you intend to use (for example, TensorFlow 2.5+ requires CUDA 11.2).
3. **Create an NVIDIA developer account** (`https://nvidia.custhelp.com/app/utils/create_account`) so you can download the matching **cuDNN** library.
4. **Extract** the downloaded cuDNN zip file and copy its contents.
5. Locate the **NVIDIA GPU Computing Toolkit** folder inside `Program Files`.
6. Go into the CUDA folder inside that toolkit directory and paste the cuDNN files into the version-specific folder (e.g., `v11.2`).
7. Navigate to the `bin` folder inside that CUDA directory, and copy its full path — you'll need this for the system PATH. Then open **System Properties → Environment Variables**.
8. Double-click the **Path** environment variable to edit it.
9. Click **New**, paste the copied `bin` folder path at the bottom, and click **OK**.
10. Go back and locate the **libnvvp** folder, and copy its path as well.
11. Open **Environment Variables** again, double-click **Path**, click **New**, and paste this second copied path too.

Once all these steps are completed, **restart the computer** before attempting to install/import TensorFlow — this ensures the updated environment variables are picked up by the operating system.

### 6.3 Installing TensorFlow (the simple case)

For most users who don't need GPU acceleration, TensorFlow can be installed with a single line of code:

```python
pip install tensorflow
```

Once installed, verify the installation by running the following in a Python interpreter:

```python
import tensorflow as tf
print(tf.__version__)
```

**What this code does:** the `pip install tensorflow` command downloads and installs the TensorFlow package (and its dependencies) from PyPI. The Python snippet then imports the library under the common alias `tf` and prints its version string — a simple sanity check confirming that TensorFlow was installed correctly and is importable.

---

## 7. TensorFlow Playground

### 7.1 What Is It?

**TensorFlow Playground** is a free, browser-based application for learning about and experimenting with neural networks — no coding or installation required. It is an excellent tool for building intuition, letting you **visualize how hyperparameter changes influence a machine learning model** in real time, using simple 2-D classification/regression datasets.

### 7.2 Hands-on Walkthrough

The typical workflow for exploring the Playground is:

1. **Log in / open the website** (the Playground runs entirely in-browser).
2. **Set the dataset** — choose the shape of the data (e.g., circle, spiral, XOR) and configure the ratio of training to test data, the amount of noise, and the batch size.
3. **Set the training features** — configure the number of **epochs**, the **learning rate**, the **activation function** (ReLU, tanh, sigmoid, linear), **regularization** type (L1/L2), the **regularization rate**, and the **problem type** (classification or regression).
4. **Set the fully connected dense layers** — add/remove hidden layers and neurons to change the network's architecture.
5. **Click the play button** to start training and watch the decision boundary evolve live.
6. **Click play again to pause** once the test loss reaches its lowest observed value, so you can inspect the resulting decision boundary.

**Result observed in the lesson:** within **649 epochs**, the network built a clear decision boundary separating two classes — a nice concrete demonstration that, given enough training iterations and a reasonable architecture, a neural network can learn a non-linear separation between classes purely from data.

This tool is valuable because it makes abstract hyperparameters (learning rate, regularization, layer depth) tangible: you can watch, for instance, a learning rate that's too high cause the loss to oscillate wildly, or too many layers cause overfitting on noisy data.

---

## 8. TFLearn

### 8.1 What Is TFLearn?

**TFLearn** is a modular and transparent deep learning library built *on top of* TensorFlow. It provides a high-level API to facilitate and speed up experiments, while still maintaining full transparency and compatibility with the underlying TensorFlow graph — meaning you can always drop back down to raw TensorFlow code when you need to.

### 8.2 Features of TFLearn

- Easy to use, understand, and implement.
- Fast prototyping through highly modular built-in components.
- Full transparency over TensorFlow (nothing is hidden — you can always inspect or modify the underlying graph).
- Powerful helper functions to train *any* TensorFlow graph, not just ones built with TFLearn's own layers.
- Easy and clear graph visualization.
- Effortless device placement for utilizing multiple CPUs or GPUs.

### 8.3 TFLearn vs. TensorFlow

| Feature | TensorFlow | TFLearn |
|---|---|---|
| **Level of API** | Lower-level, allowing control over architecture | High-level, focused on user-friendliness and rapid prototyping |
| **Scalability** | Supports CPUs, GPUs, TPUs, and distributed training | Limited to TensorFlow's underlying scalability |
| **Deployment options** | Robust deployment on various platforms including edge devices | Dependent on TensorFlow's deployment options |
| **Best suited for** | Complex and large-scale projects, advanced users | Quick experimentation, beginners and intermediate users |
| **Integration & visualization** | Integrates with TensorBoard and other advanced tools | Integrates with TensorFlow; simpler, without advanced tooling |

In short: TFLearn sits as a thin, friendlier "wrapper" layer over TensorFlow, trading some flexibility for speed of development — conceptually similar in spirit to how Keras relates to TensorFlow (and indeed, `tf.keras` has now largely superseded TFLearn's role in most modern workflows).

### 8.4 Installing TFLearn

The easiest way to install TFLearn is via `pip`. For the latest stable version:

```python
pip install tflearn
```

### 8.5 Workflow of TFLearn

The typical TFLearn API workflow follows these steps:

1. Create an **input layer** first.
2. Pass the input object to create further (hidden) layers.
3. Add an **output layer**.
4. **Configure** the model (specify loss, optimizer, metrics).
5. **Initialize** the model.
6. **Train** the model with the `model.fit()` method.
7. Use the trained model to **predict** or **evaluate**.

This mirrors the general pattern used across almost all deep learning frameworks: define architecture → configure training → fit → evaluate/predict.

### 8.6 Layers of TFLearn

Layers are a core concept of TFLearn — they represent an abstract set of operations that make building neural networks more convenient (so you don't have to define every matrix multiplication and bias addition by hand).

| File | Layers |
|---|---|
| `core` | `input_data`, `fully_connected`, `dropout`, `custom_layer`, `reshape`, `flatten`, `activation`, `single_unit`, `highway`, `one_hot_encoding`, `time_distributed` |
| `conv` | `conv_2d`, `conv_2d_transpose`, `max_pool_2d`, `avg_pool_2d`, `upsample_2d`, `conv_1d`, `max_pool_1d`, `avg_pool_1d`, `residual_block`, `residual_bottleneck`, `conv_3d`, `max_pool_3d`, `avg_pool_3d`, `highway_conv_1d`, `highway_conv_2d`, `global_avg_pool`, `global_max_pool` |
| `recurrent` | `simple_rnn`, `lstm`, `gru`, `bidirectional_rnn`, `dynamic_rnn` |
| `embedding` | `embedding` |
| `normalization` | `batch_normalization`, `local_response_normalization`, `l2_normalize` |
| `merge` | `merge`, `merge_outputs` |
| `estimator` | `regression` |

### 8.7 Built-In Operations of TFLearn

Besides layers, TFLearn also provides several categories of built-in operations used when building a neural network:

| File | Operations |
|---|---|
| `activations` | `linear`, `tanh`, `sigmoid`, `softmax`, `softplus`, `softsign`, `relu`, `relu6`, `leaky_relu`, `prelu`, `elu` |
| `objectives` (loss functions) | `softmax_categorical_crossentropy`, `categorical_crossentropy`, `binary_crossentropy`, `mean_square`, `hinge_loss`, `roc_auc_score`, `weak_cross_entropy_2d` |
| `optimizers` | `SGD`, `RMSProp`, `Adam`, `Momentum`, `AdaGrad`, `Ftrl`, `AdaDelta` |
| `metrics` | `Accuracy`, `Top_k`, `R2` |
| `initializations` | `zeros`, `uniform`, `uniform_scaling`, `normal`, `truncated_normal`, `xavier`, `variance_scaling` |
| `losses` (regularization) | `l1`, `l2` |

### 8.8 Training in TFLearn

Training functions are another core feature of TFLearn. Plain TensorFlow has no prebuilt, one-line API to train a network end-to-end, so TFLearn integrates a set of functions that can easily handle training for **any** number of inputs, outputs, and optimizers.

#### Trainer, Evaluator, and Predictor

These are three roles/classes in TFLearn, each handling a different aspect of working with a neural network model:

- **Trainer** — handles the training process. Any TensorFlow graph can be trained using TFLearn's helper functions. By adding real-time monitoring, batch sampling, moving averages, and TensorBoard logging, TFLearn significantly enhances the convenience of the training process. It accepts any quantity of inputs, outputs, and optimization operations.
- **Evaluator** — used to evaluate/predict once training is complete.
- **Predictor** — produces predictions on new inputs.

**Defining a TrainOp (describes an optimization procedure such as backpropagation):**

```python
import tensorflow as tf
import tflearn

# Define your network architecture
input_placeholder = tf.placeholder(tf.float32, shape=[None, input_size])
target_placeholder = tf.placeholder(tf.float32, shape=[None, num_classes])
my_network = tflearn.fully_connected(input_placeholder, 32)
loss = tflearn.objectives.categorical_crossentropy(my_network, target_placeholder)
accuracy = tflearn.metrics.accuracy(my_network, target_placeholder)

# Create TrainOp and Trainer
trainop = tflearn.TrainOp(net=my_network, loss=loss, metric=accuracy)
model = tflearn.Trainer(train_ops=trainop, tensorboard_dir='/tmp/tflearn')
```

**What this code does:** it builds a small fully-connected network, defines a categorical cross-entropy loss and an accuracy metric against that network's output, wraps the network/loss/metric into a single `TrainOp` (which encapsulates one full "optimization procedure"), and then creates a `Trainer` that will drive the training loop and log results to TensorBoard at `/tmp/tflearn`.

**Training the model with the Trainer:**

```python
# Train the model
model.fit(feed_dicts={input_placeholder: X, target_placeholder: Y},
          n_epoch=10, batch_size=128, show_metric=True)
```

**What this code does:** this feeds the training data `X` (inputs) and `Y` (labels) into the placeholders defined earlier, and runs training for 10 full passes over the dataset (`n_epoch=10`) with a batch size of 128 samples per step, printing metrics (like accuracy) as it goes because `show_metric=True`.

**Handling multiple TrainOps together (useful for more complex, multi-network models):**

```python
# Create TrainOp objects for each training operation
trainop1 = tflearn.TrainOp(net=network1, loss=loss1)
trainop2 = tflearn.TrainOp(net=network2, loss=loss2)
trainop3 = tflearn.TrainOp(net=network3, loss=loss3)

# Create Trainer with multiple TrainOps
model = tflearn.Trainer(train_ops=[trainop1, trainop2, trainop3])

# Train the model with different feed dictionaries for each training operation
feed_dict1 = {in1: X1, label1: Y1}
feed_dict2 = {in2: X2, in3: X3, label2: Y2}
model.fit(feed_dicts=[feed_dict1, feed_dict2])
```

**What this code does:** it defines three separate optimization procedures (`trainop1`, `trainop2`, `trainop3`), each tied to its own network and loss, then bundles all three into a single `Trainer`. When `.fit()` is called, each `TrainOp` receives its own feed dictionary of inputs/labels — a pattern useful when you're jointly training multiple related networks (for example, a multi-task model or a GAN-like setup with a generator and discriminator).

**Making predictions with an Evaluator:**

```python
# Create Evaluator
model = tflearn.Evaluator(network)

# Make predictions
predictions = model.predict(feed_dict={input_placeholder: X})
```

**What this code does:** an `Evaluator` wraps an already-defined network and exposes a `.predict()` method; feeding it new data `X` returns the network's output/predictions for that data, without needing to run a full training loop.

**Handling `is_training` mode (e.g., for Dropout):**

```python
x = ...

def apply_dropout():  # Function to apply when training mode is ON.
    return tf.nn.dropout(x, keep_prob)

is_training = tflearn.get_training_mode()  # Retrieve is_training variable.
tf.cond(is_training, apply_dropout, lambda: x)  # Only apply dropout at training time.
```

**What this code does:** many layers (like Dropout or BatchNorm) must behave *differently* during training versus inference/testing. TFLearn's `Trainer` maintains an internal `is_training` boolean flag; this snippet checks that flag with `tf.cond` and applies dropout only when the model is actually in training mode — during evaluation/prediction, dropout is skipped and the original activations `x` pass through unchanged.

**Setting the training mode explicitly:**

```python
# Set training mode ON (set is_training var to True)
tflearn.is_training(True)

# Set training mode OFF (set is_training var to False)
tflearn.is_training(False)
```

**What this code does:** these two calls let you manually toggle the framework-wide `is_training` flag — useful when you want to run inference (`is_training(False)`) after having trained the model (`is_training(True)`), ensuring dropout/batch-norm layers switch to their "test-time" behavior.

### 8.9 Visualization in TFLearn

TFLearn automatically handles the creation and management of logs for training metrics without requiring manual setup. It supports four verbosity levels for automatically-generated TensorBoard summaries:

| Level | Summaries logged |
|---|---|
| **1** | Loss and Metric (fastest — "Best Speed") |
| **2** | Loss, Metric, and Gradients |
| **3** | Loss, Metric, Gradients, and Weights |
| **4** | Loss, Metric, Gradients, Weights, Activations, and Sparsity ("Best Visualization", but slowest) |

There is a clear speed-vs-insight tradeoff here: level 1 gives you the bare minimum needed to know whether training is progressing, while level 4 gives you deep diagnostic visibility (e.g., detecting vanishing gradients or dead neurons) at the cost of extra logging overhead.

- **Visualization: Loss and Accuracy** — plotting loss and accuracy curves across epochs aids in analyzing and optimizing neural network training (e.g., spotting overfitting when training accuracy keeps rising but validation accuracy plateaus or falls).
- **Visualization: Layers** — visualizing the layers between convolutional operations and convolutional weight layers provides insight into feature extraction and transformations happening inside a CNN. Similarly, visualizing convolutional weight gradients versus convolutional bias layers reveals the influence of biases on feature extraction within the network.

---

## 9. Introduction to Keras

### 9.1 What Is Keras?

**Keras** is a high-level deep learning API that simplifies the process of building and training neural network models. It provides a user-friendly interface and extensive support for various deep learning tasks. Keras is:

- **Fast**
- **Easy to implement**
- **Modular** in nature

More specifically, Keras is the most powerful and easy-to-use API for developing and evaluating deep learning models. It is a high-level neural network API written in Python, and it runs seamlessly on CPU and GPU without requiring you to change any code.

### 9.2 Keras and TensorFlow

Keras is closely tied to the TensorFlow library and acts as an **interface** for it — since TensorFlow 2.x, `tf.keras` is TensorFlow's own official high-level API, meaning Keras and TensorFlow are effectively bundled together. Keras allows you to define and train neural network models with only a few lines of code, hiding away most of the low-level graph-construction details you would otherwise need to manage manually.

### 9.3 Frameworks Supported by Keras

Historically, Keras was designed to be backend-agnostic and could run on top of multiple deep learning engines:

- **TensorFlow**
- **Theano**
- **CNTK** (Microsoft Cognitive Toolkit)
- **MXNet**
- **PlaidML**

```
Keras
   |
   +-- TensorFlow, MXNet, CNTK, Theano   (backend engines)
   |
   +-- CPU / GPU / TPU                   (hardware)
```

### 9.4 Features of Keras

- **Time-Saving**: efficient as a versatile library, enabling utilization across a wide range of machine learning tasks and accommodating multiple types of models.
- **Powerful**: follows the principle of *progressive disclosure of complexity* — simple things are simple, but you can access lower-level control when you need it.
- **Flexible**: provides industry-strength performance and scalability, while still letting the user define and train models with very little code.

### 9.5 Why Use Keras?

- Allows easy and fast prototyping.
- Supports convolutional networks, recurrent networks, and combinations of both.
- Follows best practices to reduce cognitive load on the developer.
- Provides clear and actionable feedback for user error (helpful error messages rather than cryptic stack traces).

### 9.6 Advantages of Keras

1. **User-friendly and quick development** — Keras provides clear and concise APIs, enabling quick experimentation and easy, fast development of deep learning models.
2. **Quality documentation and good community support** — Keras is well-documented, with a wide range of tutorials and resources, and has a huge, active community across several open-source platforms.
3. **Multiple backends and modularity** — you can train a Keras model on one backend and test its results on another; its modular design lets you plug together building blocks with limited restriction.
4. **Pretrained models** — Keras provides access to various deep learning models with pretrained weights, which you can use directly for predictions or as feature extractors (transfer learning).
5. **Multiple GPU support** — Keras allows training on a single GPU or multiple GPUs, with built-in support for data parallelism, letting it process large amounts of data efficiently.

---

## 10. Keras API Components

### 10.1 Layers

The `tf.keras.layers.Layer` class is the **fundamental abstraction** in Keras. A layer encapsulates:

- A **state** (its weights).
- Some **computation** (the forward-pass logic it performs on its inputs).

Layers are **recursively composable**: if a layer instance is assigned as an attribute of another layer, the outer layer will automatically start tracking the weights created by the inner layer. This composability is what lets you build arbitrarily deep and complex models simply by nesting simpler layers/blocks inside each other.

### 10.2 Models

A **model** is an object that combines layers and can be trained on data. The `tf.keras.Model` class features several built-in training and evaluation methods:

| Method | Purpose |
|---|---|
| `tf.keras.Model.compile` | Configures the model for training — sets the loss function, optimizer, and metrics. |
| `tf.keras.Model.fit` | Trains the model for a predetermined number of epochs. |
| `tf.keras.Model.evaluate` | Reports the model's loss and metric values (as set in `compile`) on a given dataset. |
| `tf.keras.Model.predict` | Predicts the output for the given input samples. |

---

## 11. Sequential and Functional APIs in Keras

Keras provides two primary ways to build models: the **Sequential API** and the **Functional API**.

### 11.1 Sequential API

The Sequential API is the simpler of the two, and is best suited for models that have exactly **one input tensor and one output tensor**. It lets you create models **layer-by-layer in a linear stack** — each layer feeds directly into the next.

```python
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Activation

model = Sequential([
    Dense(64, input_shape=(input_dim,), activation='relu'),
    Dense(10, activation='softmax')
])
```

**What this code does:** it builds a simple two-layer feed-forward network. The first `Dense` layer has 64 neurons, expects input vectors of size `input_dim`, and applies a ReLU activation. The second `Dense` layer has 10 output neurons with a `softmax` activation — a common configuration for a 10-class classification problem, since softmax turns the raw outputs into a probability distribution over the 10 classes.

### 11.2 Functional API

The Functional API is more flexible and powerful. It allows the creation of complex models such as:

- Multi-input or multi-output models.
- Models with **shared layers**.
- Models with **non-sequential data flows** (e.g., skip connections, branches that merge back together).

```python
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense, Activation

input_layer = Input(shape=(input_dim,))
hidden_layer = Dense(64, activation='relu')(input_layer)
output_layer = Dense(10, activation='softmax')(hidden_layer)

model = Model(inputs=input_layer, outputs=output_layer)
```

**What this code does:** rather than passing a list of layers to `Sequential`, the Functional API treats layers as callables applied directly to tensors. `Input` creates a placeholder tensor for the model's input; each subsequent layer is called on the output tensor of the previous layer, explicitly wiring the graph. Finally, `Model(inputs=..., outputs=...)` ties the whole graph together into a trainable model. This example produces the exact same architecture as the Sequential example above, but the explicit wiring is what allows you to branch, merge, or reuse layers in more complex architectures.

### 11.3 Sequential API vs. Functional API

| Aspect | Sequential API | Functional API |
|---|---|---|
| **Architecture** | Linear stack of layers | Customized and complex (branches, merges, multiple I/O) |
| **Complexity** | Limited to simple models | Supports complex architectures |
| **Flexibility** | Limited customization | High customization and control |
| **Usage** | Simple models, quick start | Complex architectures requiring fine control |

### Assisted Practice

- **5.09_Sequential_APIs_in_TensorFlow**
- **5.10_Functional_APIs_in_TensorFlow**

*Note: refer to the Reference Material section to download the notebook files corresponding to each topic.*

---

## 12. Creating a Keras Model — Step by Step

Building a Keras model generally follows six steps:

1. **Import** the required libraries and load the dataset.
2. **Assign** the number of layers, the number of nodes in each layer, and the activation function to be used.
3. **Compile** — set the loss function and select a set of weights to evaluate against it (along with the optimizer and metrics).
4. **Fit** the model using backpropagation and weight optimization with the input data.
5. **Evaluate** the model's performance on a separate validation/test dataset.
6. **Predict** the output using the trained/prepared model.

Below is a worked example using the classic **CIFAR-10** image classification dataset (60,000 32×32 color images across 10 classes).

### Step 1: Import the libraries and load data

```python
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Convolution2D, MaxPooling2D, Flatten, Dense
from tensorflow.keras.datasets import cifar10
from tensorflow.keras.utils import to_categorical

# Load and preprocess the CIFAR-10 dataset
(x_train, y_train), (x_test, y_test) = cifar10.load_data()
x_train = x_train.astype('float32') / 255
x_test = x_test.astype('float32') / 255
y_train = to_categorical(y_train, 10)
y_test = to_categorical(y_test, 10)

# Image dimensions
img_width, img_height = x_train.shape[1], x_train.shape[2]
```

**What this code does:** it loads the CIFAR-10 dataset (already split into train/test sets), then **normalizes** the pixel values from the raw `0–255` range down to `0.0–1.0` (dividing by 255) — a standard preprocessing step that helps neural networks train faster and more stably. It also **one-hot encodes** the integer labels (e.g., class `3`) into 10-length binary vectors (e.g., `[0,0,0,1,0,0,0,0,0,0]`) via `to_categorical`, since the model's output layer will use softmax over 10 classes. Finally, it reads the image width/height directly from the training data's shape.

### Step 2: Create the model

```python
# Model definition
model = Sequential()
model.add(Convolution2D(16, (5, 5), activation='relu', input_shape=(img_width, img_height, 3)))
model.add(MaxPooling2D(2, 2))
model.add(Convolution2D(32, (5, 5), activation='relu'))
model.add(MaxPooling2D(2, 2))
model.add(Flatten())
model.add(Dense(1000, activation='relu'))
model.add(Dense(10, activation='softmax'))
```

**What this code does:** this builds a convolutional neural network (CNN) as a linear stack of layers using the Sequential API:
- Two convolutional blocks (`Convolution2D` + `MaxPooling2D`) extract spatial features from the images, progressively increasing the number of filters (16 → 32) while the pooling layers shrink the spatial resolution.
- `Flatten()` converts the resulting 3-D feature maps into a 1-D vector so they can feed into fully-connected (`Dense`) layers.
- A `Dense(1000, activation='relu')` layer acts as a large fully-connected hidden layer.
- The final `Dense(10, activation='softmax')` layer produces a probability distribution over the 10 CIFAR-10 classes.

### Step 3: Compile the model

```python
# Compile the model
model.compile(loss='binary_crossentropy',
              optimizer='adam',
              metrics=['accuracy'])
```

**What this code does:** `compile()` configures the model for training. It sets:
- The **loss function** — here `binary_crossentropy` (note: for a genuinely 10-class multi-class problem, `categorical_crossentropy` is more standard; `binary_crossentropy` is more commonly used for binary or multi-label problems — this is a detail worth double-checking when reusing this snippet).
- The **optimizer** — `adam`, which searches through different weight values to minimize the loss.
- The **metrics** to track — `accuracy`, so that Keras reports accuracy alongside loss during training.

### Step 4: Fit (train) the model

```python
# Train the model
model.fit(x_train, y_train,
          batch_size=32,
          epochs=10,
          verbose=1,
          validation_data=(x_test, y_test))
```

**What this code does:** `fit()` executes the actual training loop: it trains the model on `x_train`/`y_train`, processing the data in batches of 32 samples at a time, repeating this for 10 full epochs (passes over the entire training set). `verbose=1` prints a progress bar during training, and passing `validation_data=(x_test, y_test)` means that after every epoch, Keras also reports how the model performs on the held-out test set — useful for spotting overfitting early.

### Step 5: Evaluate the model

```python
# Evaluate the model
score = model.evaluate(x_test, y_test, verbose=0)
print('Test loss:', score[0])
print('Test accuracy:', score[1])
```

**What this code does:** `evaluate()` runs the trained model against the test dataset one final time and returns the loss and any tracked metrics (accuracy, in this case) as a list — `score[0]` is the test loss and `score[1]` is the test accuracy. `verbose=0` suppresses the progress output.

### Step 6: Predict with the model

```python
classes = model.predict(x_test, batch_size=128)
```

**What this code does:** `predict()` runs the trained model in inference mode on new data (`x_test`), returning the model's raw output — in this case, a probability distribution over the 10 classes for each test image, processed in batches of 128 images at a time. To get the actual predicted class label, you would typically take `argmax` over the last axis of `classes`.

---

## 13. Implementation of Loss Functions

Loss functions in TensorFlow are implemented using TensorFlow's **computational graph** and **automatic differentiation** capabilities — meaning TensorFlow can automatically compute the gradient of the loss with respect to every weight in the network, without you writing any calculus by hand.

The loss function's job is to **estimate the model's error** (how far its predictions are from the true values) and drive changes to the weights in the hidden layers so as to **reduce the loss** in the next round of evaluation. This is the mechanism — via backpropagation and gradient descent — through which a neural network actually "learns."

### How Are Loss Functions Implemented in TensorFlow?

To implement a loss function, you must first choose a loss function that fits the framing of your specific predictive-modeling problem (e.g., regression vs. classification, binary vs. multi-class). The output layer's configuration must also be compatible/sufficient for the chosen loss function (for example, a softmax output layer pairs naturally with categorical cross-entropy).

```python
model.compile(optimizer=tf.optimizers.Adam(),
              loss='mae',
              metrics='mean_absolute_error')
```

**What this code does:** this compiles the model using the **Adam** optimizer and **Mean Absolute Error (`mae`)** as the loss function — a common choice for regression problems (predicting continuous numeric values rather than class labels). It also tracks `mean_absolute_error` as an evaluation metric during training.

### Assisted Practice

- **5.11_Hands-on TensorFlow and Keras: Part B**

*Note: refer to the Reference Material section to download the notebook files corresponding to each topic.*

---

## Key Takeaways

- **TensorFlow** is a flexible, open-source library for machine learning and artificial intelligence, built around the concept of tensors and dataflow graphs.
- **TensorBoard**, a suite of visualization tools, makes it easier to visualize the computational graph and monitor training metrics.
- **TFLearn** is a high-level deep learning library built on TensorFlow, providing simplified development of neural networks with a user-friendly API.
- **Keras** is a high-level deep learning API designed for easy and fast model development, built on top of TensorFlow, and offers both a **Sequential API** (simple, linear stacks of layers) and a **Functional API** (flexible, complex architectures).

---

## 📝 Practice Questions

1. **(MCQ)** Which company/team originally developed TensorFlow?
   - **A.** Facebook AI Research
   - **B.** Google Brain
   - **C.** Microsoft Research
   - **D.** OpenAI

2. **(MCQ)** In TensorFlow, how is data represented internally?
   - **A.** As native Python integers and floats
   - **B.** As NumPy arrays only
   - **C.** As objects called tensors
   - **D.** As JSON objects

3. **(MCQ)** In a TensorFlow dataflow graph, what do the **edges** represent?
   - **A.** Mathematical operations
   - **B.** Multidimensional data arrays (tensors) moving between nodes
   - **C.** The model's hyperparameters
   - **D.** Python variable names

4. **(MCQ)** Which of the following is a benefit of using dataflow graphs in TensorFlow?
   - **A.** They prevent the model from ever overfitting
   - **B.** They make it easy to identify operations that can run in parallel
   - **C.** They eliminate the need for a GPU
   - **D.** They automatically choose the best neural network architecture

5. **(MCQ)** Which API level is `tf.keras` considered?
   - **A.** Low-level API, for maximum control
   - **B.** High-level API, for ease of use without sacrificing flexibility
   - **C.** A completely separate framework unrelated to TensorFlow
   - **D.** A hardware abstraction layer only

6. **(Short answer)** Name three real-world use-case industries mentioned in the lesson where TensorFlow has been applied, and give one example application from each.

7. **(Short answer)** What is TensorFlow Playground, and what is its main educational value for someone learning about neural networks?

8. **(MCQ)** What is the main advantage of the Sequential API over the Functional API in Keras?
   - **A.** It supports multi-input, multi-output architectures
   - **B.** It supports skip connections
   - **C.** It is simpler and best suited for a linear stack of layers with one input/output
   - **D.** It requires no compilation step

9. **(MCQ)** Which of the following architectures would require you to use the Keras **Functional API** rather than the Sequential API?
   - **A.** A single stack of Dense layers for tabular classification
   - **B.** A model with two separate inputs that get merged partway through the network
   - **C.** A single Conv2D layer followed by a Dense layer
   - **D.** Any model with fewer than 5 layers

10. **(What does this code do?)**
    ```python
    model = Sequential()
    model.add(Convolution2D(16, (5, 5), activation='relu', input_shape=(32, 32, 3)))
    model.add(MaxPooling2D(2, 2))
    model.add(Flatten())
    model.add(Dense(10, activation='softmax'))
    ```
    Describe, in your own words, what each layer does and what kind of task this network is likely designed for.

11. **(What does this code do?)**
    ```python
    tflearn.is_training(True)
    ```
    What effect does this line have on layers such as Dropout inside a TFLearn model?

12. **(MCQ)** Which of the following is **not** listed in the lesson as a feature of TFLearn?
    - **A.** Fast prototyping through modular built-in components
    - **B.** Full transparency over TensorFlow
    - **C.** Automatic hyperparameter tuning without any configuration
    - **D.** Effortless device placement across CPUs/GPUs

13. **(Short answer)** In the Keras `model.compile()` step, what three things are typically configured, and why does the loss function need to match the output layer's configuration?

14. **(MCQ)** In TFLearn's verbosity levels for visualization, which level provides "Best Visualization" (logging loss, metric, gradients, weights, activations, and sparsity)?
    - **A.** Level 1
    - **B.** Level 2
    - **C.** Level 3
    - **D.** Level 4

15. **(Short answer)** Explain the difference between `model.fit()`, `model.evaluate()`, and `model.predict()` in `tf.keras.Model`.

16. **(MCQ)** Which statement correctly distinguishes TensorFlow from TFLearn?
    - **A.** TensorFlow is high-level and TFLearn is low-level
    - **B.** TensorFlow is a lower-level library offering fine control, while TFLearn is a high-level wrapper focused on rapid prototyping
    - **C.** TFLearn and TensorFlow are unrelated, competing libraries
    - **D.** TFLearn replaces the need for Python entirely

### Answers

1. **B — Google Brain.** TensorFlow was developed by the Google Brain team and released as open source in 2015.

2. **C — As objects called tensors.** TensorFlow encapsulates all data (including Python lists passed into it) inside tensor objects rather than storing them as native Python primitives.

3. **B — Multidimensional data arrays (tensors) moving between nodes.** In a dataflow graph, nodes represent operations, while edges represent the tensors flowing between those operations.

4. **B — They make it easy to identify operations that can run in parallel.** Because dependencies are explicit in the graph structure, TensorFlow's runtime can safely parallelize independent operations across CPUs/GPUs.

5. **B — High-level API.** `tf.keras` is one of the high-level APIs (along with `tf.estimator`) that make TensorFlow easier to use without sacrificing flexibility or performance, unlike the lower-level TensorFlow Core API.

6. **Sample answer:** Healthcare — Google's DermAssist app diagnoses skin conditions from photos. Social Media — X (Twitter) ranks tweets by user preference using TensorFlow. Education — TensorFlow is used to filter toxic classroom chat messages on virtual learning platforms. (Retail is also acceptable: personalized e-commerce recommendations or AR makeup try-on.)

7. TensorFlow Playground is a free, browser-based, no-code tool for experimenting with small neural networks. Its main educational value is letting learners directly manipulate hyperparameters (learning rate, activation function, regularization, number of layers/neurons) and immediately see the effect on the model's decision boundary and loss — building intuition that's hard to get from equations alone.

8. **C — It is simpler and best suited for a linear stack of layers with one input/output.** The Sequential API is intentionally limited to single-input, single-output, layer-by-layer architectures in exchange for simplicity.

9. **B — A model with two separate inputs that get merged partway through the network.** Multi-input/multi-output and non-linear data flows require the Functional (or Subclassing) API, since Sequential only supports one linear chain of layers.

10. This builds a small CNN: the `Convolution2D` layer scans the 32×32×3 input image with learned filters (5x5 kernels, 16 filters) and applies ReLU activation to extract low-level visual features; `MaxPooling2D` downsamples the resulting feature maps, reducing spatial size while keeping the strongest activations; `Flatten` reshapes the 3-D feature maps into a 1-D vector; and the final `Dense(10, activation='softmax')` layer outputs a probability distribution over 10 classes. This architecture is designed for **image classification** into 10 categories (matching the CIFAR-10 example used in the lesson).

11. Calling `tflearn.is_training(True)` sets the framework-wide `is_training` flag to `True`, which tells layers like Dropout (and BatchNorm) to behave in "training mode" — for Dropout specifically, this means it will actually randomly zero out a fraction of activations (`tf.nn.dropout`) rather than passing all activations through unchanged, as it would when `is_training` is `False` (inference mode).

12. **C — Automatic hyperparameter tuning without any configuration.** The lesson lists ease of use, fast prototyping, transparency, helper training functions, easy visualization, and effortless device placement as TFLearn features — automatic hyperparameter tuning is not among them.

13. `model.compile()` typically configures the **loss function** (how error is measured), the **optimizer** (the algorithm used to update weights, e.g. Adam or SGD), and the **metrics** to monitor (e.g., accuracy). The loss function must match the output layer's configuration because the mathematical form of the loss assumes a particular kind of output — for example, a softmax output (producing a probability distribution) pairs with categorical cross-entropy loss, while a single linear output pairs with a regression loss like MAE or MSE; mismatching them produces nonsensical gradients or errors.

14. **D — Level 4.** Level 4 logs loss, metric, gradients, weights, activations, and sparsity, offering the richest ("Best Visualization") diagnostics at the cost of speed, compared to Level 1's minimal "Best Speed" logging.

15. `model.fit()` **trains** the model on labeled data over a set number of epochs, updating its weights via backpropagation. `model.evaluate()` **measures** the trained model's loss and metrics (e.g., accuracy) on a held-out dataset, without updating any weights. `model.predict()` **runs inference** — it takes new input samples and returns the model's raw output/predictions, with no ground-truth labels involved and no weight updates.

16. **B — TensorFlow is a lower-level library offering fine control, while TFLearn is a high-level wrapper focused on rapid prototyping.** TFLearn is built on top of TensorFlow specifically to provide a simpler, faster-to-prototype-with API while still allowing full transparency into (and compatibility with) the underlying TensorFlow graph.
