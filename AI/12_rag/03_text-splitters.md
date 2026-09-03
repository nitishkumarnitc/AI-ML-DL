# 3. Text Splitters in LangChain

> 📺 [Watch on YouTube](https://www.youtube.com/watch?v=SEWS9P4ODmc&list=PLKnIA16_Rmva0dRLWEHLznSHKbFD_RJfX) · ⏱️ ~59 min · CampusX — Generative AI using LangChain

---

## 🎯 What You'll Learn

- What "text splitting" means and why it's the **second core component** of a RAG pipeline (right after Document Loaders).
- Three concrete reasons splitting improves LLM-application quality: context-length limits, better downstream results (embedding / semantic search / summarization), and computational efficiency.
- Four splitting strategies LangChain provides, from simplest to most sophisticated:
  1. **Length-based** — `CharacterTextSplitter`
  2. **Text-structure-based** — `RecursiveCharacterTextSplitter`
  3. **Document-structure-based** — `RecursiveCharacterTextSplitter.from_language()` for code / Markdown / HTML
  4. **Semantic-meaning-based** — `SemanticChunker` (experimental)
- Exactly how `RecursiveCharacterTextSplitter`'s separator fallback and chunk-merging logic works, traced through a worked example.
- What `chunk_size` and `chunk_overlap` control, and a rule of thumb for setting `chunk_overlap`.
- How to wire a **Document Loader → Text Splitter** pipeline end to end.

---

## 📖 Overview / Why Split?

**Definition:** Text splitting is the process of breaking large pieces of text — articles, PDFs, HTML pages, books — into smaller, manageable pieces ("chunks") that an LLM can handle effectively. The tool/class that performs this operation is called a **text splitter**.

Where this sits in the pipeline:

```
Document Loading  →  Text Splitting  →  Embedding  →  Vector Store  →  Retrieval
   (video 2)          (this video)
```

You almost never want to hand a huge document to an LLM (or an embedding model) as one single blob. Three reasons come up again and again:

### 1. Overcoming context-length limits
Every LLM (and every embedding model) has a maximum input size — its **context window**. Say a model's context length is 50,000 tokens (for simplicity, treat a token ≈ a word here, even though they aren't strictly equal). If you try to summarize a PDF with 100,000+ words, you simply cannot pass the whole thing in one call — you'd breach the limit. Splitting the document into chunks that each fit inside the context window is what makes processing possible at all.

### 2. Better results on downstream tasks
Whatever task you run on top of your text — embedding, semantic search, summarization — tends to produce **better results on small chunks than on one giant blob**:

- **Embedding quality.** An embedding model compresses a piece of text's meaning into a fixed-size vector. The bigger and more topically mixed the text, the harder it is for one vector to represent it well. Example from the video: a document with three paragraphs, one about each of CSK, MI, and RCB (IPL teams). Embedding the whole document as a single vector captures the combined meaning poorly. Splitting it into three chunks — one per team — and embedding each separately produces vectors that each capture their paragraph's semantic meaning much more precisely.
- **Semantic search quality.** If you've embedded documents per-chunk (e.g. one vector per team), an incoming query ("Which IPL team does Virat Kohli play for?") is embedded too and compared against each stored vector via similarity. Search over well-scoped chunks is measurably more precise than search over one large, unfocused vector.
- **Summarization quality.** LLMs are empirically not great at handling very large inputs directly — they can "drift" off-topic or hallucinate details that aren't actually in the source document. Splitting first and processing chunk-by-chunk (or hierarchically) tends to produce more faithful summaries.

### 3. Optimizing computational resources
Processing many small chunks instead of one huge document reduces memory footprint (less to hold in memory at once) and — because chunks are independent — allows **parallel processing**, which large monolithic documents don't allow.

---

## 🔑 Splitting Strategies

LangChain offers (broadly) four families of text-splitting strategy, covered here in increasing order of sophistication.

### 1. Length-based splitting (`CharacterTextSplitter`)

The simplest and fastest approach. You decide a fixed **chunk size** up front — in characters or in tokens — then walk through the text from the start, and every time you hit that many units, you cut a chunk and continue from where you left off.

