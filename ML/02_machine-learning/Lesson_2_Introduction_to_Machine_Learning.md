# Introduction to Machine Learning

## Learning Objectives

By the end of this lesson, you will be able to:

- **Analyze the distinctions and applications of machine learning, deep learning, and artificial intelligence** through real-world examples across various technical domains.
- **Differentiate among various machine learning models** and explore how each model learns from data to predict outcomes.
- **Explore Python libraries** for effective data manipulation, visualization, and implementation of machine learning algorithms.

---

## Business Scenario

**ABC Inc.**, an e-commerce company, is struggling with a surge in fraudulent transactions on its website. Its manual review process for transactions has caused delays in order processing and led to a negative customer experience.

To address this, ABC Inc. will use machine learning algorithms to detect fraudulent transactions in real time. These algorithms will be integrated into ABC Inc.'s existing transaction-processing system to flag suspicious transactions and prevent fraud before it happens.

Additionally, the company will use machine learning to predict customer behavior based on past purchase history, thereby improving the recommendation engine's performance. With machine learning, ABC Inc. can:

- Provide a more personalized customer experience
- Streamline order processing
- Increase sales

> **Why this scenario matters:** This is a realistic pattern you will see repeated throughout the industry — a company has a large volume of historical transaction/behavior data, a manual/rule-based process that doesn't scale, and a business goal (fraud reduction, better recommendations) that a learning algorithm can address by finding patterns humans would miss or take too long to find.

---

## What Is Machine Learning?

**Machine Learning (ML)** is a subset of artificial intelligence (AI) that assists systems in learning and improving automatically from experience, without being explicitly programmed for every scenario.

- The term **"machine learning"** was coined by **Arthur Samuel in 1959**, while he was working on a checkers-playing program at IBM that improved its play by learning from its own games.
- ML enables programs to learn automatically from data, making computers more intelligent without constant human intervention — instead of a programmer writing every rule, the system infers the rules (or patterns) itself from examples.

**Example to anchor the definition:** Instead of hand-coding thousands of "if-this-then-that" rules to detect spam email, a machine learning system is shown thousands of emails already labeled "spam" or "not spam." It learns the statistical patterns that separate the two categories (certain words, sender patterns, formatting) and can then classify emails it has never seen before.

### Traditional Approach vs. Machine Learning Approach

The table below contrasts how conventional software engineering solves problems versus how machine learning solves problems:

| Traditional Approach | Machine Learning Approach |
|---|---|
| Uses predefined rules and algorithms explicitly programmed by human developers | Learns from data to make predictions or take actions without being explicitly programmed |
| Relies on explicitly defined logic and rules to perform tasks | Uses statistical techniques and optimization algorithms to learn patterns and make decisions |
| Requires manual feature engineering, where relevant features must be identified and extracted by human experts | Automatically learns features from raw data, reducing the need for manual feature engineering |
| Faces challenges handling complex and unstructured data without significant preprocessing | Handles complex and unstructured data — such as images, text, and audio — without requiring extensive preprocessing |
| Performance depends on the accuracy and completeness of the predefined rules and algorithms | Performance improves with more data and learning iterations, enhancing accuracy and generalization |

**Concrete illustration:** Imagine building a system to approve or reject loan applications.
- *Traditional approach:* A developer sits with a loan officer and writes explicit rules: "If credit score < 600, reject," "If income < $30k AND loan amount > $50k, reject," etc. Every edge case requires a new rule.
- *Machine learning approach:* You instead feed the system thousands of historical applications along with their outcomes (approved/defaulted, approved/repaid, rejected). The algorithm discovers on its own which combinations of features (income, credit history, debt ratio, employment length) are most predictive of default risk — and it can keep improving as more loan outcomes come in over time.

---

## Difference Between ML, DL, and AI

Machine learning (ML), deep learning (DL), and artificial intelligence (AI) are often used interchangeably in casual conversation, but they describe **nested, increasingly specific concepts**:

```
Artificial Intelligence (broadest)
   └── Machine Learning (subset of AI)
          └── Deep Learning (subset of ML)
```

