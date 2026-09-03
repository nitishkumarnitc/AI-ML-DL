# Neural Network Training on GPU

*CampusX — "Practical Deep Learning using PyTorch" (Video 8/14) · [YouTube](https://www.youtube.com/watch?v=CabHrf9eOVs) · 10:54 · [Colab notebook](https://colab.research.google.com/drive/17hjS23CgFqIZjuB2XKt2u7pVu1MpD2Qr)*

This video takes the Fashion-MNIST ANN built in Video 7 and moves training onto the GPU, scaling up from the 6,000-row sample used earlier to the full 60,000-row dataset. There are no new modeling concepts here — it's purely the engineering change of running the same architecture on GPU.

## Chapters
- 0:00 Recap
- 3:10 Steps for GPU Training
- 4:56 Code Demo

## The 3-step recipe for GPU training

This is the whole point of the video:

1. Detect the device: `device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')`
2. Move the model's parameters once: `model = model.to(device)`
3. Inside every loop that touches data — both training **and** evaluation — move that batch to the same device: `x, y = x.to(device), y.to(device)`

Model and data must be on the **same device** for any operation between them. This is the single most common PyTorch device bug, and it surfaces as `RuntimeError: Expected all tensors to be on the same device`.

## Code demo

Same Fashion-MNIST ANN as Video 7, but now trained on the **full** dataset (60,000 rows, loaded from `/content/fashion-mnist_train.csv` instead of the `fmnist_small.csv` sample) and moved to GPU end-to-end:

```python
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')   # Step 1: detect device

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True, pin_memory=True)   # pin_memory speeds up host->GPU copy
test_loader  = DataLoader(test_dataset,  batch_size=32, shuffle=False, pin_memory=True)

model = MyNN(X_train.shape[1])
model = model.to(device)              # Step 2: move MODEL parameters to GPU

for epoch in range(epochs):
    for batch_features, batch_labels in train_loader:
        batch_features, batch_labels = batch_features.to(device), batch_labels.to(device)   # Step 3: move each BATCH to GPU
        outputs = model(batch_features)
        loss = criterion(outputs, batch_labels)
        optimizer.zero_grad(); loss.backward(); optimizer.step()

# same pattern repeated in the evaluation loop: move each eval batch to device too
```

## Results

Full 60k dataset, 100 epochs, same architecture as Video 7:

- Train accuracy: **0.9796**
- Test accuracy: **0.8869**
- Loss curve: 0.640 → 0.066 over 100 epochs.

> **Note:** The train/test gap (0.98 vs 0.89) is still large. This overfitting gap is what motivates Video 9's regularization techniques (BatchNorm, Dropout, weight decay) on this exact same GPU-trained setup.

## Key takeaways

- GPU training requires exactly three changes to existing training code: detect the device, move the model to it once, and move every batch to it inside both the training and evaluation loops.
- `pin_memory=True` on the `DataLoader` speeds up the host-to-GPU memory copy for batches.
- The model's parameters only need to be moved to the device once (`model.to(device)`), but data must be moved on every batch since new tensors are created each iteration.
- Mixing devices between model and data is the most common PyTorch bug at this stage, raised as `RuntimeError: Expected all tensors to be on the same device`.
- Scaling from a 6k-row sample (Video 7) to the full 60k-row dataset, with the same architecture, GPU training pushed train accuracy to 0.98 and test accuracy to 0.89.
- The persistent train/test gap under this setup sets up the need for regularization (BatchNorm, Dropout, weight decay), covered next in Video 9.
