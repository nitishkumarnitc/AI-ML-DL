# Lesson 3 Knowledge Checks — Supervised Learning: Regression and its Application

## Concept Primer

**Linear regression** models the relationship between a dependent (target) variable and one or more independent (predictor) variables as a straight line: `y = β0 + β1x1 + β2x2 + ... + βn*xn + ε`. The `β` coefficients represent how much the target changes for a one-unit change in a predictor, holding other predictors constant, and `ε` is the irreducible error term. When there is one predictor, this is *simple linear regression*; with multiple predictors, it is *multiple linear regression*.

**Cost functions** measure how far the model's predictions are from the actual values, and training means finding the parameters that minimize this cost. The most common cost function for linear regression is **Mean Squared Error (MSE)** — the average of the squared differences between predicted and actual values. Squaring the errors penalizes large mistakes more heavily and keeps the function smooth and differentiable, which matters for optimization.

**Gradient descent** is the optimization algorithm typically used to minimize the cost function. It starts with initial (often random) parameter values, computes the gradient (slope) of the cost function with respect to each parameter, and repeatedly updates the parameters in the direction that reduces the cost, scaled by a **learning rate**. Too small a learning rate makes convergence slow; too large a learning rate can cause the algorithm to overshoot the minimum or diverge entirely.

**R² (coefficient of determination)** measures the proportion of variance in the dependent variable that is explained by the independent variable(s), ranging from 0 (no explanatory power) to 1 (perfect fit). A high R² does not automatically mean a good model — it can be inflated by adding more predictors even if they are irrelevant, which is why **Adjusted R²** (which penalizes unnecessary predictors) is often preferred when comparing models with different numbers of features.

**Multicollinearity** occurs when independent variables are highly correlated with each other, which destabilizes coefficient estimates and makes them hard to interpret. The **Variance Inflation Factor (VIF)** quantifies how much a predictor's variance is inflated due to correlation with other predictors — a VIF above roughly 5–10 is generally treated as a warning sign of problematic multicollinearity.

**Regularization** techniques like **Ridge** and **Lasso** regression add a penalty term to the cost function to shrink coefficients and reduce model complexity/overfitting. Ridge regression (L2 penalty) shrinks coefficients toward zero but rarely to exactly zero, making it useful for handling multicollinearity while keeping all features. Lasso regression (L1 penalty) can shrink some coefficients exactly to zero, effectively performing feature selection.

**Logistic regression**, despite the name, is used for classification rather than regression on continuous values. It applies the **sigmoid (logistic) function** to a linear combination of inputs, squashing the output into the range (0, 1) so it can be interpreted as a probability of belonging to a class, which is then typically thresholded (e.g., at 0.5) to produce a class label.

---

## Original Knowledge Check Questions

### Question 1
**What is the purpose of VIF in regression analysis?**

- **A.** To check the correlation between dependent and independent variables
- **B.** To check the correlation between independent variables
- **C.** To calculate the accuracy of the regression model
- **D.** To calculate the variability of the regression model

### Question 2
**Why is a sigmoid function used in logistic regression?**

- **A.** To plot data points on a graph
- **B.** To cluster data points based on their distance from a centroid
- **C.** To map real values to probabilities between 0 and 1
- **D.** To perform classification analysis

### Question 3
**What is ridge regression?**

- **A.** A technique to reduce multicollinearity between features in the data set
- **B.** A form of regression that shrinks the coefficient toward zero to reduce the complexity of the data
- **C.** A technique to fit the data points to the line using polynomial features
- **D.** A technique to predict the rise of different diseases within populations and their spread rates

---

## Answers

**1. Correct answer: B — To check the correlation between independent variables.**
The Variance Inflation Factor (VIF) measures how much the variance of a regression coefficient is inflated because a predictor is correlated with other predictors. It is used to detect and address multicollinearity among independent variables, not to check correlation with the dependent variable or to assess model accuracy.

**2. Correct answer: C — To map real values to probabilities between 0 and 1.**
Logistic regression needs an output that can be interpreted as a probability. The sigmoid function takes any real-valued input (from the linear combination of features) and squashes it into the (0, 1) range, which is then used for classification decisions.

**3. Correct answer: B — A form of regression that shrinks the coefficient toward zero to reduce the complexity of the data.**
Ridge regression adds an L2 penalty (proportional to the sum of squared coefficients) to the cost function. This shrinks coefficients toward zero, reducing model complexity and variance, and is particularly helpful when features are highly correlated.

---

## 📝 Additional Practice Questions

**Q4.** What does the Mean Squared Error (MSE) cost function measure in linear regression?
- **A.** The sum of absolute differences between predicted and actual values
- **B.** The average of the squared differences between predicted and actual values
- **C.** The correlation between predicted and actual values
- **D.** The number of misclassified data points

