# Lesson 03: Artificial Neural Network

*Deep Learning with Keras and TensorFlow*

## Learning Objectives

By the end of this lesson, you will be able to:

- Understand the structure and function of neural networks, including perceptrons and multilayer perceptrons.
- Analyze various activation functions like ReLU, Sigmoid, and Softmax and their effects on performance.
- Create and optimize neural network models, addressing issues like vanishing and exploding gradients.
- Evaluate the performance of different neural networks, including DNNs, CNNs, and RNNs.

---

## Business Scenario

A startup company called **AI Detect** is developing a new product that uses perceptron-based machine learning to detect fraud in financial transactions. The perceptron-based algorithm is specifically designed to identify patterns of fraudulent behavior in data, allowing the system to detect fraud with high accuracy.

The system takes in large volumes of financial transaction data and uses **forward propagation** to classify each transaction as either fraudulent or legitimate. If a transaction is classified as fraudulent, the system alerts the relevant authorities for further investigation.

The company has already tested the system on a small scale and achieved promising results, but it is now seeking funding to scale up its operations and expand its customer base. AI Detect plans to market its product to financial institutions and government agencies responsible for investigating financial crimes.

> **Why this matters:** This scenario is a good motivating example for the whole lesson — a perceptron takes many numeric signals (transaction amount, location mismatch, time of day, device fingerprint, etc.), weighs their relative importance, sums them up, and produces a binary decision (fraud / not fraud). Everything that follows — weights, bias, activation functions, forward propagation, and training via backpropagation — is exactly the machinery that makes a system like AI Detect's possible.

---

## 1. Neurons

### 1.1 Biological Neurons

Neurons are interconnected nerve cells that build the nervous system and transmit information throughout the body. A biological neuron is made up of several key parts:

| Part | Function |
|---|---|
| **Cell nucleus** | Used for information processing (the "computation" center of the cell). |
| **Dendrites** | Receive inputs from other neurons — the "input wires" of the cell. |
| **Synapse** | The connection between two nerve cells, across which a signal passes from one neuron to the next. |
| **Axon / Axon terminals** | Transmit the biological neuron's output to other neurons — the "output wire." |
| **Myelin sheath** | Insulates the axon, helping electrical impulses travel faster along it. |

In short: **dendrites receive → nucleus processes → axon transmits the output → synapse hands it off to the next neuron.** This receive-process-transmit pattern is the direct inspiration for the artificial neuron model used in every neural network.

### 1.2 Artificial Neurons

**Definition:** An artificial neuron is analogous to a biological neuron. Each artificial neuron takes inputs, multiplies each one by a separate weight, sums the weighted inputs, and passes that sum through a **transfer (activation) function** to produce a nonlinear output.

Think of it as a mini decision-maker: it looks at several pieces of evidence (inputs), decides how much to trust each piece (weights), tallies up the weighted evidence (summation), and then makes a final call (activation function) about whether to "fire" or not.

**How the artificial neuron works, step by step:**

1. A nerve cell (and its artificial analogue) can be thought of as a simple logic gate with a binary output — it either fires or it doesn't.
2. Dendrites (inputs) feed signals into the cell with a certain **threshold** — if the combined signal exceeds the threshold, an output signal is generated; otherwise, it is not.
3. Mathematically, for inputs `x1, x2, … xn` with corresponding weights `w1, w2, … wn` and a bias `b`:

```
Summation:  Σ(i=1 to n) wi·xi + b
Output:     passed through a threshold/activation unit
```

Where:
- `W1, W2, … Wn` — weights of the connections (how important each input is)
- `X1, X2, … Xn` — the inputs themselves
- `b` — the bias (a constant offset added to the sum)

### 1.3 Biological Neurons vs. Artificial Neurons

The artificial neuron is a deliberate simplification of the biological one — each biological structure maps to a computational equivalent:

| Biological Neuron | Artificial Neuron |
|---|---|
| Cell nucleus | Node |
| Dendrites | Input |
| Synapses | Weights (interconnections) |
| Axon | Output |

So, "dendrites receiving signals with varying importance" becomes "inputs multiplied by weights," and "the nucleus deciding whether to fire" becomes "the summation plus activation function deciding the node's output."

---

## 2. Neural Networks and Types of Neural Networks

### 2.1 What Is a Neural Network?

A **neural network** consists of interconnected computation modules (artificial neurons) that simulate the behavior of biological neurons. Each neural network is organized into layers of nodes:

- **Input layer** — receives the raw data/features.
- **One or more hidden layers** — perform intermediate computations, progressively extracting more abstract representations of the data.
- **Output layer** — produces the final prediction.

### 2.2 How a Neural Network Processes Information

An ANN (Artificial Neural Network) processes information in the following sequence, and the process continues layer by layer until the final output is produced:

1. Inputs are passed into the first layer.
2. Each individual neuron receives the inputs and assigns a weight to each of them.
3. The neurons generate an output based on the assigned weights (summed and passed through an activation function).
4. The outputs from that layer are forwarded to the next layer for further processing, and this repeats until the output layer is reached.

This is the essence of **forward propagation** — data flows strictly forward, layer by layer, from input to output.

### 2.3 Types of Neural Networks

Neural networks are used to solve complex problems that require analytical calculations that traditional rule-based programs struggle with. The major types include:

- **Perceptron** — the simplest ANN; a single computational unit for binary classification.
- **Multilayer Perceptron (MLP)** — multiple layers of perceptrons stacked together to model non-linear relationships.
- **Deep Neural Networks (DNNs)** — networks with many hidden layers, capable of learning highly complex patterns.
- **Convolutional Neural Networks (CNNs)** — specialized for spatial/visual data such as images.
- **Recurrent Neural Networks (RNNs)** — specialized for sequential data such as time series or language.

