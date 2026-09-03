# Tensors in PyTorch

*Video 2 of 14 — CampusX "Practical Deep Learning using PyTorch" · [Watch on YouTube](https://www.youtube.com/watch?v=mDsFsnw3SK4) · 1:14:32 · [Official Colab notebook](https://colab.research.google.com/drive/1LgMnRIHSE9NjI2G1YRGSa8wIQqfSf8W8)*

This video introduces tensors — the core data structure in PyTorch — covering the conceptual picture (scalars, vectors, matrices, and N-dimensional tensors) and why they matter for deep learning, then moves into hands-on Colab work: creating tensors, inspecting shapes and dtypes, running mathematical operations, copying tensors safely, moving tensors to the GPU, reshaping, and interoperating with NumPy.

## Chapters
- 0:00 Intro
- 1:12 Before Starting
- 3:52 What are Tensors?
- 6:05 Scalar
- 7:55 Vector
- 9:08 Matrices
- 9:47 3D Tensors
- 10:56 4D Tensors
- 11:55 5D Tensors
- 13:45 Why are Tensors Useful?
- 17:35 Where are Tensors used in Deep Learning?
- 19:54 Practical with Code Example
- 23:20 Creating a Tensor
- 30:30 Tensor Shapes
- 34:35 Tensor Data Types
- 38:06 Mathematical Operations on Tensors
- 53:11 Inplace Operations
- 56:57 Copying a Tensor
- 1:00:15 Tensor Operations on GPU
- 1:05:37 Reshaping Tensors
- 1:11:18 NumPy and PyTorch

## Setup

```python
import torch
print(torch.__version__)   # 2.5.1+cu121

if torch.cuda.is_available():
    print("GPU is available!")
    print(f"Using GPU: {torch.cuda.get_device_name(0)}")   # Tesla T4
else:
    print("GPU not available. Using CPU.")
```

## Creating a Tensor

PyTorch offers several constructors for getting a tensor onto the board: uninitialized memory, filled tensors, random tensors, tensors built from Python data, and range/spacing/identity helpers.

```python
a = torch.empty(2,3)          # uninitialized memory
type(a)                       # torch.Tensor
torch.zeros(2,3)
torch.ones(2,3)
torch.rand(2,3)                # new random values every call
torch.manual_seed(100); torch.rand(2,3)   # seeded -> reproducible
torch.tensor([[1,2,3],[4,5,6]])            # from nested list
torch.arange(0,10,2)                       # tensor([0,2,4,6,8])
torch.linspace(0,10,10)                    # 10 evenly spaced points 0..10
torch.eye(5)                               # 5x5 identity
torch.full((3,3), 5)                       # filled with 5
```

## Tensor Shapes

Every tensor carries a `.shape`, and PyTorch provides `_like` variants that create a new tensor matching another tensor's shape.

```python
x = torch.tensor([[1,2,3],[4,5,6]])
x.shape                        # torch.Size([2, 3])
torch.empty_like(x)            # same shape, garbage values
torch.zeros_like(x)
torch.ones_like(x)
torch.rand_like(x, dtype=torch.float32)   # rand_like needs float dtype override since x is int64
```

## Tensor Data Types

A tensor's dtype can be inspected via `.dtype`, forced at creation time, or changed afterwards with `.to()`.

```python
x.dtype                                          # torch.int64
torch.tensor([1.0,2.0,3.0], dtype=torch.int32)   # force dtype at creation
torch.tensor([1,2,3], dtype=torch.float64)
x.to(torch.float32)                              # cast after creation via .to()
```

| Data Type | Dtype | Description |
|---|---|---|
| 32-bit Float | `torch.float32` | Standard dtype for most DL tasks; balances precision/memory. |
| 64-bit Float | `torch.float64` | Double precision; high-precision numerics, more memory. |
| 16-bit Float | `torch.float16` | Half precision; mixed-precision training on modern GPUs. |
| BFloat16 | `torch.bfloat16` | Reduced-precision float, common in TPU mixed-precision training. |
| 8-bit Float | `torch.float8` | Ultra-low precision; experimental/extreme memory-constrained use. |
| 8-bit Int | `torch.int8` | Quantized models, memory/compute savings at inference. |
| 16-bit Int | `torch.int16` | Intermediate-precision numeric tasks. |
| 32-bit Int | `torch.int32` | General-purpose indexing/numerics. |
| 64-bit Int | `torch.int64` | Long integer; large indices/large numbers. |
| 8-bit Unsigned Int | `torch.uint8` | Image pixel data (0-255). |
| Boolean | `torch.bool` | True/False masks for logical ops. |
| Complex64 | `torch.complex64` | 32-bit real + 32-bit imaginary; scientific/signal processing. |
| Complex128 | `torch.complex128` | 64-bit real + 64-bit imaginary; higher precision. |
| Quantized Int8 | `torch.qint8` | Quantized inference. |
| Quantized UInt8 | `torch.quint8` | Quantized image tensors. |

## Mathematical Operations

The notebook walks through six categories of tensor math: scalar ops, element-wise ops between two same-shape tensors, reduction ops, matrix ops, comparison ops, and special functions (log/exp/activations).

```python
# 1. Scalar ops
x = torch.rand(2,2)
x + 2; x - 2; x * 3; x / 3; (x*100)//3; ((x*100)//3) % 2; x**2

# 2. Element-wise ops (two same-shape tensors)
a + b; a - b; a * b; a / b; a ** b; a % b
torch.abs(c); torch.neg(c)
torch.round(d); torch.ceil(d); torch.floor(d)
torch.clamp(d, min=2, max=3)

# 3. Reduction ops
torch.sum(e); torch.sum(e, dim=0); torch.sum(e, dim=1)
torch.mean(e); torch.mean(e, dim=0)
torch.median(e); torch.max(e); torch.min(e); torch.prod(e)
torch.std(e); torch.var(e)
torch.argmax(e); torch.argmin(e)

# 4. Matrix ops
torch.matmul(f, g)             # (2,3) x (3,2) -> (2,2)
torch.dot(vector1, vector2)    # 1D dot product
torch.transpose(f, 0, 1)
torch.det(h); torch.inverse(h)

# 5. Comparison ops
i > j; i < j; i == j; i != j; i >= j; i <= j

# 6. Special functions
torch.log(k); torch.exp(k); torch.sqrt(k)
torch.sigmoid(k); torch.softmax(k, dim=0); torch.relu(k)
```

## Inplace Operations

```python
m.add_(n)      # trailing underscore = inplace, mutates m and frees n's separate result
m.relu_()
```

> **Note:** Inplace ops (trailing underscore) modify the tensor's own memory instead of allocating a new tensor — this saves memory, but it can break autograd if the tensor is needed unmodified during the backward pass.

## Copying a Tensor

```python
b = a          # b is just another reference to the SAME tensor (id(a) == id(b))
a[0][0] = 0    # mutates both a and b

b = a.clone()  # b is now an independent copy (different id)
a[0][0] = 10   # only a changes; b keeps its own values
```

> **Note:** Plain `=` only copies the reference, not the data — both names point at the same tensor, so mutating one mutates the other. `clone()` is the correct way to get an independent copy.

## Tensor Operations on GPU

Moving a tensor to the GPU is done with `torch.cuda.is_available()` to check availability, and then either `x.to('cuda')` / `x.cuda()`, or the more portable pattern `x.to(device)` where `device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')`. Both operands of an operation must live on the same device, or PyTorch will raise an error.

## Reshaping Tensors

Common reshaping operations include `x.reshape(shape)` and `x.view(shape)` (the latter requires the underlying memory to be contiguous), `x.flatten()` to collapse to 1D, `x.squeeze()` to drop size-1 dimensions, `x.unsqueeze(dim)` to insert a size-1 dimension, and `x.permute(*dims)` to reorder dimensions.

## NumPy and PyTorch

`x.numpy()` converts a CPU tensor to a NumPy `ndarray`, and `torch.from_numpy(arr)` converts a NumPy array back into a tensor.

> **Note:** Both conversions share the underlying memory rather than copying it — mutating the tensor mutates the array (and vice versa) unless you explicitly call `.clone()` (tensor) or `.copy()` (ndarray) first.

## Key takeaways
- Tensors generalize scalars → vectors → matrices → N-D arrays, and are the fundamental data structure PyTorch uses to represent inputs, weights, and activations in deep learning.
- PyTorch has dedicated constructors for every common case: `empty`/`zeros`/`ones`/`rand` for uninitialized/filled/random data, `tensor()` from Python lists, and `arange`/`linspace`/`eye`/`full` for structured values; `manual_seed` makes random tensors reproducible.
- Every tensor has a `.shape` and a `.dtype`; `_like` constructors (`zeros_like`, `rand_like`, etc.) copy shape from another tensor, and `.to(dtype)` casts after creation — note that `rand_like` needs an explicit float dtype override when the source tensor is integer-typed.
- Tensor math is organized into scalar ops, element-wise ops, reductions (`sum`, `mean`, `argmax`, ...), matrix ops (`matmul`, `dot`, `transpose`, `det`, `inverse`), comparisons, and special functions (`log`, `exp`, `sigmoid`, `softmax`, `relu`).
- Inplace ops (trailing `_`) save memory but can interfere with autograd; `clone()` — not plain `=` — is required to get a truly independent copy of a tensor.
- GPU transfer (`.to(device)`) and reshaping (`view`/`reshape`/`squeeze`/`unsqueeze`/`permute`) are standard tensor manipulations, and NumPy interop via `.numpy()` / `torch.from_numpy()` shares memory rather than copying it.
