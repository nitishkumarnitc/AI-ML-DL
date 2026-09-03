# Lesson 10: Feature Engineering — Knowledge Check

## Concept Primer

**Feature engineering** is the process of using domain knowledge and data analysis to select, modify, combine, or create new input variables ("features") so that a machine learning model can learn patterns more effectively. It sits between raw data collection and model training, and in practice often matters more for final model performance than the choice of algorithm itself. Common activities include encoding categorical variables, scaling numeric variables, handling skewed distributions, creating derived features (e.g., ratios, date parts, interaction terms), and selecting the subset of features that are most predictive.

**Encoding categorical variables** converts non-numeric labels into a numeric form models can use. *One-hot encoding* creates a separate binary column for each category and works well for nominal (unordered) categories with a manageable number of levels. *Label encoding* (or ordinal encoding) assigns each category an integer, which is appropriate when categories have a natural order (e.g., "low/medium/high") but can mislead algorithms into assuming a false numeric relationship if applied to unordered categories. Other techniques include target encoding and frequency encoding, which are useful for high-cardinality categorical features where one-hot encoding would create too many columns.

**Scaling and normalization** put numeric features on comparable ranges so that features with large magnitudes don't dominate distance-based or gradient-based algorithms. *Min-max scaling* rescales values into a fixed range (typically 0 to 1) by subtracting the minimum and dividing by the range; it is sensitive to outliers because the min and max define the scale. *Standardization (z-score scaling)* subtracts the mean and divides by the standard deviation, producing a distribution centered at 0 with unit variance; it is less sensitive to outliers and is generally preferred for algorithms that assume roughly normal data (e.g., linear regression, SVMs, PCA). Tree-based models (decision trees, random forests, gradient boosting) are generally scale-invariant and don't require scaling.

**Handling skewness** addresses features whose distribution is heavily lopsided, which can violate the assumptions of linear models and reduce the effectiveness of scaling. *Log transformation* compresses large values and is the most common first choice for right-skewed, strictly positive data (e.g., income, price). *Square root transformation* offers a milder correction, useful when skew is moderate or when some zero values are present. The *Box-Cox transformation* is a more general, parameterized family that automatically searches for the power transformation (λ) that best normalizes the data, subsuming log and square-root as special cases; it requires strictly positive input (its cousin, the Yeo-Johnson transformation, handles zero and negative values).

**Feature creation and selection** are two complementary sides of feature engineering. *Feature creation* generates new, more informative variables from existing ones — for example, extracting day-of-week from a timestamp, computing body-mass index from height and weight, or building interaction terms that capture how two variables jointly affect the outcome. *Feature selection* does the opposite: it removes redundant, irrelevant, or highly correlated features to reduce overfitting, speed up training, and improve interpretability. Common approaches include filter methods (correlation, mutual information, chi-square tests), wrapper methods (recursive feature elimination), and embedded methods (L1/Lasso regularization, tree-based feature importances).

Together, these techniques form the toolbox of feature engineering: encode what's categorical, scale what's numeric, correct what's skewed, create what's missing, and select what's essential. A well-engineered feature set frequently yields larger performance gains than switching to a more complex algorithm on poorly prepared data.

---

## Original Knowledge Check Questions

### Question 1

**What is the purpose of feature engineering in machine learning?**

- **A.** To increase the complexity of models
- **B.** To reduce the size of the dataset
- **C.** To improve the performance of machine learning models by modifying or creating features
- **D.** To visualize data patterns

### Question 2

**Which transformation is commonly used to stabilize variance and handle skewed distributions?**

- **A.** Log transformation
- **B.** Min-max scaling
- **C.** Box-cox transformation
- **D.** Square root transformation

### Question 3

**What is the purpose of min-max scaling in feature engineering?**

- **A.** To standardize the range of features in a dataset
- **B.** To transform categorical variables into numerical
- **C.** To split a dataset into groups based on criteria
- **D.** To convert input data into fixed-length hash codes

---

## Answers

**1. Correct answer: C — To improve the performance of machine learning models by modifying or creating features.**
Feature engineering is fundamentally about selecting, modifying, or creating new features from raw data so the resulting data representation is more suitable for a model to learn from, which directly improves predictive performance.

**2. Correct answer: D — Square root transformation.**
As stated in the source material, square root transformation stabilizes variance and reduces skew in a manner similar to log transformation. *Note:* in general practice, log transformation and the Box-Cox transformation are also extremely common (and often more powerful) choices for this exact purpose — treat D as the answer specified by this course's slide deck rather than the only correct technique in the real world.

**3. Correct answer: A — To standardize the range of features in a dataset.**
Min-max scaling is a normalization technique that rescales feature values into a fixed range (commonly [0, 1]) by using each feature's minimum and maximum, making features with different original scales directly comparable.

---

## 📝 Additional Practice Questions

1. **(Multiple Choice)** Which encoding technique is most appropriate for a nominal categorical feature (no inherent order) with only 4 unique values, such as `color = {red, green, blue, yellow}`?
   - **A.** Label encoding
   - **B.** One-hot encoding
   - **C.** Min-max scaling
   - **D.** Box-Cox transformation

2. **(Multiple Choice)** A dataset has a categorical feature `education_level = {high school, bachelor's, master's, PhD}` with a clear natural order. Which encoding approach best preserves this ordinal relationship?
   - **A.** One-hot encoding
   - **B.** Ordinal (label) encoding
   - **C.** Frequency encoding
   - **D.** Min-max scaling