#### Perceptron and Multilayer Perceptron

- **Perceptron:** the simplest type of ANN, mainly used for binary prediction. A perceptron can only work correctly if the data is **linearly separable** (i.e., a straight line/plane can separate the two classes).
- **Multilayer Perceptron (MLP):** consists of multiple layers of perceptrons. Inputs pass through each layer, and the outputs of the last layer are the final outputs of the MLP. Because it stacks multiple layers (each with a nonlinear activation), it can handle more complex problems by learning **non-linear** relationships — something a single perceptron cannot do.

#### Deep Neural Networks (DNN)

A DNN is a multilayered computational model that processes data in a layered manner, refining information at each successive layer — loosely analogous to how a human brain processes sensory information in stages. Because a DNN has many hidden layers ("depth"), it can effectively address complex problems such as image processing and speech recognition, where simple linear models would fail.

#### Convolutional Neural Network (CNN)

CNNs were neurobiologically motivated by findings about locally sensitive, orientation-selective nerve cells in the visual cortex (regions such as V1, V2, V4, and IT progressively extract edges → shapes → faces/objects). CNNs analyze visual data and are inspired by the brain's visual cortex, making them highly effective for recognizing patterns in images.

*Example:* Image classification — a CNN learns to detect edges and lines in early layers, combines them into shapes in middle layers, and recognizes faces/objects in later layers.

#### Recurrent Neural Network (RNN)

RNNs handle **sequential data**, making them suitable for time series and language modeling tasks. Unlike a plain feedforward network, an RNN maintains a **state (memory)** of previous inputs — the network's output is recycled back into itself as part of the input for the next time step.

> **Note:** You can think of the state as the "memory" of the RNN — it recurs into the network with each new input, letting the network use context from earlier in the sequence (e.g., previous words in a sentence) to inform its current prediction.

### 2.4 Network Architecture

Deep neural networks consist of multiple hidden layers. Critically, the architecture is programmable/configurable: one can set the **number of layers** and the **number of neurons per layer** to match the complexity of the problem being solved. There is no single "correct" architecture — it is a design choice tuned through experimentation.

### 2.5 Model Performance vs. Data Size

Deep neural network models tend to have **greater precision** than conventional/traditional ML techniques (such as classical statistical learning algorithms), but this advantage only shows up once enough data is available to train them. In other words:

- With **small data**, traditional ML algorithms or small/medium neural networks tend to perform comparably or better.
- With **large data**, larger neural networks pull ahead in performance because they have the capacity to model far more complex relationships — but they need that volume of data to avoid overfitting and to actually learn useful patterns.

This is a key practical trade-off: deep learning's power comes at the cost of requiring much more labeled data (and compute) to realize it.

### 2.6 Combination of Neural Network Layers

- The **input layer** represents the dimensions of the input vector (i.e., how many features describe each data point).
- The **hidden layer(s)** represent intermediary nodes that divide the input space into regions with "soft" (non-rigid, probabilistic) boundaries — this is what allows the network to model curved/complex decision boundaries rather than only straight lines.
- The **output layer** represents the final output of the network (e.g., class probabilities).

The number of layers in a CNN or RNN depends on the complexity of the task and data — deeper architectures are generally used for more complex problems, at the cost of more computation and a greater risk of training difficulties (like vanishing gradients, discussed later).

---

## 3. Perceptron

### 3.1 What Is a Perceptron?

The **perceptron** is the most fundamental type of artificial neural network, designed for **binary classification** tasks. It computes a weighted sum of its inputs, which is then passed through a **step function** to determine the output class (0 or 1).

**Perceptron equation:**

```
f(x) = 1   if  w·x + b > 0
       0   otherwise
```

Where:
- `w` — a vector of real-valued **weights**.
- `b` — the **bias**, an offset term that adjusts (shifts) the decision boundary independent of the input values.
- `x` — the vector of input values.

Intuitively: the perceptron draws a straight line (or, in higher dimensions, a hyperplane) through the input space. Everything on one side of the line is classified as 1; everything on the other side is classified as 0. The weights determine the *orientation* of that line, and the bias determines how far it is shifted from the origin.

### 3.2 Working of a Perceptron

Consider a perceptron with three inputs `x1, x2, x3` and one output, where each input has a corresponding weight `w1, w2, w3` reflecting its importance:

- The neuron computes the weighted sum: `x1·w1 + x2·w2 + x3·w3` (plus bias).
- This works for **any number of inputs** — the same weighted-sum idea generalizes to `n` inputs.
- The perceptron is fundamentally a **linear classifier**: it can only learn a decision boundary that is a straight line (in 2D) or a hyperplane (in higher dimensions).

**Training intuition:**
- The weights of the perceptron are trained using different sets of labeled inputs.
- On every pass, the perceptron produces an output of either 0 or 1, which is compared against the ground truth (the correct label).
- Based on how wrong the prediction was, the weights are adjusted to make future predictions better.
- A perceptron works well **only** when the classes in the data are linearly separable — if a straight line can't cleanly divide the two classes, a single perceptron will never converge to a perfect solution.

### 3.3 Components of a Perceptron

| Component | Role |
|---|---|
| **Inputs** (`x1…xn`) | The set of values for which we want to predict an output. |
| **Weights** (`w1…wn`) | Real values associated with each feature, indicating how important that feature is for the final prediction. Larger magnitude = more influence. |
| **Bias** (`b`) | Shifts the activation function left or right; conceptually similar to the y-intercept in a line equation (`y = mx + c`). Lets the neuron fire even when all inputs are zero, or prevents it from firing too easily. |
| **Summation function** | Binds the weights and inputs together and computes their weighted sum (`Σ wi·xi`). |
| **Activation function** (`f`) | Introduces nonlinearity and converts the raw weighted sum into the final output. |

