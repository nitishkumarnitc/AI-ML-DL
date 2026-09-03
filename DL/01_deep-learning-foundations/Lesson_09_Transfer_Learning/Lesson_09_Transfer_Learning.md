# Transfer Learning
### Deep Learning with Keras and TensorFlow — Lesson 09

## Learning Objectives

By the end of this lesson, you will be able to:

- Understand the concept of transfer learning and differentiate between positive and negative transfer learning scenarios.
- Utilize transfer learning to achieve higher accuracy in specific deep learning applications with limited datasets.
- Implement a custom transfer learning model using pre-trained architectures and fine-tune it for specific tasks, such as image classification and object detection.
- Assess the factors to consider when selecting pre-trained models for different tasks.

---

## Business Scenario

A healthcare company wants to build a deep learning model that can detect rare diseases in medical images. Rare diseases are, by definition, rare — so the company only has a small number of labeled images to work with, and training a large convolutional network from scratch on such a small dataset would almost certainly overfit and perform poorly.

Instead of starting from zero, the company adopts **transfer learning**: it takes a model that was already trained on a large, related image-classification task, and adapts (fine-tunes) it to recognize the rare-disease patterns in medical scans. Because the pre-trained model already "knows" how to detect general visual features (edges, textures, shapes), it only needs to learn the specific patterns relevant to the new task. The result is a model that reaches higher accuracy than one trained from scratch, while using far less data, time, and compute.

This is not unique to healthcare — the same strategy (start from a model trained on a large, general dataset, then adapt it to a narrower, data-scarce problem) is used across industries whenever labeled data is expensive or scarce but a related pre-trained model already exists.

---

## Introduction to Transfer Learning

### What Is Transfer Learning?

Transfer learning is a deep learning technique in which a model that was developed and trained for one task is **reused as the starting point** for a model on a second, related task, instead of training a brand-new network from randomly initialized weights.

In practice, the early/middle layers of the pre-trained model — which have already learned general-purpose features — are kept largely as-is, while the **later layers** of the network are fine-tuned or adapted so that the model's output matches the requirements of the new task. For example, a network trained to classify thousands of everyday objects has already learned to detect edges, textures, shapes, and object parts; those low-level and mid-level features are broadly useful, so instead of re-learning them from scratch for a new task (say, classifying X-ray images), we reuse them and only retrain the final layers to make the new, task-specific decision.

### Key Aspects of Transfer Learning in Deep Learning Models

- **Reuse the pre-trained models** — Start from a network whose weights were learned on a large, general dataset (such as ImageNet) rather than initializing weights randomly.
- **Retrain the latter layers for new tasks** — Only the last few layers (often the classifier head) are retrained/fine-tuned so the network learns to map its existing feature representations onto the new task's labels.
- **Leverage learned features for a wide range of tasks** — The general features learned by the base model (edges, shapes, textures, and so on) transfer well to many downstream tasks, including but not limited to object recognition, medical imaging, and face detection.

### Why Is Transfer Learning Used?

Transfer learning is popular in deep learning for several practical reasons:

1. **Faster training** — Because the network doesn't need to learn basic features from scratch, training converges much faster; you are effectively starting the optimization process from a much better point than random initialization.
2. **Handling small datasets** — Many real-world problems (like the rare-disease example above) simply don't have enough labeled data to train a deep network from scratch. Transfer learning lets you get good performance even when your own dataset is small, because most of the "hard learning" was already done on a much bigger dataset.
3. **Improved performance** — Models built with transfer learning frequently outperform models trained from scratch on the same limited data, while also requiring less training time and fewer computational resources.
4. **Domain adaptation** — Transfer learning allows a model trained in one domain or data distribution (e.g., photos taken in daylight) to be adapted to a related but different domain (e.g., low-light or infrared images), without starting over.
5. **Transfer of knowledge** — Insights and patterns learned while solving one task (e.g., recognizing shapes in natural images) can be carried over and applied usefully to a different but related task (e.g., recognizing shapes in medical scans).
6. **Resource efficiency** — Since much of the heavy lifting (feature learning) is already done, transfer learning reduces the amount of new data that needs to be collected and manually annotated/labeled, saving cost and effort.

