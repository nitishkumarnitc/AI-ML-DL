# 9 · Projects and Interview Prep

---

## Part 1 · Projects

### Project 1 — Beginner: the metrics report card

**Goal.** Build a reusable function that, given a fitted model and a test set, produces a complete evaluation report — and understand every number in it.

**Concepts used.** Chapters 1–5.

**Steps.**
1. Pick two datasets: one regression (`placement.csv` or California housing) and one binary classification (`heart.csv` or breast cancer).
2. Write `regression_report(y_true, y_pred, n_features)` returning MAE, MSE, RMSE, R², adjusted R², and the RMSE/MAE ratio.
3. Write `classification_report_plus(y_true, y_pred, y_proba)` returning accuracy, balanced accuracy, precision, recall, F1, the confusion matrix, and ROC-AUC.
4. Implement MAE, MSE, R², precision, and recall **from scratch** in NumPy and assert agreement with sklearn to 10 decimal places.
5. Run both reports against a `DummyRegressor` / `DummyClassifier` baseline and print the two side by side.

**Definition of done.** Every from-scratch implementation matches sklearn on 100 random trials; your report prints the dummy baseline next to the model; and you can explain, out loud and without notes, what each number means and one situation where it would mislead.

---

### Project 2 — Intermediate: the threshold and cost optimiser

**Goal.** Show that metric choice and threshold choice change which model you ship — on real data, with money attached.

**Concepts used.** Chapters 4–7.

**Steps.**
1. Take an imbalanced dataset (Kaggle credit-card fraud, or `make_classification(weights=[0.98, 0.02])`).
2. Train three models: logistic regression, random forest, and gradient boosting.
3. For each, produce ROC and PR curves on the same axes, and report ROC-AUC, Average Precision, and prevalence.
4. Build the expected-cost curve from §7.2 for three cost ratios: $C_{FN}/C_{FP}$ = 1, 10, and 200. Find the optimal threshold for each.
5. Build a table: rows = models, columns = cost ratios, cells = (optimal threshold, expected cost, resulting precision/recall).
6. Bootstrap a 95% CI on Average Precision for each model.

**Definition of done.** Your table shows at least one cost ratio where the model ranking *changes*; you can name the winning model for each ratio and defend it; and you can state whether the AP differences are statistically defensible or inside the noise.

---

### Project 3 — Advanced: a production evaluation harness

**Goal.** Build the evaluation infrastructure a real deployment needs — not a notebook cell, a harness.

**Concepts used.** All chapters, plus engineering.

**Steps.**
1. Pick a dataset with a **time column** and a natural **grouping key** (e.g. Olist e-commerce, or lending-club loans).
2. Implement three splitting strategies — random, `GroupKFold`, and time-ordered — and report your primary metric under all three. Quantify the optimism of random splitting.
3. Wrap all preprocessing in a `Pipeline` so no transform can see the validation fold. Prove it by showing the metric gap against a deliberately leaky version.
4. Implement slice evaluation: a function that takes a dict of segment masks and returns a per-slice metric table with support counts, suppressing slices below a minimum n.
5. Implement drift monitoring: split the test period into monthly blocks and plot the primary metric plus the mean predicted probability per block.
6. Implement `bootstrap_ci` and `mcnemar_compare`, and use them to compare two model versions.
7. Add guardrails: measure p50/p99 inference latency and alert volume at your chosen threshold.
8. Emit the §8.8 markdown report automatically.

**Definition of done.** Running one command produces the full report; the report includes baselines, intervals, slices, drift, and guardrails; the random-vs-grouped split gap is quantified; and you can point to a specific slice or month where the model underperforms and say what you'd do about it.

---

## Part 2 · Interview Questions

### Basic (10)

**1. What is the difference between MAE and MSE?**
MAE averages absolute residuals, MSE averages squared ones. MAE is in the target's units and weights all errors linearly; MSE is in units-squared and weights large errors quadratically, making it far more outlier-sensitive. MSE is differentiable everywhere; MAE has a kink at zero.

**2. Why do we use RMSE instead of MSE?**
Purely for interpretability — the square root restores the target's unit. RMSE and MSE always rank models identically because √ is monotone, so RMSE adds no information beyond readability.

**3. What does R² = 0.75 mean?**
The model's inputs explain 75% of the variance in the target; equivalently, it eliminated 75% of the squared error that predicting the mean would incur. It does **not** mean "75% accurate".

**4. Can R² be negative? What does it mean?**
Yes, on a test set. It means $SS_{res} > SS_{tot}$ — the model has larger squared error than a horizontal line at the test set's mean. Usually a wrong model family (a line through non-linear data) or severe distribution shift. Training R² for OLS with an intercept cannot go negative.