**Overall equation:**

```
Output = f(w · x + b)
```

### 3.4 Perceptron as a Feedforward Neural Network

A perceptron (and networks built from perceptrons) is a **feedforward neural network**:

- **Information flow is unidirectional** — it moves only from input → hidden → output, never backward during inference.
- **Information is distributed** across many weighted connections rather than stored in one place.
- **Information processing is parallel** — all neurons within a layer can, in principle, compute simultaneously.

In a Feedforward Neural Network (FNN):
- Information moves only from the input layer, through the hidden layers, to the output layer.
- It **cannot remember** anything that happened in the recent past, except what it "learned" during training (i.e., its fixed weights).
- Since it only considers the current input, it has **no notion of order in time** — each prediction is independent of prior predictions.
- Information moves straight through the network and never touches the same node twice per forward pass; the network has **no memory** of the input it previously received (this is the key contrast with RNNs, which *do* retain state).

### 3.5 Multilayer Perceptrons (MLP)

A Multilayer Perceptron is a type of feedforward artificial neural network that produces a collection of outputs from a set of inputs, built from **multiple stacked layers** of perceptrons (input layer → one or more hidden layers → output layer).

**General linear-algebraic equation for a DNN/MLP:**

```
y = f(w · x + b)
```

Where:
- `y` — the output
- `x` — the input
- `w` — the weight matrix
- `b` — the bias vector
- `f` — the activation function

This is exactly the single-neuron equation from before, generalized to matrix form — every neuron in every layer performs this same weighted-sum-then-activate computation.

### 3.6 The Exclusive OR (XOR) Problem

A single perceptron can learn to represent anything that is **linearly separable** — anything separable by a hyperplane. However, it **cannot represent XOR**, because the XOR function is *not* linearly separable.

| X1 | X2 | X1 XOR X2 |
|---|---|---|
| -1 | -1 | -1 |
| -1 | 1 | 1 |
| 1 | -1 | 1 |
| 1 | 1 | -1 |

If you plot these four points, the "-1" outputs and "1" outputs cannot be separated by any single straight line — you'd need at least two lines (or a curved boundary), which is exactly why this problem historically motivated the move from single perceptrons to **multilayer** perceptrons (which combine several linear boundaries to represent nonlinear functions like XOR).

### 📓 Assisted Practice

- **Notebook: `3.04_Perceptron-Based Classification Model`** — hands-on notebook exploring how a perceptron performs binary classification.

---

## 4. Activation Functions

### 4.1 Why Do We Need Them?

Before producing an output from a perceptron, the network needs to decide **whether to "activate" the neuron or not** — that is exactly the job of the activation function.

The sum of products of inputs and weights (`Σ wi·xi + b`) can range anywhere from `-∞` to `+∞`. Left alone, this unbounded value is not very useful for making a clean decision. The activation function is applied on top of this raw sum to:

- **Bound the output** into a usable range (e.g., between 0 and 1, or -1 and 1) so it can represent something meaningful like a probability or a class decision.
- **Introduce non-linearity**, letting the network model complex, non-linear relationships in data — without a non-linear activation function, stacking multiple layers would collapse mathematically into just one big linear function, and depth would add no extra representational power at all.

**Formulas:**

```
Raw output:        y = Σ(weights · input) + bias        (ranges from -∞ to +∞)
After activation:  y = ActivationFunction(Σ(weights · input) + bias)
```

Activation functions are mathematical equations that determine the final output of a neuron/network. They play a crucial role in whether — and how fast — a neural network **converges** during training, i.e., how quickly and reliably it settles on good weight values.

### 4.2 Types of Activation Functions

The slide deck highlights four commonly used activation functions:

#### a) Step Function

The step function is the classic activation used in the original perceptron. Consider a perceptron `P` with weighted inputs `x1·w1 + x2·w2 + b·w0`:

```
y = 1  if (x1·w1 + x2·w2 + b·w0) > 0
y = 0  otherwise
```

The perceptron "activates" (outputs 1) whenever the sum of weighted inputs is positive (non-zero and positive); otherwise it outputs 0. Graphically, this looks like a sharp jump from 0 to 1 at the threshold — a hard, discontinuous cutoff. This simplicity is also its weakness: the step function has a derivative of zero almost everywhere, which makes it useless for gradient-based training methods like backpropagation.

#### b) Sigmoid Function

The **Sigmoid** activation function squashes any real-valued input into the range **(0, 1)**, making it useful for **binary classification** tasks (the output can be interpreted as a probability).

```
S(x) = 1 / (1 + e^-x)
```

Unlike the step function, sigmoid is smooth and differentiable everywhere, which makes it usable in gradient-based training. Its main drawback (discussed below) is the vanishing gradient problem in deep networks.

#### c) Rectified Linear Unit (ReLU)

ReLU is the **most widely used activation function** in modern deep learning, defined as:

```
f(x) = max(0, x)
```

If the input to a neuron is zero or negative, ReLU outputs 0. If the input is positive, the output equals the input directly (an identity pass-through). This simple piecewise-linear behavior is cheap to compute and has favorable gradient properties for positive inputs.

#### d) Softmax Function

The **Softmax** function is a variant of the sigmoid function, particularly useful for handling **multiclass classification** problems.

- Used when there are **more than two classes** to predict.
- Commonly found in the **output layer** of image classification models (and other multiclass classifiers).
- **Normalizes** outputs for each class to fall between 0 and 1, and — critically — all the class outputs sum to 1, so they can be interpreted as a probability distribution.
- Achieves this by dividing each class's raw score by the **sum of all classes' raw scores** (exponentiated).

### 4.3 ReLU vs. Sigmoid