Example: chunk size = 100 characters. Traverse the text; at character 100, cut chunk 1; resume, traverse another 100, cut chunk 2; and so on until the text is exhausted (the last chunk is whatever remains, even if shorter).

**Advantages:** conceptually trivial, easy to implement, and very fast.

**Disadvantage:** it pays no attention to linguistic structure, grammar, or semantic meaning. It will happily cut a chunk mid-word, mid-sentence, or mid-paragraph, purely because the character count hit its limit. This means related information can end up split across two chunks — which hurts embedding quality, since half the context for a topic lives in one chunk and half in another. Because of this, `CharacterTextSplitter` is fast but not the go-to choice in practice.

### 2. Text-structure-based splitting (`RecursiveCharacterTextSplitter`)

This is the most widely used text splitter in LangChain. Instead of blindly cutting at a character count, it leans on the fact that text has an **inherent hierarchical structure**: documents are organized into paragraphs → paragraphs into sentences → sentences into words → words into characters.

**How it works — the separator fallback hierarchy:**

The splitter is given an ordered list of separators (LangChain's default is `["\n\n", "\n", " ", ""]`), representing, in order: paragraph breaks, line/sentence breaks, word boundaries (space), and finally raw characters. The algorithm tries each separator in order, only falling back to the next one where necessary:

1. Try splitting on `"\n\n"` (paragraph breaks).
2. For any resulting piece that's still **bigger than `chunk_size`**, split *that piece* further on `"\n"` (sentence/line breaks).
3. For any piece still too big, split on `" "` (words).
4. If a piece is still too big even at the word level, fall back to splitting on `""` (individual characters).

Critically, after breaking things down, the splitter also **merges adjacent small pieces back together** — greedily combining neighboring fragments (with the separator that joins them) as long as the combined size stays within `chunk_size`. This means it always tries to produce chunks that are as close to `chunk_size` as possible **without cutting a sentence or word if it can be avoided** — a big improvement over the length-based approach.

**Worked example.** Take the text:

```
My name is Nitish
I am 35 years old

I live in Gurgaon
How are you
```

(two paragraphs, separated by a blank line; each paragraph has two lines/sentences.)

- With **`chunk_size = 10`**: Splitting by paragraph gives two pieces (34 and 28 "characters" of content), both too big → split by line into 4 sentences (17, 17, 17, 11), still all too big → split by word. Individual words (`My`, `name`, `is`, `Nitish`, `I`, `am`, `35`, ...) are now all under 10 characters. The algorithm then greedily **re-merges** adjacent words as long as the merged size stays ≤ 10, producing the final chunks: `"My name is"`, `"Nitish"`, `"I am 35"`, `"years old"`, `"I live in"`, `"Gurgaon"`, `"How are"`, `"you"` — 8 chunks total, never breaking in the middle of a word.
- With **`chunk_size = 25`**: Paragraphs (34, 28) are still too big → split into the 4 sentences (17, 17, 17, 11), all now ≤ 25 → try to merge sentence pairs back into paragraphs, but each paragraph's combined length (35 and ~29) exceeds 25, so no merge happens. Result: 4 chunks, one per sentence.
- With **`chunk_size = 50`**: Both paragraphs (34 and 28 characters) already fit under 50, so no further splitting is needed. Merging the two paragraphs together would exceed 50, so they stay separate. Result: 2 chunks, one per paragraph.

This demonstrates the core intuition: **increase `chunk_size` and the splitter naturally gravitates toward paragraph-level chunks; decrease it and it gravitates toward sentence-, then word-, then (only as a last resort) character-level chunks.** This adaptivity is why `RecursiveCharacterTextSplitter` is the default choice for most RAG pipelines.

### 3. Document-structure-based splitting (`RecursiveCharacterTextSplitter.from_language()`)

Plain-text assumptions (paragraphs → sentences → words) break down for documents that aren't natural-language prose — source code, Markdown, HTML. These have their own structural units: a Python file is organized around `class` and `def` keywords and loops; a Markdown file is organized around headings, lists, and code fences.

The fix is the *same* `RecursiveCharacterTextSplitter` algorithm, but with a **different, language-specific separator list**. For Python, the separator list starts with class/function boundaries (roughly: `"\nclass "`, `"\ndef "`, `"\n\tdef "`) before falling back to the same generic `"\n\n"`, `"\n"`, `" "`, `""` hierarchy used for plain text. For Markdown, separators are things like headings, horizontal rules, and code fences, again falling back to the generic hierarchy. This is exposed via the `from_language()` factory method together with a `Language` enum (e.g. `Language.PYTHON`, `Language.MARKDOWN`), and LangChain supports many languages this way — Python, JavaScript, TypeScript, Java, PHP, Go, Ruby, HTML, Markdown, LaTeX, and more.

In practice, this means a Python file gets split along class/function boundaries first (each method landing in its own logical chunk where possible) instead of being cut arbitrarily mid-line, and a Markdown document gets split along its heading structure instead of mid-sentence.

### 4. Semantic-meaning-based splitting (`SemanticChunker`)

Both previous strategies decide *where* to cut based on **length** or **structural syntax** — never on what the text actually *means*. This fails in a specific, important scenario: a single paragraph that covers two unrelated topics.

**Motivating example from the video:** a paragraph that starts by discussing agriculture/farmers, then — without a paragraph break — pivots to talking about IPL cricket, followed by a second paragraph about terrorism. Structurally this is just two paragraphs, so length- or structure-based splitting would produce two chunks (agriculture+IPL mixed together, then terrorism). Ideally, though, you want **three** chunks — one per actual topic — because embedding a chunk that blends two unrelated topics produces a poor-quality vector for both.

**How `SemanticChunker` works:**
1. Break the text into individual sentences.
2. Generate an embedding vector for every sentence (using any embedding model, e.g. OpenAI embeddings).
3. Using a sliding window, compute the cosine similarity between each pair of consecutive sentence embeddings (s1↔s2, s2↔s3, s3↔s4, …).
4. Wherever similarity drops **abruptly**, that's flagged as a topic boundary — a split point.
5. The "how abrupt is abrupt" decision is controlled by a **breakpoint threshold type**, e.g.:
   - `standard_deviation` — flag a boundary where the distance between consecutive sentences exceeds N standard deviations from the mean.
   - `percentile`
   - `interquartile`
   - `gradient`

**Caveats (as observed in the video):** this technique lives in `langchain_experimental` (not the core `langchain` package) because it's still an experimental, evolving idea. In hands-on testing, results were inconsistent — e.g. a sentence about weather ("the sun was bright and the air smelled of earth and fresh grass") that should have belonged to the agriculture chunk instead got grouped with the IPL sentences. Tightening/loosening the threshold (e.g. raising it to 3 standard deviations) changes behavior a lot — too loose and everything collapses back into one chunk. As embedding models keep improving, this approach is expected to mature, but as of this video, `RecursiveCharacterTextSplitter` remains the most reliable, most-used option.

### `chunk_size` and `chunk_overlap`

Two parameters control (almost) every splitter above:

- **`chunk_size`** — the maximum size of each chunk (in characters, or tokens, depending on the `length_function` used).
- **`chunk_overlap`** — how many characters/tokens of overlap to keep between the *end* of one chunk and the *start* of the next.

**Why overlap matters:** because length-based (and to a lesser extent, structure-based) splitting can cut abruptly in the middle of useful context, some information can get "orphaned" at a chunk boundary — half of an idea in chunk N, the other half in chunk N+1. Overlap re-includes a bit of the previous chunk's tail at the start of the next chunk, so that context isn't lost outright; it's a small trade-off in exchange for continuity across the cut point.

**Trade-off:** more overlap → more preserved context, but also more chunks overall → more storage and compute (since overlapping regions are stored/embedded twice). Too little overlap and you risk losing context at every boundary; too much and you multiply your chunk count for little added benefit.

**Rule of thumb given in the video:** for RAG applications, set `chunk_overlap` to roughly **10–20% of `chunk_size`** (e.g. `chunk_size=100` → `chunk_overlap` somewhere around 10–20), scaling proportionally as `chunk_size` grows.

---

## 💻 Code Examples

### 1. Length-based splitting — `CharacterTextSplitter`

```python
from langchain_text_splitters import CharacterTextSplitter
# (equivalently: from langchain.text_splitter import CharacterTextSplitter)

text = """... a large block of plain text ..."""

splitter = CharacterTextSplitter(
    chunk_size=100,
    chunk_overlap=0,
    separator="",   # cut purely on character count, ignoring structure
)

chunks = splitter.split_text(text)
print(len(chunks))   # number of chunks produced
print(chunks[0])     # the first chunk
```

### 2. Connecting a Document Loader to a Text Splitter

```python
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import CharacterTextSplitter

# 1. Load — one Document object per PDF page
loader = PyPDFLoader("dl_curriculum.pdf")
docs = loader.load()

# 2. Split — split_documents() works directly on Document objects
splitter = CharacterTextSplitter(chunk_size=200, chunk_overlap=0, separator="")
chunks = splitter.split_documents(docs)

print(len(chunks))            # more chunks than pages, since each page can split further
print(chunks[0].page_content) # the text of the first chunk
```

Each item returned by `split_documents()` is itself a `Document` object (with `page_content` and `metadata`), not a raw string — so downstream code (embedding, storing, etc.) can keep working with `Document`s throughout the pipeline.

### 3. `chunk_overlap` in action

```python
splitter = CharacterTextSplitter(
    chunk_size=100,
    chunk_overlap=20,   # last ~20 characters of chunk N reappear at the start of chunk N+1
    separator="",
)
chunks = splitter.split_text(text)
```

### 4. Text-structure-based splitting — `RecursiveCharacterTextSplitter`

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

text = """Space exploration has led to incredible scientific discoveries...

(more paragraphs...)"""

splitter = RecursiveCharacterTextSplitter(
    chunk_size=100,
    chunk_overlap=0,
    # separators default to ["\n\n", "\n", " ", ""] — override only if needed
)

chunks = splitter.split_text(text)
print(len(chunks))     # e.g. 5 chunks at chunk_size=100
print(chunks[0])
```

Raising `chunk_size` (e.g. to 300, then 500) on the same text shows the chunk count dropping — larger sizes let entire sentences, then entire paragraphs, fit in a single chunk without being forced to split further.

### 5. Document-structure-based splitting — code and Markdown

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

python_code = """
class ChatBot:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"Hello, I am {self.name}"

bot = ChatBot("Nitish")
if bot:
    print(bot.greet())
"""

python_splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.PYTHON,
    chunk_size=300,
    chunk_overlap=0,
)
chunks = python_splitter.split_text(python_code)
print(len(chunks))
print(chunks[0])   # e.g. the class + constructor land together
```

```python
markdown_text = """
# My Project

## Features
- Fast
- Simple

## Getting Started
Install with pip and run `main.py`.
"""

markdown_splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.MARKDOWN,
    chunk_size=200,
    chunk_overlap=0,
)
chunks = markdown_splitter.split_text(markdown_text)
print(len(chunks))   # tends toward one chunk per heading section, once chunk_size is large enough
```

The same `from_language()` call works for `Language.JS`, `Language.JAVA`, `Language.PHP`, `Language.HTML`, and many others — only the `language` argument changes.

### 6. Semantic-meaning-based splitting — `SemanticChunker`

```python
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings

text = """... paragraph mixing agriculture and IPL topics ...

... paragraph about terrorism ..."""

splitter = SemanticChunker(
    OpenAIEmbeddings(),
    breakpoint_threshold_type="standard_deviation",
    breakpoint_threshold_amount=1,   # split wherever similarity drops > 1 std. dev.
)

docs = splitter.create_documents([text])
print(len(docs))          # ideally 3 chunks — one per actual topic
print(docs[0].page_content)
```

Raising `breakpoint_threshold_amount` (e.g. to `3`) makes the splitter more tolerant of context shifts, producing fewer (larger) chunks; lowering it makes it split more aggressively.

---

## 📊 When to Use Which

| Strategy | Class / API | Best for | Strength | Weakness |
|---|---|---|---|---|
| Length-based | `CharacterTextSplitter` | Quick prototyping, uniform chunk sizes, speed-critical pipelines | Extremely simple and fast | Ignores grammar/meaning — cuts mid-word, mid-sentence, mid-paragraph |
| Text-structure-based | `RecursiveCharacterTextSplitter` | The default choice for most plain-text RAG pipelines | Recursively falls back through paragraph → sentence → word → character, and merges small fragments back up to `chunk_size` — rarely cuts mid-word | Still purely length/structure-driven — has no notion of topical meaning |
| Document-structure-based | `RecursiveCharacterTextSplitter.from_language(...)` | Source code (Python, JS, Java, PHP, ...), Markdown, HTML | Splits along real logical units — classes, functions, headings | Only as good as the predefined separators for that language/format |
| Semantic-meaning-based | `SemanticChunker` (`langchain_experimental`) | Text where topics shift within a paragraph/structure, and embedding quality matters most | Splits by actual meaning shift, not by position | Experimental; requires embedding calls (slower, costs money); results can be inconsistent |

---

## 🧠 Key Takeaways

- **Text splitting = breaking a large document into smaller, LLM-manageable chunks.** It's the second core component of a RAG pipeline, right after document loading.
- **Three reasons splitting matters:** (1) it works around hard context-length limits of LLMs and embedding models, (2) it improves the quality of downstream tasks — embedding, semantic search, and summarization all perform better on focused chunks than on one giant blob, and (3) it reduces memory usage and enables parallel processing.
- **`CharacterTextSplitter`** (length-based) is the simplest and fastest splitter but ignores structure entirely — it will cut mid-word or mid-sentence.
- **`RecursiveCharacterTextSplitter`** (text-structure-based) is the most commonly used splitter. It tries a hierarchy of separators (`"\n\n"` → `"\n"` → `" "` → `""`), recursively splitting only pieces that exceed `chunk_size`, and then **merges small adjacent pieces back together** up to `chunk_size` — always favoring natural boundaries over arbitrary cuts.
- **`RecursiveCharacterTextSplitter.from_language()`** extends the same algorithm to code, Markdown, and HTML by swapping in format-specific separators (e.g. `class`/`def` for Python, headings/code-fences for Markdown).
- **`SemanticChunker`** (semantic-meaning-based, experimental) splits based on where sentence-embedding similarity drops abruptly, rather than on position — the only strategy of the four that reasons about actual meaning. It's promising but currently experimental and less reliable in practice.
- **`chunk_size`** caps how big a chunk can be; **`chunk_overlap`** re-includes a bit of the previous chunk at the start of the next one to preserve context across the cut. A good starting point for RAG is `chunk_overlap` ≈ **10–20% of `chunk_size`**.
- Document loaders and text splitters compose directly: `loader.load()` → `splitter.split_documents(docs)`, producing a list of `Document` objects ready for embedding.

---

## ❓ Revision Questions

1. What is text splitting, and where does it sit in the overall RAG/document-indexing pipeline?
2. Give three distinct reasons why splitting a large document before processing improves the quality of an LLM-powered application.
3. Using the IPL-teams example (CSK / MI / RCB), explain why embedding three separate paragraphs produces better vectors than embedding them as one combined paragraph.
4. What are `chunk_size` and `chunk_overlap`? What overlap ratio is generally recommended for RAG applications, and why is more overlap not always better?
5. Walk through how `RecursiveCharacterTextSplitter` would split the text `"My name is Nitish\nI am 35 years old\n\nI live in Gurgaon\nHow are you"` with `chunk_size=25`. Which separator does it stop at, and why doesn't it merge the two resulting chunks per paragraph back together?
6. What is the default separator list used by `RecursiveCharacterTextSplitter`, and in what order are the separators tried?
7. How does `RecursiveCharacterTextSplitter.from_language(language=Language.PYTHON, ...)` differ from a plain `RecursiveCharacterTextSplitter`? What happens if the input text isn't valid Python?
8. Describe how `SemanticChunker` decides where to place a chunk boundary. What role does `breakpoint_threshold_type` (e.g. `standard_deviation`) play?
9. Give an example of a document that would be split incorrectly by both length-based and text-structure-based splitters, but correctly by a semantic-meaning-based splitter.
10. Why is `SemanticChunker` imported from `langchain_experimental` rather than the core `langchain` package, and what practical downsides does the video call out for it?