| Concept | Definition | Example |
|---|---|---|
| **Artificial Intelligence (AI)** | The broadest concept — encompasses the simulation of human intelligence in machines, including reasoning, planning, perception, and decision-making, whether or not it involves learning from data. | Self-driving cars (perception, planning, and decision-making combined) |
| **Machine Learning (ML)** | A subset of AI that focuses specifically on algorithms that enable computers to learn from data rather than being explicitly programmed. | Amazon Alexa (learns to better recognize speech patterns and respond to voice commands over time) |
| **Deep Learning (DL)** | A subset of ML that uses neural networks with multiple ("deep") layers to perform complex pattern recognition, such as recognizing patterns in images, speech, and text. | Handwriting recognition (a deep neural network learns to recognize pen strokes and shapes as letters/digits) |

**Why the nesting matters:** Not all AI involves learning from data (some AI systems are purely rule-based, e.g., a classic chess engine using brute-force search with hand-coded heuristics). Not all machine learning is "deep" — many ML algorithms (like linear regression or decision trees) don't use neural networks at all. Deep learning is simply the branch of ML that relies on multi-layered neural networks, which tends to excel at unstructured data like images, audio, and raw text.

### Machine Learning: Example — Chess

In a chess game between a computer and a person, the computer uses **AI** broadly to analyze the game, predict moves, and decide its actions. Within that:

- The AI decides its next move against the opponent using a **complex neural network** (a deep learning component) that learns various features and patterns from the data — this is the "how it evaluates the board" piece.
- The AI also uses **machine learning** to figure out whether the opponent is a beginner, intermediate, or advanced player — this is a classification task learned from patterns in the opponent's move history, allowing the system to adapt its difficulty or strategy.

This example shows how AI, ML, and DL can all be present within a single application, each solving a different part of the overall problem.

---

## Applications of Machine Learning

Machine learning is not confined to a single industry — it shows up anywhere there is enough historical data to learn patterns from. Common applications include:

- **Social media analysis** — analyzing posts, engagement, and networks to detect trends, influencers, or harmful content.
- **Customer service chatbots** — using natural language understanding to interpret customer questions and provide automated responses or route to the right department.
- **Spam filtering** — classifying incoming emails/messages as spam or legitimate based on learned patterns from labeled examples.
- **Sentiment analysis** — determining whether text (reviews, tweets, support tickets) expresses positive, negative, or neutral sentiment, useful for brand monitoring and customer feedback analysis.
- **Online recommendation systems** — suggesting products, videos, or content based on a user's past behavior and the behavior of similar users (e.g., Netflix, Amazon, YouTube).

**Additional real-world context:** Beyond these five, ML also powers fraud detection in banking, medical image diagnosis, predictive maintenance in manufacturing, voice assistants, and self-driving vehicle perception — essentially any domain where "learn from historical examples to make a decision about new, unseen cases" applies.

---

## Machine Learning Algorithms

Machine learning algorithms are the mathematical procedures that allow computers to learn patterns from data and make predictions on their own, without being told the exact rule to follow. Broadly, ML algorithms help applications to:

- **Predict outcomes** — e.g., predicting next month's sales based on historical sales data.
- **Improve performance** — e.g., a recommendation engine getting more accurate over time as it processes more user interactions.
- **Classify the target feature** — e.g., sorting emails into "spam" or "not spam," or images into "cat" or "dog."

These three capabilities — prediction, performance improvement, and classification — are the building blocks behind almost every ML use case you will encounter in this course.

### Data and Machine Learning Algorithms

A critical principle in machine learning is: **the quality and quantity of the provided data determine the algorithm's performance.**

- High-quality, high-quantity data is crucial for machine learning because it ensures better predictions and insights. An algorithm is only as good as the data it learns from — this is often summarized as "garbage in, garbage out."
- Even the most sophisticated algorithm will perform poorly if trained on data that is noisy, biased, incomplete, or too small in volume to capture the true underlying patterns.
- Conversely, a relatively simple algorithm trained on abundant, clean, representative data can often outperform a complex algorithm trained on poor data.