| Aspect | Sigmoid | ReLU |
|---|---|---|
| Deep network training | Suffers from the **vanishing gradient** problem (gradients shrink toward zero as they propagate back through many layers, stalling learning in early layers). | Largely avoids the vanishing gradient problem for positive inputs, since its gradient is a constant 1 there. |
| Computation | Mathematically more complex (involves an exponential). | Simple calculation — just a max operation. |

This is why ReLU (and its variants) largely replaced sigmoid/tanh as the default activation for hidden layers in modern deep networks, while sigmoid/softmax are still commonly used in the *output* layer for classification tasks.

### 📓 Assisted Practice

- **Notebook: `3.06_Configure_Neural_Network_and_Activation_Function`** — hands-on notebook exploring how to configure a neural network and experiment with different activation functions.

---

## 5. Forward Propagation in the Perceptron

### 5.1 Two Phases of Training a Perceptron Model

Training a perceptron (or any neural network) model involves two complementary phases:

1. **Forward propagation (forward pass)** — computing the network's prediction given the current weights.
2. **Backward propagation (backprop)** — using the prediction error to update the weights.

### 5.2 Concept of Forward Propagation

A perceptron is a type of feedforward network: the process of generating an output flows in **one direction only**, from the input layer to the output layer (no loops, no going backward during inference).

For a simple perceptron with two inputs:

```
If  x1·w1 + x2·w2 + b > 0,   then y = 1
If  x1·w1 + x2·w2 + b <= 0,  then y = 0
```

At the start of training, the weights `w1` and `w2` (and bias `b`) are **randomly initialized**. The objective of training is to iteratively search for the right set of weights that produces the best (most accurate) predictions — this is where the loss function, cost function, and gradient descent (covered next) come in.

---

## 6. Loss Function and Cost Function

### 6.1 What Is a Loss Function?

In a deep learning model, the predicted output typically deviates from the actual (true) value. The quantitative measure of this difference is called the **loss**.

*Example (archery analogy):* if an arrow hits the target at point 8, but the archer was aiming for (predicted) point 10, the loss is `actual − predicted = 8 − 10 = -2`.

The **loss function** — also known as the **cost function** or **objective function** — measures the discrepancy between the predicted outputs of a machine learning model and the true values in the training data. A common choice, especially for regression, is **Mean Squared Error (MSE)**:

```
Loss (MSE) = (1/n) · Σ (i=0 to n) (y_true,i − y_pred,i)²
```

Where:
- `n` — the number of data points in the training set.
- `y_true,i` — the true (ground-truth) value for data point `i`.
- `y_pred,i` — the model's predicted value for data point `i`.

Squaring the difference ensures that positive and negative errors don't cancel out, and it penalizes larger errors disproportionately more than smaller ones.

### 6.2 What Is a Cost Function?

While "loss" often refers to the error on a *single* data point, the **cost function aggregates the difference (error) across the entire training dataset**. To measure a model's overall accuracy, you compare its predicted results against the actual values across all examples — the greater the discrepancy, the higher the resulting cost/error metric.

### 6.3 Why We Need a Cost Function

The cost function is essential for implementing **gradient descent** — the optimization procedure that adjusts model parameters to make predictions better. The goal of training is always to **minimize** the cost function as much as possible by tuning the model's parameters (weights and biases).

In linear regression, MSE is commonly used as both the "loss function" (per example) and "cost function" (aggregated). If we substitute the linear regression prediction `y_pred = m·x + c` into MSE:

```
Cost (MSE) = (1/n) · Σ (i=0 to n) (y_i − (m·xi + c))²
```

Here, `y_i` represents the ground-truth values, and `(m·xi + c)` represents the predicted/estimated values from the line. **Gradient descent** optimizes linear regression by iteratively adjusting the parameters `m` (slope) and `c` (y-intercept) to find the best-fit line — since an exhaustive search over every possible combination of `m` and `c` would be computationally impractical.

---

## 7. Backpropagation in the Perceptron

### 7.1 How Networks Learn

- The network **learns from input data/training examples** in order to generalize and acquire useful knowledge (rather than merely memorizing training examples).
- By adjusting weights and biases, the network aims to find a line, plane, or hyperplane that accurately separates different classes (for classification) or fits the data (for regression).
- Through this training process, the network **configures itself** to effectively solve the problem at hand.

### 7.2 The Backpropagation Algorithm (High-Level Steps)

1. **Initialize** the weights and the threshold (typically with small random values).
2. Let `x` be the input and `y` be the desired/target output.
3. **Provide the input** and calculate the actual output (this is the forward pass).
4. **Update the weights** based on the error between actual output and target output.
5. **Repeat** the initial steps, iterating continuously (across many passes, indexed by `n`) until a satisfactory output is obtained.

**Weight update rule:**

```
wi(t + 1) = wi(t) + η · (d − y) · x
```

Where:
- `wi(t)` — the weight at the current iteration/time step
- `η` (eta) — the learning rate
- `d` — the desired (target) output
- `y` — the actual output produced by the network
- `x` — the input

### 7.3 The Error Landscape

If we plot the **Sum of Squared Errors (SSE)** against different weight values, we get an "error landscape" — typically a curved surface with a minimum point somewhere.

```
SSE = Σ (ti − zi)²
```

Where `ti` are the target values and `zi` are the predicted values for a dataset. The whole point of training is to **minimize this SSE** — to find the weight values that sit at (or near) the lowest point of this error landscape.

### 7.4 The Concept of Backpropagation

Once a model computes the sum of weighted inputs and passes it through the activation function, it produces the final output (0 or 1 for a perceptron). This output is compared against the ground-truth value, and an **error** is computed:

| Prediction | Actual | Error |
|---|---|---|
| 1 | 1 | 0 |
| 1 | 0 | 1 |