### Transfer Learning: Example — Classroom Engagement Detection

Consider a teacher trying to gauge student engagement in a classroom — whether in-person or virtual. Traditionally, this relies on the teacher's direct, subjective observation, which is inconsistent and doesn't scale (a teacher can't watch every student's face simultaneously with full attention).

Transfer learning offers an automated alternative:

- A model originally trained for general facial-expression and emotion recognition can be reused to **detect facial expressions and emotions** in a classroom video feed.
- That same pre-trained model can then be **fine-tuned specifically to recognize "engagement" cues** (e.g., attentiveness, confusion, distraction) in virtual meeting environments, something the original model was never explicitly trained to do, but can learn quickly because it already understands faces and expressions.

---

## Scenarios of Transfer Learning

There are two possible outcomes when you apply transfer learning to a new task: **positive transfer learning** and **negative transfer learning**.

### Positive Transfer Learning

Positive transfer learning occurs when the knowledge or experience gained from one task **improves** performance on a different but related task. This is the desired, expected outcome of transfer learning — it works because the two tasks share enough underlying structure that what the model learned previously is genuinely useful for the new task.

**Example:** A model trained to detect one specific type of cancer cell under a microscope may, thanks to the general cellular and morphological features it has learned, also perform well when asked to detect *variants* of that same type of cancer cell in the future — even without being explicitly retrained on those variants from scratch.

### Negative Transfer Learning

Negative transfer learning occurs when knowledge gained from one task actually **hinders** performance on a different, unrelated task. This happens when the source and target tasks are too dissimilar — the features that were useful for the original task actively mislead the model on the new one. If you observe negative transfer learning, the general prescription is to conduct further (or different) training rather than relying solely on the pre-trained features.

**Example:** A model trained on the MNIST dataset (handwritten Arabic-numeral digits 0–9) cannot perform well at detecting handwritten Chinese digits/characters, because the visual structure of Chinese characters is fundamentally different from that of Arabic numerals — the learned features simply don't generalize, and may even bias the model in the wrong direction.

### Positive vs. Negative Transfer Learning — Visual Summary

Picture a graph of **training accuracy over time**. You start with a **pre-trained model** — a pre-existing neural network that was trained on a large dataset. From that same starting point, two different paths are possible:

| Path | Effect on accuracy | Description |
|---|---|---|
| Positive transfer learning | Accuracy on the new problem **improves** relative to training from scratch | The pre-trained model's knowledge is relevant and helpful for the new problem |
| Negative transfer learning | Accuracy on the new problem **deteriorates** relative to the original model's performance | The pre-trained model's knowledge is irrelevant or misleading for the new problem |

The takeaway: transfer learning is not automatically beneficial — it depends heavily on how related the source task (what the model was originally trained on) is to the target task (what you want it to do now).

---

## How to Select Pre-trained Models

### What Are Pre-trained Models?

Pre-trained models are pre-built deep learning models that have already been trained on large datasets (such as ImageNet for images, or large text corpora for language models). Because they've already learned rich, general-purpose feature representations, they enable efficient transfer learning and typically deliver improved performance on new, related tasks compared to training a model from scratch.

### Factors Considered to Choose a Pre-trained Model

When deciding which pre-trained model to use for a project, six factors matter:

1. **Size of the model**
2. **Extension of the model**
3. **Input of the model**
4. **Output of the model**
5. **Model specifications and accuracy**
6. **Compare and contrast** (across candidate models)

Each is discussed below.

#### 1. Size of the Model

Model size is one of the most crucial considerations because it directly determines how much storage capacity and memory the deployment system needs. A very large, highly accurate model may be unusable if it has to run on constrained hardware.

