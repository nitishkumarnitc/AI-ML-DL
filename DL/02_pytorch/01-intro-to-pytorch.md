# Video 1: PyTorch for Beginners | Introduction to PyTorch

*[Watch on YouTube](https://www.youtube.com/watch?v=QZsguRbcOBM) · 51:28 · [Official notes PDF (CampusX)](https://drive.google.com/file/d/1OROYIk7ZNp980C68qcGv5mWGgq1FG-Vy/view)*

This is the orientation video for the playlist: it traces where PyTorch came from, lays out its core features, compares it with TensorFlow, walks through its core modules, and points at where it's used in industry before previewing the plan for the rest of the course.

## Chapters

- 00:00 Intro
- 02:49 Journey of PyTorch
- 26:43 Core Features in PyTorch
- 30:45 PyTorch or TensorFlow?
- 42:22 Core Modules in PyTorch
- 46:39 Where is PyTorch used in Industry?
- 49:52 Plan of Attack

## The Journey of PyTorch

PyTorch is an open-source deep learning library developed by Meta AI (formerly Facebook AI Research). It combines Python's ease of use with the efficiency of the Torch scientific computing framework, which was originally built with Lua and was known for high-performance, GPU-accelerated tensor operations.

**Release timeline:**

- **PyTorch 0.1 (2017)** — Introduced the dynamic computation graph, enabling more flexible model architectures, along with seamless integration with other Python libraries (e.g., NumPy, SciPy). This gained it popularity among researchers thanks to its intuitive, Pythonic interface and flexibility, and it was quickly featured in numerous research papers.
- **PyTorch 1.0 (2018)** — Bridged the gap between research and production environments. Introduced TorchScript for model serialization and optimization, and improved performance through Caffe2 integration. This enabled smoother transitions of models from research to deployment.
- **PyTorch 1.x series** — Added support for distributed training, ONNX compatibility for interoperability with other frameworks, and quantization for model compression and efficiency. The ecosystem expanded with torchvision (computer vision), torchtext (NLP), and torchaudio (audio). This increased adoption across research and industry, inspired community libraries like PyTorch Lightning and Hugging Face Transformers, and strengthened cloud support for deployment.
- **PyTorch 2.0** — Brought significant performance improvements, enhanced support for deployment and production-readiness, and optimization for modern hardware (TPUs, custom AI chips) — improving speed and scalability for real-world applications and compatibility with a wider range of deployment environments.

## Core Features in PyTorch

1. Tensor computations
2. GPU acceleration
3. Dynamic computation graph
4. Automatic differentiation
5. Distributed training
6. Interoperability with other libraries

## PyTorch or TensorFlow?

> **Source note:** the notes PDF pages backing this chapter (and the two below) are diagrams/images with no extractable text layer — the video's slides couldn't be read directly. What follows is the standard, generally-accurate version of this comparison, not a verified transcript of this specific slide's content.

This chapter frames the classic PyTorch-vs-TensorFlow comparison that most practitioners run into when choosing a framework: PyTorch's historically dynamic computation graph versus TensorFlow's originally static graph, PyTorch's Pythonic and more intuitive API, the relative maturity and breadth of each ecosystem, differences in industry adoption, and ease of debugging — with PyTorch's eager, define-by-run execution generally making it more approachable to debug and prototype in.

## Core Modules in PyTorch

> **Source note:** same caveat as above — this slide's diagram had no extractable text. The list below is the standard set of PyTorch core modules (verified accurate as a matter of PyTorch's actual API), not a transcript of this slide.

The framework is organized into a small set of core modules that recur throughout the rest of the course:

- **`torch`** — the base package providing tensors and core operations.
- **`torch.nn`** — building blocks for defining neural network layers and architectures.
- **`torch.optim`** — optimization algorithms (e.g., SGD, Adam) used to update model parameters during training.
- **`torch.utils.data`** — utilities for building datasets and data loaders.
- **`torch.autograd`** — PyTorch's automatic differentiation engine.
- **`torch.cuda`** — utilities for GPU acceleration.
- **Domain libraries** — `torchvision` (computer vision), `torchtext` (NLP), and `torchaudio` (audio), extending the core framework into specific domains.

## Where Is PyTorch Used in Industry?

> **Source note:** same caveat again — this is the commonly-cited list of companies using PyTorch, offered as a plausible reconstruction of this slide, not a confirmed transcript of it.

PyTorch has broad industry adoption; companies such as Tesla, Meta, OpenAI, Microsoft, Uber, and Airbnb are commonly cited among its users.

## Plan of Attack

The video closes by previewing the roadmap for the rest of the playlist, setting up what the following videos will build toward.

## Key takeaways

- PyTorch is Meta AI's open-source deep learning library, born out of the Lua-based Torch framework, and it moved from a research-favorite (0.1, 2017) to production-ready (1.0, 2018) to a performance-and-deployment-focused release (2.0).
- Its six core features are tensor computations, GPU acceleration, a dynamic computation graph, automatic differentiation, distributed training, and interoperability with other libraries.
- Compared to TensorFlow, PyTorch is generally seen as more Pythonic and easier to debug, historically owing to its dynamic (define-by-run) computation graph versus TensorFlow's originally static graph.
- The framework's functionality is organized into a handful of core modules — `torch`, `torch.nn`, `torch.optim`, `torch.utils.data`, `torch.autograd`, `torch.cuda` — plus domain-specific libraries `torchvision`, `torchtext`, and `torchaudio`.
- PyTorch has broad industry adoption, with companies like Tesla, Meta, OpenAI, Microsoft, Uber, and Airbnb commonly cited as users.
- This video is purely conceptual (no code or notebook), setting the stage for the hands-on tensor and autograd work in the videos that follow.
