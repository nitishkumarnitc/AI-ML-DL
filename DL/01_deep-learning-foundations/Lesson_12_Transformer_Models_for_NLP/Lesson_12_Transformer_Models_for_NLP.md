# Transformer Models for NLP

*Deep Learning with Keras and TensorFlow — Lesson 12*

## Learning Objectives

By the end of this lesson, you will be able to:

- Apply self-attention mechanisms to analyze the importance of different words in a sentence for text processing.
- Utilize Transformer models to improve machine translation tasks, and explore how these models effectively manage long-range dependencies.
- Employ the Transformer architecture in natural language processing to develop more efficient sentiment analysis tools.
- Implement a Transformer model to recognize and translate languages, demonstrating the model's ability to handle different linguistic inputs.

---

## Business Scenario

**TelNet Global**, a multinational telecommunications company, handles millions of customer interactions every month across channels such as social media, email, and live chat. The sheer volume and complexity of these queries — everything from billing disputes to technical support tickets — creates serious strain on response time and support quality.

**The challenge.** TelNet Global needs a solution that can:

- Automate responses to common, repetitive queries so human agents are not overloaded with routine work.
- Understand and correctly route complex customer inquiries to the right department (e.g., billing vs. technical support).
- Enhance the customer experience by providing fast, accurate, and context-aware responses instead of generic scripted replies.
- Reduce the operational costs associated with running a large customer support organization.

This is exactly the kind of problem that modern NLP systems built on **Transformer models** are designed to solve: they can read and understand full customer messages in context, classify intent, retrieve relevant information, and generate natural-sounding responses — all much faster and more accurately than older sequence models. This lesson builds the conceptual foundation (self-attention, encoder-decoder architecture, BERT) needed to understand how such systems work under the hood.

---

## Overview of Transformer Models

### Introduction to Transformer Models

**Transformer models** are a type of deep learning architecture that relies on **self-attention mechanisms** to process every element of an input sequence *simultaneously*, rather than one step at a time.

This is a fundamental departure from how older architectures worked:

- **RNNs (Recurrent Neural Networks)** process data sequentially — each word (or time step) must be handled one after another, in order, because each step's computation depends on the hidden state produced by the previous step. This makes RNNs inherently slow to train (they cannot be easily parallelized) and prone to "forgetting" information from far earlier in the sequence.
- **Transformers**, by contrast, look at the *entire* sequence at once. Every word can attend to every other word directly, regardless of how far apart they are in the sentence. This parallel processing is both faster to train (it can leverage GPU/TPU parallelism far better) and much better at capturing relationships between distant words.

**Example intuition:** Imagine translating the sentence "The animal didn't cross the street because it was too tired." To correctly translate "it," a model needs to know that "it" refers to "the animal," not "the street" — even though several words separate them. An RNN has to carry that information forward step by step and can lose it; a Transformer can directly connect "it" back to "the animal" in a single attention computation.

### Understanding Self-Attention

**Self-attention** is the key mechanism that allows a Transformer to decide which words in a sentence are most relevant to understanding any other given word. It lets the network "focus" on specific words or phrases to build a richer, context-aware representation of meaning.

**Analogy — reading a mystery novel:** When you read a mystery novel, you don't process each page in total isolation. While reading the current page, you simultaneously recall earlier events, characters, and clues that were introduced many chapters ago. That accumulated context is what lets you understand the current scene properly and predict what might happen next. Self-attention gives a neural network this same capability — the ability to relate the "current word" to any other word anywhere in the text, weighted by how relevant that other word is.

### Mechanics Behind Self-Attention

To compute self-attention, the model derives **three vectors** from every input (word) vector fed into the encoder:

1. **Query Vector (Q):** Represents the current word's "question" — it scores each other word in the sequence according to how much attention the current word needs to pay to it.
2. **Key Vector (K):** Represents each word's "label" or identity — it is compared against queries to score how relevant (attention-worthy) that word is to whoever is querying.
3. **Value Vector (V):** Represents the actual semantic content of the word. Once attention weights (from Q and K) are computed, they are used to combine the Value vectors into the final output representation.

