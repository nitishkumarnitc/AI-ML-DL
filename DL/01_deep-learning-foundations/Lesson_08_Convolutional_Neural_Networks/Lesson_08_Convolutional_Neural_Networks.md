# Convolutional Neural Networks

*Deep Learning with Keras and TensorFlow — Lesson 08 Study Notes*

## Learning Objectives

By the end of this lesson, you will be able to:

- Interpret the structure and functionality of various convolutional neural network (CNN) architectures.
- Implement convolutional and pooling layers to extract significant features from images in a neural network.
- Apply advanced CNN architectures, such as ResNet, to solve complex image recognition problems.
- Utilize TensorBoard to monitor, analyze, and optimize the performance of convolutional neural networks throughout the training process.

## Business Scenario

A startup is building an image-recognition system to aid medical diagnosis through medical imaging. The team applies convolutional neural network (CNN) algorithms, training their models to identify medical conditions from X-rays and CT scans. They use **TensorBoard** to visualize model performance and iterate on their design. While searching for the best feature extractors for X-ray/CT images, they experiment with several classic CNN filters — horizontal and vertical **Sobel** filters, **blur** filters, and **outline** filters — to see which highlights the diagnostically relevant structures most clearly. To push accuracy further, they are also considering adopting a **Residual Neural Network (ResNet)** architecture, which can go far deeper than a plain CNN without degrading in accuracy.

This scenario threads through the whole lesson: image representation → convolution → filters → pooling → full CNN architecture → ResNet → monitoring with TensorBoard.

---

## 1. Introduction to CNN

### 1.1 What Is a CNN?

A **Convolutional Neural Network (CNN)** is a deep learning model purpose-built for analyzing visual data. Instead of treating an image as an unstructured list of numbers (as a plain feed-forward network would), a CNN exploits the *spatial* structure of images — the fact that nearby pixels are related — using **convolutional** and **pooling** layers to progressively extract low-level features (edges, corners) and combine them into higher-level patterns (shapes, objects, faces). Its design is loosely inspired by the organization of the animal **visual cortex**, where different groups of neurons respond to small, overlapping regions of the visual field. This biological inspiration, combined with efficient weight-sharing, is why CNNs have become the dominant architecture in computer vision.

### 1.2 Advantages of CNN

| # | Advantage | Why it matters |
|---|-----------|-----------------|
| 1 | **Automatic feature detection** | CNNs learn which features (edges, textures, shapes) matter directly from data, removing the need for hand-crafted feature engineering that older computer-vision pipelines required. |
| 2 | **Higher accuracy on images than feed-forward networks** | Because convolution layers preserve spatial relationships between pixels, CNNs pick up on local patterns (like the corner of an eye or the edge of a wheel) that a fully-connected network would struggle to learn efficiently. |
| 3 | **Better results than generic ML techniques** | Compared to traditional machine-learning approaches (e.g., SVMs on hand-crafted features), CNNs generally achieve more accurate results on vision tasks because representation learning and classification happen jointly, end-to-end. |

### 1.3 Disadvantages of CNN

| # | Disadvantage | Explanation |
|---|---------------|--------------|
| 1 | **High computational requirements** | Convolution across many channels and layers involves a large number of multiply-add operations, which typically requires GPUs/TPUs for practical training times. |
| 2 | **Needs large amounts of data and compute** | To learn good general-purpose filters, CNNs typically need large labeled datasets and significant training time/hardware. |
| 3 | **No explicit encoding of position/orientation** | A standard CNN with pooling is largely *translation invariant* — it can recognize an object no matter where it appears, but it does not explicitly track *where* it is or *how it is rotated/oriented* in the image (this is one motivation behind architectures like Capsule Networks). |

### 1.4 CNN Applications

CNNs are the backbone of most modern computer vision systems, including:

- **Industrial defect/anomaly detection** — e.g., detecting misplaced or missing tools on a factory floor from a camera feed.
- **Medical imaging** — e.g., detecting pulmonary fibrosis by feeding a CNN a large dataset of patients' lung images so it can learn to spot scarring in lung tissue.
- **Image classification** — assigning a label (cat, dog, tumor, no tumor, etc.) to an entire image.
- **Face recognition** — identifying or verifying a person's identity from a photo.
- **Object detection** — locating and classifying multiple objects within a single image (bounding boxes + labels).

In each of these, the CNN's job is the same at its core: use learned filters to extract features from the raw pixels, then use those features to make a decision.

### 1.5 Why Not Just Use a Feed-Forward Network (FFN)?

Feed-forward networks require the input to be a flat vector, so an image must first be **flattened**. Consider a dataset of 60,000 images, each of shape `(28, 28, 3)` (height × width × color channels):

- Flattening one image gives a vector of length `28 × 28 × 3 = 2,352`. That's already a lot of input weights for the very first layer.
- Now imagine higher-resolution images of shape `(1000, 1000, 3)`. Flattening gives `1000 × 1000 × 3 = 3,000,000` inputs. A fully-connected first layer with even a modest number of neurons would need billions of parameters — computationally infeasible and highly prone to overfitting.
- Flattening also **throws away spatial structure**: a pixel that used to be next to another pixel is now just "some other position in a long vector," so the network has to relearn spatial relationships from scratch, inefficiently.

CNNs were introduced specifically to avoid this. A concrete example from the slides: an image of shape `(400, 400, 3)` would need `400 × 400 × 3 = 480,000` input neurons if flattened directly into an FFN. After passing through a stack of convolution (and pooling) layers, the same information can be compressed down to a tensor as small as `1 × 1 × 3` — meaning the fully-connected part of the network at the end only needs **3** input neurons instead of 480,000. Convolution performs this dimensionality reduction while *preserving* the characteristics that matter for classification, rather than throwing them away like naive flattening would.

