# RNN using PyTorch | Question Answering System

*[CampusX — Practical Deep Learning using PyTorch, Video 13](https://www.youtube.com/watch?v=xjzWrPQ66VQ) · 1:07:00 · [Colab notebook](https://colab.research.google.com/drive/14VN8_INhmfE8fdKx6obLF35rt8px7JPS) · [Dataset](https://drive.google.com/file/d/1X4Hcj72NK7J2JYvgjICFj0R1XwUq1w0a) (`100_Unique_QA_Dataset.csv`, 100 short Q&A pairs)*

This is the first NLP/sequence-modeling video in the series: it builds a single-word-answer "question answering system" — framed as next-word-style prediction rather than free-form generation — using a vanilla `nn.RNN` trained on a 100-pair toy dataset.

## Chapters
- 0:00 Intro
- 0:25 Recap
- 1:27 Plan of Action / App Demo
- 4:41 Prerequisites
- 5:53 What is RNN?
- 14:10 Code Strategy
- 17:15 Project Code Demo
- 33:30 RNN Architecture
- 36:00 Coding the Project
- 51:50 Debugging the Code
- 66:38 Outro

## What is an RNN?

A plain `Linear`/MLP has no notion of order or variable length. `nn.RNN` processes a sequence one token at a time, carrying a **hidden state** forward — at each step, `h_t = tanh(W_ih @ x_t + W_hh @ h_{t-1} + b)` — so the hidden state at the end is (in principle) a summary of everything seen so far.

`nn.Embedding` is a lookup table (a learnable `vocab_size x embedding_dim` matrix) that maps a discrete token index to a dense vector. It's the standard first layer for any text model, replacing one-hot encoding with a compact, trainable representation.

## Preprocessing — tokenize, build vocabulary, convert to indices

```python
import pandas as pd
df = pd.read_csv('/content/100_Unique_QA_Dataset.csv')

def tokenize(text):
    text = text.lower()
    text = text.replace('?', '').replace("'", "")
    return text.split()

vocab = {'<UNK>': 0}          # index 0 reserved for unknown/out-of-vocabulary tokens
def build_vocab(row):
    merged_tokens = tokenize(row['question']) + tokenize(row['answer'])
    for token in merged_tokens:
        if token not in vocab:
            vocab[token] = len(vocab)     # assign each new token the next integer index
df.apply(build_vocab, axis=1)
# len(vocab) -> 324

def text_to_indices(text, vocab):
    return [vocab.get(token, vocab['<UNK>']) for token in tokenize(text)]
```

## Dataset / DataLoader

```python
from torch.utils.data import Dataset, DataLoader
import torch

class QADataset(Dataset):
    def __init__(self, df, vocab):
        self.df = df; self.vocab = vocab
    def __len__(self):
        return self.df.shape[0]
    def __getitem__(self, index):
        numerical_question = text_to_indices(self.df.iloc[index]['question'], self.vocab)
        numerical_answer = text_to_indices(self.df.iloc[index]['answer'], self.vocab)
        return torch.tensor(numerical_question), torch.tensor(numerical_answer)

dataset = QADataset(df, vocab)
dataloader = DataLoader(dataset, batch_size=1, shuffle=True)   # batch_size=1 -- questions have variable length, so no padding/collate_fn is used; this only works because each batch contains a single (unpadded) sequence
```

Answers in this dataset are always a single word, so `answer[0]` (an index into `vocab`) is used directly as the classification target — the whole task is framed as "predict one word (a class out of `len(vocab)`) from a variable-length question," not free-form generation.

## The model — a minimal RNN classifier

```python
import torch.nn as nn

class SimpleRNN(nn.Module):
    def __init__(self, vocab_size):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim=50)   # learnable word-vector lookup table
        self.rnn = nn.RNN(50, 64, batch_first=True)                    # input_size=50 (embedding dim), hidden_size=64
        self.fc = nn.Linear(64, vocab_size)                            # maps final hidden state -> a score per vocab word

    def forward(self, question):
        embedded_question = self.embedding(question)     # (batch, seq_len) -> (batch, seq_len, 50)
        hidden, final = self.rnn(embedded_question)       # hidden: all timestep outputs; final: last hidden state
        output = self.fc(final.squeeze(0))                # use only the FINAL hidden state to predict the answer word
        return output
```

## Shape walk-through

This matches the debug prints shown live in the "RNN Architecture" chapter:

```python
a = dataset[0][0].reshape(1, 6)          # a: (1, 6)            -- 1 question, 6 tokens
b = embedding(a)                         # b: (1, 6, 50)        -- each token -> 50-dim vector
c, d = rnn(b)                            # c: (1, 6, 64)        -- hidden state at EVERY timestep
                                          # d: (1, 1, 64)        -- FINAL hidden state only
e = fc(d.squeeze(0))                     # e: (1, 324)          -- one score per vocabulary word
```

`nn.RNN` returns a tuple `(output, h_n)`: `output` stacks the hidden state at every timestep (useful for seq2seq/attention-style models), while `h_n` is just the last timestep's hidden state (what a simple sequence-classification head needs). This is a foundational shape distinction for every recurrent architecture (RNN/LSTM/GRU) in PyTorch.

## Training loop

```python
model = SimpleRNN(len(vocab))
criterion = nn.CrossEntropyLoss()          # again: raw logits in, integer class index target -- same pattern as Video 7's multi-class classifier
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

for epoch in range(20):
    total_loss = 0
    for question, answer in dataloader:
        optimizer.zero_grad()
        output = model(question)
        loss = criterion(output, answer[0])    # answer[0]: because batch_size=1, answer is a length-1 tensor; index [0] unwraps it to a scalar-shaped target the loss expects
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    print(f"Epoch: {epoch+1}, Loss: {total_loss:4f}")
# Loss falls from 523.7 (summed over all 100 samples) -> 11.6 over 20 epochs
```

## Inference

```python
def predict(model, question, threshold=0.5):
    numerical_question = text_to_indices(question, vocab)
    question_tensor = torch.tensor(numerical_question).unsqueeze(0)   # add batch dim -> (1, seq_len)
    output = model(question_tensor)
    probs = torch.nn.functional.softmax(output, dim=1)
    value, index = torch.max(probs, dim=1)
    if value < threshold:
        print("I don't know")            # abstain if the model isn't confident
    print(list(vocab.keys())[index])

predict(model, "What is the largest planet in our solar system?")   # -> "jupiter"
```

> **Note:** A vanilla `nn.RNN`'s hidden state struggles to retain information over long sequences, due to vanishing gradients through many timesteps. This limitation is exactly what motivates LSTM's gating mechanism in the next video.

## Key takeaways

- The QA task is framed as single-word classification, not generation: since every answer in the dataset is one word, the model predicts a class index over the full vocabulary (`len(vocab)` = 324) rather than generating a token sequence.
- `nn.Embedding` replaces one-hot encoding with a compact, learnable `vocab_size x embedding_dim` lookup table — the standard first layer for text models.
- `nn.RNN` returns `(output, h_n)`: `output` holds the hidden state at every timestep, `h_n` holds only the final one. This model uses only `h_n` (via `final.squeeze(0)`) to feed the classification head — a shape distinction that recurs in every recurrent architecture in PyTorch.
- `batch_size=1` is a deliberate simplification: since questions have variable length and no padding/`collate_fn` is used, each "batch" must be a single unpadded sequence.
- Training with `nn.CrossEntropyLoss` and Adam (`lr=0.001`) for 20 epochs drives the summed loss from 523.7 down to 11.6, and the trained model correctly answers a held-out-style question ("What is the largest planet in our solar system?" → "jupiter").
- A vanilla RNN's hidden state degrades over long sequences due to vanishing gradients — the explicit setup for LSTM's gating mechanism, covered in the next video.