3. **(Short Answer)** Explain why applying min-max scaling instead of standardization (z-score scaling) can be problematic when a numeric feature contains extreme outliers.

4. **(Multiple Choice)** Which of the following algorithms is generally LEAST sensitive to whether input features have been scaled?
   - **A.** K-Nearest Neighbors
   - **B.** Support Vector Machines
   - **C.** Random Forest
   - **D.** Linear Regression with gradient descent

5. **(Short Answer)** Give one example of a "created" (derived) feature you could engineer from a raw `timestamp` column, and explain why it might help a model predict retail sales.

6. **(Multiple Choice)** A feature is right-skewed and contains some zero values, so a standard log transformation (log(x)) cannot be applied directly. Which of the following is the most appropriate fix?
   - **A.** Apply log(x) anyway and ignore the error
   - **B.** Apply log(x + 1) or use the Yeo-Johnson transformation
   - **C.** Apply min-max scaling only
   - **D.** Discard the feature entirely

7. **(Multiple Choice)** Which of the following is an example of a filter-based feature selection method?
   - **A.** Recursive Feature Elimination (RFE)
   - **B.** Correlation coefficient thresholding
   - **C.** Lasso (L1) regularized regression
   - **D.** Forward stepwise selection using model accuracy

8. **(Short Answer)** What is the main risk of keeping two highly correlated (collinear) features in a linear regression model, and how does feature selection help mitigate it?

9. **(Multiple Choice)** Which statement about the Box-Cox transformation is TRUE?
   - **A.** It can be applied to data containing negative or zero values without modification
   - **B.** It automatically identifies an optimal power parameter (λ) to reduce skewness and stabilize variance
   - **C.** It is only used for categorical variables
   - **D.** It always produces the same result as min-max scaling

10. **(Short Answer)** Why is it best practice to fit a scaler (e.g., `MinMaxScaler` or `StandardScaler`) only on the training data and then use that same fitted scaler to transform the validation/test data, rather than fitting a new scaler on each split?

### Answers

**1. Correct answer: B — One-hot encoding.**
With no natural order among categories and only a small number of unique values, one-hot encoding creates a separate binary indicator column per category without implying any false ordinal relationship — label encoding would incorrectly imply that "blue" is numerically greater than "red," for example.

**2. Correct answer: B — Ordinal (label) encoding.**
Because `education_level` has a genuine rank order (high school < bachelor's < master's < PhD), mapping it to increasing integers preserves that meaningful order for the model, whereas one-hot encoding would discard the ordering information.

**3. Sample answer:** Min-max scaling uses the minimum and maximum values of a feature to define its scale, so a single extreme outlier stretches the range and compresses all the other "normal" values into a very narrow band near 0. Standardization instead uses the mean and standard deviation, which are less distorted by a single extreme value, making it more robust when outliers are present.

**4. Correct answer: C — Random Forest.**
Tree-based models split on feature thresholds rather than computing distances or gradients across feature magnitudes, so the absolute scale of a feature does not affect how the tree partitions the data. KNN, SVMs, and gradient-descent-based linear regression are all sensitive to feature scale.

**5. Sample answer:** From a timestamp you could derive features such as `day_of_week`, `is_weekend`, `month`, or `hour_of_day`. These matter for retail sales prediction because purchasing behavior is often cyclical — e.g., sales may spike on weekends or during particular months (holiday seasons) — and the model cannot learn these patterns directly from a raw timestamp value.

**6. Correct answer: B — Apply log(x + 1) or use the Yeo-Johnson transformation.**
Standard log transformation is undefined at zero (log(0) is undefined) and for negative numbers. Adding a constant of 1 before taking the log (`log1p`) is a common workaround for non-negative data with zeros, while Yeo-Johnson is a generalization of Box-Cox specifically designed to also handle zero and negative values.

**7. Correct answer: B — Correlation coefficient thresholding.**
Filter methods evaluate features independently of any model, using statistical measures like correlation, mutual information, or chi-square tests. RFE and forward stepwise selection are wrapper methods (they rely on a model's performance), and Lasso is an embedded method (feature selection happens as part of model fitting).

**8. Sample answer:** Highly correlated (collinear) features make coefficient estimates in a linear model unstable and difficult to interpret, because the model cannot reliably distinguish each feature's individual contribution to the outcome — small changes in the data can produce large swings in the estimated coefficients. Feature selection mitigates this by removing one of the redundant features (or combining them), which stabilizes the model and improves interpretability without materially reducing predictive information.

**9. Correct answer: B — It automatically identifies an optimal power parameter (λ) to reduce skewness and stabilize variance.**
Box-Cox searches over a range of λ values to find the power transformation that best normalizes the data's distribution. It requires strictly positive input (option A is false — its extension, Yeo-Johnson, handles zero/negative values), it applies to continuous numeric data (not categorical, so option C is false), and it is mathematically distinct from min-max scaling (option D is false).

**10. Sample answer:** Fitting the scaler only on training data and reusing those same parameters (min/max or mean/std) on the validation/test data prevents data leakage — if you fit a new scaler on the test set, information about the test set's distribution would leak into preprocessing, giving an overly optimistic and unrealistic estimate of how the model will perform on truly unseen data in production.