---

## 2. Getting Started with Image Data

### 2.1 Image Data Shape

A digital image is represented as a 3-dimensional array with the shape:

```
(height, width, channels)
```

For example, `(400, 400, 3)` means:
- `400` — the image's **height** in pixels.
- `400` — the image's **width** in pixels.
- `3` — the number of **channels** (in this case, Red, Green, and Blue).

### 2.2 Color Channels

A color image typically has three channels — **R**ed, **G**reen, and **B**lue (RGB) — that are combined to produce the final color you see. Each channel is itself a 2D grid of intensity values ranging from **0 to 255**:

- `0` means the complete absence of that color's contribution at that pixel.
- `255` means the maximum possible intensity of that color at that pixel.

Mixing different intensities of R, G, and B at each pixel location produces the full range of visible colors (e.g., high R + low G + low B looks reddish; high R + high G + high B looks white).

### 2.3 CNN on Image Data

When a CNN operates on image data, the **convolution operation** performs feature extraction: it identifies and isolates characteristics such as edges, textures, and shapes within the image. Over successive layers, the network builds up a hierarchy of features — early layers detect simple things like edges, and deeper layers combine those into more complex, task-relevant patterns. This lets the CNN "extract all the necessary information" from raw pixels that is useful for training the downstream classifier.

---

## 3. The Convolution Operation

### 3.1 What Is Convolution?

**Convolution** is the core mathematical operation in a CNN. It works by sliding a small matrix, called a **filter** (or **kernel**), across the input image and, at every position, computing the sum of the element-wise products between the filter's weights and the pixel values currently underneath it (essentially a dot product between the flattened filter and the flattened image patch). The filter's weights are **learned automatically during training** — the network is not told in advance what edges or textures to look for; it discovers the most useful filters on its own by minimizing the loss function.

A filter can be tiny — commonly 3×3 or 5×5 — yet by sliding it over every possible position in the image, it can detect a specific pattern (such as a vertical edge) anywhere it occurs.

### 3.2 Worked Example: Convolving a 4×4 Image with a 2×2 Filter

Consider a single-channel 4×4 image:

```
155   67  111   45
 32  254  123   67
 54   55   32   89
100  220  255   56
```

And a 2×2 filter (kernel):

```
0.4  0.8
0.3  0.2
```

To convolve, place the filter over the top-left 2×2 patch of the image, multiply element-by-element, and sum the results:

```
155 × 0.4 + 67 × 0.8 + 32 × 0.3 + 254 × 0.2
= 62.0 + 53.6 + 9.6 + 50.8
= 176.0
```

That single number, `176.0`, becomes the top-left pixel of the **output feature map**. The filter then slides one pixel to the right (this "one pixel" shift is the **stride**, discussed below) and the same multiply-and-sum is repeated for the next patch, and so on, until the filter has swept across the entire image. Because a 2×2 filter fits `4 − 2 + 1 = 3` times across a dimension of length 4, sliding it over the full 4×4 image produces a smaller **3×3 feature map**:

```
176.0   216.4   130.7
243.2   222.9   130.2
139.6   164.6   171.7
```

Each value in this output tells you *how strongly the pattern encoded by the filter matched* the corresponding patch of the original image — this output grid is called the **feature map**. Notice the output (3×3) is smaller than the input (4×4); this natural shrinkage is why techniques like padding (Section 4.3) exist.

### 3.3 General Output-Size Formula

If an input has size `n × n`, a filter has size `f × f`, the stride is `s`, and no padding is used, the output feature map size is:

```
output_size = ⌊(n − f) / s⌋ + 1
```

In the worked example above: `n = 4`, `f = 2`, `s = 1` → `(4 − 2)/1 + 1 = 3`, matching the 3×3 output.

---

## 4. CNN Architecture

### 4.1 Overall Pipeline

A CNN combines the classic **backpropagation** training algorithm with a stack of specialized layer types — convolution, pooling, and fully connected layers — arranged so the network can *automatically and adaptively learn spatial hierarchies* directly from the input data. Conceptually, the pipeline looks like:

```
Input Image  →  [Convolution → Pooling] × N  →  Flatten  →  Fully Connected  →  Output
                └──────── Feature Extraction ────────┘      └──── Classification ────┘
```

Early convolution/pooling blocks act as **feature extractors** (finding edges, textures, then shapes, then object parts), while the fully connected layers at the end act as the **classifier**, mapping the extracted high-level features to final class scores.

### 4.2 The Five Core Building Blocks

A typical CNN architecture is composed of the following layers, along with the **padding** and **stride** parameters that control how convolution/pooling slide over the input:

1. **Convolution layer** — applies learned filters to extract features (edges, textures, shapes) and produces feature maps.
2. **Pooling layer** — downsamples feature maps, shrinking their spatial size to reduce computation and add a degree of robustness to small shifts in the input.
3. **Fully connected layer** — a standard feed-forward layer that takes the flattened, high-level features and starts combining them for the final decision.
4. **Activation function** — introduces non-linearity so the network can learn complex, non-linear relationships instead of being limited to linear transformations.
5. **Output layer** — produces the final prediction (e.g., class probabilities).

#### Convolution Layer (in depth)