**Example:** For an object-detection task that needs to run on an *edge device* (e.g., a security camera, a mobile phone, an IoT sensor), a small, lightweight model is strongly preferable to a large, "heavy" model — even if the heavy model is marginally more accurate — because the edge device simply may not have the memory or compute budget to run it.

#### 2. Extension of the Model

The file extension of a pre-trained model reflects the **framework** it was trained and saved with, and this affects which tools and libraries you can use to load and run it. The choice of pre-trained model is therefore also a choice of software ecosystem.

**Example:** A model trained with **TensorFlow/Keras** is typically saved with a `.h5` file extension, while a model trained with **PyTorch** is typically saved with a `.pth` extension. If your production pipeline is built around PyTorch, you'll generally prefer a `.pth` model (or convert formats) rather than fight framework mismatches.

#### 3. Input of the Model

Every pre-trained model was trained expecting inputs in a specific format — a particular image resolution, number of color channels, normalization/scaling range, or (for text/audio) a particular tokenization or sampling rate. These input requirements must be identified and satisfied during your **preprocessing phase**, or the model's performance will degrade badly (or it will simply error out).

#### 4. Output of the Model

Once input has been correctly processed and passed through the model, the model produces an output (e.g., class probabilities, bounding boxes, embeddings). Understanding the output format is essential so that it can be correctly interpreted and translated into the result your application actually needs (e.g., converting raw logits into a human-readable class label).

#### 5. Model Specifications and Accuracy

Specifications — such as the number of layers, parameter count, expected accuracy on benchmark datasets, and typical inference latency — vary considerably between pre-trained models, largely depending on what task each one was designed and optimized for. These specifications help you judge whether a candidate model is a good match for your task's accuracy and performance requirements.

#### 6. Compare and Contrast

After all the above factors have been evaluated individually for each candidate model, the final step is to directly **compare and contrast** the shortlisted models against one another before making a final choice. The three practical dimensions typically used for this comparison are:

- **Speed** — How long the model takes to produce a prediction (inference latency).
- **Accuracy** — How frequently the model's predictions are correct, always considered together with (i.e., balanced against) speed and size rather than in isolation.
- **Size** — The computational and memory demands of the model, which must fit within the constraints of the deployment environment (cloud server vs. mobile app vs. embedded device).

In short: there is rarely a single "best" pre-trained model in absolute terms — the best model is the one that best balances speed, accuracy, and size *for your specific deployment context*.

---

## Pre-trained Model Lists by Domain

Pre-trained models exist across multiple data domains — image, text, audio, and video — and within each domain, different model families are optimized for different tasks.

### Image Domain

The main image-domain tasks with well-known pre-trained models are: **face detection, object detection, image segmentation, image classification,** and **pose detection**.

#### Face Detection

| Model | Description |
|---|---|
| **MTCNN** (Multi-task Cascaded Convolutional Networks) | A deep learning model specifically designed for face detection, using a cascade of CNN stages to progressively refine face bounding boxes and facial landmarks. |
| **Inception-ResNet** | A hybrid architecture that combines the Inception module's multi-scale feature extraction with ResNet's residual (skip) connections, often used for high-accuracy face recognition. |
| **MobileNet** | A lightweight architecture that is quick and effective for smartphones and other resource-limited devices, trading some accuracy for large gains in speed and small model size. |

#### Object Detection

| Model | Description |
|---|---|
| **Detectron2** | An object detection framework developed by Facebook AI Research (FAIR), providing state-of-the-art detection and segmentation algorithms. |
| **YOLOv5** (You Only Look Once) | An object detection algorithm known for its real-time processing speed, detecting objects in a single forward pass through the network. |
| **InceptionResNetV2** | A convolutional neural network architecture that combines Inception modules and ResNet's residual connections for accurate feature extraction, often used as a backbone for detection tasks. |

#### Image Segmentation