To **minimize the error**, the neural network traverses backward through the network to adjust ("correct") the weights of the input neurons — this is the core concept of **backpropagation**. After the update, `w1` and `w2` have different (hopefully better) values. New predictions are made with the updated weights and compared again to the ground truth; this cycle continues until the error can't be reduced any further.

**Weight update formula (perceptron style):**

```
w1 = w1 + η · error · x1
w2 = w2 + η · error · x2
```

Where:
- `η` (eta) — the learning rate, typically ranging from 0 to 1
- `error` — the difference between the desired output and the actual output
- `w1, w2` — the weight parameters being updated
- `x1, x2` — the input variables

Backpropagation is more computationally expensive than simpler update rules, but it is far more effective at minimizing error and improving the accuracy of the network's output — which is why it remains the foundation of how virtually all modern neural networks are trained.

---

## 8. Worked Backpropagation Example

This worked numeric example walks through one complete forward pass and backward pass on a small feedforward network with 2 inputs, 2 hidden neurons, and 2 output neurons.

### 8.1 The Network Setup

**Given:**
- **Input layer:** two input neurons `i1 = 0.05`, `i2 = 0.10`.
- **Hidden layer:** two hidden neurons `h1`, `h2`, with bias `b1 = 0.35`. Weights from input to hidden layer: `w1 = 0.15`, `w2 = 0.20` (from `i1` to `h1` and `h2` respectively... actually connecting `i1`→`h1` uses `w1`, `i1`→`h2` uses `w2`), and `w3 = 0.25`, `w4 = 0.30` (connecting `i2` to `h1` and `h2`).
- **Output layer:** two output neurons `o1`, `o2`, with bias `b2 = 0.60`. Weights from hidden to output layer: `w5 = 0.40`, `w6 = 0.45` (connecting `h1` to `o1` and `o2`), and `w7 = 0.50`, `w8 = 0.55` (connecting `h2` to `o1` and `o2`).
- **Target outputs:** `o1 = 0.01`, `o2 = 0.99`.

The activation function used throughout this example is the **sigmoid/logistic function**: `f(x) = 1 / (1 + e^-x)`.

### 8.2 Forward Pass

**Step 1 — Net input to hidden neuron h1:**

```
net_h1 = w1·i1 + w3·i2 + b1·1
net_h1 = 0.15 × 0.05 + 0.25 × 0.10 + 0.35 × 1 = 0.3775
```

**Step 2 — Squash with the logistic (sigmoid) function to get the output of h1** (and, by the same process, h2):

```
out_h1 = 1 / (1 + e^-0.3775) = 0.593269992
out_h2 = 0.596884378   (rounded in the slides as 0.59869)
```

**Step 3 — Repeat for the output layer**, using the hidden-layer outputs as inputs:

```
net_o1 = w5·out_h1 + w7·out_h2 + b2·1
net_o1 = 0.40 × 0.593269992 + 0.45 × 0.596884378 + 0.60 × 1 = 1.105905967
out_o1 = 1 / (1 + e^-net_o1) = 0.7571

out_o2 = 0.7679   (computed the same way with w6, w8)
```

At this point, the forward pass gives predicted outputs `out_o1 = 0.7571` and `out_o2 = 0.7679` — but the *targets* were `0.01` and `0.99` respectively, so the network is currently very wrong. That's expected before any training.

### 8.3 Calculating Total Error

Using the **squared error** function for each output neuron, then summing:

```
E_total = Σ ½ (target − output)²

E_o1 = ½ (target_o1 − out_o1)² = ½ (0.01 − 0.7571)² = 0.2791
E_o2 = 0.0247

E_total = E_o1 + E_o2 = 0.2791 + 0.0247 = 0.3038
```

### 8.4 Backward Pass — Updating an Output-Layer Weight (w5)

The goal of the backward pass is to figure out **how much each weight contributed to the total error**, so it can be nudged in the direction that reduces that error. For `w5`, using the **chain rule**:

```
∂E_total/∂w5 = (∂E_total/∂out_o1) × (∂out_o1/∂net_o1) × (∂net_o1/∂w5)
```

Each factor is computed in turn:

1. **How much does total error change with respect to out_o1?**
```
∂E_total/∂out_o1 = −(target_o1 − out_o1) = −(0.01 − 0.7571) = 0.7471
```
(Note: `−(target − out)` is sometimes written equivalently as `out − target`.)

2. **How much does out_o1 change with respect to net_o1?** (derivative of the sigmoid function is `out·(1−out)`)
```
∂out_o1/∂net_o1 = out_o1 × (1 − out_o1) = 0.7571 × (1 − 0.7571) = 0.1839
```

3. **How much does net_o1 change with respect to w5?** (net_o1 is linear in w5, so this is just the coefficient of w5, i.e., out_h1)
```
∂net_o1/∂w5 = out_h1 = 0.5933
```

**Putting it all together:**

```
∂E_total/∂w5 = 0.7471 × 0.1839 × 0.5933 = 0.0815
```

**Updating the weight** (subtracting the gradient, scaled by the learning rate `η`, to move *downhill* on the error landscape):

```
w5_new = w5 − η × ∂E_total/∂w5 = 0.40 − 0.5 × 0.0815 = 0.35925
```

Following the identical process for the other output-layer weights:

```
w6_new = 0.4617
w7_new = 0.51183
w8_new = 0.56183
```

### 8.5 Backward Pass — Updating a Hidden-Layer Weight (w1)

Updating hidden-layer weights is slightly more involved because a hidden neuron's output (e.g., `out_h1`) influences the error through **both** output neurons (`o1` and `o2`), so its gradient must account for both downstream paths:

```
∂E_total/∂w1 = (∂E_total/∂out_h1) × (∂out_h1/∂net_h1) × (∂net_h1/∂w1)
```

Since `out_h1` affects both `out_o1` and `out_o2`:

```
∂E_total/∂out_h1 = ∂E_o1/∂out_h1 + ∂E_o2/∂out_h1
```

Where each term uses the weight connecting that hidden neuron to that output neuron (e.g., `∂E_o1/∂net_o1 × ∂net_o1/∂out_h1`, and `∂net_o1/∂out_h1 = w5`). Plugging in numbers:

```
∂E_o1/∂out_h1 = 0.138498562 × 0.40 = 0.055399425
∂E_o2/∂out_h1 = −0.019049119

∂E_total/∂out_h1 = 0.055399425 + (−0.019049119) = 0.036350306
```

Then, continuing the chain rule down to `w1`:

```
∂out_h1/∂net_h1 = out_h1 × (1 − out_h1) = 0.59326999 × (1 − 0.59326999) = 0.241300709
∂net_h1/∂w1 = i1 = 0.05

∂E_total/∂w1 = 0.036350306 × 0.241300709 × 0.05 = 0.000438568
```

**Updating w1:**

```
w1_new = w1 − η × ∂E_total/∂w1 = 0.15 − 0.5 × 0.000438568 = 0.14978071
```

By the same process:

```
w2_new = 0.19956143
w3_new = 0.24975114
w4_new = 0.29950229
```

**Key takeaway from the worked example:** notice how small the hidden-layer gradient (`0.000438568`) is compared to the output-layer gradient (`0.0815`) — the hidden-layer weight barely moved. This is a first-hand illustration of why gradients tend to shrink as they propagate backward through more layers, setting up the vanishing gradient problem discussed next. After many repeated forward/backward passes like this one, the network's total error steadily decreases and its predictions converge toward the targets (0.01 and 0.99).

---

## 9. Vanishing and Exploding Gradients

### 9.1 Vanishing Gradient

The **vanishing gradient problem** occurs during the training of deep neural networks, particularly those using gradient-based learning and backpropagation. As the error gradient is propagated backward through many layers, it is repeatedly multiplied by small derivative terms (such as the sigmoid derivative, which is at most 0.25). Across many layers, these small numbers compound and the gradient shrinks toward zero.

If gradients become very small (close to zero) by the time they reach the earlier layers, they effectively **prevent the weights in those layers from changing** in any meaningful way — meaning the network stops learning, or learns extremely slowly, in its earliest layers. Visually, the slope of the error curve decreases gradually to a very small value, making training difficult.

### 9.2 Exploding Gradient

Conversely, the **exploding gradient problem** occurs when the gradients of the network's parameters become too large. This can lead to very large swings in the weight values on each update, resulting in an unstable network.

During training, this often causes the model to **fail to converge** — the weights diverge (grow without bound) and the cost function (the loss/error metric) can become infinitely large (or `NaN`) rather than settling toward a minimum. Visually, the slope of the error curve grows exponentially rather than smoothly decreasing.

> Together, vanishing and exploding gradients are the classic obstacles to training very deep networks with plain gradient descent + sigmoid-style activations — this is part of why ReLU-family activations, careful weight initialization, batch normalization, and gradient clipping became standard tools in modern deep learning (covered in later lessons).

---

## 10. Gradient Descent

### 10.1 What Is Gradient Descent?

**Gradient descent** is an optimization algorithm used to **iteratively minimize a loss function**. It works by repeatedly adjusting the model's parameters in the direction that reduces the loss function's value the most (i.e., opposite to the direction of the gradient). Depending on the shape of the loss function and the starting point, gradient descent can end up at different minimum points (this matters especially for non-convex loss surfaces, common in deep networks).

Recall the linear regression setup: a linear regression model finds the equation of a straight line used to estimate the output:

```
y = m·x + c
```

Where:
- `y` — the target/dependent variable
- `x` — the input variable
- `c` — the intercept
- `m` — the slope of the line

> Note the conceptual distinction: linear regression focuses on finding the **best-fit line** for a regression task, while a simple perceptron aims to **classify** data into different classes. Both, however, are trained by minimizing some notion of error via gradient descent.

### 10.2 Working of Gradient Descent

There are (in the linear regression case) two parameters, `m` and `c`, that need to be optimized to find the best possible solution. If you plot the cost function (e.g., MSE) as a function of `m` and `c`, the resulting surface typically forms a **bowl shape**. The bottom of that bowl is the minimum value of the cost function — and the `m`, `c` values at that point are the optimal parameters.

### 10.3 Deriving a Gradient Descent (or Ascent) Algorithm

The algorithm iteratively updates weights to minimize (or, for gradient ascent, maximize) the overall error/objective function:

- It considers the **local gradient** at the current point, which indicates the direction of the largest rate of change.
- Weights are updated by taking a step **proportional to the gradient** (scaled by the learning rate).
- This mechanism accelerates convergence toward the optimum compared to random or exhaustive search.

### 10.4 Gradient Ascent — Conceptual Walkthrough

Gradient *ascent* is the mirror image of gradient descent: instead of minimizing a function, it maximizes it. The slides describe it as an iterative process:

1. **Step 1 — Initialize:** select random values for the model's parameters as a starting point for optimization.
2. **Step 2 — Take a step:** move in the direction of the **steepest ascent**, maximizing the objective function, to iteratively approach the optimal solution.
3. **Step 3 — Repeat:** repeat steps 1–2 until a stopping criterion is met, enabling continuous parameter refinement toward an optimal solution.

**Observations about the process:**

- The algorithm **stops iterating** if the next step would reduce the objective function, or once a termination condition is met — signaling it has reached a satisfactory (or optimal) solution.
- As optimization proceeds, the process typically **reduces the step size**, taking smaller and more precise steps to improve convergence and accuracy near the optimum.
- The overall aim is to **converge to a (local) maximum** by iteratively updating parameters and adjusting step size.

