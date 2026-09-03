# Practical Deep Learning using PyTorch — CampusX Playlist Notes

> Notes for the YouTube playlist [Practical Deep Learning using PyTorch | CampusX](https://www.youtube.com/playlist?list=PLKnIA16_Rmvboy8bmDCjwNHgTaYH2puK7) (14 videos, CampusX, instructor Nitish Singh).
>
> Each note is built from the video's **official source material** — the instructor's own Google Colab notebook(s) and/or written notes PDF linked in the video description, cross-checked against the YouTube chapter timestamps — not a transcript summary. Code blocks are the actual code run in the video, not a paraphrase.

## Document map

| # | Note | Video | Duration | Primary source |
| --- | --- | --- | --- | --- |
| 01 | [01-intro-to-pytorch.md](01-intro-to-pytorch.md) | [PyTorch for Beginners \| Introduction to PyTorch](https://www.youtube.com/watch?v=QZsguRbcOBM) | 51:28 | Notes PDF |
| 02 | [02-tensors.md](02-tensors.md) | [Tensors in PyTorch](https://www.youtube.com/watch?v=mDsFsnw3SK4) | 1:14:32 | Colab |
| 03 | [03-autograd.md](03-autograd.md) | [PyTorch Autograd](https://www.youtube.com/watch?v=BECZ0UB5AR0) | 54:18 | Colab |
| 04 | [04-training-pipeline.md](04-training-pipeline.md) | [PyTorch Training Pipeline](https://www.youtube.com/watch?v=MKxEbbKpL5Q) | 30:21 | Colab |
| 05 | [05-nn-module.md](05-nn-module.md) | [PyTorch NN Module](https://www.youtube.com/watch?v=CAgWNxlmYsc) | 39:27 | Colab (x2) + Notes PDF |
| 06 | [06-dataset-dataloader.md](06-dataset-dataloader.md) | [Dataset & DataLoader Class in PyTorch](https://www.youtube.com/watch?v=RH6DeE3bY6I) | 51:42 | Colab (x2) + Notes PDF |
| 07 | [07-building-an-ann.md](07-building-an-ann.md) | [Building a ANN using PyTorch](https://www.youtube.com/watch?v=6EJaHBJhwDs) | 39:23 | Colab |
| 08 | [08-training-on-gpu.md](08-training-on-gpu.md) | [Neural Network Training on GPU](https://www.youtube.com/watch?v=CabHrf9eOVs) | 10:54 | Colab |
| 09 | [09-optimizing-the-network.md](09-optimizing-the-network.md) | [Optimizing the Neural Network](https://www.youtube.com/watch?v=7smLlJ8oj4o) | 28:44 | Colab |
| 10 | [10-hyperparameter-tuning-optuna.md](10-hyperparameter-tuning-optuna.md) | [Hyperparameter Tuning the ANN using Optuna](https://www.youtube.com/watch?v=Y3s-wBBLj_o) | 56:13 | Colab |
| 11 | [11-building-a-cnn.md](11-building-a-cnn.md) | [Building a CNN using PyTorch](https://www.youtube.com/watch?v=hkiBZLRFvO4) | 32:22 | Colab |
| 12 | [12-transfer-learning.md](12-transfer-learning.md) | [Transfer Learning using PyTorch](https://www.youtube.com/watch?v=aPu6a5htRXM) | 53:17 | Colab (x2) |
| 13 | [13-rnn-qa-system.md](13-rnn-qa-system.md) | [RNN using PyTorch \| Question Answering System](https://www.youtube.com/watch?v=xjzWrPQ66VQ) | 1:07:00 | Colab |
| 14 | [14-lstm-next-word-predictor.md](14-lstm-next-word-predictor.md) | [Next Word Predictor using PyTorch \| LSTM](https://www.youtube.com/watch?v=FAUha5mYSGQ) | 1:05:17 | Colab |

## The throughline

The playlist is one continuous build, not 14 disconnected topics. Two datasets carry almost the entire course:

- **Breast Cancer Wisconsin** (binary classification, tabular) — Videos 4-6. Same data, three successive rewrites of the training loop: raw tensors + manual gradient descent (04) → `nn.Module` + `nn.Linear` + `torch.optim` (05) → mini-batch training via `Dataset`/`DataLoader` (06).
- **Fashion-MNIST** (10-class image classification) — Videos 7-12. Same data, six successive improvements to the same problem:

| Video | Change | Test accuracy |
| --- | --- | --- |
| 07 | Flat MLP (784→128→64→10), CPU, 6k-row sample | 0.8325 |
| 08 | Same MLP, moved to GPU, full 60k rows | 0.8869 |
| 09 | + BatchNorm, Dropout, weight decay (regularization) | 0.8833 (train/test gap shrinks 9.3pt → 4.9pt) |
| 10 | Same regularized MLP, architecture + hyperparameters tuned by Optuna | 0.8908 |
| 11 | Switched to a CNN (`Conv2d`/`MaxPool2d`) instead of a flat MLP | 0.9262 |
| 12 (bonus nb) | CNN + Optuna tuning + data augmentation | 0.9222 |
| 12 (main nb) | Transfer learning: frozen pretrained VGG16 + new head | not meaningful — notebook has a training-loop bug (see note) |

Videos 13-14 pivot to text/sequence data (a Q&A dataset, then a raw FAQ document) and swap the model family entirely: plain `nn.RNN` (13) → `nn.LSTM` (14), building up to autoregressive next-word generation.

Across all 14 videos, one training-loop shape never changes: **forward pass → compute loss → `zero_grad()` → `backward()` → `step()`**. Everything from Video 4 onward is either ergonomics on top of that loop (`nn.Module`, `torch.optim`, `DataLoader`) or model-architecture changes plugged into it (MLP → CNN → pretrained backbone → RNN → LSTM). Video 3 (Autograd) is the mechanism that makes `backward()` possible in the first place; keep that link in mind — it's the connective tissue for the entire rest of the course.

## Two source-material bugs worth knowing before you copy any code

- **Video 10** (Optuna): the tuned optimizer is constructed but never assigned back to the variable used in training — every trial actually trains with plain SGD regardless of the `optimizer` search space entry. The *architecture* hyperparameters (layers, width, dropout, batch size) are genuinely tuned; the *optimizer* ones are not. See [10-hyperparameter-tuning-optuna.md](10-hyperparameter-tuning-optuna.md).
- **Video 12** (Transfer Learning): the training loop has a stray `break` that limits each "epoch" to a single batch, so the printed 10-epoch run isn't a real full-dataset training run; there's also a `model`/`vgg16` variable-name typo in the final evaluation cell. See [12-transfer-learning.md](12-transfer-learning.md).

Both are flagged inline in the relevant notes rather than silently reproduced or silently fixed.

## Reading order

Follow the numbering — each video assumes the previous one's code as a baseline. If you already know PyTorch basics, 01-03 (intro/tensors/autograd) can be skimmed; 04 onward is where the course's own running examples begin and every later video builds on it directly.