Image segmentation goes a step beyond classification/detection — instead of just labeling an image or drawing a box, it labels *every pixel* according to what object or region it belongs to.

| Model | Description |
|---|---|
| **UNet** | A popular encoder-decoder architecture widely used for image segmentation, especially in biomedical image analysis. |
| **MANet** (Microscopy Adaptive Network) | A deep learning model designed specifically for microscopy image analysis tasks. |
| **LinkNet** | A lightweight and efficient model architecture designed for semantic segmentation, favoring speed without sacrificing too much accuracy. |
| **Mask R-CNN** | An object detection *and* instance segmentation model — it not only detects objects but also produces a pixel-level mask for each detected instance. |
| **DeepLabv3** | A widely adopted model for semantic image segmentation, known for its use of atrous (dilated) convolutions to capture context at multiple scales. |

#### Image Classification

| Model | Description |
|---|---|
| **ResNet-50** | Revolutionized computer vision with its deep architecture and **skip (residual) connections**, which allow gradients to flow through very deep networks without vanishing, enabling networks with 50+ layers to train effectively. |
| **VGG-16** | Known for its simplicity and effectiveness in image classification using a deep stack of small (3×3) convolution filters. |
| **MobileNet V2** | Optimized for mobile and embedded vision applications, using lightweight, efficient CNN operations (e.g., depthwise separable convolutions) to minimize compute and memory footprint. |
| **RegNetY** | Designed for a strong balance of high performance and computational efficiency, based on a systematic architecture-design search. |
| **EfficientNet** | Achieves strong accuracy while remaining computationally efficient, by jointly and systematically scaling network depth, width, and input resolution. |

> **Note on ResNet and VGG (highlighted in the lesson objectives):** These two architectures are the most commonly cited "classic" pre-trained backbones for transfer learning in computer vision:
> - **VGG (e.g., VGG-16)** uses a straightforward, uniform stack of small convolution filters and pooling layers. It's simple to understand and implement, and its learned features transfer well, but it is relatively large and computationally heavier than more modern designs.
> - **ResNet (e.g., ResNet-50)** introduced residual/skip connections that let very deep networks train successfully by allowing gradients to "skip" over layers during backpropagation, avoiding the vanishing-gradient problem that limited earlier very-deep networks. This made it possible to go much deeper than VGG while still training effectively, generally yielding better accuracy for similar or better efficiency.

#### Pose Detection

| Model | Description |
|---|---|
| **OpenPose** | A popular framework for keypoint detection and action recognition, capable of tracking body, hand, and facial keypoints simultaneously. |
| **MoveNet** | A lightweight pose-estimation model designed for fast, accurate human pose detection, well-suited to mobile and real-time applications. |

### Text Domain

Text-domain tasks with pre-trained models include: **text classification, text embedding, text-based question answering, text generation,** and **text language models**.

#### Text Classification

| Model | Description |
|---|---|
| **XLNet** (eXtreme Language Model) | Uses permutation-based training (predicting tokens in various orders) to improve contextual learning; well suited to tasks like sentiment analysis and spam detection. |
| **ERNIE** (Enhanced Representation through Knowledge Integration) | Integrates structured external knowledge into pretraining, outperforming BERT and XLNet on several benchmarks; well suited for relation extraction and sentiment analysis. |

#### Text Embedding

| Model | Description |
|---|---|
| **BERT** | Known for bidirectional training (looking at context from both left and right of a word) and strong contextual understanding; widely used for Named Entity Recognition (NER), question answering, and sentiment analysis. |
| **ELECTRA** (Efficiently Learning an Encoder that Classifies Token Replacements Accurately) | An efficient pretraining method (predicting which tokens were replaced, rather than masked-token prediction) that delivers strong performance in text-embedding tasks at lower training cost. |

#### Text Generation