**Impacts on the neural network:** in gradient ascent, the Y-axis represents the function value, and the sign of the gradient tells you which way to move the weights:

- If the gradient is **positive**, the weights are **decreased**.
- If the gradient is **negative**, the weights are **increased**.
- Unlike gradient descent, the objective of gradient ascent is to **maximize**, not minimize, a function.

### 10.5 The Learning Rate

The **learning rate** (`η`) controls the size of the changes made to weights and biases at each update step, in order to minimize errors. It essentially controls *how sensitively* the error responds when weights/biases are changed by one unit — i.e., how big a "step" the optimizer takes at each iteration.

> **Rule of thumb:** a learning rate of **0.01** is generally considered a safe starting point. Too high a learning rate can cause training to overshoot the minimum (or even diverge, contributing to exploding gradients); too low a learning rate makes training painfully slow (and can get stuck in shallow local minima).

---

## 11. Limitations of a Perceptron

Although the perceptron is a simple and efficient supervised learning algorithm, it has several notable limitations:

### 11.1 Binary Output Only

The output of a perceptron takes only one of two values — 0 or 1. This makes it inherently unsuitable for regression tasks or for problems requiring a continuous or multi-valued output without further extension (e.g., stacking layers, changing the output activation, or using it purely as a classification building block).

### 11.2 Requires Linearly Separable Data

A perceptron works **only** with data that is linearly separable. Consider two-dimensional data made of circles and crosses arranged such that no single straight line can separate them — a perceptron simply cannot solve this. This is exactly the situation illustrated earlier by the XOR problem.

**Linearly separable data**, by contrast, can be split perfectly by a hyperplane:

```
Positive examples:  dot(x, w) + b > 0
Negative examples:  dot(x, w) + b < 0
Hyperplane:          H = { x : dot(x, w) + b = 0 }
```

Here, the hyperplane `H` is perpendicular to the weight vector `w`, and the weight vector defines the orientation of that separating hyperplane.

### 11.3 Convergence Issues

The perceptron learning algorithm struggles with data that is **not** linearly separable: because no set of weights can ever produce a perfect boundary, the algorithm fails to converge and instead enters an endless cycle of weight updates, forever trying (and failing) to fix misclassified points.

Setting a maximum number of training iterations can prevent this infinite loop from running forever, but it is only a workaround — it does not fix the underlying problem, which is the perceptron's fundamental inability to correctly classify data that isn't linearly separable. (The real fix, as covered earlier, is to move to a **multilayer perceptron**, which combines multiple linear boundaries and nonlinear activations to represent much more complex decision surfaces.)

---

## 12. Key Takeaways

- A **perceptron** is a type of artificial neuron used for **binary classification** in machine learning.
- **Forward propagation** generates an output in a perceptron model by passing inputs through weights, summing them (plus bias), and applying an activation function.
- **Backpropagation** involves adjusting the weights of the inputs in order to minimize the error in the perceptron model, by propagating the error gradient backward through the network.
- **Gradient descent** is a technique used to minimize the cost function in a neural network by iteratively updating parameters in the direction that reduces error.
- **Perceptrons have limitations** — they can only handle linearly separable data, which is why multilayer architectures and nonlinear activation functions became necessary for modeling real-world, non-linear problems.

---

## 📝 Practice Questions

### Multiple Choice

**Q1.** What is the primary function of weights in a perceptron?
- **A.** To store the output of the neuron
- **B.** To determine the importance/influence of each input on the output
- **C.** To define the activation function used
- **D.** To count the number of layers in the network

**Q2.** What is the role of the bias term `b` in a perceptron?
- **A.** It scales the learning rate during training
- **B.** It shifts the decision boundary independently of the input values
- **C.** It determines the number of hidden layers
- **D.** It normalizes the output between 0 and 1

**Q3.** Which of the following best describes an activation function?
- **A.** A process used to initialize the weights of a network
- **B.** An equation that determines the output of a neuron/neural network model given its weighted input
- **C.** A method for splitting training and test data
- **D.** A type of supervised learning algorithm

**Q4.** Why can't a single-layer perceptron solve the XOR problem?
- **A.** XOR requires more than two inputs
- **B.** XOR data is not linearly separable, and a perceptron can only learn a linear decision boundary
- **C.** The perceptron's activation function cannot output negative numbers
- **D.** XOR requires a bias term, which perceptrons do not support

**Q5.** Which activation function is most associated with the vanishing gradient problem in deep networks?
- **A.** ReLU
- **B.** Softmax
- **C.** Sigmoid
- **D.** Step function

**Q6.** In the ReLU activation function `f(x) = max(0, x)`, what is the output when the input is -3?
- **A.** -3
- **B.** 0
- **C.** 3
- **D.** Undefined

**Q7.** Which activation function is most appropriate for the output layer of a multiclass classification problem (e.g., classifying an image into one of 10 categories)?
- **A.** Step function
- **B.** Sigmoid function
- **C.** Softmax function
- **D.** Linear function

**Q8.** What does the cost function measure in a neural network?
- **A.** The number of layers required to solve a problem
- **B.** The aggregate error/discrepancy between predicted outputs and actual (ground-truth) values across the training set
- **C.** The learning rate used during training
- **D.** The total number of weights in the network

**Q9.** During backpropagation, in which direction does the error signal travel through the network?
- **A.** From the input layer to the output layer only
- **B.** From the output layer backward toward the input layer
- **C.** Simultaneously in both directions with no defined order
- **D.** Only within a single layer, never between layers

**Q10.** What happens to a neural network's training when the exploding gradient problem occurs?
- **A.** The network trains faster than expected and converges early
- **B.** Weight updates become excessively large, causing instability and preventing convergence
- **C.** All weights are set to zero, halting training
- **D.** The activation function switches automatically to ReLU

