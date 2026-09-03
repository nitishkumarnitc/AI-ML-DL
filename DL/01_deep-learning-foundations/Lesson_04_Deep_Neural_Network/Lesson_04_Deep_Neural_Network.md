# Deep Neural Networks

*Deep Learning with Keras and TensorFlow — Lesson 04*

## 🎯 Learning Objectives

By the end of this lesson, you will be able to:

- Understand the architecture and functionality of a deep neural network (DNN).
- Evaluate different loss functions used in deep neural networks.
- Demonstrate the process of forward and backward propagation in deep neural networks.
- Interpret and calculate the effects of different types of regression losses, such as MAE and MSE, on the performance of neural network models.

---

## 💼 Business Scenario

A financial services company wants to improve its loan application process by building a better risk-assessment model. It plans to use a **deep neural network (DNN)** to analyze customer data — income, credit score, employment history, and other features — and estimate the likelihood that a loan applicant will default.

To make this work, the company needs to:

1. Construct a DNN and **normalize** the input data so the network can learn efficiently (features on wildly different scales, like income in the tens of thousands versus a credit score in the hundreds, can make training unstable).
2. Use a suitable **loss function** to measure how wrong the model's predictions are, and use that signal to adjust the network's internal weights.
3. Use a tool like **TensorFlow Playground** to visually experiment with network architecture and see how changes affect learning.

The end goal is a more accurate risk model that reduces defaults and leads to better-informed loan decisions. This scenario motivates everything covered in this lesson: what a DNN is, how it computes an answer (forward propagation), how it learns from its mistakes (backward propagation and loss functions), and how to keep it from memorizing noise instead of genuinely learning (regularization).

---

## 1. Introduction to Deep Neural Networks (DNN)

### 1.1 What Is a Deep Neural Network?

A **Deep Neural Network (DNN)** is a type of artificial neural network that has one or more **hidden layers** stacked between the input layer and the output layer. The word "deep" refers specifically to this stacking of multiple hidden layers — the more layers a network has, the "deeper" it is considered to be.

Compared to a traditional, shallow neural network (which might have zero or one hidden layer), DNNs generally:

- Offer **higher accuracy** on complex tasks.
- Are better able to **emulate the layered, hierarchical decision-making** that the human brain performs — for example, recognizing edges first, then shapes, then objects, then scenes.

**Why depth matters:** The depth (number of hidden layers) is the key structural factor that separates a DNN from a traditional neural network. Each additional hidden layer lets the network learn a new, more abstract representation of the data built on top of the representation learned by the previous layer. This is what allows DNNs to outperform shallow networks on tasks like image recognition, speech recognition, and natural language processing, where the relationship between raw input and the desired output is highly non-linear and hierarchical.

A DNN is generally described as having three types of layers:

- **Input layer** — receives the raw features (e.g., pixel values, or income/credit score/employment history in our loan example).
- **Hidden layers** — one or more layers that transform the input into increasingly abstract, useful representations.
- **Output layer** — produces the final prediction (e.g., probability of loan default).

### 1.2 Depth and Width

DNNs are best understood as a powerful category of machine learning models built by stacking layers of neurons both:

- **Along the depth** — the number of layers (Layer 1, Layer 2, …) stacked between input and output.
- **Along the width** — the number of neurons (units) within each individual layer.

A network can be made more powerful either by adding more layers (going deeper) or by adding more neurons per layer (going wider). In practice, depth tends to be more parameter-efficient at capturing hierarchical structure, which is why "deep" learning became the dominant paradigm rather than simply building very wide, shallow networks.

### 1.3 Worked Example: Dog Breed Recognition

Imagine a DNN trained to recognize dog breeds from photographs. Given an input image, the network doesn't output a single definitive label directly — instead, it computes a **probability** for each possible breed it was trained on. For example, it might output something like:

| Breed | Predicted probability |
|---|---|
| Breed A | 0.1 |
| Breed B | 0.6 |
| Breed C | 0.3 |

The network then typically selects the breed with the **highest probability** (Breed B, at 0.6) as its predicted answer. This "probability distribution over classes" pattern is central to how classification neural networks operate — you'll see it again below when we discuss cross-entropy loss.

### 1.4 Worked Example: Audio Classification

The same principle extends beyond images. If a computer is given raw audio — say, the sound of a trumpet — it has no built-in understanding of "trumpet" without a trained model. A DNN can listen to (i.e., process a numerical representation of) that sound and sort it into categories such as "trumpet," "violin," "drum," and so on. This categorization happens through the combined processing of the network's many hidden layers, each of which extracts increasingly abstract audio features (e.g., low-level frequency patterns first, then timbre, then instrument identity).

### 1.5 Benefits and Real-World Applications of DNNs

DNNs are among the most efficient and accurate machine learning approaches **when given large amounts of data** — their advantage grows as more training examples become available, unlike some traditional algorithms that plateau quickly. This data-hungry but highly accurate nature has accelerated the development of technologies such as:

1. **Self-driving cars** — perception systems that identify lanes, pedestrians, and other vehicles.
2. **Image and voice recognition software** — e.g., unlocking a phone with your face, or transcribing speech.
3. **Chatbots** — understanding and generating natural language responses.
4. **Voice assistants** — Siri, Alexa, Google Assistant, and similar systems.
5. **Online translation software** — translating text or speech between languages.

---

## 2. Loss Functions in DNN and Their Types

### 2.1 What Is a Loss Function?

A **loss function** measures the discrepancy (difference) between what the model predicted and what the correct answer actually was. This measurement is what allows the network to learn: without a numeric sense of "how wrong am I," there would be no signal to guide weight updates.

During training, the model being developed must be **continually assessed for potential errors** as part of the optimization process — every time the network makes a prediction on training data, the loss function quantifies the mistake, and that quantity feeds directly into the weight-update process (backpropagation, covered later).

### 2.2 Worked Example: A Simple Error Calculation

Suppose we're building a binary classifier for images of horses and humans, and we assign the label 0 to "horse" and 1 to "human." Every output the model produces undergoes this same comparison process, and the resulting error is collected across all outputs during each learning iteration.