| Model | Description |
|---|---|
| **SmartReply** | A text-generation model developed by Google that automatically suggests short message responses (e.g., quick email/chat replies). |
| **RoBERTa** | A state-of-the-art model based on the BERT architecture, retrained with more data and refined pretraining choices for stronger downstream performance. |

#### Text-Based Question Answering

| Model | Description |
|---|---|
| **TF2NQ** (TensorFlow 2.0 Natural Questions) | A text-based question-answering model specifically designed for the Natural Questions dataset (real user questions paired with Wikipedia-based answers). |

#### Text Language Models

| Model | Description |
|---|---|
| **GPT-4** | Superior at handling longer texts, offering multilingual support and strong factual accuracy; useful for tasks like language translation and summarization. |
| **Enformer** | A transformer-based text model with enhanced long-range context handling, able to model relationships between distant parts of a sequence. |

### Audio Domain

Audio-domain tasks with pre-trained models include: **audio classification, audio embedding, audio speech-to-text,** and **audio pitch extraction**.

#### Audio Classification

| Model | Description |
|---|---|
| **YAMNet** (Yet Another Music Network) | Classifies audio signals into a wide range of sound categories, including environmental sounds, musical instruments, and human actions/vocalizations. |

#### Audio Embedding

| Model | Description |
|---|---|
| **TRILL** (Transferable and Interpretable Learning for Language) | An audio embedding model that learns transferable representations directly from speech data. |
| **OpenL3** | An open-source Python library that computes deep audio and image embeddings, based on the "Look, Listen, and Learn" (L3) approach, which jointly uses audio and visual data to learn useful, transferable representations. |

#### Audio Pitch Extraction

| Model | Description |
|---|---|
| **CREPE** (Convolutional REpresentation for Pitch Estimation) | A deep convolutional neural network that estimates pitch directly from raw, time-domain waveform inputs; its design makes it robust to various types of noise and audio distortion. |

#### Audio Speech-to-Text

| Model | Description |
|---|---|
| **Wav2Vec** | Converts audio speech signals into textual representations, learning useful speech representations in a self-supervised manner. |
| **Wav2Vec2** | Achieves strong results across various speech-recognition benchmarks and is widely used in both industry and academia. |
| **Wav2Vec2-Robust** | A variant of Wav2Vec2 specifically designed to remain accurate under noisy and otherwise challenging audio conditions. |

### Video Domain

Video-domain tasks with pre-trained models include: **video classification** and **video generation**.

#### Video Classification

| Model | Description |
|---|---|
| **VideoMAE** (Masked Autoencoder for Video) | A video classification model that uses a masked-autoencoder architecture — it learns by reconstructing masked-out portions of video, forcing it to learn meaningful spatiotemporal features. |
| **ViViT** | A transformer-based architecture tailored for video classification; it applies self-attention mechanisms across frames to capture long-range temporal dependencies. |

#### Video Generation

| Model | Description |
|---|---|
| **VideoFlow Encoder** | A component of a video-generation pipeline that extracts high-level features from input video frames. |
| **VideoFlow Generator** | The companion component that takes the encoded features from the VideoFlow Encoder and generates new video frames. |
| **Tweening Conv3D** | A video-generation model focused specifically on generating the intermediate ("in-between"/tweened) frames that connect two given frames. |

---

## Advantages of Transfer Learning

Transfer learning brings a wide range of benefits to the deep learning development process:

- **Better model training using simulations instead of resource-intensive real-world environments** — For tasks like robotics or autonomous driving, it's often far cheaper and safer to pre-train a model in a simulated environment and then transfer that learned behavior/knowledge to the real-world task, rather than collecting expensive and risky real-world training data from scratch.
- **Enhanced efficiency in deploying multiple deep learning models** — If an organization needs several related models (e.g., classifiers for many product categories), starting each one from a shared pre-trained base is far more efficient than training every model independently from scratch.
- **Reduced training time for models on similar datasets** — Because the model doesn't need to relearn generic features, training time on new-but-similar datasets is significantly shortened.

