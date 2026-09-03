# Lesson 5 Knowledge Check — Ensemble Learning

## Concept Primer

**Ensemble learning** combines multiple "base" or "weak" learners into a single, stronger predictive model. The core idea is that a committee of models, each with its own errors and biases, can outperform any single model if their mistakes are sufficiently uncorrelated. Ensemble methods are broadly split into **parallel** techniques, where base learners are trained independently of one another (often on different subsets of data), and **sequential** techniques, where each new learner is trained with knowledge of how previous learners performed. Parallel methods exploit *independence* between learners to reduce variance; sequential methods exploit *dependence* between learners — each one correcting the errors of the last — to reduce bias/error.

**Bagging** (Bootstrap Aggregating) is the classic parallel technique. It draws multiple bootstrap samples (random samples with replacement) from the training data, fits an independent base model (commonly a decision tree) to each sample, and aggregates the results — by averaging for regression or majority/max voting for classification. Because the base learners are trained independently, bagging primarily reduces **variance** and helps prevent overfitting, without changing bias much. **Random Forest** is the best-known bagging variant: alongside bootstrapped rows, it also randomly samples a subset of features at each split, which further decorrelates the trees and improves generalization.

**Boosting** is the flagship sequential technique. Learners are added one at a time, and each new learner focuses on the examples the previous learners got wrong (e.g., by upweighting misclassified points, as in **AdaBoost**, or by fitting the residual errors, as in **Gradient Boosting**/XGBoost/LightGBM). Because each model depends on the ones before it, boosting reduces **bias** and can build a highly accurate model from many weak learners, though it is more prone to overfitting and is sensitive to noisy data/outliers if not regularized (learning rate, tree depth, early stopping, etc.).

**Averaging and voting** are the simplest combination rules used to merge predictions from an ensemble of already-trained models. Averaging (or weighted averaging) is used for regression outputs or probability scores; voting — hard (majority) voting or soft voting — is used for classification labels. Their purpose is to smooth out the idiosyncratic errors of individual models, producing a final prediction whose overall error is lower than that of any single member.

**Stacking (stacked generalization)** and **blending** go a step further than simple averaging/voting. In stacking, predictions from several diverse base models (level-0 models) become the input features for a second-level "meta-model" that learns how to best combine them, typically using cross-validated out-of-fold predictions. Blending is a simpler, related variant that combines base-model predictions (often via a held-out validation set and weighted averaging) rather than a fully cross-validated meta-model. Both approaches work best when the base models are diverse (different algorithms, different feature views), since a meta-learner can only add value if the base models make different kinds of mistakes.

In short: **bagging/Random Forest → parallel, reduces variance; boosting/AdaBoost/Gradient Boosting → sequential, reduces bias; averaging/voting → simple combination rules; stacking/blending → learned combination via a meta-model.** Knowing which category a named technique falls into is the fastest way to answer conceptual ensemble-learning questions.

---

## Questions

**1.** What is the difference between sequential and parallel ensemble techniques?

- **A.** In sequential ensemble, base learners are generated in parallel, and in parallel ensemble, learners are generated consecutively.
- **B.** The sequential technique is applied when the base learners are generated in parallel, and the parallel is applied when the learners are generated consecutively.
- **C.** The sequential technique uses dependence between the base learners to reduce error, whereas the parallel technique uses independence between the base learners to reduce error.
- **D.** There is no difference between sequential and parallel ensemble techniques.

**2.** What is the purpose of averaging and voting techniques?

- **A.** To reduce errors in the model
- **B.** To reduce the variance in the model
- **C.** To increase the bias in the model
- **D.** To increase the variance in the model

**3.** Which of the following ensemble learning techniques involves combining predictions from multiple base models to make a final prediction?

- **A.** Bagging
- **B.** Max voting
- **C.** AdaBoost
- **D.** Blending ensemble

---

## Answers

**1. Answer: C** — *The sequential technique uses dependence between the base learners to reduce error, whereas the parallel technique uses independence between the base learners to reduce error.*
Sequential techniques (e.g., boosting) build each new learner using information about previous learners' errors — that dependence is what drives error reduction. Parallel techniques (e.g., bagging) train learners independently and rely on that independence to reduce variance when combined.

**2. Answer: A** — *To reduce errors in the model.*
Averaging (for continuous outputs) and voting (for class labels) combine multiple predictions so that individual models' random or idiosyncratic errors cancel out, lowering the overall error of the ensemble compared to any single model.

**3. Answer: D** — *Blending ensemble.*
As presented in this course, blending combines predictions from multiple, typically diverse, base models using (often weighted) averaging on a held-out set, producing one final prediction. Note this answer is somewhat instructor-specific: strictly speaking, bagging, max voting, and AdaBoost also combine multiple base models' outputs — the intended distinction here is that blending explicitly learns/uses weighted combination of diverse model *types*, which the original slide's explanation emphasizes.

