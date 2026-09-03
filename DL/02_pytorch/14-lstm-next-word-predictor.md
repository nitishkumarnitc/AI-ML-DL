# Next Word Predictor using PyTorch | LSTM using PyTorch

*Video 14 of "Practical Deep Learning using PyTorch" (CampusX) — [watch on YouTube](https://www.youtube.com/watch?v=FAUha5mYSGQ) · 1:05:17 · [Notebook (official)](https://colab.research.google.com/drive/1YKhXxYlwteT8uGpp6pHmki1QoOMR4bdB)*

This video builds a next-word predictor on a real, unstructured block of running text using an `nn.LSTM` in place of Video 13's vanilla `nn.RNN`. It covers turning a text corpus into next-token-prediction training data via the every-prefix-of-every-sentence trick, the LSTM architecture and why it beats a plain RNN on longer sequences, the training loop, and autoregressive multi-word generation at inference time.

## Chapters
- 0:00 Intro / Plan of Attack
- 2:54 Working Demo
- 6:12 Strategy
- 12:55 Coding Demo
- 35:18 LSTM Architecture
- 42:31 Coding the Architecture
- 65:01 Outro

## The corpus: a real, messy text document

The training text is the CampusX "DSMP" course FAQ document — a long block of realistic Hinglish-adjacent FAQ prose (course fee, refund policy, certificate criteria, etc.) pasted directly as a Python string. Unlike Video 13's clean 100-row Q&A CSV, this is the first video to train on **unstructured free text**, which is the actual point: a next-word predictor needs a large corpus of natural running text, not question/single-word-answer pairs.

## Preprocessing — sentence-level tokenization + N-gram training sequences

```python
import nltk
from nltk.tokenize import word_tokenize
from collections import Counter

nltk.download('punkt'); nltk.download('punkt_tab')

tokens = word_tokenize(document.lower())

vocab = {'<unk>': 0}
for token in Counter(tokens).keys():          # iterate unique tokens (Counter.keys() preserves first-seen order)
    if token not in vocab:
        vocab[token] = len(vocab)
# len(vocab) -> 289

input_sentences = document.split('\n')         # split corpus into individual lines/sentences
input_numerical_sentences = [
    [vocab.get(tok, vocab['<unk>']) for tok in word_tokenize(s.lower())]
    for s in input_sentences
]                                                # len -> 78 sentences

# build ALL prefixes of every sentence as separate training examples
training_sequence = []
for sentence in input_numerical_sentences:
    for i in range(1, len(sentence)):
        training_sequence.append(sentence[:i+1])
# len(training_sequence) -> 942  -- e.g. sentence [1,2,3] yields [1,2] and [1,2,3] as two training rows

# pad every sequence on the LEFT to the same max length so they can batch into one tensor
max_len = max(len(seq) for seq in training_sequence)     # 62
padded = [[0]*(max_len - len(seq)) + seq for seq in training_sequence]
padded_training_sequence = torch.tensor(padded, dtype=torch.long)

X = padded_training_sequence[:, :-1]     # everything except the last token = the "context"
y = padded_training_sequence[:, -1]      # the last token = the word to predict
```

This "every-prefix-of-every-sentence" construction is the standard way to turn a corpus into a next-token-prediction training set: for a sentence "the cat sat", it yields training pairs (context -> next word) `("the" -> "cat")` and `("the cat" -> "sat")`, teaching the model to predict the next word at every position, not just at the end of a fixed-length window.

## The model — LSTM instead of vanilla RNN

```python
class LSTMModel(nn.Module):
    def __init__(self, vocab_size):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, 100)
        self.lstm = nn.LSTM(100, 150, batch_first=True)     # input_size=100, hidden_size=150
        self.fc = nn.Linear(150, vocab_size)

    def forward(self, x):
        embedded = self.embedding(x)
        intermediate_hidden_states, (final_hidden_state, final_cell_state) = self.lstm(embedded)
        # nn.LSTM returns (all-timestep outputs, (final hidden state, final cell state)) --
        # one more tuple level than nn.RNN, because LSTM tracks a separate cell state (long-term memory) alongside the hidden state (short-term/output)
        output = self.fc(final_hidden_state.squeeze(0))
        return output

model = LSTMModel(len(vocab))
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
```

## Training

```python
dataset = CustomDataset(X, y)                      # same minimal Dataset pattern as every prior video
dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

for epoch in range(50):
    total_loss = 0
    for batch_x, batch_y in dataloader:
        batch_x, batch_y = batch_x.to(device), batch_y.to(device)
        optimizer.zero_grad()
        output = model(batch_x)
        loss = criterion(output, batch_y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    print(f"Epoch: {epoch + 1}, Loss: {total_loss:.4f}")
# Loss: 166.5 (epoch 1) -> 23.9 (epoch 17) -- steadily decreasing, same 5-step loop shape as every prior training video
```

## Multi-word prediction at inference time

```python
def predict(model, vocab, text, num_words=10):
    for _ in range(num_words):
        tokenized = word_tokenize(text.lower())
        numerical = [vocab.get(tok, vocab['<unk>']) for tok in tokenized]
        padded = torch.tensor([0]*(61 - len(numerical)) + numerical, dtype=torch.long).unsqueeze(0).to(device)
        output = model(padded)
        next_word_idx = torch.argmax(output, dim=1).item()
        next_word = list(vocab.keys())[next_word_idx]
        text = text + ' ' + next_word            # feed the predicted word back in as new context -- this is what makes it a *generator*, not just a one-shot classifier
    return text
```

> **Note:** the notebook's final interactive-prediction cell renders as virtualized output, so it couldn't be captured directly. The `predict()` function above follows the same pattern as Video 13's single-word `predict()`, just looped to generate multiple words, rather than being a literal capture of that one cell.

This feed-the-prediction-back-in loop (autoregressive generation) is the key conceptual step up from Video 13: Video 13 predicted a single answer word from a fixed question, while this video repeatedly re-predicts the "next word" and appends it, producing a growing generated sentence — the same basic idea, scaled up enormously, behind modern autoregressive language models.

## LSTM vs RNN

Video 13's plain `nn.RNN` struggles to carry information across many timesteps because repeatedly multiplying by the same recurrent weight matrix causes gradients to vanish (or explode) over long sequences. `nn.LSTM` fixes this with a **cell state** plus three gates:
- **Forget gate**: decides what fraction of the previous cell state to discard.
- **Input gate**: decides how much of the new candidate information to write into the cell state.
- **Output gate**: decides what part of the (updated) cell state to expose as the hidden state/output at this timestep.

The cell state acts as a more stable long-term memory highway (mostly additive updates, gated rather than fully overwritten each step), which is why LSTMs handle longer text sequences far better than vanilla RNNs — directly relevant here since sentences in the padded training set run up to 61 tokens of context.

## Key takeaways

- This is the first video in the series to train on real unstructured free text (a CampusX FAQ document) rather than a toy or Q&A-structured dataset — the actual target task for a next-word predictor.
- The every-prefix-of-every-sentence trick turns a small corpus (78 sentences) into a much larger next-token-prediction training set (942 rows), pairing each prefix with the word that follows it.
- Variable-length prefixes are left-padded to a common max length (62 tokens) so they can be batched into a single tensor.
- Swapping `nn.RNN` for `nn.LSTM` only changes the model's forward pass by one extra tuple level in the return value, since the LSTM tracks a separate cell state (long-term memory) alongside the hidden state (short-term/output).
- The LSTM's forget/input/output gates and mostly-additive cell-state updates solve the vanishing/exploding gradient problem that limits vanilla RNNs on long sequences, which matters here since contexts run up to 61 tokens.
- Inference is autoregressive: predict one word, append it to the input text, and repeat — the same fundamental mechanism (at vastly larger scale) behind modern generative language models.