**5. What is a confusion matrix?**
A table cross-tabulating actual against predicted classes. For binary it holds TP, FP, FN, TN. The diagonal is correct predictions; off-diagonal cells separate the error *types*, which accuracy collapses into one number.

**6. Define precision and recall.**
Precision = TP/(TP+FP) — of everything flagged positive, what fraction was truly positive. Recall = TP/(TP+FN) — of all actual positives, what fraction was caught. Precision divides by the predicted-positive column; recall by the actual-positive row.

**7. What is the difference between Type 1 and Type 2 errors?**
Type 1 = False Positive = a false alarm (predicted positive, actually negative). Type 2 = False Negative = a miss (predicted negative, actually positive).

**8. What is the F1 score and why the harmonic mean?**
F1 = 2PR/(P+R), the harmonic mean of precision and recall. The harmonic mean sits near the *lower* of the two, so a model cannot hide a weak metric behind a strong one. With P=2 and R=100, the arithmetic mean is 51 while F1 is 3.92 — F1 is the honest number.

**9. Why is accuracy a bad metric for imbalanced datasets?**
It weights all predictions equally while the class you care about is rare. With 1 positive in 100,000, a model that always predicts negative scores 99.999% and detects nothing. Neither precision nor recall contains TN, which is why they survive imbalance.

**10. What accuracy should a model have?**
It depends entirely on the cost of error in the domain. 99% is unacceptable for cancer screening or autonomous steering and generous for predicting whether someone orders takeaway. Any specific number is a wrong answer.

---

### Intermediate (10)

**11. When would you prefer MAE over RMSE as a reported metric?**
When outliers are legitimate and you don't want them dominating the score, when the cost of error is roughly linear in its size, and when reporting to a non-technical audience who need a typical-error figure. Compute both — the RMSE/MAE ratio is a free outlier diagnostic; a ratio near 1 means uniform errors, ≫1 means a few large ones dominate.

**12. Why does R² never decrease when you add a feature, and what fixes it?**
OLS minimises $SS_{res}$ over a larger space when a column is added; the previous solution remains available (coefficient 0), so the minimum cannot get worse, and in finite samples random correlation with the residuals makes it slightly better. $SS_{tot}$ is unchanged. Adjusted R² fixes it by dividing by $n-k-1$, so each extra feature must earn its keep.

**13. Can adjusted R² be negative when R² is positive?**
Yes. With small $n$ and large $k$ the penalty $(n-1)/(n-k-1)$ becomes large enough to push the result below zero — a correct signal that you cannot support that many features on that little data. At $n = k+1$ it is undefined.

**14. Precision and recall are both high but F1 is lower than both. Possible?**
No. F1 is bounded between min(P, R) and max(P, R), so it can never fall below both. If you compute otherwise you have a bug — commonly averaging the wrong axis in a multiclass setting, or mixing per-class and averaged values.

**15. What's the difference between macro, micro and weighted averaging?**
Macro averages per-class scores equally. Weighted averages them by support. Micro pools all TP/FP/FN counts before computing. For single-label multiclass, micro-P = micro-R = micro-F1 = accuracy, and weighted recall also equals accuracy, so both are redundant there. Micro becomes distinct only for multi-label.

**16. Your ROC-AUC is 0.97 but the model is useless in production. Explain.**
Most likely the positive class is rare. FPR's denominator is the whole negative class, so thousands of false positives barely register while precision is terrible — a fraud model can have AUC 0.97 and a review queue that's 92% false alarms. Report PR-AUC against prevalence instead. Alternatively the ranking is fine but the *threshold* or the *calibration* is wrong.

**17. What does ROC-AUC actually measure?**
The probability that the model scores a randomly chosen positive above a randomly chosen negative. It measures ranking quality only, is threshold-independent, and is invariant to any monotone rescaling of the scores — which is why recalibrating a model never changes its AUC.

**18. Difference between discrimination and calibration?**
Discrimination is ranking positives above negatives (measured by AUC). Calibration is whether a predicted 0.7 corresponds to 70% actually being positive (measured by log loss, Brier, calibration curves). They are independent: dividing every probability by 10 leaves AUC at 1.0 and destroys calibration. It matters whenever the probability feeds a downstream calculation rather than just a threshold.

**19. Why is `roc_auc_score(y_true, model.predict(X))` wrong?**
`predict()` returns hard labels, collapsing the ROC curve to three points and returning a spuriously low value with no error raised. AUC needs scores: `predict_proba(X)[:, 1]` or `decision_function(X)`.