If the model is shown an image of a horse (true label = 0) and the model's output is 0.25, then the error is simply the difference between prediction and label:

```
error = 0.25 − 0 = 0.25
```

This simple subtraction is the conceptual seed of a loss function — real loss functions build on this idea but combine, scale, and shape these individual errors in different mathematically useful ways (as we'll see with MAE, MSE, cross-entropy, and hinge loss).

### 2.3 Two Major Categories of Loss Functions

Loss functions used in deep learning fall into two broad categories, depending on what kind of value the network is trying to predict:

```
Loss Function
    ├── Regression Loss        (predicting a continuous number)
    └── Classification Loss    (predicting a category/class)
```

- **Regression loss** is used when the network's output is a continuous value — for example, predicting an employee's salary, a house price, or a probability of default expressed as a continuous risk score.
- **Classification loss** is used when the network's output is a discrete category — for example, "horse" vs. "human," or which of several phone brands an image most resembles.

---

## 3. Regression Loss

### 3.1 Overview

In **neural network regression**, the goal is to predict continuous values from input features, and a suitable loss function is used to measure how far off those predictions are. The classic example given is predicting an employee's salary from features like years of experience, education, and role — the output is a single real number, not a category.

The two main types of regression loss covered in this lesson are:

- **Mean Absolute Error (MAE)**
- **Mean Squared Error (MSE)**

### 3.2 Mean Absolute Error (MAE)

**MAE** measures the average absolute difference between the predicted and actual values across all observations in regression tasks.

**Formula:**

```
MAE = (1/n) * Σ |y − ŷ|
```

Where:
- `y` = the actual target value
- `ŷ` ("y-hat") = the predicted value
- `y − ŷ` = the absolute difference between actual and predicted values for one observation
- `n` = the total number of observations

**Worked example:**

| Y (Actual) | Y′ (Predicted) | \|Y − Y′\| |
|---|---|---|
| 10.2 | 9.4 | 0.8 |
| 7.1 | 6.9 | 0.2 |
| 17.2 | 18.4 | 1.2 |
| 9.5 | 11.3 | 1.8 |
| 11.5 | 11.1 | 0.4 |
| **Sum** | | **4.4** |

```
MAE = 4.4 / 5 = 0.88
```

MAE is used as a metric for the **average magnitude of error** between predicted and actual values — it treats every unit of error the same regardless of direction (over- or under-prediction) or size, because it simply takes the absolute value.

**Python implementation:**

```python
# Calculate the mean absolute error
import numpy as np

def mean_absolute_error(actual, predicted):
    absolute_errors = np.abs(actual - predicted)
    mean_absolute_error = np.mean(absolute_errors)
    return mean_absolute_error
```

This function computes the absolute error for every prediction, then averages them — a direct implementation of the MAE formula above.

### 3.3 Mean Squared Error (MSE)

**MSE** measures the average **squared** difference between predicted and true values in regression tasks. Because errors are squared before averaging, MSE behaves quite differently from MAE, especially with large errors or outliers (see comparison below). When multiple samples are processed at once, MSE simply takes the mean of the squared errors across all of them, and it is one of the most standard, widely implemented loss functions in regression.

**Formula:**

```
MSE = (1/n) * Σ (y − ŷ)²
```

Where:
- `(y − ŷ)²` = the squared difference between actual and predicted values
- `y` = actual target value, `ŷ` = predicted value

**Worked example:**

| Y (Actual) | Y′ (Predicted) | \|Y − Y′\|² |
|---|---|---|
| 10.2 | 9.4 | 0.64 |
| 7.1 | 6.9 | 0.04 |
| 17.2 | 18.4 | 1.44 |
| 9.5 | 11.3 | 3.24 |
| 11.5 | 11.1 | 0.16 |
| **Sum** | | **5.52** |

```
MSE = 5.52 / 5 = 1.104
```

**Python implementation:**

```python
# Calculate the mean squared error
import numpy as np

def mean_squared_error(actual, predicted):
    square_errors = (actual - predicted) ** 2
    mean_square_error = np.mean(square_errors)
    return mean_square_error
```

### 3.4 MSE vs. MAE: Side-by-Side Comparison

Because MSE squares every error term before averaging, it **penalizes larger errors much more heavily** than MAE does. Using the same five data points for both metrics:

| Y | Y′ | \|Y−Y′\| | \|Y−Y′\|² |
|---|---|---|---|
| 10.2 | 9.4 | 0.8 | 0.64 |
| 7.1 | 6.9 | 0.2 | 0.04 |
| 17.2 | 18.4 | 1.2 | 1.44 |
| 9.5 | 11.3 | 1.8 | 3.24 |
| 11.5 | 11.1 | 0.4 | 0.16 |
| **Sum** | | **4.4** | **5.52** |

```
MAE = 4.4 / 5 = 0.88
MSE = 5.52 / 5 = 1.104
```

At this point, MSE and MAE tell a broadly similar story. But watch what happens when one data point becomes an **outlier**.

### 3.5 The Effect of Outliers on MSE vs. MAE

Suppose one actual value is far from its prediction — for example, the third-to-last row's actual value jumps from 9.5 to **31.5** (predicted stays 11.3), producing a large error of 20.2:

| Y | Y′ | \|Y−Y′\| | \|Y−Y′\|² |
|---|---|---|---|
| 10.2 | 9.4 | 0.8 | 0.64 |
| 7.1 | 6.9 | 0.2 | 0.04 |
| 17.2 | 18.4 | 1.2 | 1.44 |
| 31.5 | 11.3 | 20.2 | 408.04 |
| 11.5 | 11.1 | 0.4 | 0.16 |
| **Sum** | | **22.8** | **410.32** |

```
MAE = 22.8 / 5 = 4.56
MSE = 410.32 / 5 = 82.064
```

Notice the dramatic difference: MAE increased modestly (from 0.88 to 4.56), but MSE **exploded** (from 1.104 to 82.064). This is because squaring a large error (20.2² = 408.04) makes it dominate the sum completely. This illustrates a crucial practical rule:

> **If your data contains outliers, prefer MAE** — it is more robust and won't let a few extreme points dominate the loss. **If your data is relatively clean (no significant outliers), MSE is often preferable** — it's smoother, differentiable everywhere, and tends to produce faster, more stable gradient-based optimization.

### 3.6 MSE in Backpropagation

**Formula (summation notation):**

```
MSE(W) = (1/N) * Σ_{i=1}^{N} (y − y′)²
```

MSE is very commonly used as the loss function that drives **backpropagation** (covered in detail later) because, empirically, minimizing squared differences between predicted and actual values tends to work well and produces mathematically convenient gradients (the derivative of a squared term is simple and well-behaved), which makes gradient-based training more stable.

---

## 4. Classification Problems: Binary vs. Multi-Class

Before covering classification losses, it's important to distinguish the two main types of classification tasks they're designed for.

### 4.1 Binary Classification

A **binary classification problem** is one where each example is placed into exactly one of **two classes** — conventionally labeled with the integer value **1** for one class and **0** for the other (e.g., "loan defaults" = 1, "loan does not default" = 0). The model in this setting assigns examples to one of the two predefined classes based on the likelihood of belonging to that class, rather than needing to predict probabilities across many possible classes.

### 4.2 Multi-Class Classification

A **multi-class classification problem** is one where an example can belong to one of **more than two classes**. The model is set up to predict the probability of the example belonging to *each* class, and the class with the highest predicted probability is usually chosen as the answer.

**Example:** Classifying images of fruits into categories such as apples, bananas, grapes, and oranges — each fruit type is a distinct class label, and the model outputs a probability for each of the four categories.

### 4.3 Types of Classification Loss

```
Classification Loss
    ├── Cross-Entropy Loss
    └── Hinge Loss
```

---

## 5. Cross-Entropy Loss

### 5.1 Concept and Intuition

**Cross-entropy** is a mathematical measure used to quantify the difference between two probability distributions: the distribution the model *predicted*, and the distribution that represents the *actual/true* label.

**Worked setup:** Consider a classification problem with three brands: Samsung, Apple, and LG. The model's output is a vector of probabilities:

```
Output = [P(Samsung), P(Apple), P(LG)]
```

The class with the highest predicted probability is chosen as the winner. The **actual** probability distribution for each true class is represented using **one-hot encoding** — a vector where the correct class gets probability 1 and all others get probability 0:

```
Samsung = [1, 0, 0]
Apple   = [0, 1, 0]
LG      = [0, 0, 1]
```

If the predicted probability distribution is far from this actual one-hot vector, the model needs to adjust its weights; cross-entropy is precisely the tool used to measure "how far" the predicted distribution is from the actual one, so that this discrepancy can be minimized during training.

**Visual intuition:** Given an input (say, a photo of an LG phone), the model produces a predicted probability distribution, e.g. `[0.1 (Samsung), 0.3 (Apple), 0.6 (LG)]`, while the actual/true distribution is `[0, 0, 1]`. Cross-entropy measures the "distance" between these two distributions — the larger the mismatch, the larger the loss.

### 5.2 Cross-Entropy: General Formula

For a model that outputs a predicted probability distribution over N classes for input data C:

```
P(C) = [y1′, y2′, y3′, ..., yN′]     (predicted distribution)
A(C) = [y1, y2, y3, ..., yN]         (actual/target distribution)

Cross-entropy(A, P) = −(y1·log(y1′) + y2·log(y2′) + y3·log(y3′) + ... + yN·log(yN′))
```

In words: multiply each true-class indicator by the log of the corresponding predicted probability, sum these products across all classes, and negate the result. Because the true distribution is one-hot, only the term for the correct class actually contributes (every other `y_i` is 0).

**Worked numeric example:** Suppose the true label is LG, so `A(LG) = [1, 0, 0]` (say ordered Samsung, Apple, LG isn't quite matching order in the text, but the arithmetic below follows the source exactly), and the predicted distribution is `P(LG) = [0.6, 0.3, 0.1]`:

```
Cross-entropy(A, P) = −(1·log(0.6) + 0·log(0.3) + 0·log(0.1)) ≈ 0.51
```

Only the "correct class" probability (0.6) matters here because it's multiplied by 1, while the other two terms are multiplied by 0 and vanish. Intuitively: the closer the predicted probability for the true class is to 1.0, the smaller `-log(p)` becomes (approaching 0 loss); the closer it is to 0, the larger (and eventually infinite) the loss becomes. This is exactly the "harshly punish confident wrong answers" behavior that makes cross-entropy so effective for classification.

### 5.3 Types of Cross-Entropy Loss

```
Cross-Entropy Loss
    ├── Categorical Cross-Entropy Loss   (multi-class, one-hot labels)
    └── Binary Cross-Entropy Loss        (two classes)
```

### 5.4 Categorical Cross-Entropy Loss

Categorical cross-entropy measures the **dissimilarity between predicted class probabilities and true class labels** in multi-class classification. The overall loss across a dataset is the average of the per-example cross-entropy values:

```
Categorical cross-entropy = (sum of cross-entropy for N data points) / N
```

**Worked example across 7 data points:**

| Data | Actual distribution | Predicted distribution | Cross-entropy |
|---|---|---|---|
| Samsung | [1,0,0] | [0.6,0.3,0.1] | −(1·log0.6 + 0 + 0) = 0.51 |
| Samsung | [1,0,0] | [0.9,0.1,0] | ≈ 0.1 |
| Apple | [0,1,0] | [0.2,0.7,0.1] | ≈ 0.35 |
| LG | [0,0,1] | [0.3,0.2,0.5] | ≈ 0.69 |
| Apple | [0,1,0] | [0.6,0.1,0.3] | ≈ 2.3 |
| Samsung | [1,0,0] | [0.5,0.2,0.3] | ≈ 0.69 |
| LG | [0,0,1] | [0.1,0.1,0.8] | ≈ 0.22 |

```
Loss = (0.51 + 0.1 + 0.35 + 0.69 + 2.3 + 0.69 + 0.22) / 7 = 4.76 / 7 ≈ 0.68 (rounded per-example sum 4.76)
```

Notice the second Apple example (predicted [0.6, 0.1, 0.3], true label Apple) has a *much* higher loss (2.3) than the first Samsung example (0.51) even though both have similarly "wrong-ish" predictions — this is because the model assigned only 0.1 probability to the *correct* class (Apple) in that row, and cross-entropy punishes low confidence in the correct answer sharply due to the `-log` term.

### 5.5 Binary Cross-Entropy Loss

When there are only two classes (and hence only one output neuron, since class-1 probability implies class-0 probability = 1 − p), binary cross-entropy assumes actual values of 0 or 1 for the negative and positive classes, respectively.

The per-example cross-entropy simplifies to two cases:

```
Cross-entropy(C) = −y · log(y′)          when y = 1
Cross-entropy(C) = −(1 − y) · log(1 − y′) when y = 0
```

The overall binary cross-entropy for the whole model is the mean of the per-example cross-entropy values:

```
Binary cross-entropy = (sum of cross-entropy for N data) / N
```

**Python implementation:**

```python
from math import log

# Calculate binary cross entropy
def binary_cross_entropy(actual, predicted):
    sum_score = 0.0
    for i in range(len(actual)):
        sum_score += actual[i] * log(1e-15 + predicted[i]) + \
                     (1 - actual[i]) * log(1e-15 + (1 - predicted[i]))
    mean_sum_score = 1.0 / len(actual) * sum_score
    return -mean_sum_score
```

Note the small constant `1e-15` added inside each `log()` call — this is a numerical-stability trick to avoid computing `log(0)`, which is undefined (negative infinity), in case a predicted probability is exactly 0 or 1.

### 5.6 Sparse Categorical Cross-Entropy Loss

**Sparse categorical cross-entropy** is used for multi-class classification tasks where each sample belongs to exactly one class, but — unlike categorical cross-entropy — the true labels are given as plain **integers** (e.g., class index 2) rather than **one-hot encoded vectors** (e.g., `[0, 0, 1, 0]`). This is purely a convenience/efficiency variant: mathematically it computes the same underlying quantity, just from a more memory-efficient label representation, which is especially useful when there are many classes.

**Formula:**

```
Loss = − (1/N) * Σ_{i=1}^{Output size} log(Pi)
```

Where:
- `N` is the number of samples/instances in the dataset.
- `Pi` is the predicted probability assigned to the *correct* class for the i-th sample.

### 5.7 Why Not Just Use MSE/MAE for Classification?

Using MSE or MAE as the loss function for a classification problem can be problematic and can lead to what's called an **overconfident wrong prediction** — the model can be very sure about an incorrect answer, especially during training. (The slides illustrate this with a lighthearted example: a model confidently telling a male patient he is "pregnant.")

Why this happens:

- MSE/MAE measure raw numeric distance, not probability calibration. A wrong classification might still produce a *numerically small* squared/absolute error (e.g., predicting 0.4 when the true label is 0 gives a small MSE contribution), which doesn't strongly push the model to reconsider.
- This can result in the model assigning **relatively small errors to wrong predictions**, causing it to develop high (mistaken) certainty in incorrect classifications.
- This overconfidence means the model can make mistakes while appearing very "sure" of itself, which is especially dangerous in decision-critical applications like the loan-default model from our business scenario.

**Mitigation:** Use loss functions purpose-built for classification, like **cross-entropy**, which directly optimizes for classification accuracy and proper probability distributions rather than raw numeric closeness.

---

## 6. Hinge Loss

### 6.1 Overview

**Hinge loss** is a loss function used to train classifiers — most famously **Support Vector Machines (SVMs)** — with a focus on **maximum-margin classification**. Rather than just asking "did we get the label right," hinge loss asks "did we get the label right *by a comfortable margin*?" It penalizes:

- Misclassified predictions (wrong answers), and
- Correctly classified predictions that are **too close to the decision boundary** (right, but not confidently so).

This encourages the classifier to find a decision boundary that separates classes with as wide a margin as possible, which tends to generalize better to unseen data.

### 6.2 Formula and Notation

Hinge loss is defined for binary classification where the true label `y` is either **+1** or **−1** (note: this is a different labeling convention from the 0/1 convention used in cross-entropy). For a single prediction:

```
Hinge loss = max(0, 1 − y · f(x))
```

Where:

- **`y`** — the true label of the data point, either +1 or −1.
- **`f(x)`** — the predicted score (decision function output) for input `x`. Unlike a probability, `f(x)` can be *any real number* — not bounded between 0 and 1.

**Interpreting f(x):**

- If the classifier is very confident the sample is positive, `f(x)` might be a large positive number (e.g., 2.5).
- If very confident it's negative, `f(x)` might be a large negative number (e.g., −3.0).
- If unsure, `f(x)` will be close to zero (e.g., 0.1).

### 6.3 The Three Hinge Loss Scenarios

**Scenario 1 — Correct and confident prediction:** occurs when `f(x) ≥ 1.0` (aligned with `y`).

*Example:* `y = 1`, and the "combined" quantity `y·f(x) = 1.2`. Then `1 − (f(x)·y) = 1 − 1.2 = −0.2`, and the loss is `max(0, −0.2) = 0`. **The loss is zero for all correct predictions, even ones that are "too correct"** (i.e., overshooting the margin doesn't help or hurt further) — this is one of hinge loss's defining properties.

**Scenario 2 — Incorrect prediction:** occurs when `f(x) < 0` while `y = 1` (i.e., the predicted sign is flipped relative to the true label).

*Example:* `y = 1`, `f(x) = −0.5`. Then loss `= max(0, 1 − (1 × −0.5)) = max(0, 1.5) = 1.5`. **Wrong predictions are penalized heavily** — the more confidently wrong, the larger the loss.

**Scenario 3 — Incorrect but close to correct:** occurs when `0.0 ≤ f(x) < 1.0`, i.e., the prediction is on the correct side of zero but still inside the margin.

*Example:* `y = 1`, `f(x) = 0.9`. Then loss `= max(0, 1 − 0.9) = max(0, 0.1) = 0.1`. **The prediction is "approaching correctness,"** reflected by a small but non-zero loss that still nudges the model to push its confidence further past the margin.

### 6.4 Properties of Hinge Loss

- **Max-margin:** Hinge loss actively encourages a large separating margin between classes, because it keeps penalizing correct-but-too-close-to-the-boundary predictions until they clear the margin (`y·f(x) ≥ 1`).
- **Non-differentiability:** The function is not differentiable exactly at the "kink" point where `y·f(x) = 1`. In practice this is handled using **sub-gradient methods**, which allow gradient-based optimization to proceed even where the true derivative doesn't exist.
- **Regularization:** Hinge loss is frequently paired with regularization terms (such as L2 regularization) to prevent overfitting and encourage simpler decision boundaries.
- **Sensitivity to outliers:** Because hinge loss penalizes large margin violations heavily (the penalty grows linearly and without bound), it can be quite sensitive to outliers in the training data.

### 6.5 Squared Hinge Loss

**Squared hinge loss** extends ordinary hinge loss (used in SVMs and elsewhere) by **squaring** the hinge term. This small change has meaningful consequences:

**Formula (conceptually):**

```
Squared hinge loss = [max(0, 1 − y · f(x))]²
```

Where `y` is the true label (+1 or −1) and `f(x)` is the predicted decision score, same as ordinary hinge loss.

**Properties of squared hinge loss:**

- **Smooth penalty:** Squaring the hinge term produces a smoother penalty curve for misclassifications, avoiding the sharp linear "corner" of ordinary hinge loss.
- **Stronger penalty for misclassifications:** Because the error term is squared, larger violations are penalized *more severely* than under standard hinge loss.
- **Enhanced gradient descent:** The squared formulation improves the gradient's mathematical properties (it's smoother and better behaved near the margin), which can aid **stable and efficient convergence** during training.

---

## 7. Forward Propagation in DNN

### 7.1 What Is Forward Propagation?

**Forward propagation** is the process of feeding input data through a neural network, layer by layer, to produce an output/prediction. As data moves through each hidden layer, that layer applies weights, biases, and an **activation function** to transform the data before passing it along to the next layer.

Crucially, this flow is strictly **forward** — from input layer, through each hidden layer in sequence, to the output layer — with no loops or backward cycles during this phase. This directional structure is what "prevents non-output states": every input deterministically flows to exactly one output, layer by layer, in one direction.

```
Network inputs → Input layer → Hidden layer(s) → Output layer → Network output
                        \_______________________/
                            Forward propagation
```

This process repeats for every layer in the network in turn, until the signal originating from the input reaches the output layer and produces the final prediction.

### 7.2 The Mathematical Intuition Behind Forward Propagation

To build intuition mathematically, the lesson uses the simplest possible analogy: a straight line. If `x` is the input and `y` is the output, a very simple model of the relationship between them is a linear one, where `y` is `x` multiplied by some factor and shifted by an offset:

```
y = mx + b
```

Where:
- **`y`** — the y-coordinate (the output) of a point on the line.
- **`m`** — the slope, which controls how much `y` changes as `x` changes (this plays the role of a *weight* in a neural network).
- **`x`** — the x-coordinate (the input).
- **`b`** — the y-intercept, i.e., the point where the line crosses the y-axis (this plays the role of a *bias* in a neural network).

Each neuron in a real neural network performs a generalized version of this: it computes a weighted sum of its inputs plus a bias term (analogous to `mx + b`, but with many inputs and weights instead of just one), and then passes that sum through a non-linear activation function. Stacking many such neurons across many layers is what gives a DNN the ability to represent far more complex functions than a single straight line.

### 🧪 Assisted Practice

The lesson includes a hands-on Jupyter Notebook exercise to reinforce forward propagation concepts:

> **4.04 — Example: Working on Forward Propagation**

(Refer to the Reference Material section of the course to download the corresponding notebook file.)

---

## 8. Backward Propagation in DNN

### 8.1 What Is Backward Propagation?

**Backward propagation** (or "backprop") is the practice of adjusting a neural network's **weights** based on the error/loss that was measured in the previous training pass (epoch). It is, in a very real sense, the "learning" part of neural network training — the mechanism by which the network improves over time and drives error rates down.

An important caveat repeated in the lesson: **backpropagation can overtrain or overfit a model**, just like any other training/fitting method. Having a powerful learning mechanism does not automatically guarantee good generalization — this is exactly why the lesson later introduces regularization techniques.

### 8.2 Loss Calculation in Backward Propagation

The specific method used to calculate the loss depends on which loss function is chosen for the task (MSE, cross-entropy, hinge loss, etc. — all covered above). But conceptually, in every case, the **loss function represents the "distance"** the model's current prediction is from being correct for a given input — i.e., the difference between what the model predicted and what the correct answer actually was.

### 8.3 How Backward Propagation Is Used: Gradient Descent

The **gradient descent** algorithm relies on backward propagation to compute the **gradient of the loss function** with respect to the network's weights. The overall procedure is:

1. Run forward propagation to compute the model's output for a given input.
2. Calculate the loss for that output using the chosen loss function.
3. Use backward propagation to compute how the loss would change if each individual weight changed slightly — this is the **gradient** (the derivative of the error with respect to each weight).
4. Update the weights in the direction that reduces the loss (opposite the gradient direction), thereby minimizing the loss function over successive iterations.

In short: to reduce error, we need to know *how* the error changes as we tweak each weight. That sensitivity is precisely what the gradient captures, and computing it efficiently for every weight in the network is exactly what the backpropagation algorithm does (via the chain rule of calculus, propagating error signals backward from the output layer to the input layer).

```
Network inputs → [Input layer] → [Hidden layer] → [Output layer] → Network output
                        ←──────────── Backpropagation ────────────
                        ──────────────→ Feed forward ─────────────→
```

Gradient descent begins by examining the activation outputs at the **output nodes** and works backward from there to figure out how each preceding weight should be readjusted.

### 8.4 Direction of Weight Adjustment

If the output nodes predict a value **higher** than the true value, gradient descent will **lower** the predicted values by adjusting the relevant weights — this reduces the loss for that input. More generally: the algorithm travels **backward through the network** (from output layer back toward input layer, i.e., "right to left" in a typical left-to-right network diagram) and adjusts the weights at each layer in turn, based on how much each weight contributed to the overall error.

```
Network input → [Input layer] → [Hidden layer] → [Output layer] → Network output
                                                          ↑
                                        Backward propagation adjusts weights,
                                        moving right → left through the network
```

**Worked intuition:** Imagine our loan-default model (from the business scenario) predicts a default probability of 0.9 for an applicant who actually did *not* default (true label 0). The loss function flags this as a large error. Backpropagation computes how much each weight in the network contributed to that overinflated prediction, and gradient descent nudges each of those weights slightly in the direction that would have produced a lower (more accurate) prediction, layer by layer, moving backward from the output toward the input.

> **Note on vanishing/exploding gradients:** Although not explicitly named in these slides, the mechanism described above — gradients flowing backward across many layers — is exactly why very deep networks can suffer from **vanishing gradients** (the gradient signal shrinks as it's multiplied backward through many layers with small derivatives, so early layers barely update) or **exploding gradients** (the reverse: gradients grow uncontrollably large, causing unstable, huge weight updates). This is one of the central practical challenges of training genuinely deep networks and is a major motivation for techniques such as careful weight initialization, normalization layers, and choosing activation functions (like ReLU) that resist gradient vanishing better than saturating functions like sigmoid/tanh.

---

## 9. Regularization

### 9.1 Recap: What Makes a Network "Deep"

A neural network becomes a **deep neural network** once it contains **more than one hidden layer** between its input and output layers. As we've seen, this depth is what gives DNNs their representational power — but that power comes with a risk: **overfitting**.

### 9.2 The Overfitting Problem

An **epoch** refers to one complete pass of the entire training dataset forward and backward through the network. As training proceeds across many epochs, a model can begin to **fit the training data too well** — including its outliers and noise — while its performance on new, unseen (test) data stops improving or even gets worse. This is the classic **overfitting** problem: excellent memorization of the training set, poor generalization to the real world.

```
error
  ^
  |    \
  |     \___ Training error (keeps decreasing)
  |
  |  Test/validation error (starts increasing after some point)
  |          ↑
  |     Early stopping point
  +----------------------------------> Epochs
```

**Early stopping** is one practical remedy: it's an algorithm/rule that monitors validation performance and decides how many training iterations to run before the model begins to overfit, halting training at (roughly) the point where test error starts rising even as training error keeps falling.

### 9.3 What Is Regularization?

**Regularization** is a broader family of methods used in machine learning and deep learning specifically to **avoid overfitting** and improve a model's ability to **generalize** to new data. Mechanically, regularization works by introducing an extra **penalty term into the loss function** during training — this penalty discourages the model from becoming unnecessarily complex (e.g., relying on very large weights, or on too many active units at once).

Two commonly used regularization techniques covered in this lesson:

```
Regularization
    ├── L2 Regularization (Weight Decay)
    └── Dropout Regularization
```

### 9.4 L2 Regularization (Weight Decay)

**L2 regularization**, also known as **weight decay**, is a specific regularization technique that adds the **squared magnitude of the weights** to the cost function. The intuition: large weights often correspond to a model that has learned overly specific, complex patterns (including noise) from the training data, so penalizing large weights nudges the model toward simpler, smoother solutions.

**Key mechanics:**

- Regularization penalizes large weights **in addition to** the original cost/loss function value.
- A **weight decay coefficient (λ, "lambda")** determines how strongly regularization influences gradient computation — it controls the trade-off between fitting the data well and keeping weights small.
- A **larger** weight decay coefficient implies a **larger penalty** for large weights (i.e., stronger regularization, pushing weights closer to zero).
- Using the notation from the lesson: `C` is the regularized cost function, `C0` is the original (unregularized) cost function, and `λ` is the weight decay coefficient. Conceptually: `C = C0 + λ · (regularization term based on squared weights)`.

**Effect on the network:** Applying L2 regularization tends to reduce the effective complexity that hidden layers contribute — pushing a network's learned function to behave in a more linear, less wildly nonlinear way, since large weights (which enable sharp, complex nonlinear behavior) are discouraged.

### 9.5 Dropout Regularization

**Dropout** is a technique applied *during training* that helps prevent overfitting by **randomly deactivating (dropping) units (neurons)**, along with their connections, with a certain probability.

**Key mechanics:**

- During each training step, units are randomly dropped, along with their connections to the rest of the network.
- Each unit is **retained** (kept active) with a fixed probability `p`, independent of every other unit's status, where `0 < p < 1`.
- `p` is a **hyperparameter** that must be chosen/tuned by the practitioner — it isn't learned automatically by the network.
- In practice, this means a random fraction of the weights/activations are effectively set to zero for that particular training step, forcing the rest of the network to not over-rely on any single unit or narrow combination of units.

**Visual idea:**

```
(a) Standard network             (b) Network with dropout applied
    ● ● ● ●                          ● ✕ ● ✕
    ● ● ● ●          --->            ✕ ● ✕ ●
    ● ● ● ●                          ● ● ✕ ●
(all neurons active)              (✕ = temporarily deactivated neuron)
```

The overarching goal is to **prevent overfitting** and **improve generalization** by ensuring the network can't become overly dependent on any specific subset of neurons — since any neuron might be "switched off" on a given training step, the network is forced to develop more redundant, robust internal representations.

### 9.6 The Dropout Experiment: Choosing the Right Dropout Rate

A classic illustrative experiment uses a neural network with architecture **784-2048-2048-2048-10** (784 input features, three hidden layers of 2048 units each, 10 output classes — this matches the well-known MNIST handwritten-digit dataset, which has 28×28 = 784 pixel inputs and 10 digit classes) trained on **MNIST**. The dropout rate `p` (probability of *keeping* a unit) is varied from very low up to 1.0 (no dropout at all), with these results:

| Dropout setting | Training error | Test error | Interpretation |
|---|---|---|---|
| **No dropout** (p = 1.0) | Low | **High** | Overfitting — memorizes training data, generalizes poorly |
| **Best dropout rate** (p ≈ 0.5) | Low | **Low** | Good balance — strong regularization without losing capacity |
| **High dropout rate** (p < 0.3) | High (underfitting) | High | Too many units switched off; network can't learn enough during training |

This experiment nicely illustrates that dropout rate is a trade-off knob: **too little dropout → overfitting**, **too much dropout → underfitting**, and a well-tuned middle value (here, around p = 0.5) gives the best of both worlds — low training error *and* low test error.

---

## 10. Key Takeaways

- A **deep neural network (DNN)** is an artificial neural network that has **multiple hidden layers** between its input and output layers.
- A DNN provides **better calculation of output probabilities** and generally more **accurate predictions** than shallower models, especially on complex, hierarchical problems.
- **Loss functions** in DNNs act as error functions — they estimate the model's error/loss, and that estimate is what backpropagation uses to update the network's weights.
- There are different types of **regularization techniques** (such as L2 regularization and dropout) used to **reduce overfitting** and improve a model's ability to **generalize to unseen data**.

---

## ✅ Knowledge Check (From the Lesson)

**1. What is the task of a loss function in a DNN?**

- **A.** To calculate the probability of an output
- **B.** To pass input to multiple hidden layers
- **C.** To adjust the weights of the neural network based on the error rate
- **D.** To estimate the model's error or loss

**Correct answer: D.** The task of a loss function is to estimate the model's error or loss, which is then used to change the weights in the hidden layers of the network in order to reduce the loss on the next assessment.

**2. How does a DNN work?**

- **A.** By passing input through one hidden layer
- **B.** By passing input through multiple hidden layers
- **C.** By using decision trees
- **D.** By using linear regression

**Correct answer: B.** A DNN works by passing input through multiple hidden layers, which allows for better calculation of the probability of every possible output.

**3. What is the purpose of regularization in building deep neural networks?**

- **A.** To make the model more complex
- **B.** To prevent overfitting
- **C.** To speed up the training process
- **D.** None of the above

**Correct answer: B.** The purpose of regularization is to prevent overfitting, which occurs when the model becomes too complex and fits the training data too well, at the expense of generalizing to new data.

---

## 📝 Practice Questions

### Multiple Choice

**Q1.** What structurally distinguishes a Deep Neural Network (DNN) from a traditional, shallow neural network?
- **A.** The type of programming language used to implement it
- **B.** The presence of more than one hidden layer between the input and output layers
- **C.** The use of only linear activation functions
- **D.** The absence of an output layer

**Q2.** A model predicts salary as a continuous number from features like experience and education. Which category of loss function is appropriate?
- **A.** Hinge loss
- **B.** Categorical cross-entropy loss
- **C.** Regression loss
- **D.** Binary cross-entropy loss

**Q3.** Given actual values [10, 20, 30] and predicted values [12, 18, 33], what is the Mean Absolute Error (MAE)?
- **A.** 1.0
- **B.** 2.33
- **C.** 3.0
- **D.** 7.0

**Q4.** Why does Mean Squared Error (MSE) react much more strongly to outliers than Mean Absolute Error (MAE)?
- **A.** MSE ignores outliers entirely
- **B.** MSE squares each error term, so large errors are amplified disproportionately
- **C.** MSE is calculated only on the largest error in the dataset
- **D.** MAE always produces larger values than MSE regardless of outliers

**Q5.** For a dataset known to contain significant outliers, which regression loss function is generally the more robust choice?
- **A.** MSE, because squaring stabilizes outlier influence
- **B.** MAE, because it treats every error linearly instead of amplifying large ones
- **C.** Hinge loss, because it is designed for regression
- **D.** Cross-entropy loss, because it works for any numeric target

**Q6.** In a 3-class cross-entropy calculation, the actual (one-hot) label is [0, 1, 0] and the predicted distribution is [0.2, 0.7, 0.1]. Which term(s) actually contribute a nonzero value to the cross-entropy sum?
- **A.** All three terms contribute equally
- **B.** Only the term corresponding to the "Apple" class (index 1), since its true-label indicator is 1
- **C.** Only the first term, since it has the smallest predicted probability
- **D.** None of the terms contribute, since none of the predictions equal exactly 1

**Q7.** What is the key difference between categorical cross-entropy and sparse categorical cross-entropy?
- **A.** Sparse categorical cross-entropy is used only for regression, not classification
- **B.** Categorical cross-entropy requires one-hot encoded labels, while sparse categorical cross-entropy uses plain integer class labels
- **C.** Sparse categorical cross-entropy cannot be used with more than two classes
- **D.** There is no real difference; the names are interchangeable in all cases

**Q8.** Why is using MSE or MAE as a loss function for a classification problem potentially risky?
- **A.** It automatically causes underfitting
- **B.** It can produce "overconfident wrong predictions" since numeric closeness doesn't reflect proper probability calibration
- **C.** It makes the model incapable of producing an output
- **D.** It requires one-hot encoded labels, which are hard to generate

**Q9.** In hinge loss, what target label convention is used for binary classification (as opposed to the 0/1 convention used with cross-entropy)?
- **A.** 0 and 1
- **B.** -1 and +1
- **C.** Any real number between 0 and 1
- **D.** Class names as strings only

**Q10.** According to the hinge loss scenarios described in the lesson, what is the loss when a prediction is correct and f(x)·y ≥ 1 (i.e., correctly classified with a comfortable margin)?
- **A.** Always exactly 1
- **B.** A large positive penalty proportional to confidence
- **C.** Zero
- **D.** Negative, to reward the model

**Q11.** What is the primary purpose of the activation function applied at each layer during forward propagation?
- **A.** To reverse the direction of data flow through the network
- **B.** To transform the weighted sum of inputs at a layer before passing it to the next layer, enabling non-linear representations
- **C.** To calculate the final loss value for the network
- **D.** To randomly drop neurons during training

**Q12.** What mathematical operation does backpropagation rely on to determine how much each weight contributed to the overall error?
- **A.** Random sampling of weights
- **B.** Computing the gradient (derivative) of the loss function with respect to each weight
- **C.** Sorting the training data by label
- **D.** Recomputing the forward pass with all weights set to zero

**Q13.** In the classic dropout experiment on MNIST (network architecture 784-2048-2048-2048-10), what happens when the dropout rate is very high (p < 0.3, meaning most units are dropped)?
- **A.** The model overfits heavily, with very low training error and very high test error
- **B.** The model underfits, since too few units remain active during training
- **C.** Training and test error both become zero
- **D.** Dropout has no effect on training or test error in this case

**Q14.** What does the weight decay coefficient (λ) control in L2 regularization?
- **A.** The number of hidden layers in the network
- **B.** The learning rate used during forward propagation
- **C.** How strongly large weights are penalized in the regularized cost function
- **D.** The number of epochs used during training

**Q15.** Which of the following is a well-known practical training difficulty specifically associated with backpropagation in very deep networks, where the gradient signal shrinks (or grows) as it passes backward through many layers?
- **A.** Vanishing/exploding gradients
- **B.** Overfitting on the test set only
- **C.** The one-hot encoding problem
- **D.** Hinge loss non-convergence

### Short Answer

**Q16.** In your own words, explain why "depth" (multiple hidden layers) allows a DNN to outperform a shallow neural network on complex tasks like image recognition.

**Q17.** Explain the difference between a binary classification problem and a multi-class classification problem, and give one example of each that is different from the examples used in the lesson.

**Q18.** Describe, in 2–3 sentences, how gradient descent uses the output of backpropagation to update a network's weights.

**Q19.** Why might early stopping be considered a form of regularization, even though it doesn't add a penalty term to the loss function?

---

### Answers

**A1: B.** Depth — specifically the presence of more than one hidden layer between input and output — is the defining structural feature of a DNN; it's what lets it learn increasingly abstract, hierarchical representations that shallow networks cannot.

**A2: C.** Predicting a continuous numeric value (like salary) is a regression task, so a regression loss (such as MAE or MSE) is the appropriate category — not a classification loss like hinge or cross-entropy.

**A3: B (2.33).** Errors are |10−12|=2, |20−18|=2, |30−33|=3; sum = 7; MAE = 7/3 ≈ 2.33.

**A4: B.** MSE squares each individual error before averaging, so a single large error contributes disproportionately (e.g., an error of 20 contributes 400 to the sum, versus only 20 under MAE), making MSE far more sensitive to outliers than MAE.

**A5: B.** MAE treats every error linearly (via absolute value) rather than squaring it, so a handful of extreme outliers won't dominate the overall loss the way they do with MSE.

**A6: B.** Because the true label is one-hot encoded ([0,1,0]), only the term multiplied by 1 (the "Apple" position) survives in the cross-entropy sum; every other term is multiplied by 0 and vanishes regardless of its predicted probability.

**A7: B.** Categorical cross-entropy expects labels as one-hot vectors (e.g., [0,0,1,0]), while sparse categorical cross-entropy expects the same information as a plain integer class index (e.g., 2) — the underlying math/result is equivalent, but sparse is often more memory-efficient with many classes.

**A8: B.** MSE/MAE measure raw numeric distance rather than proper probability calibration, so a wrong classification can still produce a small numeric loss, letting the model become confidently wrong — cross-entropy avoids this by directly penalizing low probability assigned to the correct class.

**A9: B.** Hinge loss uses the +1/−1 label convention (as opposed to cross-entropy's 0/1 convention), which is what allows the `y · f(x)` product to naturally represent "agreement" (positive) or "disagreement" (negative) between prediction and true label.

**A10: C.** When `y·f(x) ≥ 1`, the quantity `1 − y·f(x)` is zero or negative, so `max(0, 1 − y·f(x)) = 0` — hinge loss gives zero penalty to any correct prediction that clears the margin, no matter how much it "overshoots."

**A11: B.** The activation function introduces non-linearity into each layer's output; without it, stacking layers would just be equivalent to one big linear transformation, and the network would lose the ability to model complex, non-linear relationships.

**A12: B.** Backpropagation computes the gradient (partial derivative) of the loss with respect to each weight via the chain rule, which tells gradient descent exactly how much — and in which direction — each weight should be adjusted to reduce the loss.

**A13: B.** With a high dropout rate, too many units are turned off during training, so the network doesn't have enough active capacity to learn the underlying patterns — this produces underfitting, with high error on both training and test data.

**A14: C.** λ (the weight decay coefficient) scales the strength of the penalty applied to large weights in the regularized cost function — a larger λ means a stronger penalty and thus smaller learned weights.

**A15: A.** Vanishing/exploding gradients occur because the gradient signal is repeatedly multiplied backward through many layers during backpropagation; if those multiplicative factors are consistently small, the gradient shrinks toward zero (vanishing), and if consistently large, it grows unboundedly (exploding) — both make training very deep networks difficult.

**A16:** Each additional hidden layer lets the network build a new, more abstract representation on top of the previous layer's output — for example, early layers might detect edges, middle layers might combine edges into shapes, and later layers might combine shapes into recognizable objects. This hierarchical feature-building is what lets DNNs capture the highly non-linear, layered structure present in complex data like images or speech, which a shallow network with limited transformation capacity struggles to represent.

**A17:** Binary classification assigns each example to exactly one of two classes (e.g., "loan defaults" vs. "loan does not default," labeled 0/1). Multi-class classification assigns each example to one of more than two possible classes, predicting a probability for each (e.g., classifying an email as "spam," "promotions," or "primary"). (Any reasonable original examples are acceptable.)

**A18:** Backpropagation computes the gradient of the loss function with respect to every weight in the network, essentially answering "how would the loss change if I nudged this weight slightly?" Gradient descent then updates each weight by moving it a small step in the direction that decreases the loss (opposite to the gradient), and this process repeats over many iterations/epochs until the loss is sufficiently minimized.

**A19:** Regularization broadly refers to any technique that helps a model avoid overfitting and generalize better to unseen data. Early stopping achieves this goal indirectly — not by penalizing the loss function, but by halting training at the point where validation/test error starts rising even as training error keeps falling — which prevents the model from continuing to "overlearn" the training set's noise. Because it serves the same purpose (better generalization, less overfitting) through a different mechanism, it's commonly grouped together with regularization techniques.
