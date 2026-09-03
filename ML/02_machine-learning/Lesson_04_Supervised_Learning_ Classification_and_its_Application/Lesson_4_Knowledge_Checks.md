# Lesson 4 Knowledge Checks — Supervised Learning: Classification and its Application

## Concept Primer

**Classification** is a supervised learning task where the model learns to assign a discrete label (class) to an input based on labeled training examples. Algorithms are commonly grouped into four categories: **binary classification** (two possible classes, e.g., spam vs. not spam), **multi-class classification** (more than two mutually exclusive classes, e.g., digit recognition 0–9), **multi-label classification** (an instance can belong to more than one class simultaneously, e.g., tagging a news article with several topics), and **imbalanced classification** (the classes are not represented equally in the data, e.g., fraud detection where fraud cases are rare). Common algorithms used to solve these problems include logistic regression, decision trees, k-nearest neighbors, support vector machines, naive Bayes, and neural networks.

**Logistic regression** is one of the most widely used classification algorithms. Despite the name, it is a classification method, not a regression method for continuous outputs. It models the probability that an instance belongs to a given class by passing a linear combination of the input features through the **sigmoid (logistic) function**, which squashes any real number into the range (0, 1). A threshold (typically 0.5) is then applied to this probability to produce the final class prediction. The line (or hyperplane in higher dimensions) where the model is equally uncertain between classes — i.e., where predicted probability equals 0.5 — is called the **decision boundary**. For logistic regression, this boundary is linear, which means it works best when classes are linearly (or near-linearly) separable; more complex, non-linear boundaries typically require algorithms like decision trees, kernel SVMs, or neural networks.

To find the model parameters (weights) that best fit the data, logistic regression minimizes a **cost function** (typically log loss / cross-entropy) using an optimization algorithm such as **gradient descent**. Standard (batch) gradient descent computes the gradient of the cost function using the *entire* training dataset before updating the weights — this gives a smooth, stable path to the minimum but becomes very slow and memory-intensive on large datasets. **Stochastic gradient descent (SGD)** instead updates the weights using only *one* (or a small mini-batch of) training example(s) at a time. This makes each individual update far less computationally expensive and allows the model to start learning and converge much faster in practice on large datasets, though the path to the minimum is noisier and SGD does not guarantee reaching the exact global minimum.

Once a classifier is trained, its performance is evaluated on a held-out test set using a **confusion matrix**, a table that cross-tabulates actual classes against predicted classes into four outcomes: **True Positives (TP)** — correctly predicted positive; **True Negatives (TN)** — correctly predicted negative; **False Positives (FP)** — negative cases incorrectly predicted as positive (a "Type I error"); and **False Negatives (FN)** — positive cases incorrectly predicted as negative (a "Type II error"). From these four counts, several key metrics are derived. **Accuracy** = (TP + TN) / (TP + TN + FP + FN) measures overall correctness but can be misleading on imbalanced datasets. **Precision** = TP / (TP + FP) measures how many of the predicted positives were actually correct (important when false positives are costly, e.g., flagging legitimate email as spam). **Recall (Sensitivity)** = TP / (TP + FN) measures how many of the actual positives were correctly identified (important when false negatives are costly, e.g., missing a disease diagnosis). The **F1-score** is the harmonic mean of precision and recall, 2·(Precision·Recall)/(Precision+Recall), and is useful when you need a single metric that balances both, especially on imbalanced data.

Finally, the **ROC (Receiver Operating Characteristic) curve** plots the True Positive Rate (recall) against the False Positive Rate at various classification thresholds, showing the trade-off between catching positives and generating false alarms as the decision threshold changes. The **AUC (Area Under the Curve)** summarizes this curve into a single number between 0 and 1: an AUC of 0.5 indicates the model performs no better than random guessing, while an AUC closer to 1 indicates excellent separability between classes, regardless of the specific threshold chosen. AUC-ROC is especially useful for comparing models independent of a fixed decision threshold and is more robust to class imbalance than accuracy alone.

---

## Knowledge Check Questions

**1. What are the types of classification algorithms?**

- **A.** Binary classification, multi-class classification, multi-label classification, and imbalance classification
- **B.** Linear regression, logistic regression, decision trees, and k-nearest neighbors
- **C.** Neural networks, random forests, and support vector machines
- **D.** Naive Bayes, multinomial Bayes, and Bernoulli Bayes

**2. What is the advantage of stochastic gradient descent over the gradient descent algorithm?**

- **A.** It guarantees to reach the minimum point of the function.
- **B.** It is less computationally expensive than gradient descent.
- **C.** It provides more accurate results than gradient descent.
- **D.** It reduces the number of computations required to complete the algorithm.

---

## Answers

**1. Correct answer: A — Binary classification, multi-class classification, multi-label classification, and imbalance classification.**
These four categories describe classification problems by the nature and distribution of their target classes (two classes, several mutually exclusive classes, overlapping/multiple classes per instance, and unevenly distributed classes, respectively). Options B, C, and D list specific *algorithms* (e.g., logistic regression, random forests, naive Bayes variants), not fundamental *types* of classification problems.

**2. Correct answer: B — It is less computationally expensive than gradient descent.**
Stochastic gradient descent updates model weights using one (or a small batch of) training example(s) at a time instead of the full dataset, so each update requires far fewer computations, making it much faster and more scalable on large datasets. It does not guarantee reaching the exact minimum (A is false — it can oscillate around the minimum), it is not inherently more accurate (C is false), and while it does reduce computation per step, "less computationally expensive" (B) is the precise textbook framing of this advantage as given in the source material's answer key.

---

## 📝 Additional Practice Questions