**Q5.** In gradient descent, what happens if the learning rate is set too high?
- **A.** The algorithm converges faster with no downside
- **B.** The algorithm may overshoot the minimum and fail to converge (diverge)
- **C.** The model automatically switches to Ridge regression
- **D.** The cost function becomes non-differentiable

**Q6.** Which statement best describes the difference between Ridge and Lasso regression?
- **A.** Ridge can shrink coefficients exactly to zero; Lasso cannot
- **B.** Lasso can shrink coefficients exactly to zero (feature selection); Ridge shrinks them toward zero but rarely to exactly zero
- **C.** Ridge and Lasso are identical except for their names
- **D.** Lasso is only used for classification problems, and Ridge is only used for regression problems

**Q7.** What does an R² value of 0.85 for a regression model indicate?
- **A.** The model correctly classifies 85% of data points
- **B.** 85% of the variance in the dependent variable is explained by the independent variable(s)
- **C.** The model has an 85% chance of overfitting
- **D.** The regression coefficients are 85% statistically significant

**Q8.** Why might Adjusted R² be preferred over plain R² when comparing models with different numbers of predictors?
- **A.** Adjusted R² is always higher than R²
- **B.** Adjusted R² penalizes the addition of predictors that don't meaningfully improve the model, while plain R² never decreases as predictors are added
- **C.** Adjusted R² is easier to calculate
- **D.** Adjusted R² only works for logistic regression

**Q9 (Short Answer).** Explain, in your own words, why multicollinearity is a problem in a multiple linear regression model.

**Q10 (Short Answer).** Describe what "overfitting" means in the context of a regression model, and name one technique that helps reduce it.

**Q11.** A regression model has a very low training error but a very high test error. Which of the following is the most likely explanation?
- **A.** Underfitting
- **B.** Overfitting
- **C.** Perfect regularization
- **D.** High bias, low variance

**Q12 (Short Answer).** What is the role of the threshold (e.g., 0.5) in converting a logistic regression model's probability output into a class prediction?

---

### Answers

**A4. Correct answer: B.**
MSE is the average of the squared differences (errors) between predicted values and actual observed values. Squaring the errors penalizes larger deviations more heavily and produces a smooth, differentiable function that is convenient to optimize with gradient descent.

**A5. Correct answer: B.**
A learning rate that is too large causes each parameter update to overshoot the minimum of the cost function, and the algorithm can bounce around or diverge instead of converging. A learning rate that is too small, conversely, makes convergence very slow.

**A6. Correct answer: B.**
Lasso regression uses an L1 penalty that can drive some coefficients to exactly zero, effectively performing automatic feature selection. Ridge regression uses an L2 penalty that shrinks coefficients toward zero but typically keeps all of them nonzero, so it addresses multicollinearity without eliminating features.

**A7. Correct answer: B.**
R² (coefficient of determination) represents the proportion of variance in the target variable that is explained by the model's predictors. An R² of 0.85 means 85% of the variability in the outcome is accounted for by the independent variable(s), with the remaining 15% unexplained.

**A8. Correct answer: B.**
Plain R² never decreases when new predictors are added, even if they add no real explanatory value, which can mislead model comparison. Adjusted R² incorporates a penalty for the number of predictors relative to the number of observations, so it can decrease if a new predictor doesn't improve the model enough to justify the added complexity.

**A9. Sample answer.**
Multicollinearity occurs when two or more independent variables are highly correlated with each other. This makes it difficult for the regression model to isolate the individual effect of each correlated variable on the target, leading to unstable, inflated, or even sign-flipped coefficient estimates and less reliable interpretation of the model — even though overall predictive accuracy may not be badly affected. It is typically diagnosed using VIF and addressed via feature removal, combining features, or regularization (e.g., Ridge regression).

**A10. Sample answer.**
Overfitting occurs when a model learns the training data too closely — including its noise and random fluctuations — so it performs very well on training data but generalizes poorly to new, unseen data. Techniques that help reduce overfitting include regularization (Ridge/Lasso), cross-validation, simplifying the model (fewer features/lower polynomial degree), and gathering more training data.

**A11. Correct answer: B.**
A large gap between low training error and high test error is the classic signature of overfitting: the model has essentially memorized the training data (including its noise) rather than learning generalizable patterns, so it fails to perform well on unseen data.

**A12. Sample answer.**
Logistic regression outputs a continuous probability between 0 and 1 via the sigmoid function. The threshold converts this probability into a discrete class label — for example, with a 0.5 threshold, any predicted probability ≥ 0.5 is classified as the positive class and anything below 0.5 as the negative class. The threshold can be adjusted (e.g., based on precision/recall tradeoffs) depending on the application's tolerance for false positives versus false negatives.