**20. How do you choose a decision threshold?**
Not by leaving it at 0.5, which implicitly asserts equal error costs. Either maximise the metric you care about ($F_\beta$) or — better — minimise expected cost $C_{FP}\cdot FP + C_{FN}\cdot FN$ over a threshold sweep. Always tune on validation data; the threshold is a fitted parameter and tuning it on test leaks.

---

### Advanced (10)

**21. Precision-recall trade-off: is it fundamental or fixable?**
Both, at different levels. For a **fixed model**, moving the threshold trades one against the other — that is fundamental. Better features, more data, or a better model class moves the entire PR curve outward, improving both simultaneously. Conflating "moving along the curve" with "moving the curve" makes people believe improvement is impossible.

**22. Why is MCC often preferred over F1 for binary classification?**
MCC uses all four confusion-matrix cells symmetrically, so it cannot be fooled by a degenerate predictor and doesn't change when you relabel which class is "positive". F1 ignores TN entirely and is asymmetric under class swapping. On the always-negative airport model MCC is 0 while accuracy is 99.999%.

**23. You have 200 test rows and models scoring 0.86 and 0.88. Ship the second?**
Not on that evidence. Bootstrap a CI — at n=200 the interval is likely ±0.04 or wider, so the gap is inside noise. Run McNemar's paired test, which uses only the disagreement cells and is the correct test for two models on one test set. If inconclusive, get more test data or run an A/B test; don't ship randomness.

**24. Your model scores 0.91 offline and shows no lift in the A/B test. Diagnose.**
Candidates, roughly in order of frequency: **training/serving skew** (a feature computed differently at inference — offline evaluation is structurally blind to this); **leakage** offline, inflating the score; **feedback loops** making the offline label distribution self-fulfilling; **distribution shift** since the training window; the **action** not matching the prediction (a human overrides the alert); or the **proxy metric** being genuinely disconnected from the business outcome. Start by logging served feature vectors and replaying them offline — that isolates skew from everything else.

**25. Aggregate accuracy 92%, and a subgroup is at 65%. How did the metric miss it?**
Weighted averages are dominated by large segments: 0.9(95%) + 0.1(65%) = 92%. The aggregate is not wrong, it is the wrong granularity. Fix by slicing on every dimension that partitions the population meaningfully and reporting the worst slice next to the headline, with support counts and a minimum-n suppression rule.

**26. Three fairness definitions are mutually incompatible. Which do you pick?**
Demographic parity (equal positive rates), equal opportunity (equal TPR), and predictive parity (equal precision) cannot all hold simultaneously unless base rates are equal or the classifier is perfect — this is a proved impossibility, not an engineering shortfall. The choice is normative and domain-specific: equal opportunity for opportunity-allocation (hiring, lending approvals); predictive parity where downstream actors rely on the score's meaning (risk scores used by judges). The requirement is to choose explicitly and document why, not to find the "correct" one.

**27. What breaks about R² and adjusted R² for non-linear models?**
$R^2 = 1 - SS_{res}/SS_{tot}$ is still computable and still interpretable as variance-explained-relative-to-the-mean, so it transfers fine. Adjusted R² does not: $k$ is defined as the number of input columns, which is a poor proxy for the effective degrees of freedom of a random forest or a boosted ensemble. Use cross-validated R², or information criteria with a proper complexity term, rather than adjusted R² outside linear models.

**28. Metric to optimise when labels are delayed by 90 days?**
You cannot optimise a label-dependent metric in real time, so split the problem. Optimise offline on ripened data with a proper time-ordered split, excluding the unripe tail. Monitor label-free signals daily — prediction distribution, feature health, unseen-category rates — plus proxy outcomes available immediately (analyst action rate, appeal rate, override rate). Then backfill true metrics as labels ripen and reconcile against what the proxies predicted; a divergence between proxy and eventual truth is itself the alarm.

**29. When is log loss a bad choice despite being the standard training loss?**
When a single overconfident error can dominate: it is unbounded, so one prediction of 0.999 on a true negative contributes ~6.9 and can swamp thousands of good predictions. Also when the target is a decision rather than a probability — log loss will happily prefer a model with better probabilities and worse decisions at your operating threshold. Brier is bounded and more robust; if the threshold is what matters, evaluate at the threshold.

**30. Metric suite for a 30-class classifier with supports from 40,000 to 12?**
Report per-class precision/recall/F1 with support, and suppress or explicitly flag classes below a minimum n — a score from 12 samples is not an estimate. For the headline, macro-F1 over the classes you can actually measure, plus weighted-F1 to reflect the population, and state that they answer different questions. Add a confusion heatmap for the confusable pairs. If some rare classes carry disproportionate business or regulatory weight, give them their own named tiles rather than letting any average absorb them; consider whether the smallest classes should be merged or handled by a rule instead of the model.