*(Reference cited in the source material: https://academic.oup.com/nsr/article/10/7/nwad125/7147579)*

---

## Types of Machine Learning

Machine learning can be divided into **four main categories**, each characterized by its capacity to predict conditions or identify patterns to produce outcomes:

1. Supervised Learning
2. Unsupervised Learning
3. Semi-Supervised Learning
4. Reinforcement Learning

### 1. Supervised Learning

Supervised learning is a method that uses **labeled data** to predict outcomes, guided by specific input-output pairs. In supervised learning, both the inputs (features) and the outputs (labels/targets) are known during training — the algorithm's job is to learn the mapping between them so it can predict the output for new, unseen inputs.

**Analogy:** Think of a student learning with an answer key. The student (algorithm) is shown many practice problems (inputs) along with the correct answers (outputs/labels). Over time, the student learns the pattern well enough to solve new problems it hasn't seen before, without the answer key.

#### Supervised Learning Algorithms

Some commonly known supervised learning algorithms are:

- **Decision Trees** — a tree-like model of decisions, where each internal node represents a test on a feature and each leaf represents an outcome.
- **Support Vector Machines (SVM)** — finds the optimal boundary (hyperplane) that best separates classes of data.
- **Linear Regression** — predicts a continuous numeric value based on a linear relationship between input features and the output.
- **Logistic Regression** — despite the name, used for classification; predicts the probability that an input belongs to a particular category.

#### Supervised Learning: Examples

- **Predicting temperature rise** based on yearly temperature trends — a regression problem where historical temperature data (labeled with actual recorded values) is used to forecast future temperatures.
- **Sorting waste** based on known waste items and their corresponding waste types — a classification problem where the model learns from labeled examples of "plastic," "paper," "organic," etc.
- **Predicting crop yield** based on seasonal crop quality changes — a regression problem useful in agriculture for planning harvests and supply chains.
- **Spam filtering** — computers learn from labeled emails (marked as "spam" or "not spam" by users) to decide whether new, incoming emails are spam.

**Key takeaway:** Supervised learning always requires labeled training data — this labeling is often the most expensive and time-consuming part of building a supervised model, since it usually requires human annotation.

### 2. Unsupervised Learning

Unsupervised learning allows models to identify patterns and structures in **unlabeled data** without explicit guidance. Instead of being told the "correct answer," the algorithm is given raw data and asked to find structure, groupings, or relationships on its own.

An unlabeled dataset is provided to an unsupervised learning algorithm to discover hidden patterns and recognize relationships between data points — there is no "answer key" to check against.

**Examples:**

- **Image segmentation for object detection** — grouping pixels in an image into segments that correspond to different objects, without being told in advance what those objects are.
- **Identification of user groups based on commonalities** — e.g., clustering customers into segments (budget shoppers, luxury shoppers, frequent buyers) purely from their purchasing behavior, without predefined labels.
- **Identification of anomalies over geographical landscapes** based on data patterns — e.g., detecting unusual land-use changes in satellite imagery without being told in advance what an "anomaly" looks like.

#### Unsupervised Learning: Example

A practical illustration is a system that automatically groups images into distinct categories based on similarities — such as age group or gender — **without any prior labels**. The algorithm looks purely at visual similarity between images and clusters similar-looking images together, discovering the grouping itself rather than being told which category each image belongs to.

**Contrast with supervised learning:** In supervised learning, you'd need every image pre-labeled "child," "adult," "male," "female" before training. In unsupervised learning, the algorithm looks at the raw pixels/features and decides for itself which images "belong together," and a human might only later interpret what each discovered cluster represents.

### 3. Semi-Supervised Learning

Semi-supervised learning uses a combination of a **small amount of labeled data** and a **large amount of unlabeled data** for training. This is a highly practical middle ground because, in the real world, labeling every single data point is often expensive or impractical, but collecting large volumes of raw, unlabeled data is comparatively cheap.

- Like supervised learning, semi-supervised learning aims to learn a function that can accurately predict the output variable from the input variables.
- It uses the unlabeled data to assist the learning process — either by collecting more information about the structure of the data or by improving how well the model generalizes to new examples.
- Because it combines properties of both approaches, semi-supervised learning **falls between supervised and unsupervised learning**.

**Example dataset scenario:** If a dataset contains both labeled and unlabeled data (for instance, 1,000 labeled photos and 100,000 unlabeled photos of the same general subject), semi-supervised learning is the appropriate technique — using the 1,000 known examples as a guide while leveraging the much larger unlabeled set to learn richer patterns.

#### Semi-Supervised Learning: Example — Google Photos

**Google Photos** is a popular real-world example of semi-supervised learning:

- In various instances, uploaders manually label some images (e.g., tagging a person's name).
- Despite Google's platform having no built-in knowledge of who is in a photo, its algorithm can identify and group images of the same person by analyzing visual features like shapes and colors, extending the few labeled examples to the much larger unlabeled photo library.
- Whenever a picture is taken, it gets stored on the Google Cloud platform or a database, continuously growing the pool of unlabeled data the system can leverage.

### 4. Reinforcement Learning

Reinforcement learning (RL) is a type of machine learning where an algorithm (called an **agent**) learns from its **environment** by performing **actions** and receiving either **rewards** or **penalties** as feedback — rather than learning from a static labeled dataset.

- If the program finds the correct solution, the interpreter (environment) **rewards** the algorithm.
- If the outcome is incorrect, the algorithm is **penalized** for the wrong prediction/action. It must reiterate — trying again and adjusting its strategy — until it finds a better result.
- More formally: reinforcement learning involves an **agent interacting with an environment**, learning from rewards and states, to choose the best actions and improve performance over time. This trial-and-error, feedback-driven loop is fundamentally different from supervised learning, where correct answers are provided up front.

**Analogy:** Think of training a dog with treats. The dog (agent) tries different behaviors (actions) in its surroundings (environment). Behaviors that earn a treat (reward) are repeated more often; behaviors that don't (or that are corrected) happen less often over time. The dog never sees an explicit "labeled dataset" of behaviors — it learns purely through repeated interaction and feedback.

#### Reinforcement Learning: Example — YouTube Recommendations

This type of learning is well illustrated by **YouTube recommendations**: a user searches for a particular song, and the program shows a list of available songs (actions the system can take). When the user selects a specific song (positive feedback signal), the system trains itself to remember this and deliver similar results for future searches, based on ongoing user interactions such as likes, views, and shares (continuous reward signals).

#### Reinforcement Learning: Additional Examples

- **Search recommendation engines** — refining what content to surface based on click-through and engagement feedback.
- **Self-driving cars** — learning safe driving actions (accelerate, brake, steer) through simulated or real-world trial and error, rewarded for safe, smooth driving and penalized for collisions or violations.
- **Autocorrect tools** — learning which corrections users accept versus reject, improving suggestions over time.
- **Games where players compete with bots** — game-playing AI (such as in chess, Go, or video games) that improves by playing many games and being rewarded for winning moves.

### Summary Comparison of the Four Types

| Type | Data Used | Goal | Example |
|---|---|---|---|
| Supervised Learning | Fully labeled data (input-output pairs) | Predict a known output for new inputs | Spam filtering, crop yield prediction |
| Unsupervised Learning | Unlabeled data | Discover hidden patterns/structure | Customer segmentation, anomaly detection |
| Semi-Supervised Learning | Small labeled + large unlabeled data | Predict outputs while leveraging unlabeled data | Google Photos face grouping |
| Reinforcement Learning | No fixed dataset; rewards/penalties from an environment | Learn optimal actions through trial and error | Self-driving cars, game-playing bots |

---

## Introduction to Python Packages for Machine Learning

Python is the dominant language for machine learning largely because of its rich ecosystem of specialized libraries. Below are the core libraries introduced in this lesson.

### Core Python Libraries Used in Machine Learning

| Library | Purpose |
|---|---|
| **NumPy** | A powerful library for numerical computing in Python — provides efficient array structures and mathematical operations that underpin most other ML libraries. |
| **Matplotlib** | Performs data visualization and graphical plotting — used to create charts, graphs, and plots to explore and present data. |
| **Pandas** | A versatile data manipulation library in Python, offering data structures like **DataFrames** for organizing, cleaning, and analyzing tabular data. |
| **SciPy** | Solves mathematical equations and processes scientific/statistical algorithms, building on top of NumPy. |
| **Scikit-learn** | Offers efficient, ready-to-use implementations of common machine learning algorithms, facilitating the development, training, and evaluation of ML models. |

**Why these matter together:** In a typical ML workflow, you might use **Pandas** to load and clean a dataset, **NumPy** for underlying numerical operations, **Matplotlib** to visualize distributions and relationships in the data, **SciPy** for statistical tests, and **Scikit-learn** to actually build, train, and evaluate your machine learning model. Learning to use these libraries together is a foundational skill for practical machine learning work, and later lessons in this course will use them hands-on.

---

## Key Takeaways

- Machine learning refers to a machine's ability to learn from data and replicate human-like decision behavior, rather than following explicitly hand-coded rules.
- AI is the broader field that includes machine learning and deep learning, each with unique capabilities for simulating intelligence — AI is the umbrella, ML is a subset of AI, and DL is a subset of ML.
- There are four main types of machine learning: **supervised learning, unsupervised learning, semi-supervised learning, and reinforcement learning** — each suited to different data availability and problem types.
- Python packages are folders with modules that organize code for easy reuse and maintenance, improving development efficiency — libraries like NumPy, Pandas, Matplotlib, SciPy, and Scikit-learn form the practical toolkit for implementing machine learning in Python.

---

## Knowledge Check (From Original Slides)

**Question 1.** Which of the following best describes machine learning?

- A. A subset of artificial intelligence (AI) that assists systems to learn and improve automatically from experience without being explicitly programmed.
- B. A method of programming where developers manually define a set of rules and instructions.
- C. The process of creating a set of fixed logic that a program will follow.
- D. A technique used only for image and speech recognition tasks.

**Correct Answer: A** — Machine learning is a subset of AI that enables systems to learn and improve automatically from experience without explicit programming.

**Question 2.** Which example illustrates the use of machine learning to enhance customer experience in an e-commerce company?

- A. ABC Inc. using predefined rules for transaction processing.
- B. ABC Inc. using manual review to detect fraudulent transactions.
- C. ABC Inc. using machine learning algorithms to detect real-time fraudulent transactions and predict customer behavior.
- D. ABC Inc. using machine learning solely for inventory management.

**Correct Answer: C** — ABC Inc. uses machine learning to detect fraudulent transactions in real time and predict customer behavior to enhance the recommendation engine and customer experience.

**Question 3.** What distinguishes deep learning (DL) from machine learning (ML) and artificial intelligence (AI)?

- A. Deep Learning is a subset of AI focused on learning from data.
- B. Deep Learning uses neural networks with multiple layers for complex pattern recognition.
- C. Deep Learning encompasses the simulation of human intelligence in machines.
- D. Deep Learning involves manually defined rules and instructions.

**Correct Answer: B** — Deep learning is a subset of ML that uses neural networks with multiple layers for complex pattern recognition, such as recognizing patterns in images, speech, and text.

---

## 📝 Practice Questions

The following are **new** questions (not from the original slides) designed to test and reinforce your understanding of this lesson's concepts.

**Q1.** Which of the following best defines the relationship between AI, ML, and DL?

- A. AI, ML, and DL are unrelated, competing fields.
- B. DL is the broadest field, containing both AI and ML.
- C. AI is the broadest field; ML is a subset of AI; DL is a subset of ML.
- D. ML and DL are identical terms for the same concept.

**Q2.** A company wants to group its customers into segments based on purchasing behavior, but it has no predefined categories or labels for the customers. Which type of machine learning is most appropriate?

- A. Supervised learning
- B. Unsupervised learning
- C. Reinforcement learning
- D. Semi-supervised learning

**Q3.** In the chess game example from this lesson, what specific task does the AI use machine learning for (as distinct from the neural network's move evaluation)?

- A. To render the chessboard graphics
- B. To determine if the opponent is a beginner, intermediate, or advanced player
- C. To enforce the rules of chess
- D. To time each player's moves

**Q4.** Which statement about reinforcement learning is TRUE?

- A. It requires a fully labeled dataset before training begins.
- B. It learns exclusively from unlabeled, static data with no feedback loop.
- C. It learns through an agent taking actions in an environment and receiving rewards or penalties.
- D. It cannot be used for real-time decision-making tasks like self-driving cars.

**Q5.** Why is Google Photos considered an example of semi-supervised learning?

*(Short answer)*

**Q6.** Name two supervised learning algorithms mentioned in this lesson.

*(Short answer)*

**Q7.** Which Python library would you use specifically to create a bar chart or scatter plot to visualize your dataset?

- A. NumPy
- B. Pandas
- C. Matplotlib
- D. Scikit-learn

**Q8.** What is the primary reason data quality and quantity are described as crucial to machine learning algorithm performance?

*(Short answer)*

**Q9.** A spam filter is trained on a large set of emails, each already marked "spam" or "not spam" by users. Which type of machine learning does this represent?

- A. Unsupervised learning
- B. Reinforcement learning
- C. Supervised learning
- D. Semi-supervised learning

**Q10.** Which of the following is NOT one of the four main types of machine learning covered in this lesson?

- A. Supervised learning
- B. Transfer learning
- C. Semi-supervised learning
- D. Reinforcement learning

**Q11.** Explain, in your own words, one key difference between the traditional programming approach and the machine learning approach to solving a problem.

*(Short answer)*

**Q12.** Which Python library provides the DataFrame data structure commonly used for organizing and manipulating tabular data?

- A. Matplotlib
- B. SciPy
- C. Pandas
- D. NumPy

**Q13.** A self-driving car learns to make better driving decisions over time by being rewarded for smooth, safe driving and penalized for unsafe maneuvers, with no fixed "correct answer" dataset provided in advance. Which type of machine learning best describes this scenario?

- A. Supervised learning
- B. Unsupervised learning
- C. Semi-supervised learning
- D. Reinforcement learning

**Q14.** Who coined the term "machine learning," and in what year?

*(Short answer)*

### Answers

**A1. C** — AI is the broadest field, ML is a subset of AI focused on learning from data, and DL is a further subset of ML that uses multi-layer neural networks. The nesting is AI ⊃ ML ⊃ DL.

**A2. B** — With no labels or predefined categories, the algorithm must discover groupings on its own from the raw data — this is the defining characteristic of unsupervised learning (e.g., clustering).

**A3. B** — Per the lesson's chess example, the AI uses machine learning specifically to classify the opponent's skill level (beginner/intermediate/advanced) based on observed play patterns, separate from the neural network used to evaluate moves.

**A4. C** — Reinforcement learning is defined by an agent interacting with an environment, taking actions, and learning from reward/penalty feedback rather than from a static labeled dataset.

**A5. Sample answer:** Google Photos combines a small number of user-provided labels (e.g., a name tag on a photo) with a very large number of unlabeled photos, then uses visual similarity (shapes, colors) to extend those labels across the unlabeled set — the defining trait of semi-supervised learning.

**A6. Sample answer:** Any two of: Decision Trees, Support Vector Machines, Linear Regression, Logistic Regression.

**A7. C** — Matplotlib is the library in this lesson dedicated to data visualization and graphical plotting, such as bar charts and scatter plots.

**A8. Sample answer:** Because machine learning algorithms find patterns purely from the data they are given — insufficient, noisy, or low-quality data leads to poor or unreliable patterns and predictions ("garbage in, garbage out"), regardless of how sophisticated the algorithm is.

**A9. C** — Supervised learning, because the algorithm learns from emails that already carry known labels ("spam" / "not spam"), i.e., labeled input-output pairs.

**A10. B** — Transfer learning is a real ML technique, but it is not one of the four categories introduced in this lesson (supervised, unsupervised, semi-supervised, reinforcement).

**A11. Sample answer:** The traditional approach relies on developers explicitly writing fixed rules/logic to handle every case, while the machine learning approach learns the underlying patterns and decision logic directly from data, allowing it to improve automatically as more data becomes available and to better handle complex or unstructured inputs.

**A12. C** — Pandas offers the DataFrame structure specifically designed for organizing, cleaning, and manipulating tabular (rows-and-columns) data.

**A13. D** — This is reinforcement learning: an agent (the car's driving system) learns optimal actions through a continuous reward/penalty feedback loop rather than from a fixed labeled dataset.

**A14. Sample answer:** Arthur Samuel coined the term "machine learning" in 1959, while developing a self-improving checkers-playing program.