The convolution layer performs the convolution operation described in Section 3 on the input image (or the previous layer's feature map) using one or more filters. For every patch the filter visits, it computes the sum of the products between filter weights and the underlying pixel values, producing one entry of the output **feature map**. Multiple filters can be applied in the same layer, each specializing in detecting a different pattern, and each producing its own feature map.

#### Pooling Layer (in depth)

Also known as the **downsampling layer**, pooling reduces the spatial size (height × width) of feature maps, which speeds up computation in later layers and reduces the number of parameters the network must learn. It does this by sliding a small window (e.g., 2×2) over the feature map and summarizing each window with a single number. The two most common variants:

| Type | What it computes | Typical effect |
|------|-------------------|-----------------|
| **Max pooling** | The **maximum** value within each patch. | Keeps the strongest activation in each region; tends to preserve the brightest/most salient pixels, which is why it works well on images with dark backgrounds and bright objects/edges of interest. |
| **Average pooling** | The **average** value within each patch. | Smooths the feature map, softening harsh edges; useful when fine edge detail is not critical and a smoother summary is preferred. |

**Max-pooling worked example.** Using the same 4×4 image as before and a 2×2 max-pooling window with **stride 1** (i.e., the window moves one pixel at a time, so windows overlap):

```
Input:                Output (each cell = max of the 2×2 patch it covers):
155   67  111   45     254  254  123
 32  254  123   67  →  254  254  123
 54   55   32   89     220  255  255
100  220  255   56
```

For instance, the top-left output cell, `254`, is the maximum of the patch `{155, 67, 32, 254}`.

**Average-pooling worked example.** Same input, same 2×2 window, stride 1:

```
Input:                 Output (each cell = average of the 2×2 patch it covers):
155   67  111   45     127.00  138.75   86.50
 32  254  123   67  →   98.75  116.00   77.75
 54   55   32   89     107.25  140.50  108.00
100  220  255   56
```

For instance, the top-left output cell, `127.00`, is the average of `{155, 67, 32, 254} = 508 / 4 = 127`.

#### Fully Connected (FC) Layer

Once the convolution/pooling stack has produced a small, information-dense feature map, that feature map is **flattened** into a 1D vector and fed into one or more fully connected (feed-forward) layers — the same kind of layer used in a classic multilayer perceptron. This is where the network combines high-level features into a decision. FC layers form the final stage of the network, right before the output layer.

#### Activation Function

The activation function computes a weighted sum of its inputs, adds a bias term, and decides whether/how strongly a neuron should "fire." Its key role is to introduce **non-linearity**, without which stacking many linear layers would collapse mathematically into a single linear layer — incapable of modeling the complex patterns real-world images require. Common activation functions by network type:

| Network Type | Commonly Used Activation(s) |
|---------------|------------------------------|
| Multilayer Perceptron (MLP) | Sigmoid, Tanh |
| CNN | ReLU |
| RNN | ReLU / Tanh |

**ReLU** (Rectified Linear Unit) is the default choice in modern CNNs because it is computationally cheap and helps mitigate the vanishing-gradient problem compared to sigmoid/tanh.

#### Output Layer

The output layer produces the network's final predictions or classifications from the features extracted by all previous layers. It typically consists of one or more fully connected layers followed by an activation function such as **softmax** (for multi-class classification, converting raw scores into a probability distribution over classes). The weights here — like everywhere else in the network — are learned via **backpropagation**, adjusting to minimize the training loss and improve prediction accuracy.

### 4.3 Architecture Parameters: Stride and Padding

#### Stride

**Stride** controls how many pixels the filter (in convolution) or pooling window moves at each step. It directly affects:
- The **size of the output** feature map (larger stride → smaller output).
- The **computational cost** (larger stride → fewer positions to compute → faster, but coarser).
- The **amount of detail retained** (larger stride → more information potentially skipped between positions).

For example, with **stride = 1**, a filter starting at the top-left corner of the image (covering, say, columns 0–1) moves one pixel to the right for its next application (now covering columns 1–2) — a dense, overlapping sweep. With **stride = 2**, the same filter instead jumps two pixels to the right (covering columns 2–3 next), skipping over column 1 entirely — a sparser, non-overlapping (or less-overlapping) sweep that produces a smaller output and requires fewer computations, at the cost of potentially missing finer detail between the skipped positions.

#### Padding

**Padding** adds extra values — typically **zeros** — symmetrically around the border of the input matrix before convolution. Its purposes are:
- To **counteract the natural shrinkage** that convolution causes (recall the 4×4 → 3×3 shrinkage in the worked example above); with the right amount of padding, the output can be made the *same* size as the input (this is often called **"same" padding**, versus **"valid" padding**, which uses no padding and allows the output to shrink).
- To **improve accuracy**, since without padding, pixels near the border are used in far fewer convolution computations than pixels near the center, meaning border information is under-represented. Padding gives border pixels more "coverage" by the filter.

Visually, padding surrounds the original pixel grid with a border of zeros; the filter can then be centered on true edge pixels without running off the image.

---

## 5. ResNet (Residual Neural Network)

### 5.1 Why ResNet?

**ResNet** is a CNN architecture designed specifically to make it possible to train *very* deep networks — potentially with **thousands of convolutional layers** — something that was previously impractical because very deep plain CNNs suffer from the **vanishing gradient problem**: as gradients are backpropagated through many layers, they can shrink toward zero, so early layers barely update and training stalls or even performs worse than a shallower network.

### 5.2 Residual (Skip) Connections

ResNet's key innovation is the **residual connection**, also called a **skip connection**. Instead of forcing each stacked block of layers to learn a completely new representation from scratch, a skip connection carries the *input* of a block forward and adds it directly to the block's *output*:

```
        ┌─────────────────────────────┐
   x ───┤                             │
        │  Weight layer → ReLU →      ├──▶ (+) ──▶ ReLU ──▶  F(x) + x
        │  Weight layer               │     ▲
        │                             │     │
        └─────────────────────────────┘     │
   x ───────────────────────────────────────┘   (identity / skip connection)
```

Here, if `F(x)` is what the stacked weight layers compute, the block's final output is `F(x) + x` rather than just `F(x)`. This "identity mapping" makes it much easier for the network to learn: in the simplest case, a block can learn to output `F(x) ≈ 0` and let the identity shortcut pass the input straight through, meaning adding more layers can never make the network *worse* than a shallower version — it can always fall back to doing nothing extra. This directly combats the vanishing-gradient problem because gradients have a direct, unimpeded path (the skip connection) back to earlier layers during backpropagation.

### 5.3 ResNet Variants

ResNet comes in several standard sizes, named after their total layer count:

- **ResNet18**
- **ResNet34**
- **ResNet50**
- **ResNet101**
- **ResNet152**

### 5.4 ResNet50 in Detail

**ResNet50** has 50 layers in total: **48 convolutional layers**, **1 max-pooling layer**, and **1 average-pooling layer**. It won the **ILSVRC** (ImageNet Large Scale Visual Recognition Challenge) image classification competition in **2015**.

Its layers are organized into **5 stages/blocks**, each containing a set of residual blocks. Every residual block in ResNet50 is built from three stacked **3×3 convolution layers**. Stacking these residual blocks across stages lets the network preserve and build upon information learned in earlier layers, resulting in richer, more robust representations than a comparably deep plain CNN could achieve.

**High-level ResNet50 architecture flow:**

```
INPUT
  → CONV → BATCH NORM → ReLU → MAX-POOL           (stem)
  → STAGE 1: CONV BLOCK → ID BLOCK ×2
  → STAGE 2: CONV BLOCK → ID BLOCK ×3
  → STAGE 3: CONV BLOCK → ID BLOCK ×5
  → STAGE 4: CONV BLOCK → ID BLOCK ×2
  → STAGE 5: AVG POOL → FLATTEN → FULLY CONNECTED
  → OUTPUT
```

("CONV BLOCK" changes the tensor's dimensions, typically at the start of a stage; "ID BLOCK" — identity block — preserves dimensions and is repeated multiple times within a stage to add depth without changing shape.)

### 5.5 Use Cases of ResNet

Because of its depth and residual connections, ResNet can tackle almost any computer vision problem effectively, including:

- **Emotion recognition** — inferring human emotional states from facial images to understand behavior.
- **Medical imaging** — detecting brain tumors from patients' brain MRI scan images.
- **Game AI** — recognizing player activity/behavior in games in order to build bots that provide an appropriately challenging opponent.

### 5.6 Other Well-Known CNN Architectures

Beyond ResNet, several other CNN architectures are widely used and referenced in the field:

- **VGG16** — a deep but architecturally simple network using stacks of small 3×3 convolutions.
- **AlexNet** — one of the early breakthrough deep CNNs that popularized deep learning for image classification (ILSVRC 2012 winner).
- **GoogLeNet (Inception)** — introduced the "Inception module," which applies multiple filter sizes in parallel within the same layer to capture features at multiple scales efficiently.

---

## 6. Filters in CNN

### 6.1 What Filters Do

**Filters** (kernels) are small matrices designed to detect specific spatial patterns or features in an image — such as edges, arches, and diagonals — by responding strongly to particular changes in pixel intensity. The convolution operation (sum of the products of filter weights and image pixel values) is how a filter's response at each location is computed. Different filters, applied to the same image, will highlight entirely different aspects of it — this is why a filter is sometimes called a **feature detector**.

### 6.2 Common Hand-Crafted CNN Filters

While a trained CNN *learns* its own filters automatically, it is instructive to study classic, hand-designed filters used in traditional image processing, since a CNN's learned filters often converge to something conceptually similar (especially in early layers):

| Filter | Typical 3×3 Matrix | Effect |
|--------|--------------------|--------|
| **Horizontal Sobel** | `[-1 -2 -1; 0 0 0; 1 2 1]` | Emphasizes **horizontal edges** by detecting changes in pixel intensity along the vertical direction (i.e., comparing rows above vs. below). |
| **Vertical Sobel** | `[-1 0 1; -2 0 2; -1 0 1]` | Emphasizes **vertical edges** by detecting changes in pixel intensity along the horizontal direction (i.e., comparing columns left vs. right). |
| **Blur** | `[0.0625 0.125 0.0625; 0.125 0.25 0.125; 0.0625 0.125 0.0625]` | Smooths/softens the image, reducing noise and fine detail — useful as a preprocessing step to make a model less sensitive to minor pixel-level variations. All weights are positive and sum to 1, so it acts as a weighted local average. |
| **Outline** | `[-1 -1 -1; -1 8 -1; -1 -1 -1]` | Highlights the **boundary/outline** of objects: the strong positive center weight (8) combined with negative surrounding weights makes the filter respond strongly wherever a pixel differs sharply from its neighbors in every direction, i.e., at edges/boundaries. |

Intuition for the Sobel filters: the horizontal Sobel filter has negative weights in the top row and positive weights in the bottom row, so it produces a large response wherever intensity changes sharply from top to bottom (a horizontal edge). The vertical Sobel filter mirrors this with negative weights on the left and positive weights on the right, responding to sharp left-to-right intensity changes (a vertical edge).

The blur filter's positive, symmetric weights (summing to 1) mean the output pixel is essentially a weighted average of the 3×3 neighborhood, which naturally smooths out noise and small variations. The outline filter, by contrast, is a form of Laplacian-like edge detector: flat, uniform regions produce a near-zero response (since center × 8 roughly cancels the 8 negative neighbors when they're similar in value), while regions with a sharp local contrast — an edge or outline — produce a large non-zero response.

---

## 7. Working of CNNs (Putting It All Together)

CNNs build up increasingly abstract and comprehensive representations of an image by **stacking convolutional layers**. This is a form of **hierarchical feature learning**, echoing how the human visual system is believed to process images — early visual areas detect simple features (edges, contrast), and later areas combine them into complex object recognition. The specific convolutions (filter sizes, number of filters, depths) that are useful depend entirely on the problem being solved and which features are relevant to it.

Crucially, in a real CNN, each filter's optimal weight values are **learned automatically during training**, not hand-specified — this is in contrast to the classic Sobel/blur/outline filters in Section 6, which were manually designed. In much the same way, the human visual cortex is believed to develop its feature-detecting "filters" through learning and experience, not innate hard-coding.

**Example end-to-end architecture** (a small digit-classification CNN, similar to classic LeNet-style networks), illustrating how tensor shapes evolve through the network:

```
INPUT (28×28×1, grayscale digit image)
   │
   ▼
Conv_1: Convolution, 5×5 kernel, valid padding   → n1 channels, (24×24×n1)
   │
   ▼
Max-pooling (2×2)                                 → n1 channels, (12×12×n1)
   │
   ▼
Conv_2: Convolution, 5×5 kernel, valid padding    → n2 channels, (8×8×n2)
   │
   ▼
Max-pooling (2×2)                                 → n2 channels, (4×4×n2)
   │
   ▼
Fc_3: Fully-connected layer + ReLU activation
   │
   ▼
Fc_4: Fully-connected layer
   │
   ▼
OUTPUT (with dropout) → 10-way classification (digits 0–9)
```

Notice the pattern: each convolution + valid padding step shrinks the spatial dimensions (28→24→12→8→4) while typically *increasing* the number of channels (n1 → n2), trading spatial resolution for a richer set of learned features. This is a very common design pattern across CNN architectures — get spatially smaller but "deeper" (more channels) as you go through the network.

*(Image reference in source slides: Shah, Y., Shah, P., Patel, M., Khamkar, C., & Kanani, P. (2020). Deep Learning model-based Multimedia forgery detection. 2020 Fourth International Conference on I-SMAC. https://doi.org/10.1109/i-smac49090.2020.9243530)*

---

## 8. The 2D Convolution Layer (Conv2D) in Detail

### 8.1 What Is Conv2D?

A **2D Convolution Layer**, commonly called **Conv2D**, is the fundamental building block used to process visual data (images or video frames) in a CNN. Central to it is the concept of the **receptive field**: the region of the input image that a given filter actually "looks at" as it's applied, i.e., the area of the input that influences a particular neuron's output in the resulting feature map. The filter/kernel used has a height and width that are usually much smaller than the full input image, and it slides ("convolves") over the entire image, one patch at a time.

### 8.2 Handling Multiple Color Channels

When the input has multiple channels (e.g., RGB), Conv2D filters extend across all three color channels — meaning a single filter is really a small 3D volume (height × width × 3), with **different learned weights for each channel**. The convolution computed at each spatial position sums the contributions from all channels together, and the individual per-channel convolutions are combined to produce the layer's single combined output value at that position. Filters are randomly initialized so that different filters start out different from one another and, through training, each filter learns to specialize in detecting a different aspect of the image (edges, colors, textures, etc.).

### 8.3 Multiple Filters Per Layer

A single Conv2D layer typically uses **many filters simultaneously**, not just one — because each filter can only detect one type of pattern, using multiple filters lets the layer detect many distinct features in parallel. Each filter produces its own **feature map**, and the collection of feature maps (one per filter) becomes the input volume passed to the next layer. So if a Conv2D layer uses, say, 32 filters, its output will have 32 channels — one feature map per filter.

### 8.4 Constraints of Conv2D

Despite being highly effective, Conv2D layers have real practical drawbacks:

- **Computational expense.** Large filters are expensive to slide across a whole image (each position requires many multiply-add operations), and stacking multiple such layers multiplies this cost further, since each layer must process the output of the previous one.
- **Trade-off when mitigating cost.** One way to reduce the compute burden is to shrink the filter size and/or increase the stride — but doing so also shrinks the filter's **effective receptive field** and the amount of contextual information it can capture at each step, potentially hurting the quality of learned features. This is a classic accuracy-vs-efficiency trade-off that architecture designers must balance (and is part of the motivation for techniques used in efficient architectures like Inception and ResNet's bottleneck blocks).

---

## 9. Pooling in CNN (Deeper Dive)

### 9.1 Pooling Mechanics

The pooling operation slides a small 2D filter/window over each spatial "slice" of the feature map (i.e., over height and width, independently for each channel), reducing the feature map's spatial size while retaining the most significant information within each window. In effect, pooling **summarizes** the features found within the region the window covers, rather than keeping every individual value.

### 9.2 Output Size Formula

For an input feature map of dimensions `nh × nw × nc` (height × width × channels), pooled with a filter of size `f` and stride `s`, the output dimensions are:

```
output_height  = ⌊(nh − f) / s⌋ + 1
output_width   = ⌊(nw − f) / s⌋ + 1
output_channels = nc     (pooling operates independently per channel — the channel count never changes)
```

A typical CNN architecture stacks multiple convolution + pooling layers in sequence, each shrinking the spatial dimensions while (usually) growing the channel dimension via convolution.

### 9.3 Why Use Pooling?

- **Reduces parameters and computation.** Smaller feature maps mean fewer values for later layers (especially fully connected ones) to process, directly cutting compute and memory needs.
- **Summarizes local features.** Rather than requiring the network to care about the *precise* position of a feature within a small region, pooling reports a summary (max or average) of that region.
- **Adds positional robustness.** Because pooling summarizes over a local neighborhood, the network becomes more resilient to small translations/shifts of features within the input image — an edge detected one pixel to the left or right will often still produce the same pooled output.

### 9.4 Types of Pooling Layers

1. **Max-pooling** — takes the maximum value within each window of the feature map. It highlights the strongest/ most prominent activation in each region, effectively asking "was this feature present anywhere in this patch, and how strongly?"

   *Worked example* — input `4×4`, filter `2×2`, stride `(2,2)` (non-overlapping):
   ```
   Input:                 Output:
   2 2 7 3                9 7
   9 4 6 1        →       8 6
   8 5 2 4
   3 1 2 6
   ```
   (Top-left patch `{2,2,9,4}` → max `9`; top-right patch `{7,3,6,1}` → max `7`; bottom-left patch `{8,5,3,1}` → max `8`; bottom-right patch `{2,4,2,6}` → max `6`.)

2. **Average pooling** — takes the average of the values within each window, giving a smoothed summary of the region rather than just the single strongest value.

   *Worked example* — same input, filter `2×2`, stride `(2,2)`:
   ```
   Input:                 Output:
   2 2 7 3                4.25 4.25
   9 4 6 1        →       4.25 3.5
   8 5 2 4
   3 1 2 6
   ```
   (Top-left patch average `= (2+2+9+4)/4 = 4.25`; bottom-right patch average `= (2+4+2+6)/4 = 3.5`.)

3. **Global pooling** — an extreme form of pooling that reduces an *entire* channel of the feature map down to a **single value**. A feature map of shape `nh × nw × nc` becomes `1 × 1 × nc` — equivalent to running a pooling filter whose size exactly matches the full height and width of the feature map (`f = nh = nw`). Global pooling can be either **global max-pooling** or **global average-pooling**, and is commonly used right before the final classification layer in modern architectures (replacing large fully connected layers and reducing overfitting/parameter count).

---

## 10. Introduction to TensorBoard

### 10.1 What Is TensorBoard?

**TensorBoard** is a web-based visualization tool for understanding, monitoring, and debugging machine learning models — including CNNs. It provides:

- Real-time monitoring of **training progress** (as training runs, you can watch metrics update live).
- Visualization of **model performance** (loss curves, accuracy curves, and other custom metrics).
- The ability to display **image, text, and audio data** logged during training/evaluation.
- An overall goal of **reducing the perceived complexity** of neural networks by turning raw numeric logs into intuitive charts and graphs.

### 10.2 Example Use Case

Consider building a classifier to distinguish between two types of concrete surface — **plain** vs. **marred** (damaged) — so that construction sites can automatically assess a structure's load-bearing/withstanding capacity, for instance to detect whether surfaces have been damaged by earthquakes or other natural disasters. TensorBoard would be used during training of this classifier to monitor how well the model is learning to separate the two classes.

### 10.3 Launching TensorBoard

TensorBoard is started from the command line:

```bash
tensorboard --logdir path_to_logdir
```

The `--logdir` argument tells TensorBoard which directory contains the logs that were written out during model training (e.g., loss/accuracy values, model graph definitions, histograms of weights, etc.). TensorBoard reads those logs and renders them in your browser.

### 10.4 The Five TensorBoard Dashboard Sections

| Section | What It Shows |
|---------|-----------------|
| **Scalars** | Graphs of scalar metrics over time/steps, such as training loss and accuracy — the classic "is my model improving" chart. |
| **Graphs** | A visual diagram of the model's architecture — how layers/operations are connected. |
| **Distributions** | The distribution of weight values along each layer, useful for spotting issues like dead neurons or exploding weights. |
| **Histograms** | Histogram plots (frequency counts) of values along each layer, giving another view onto weight/activation distributions over training. |
| **Time Series** | How the distribution of values in each layer changes over time/training steps. |

Together, these views let a practitioner thoroughly understand and debug a model under study — for example, spotting a layer whose weights have collapsed to zero, or noticing that validation loss has started climbing (overfitting) while training loss keeps falling.

---

## 11. Key Takeaways

- CNN is a widely used algorithm in computer vision, purpose-built to work with images and other grid-like data.
- The **convolution operation** is the sum of the products of filter values and the pixel values they overlap with at each position.
- The three essential layer types in a CNN are the **convolution layer**, the **pooling layer**, and the **fully connected layer**.
- **ResNet** is a CNN architecture, widely used in computer vision, that uses residual (skip) connections to enable training of very deep networks.
- Classic CNN filter types include the **horizontal Sobel**, **vertical Sobel**, **blur**, and **outline** filters.
- **Conv2D** filters extend across all color channels (e.g., R, G, B), and the individual per-channel convolutions are combined to produce the final output at each position.
- **TensorBoard** is an interface used to visualize, understand, and debug machine learning models during and after training.

---

## 12. Lesson-End Project: Image Classifier with CIFAR10 / Chars74k

**Problem statement:** Build a deep learning convolutional neural network to recognize characters using the **Chars74k** dataset.

**Objective:** Build a neural-network-based classification model to recognize characters, meeting these specifications:

- Use **four convolution layers**, each with a **3×3 kernel** and **ReLU** activation.
- Add a **maximum-pooling layer after every other convolution layer**.
- Add **two hidden (fully connected) layers with dropout** before the output layer.

This project applies essentially every concept from this lesson: convolution layers with a specific kernel size and activation, strategic placement of pooling layers to control feature-map shrinkage, and a fully connected classification head regularized with dropout to reduce overfitting.

---

## 13. Embedded Knowledge Checks (from the slides)

**1. What does the shape of an image data represent?**
- **A.** Height and depth of the image
- **B.** Width, depth, and brightness of the image
- **C.** Height, width, and brightness of the image
- **D.** Height, width, and channels of the image

*Correct answer: **D**. The shape of image data represents the height, width, and channels of the image, denoted as `(height, width, channels)`.*

**2. What does the convolution operation do in a CNN?**
- **A.** Subtracts the filter values from the pixel values in the image data
- **B.** Extracts all the necessary information from the image data
- **C.** Performs an addition operation on image data
- **D.** Flattens the image data

*Correct answer: **B**. In a CNN, the convolution operation extracts all the necessary information from the image data, which is helpful for training models.*

**3. What is the purpose of pooling layers in CNNs?**
- **A.** To increase the number of parameters to learn and the amount of computation in the network
- **B.** To reduce the feature map dimensions and amount of computation in the network
- **C.** To increase the feature map dimensions and amount of computation in the network
- **D.** To reduce the feature map dimensions and number of layers in the network

*Correct answer: **B**. Pooling layers reduce the feature map dimensions, which in turn helps reduce the number of parameters to learn and the amount of computation in the network.*

---

## 📝 Practice Questions

Test your understanding of this lesson with the following questions. Try to answer each one before checking the Answers section.

1. **(MCQ)** What is the primary purpose of a filter (kernel) in a CNN's convolution layer?
   - **A.** To randomly shuffle pixel values for data augmentation
   - **B.** To detect specific spatial patterns or features, such as edges, by computing a weighted sum of local pixel values
   - **C.** To permanently delete unimportant pixels from the image
   - **D.** To convert a grayscale image into an RGB image

2. **(MCQ)** An input image of shape `(6, 6, 1)` is convolved with a `3×3` filter, stride `1`, and no padding ("valid" padding). What is the shape of the resulting feature map?
   - **A.** `(6, 6, 1)`
   - **B.** `(4, 4, 1)`
   - **C.** `(3, 3, 1)`
   - **D.** `(9, 9, 1)`

3. **(Short answer)** Explain, in your own words, why flattening a large color image directly into a feed-forward network is problematic, and how a CNN avoids that problem.

4. **(MCQ)** Which of the following best describes "same" padding, as opposed to "valid" padding?
   - **A.** It removes border pixels before convolution so the output is smaller than the input.
   - **B.** It adds zeros around the input so that the output feature map has the same spatial dimensions as the input.
   - **C.** It doubles the stride so the output shrinks twice as fast.
   - **D.** It replaces the filter's weights with zeros.

5. **(Short answer)** A 2×2 max-pooling window with stride 2 is applied to the following 4×4 feature map. What is the resulting 2×2 output?
   ```
   1  3  2  4
   5  6  1  2
   7  8  9  0
   3  1  2  5
   ```

6. **(MCQ)** Which activation function is most commonly used in the hidden layers of modern CNNs, and why?
   - **A.** Sigmoid, because it is the fastest to compute
   - **B.** ReLU, because it is computationally cheap and helps reduce the vanishing-gradient problem
   - **C.** Softmax, because it normalizes every hidden layer's output into probabilities
   - **D.** Linear (identity), because CNNs do not need non-linearity

7. **(Short answer)** What is a "skip connection" (residual connection) in ResNet, and what specific training problem does it help solve?

8. **(MCQ)** Which of the following is NOT one of the classic hand-crafted CNN filters discussed in this lesson?
   - **A.** Horizontal Sobel filter
   - **B.** Outline filter
   - **C.** Rotation filter
   - **D.** Blur filter

9. **(Short answer)** Describe, step by step, how a 3×3 kernel "slides" over a 5×5 grayscale image when the stride is 1. How many total positions will the kernel visit (assume no padding)?

10. **(MCQ)** What is the key structural difference between max pooling and average pooling?
    - **A.** Max pooling only works on RGB images; average pooling only works on grayscale images
    - **B.** Max pooling takes the largest value in each window; average pooling takes the mean of the values in each window
    - **C.** Max pooling increases the size of the feature map; average pooling decreases it
    - **D.** Max pooling requires labeled data; average pooling does not

11. **(Short answer)** Why does a CNN typically increase the number of channels (filters) while decreasing the spatial (height × width) dimensions as data flows deeper into the network?

12. **(MCQ)** In ResNet50, how many layers total does the network have, and what is its most significant architectural feature?
    - **A.** 34 layers; global average pooling only
    - **B.** 50 layers; residual (skip) connections that add a block's input to its output
    - **C.** 16 layers; only fully connected layers
    - **D.** 152 layers; no convolution layers at all

13. **(Short answer)** What is "global pooling," and how does its output shape relate to its input shape?

14. **(MCQ)** Which statement about Conv2D filters operating on an RGB image is correct?
    - **A.** A single Conv2D filter can only look at one color channel at a time
    - **B.** Each Conv2D filter spans all input channels (e.g., R, G, and B), using separate weights per channel, and the per-channel results are summed to form one output value per position
    - **C.** RGB images must be converted to grayscale before any convolution can occur
    - **D.** Conv2D filters ignore color channels entirely and operate only on spatial coordinates

15. **(Short answer)** List the three essential layer types found in a basic CNN architecture and briefly state the role of each.

16. **(MCQ)** Why is TensorBoard useful when training a CNN?
    - **A.** It automatically increases the model's accuracy without any code changes
    - **B.** It provides visualizations (scalars, graphs, histograms, distributions, time series) that help monitor training progress and debug the model
    - **C.** It replaces the need for a validation dataset
    - **D.** It compiles the model into faster machine code

17. **(Short answer)** A colleague suggests removing all pooling layers from a CNN to "preserve more information." What trade-offs should they consider before doing this?

### Answers

1. **B.** A filter is a small learned matrix that produces a strong response wherever the pattern it encodes (an edge, texture, etc.) is present in the underlying image patch, via convolution's weighted sum/dot-product operation.

2. **B — `(4, 4, 1)`.** Using the formula `output = ⌊(n − f)/s⌋ + 1 = ⌊(6 − 3)/1⌋ + 1 = 4`, the resulting feature map has spatial size `4 × 4`, and since a single filter was used, the depth stays `1`.

3. **Sample answer:** Flattening a large color image (e.g., `1000×1000×3`) into a 1D vector for an FFN produces millions of input values, requiring an enormous number of weights in just the first layer — computationally very expensive and prone to overfitting. It also destroys spatial relationships between neighboring pixels, forcing the network to relearn spatial structure from an unordered list of numbers. A CNN avoids this by using small filters that slide over the image, preserving 2D spatial relationships, sharing weights across positions (far fewer parameters), and progressively compressing the image into a small but information-rich representation before any fully connected layer is used.

4. **B.** "Same" padding adds zeros around the border of the input so the convolution's output retains the same height and width as the input; "valid" padding uses no padding, letting the output shrink naturally.

5. **Answer:**
   ```
   6  4
   8  9
   ```
   Top-left patch `{1,3,5,6}` → max `6`; top-right patch `{2,4,1,2}` → max `4`; bottom-left patch `{7,8,3,1}` → max `8`; bottom-right patch `{9,0,2,5}` → max `9`.

6. **B.** ReLU (`f(x) = max(0, x)`) is cheap to compute (just a threshold at zero) and, unlike sigmoid/tanh, does not saturate for large positive inputs, which helps gradients flow better during backpropagation in deep networks.

7. **Sample answer:** A skip/residual connection adds a block's input `x` directly to its output, so the block computes `F(x) + x` instead of just `F(x)`. This gives gradients a direct path back to earlier layers during backpropagation, which helps combat the **vanishing gradient problem** that otherwise makes very deep plain CNNs difficult or impossible to train effectively.

8. **C — Rotation filter.** The lesson covers the horizontal Sobel, vertical Sobel, blur, and outline filters; a "rotation filter" is not one of the classic filters discussed.

9. **Sample answer:** With a 5×5 image, a 3×3 kernel, stride 1, and no padding, the kernel starts at the top-left corner (covering rows 0–2, columns 0–2), computes the weighted sum there, then shifts one column to the right and repeats, continuing until it reaches the right edge of that row (columns 2–4). It then drops down one row and resets to the left edge, repeating the same left-to-right sweep, until it has covered every valid position. Using the output-size formula `(n − f)/s + 1 = (5 − 3)/1 + 1 = 3`, the kernel visits a `3×3` grid of positions, i.e., **9 total positions**.

10. **B.** Max pooling reports the largest value found in each window (highlighting the strongest activation), while average pooling reports the mean of all values in the window (producing a smoother summary); both reduce spatial size in the same way but differ in *how* they summarize each window.

11. **Sample answer:** As spatial dimensions shrink (via pooling/strided convolution), the network can afford — and benefits from — representing the image with more distinct learned features per spatial location. Increasing the number of channels lets each layer capture a richer, more diverse set of patterns (edges, then combinations of edges, then parts, then objects) even as the "canvas" available to represent each individual feature map gets smaller; this trades raw spatial resolution for representational richness/depth as you move deeper into the network.

12. **B.** ResNet50 has 50 total layers (48 convolutional + 1 max-pool + 1 average-pool), organized into 5 stages of residual blocks, and its defining architectural feature is the residual/skip connection that adds a block's input to its output.

13. **Sample answer:** Global pooling reduces an entire `nh × nw` spatial slice of a feature map down to a single value per channel — so a feature map of shape `nh × nw × nc` becomes `1 × 1 × nc` after global pooling. It is equivalent to applying a pooling filter whose size exactly equals the feature map's full height and width. It can be implemented as global max-pooling (take the single largest value per channel) or global average-pooling (take the mean of all values per channel).

14. **B.** A Conv2D filter applied to an RGB image is really a small 3D volume (height × width × 3 channels) with independent weights per channel; at each spatial position, the layer computes the per-channel convolutions and sums them together to produce one combined output value, which then becomes one entry in that filter's feature map.

15. **Sample answer:** (1) **Convolution layer** — applies learned filters to extract features and produce feature maps; (2) **Pooling layer** — downsamples feature maps to reduce spatial size, computation, and parameter count while retaining important features; (3) **Fully connected layer** — takes the flattened, high-level features from the convolution/pooling stack and combines them to make the final classification decision.

16. **B.** TensorBoard's dashboards (Scalars, Graphs, Distributions, Histograms, Time Series) let practitioners watch training/validation metrics evolve, inspect the model's structure, and examine weight/activation distributions — all of which support monitoring progress and debugging problems like poor convergence or overfitting.

17. **Sample answer:** Removing pooling layers keeps feature maps larger, which does preserve more raw spatial detail and positional precision, but at the cost of: (a) significantly more parameters and computation in subsequent layers (especially fully connected ones), since feature maps stay large; (b) slower training and inference; (c) potential loss of the translation robustness pooling provides, meaning the model may become more sensitive to small shifts/noise in input position; and (d) a higher risk of overfitting due to the larger number of parameters relative to the amount of training data. In practice, many modern architectures reduce reliance on pooling by using strided convolutions instead, rather than removing downsampling altogether.