---

## 📝 Additional Practice Questions

**4.** Which of the following best describes how Random Forest reduces overfitting compared to a single decision tree?

- **A.** By training one very deep tree on all the data
- **B.** By boosting misclassified samples on each iteration
- **C.** By averaging/voting over many trees trained on bootstrapped samples with random feature subsets
- **D.** By removing features with low variance before training

**5.** In AdaBoost, what happens to the weight of a training sample that is misclassified by the current weak learner?

- **A.** It is set to zero so the sample is ignored going forward
- **B.** It is increased, so the next learner focuses more on that sample
- **C.** It is decreased, so the next learner focuses less on that sample
- **D.** It stays unchanged; only the model weights change

**6.** Which statement correctly contrasts bagging and boosting?

- **A.** Bagging reduces bias; boosting reduces variance
- **B.** Bagging trains learners sequentially; boosting trains learners in parallel
- **C.** Bagging reduces variance via independent learners; boosting reduces bias via sequential, dependent learners
- **D.** Bagging and boosting are identical techniques with different names

**7.** What is the primary role of a meta-model (blender) in a stacking ensemble?

- **A.** To directly replace all base models once trained
- **B.** To learn how to optimally combine the predictions of the base models
- **C.** To generate bootstrap samples for the base models
- **D.** To increase the variance of the base models' predictions

**8.** Short answer: Why does bagging work best when the base learners are unstable, high-variance models (like unpruned decision trees) rather than stable, low-variance models (like linear regression)?

**9.** Short answer: What is the key practical risk of boosting on a dataset with many mislabeled or noisy outliers, and why does it happen?

**10.** Which of the following is NOT a bagging-based ensemble method?

- **A.** Random Forest
- **B.** Extra Trees (Extremely Randomized Trees)
- **C.** Bagged decision trees
- **D.** Gradient Boosting Machine

**11.** True or False: Soft voting (averaging predicted class probabilities) generally uses more information than hard voting (majority vote on predicted labels), and can produce better results when base classifiers are well-calibrated.

**12.** Short answer: For stacking to add value over simply averaging the base models' predictions, what property must the base models have with respect to each other?

---

### Answers

**4. Answer: C** — Random Forest reduces overfitting by combining many decision trees, each trained on a bootstrapped sample of the data and considering only a random subset of features at each split. Averaging (regression) or voting (classification) across these decorrelated trees reduces variance without a large increase in bias.

**5. Answer: B** — AdaBoost increases the weight of misclassified samples after each round, forcing subsequent weak learners to pay more attention to the examples that are hardest to classify. Correctly classified samples get relatively lower weight.

**6. Answer: C** — Bagging (e.g., Random Forest) trains independent learners in parallel and averages/votes to reduce variance. Boosting (e.g., AdaBoost, Gradient Boosting) trains learners sequentially, each correcting the previous one's errors, primarily reducing bias.

**7. Answer: B** — The meta-model in stacking takes the base models' predictions as input features and learns the best way to weight/combine them, typically capturing patterns that a simple fixed averaging rule would miss.

**8. Answer (short answer):** High-variance, unstable models (e.g., deep/unpruned trees) produce very different predictions when trained on slightly different bootstrap samples. Averaging many such diverse-but-unbiased models cancels out their individual variance while roughly preserving their (typically low) bias, yielding a big net reduction in error. Stable, low-variance models like linear regression barely change across bootstrap samples, so bagging them gives little diversity to average over and therefore little benefit.

**9. Answer (short answer):** Boosting repeatedly increases the weight/emphasis on misclassified points. If some points are mislabeled or are true outliers, boosting will keep trying harder and harder to fit them correctly, effectively overfitting to noise and degrading generalization. This is why boosting implementations use regularization such as learning rate shrinkage, limited tree depth, subsampling, and early stopping.

**10. Answer: D** — Gradient Boosting Machine is a sequential/boosting method, not a bagging method. Random Forest, Extra Trees, and bagged decision trees are all parallel, bootstrap-based (bagging-family) methods.

**11. Answer: True** — Soft voting uses the full predicted probability distribution from each classifier rather than just the final hard label, retaining more information about model confidence. When the base classifiers produce well-calibrated probabilities, soft voting typically yields better ensemble performance than hard majority voting.

**12. Answer (short answer):** The base models must be diverse — i.e., make different, ideally uncorrelated types of errors (achieved via different algorithms, feature subsets, or data samples). If all base models make the same mistakes, a meta-model has nothing complementary to learn from and stacking offers little or no improvement over a single base model or simple averaging.