**Q1 (MCQ).** In logistic regression, what function is used to map a linear combination of inputs to a probability between 0 and 1?
- **A.** ReLU function
- **B.** Sigmoid function
- **C.** Softmax-only function
- **D.** Identity function

**Q2 (MCQ).** A model predicts "positive" for 100 emails. Of those, 80 are actually spam (true positives) and 20 are legitimate emails wrongly flagged (false positives). What is the precision of this model?
- **A.** 0.20
- **B.** 0.50
- **C.** 0.80
- **D.** 1.00

**Q3 (MCQ).** Which evaluation metric is most appropriate when the cost of missing a true positive (false negative) is very high, such as in disease diagnosis?
- **A.** Precision
- **B.** Recall
- **C.** Specificity
- **D.** R-squared

**Q4 (Short answer).** Explain in your own words what a "decision boundary" is in the context of a classification algorithm.

**Q5 (MCQ).** A dataset has 950 negative examples and 50 positive examples. A naive model that always predicts "negative" achieves what accuracy, and why is accuracy a poor metric here?
- **A.** 5% accuracy; because it never predicts positive
- **B.** 50% accuracy; because the classes are balanced
- **C.** 95% accuracy; because the dataset is imbalanced and accuracy ignores class distribution
- **D.** 100% accuracy; because negatives dominate

**Q6 (Short answer).** What does an AUC-ROC score of 0.5 indicate about a binary classifier's performance?

**Q7 (MCQ).** Which of the following is NOT one of the four outcomes recorded in a confusion matrix for binary classification?
- **A.** True Positive
- **B.** False Negative
- **C.** Mean Squared Error
- **D.** True Negative

**Q8 (Short answer).** Why might a data scientist prefer the F1-score over plain accuracy when evaluating a classifier trained on an imbalanced dataset?

**Q9 (MCQ).** Multi-label classification differs from multi-class classification in what key way?
- **A.** Multi-label allows an instance to belong to more than one class at the same time; multi-class assigns exactly one class per instance.
- **B.** Multi-label only applies to binary problems.
- **C.** Multi-class always requires neural networks.
- **D.** There is no difference; the terms are interchangeable.

**Q10 (Short answer).** Describe one practical trade-off between using batch gradient descent versus stochastic gradient descent when training a classifier on a very large dataset.

### Answers

**A1: B — Sigmoid function.**
The sigmoid function, σ(z) = 1/(1+e⁻ᶻ), maps any real-valued input to a value strictly between 0 and 1, which is exactly the range needed to represent a probability. ReLU (used mainly in hidden layers of neural networks) and the identity function do not bound outputs to (0,1), and softmax is the multi-class generalization of sigmoid, not the base binary function.

**A2: C — 0.80.**
Precision = TP / (TP + FP) = 80 / (80 + 20) = 0.80. This means 80% of the emails the model flagged as spam were actually spam.

**A3: B — Recall.**
Recall = TP / (TP + FN) measures the proportion of actual positive cases (e.g., diseased patients) that the model successfully identifies. Maximizing recall reduces false negatives, which is critical when missing a true positive carries a high cost (e.g., an undiagnosed illness).

**A4:** A decision boundary is the surface (a line in 2D, a plane or hyperplane in higher dimensions) that a classification model uses to separate the feature space into regions corresponding to different predicted classes. Points falling on one side of the boundary are assigned one class, and points on the other side are assigned another; the boundary's shape (linear vs. non-linear) depends on the algorithm used (e.g., logistic regression produces a linear boundary, while decision trees or kernel SVMs can produce non-linear boundaries).

**A5: C — 95% accuracy; because the dataset is imbalanced and accuracy ignores class distribution.**
Always predicting "negative" is correct for all 950 negative examples and wrong for all 50 positive examples, giving 950/1000 = 95% accuracy despite the model having zero ability to detect positives. This illustrates why accuracy alone is misleading on imbalanced data, and why metrics like precision, recall, F1, or AUC-ROC are preferred in such cases.

**A6:** An AUC-ROC score of 0.5 means the classifier's ability to distinguish between the positive and negative classes is no better than random guessing — plotting its ROC curve would produce roughly a straight diagonal line from (0,0) to (1,1). A well-performing classifier should have an AUC well above 0.5, approaching 1.0.

**A7: C — Mean Squared Error.**
Mean Squared Error is a regression evaluation metric that measures the average squared difference between predicted and actual continuous values; it is not a component of the confusion matrix. The confusion matrix for binary classification consists of True Positive, True Negative, False Positive, and False Negative counts.

**A8:** Accuracy treats all correct predictions equally and can be dominated by the majority class in an imbalanced dataset (a model can score high accuracy just by always predicting the majority class, as shown in Q5). The F1-score, being the harmonic mean of precision and recall, penalizes models that neglect the minority class (i.e., models with low recall or low precision on the class of interest), giving a more honest picture of performance when class distribution is skewed.

**A9: A — Multi-label allows an instance to belong to more than one class at the same time; multi-class assigns exactly one class per instance.**
In multi-class classification, classes are mutually exclusive (e.g., an image is either a "cat," "dog," or "bird," but not more than one). In multi-label classification, an instance can simultaneously carry multiple labels (e.g., a news article can be tagged as both "politics" and "economy"). Multi-label problems are not restricted to binary settings and do not require neural networks specifically — any algorithm adapted to output multiple labels can be used.

**A10:** Batch gradient descent computes the gradient using the entire training set for every update, which produces stable, smooth convergence but is very slow and memory-intensive on large datasets since all data must be processed before a single weight update occurs. Stochastic gradient descent updates weights after each individual example (or small mini-batch), making each step cheap and enabling much faster iteration and quicker initial learning on large datasets, at the cost of a noisier, less direct convergence path that may oscillate around (rather than settle exactly on) the minimum.