All three vectors (Q, K, V) are learned during training — they start as random weight matrices and are iteratively updated via backpropagation, just like any other neural network parameters.

**The attention formula:**

```
Attention(Q, K, V) = Softmax( (Q · Kᵀ) / √d_k ) · V
```

Breaking this down:

- `Q · Kᵀ` computes a similarity score between every query and every key (essentially, "how much should this word attend to that word?").
- Dividing by `√d_k` (the square root of the key vector's dimensionality) is a scaling step that keeps the values in a numerically stable range so the softmax doesn't produce extremely peaked or vanishing gradients.
- `Softmax(...)` converts the raw scores into a probability distribution — i.e., attention *weights* that sum to 1 across all words.
- Multiplying by `V` produces a weighted sum of the Value vectors, where words that received higher attention weights contribute more to the final output.

### Self-Attention: The Party Analogy

A helpful way to internalize this mechanism: imagine a person at a crowded party trying to decide whom to listen to. Everyone at the party has a story to tell, but not every story is equally relevant to that person's interests at that moment — so they must implicitly decide how much attention to give each speaker.

This maps onto the four steps of self-attention:

- **Listening:** Each person (representing a data point or word in a sentence) listens to the stories (inputs) of everyone else in the room (the sequence).
- **Scoring:** Everyone assigns a relevance score to each storyteller based on how pertinent that story is to their current interests or the conversational context — this is the **query-key matching** step.
- **Focusing:** Attention naturally concentrates on the stories with the highest scores — these get weighted more heavily.
- **Combining:** Each person forms a summary of what matters most across all the stories they heard, weighted by how much attention they paid to each one — this is the **weighted sum of values**.

This is precisely what the attention formula computes mathematically: score relevance (Q·K), normalize it into weights (softmax), then blend the content (V) according to those weights.

### Transformer Models: Advantage

Because self-attention connects every word directly to every other word — no matter the distance between them — Transformer models excel at capturing **long-range dependencies**. This makes them especially well-suited to tasks like:

- **Machine translation** — where grammatical agreement or pronoun resolution can span an entire sentence or paragraph.
- **Document summarization** — where understanding a concept mentioned early in a document may be essential to correctly summarizing a point made much later.

Earlier architectures — **RNNs** and **LSTMs** (Long Short-Term Memory networks, an improved variant of RNNs) — struggled with exactly this problem: as sequences got longer, information from early tokens tended to fade or get overwritten before it could influence later predictions. Transformers resolve this limitation structurally, since attention has direct access to the full sequence at every step.

### Long-Range Dependencies: Short Sentence Example

Consider the sentence:

> "Frenny likes to play basketball; he is good at dunking."

Here, "Frenny" is the subject, and "he" is a pronoun that refers back to "Frenny." RNNs and LSTMs are generally *proficient* at resolving this kind of short-range reference — the pronoun is close enough to its antecedent that the sequential memory hasn't had a chance to degrade yet.

### Long-Range Dependencies: Longer Paragraph Example

Now consider a longer passage:

> "Lara is a cook at McTown French Fries. She's been working there for three years now. The place immediately gained fame once she joined. Nobody knew of its existence until she joined it. She made good friends with other cooks and learned to cook various new dishes, which customers enjoyed at that place."

This paragraph contains multiple pronoun chains that a model must track simultaneously:

- References to **Lara**: "She," "she," "She"
- References to **McTown French Fries**: "there," "The place," "its," "it," "that place"

Traditional sequence models like RNNs and LSTMs often struggle here because, by the time the model reaches later pronouns, the sequential memory carried from much earlier tokens has weakened or been overwritten — the model can effectively "lose" its association with the original subject as the sequence grows. Transformer models, however, retain this context robustly because self-attention lets any pronoun directly attend back to its antecedent — however many words earlier it appeared — and they exhibit strong proficiency in tracking grammatical relationships across an entire passage.

---

## Applications of Transformer Models

Although Transformers were originally developed for NLP, self-attention has proven to be a remarkably general-purpose mechanism, and Transformer-based architectures are now used across many domains:

- **Natural Language Processing (NLP):** The original and most common use case — machine translation, text summarization, sentiment analysis, and question-answering all rely heavily on Transformer models today.
- **Speech Recognition:** Transformer models are used in automatic speech recognition (ASR) systems to convert spoken audio into written text, learning to align acoustic signals with linguistic tokens.
- **Image Recognition:** Adapted for computer vision through architectures like the Vision Transformer (ViT), used for tasks such as image classification, object detection, and image captioning.
- **Recommender Systems:** Applied to generate personalized recommendations by modeling sequences of user interactions and preferences, similar to how they model sequences of words.
- **Reinforcement Learning:** Used to enhance decision-making in sequential tasks such as game-playing (e.g., strategy games) and robot control, where an agent must weigh the relevance of past states and actions.
- **Drug Discovery:** Used to predict molecular properties, design novel candidate molecules, and accelerate the overall drug development pipeline by treating molecular structures as sequences amenable to self-attention.

The common thread across all these applications is that Transformers are good at modeling relationships between elements in a sequence (or set), regardless of whether those elements are words, audio frames, image patches, user actions, or atoms in a molecule.

---

## Architecture of the Transformer Model

### Transformer Model Architecture: Encoder and Decoder

At a fundamental level, the Transformer architecture is built from two primary components:

- **Encoder:** Reads and processes the input sequence.
- **Decoder:** Generates the output sequence.

**Worked example — French-to-English translation:**

- Input (French): "Je suis étudiant"
- Output (English): "I am a student"

The input passes through a stack of encoders, and the resulting contextual representation is passed to a stack of decoders, which produce the translated output word by word.

**Working of encoder and decoder:**

- The **encoder** processes the input sequence and captures contextual information by employing self-attention to integrate information across the *entire* sequence — every word's representation is informed by every other word in the input.
- The **decoder** generates the output sequence, predicting the next word based on the context provided by the encoder plus whatever it has generated so far.
- Together, this architecture ensures accurate and coherent sequence processing and generation, whether for translation or any other sequence-to-sequence task.

### Stacked Layers

In practice, a Transformer does not use just a single encoder and a single decoder — it stacks **multiple identical encoder layers** and **multiple identical decoder layers** on top of each other (commonly **six or more** of each, as in the original "Attention Is All You Need" paper). This stacking allows the network to progressively refine and enrich its representations, layer by layer, which enables much more effective information capture and generation than a single-layer model could achieve.

**The full architecture (as depicted in the original Transformer diagram) includes:**

- **Input Embedding** — converts input tokens into dense vectors.
- **Positional Encoding** — added to the input embeddings to inject information about word order (since self-attention alone has no inherent sense of sequence position).
- **Encoder stack (×N):** Each encoder layer contains:
  - A **Multi-Head Attention** sub-layer (self-attention computed multiple times in parallel with different learned projections, then combined — this lets the model attend to different types of relationships simultaneously).
  - An **Add & Norm** step (residual connection plus layer normalization) after attention.
  - A **Feed Forward** network (applied independently to each position).
  - Another **Add & Norm** step after the feed-forward network.
- **Output Embedding** and **Positional Encoding** for the (shifted-right) target sequence feeding into the decoder.
- **Decoder stack (×N):** Each decoder layer contains:
  - A **Masked Multi-Head Attention** sub-layer (self-attention restricted so a position can only attend to earlier positions — this preserves the auto-regressive property needed for generation).
  - An **Add & Norm** step.
  - A **Multi-Head Attention** sub-layer that attends over the **encoder's output** (encoder-decoder attention).
  - Another **Add & Norm** step.
  - A **Feed Forward** network, followed by another **Add & Norm** step.
- **Linear layer** followed by **Softmax** — converts the decoder's final representations into a probability distribution over the vocabulary, from which the next output word is selected.

*Source: Vaswani, Ashish, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Łukasz Kaiser, and Illia Polosukhin. "Attention is all you need." Advances in Neural Information Processing Systems 30 (2017).*

---

## Working of the Transformer in Language Translation

To make the architecture concrete, let's walk through translating the French sentence **"Je suis étudiant"** ("I am a student") step by step.

### Transformer Working: Encoder

Each encoder layer has two sub-layers:

1. A self-attention mechanism
2. A feed-forward neural network

**Step 1 — Input processing:** The model begins by taking the input sentence, "Je suis étudiant." Each word is first converted into a numeric vector through an **embedding** process — this maps discrete tokens into a continuous vector space where semantically similar words tend to lie closer together.

**Step 2 — Positional encoding:** After embedding, **positional encoding** is added to each word's vector. Because self-attention treats the sequence as a set (with no inherent order), the model needs an explicit way to know *where* each word falls in the sequence. Positional encoding injects that positional information directly into each word's vector representation, which is essential for understanding syntax (e.g., subject-verb-object order) and semantics.

**Step 3 — Passing through encoders:** The word vectors — now enhanced with positional information — pass through multiple stacked encoder layers. Each layer processes the vectors, refining and enriching their representations using the context provided by the entire sentence. This refinement happens through the combination of self-attention (relating words to each other) and the feed-forward network (transforming each position's representation independently).

### Transformer Working: Decoder

Each decoder layer has three sub-layers:

1. Self-attention
2. Encoder-decoder attention
3. Feed-forward

**Step 1 — Receiving encoder outputs:** The decoder begins by receiving the complete sequence of outputs produced by the encoder stack. These outputs encode contextual information about every word in the input sentence, giving the decoder the full context it needs to produce an accurate translation.

**Step 2 — Output sequence initialization:** The decoder starts generating output by receiving a special **start token**. This token acts as the initial input that kicks off the decoding (generation) process.

**Step 3 — Self-attention mechanism (masked):** Each decoder layer first applies self-attention, but with an important restriction: each position in the decoder is only allowed to attend to *earlier* positions in the output sequence (this is called **masked** self-attention). This ensures predictions for each word depend only on the words already generated — never on future words — preserving the **auto-regressive** property that is essential for coherent, left-to-right generation. This step also helps the decoder maintain grammatical structure and flow within the output sequence itself.

**Step 4 — Encoder-decoder attention:** After its own self-attention step, each decoder layer applies an **encoder-decoder attention** mechanism. This is the crucial step that lets the decoder look back at the relevant parts of the *input* sequence for whichever word it is currently generating. By attending directly to the encoder's outputs, the decoder ensures that the translation it produces stays semantically aligned with the original input sentence.

**Step 5 — Feed-forward network:** Just like the encoder, each decoder layer includes a position-wise feed-forward neural network. This processes the output of the attention mechanisms and produces intermediate representations used to generate the next word.

**Step 6 — Output generation:** The decoder's final layer transforms these intermediate representations into **logits**, which are passed through a **softmax** layer to produce a probability distribution over every possible word in the vocabulary. The word with the highest probability is selected as the next output word.

**Step 7 — Repeat until done:** This entire decoding process repeats, one word at a time, until the decoder produces a special **end-of-sequence token**, signaling that translation generation is complete.

---

## Introduction to the BERT Model

### BERT Model

**BERT** stands for **Bidirectional Encoder Representations from Transformers**.

Unlike a standard sequence-generation model that reads text strictly left-to-right (or processes it step by step), BERT learns the context of an input by looking in *both directions at once* — this is called **contextual learning** (specifically, bidirectional contextual learning). To understand any given word, BERT considers the words both before *and* after it simultaneously.

Structurally, BERT is a Transformer model **without any decoder** — it consists only of a stack of trained encoder layers. Because the Transformer encoder reads the *entire* sequence of words at once (rather than sequentially), BERT is naturally suited to building rich, bidirectional representations of text, which is why it works so well for understanding-oriented tasks (as opposed to generation-oriented tasks, which typically require a decoder).

### BERT and Masked Language Modeling (MLM)

A **Masked Language Model (MLM)** is a training technique used to pre-train models like BERT. The core idea is deceptively simple: hide some words from the model and have it predict them from context.

**How it works:**

- Before feeding a sequence of words into BERT, **15% of the words** are randomly replaced with a special **`[MASK]`** token.
- BERT then attempts to predict the *original* value of each masked word, using the surrounding (bidirectional) contextual information as its only clue.

**Why this matters:** Because BERT must use context from *both* sides of a masked word to guess it correctly, this pre-training objective forces the model to build genuinely deep, bidirectional language understanding — rather than merely learning to predict the "next" word in a left-to-right fashion, as earlier language models did. This is the key architectural and training innovation that gives BERT its name and its strength on comprehension-style tasks.

*Source: Lappin, Shalom. Deep learning and linguistic representation. Chapman and Hall/CRC, 2021.*

### Use Cases for BERT

- **Text classification:** BERT can identify characteristics within text, such as flagging potentially fraudulent content (e.g., fraud detection in claims or transaction descriptions).
- **Text generation:** Fine-tuned variants of BERT-style models can generate text, including chatbot responses.
- **Question-answering (Q&A) systems:** BERT's deep contextual understanding helps power systems that return accurate, relevant answers to natural-language questions.
- **Search engine optimization:** BERT-based models improve search relevance by better understanding the intent and context behind user queries, rather than just matching keywords.

### Assisted Practices

The lesson references two hands-on Jupyter Notebook exercises to reinforce these concepts practically:

- **12.05 – Introduction to BERT (V3):** A guided walkthrough introducing the BERT model hands-on.
- **12.06 – Text Classification using BERT:** A guided walkthrough applying BERT to a text classification task.

*Note: Notebook files corresponding to these topics should be downloaded from the course's Reference Material section.*

---

## Key Takeaways

- Transformers are known for their strong long-range memory / dependency handling, which they acquire through the **self-attention** mechanism.
- The Transformer architecture comprises two primary components: an **encoder** and a **decoder**.
- **BERT** is a Transformer model *without* any decoder module — it consists only of a trained **encoder stack**.
- In **Masked Language Modeling (MLM)**, **15%** of the input words are replaced with a `[MASK]` token before the sequence is fed into BERT, and the model is trained to predict the original masked words from context.

---

## 📝 Practice Questions

1. **(MCQ)** What is the primary reason Transformer models can process a sequence faster during training than RNNs?
   - **A.** They use fewer parameters than RNNs
   - **B.** They process all sequence elements simultaneously rather than one step at a time
   - **C.** They only work on short sentences
   - **D.** They do not require any embeddings

2. **(MCQ)** In the self-attention mechanism, what is the role of the Value (V) vector?
   - **A.** It determines the position of a word in the sequence
   - **B.** It scores how much attention a word should receive
   - **C.** It represents the actual content of the word, used to generate the final output
   - **D.** It normalizes the softmax output

3. **(MCQ)** Why is the dot product `Q·Kᵀ` divided by `√d_k` in the attention formula?
   - **A.** To convert the scores into probabilities directly
   - **B.** To scale the values and keep them numerically stable before applying softmax
   - **C.** To remove the need for a Key vector
   - **D.** To make the Query and Key vectors identical

4. **(Short answer)** Using the "party" analogy from the lesson, explain what "scoring" and "focusing" correspond to in the mathematical self-attention mechanism.

5. **(MCQ)** What advantage do Transformer models have over RNNs and LSTMs when processing a long paragraph with multiple pronoun references?
   - **A.** Transformers ignore pronouns entirely
   - **B.** Transformers retain long-range context because any word can attend directly to any other word
   - **C.** Transformers process the paragraph one sentence at a time, like RNNs
   - **D.** Transformers require the paragraph to be shortened before processing

6. **(Short answer)** Why do RNNs and LSTMs tend to struggle with long paragraphs even though they generally handle short sentences (like pronoun resolution) well?

7. **(MCQ)** Which of the following is NOT listed in the lesson as an application domain of Transformer models?
   - **A.** Drug discovery
   - **B.** Speech recognition
   - **C.** Reinforcement learning
   - **D.** Weather forecasting

8. **(MCQ)** What is the purpose of positional encoding in the Transformer architecture?
   - **A.** To reduce the size of the input embeddings
   - **B.** To inject information about word order into each word's vector representation
   - **C.** To mask future tokens during decoding
   - **D.** To replace the need for a decoder

9. **(Short answer)** Describe the difference between the self-attention sub-layer in an encoder and the masked self-attention sub-layer in a decoder.

10. **(MCQ)** What is the function of the "encoder-decoder attention" sub-layer within a decoder layer?
    - **A.** It masks future words in the output sequence
    - **B.** It allows the decoder to focus on relevant parts of the input sequence for the word currently being generated
    - **C.** It converts logits into a probability distribution
    - **D.** It generates the positional encoding for the output

11. **(Short answer)** Explain why the decoder's self-attention must be "masked" (restricted to earlier positions) while the encoder's self-attention is not.

12. **(MCQ)** What does BERT stand for?
    - **A.** Bidirectional Encoder Representations from Transformers
    - **B.** Basic Encoder for Recurrent Transformers
    - **C.** Bilateral Embedding and Recurrent Training
    - **D.** Binary Encoded Representation Technique

13. **(MCQ)** Structurally, how does BERT differ from the full Transformer architecture described in "Attention Is All You Need"?
    - **A.** BERT has no encoder, only a decoder stack
    - **B.** BERT has no decoder, only a trained encoder stack
    - **C.** BERT has both encoder and decoder but no attention mechanism
    - **D.** BERT replaces self-attention with RNN layers

14. **(Short answer)** In Masked Language Modeling, what percentage of input words are replaced with a `[MASK]` token, and what is the model trained to do with them?

15. **(MCQ)** Which of the following is a real-world use case for BERT mentioned in the lesson?
    - **A.** Predicting stock prices from numerical time series
    - **B.** Text classification, such as fraud detection
    - **C.** Rendering 3D graphics
    - **D.** Compressing video files

16. **(Short answer)** Why is BERT's approach to learning context described as "bidirectional," and why does this matter for tasks like question-answering?

### Answers

1. **B** — Transformers process all sequence elements simultaneously (in parallel) via self-attention, unlike RNNs which must handle each step sequentially, one after another.

2. **C** — The Value (V) vector carries the actual semantic content of a word; after attention weights are computed from Q and K, they are used to combine Value vectors into the output.

3. **B** — Dividing by `√d_k` scales the dot-product scores to prevent them from becoming too large, which keeps softmax gradients stable during training.

4. In the party analogy, "scoring" corresponds to query-key matching (computing how relevant each word/story is to the current context), and "focusing" corresponds to concentrating attention (higher softmax weight) on the highest-scoring words/stories.

5. **B** — Self-attention lets any word attend directly to any other word regardless of distance, so context (like a pronoun's antecedent) is preserved even across long spans of text.

6. RNNs/LSTMs process text sequentially and carry context forward through a hidden state; as the sequence grows longer, information from early words gradually fades or gets overwritten, so the model can lose track of the original subject by the time it reaches later parts of the paragraph.

7. **D** — Weather forecasting is not mentioned; the lesson lists NLP, speech recognition, image recognition, recommender systems, reinforcement learning, and drug discovery.

8. **B** — Positional encoding injects order/position information into word vectors, since self-attention alone has no built-in sense of sequence order.

9. The encoder's self-attention lets every position attend to every other position in the input (full bidirectional access). The decoder's masked self-attention restricts each position to only attend to earlier positions in the output, preserving the auto-regressive property needed for generating text left-to-right.

10. **B** — Encoder-decoder attention lets the decoder attend to the encoder's output representations, keeping the generated word semantically aligned with the relevant part of the input.

11. Masking is required in the decoder because generation is auto-regressive — each output word must be predicted using only previously generated words, not future ones (which don't exist yet at inference time and would leak information during training). The encoder, however, sees the complete, fixed input sequence at once, so there is no such restriction and every position can attend to every other position.

12. **A** — BERT stands for Bidirectional Encoder Representations from Transformers.

13. **B** — BERT uses only a stack of trained Transformer encoder layers; it has no decoder module.

14. 15% of the input words are replaced with a `[MASK]` token, and BERT is trained to predict the original (masked) word using the surrounding bidirectional context.

15. **B** — Text classification (e.g., fraud detection) is explicitly listed as a BERT use case, along with text generation, question-answering, and search engine optimization.

16. BERT is called bidirectional because it considers context from both the words before *and* after a given word simultaneously (rather than only reading left-to-right). This matters for question-answering because understanding a question or passage often requires information from both directions around a word or phrase to correctly infer meaning and provide an accurate answer.