---

### System Design (8)

**31. Design the evaluation system for a medical diagnostic model.**
Recall-first with a hard precision guardrail — a missed diagnosis is the catastrophic error, but an unusable false-alarm rate destroys clinician trust and gets the system switched off. Use $F_2$ or explicit cost minimisation with clinician-supplied cost ratios. Stratify by site, scanner model, demographic group, and disease subtype; each is a plausible failure axis. Require calibration (clinicians need to read the probability, not just the flag). Report intervals, not point estimates. Add prospective monitoring on the prediction distribution because labels arrive via biopsy weeks later. Governance: fixed pre-registered test set, versioned, never used for tuning.

**32. Design metrics for a recommender at scale.**
Offline: ranking metrics at the position users actually see — recall@k, NDCG@k, MAP@k — with k set by the real UI. Recognise that logged data is confounded by the incumbent recommender's exposure, so use counterfactual/off-policy estimators or at least acknowledge the bias. Online is the real evaluation: CTR plus guardrails against the obvious failure modes — long-term retention, diversity/catalogue coverage, and creator-side fairness — because pure CTR optimisation reliably yields clickbait and a collapsing catalogue. Slice by user tenure and by item popularity; cold-start segments are where recommenders actually fail.

**33. Design evaluation for a fraud detection system.**
PR-AUC as the primary offline metric, reported against prevalence. Choose the operating threshold by expected cost using the real numbers ($C_{FN}$ = mean fraud loss, $C_{FP}$ = review cost + customer-friction cost). Hard guardrail on daily alert volume against analyst capacity — exceeding it silently destroys real-world recall through rubber-stamping. Split by `GroupKFold` on customer and time-ordered for the final holdout; random splitting leaks. Monitor prediction distribution daily since labels lag ~60 days. Expect adversarial concept drift and plan a retraining cadence, not a one-off deployment.

**34. Design evaluation for an LLM-based summarisation feature.**
None of this module's metrics apply directly — there is no single correct output. Build a graded eval set with rubric-based scoring (faithfulness, coverage, conciseness), use an LLM judge with the judge itself validated against human labels on a sample, and measure judge-human agreement with Cohen's kappa. Add targeted adversarial cases for hallucination. Track cost and latency as first-class metrics. Cross-reference: [`16_evals/`](../16_evals/README.md) covers this properly, and it is a genuinely different discipline from the one in this module.

**35. Your team wants one number on the exec dashboard. What do you put there and what do you refuse?**
Put a business-denominated number with a baseline — "£X fraud prevented per month vs the rules engine" or "N missed diagnoses avoided per 1,000 screens". Refuse a raw model metric as the headline, because no executive can tell whether 0.34 PR-AUC is good, and refuse accuracy on any imbalanced problem. Behind the tile, keep the metric suite, slices, and guardrails one click away, and put the worst slice on the same screen so the aggregate can never be the whole story.

**36. Design a metric strategy for a model whose predictions change user behaviour.**
This is the feedback-loop problem, and offline evaluation is structurally compromised: the model's own decisions determine which labels you observe. Preserve a randomised holdout — a small fraction of traffic scored but not acted upon — to get unconfounded labels, treating it as a standing measurement cost. Use off-policy evaluation with propensity weighting for the rest. Monitor for the specific pathology of the loop tightening (predictions becoming self-fulfilling), and A/B test every change rather than trusting offline deltas.

**37. Design evaluation for an edge-deployed model on 10M devices.**
Quality metrics are the easy half. The binding constraints are model size, memory ceiling, p99 latency on the slowest supported device, and battery/thermal cost — any of which can veto a more accurate model. Evaluate quality **per device class**, since a quantised model degrades unevenly across hardware. You cannot centrally collect labels, so instrument privacy-preserving aggregate telemetry: prediction distribution, on-device confidence histograms, user-correction rate as a proxy for error. Plan for staged rollout and remote rollback, and define the fallback behaviour and *its* metrics.

**38. A regulator asks you to prove your model is fair. What do you produce?**
First, establish which fairness definition the relevant regulation actually requires — they are mutually incompatible, so this is the whole question and it is legal before it is technical. Then produce per-group confusion matrices and metrics with confidence intervals (not point estimates, since protected groups are often small), the chosen fairness metric with its threshold and justification, the intersectional slices, documentation of what you tested and rejected, and a data statement covering representation in training data. Include the mitigation attempted and its cost in aggregate performance. Be explicit about what you did *not* test and why — an audit that claims completeness is less credible than one that scopes itself honestly.

---

**Next:** [10 · Glossary and Dependency Map](10-glossary-and-dependency-map.md)