### Why This Matters: Data and Resource Efficiency

Deep learning algorithms typically require large labeled datasets to train effectively — and collecting and labeling such datasets is expensive and time-consuming. The central advantage of transfer learning is that it allows a model that has already been pre-trained on one (large) dataset to be **fine-tuned** for other, related tasks, dramatically reducing the need to gather a massive dataset for every single new task.

Additionally, the time and computational resources spent training the original model can effectively be "shared" and amortized across many downstream models that all start from that same pre-trained base. This substantially reduces the burden of retraining a whole new algorithm from scratch every time a related problem comes up.

---

## Assisted Practice

**Notebook:** *9.04_Implementation of Transfer Learning*

This lesson includes a hands-on Jupyter Notebook exercise where the concepts above are put into practice — loading a pre-trained architecture, replacing/retraining its final layers (feature extraction and/or fine-tuning), and evaluating the adapted model on a new image classification (or object detection) task. (Refer to the Reference Material section of the course to download the notebook file.)

---

## Key Takeaways

- **Transfer learning** is a machine learning technique where a model developed for one task is reused as the starting point for a model on another task.
- There are two possible outcomes of transfer learning: **positive transfer learning** (performance improves) and **negative transfer learning** (performance deteriorates).
- The factors to consider when choosing a pre-trained model are: **size, extension, input, output, specifications and accuracy**, and how the candidate models **compare** against each other.
- Transfer learning saves the time needed to train a model and improves the overall efficiency of the machine learning workflow, especially when deploying multiple related models.

---

## 📝 Practice Questions

1. **(MCQ)** What is the primary motivation for using transfer learning instead of training a deep learning model from scratch?
   - **A.** It always produces a smaller model file
   - **B.** It removes the need for a GPU
   - **C.** It reuses previously learned features, reducing the data, time, and resources needed for a new but related task
   - **D.** It guarantees 100% accuracy on any new task

2. **(MCQ)** A company fine-tunes a model originally trained for detecting one type of skin lesion to also detect a closely related, previously unseen variant, and accuracy improves. This is an example of:
   - **A.** Negative transfer learning
   - **B.** Positive transfer learning
   - **C.** Domain adaptation failure
   - **D.** Overfitting

3. **(MCQ)** A digit-recognition model trained only on MNIST (Arabic numerals) performs poorly when applied directly to handwritten Chinese characters. This best illustrates:
   - **A.** Positive transfer learning
   - **B.** Negative transfer learning
   - **C.** Feature extraction
   - **D.** Data augmentation

4. **(Short answer)** Explain, in your own words, the difference between the "early/middle layers" and the "later layers" of a pre-trained network in the context of transfer learning, and why typically only the later layers are retrained.

5. **(MCQ)** Which of the following is NOT listed among the six factors for choosing a pre-trained model?
   - **A.** Size of the model
   - **B.** Extension of the model
   - **C.** Programming language used by the developer's IDE
   - **D.** Model specifications and accuracy

6. **(Short answer)** Why would a small, lightweight pre-trained model typically be preferred over a larger, more accurate one when deploying object detection on an edge device such as a security camera?

7. **(MCQ)** A model is trained and saved using PyTorch. Which file extension would you most likely expect to see?
   - **A.** .h5
   - **B.** .pth
   - **C.** .csv
   - **D.** .onnx (as the default PyTorch save format)

8. **(Short answer)** List the three dimensions typically used to "compare and contrast" candidate pre-trained models once all other factors have been evaluated.

9. **(MCQ)** Which architecture is best known for introducing residual (skip) connections that allow very deep networks to train effectively by mitigating the vanishing gradient problem?
   - **A.** VGG-16
   - **B.** ResNet-50
   - **C.** MobileNet V2
   - **D.** UNet

10. **(MCQ)** Which of the following pre-trained models is specifically designed for image segmentation rather than classification or detection?
    - **A.** EfficientNet
    - **B.** YOLOv5
    - **C.** UNet
    - **D.** MTCNN

