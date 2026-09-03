# Recurrent Neural Networks (RNN)

*Deep Learning with Keras and TensorFlow — Lesson 11*

## Learning Objectives

By the end of this lesson, you will be able to:

- Analyze and interpret sequential data to understand temporal dependencies using RNN architectures.
- Examine different RNN architectures to identify their suitability for various types of sequential modeling tasks.
- Apply LSTM models to perform text classification, demonstrating the ability to capture and utilize linguistic patterns effectively.
- Implement a hybrid RNN model to classify video data, integrating knowledge of both spatial and temporal feature extraction.

---

## Business Scenario

ABC Corporation is a financial company that needs a predictive model to analyze financial market trends, study time-series data, and forecast future outcomes. To achieve this, the company builds a **sequence modeling** system that can handle and predict sequential data — specifically a **recurrent neural network (RNN)** that studies historical financial data and uses it to forecast future market trends.

ABC Corporation goes a step further and builds a **hybrid model**: it combines the **one-to-many** architecture of an RNN with a **convolutional neural network (CNN)** to predict a series of sequential events. This hybrid approach lets ABC Corporation make more accurate predictions and gain a competitive edge in the financial market.

*Why this matters:* this scenario illustrates the central theme of the lesson — plain feedforward networks cannot reason about "what happened before," but RNNs (and hybrids that combine RNNs with CNNs) can, which is exactly what is needed for stock prices, sensor readings, or any data that unfolds over time.

---

## Sequential Modeling

### What Is Sequential Modeling?

**Sequential modeling** is a task or problem domain that involves predicting or modeling patterns in **sequential data** — data where the order of elements carries meaning. Examples of sequential data include:

- **Text** — the meaning of a sentence depends on word order (e.g., "dog bites man" vs. "man bites dog").
- **Video** — a sequence of image frames played in order over time.
- **Audio** — a waveform or sequence of sound samples that changes over time (e.g., speech, music).

Any tool that can model, interpret, and predict these kinds of data is doing sequential modeling. In short: whenever "what came before" changes the meaning of "what comes now," you need a sequential model rather than a model that looks at inputs independently and out of order.

### Advantages of Sequential Modeling

- **Captures temporal dependencies in data** — it can relate an event now to events that happened earlier, e.g., predicting tomorrow's stock price using the last 30 days of prices.
- **Handles variable-length input** — a sentence can be 5 words or 50 words, and an audio clip can be 2 seconds or 2 minutes; sequential models are not tied to a fixed input size.
- **Advantageous in time-series prediction tasks** — such as forecasting sales, temperature, or stock prices where the next value depends on a trend.
- **Widely used in natural language processing (NLP)** — translation, sentiment analysis, and text generation all depend on word order and context.
- **Essential in speech and audio processing** — recognizing spoken words requires understanding how sound changes moment to moment.
- **Enables sequential decision-making in various domains** — such as a game-playing agent choosing its next move based on the history of previous moves.

### Types of Sequential Models

The lesson highlights three broad families of sequential models:

- **RNNs (Recurrent Neural Networks)** — networks with a feedback loop that carries information from one time step to the next.
- **Autoencoders** — networks that learn compressed (encoded) representations of data and can be adapted for sequences.
- **Seq2Seq (Sequence-to-Sequence)** — architectures (often built from RNNs) that map an input sequence to an output sequence, used heavily in machine translation and summarization.

### How RNNs Achieve "Memory"

To achieve memory-based learning, a special AI algorithm called a **recurrent neural network (RNN)** is used. The "memory" aspect of an RNN refers to its ability to use information from **previous time steps** in the sequence to inform its **current** output. This is particularly useful in applications where context matters — for instance, understanding the word "bank" in a sentence requires remembering the words that came before it (a river bank vs. a savings bank).

### How Sequential Modeling Works

Conceptually, an RNN takes a series of input values `X1, X2, ..., Xi` and produces a series of output values `Y1, Y2, ..., Yi`, where the **same RNN cell is reused at every time step**. Each copy of the cell passes information forward to the next copy, so the network is effectively "unrolled" across time:

```
X1 → [RNN] → Y1
       |
       v
X2 → [RNN] → Y2
       |
       v
Xi → [RNN] → Yi
```

The input values are often **time-series data**, meaning variables that change over time (e.g., hourly temperature, daily stock price, or word-by-word text). The network analyzes the recurring input values and treats each one as a discrete input relevant to solving the current problem, while still being informed by the inputs that came before it.

### Real-World Applications

**Example — NLP (email spam classification):** Sequence modeling can process text into valuable insights. An **email spam classifier** reads the sequence of words in an email and decides whether it is spam. This enhances the user experience by identifying and filtering out unwanted or harmful emails, keeping the inbox organized and secure.

**Example — Audio/music:** Another use case is a computer program that (1) takes an **audio file** as input, (2) **recognizes its possible genre**, and (3) **suggests a sequence of musical notes** to complete the song. This could aid musical composition, since many musicians struggle with music theory / notation early in their careers, and an AI assistant that suggests the next notes based on the audio it has "heard" so far can help bridge that gap.

---

## Introduction to Recurrent Neural Networks

### Why RNNs Were Needed

RNNs were introduced **after** feed-forward neural networks (FNNs) specifically to address the limitation that FNNs cannot process sequential data well. A standard feedforward network has an input layer, one or more hidden layers, and an output layer, with information flowing in only one direction (input → hidden → output). It has no built-in way to remember what input it saw previously — each prediction is made independently.

### Example: FNN vs. RNN

Consider a computer program that suggests a sport to play, based on the time of day and the weather. An FNN follows a fixed pattern and always makes the same decision for the same conditions:

> An FNN would suggest the **same sport** for similar weather conditions every day (e.g., always football in the evening when the weather is clear, or always badminton when there is no wind).

An RNN, on the other hand, has memory of past interactions:

> An RNN would **remember the user's choices from the previous day** and suggest something **different** the next day — even under identical weather conditions — because it factors in the history of past choices, not just today's inputs.

This is the crucial conceptual difference: an FNN is a pure function of its current input; an RNN is a function of its current input **and** its internal memory of previous inputs.

### What Is a Recurrent Neural Network?

A **recurrent neural network (RNN)** is a state-of-the-art algorithm — used by systems such as Apple's Siri and Google's voice search — that is ideal for machine learning problems involving sequential data, such as natural language processing and time-series forecasting.

Key properties:

- It is the **first algorithm that "remembers" its input** thanks to an internal memory (the hidden state), which is carried from one time step to the next.
- The ability to carry information from the **recent past into the present** allows it to make more precise, context-aware predictions than a memoryless model.

### Common Uses of RNNs

RNNs are mainly used for:

- **Sequence classification** — e.g., sentiment classification (deciding if a movie review is positive or negative) and video classification (deciding what category a video belongs to).
- **Sequence labeling** — e.g., part-of-speech tagging (labeling each word in a sentence as noun, verb, etc.) and named entity recognition (identifying that "Paris" is a location and "Google" is an organization within a sentence).

### The Four Types of RNN Architecture

RNNs are commonly categorized by how many inputs they take relative to how many outputs they produce:

| Architecture | Input → Output | Typical Example |
|---|---|---|
| **One-to-One** | Single input → single output | Classifying a single image of a musical symbol |
| **One-to-Many** | Single input → sequence of outputs | Generating a sequence of musical notes from one starting note/genre |
| **Many-to-One** | Sequence of inputs → single output | Classifying the genre of a song from the full audio input |
| **Many-to-Many** | Sequence of inputs → sequence of outputs | Generating a string of musical symbols from a sequence of notes/chords |

#### One-to-One

The **one-to-one** architecture is essentially the basis of a standard feedforward neural network. Because there is only a single input and a single output, no recurrent activation values need to be carried across time steps — it is the simplest case. At a given time step `t`, input `x(t)` produces hidden state `h(t)` which produces output `O(t)`, with nothing fed forward to another time step.

*Example:* An architecture used to classify the image of a single musical symbol (e.g., is this a sharp, a flat, or a natural sign?) — one image in, one label out.

#### One-to-Many