**Q11.** Which of the following is a fundamental limitation of the perceptron model?
- **A.** It cannot represent numeric inputs
- **B.** It can only work correctly on data that is linearly separable
- **C.** It cannot compute a weighted sum of inputs
- **D.** It requires more than one output neuron

**Q12.** What is the purpose of the learning rate (`η`) in gradient-based training?
- **A.** It defines the number of neurons in the hidden layer
- **B.** It controls the size of the parameter update at each training step
- **C.** It determines which activation function is used
- **D.** It sets the number of training examples used per batch

**Q13.** Which type of neural network is best suited for handling sequential data such as time series or natural language, because it maintains a memory of previous inputs?
- **A.** Convolutional Neural Network (CNN)
- **B.** Perceptron
- **C.** Recurrent Neural Network (RNN)
- **D.** Feedforward Neural Network without hidden layers

### Short Answer

**Q14.** Write the general equation for the output of a single artificial neuron in terms of weights `w`, input `x`, bias `b`, and activation function `f`, and briefly explain each term.

**Q15.** Explain, in your own words, why a nonlinear activation function is necessary in a multilayer network — what would happen if every neuron used a purely linear activation function instead?

**Q16.** Describe the two phases involved in training a perceptron model, and briefly explain what happens in each phase.

**Q17.** Given a perceptron with inputs `x1 = 0.5`, `x2 = 0.8`, weights `w1 = 0.4`, `w2 = -0.2`, and bias `b = 0.1`, calculate the weighted sum `w1·x1 + w2·x2 + b`, and state whether the perceptron would output 0 or 1 (using the standard step-function rule: output 1 if the sum is greater than 0, else 0).

**Q18.** What is the difference between "loss" and "cost" as used in the context of training a neural network?

### Answers

**A1.** **B** — Weights are real-valued numbers associated with each input feature that state how important that feature is in determining the final output; larger-magnitude weights exert more influence on the neuron's decision.

**A2.** **B** — The bias shifts the activation function (decision boundary) left or right, similar to a y-intercept, without depending on the values of the inputs themselves — this lets the neuron fire (or not) even when inputs are zero.

**A3.** **B** — An activation function is a mathematical equation applied to the weighted sum of inputs that determines the final output of a neuron or network, and it introduces the non-linearity needed for the network to learn complex patterns.

**A4.** **B** — XOR's four input/output combinations cannot be separated by any single straight line (they are not linearly separable), and a single-layer perceptron can only represent linear decision boundaries; solving XOR requires a multilayer perceptron.

**A5.** **C** — The sigmoid function's derivative is at most 0.25 and shrinks toward the extremes; when many such small derivatives are multiplied together during backpropagation through many layers, the resulting gradient shrinks toward zero (vanishing gradient), unlike ReLU which has a constant gradient of 1 for positive inputs.

**A6.** **B** — ReLU is defined as `f(x) = max(0, x)`. For a negative input like -3, the function outputs 0, since any input at or below zero is clipped to zero.

**A7.** **C** — The softmax function normalizes the outputs across all classes so they fall between 0 and 1 and sum to 1, making it ideal for representing a probability distribution over multiple mutually exclusive classes.

**A8.** **B** — The cost function aggregates the error between the model's predicted outputs and the actual/ground-truth values across the entire training dataset, giving an overall measure of model accuracy that training seeks to minimize.

**A9.** **B** — Backpropagation computes the gradient of the error at the output layer first, then propagates that error signal backward through the hidden layers toward the input layer, updating weights along the way using the chain rule.

**A10.** **B** — In the exploding gradient problem, gradients become excessively large, causing correspondingly large weight updates; this destabilizes training and often prevents the model from converging (the loss may grow unbounded or become NaN).

**A11.** **B** — A perceptron can only learn a linear decision boundary (a straight line or hyperplane), so it can only correctly classify data whose classes are linearly separable; it fails on problems like XOR that require nonlinear boundaries.

**A12.** **B** — The learning rate scales how large a step is taken in the direction that reduces (or, for ascent, increases) the objective function during each parameter update; too large a value risks instability/divergence, too small a value slows training.

**A13.** **C** — RNNs maintain a "state" that recurs into the network with each new input, giving them a form of memory of previous inputs in a sequence — a capability plain feedforward networks and perceptrons lack.

**A14.** `Output = f(w · x + b)`, where `x` is the vector of inputs, `w` is the vector (or matrix, for multiple neurons) of weights indicating each input's importance, `b` is the bias that shifts the decision boundary, and `f` is the activation function that introduces non-linearity and produces the final bounded output.

**A15.** Without a nonlinear activation function, stacking multiple linear layers is mathematically equivalent to a single linear layer (since a composition of linear functions is itself linear) — so a "deep" network with only linear activations would have no more representational power than a single-layer perceptron and would only ever be able to learn linear decision boundaries, regardless of how many layers it had.

**A16.** The two phases are: (1) **Forward propagation (forward pass)** — the input data is passed through the network's weights and activation functions, layer by layer, to produce a predicted output; and (2) **Backward propagation (backprop)** — the error between the predicted and target output is computed and propagated backward through the network to update the weights (typically via gradient descent) so that future predictions improve.

**A17.** Weighted sum = `(0.4 × 0.5) + (-0.2 × 0.8) + 0.1 = 0.20 − 0.16 + 0.10 = 0.14`. Since `0.14 > 0`, the perceptron outputs **1**.

**A18.** "Loss" typically refers to the error measured for a **single** training example (the discrepancy between one predicted value and its corresponding true value), whereas "cost" (or the cost function) refers to the **aggregated** error across the entire training dataset (e.g., the average loss over all examples) — though in casual usage the two terms are often used interchangeably.