11. **(Short answer)** Name two advantages of transfer learning discussed in the lesson, beyond simply "it's faster."

12. **(MCQ)** In the text domain, which model is described as using bidirectional training and is commonly used for tasks such as NER, question answering, and sentiment analysis?
    - **A.** GPT-4
    - **B.** BERT
    - **C.** YAMNet
    - **D.** Wav2Vec

13. **(MCQ)** Which audio-domain model is specifically designed for pitch estimation directly from raw time-domain waveform input?
    - **A.** TRILL
    - **B.** YAMNet
    - **C.** CREPE
    - **D.** OpenL3

14. **(Short answer)** A hospital wants to build an image classifier for a rare disease but has only a few hundred labeled images. Explain why transfer learning is a better strategy here than training a CNN from scratch, and name one risk they should watch for (hint: think about how related the pre-trained model's original task must be).

15. **(MCQ)** Which video-domain model uses a masked-autoencoder architecture for video classification?
    - **A.** ViViT
    - **B.** VideoMAE
    - **C.** Tweening Conv3D
    - **D.** VideoFlow Generator

### Answers

1. **C** — Transfer learning's core value is reusing already-learned general features so the new model needs less data, time, and compute than training from scratch; it does not guarantee accuracy, smaller file size, or GPU-free training.

2. **B** — Performance improving on a related new task because of knowledge from a prior task is the definition of positive transfer learning.

3. **B** — Performance degrading because the new task (Chinese characters) is too dissimilar from the original task (Arabic digits) is the definition of negative transfer learning.

4. Early/middle layers learn general, broadly reusable features (edges, textures, shapes) that transfer well across many tasks, so they are usually kept frozen or lightly adjusted. Later layers learn task-specific representations and the final classification/decision logic, so they need to be retrained (fine-tuned) to map the network's features onto the new task's specific labels/outputs.

5. **C** — The six factors are size, extension, input, output, model specifications/accuracy, and compare-and-contrast; the IDE's programming language is not one of them.

6. Edge devices have limited storage, memory, and compute; a smaller model fits within those constraints and runs fast enough for real-time use, even if a larger model would be marginally more accurate — deployment feasibility outweighs a small accuracy gain.

7. **B** — PyTorch models are typically saved with a `.pth` extension, while `.h5` is typically associated with TensorFlow/Keras.

8. Speed (prediction/inference time), accuracy (frequency of correct predictions), and size (computational/memory demands relative to deployment constraints).

9. **B** — ResNet-50 introduced residual/skip connections, enabling much deeper networks to train successfully by letting gradients bypass layers during backpropagation.

10. **C** — UNet is a dedicated image-segmentation architecture; YOLOv5 is for object detection, MTCNN for face detection, and EfficientNet for image classification.

11. Any two of: better model training via simulations instead of costly real-world data collection; enhanced efficiency when deploying multiple related deep learning models; reduced training time on similar datasets; reduced data-annotation/labeling burden; shared/amortized time and resources across models.

12. **B** — BERT is known for bidirectional contextual training and is widely used for NER, question answering, and sentiment analysis.

13. **C** — CREPE is a convolutional network specifically built to estimate pitch directly from raw waveform audio, and is designed to be robust to noise and distortion.

14. Transfer learning lets the hospital start from a model that has already learned general image features from a large dataset, so it needs far fewer labeled examples to reach good accuracy than training a CNN from scratch (which would likely overfit on only a few hundred images). The key risk is negative transfer: if the pre-trained model's original task is too dissimilar from detecting this specific rare disease, its learned features may not transfer well (or could even hurt performance), so the source task should be chosen to be as related as possible (e.g., another medical-imaging model rather than a generic photo classifier).

15. **B** — VideoMAE (Masked Autoencoder for Video) explicitly uses a masked-autoencoder architecture for video classification, whereas ViViT is transformer/self-attention based.