In the **one-to-many** architecture, a single input drives the entire network. Once that one input is given, the network produces a **series of outputs**, one for each subsequent time step, by feeding each output/hidden state forward to generate the next.

*Example:* Generating a sequence of musical notes based on just the first note, or based on the genre of music given as input — one seed value produces an entire melody over time.

#### Many-to-One

In the **many-to-one** architecture, a sequence of multiple inputs is fed into the network, which is trained to produce a **single** output only after having seen the whole sequence.

*Example:* Classifying the genre of music by feeding an entire song (a sequence of audio inputs) into the network and getting back one label, such as "jazz" or "rock."

#### Many-to-Many

In the **many-to-many** architecture, a sequence of multiple inputs produces a sequence of outputs, which **may or may not be the same length** as the input sequence. These networks typically have two components: an **encoder** (which reads and compresses the input sequence) and a **decoder** (which generates the output sequence from that compressed representation).

*Example:* Generating a string of musical symbols from a sequence of input musical notes or chords — a sequence of notes goes in, and a (possibly differently-sized) sequence of symbols comes out. This encoder–decoder pattern is the same one used in machine translation, where an input sentence in English (sequence 1) becomes an output sentence in French (sequence 2), and the two sequences need not have the same number of words.

### Advantages of RNNs

- **Weights can be shared across time steps** — the same set of weights (the same RNN cell) is reused at every position in the sequence, which drastically reduces the number of parameters compared to having a separate set of weights for every time step.
- **The model can process inputs of any length** — because the same cell is applied repeatedly, an RNN is not restricted to a fixed input size the way a plain feedforward network is.
- **The model size isn't affected by the input size** — a longer sequence just means more repetitions of the same small cell, not a bigger model.
- **The model is designed to remember each piece of information**, which is helpful for any time-series predictor that must relate the current value to past values.

### Disadvantages of RNNs

1. **Difficulty in training RNN models** — RNNs are notoriously harder to train and tune than feedforward networks because errors must be propagated backward across many time steps.
2. **Computation is slow due to the recurrent nature** — because each time step depends on the previous one, RNNs must be processed sequentially and cannot be as easily parallelized as feedforward layers.
3. **Issues with exploding and vanishing gradients** — during backpropagation through many time steps, gradients can either shrink toward zero (**vanishing gradients**) or grow uncontrollably large (**exploding gradients**). Vanishing gradients mean the network effectively "forgets" long-range dependencies (it cannot learn that a word 50 steps back in a sentence matters), because the gradient signal used to update early weights becomes too small to have any effect. Exploding gradients cause unstable training, with weight updates that overshoot wildly. This single disadvantage is the main motivation behind LSTM and GRU architectures, covered later in this lesson.

---

## Architecture and Working of RNN

### Architecture of RNN

The RNN architecture is designed to process sequential data by capturing temporal dependencies and retaining memory of previous inputs. It consists of **three main components**:

- An **input layer** (`x`)
- A **hidden layer with recurrent connections** (`h`)
- An **output layer** (`y`)

Three parameter matrices — commonly labeled **A, B, and C** (or, in the equations below, `Wxh`, `Whh`, and `Why`) — are used to transform information as it flows through the network and enhance the model's output. Critically, **the output at each time step is fed back into the network** (via the hidden state) to improve the computation of subsequent outputs — this feedback loop is what makes the network "recurrent."

### Working of an RNN, Step by Step

The RNN's operation is best understood as five stages:

1. **Initialization**
2. **Input processing**
3. **Hidden state update**
4. **Output calculation**
5. **Training**

#### 1. Initialization

Using the notation where `X` is the input state, `s` (or `h`) is the hidden state, and `O` is the output, with weight matrices `U`, `V`, and `W`:

The network begins by **initializing the hidden state** to a vector of zeros (or small random values), and by defining the RNN architecture — the number of hidden units and the activation functions to use. This is analogous to how any neural network initializes its weights before training, except here there is also a hidden-state vector that needs a starting value since, at the very first time step, there is no "previous" hidden state yet.

#### 2. Input Processing

The input sequence is processed **one element at a time**. At each time step, the current input is combined with the previous hidden state so the network can capture context and dependencies. The activation of the hidden layer is then computed from this combined input.

Notation:
- `Xt` — the input at time step `t`
- `ht` — the hidden state at time step `t`
- `ht-1` — the hidden state carried over from the previous time step `t-1`

The combination is computed as:

```
at = (Wxh · Xt + Whh · ht-1) + bh
```

Where:
- `Wxh` — the weight matrix for input-to-hidden connections (how much the current input matters).
- `Whh` — the weight matrix for hidden-to-hidden connections (how much the previous memory matters).
- `Xt` — the current input.
- `bh` — the bias term for the hidden layer.
- `at` — the combined ("pre-activation") input fed into the activation function of the RNN cell, which will determine the new hidden state `ht`.

Intuitively, this equation says: "the new candidate hidden state is a mix of what I'm seeing right now and what I already remembered, plus a small constant offset."

#### 3. Hidden State Update

The hidden state is then updated by passing the combined input through a **non-linear activation function**, typically the **hyperbolic tangent (tanh)**, which squashes values into the range (-1, 1). This step is what lets information flow across different time steps.

```
ht = tanh(Whh · ht-1 + Wxh · Xt + bh + bx)
```

Where:
- `ht` — the new hidden state (the network's updated "memory").
- `Whh` — the weight matrix determining how much the previous hidden state influences the current hidden state.
- `Wxh` — the weight matrix determining how much the current input `Xt` influences the current hidden state.

The `tanh` function is chosen because it is smooth, differentiable (needed for backpropagation), and keeps the hidden state values bounded, which helps stabilize training.

#### 4. Output Calculation

Once the hidden state is updated, the network computes its output for that time step:

```
Yt = Why · ht + by
```

Where:
- `Yt` — the output at time step `t`.
- `Why` — the output-layer weight matrix (maps the hidden state to output space).
- `by` — the bias term for the output layer.

Any additional transformation or activation function needed (for example, a softmax for classification) is applied here to get the output into the desired format.

#### 5. Training

During training, the RNN calculates the **loss** between its predicted output and the actual target output at each time step. The network's weights and biases are then updated using **Backpropagation Through Time (BPTT)** together with an optimization algorithm (such as gradient descent or Adam).

**Backpropagation Through Time (BPTT)** is ordinary backpropagation applied to the "unrolled" version of the RNN — since the same weights are reused at every time step, the gradient for those weights is the sum of the gradients computed at every time step going backward through the sequence. This repeated backward chaining through many time steps is precisely why vanishing/exploding gradients are such a problem for plain RNNs: the more time steps there are, the more times a small (or large) gradient factor gets multiplied together.

This training process helps the RNN learn to make increasingly accurate predictions and improves its performance over time, similar to how a stock-forecasting RNN would gradually reduce the gap between its "Prediction" line and the "Actual" line on a chart of values over time.

### Assisted Practice: 11.05 — Text Classification Using RNN

> This section of the course pairs with a hands-on Jupyter Notebook exercise ("11.05_Part_1_Text Classification Using RNN") where learners implement text classification using a basic RNN. Refer to the course's Reference Material section to download the corresponding notebook file.

---

## Long Short-Term Memory (LSTM)

### Motivation: Solving the Gradient Problem

As noted above, when backpropagating through time, plain recurrent neural networks suffer from **exploding and vanishing gradient** problems. Because the same weight matrices are applied repeatedly across many time steps, gradients get multiplied together many times over — if those factors are consistently less than 1, the gradient shrinks toward zero (vanishing); if consistently greater than 1, it grows without bound (exploding). Either way, the network struggles to learn dependencies that span many time steps (i.e., "long-term" dependencies).

The modified versions of RNNs designed specifically to address this problem are:

- **Long Short-Term Memory networks (LSTMs)**
- **Gated Recurrent Units (GRUs)** — covered in the next section

### What Is LSTM?

**LSTM** is an RNN architecture designed to **capture and retain long-term dependencies** in sequential data, directly overcoming the vanishing-gradient limitation of traditional RNNs. LSTM networks are widely used in tasks such as:

- Natural language processing
- Speech recognition
- Time-series analysis

### The Three Gates of an LSTM Cell

LSTM achieves long-term memory by introducing a **cell state** alongside the hidden state, and by controlling what goes into and out of that cell state using three gates:

1. **Forget gate** — determines which information to **discard** from the previous memory cell state. Analogy: deciding which parts of what you remember are no longer relevant and can be dropped.
2. **Input gate** — regulates which **new** information to incorporate into the current memory cell state. Analogy: deciding what new information from the current input is worth remembering.
3. **Output gate** — controls what is actually **output** from the memory cell at this time step. Analogy: deciding, given everything currently remembered, what part of that memory is relevant to reveal right now.

Put together, the flow at each LSTM cell is: **forget** irrelevant information → **add/update** new information → **pass** the updated information (through the output gate) to produce the current output and hand off the updated cell state to the next time step.

*Example:* In a sentence like "Sam grew up in France, ... he speaks fluent ___," an LSTM's forget gate lets it retain the fact "Sam is from France" over many intervening words (a long-term dependency), while its input gate lets it fold in nearby context, and its output gate lets it use the retained "France" fact only when it becomes relevant (predicting "French").

### Hidden State and Cell State

An LSTM, like a simple RNN, includes a **hidden state**, but it additionally maintains a **cell state**:

- **Hidden state:** `Ht-1` (previous time step) and `Ht` (current time step) — similar in role to the hidden state in a vanilla RNN.
- **Cell state:** `Ct-1` (previous time step) and `Ct` (current time step) — this is the new element that LSTMs introduce.

The **cell state** is what enables LSTMs to capture and retain **long-term dependencies** in sequential data: it acts like a conveyor belt that carries relevant information across many time steps largely unchanged, only being selectively modified by the forget and input gates, rather than being completely recomputed from scratch at every step (as the hidden state in a plain RNN is). This design is precisely what mitigates the vanishing gradient problem.

### Assisted Practice: 11.07 — Text Classification Using LSTM

> This section pairs with a hands-on notebook exercise ("11.07_Part_2_Text Classification Using LSTM") in which learners re-implement text classification, this time using LSTM instead of a plain RNN, and can compare the results. Refer to the course's Reference Material section to download the notebook file.

---

## Gated Recurrent Unit (GRU)

### What Is a GRU?

**GRUs (Gated Recurrent Units)** are a type of RNN architecture that, like LSTMs, incorporate **gating mechanisms** to regulate the flow of information between neural network cells — but with a **simpler** internal structure. GRUs are relatively newer than LSTMs and have shown **comparable or better performance with fewer parameters** (a simpler architecture), since they merge some of the LSTM's gates and drop the separate cell state.

A GRU cell, unrolled across time steps, takes input `Xt`, combines it with the previous hidden state `ht-1` (labeled `hRNN` on the diagram), and passes it through:

- A **reset gate**
- An **update gate**
- Activation/squashing functions

to produce the new hidden state `ht` and output `Yt`.

### Components of a GRU

- **Reset gate:** Controls the relevance of the **previous** cell state by deciding to what extent past data should be ignored when computing the current candidate hidden state. A reset gate close to 0 means "mostly ignore the past when forming the new candidate value"; close to 1 means "keep using the past."
- **Update gate:** Functions similarly to the combination of an LSTM's input gate and forget gate — it determines whether information is **retained or discarded** as the hidden state moves from one time step to the next.
- The **current hidden state** `ht` is computed by taking the **Hadamard product** (i.e., element-wise multiplication) of the update gate's values and the previous hidden-state vector `ht-1`, combined with the candidate hidden state produced using the reset gate. In simple terms: the update gate acts like a dial that blends "how much of the old memory to keep" with "how much of the newly computed candidate memory to use."

**GRU vs. LSTM in one line:** LSTM uses three gates and a separate cell state for finer-grained control at the cost of more parameters; GRU uses two gates and no separate cell state, giving a lighter, faster-to-train model that often performs comparably.

---

## Introduction to Hybrid Modeling

### What Is Hybrid Modeling?

**Hybrid modeling** is the practice of employing two different neural network models and merging them to accomplish a sequence of tasks that neither model could handle as well alone. One of the best-known hybrid implementations is the **Convolutional Recurrent Neural Network (CRNN)**, which merges:

- A **CNN (Convolutional Neural Network)** — excellent at *spatial* analysis, i.e., extracting features from images (edges, shapes, textures).
- An **RNN** — excellent at *temporal* analysis, i.e., finding links between a sequence of extracted features over time that influence the final output.

By merging the two networks, the resulting hybrid model can learn patterns in sequential data (such as video) that require **both** spatial understanding within each frame **and** temporal understanding across frames, forming more accurate predictions than either network could produce on its own.

### Hybrid Modeling Example: Predicting the Next Handwritten Digit

Consider a model that must predict the next digit in a sequence of **handwritten** digit images, given the input `<1, 2, 4, 8, ...>` (note these are pictures of digits, not just numeric values, so plain numeric pattern-recognition will not work — the model must *see* each digit image before it can reason about the sequence).

The hybrid CRNN model performs the following steps:

1. It **slices the image of the digits into numerous segments**, one per digit in the sequence.
2. The **CNN** first extracts the essential visual features of each digit segment (its shape, strokes, curves) — this is the spatial part.
3. Those extracted features are then passed into the **RNN**, which recursively analyzes each feature while taking into account the previous inputs in the sequence — this is the temporal part (recognizing, for example, that the sequence `1, 2, 4, 8` is doubling each time).
4. The algorithm decodes the combined output, and the model predicts **16** as the next digit in the sequence (continuing the doubling pattern `1 → 2 → 4 → 8 → 16`).

This example nicely shows the division of labor in a CRNN: the CNN answers "what digit is drawn in this image?" while the RNN answers "given the sequence of digits so far, what comes next?"

---

## Applications of CRNN

### Video Classification Using CRNN

A **video** is fundamentally a series of images (frames) played in sequence, which makes it a natural fit for a CRNN hybrid model. The pipeline works as follows:

```
Video → Extract frames → CNN extracts important features (spatial)
                                     ↓
                         RNN performs temporal analysis
              (uses previous information to influence output)
                                     ↓
                                  Output
```

Step by step:

1. **Extract frames** from the video and pass each frame to the **CNN**, which extracts the essential spatial features present in that individual frame (objects, shapes, motion blur, etc.).
2. **Feed the extracted features to the RNN**, which analyzes them **sequentially**, considering the features from previous frames to find links between them (e.g., a ball moving left to right across consecutive frames) that influence the overall classification output (e.g., "this video shows a soccer match").

This is exactly the same pattern used in the handwritten-digit example above, just applied to real-world video frames instead of digit-image segments — CNN handles "what's in this single frame," RNN handles "how do the frames relate to each other over time."

### Assisted Practice: 11.11 — Video Classification Using Hybrid Model

> This section pairs with a hands-on notebook exercise ("11.11_Video Classification Using Hybrid Model") in which learners implement video classification using the CRNN hybrid model described above. Refer to the course's Reference Material section to download the notebook file.

---

## Key Takeaways

- A **sequence modeling** program can model, interpret, and predict various types of sequential data (text, audio, video, time series, and more).
- The **recurrent neural network** is a state-of-the-art algorithm that adds information from the recent past to the present, allowing it to make more precise predictions than models without memory.
- A recurrent neural network has **four types of architecture**: one-to-one, one-to-many, many-to-one, and many-to-many — chosen based on how many inputs and outputs the task requires.
- **Hybrid modeling** refers to employing two different neural network models (such as a CNN and an RNN, forming a CRNN) and merging them to achieve a sequence of tasks that need both spatial and temporal understanding.
- **LSTM** and **GRU** are gated RNN variants introduced specifically to solve the vanishing/exploding gradient problem that limits plain RNNs' ability to learn long-term dependencies — LSTM uses three gates and a separate cell state, while GRU uses two gates and no separate cell state for a lighter architecture.

---

## Knowledge Check (From Slides)

**1. What is sequential modeling?**

- **A.** A process used to analyze a series of output values to generate a sequence of input values
- **B.** A process used to analyze a series of output values to generate a sequence of output values
- **C.** A process used to analyze a series of input values to generate a sequence of input values
- **D.** A process used to analyze a series of input values to generate a sequence of values

**Correct answer: D.** Sequential modeling is a process used to generate a sequence of values by analyzing a series of input values.

**2. Which neural network model is mostly used for spatial analysis, such as extracting essential features from an image?**

- **A.** Recurrent neural network
- **B.** Convolutional neural network
- **C.** Dense neural network
- **D.** None of the above

**Correct answer: B.** The convolutional neural network (CNN) is mostly used for spatial analysis, such as extracting essential features from an image (RNNs, by contrast, specialize in temporal/sequential analysis).

---

## 📝 Practice Questions

### Multiple Choice

**Q1.** What is the primary limitation of feedforward neural networks (FNNs) that RNNs were designed to overcome?

- **A.** FNNs cannot classify images
- **B.** FNNs have too many parameters
- **C.** FNNs cannot retain memory of previous inputs when processing sequential data
- **D.** FNNs cannot be trained with backpropagation

**Q2.** In the RNN hidden-state update equation `ht = tanh(Whh·ht-1 + Wxh·Xt + bh + bx)`, what does the term `Whh·ht-1` represent?

- **A.** The influence of the current input on the output
- **B.** The influence of the previous hidden state on the current hidden state
- **C.** The bias term for the output layer
- **D.** The loss function used in training

**Q3.** Which RNN architecture would be most appropriate for classifying the overall sentiment (positive/negative) of an entire movie review given word by word?

- **A.** One-to-one
- **B.** One-to-many
- **C.** Many-to-one
- **D.** Many-to-many

**Q4.** Which RNN architecture would best suit a machine translation task where an input sentence in one language produces an output sentence in another language of potentially different length?

- **A.** One-to-one
- **B.** One-to-many
- **C.** Many-to-one
- **D.** Many-to-many (encoder-decoder)

**Q5.** What algorithm is used to compute weight updates in an RNN during training, accounting for the fact that the same weights are reused across time steps?

- **A.** Backpropagation Through Time (BPTT)
- **B.** K-means clustering
- **C.** Principal Component Analysis (PCA)
- **D.** Random forest boosting

**Q6.** Which of the following is NOT one of the three gates in a standard LSTM cell?

- **A.** Forget gate
- **B.** Input gate
- **C.** Reset gate
- **D.** Output gate

**Q7.** What new element does an LSTM maintain, in addition to the hidden state, that allows it to retain long-term dependencies?

- **A.** A convolution kernel
- **B.** A cell state
- **C.** A softmax layer
- **D.** An embedding matrix

**Q8.** Compared to an LSTM, a GRU is generally characterized by:

- **A.** More gates and a separate cell state, making it more accurate in all cases
- **B.** Fewer gates (reset and update) and no separate cell state, giving a simpler architecture
- **C.** No gating mechanism at all
- **D.** Being usable only for image data, not sequences

**Q9.** In a CRNN (hybrid CNN + RNN) used for video classification, what is the role of the CNN component?

- **A.** Performing temporal analysis across frames
- **B.** Extracting spatial features from each individual frame
- **C.** Generating the final class label directly from raw video bytes
- **D.** Storing the long-term cell state

**Q10.** Which problem, common during backpropagation in plain RNNs, causes gradients to shrink toward zero across many time steps, making it hard to learn long-range dependencies?

- **A.** Overfitting
- **B.** Vanishing gradient problem
- **C.** Exploding gradient problem
- **D.** Underflow error

### Short Answer

**Q11.** Explain, in your own words, what "memory" means in the context of an RNN, and why it matters for tasks like language modeling.

**Q12.** Describe the difference between the vanishing gradient problem and the exploding gradient problem in RNNs, and name one architecture designed to mitigate both.

**Q13.** Using the ABC Corporation business scenario as inspiration, describe a real-world example (different from the slides) of a many-to-one RNN application, and explain why many-to-one (rather than one-to-many) is the right architecture for it.

**Q14.** Walk through the five steps of RNN operation (initialization, input processing, hidden state update, output calculation, training) using a simple example of predicting the next word in the sentence "The cat sat on the ___."

### Answers

**A1. C.** FNNs process each input independently and have no mechanism to carry information from one input to the next, so they cannot model temporal/sequential dependencies. RNNs add a feedback loop (the hidden state) specifically to address this.

**A2. B.** `Whh` is the hidden-to-hidden weight matrix, and multiplying it by `ht-1` captures how much the previous time step's hidden state (memory) influences the new hidden state being computed.

**A3. C.** Many-to-one takes a sequence of inputs (the words of the review) and produces a single output (the overall sentiment label), which matches the "read the whole review, then classify it" nature of sentiment analysis.

**A4. D.** Machine translation needs a sequence in and a sequence out, where the two sequences can have different lengths — this is the classic encoder-decoder many-to-many pattern described in the lesson.

**A5. A.** Backpropagation Through Time (BPTT) unrolls the RNN across time steps and backpropagates the loss gradient through each of them, summing the gradient contributions for the shared weights.

**A6. C.** LSTM's three gates are forget, input, and output. The reset gate belongs to the GRU architecture, not the LSTM.

**A7. B.** The cell state (`Ct`) is the additional memory pathway LSTMs introduce alongside the hidden state, allowing information to be carried across many time steps with only selective modification via the gates.

**A8. B.** GRUs merge the input/forget gate functionality into a single update gate, add a reset gate, and drop the separate cell state used by LSTMs — resulting in a simpler model that is often just as effective, though not guaranteed to be "more accurate in all cases" (making option A incorrect).

**A9. B.** In a CRNN, the CNN handles the spatial part of the problem — extracting important visual features from each frame — while the RNN handles the temporal part, relating those features across the sequence of frames.

**A10. B.** The vanishing gradient problem occurs when repeated multiplication of small gradient factors during backpropagation through many time steps causes the gradient to shrink toward zero, preventing early time steps from being updated meaningfully. (Exploding gradients is the opposite issue, where the gradient grows unboundedly.)

**A11.** "Memory" in an RNN refers to the hidden state that is carried forward from one time step to the next, allowing the network's current output to be influenced by information seen at earlier time steps — not just the current input. This matters for language modeling because the meaning of a word or the correct next word often depends on words that appeared much earlier in the sentence or paragraph (e.g., resolving a pronoun to the noun it refers to), which a memoryless model could not do.

**A12.** The vanishing gradient problem happens when gradients shrink toward zero as they are backpropagated through many time steps (because they are repeatedly multiplied by factors less than 1), causing the network to effectively "forget" long-range dependencies. The exploding gradient problem is the opposite: gradients grow uncontrollably large (repeated multiplication by factors greater than 1), causing unstable, erratic weight updates. LSTM (and GRU) architectures, with their gating mechanisms and (for LSTM) separate cell state, were specifically designed to mitigate both problems by giving the network more controlled pathways for information and gradient flow.

**A13.** Example: A many-to-one RNN could take a sequence of a patient's daily vital-sign readings over a week (heart rate, blood pressure, temperature, etc., one reading per day) and output a single prediction — e.g., "high risk" or "low risk" of a medical event in the next 24 hours. Many-to-one is correct here because the goal is to condense an entire sequence of past information into one final decision, rather than to generate a new sequence of outputs (which is what one-to-many or many-to-many would be used for).

**A14.** Using "The cat sat on the ___": (1) **Initialization** — the hidden state starts as a zero vector before any words are read. (2) **Input processing** — each word ("The," "cat," "sat," "on," "the") is fed in one at a time as `Xt`, combined with the previous hidden state `ht-1` via the weighted sum `at = Wxh·Xt + Whh·ht-1 + bh`. (3) **Hidden state update** — each combined value is passed through `tanh` to produce the new hidden state `ht`, which now encodes information about all words seen so far (e.g., that the sentence is about a cat sitting on something). (4) **Output calculation** — after processing "the," the network computes `Yt = Why·ht + by` and applies a softmax to get a probability distribution over possible next words (e.g., "mat," "chair," "roof"), picking the most likely one. (5) **Training** — during training, the predicted next word is compared to the actual next word in labeled training sentences, the loss is computed, and BPTT updates all the shared weights (`Wxh`, `Whh`, `Why`) to make future predictions more accurate.
