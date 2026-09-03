# Lesson 07: Probability Distribution — Knowledge Check

## Concept Primer

A **probability distribution** describes how the probability of a random variable's outcomes is spread across its possible values. Distributions are broadly split into **discrete** (variable takes countable values, e.g., number of successes) and **continuous** (variable takes any value in a range, e.g., height, time). For discrete variables we use a **Probability Mass Function (PMF)** to get the probability of an exact value; for continuous variables we use a **Probability Density Function (PDF)**, where the probability of any single exact value is technically zero and probabilities are read as the area under the curve over an interval. In both cases, the **Cumulative Distribution Function (CDF)**, P(X ≤ x), gives the probability that the variable takes a value less than or equal to x, and is obtained by summing (discrete) or integrating (continuous) the PMF/PDF up to that point.

The **Binomial distribution** models the number of successes in *n* independent trials, each with the same probability of success *p* (and failure probability *q = 1 − p*). The probability of exactly *r* successes is P(X = r) = ⁿCᵣ · pʳ · qⁿ⁻ʳ, where ⁿCᵣ counts the number of ways to choose which *r* of the *n* trials are successes. The mean of a binomial distribution is *np* and its variance is *npq*. It is used whenever an experiment has a fixed number of yes/no (Bernoulli) trials, such as coin flips, pass/fail tests, or defective/non-defective items in a batch.

The **Poisson distribution** models the number of times a rare, independent event occurs within a fixed interval of time or space (e.g., calls to a helpdesk per hour, defects per meter of cable). It has a single parameter **λ (lambda)**, which is the expected (average) number of occurrences in that interval, and its formula is P(X = k) = (e⁻λ · λᵏ) / k!. A key property is that the Poisson mean and variance are both equal to λ. Poisson is often used as an approximation to the Binomial distribution when *n* is large and *p* is small (rare-event condition), since computing binomial probabilities directly becomes unwieldy for large *n*.

The **Normal (Gaussian) distribution** is the most important continuous distribution, characterized by its mean (μ) and standard deviation (σ), producing the familiar symmetric bell curve. Roughly 68% of values fall within ±1σ of the mean, 95% within ±2σ, and 99.7% within ±3σ — the **empirical (68-95-99.7) rule**. Many natural phenomena and, by the **Central Limit Theorem**, the sampling distribution of the mean of almost any population, approximate a normal distribution as sample size grows, which is why it underlies most classical statistical inference (confidence intervals, hypothesis tests).

An **estimator** is a rule or formula (a statistic, like the sample mean) used to estimate an unknown population parameter (like the population mean). A **good estimator** should be (1) **unbiased** — its expected value equals the true parameter value, meaning it doesn't systematically over- or under-estimate — and (2) have **minimum variance** — it is as consistent as possible across repeated samples, i.e., it doesn't fluctuate wildly from sample to sample. Together, unbiasedness and minimum variance define what's called an efficient (or "best") estimator; the sample mean is a classic example of an unbiased, minimum-variance estimator of the population mean.

---

## Questions

1. What's the equation to find the probability of a specific outcome in a binomial distribution?
   - **A.** P(X = n) = pⁿ
   - **B.** P(X = 0) = qⁿ
   - **C.** P(X = r) = ⁿCᵣ · pʳ · qⁿ⁻ʳ
   - **D.** P(X ≥ 4) = 1 – P(X ≤ 3)

2. What is the Poisson distribution parameter representing the expected value of occurrences?
   - **A.** p
   - **B.** λ
   - **C.** q
   - **D.** σ

3. What are the two criteria for a good estimator?
   - **A.** Unbiasedness and minimum variance
   - **B.** Variance and bias
   - **C.** Bias and consistency
   - **D.** Variance and efficiency

---

## Answers

1. **Correct answer: C — P(X = r) = ⁿCᵣ · pʳ · qⁿ⁻ʳ**
   This is the binomial probability mass function: it gives the probability of exactly *r* successes in *n* independent trials, where *r* can range from 0 to *n*, *p* is the success probability, and *q = 1 − p* is the failure probability.

2. **Correct answer: B — λ**
   In the Poisson distribution, λ (lambda) is the rate parameter representing the expected (mean) number of occurrences of an event in a fixed interval; uniquely, it is also equal to the distribution's variance.

3. **Correct answer: A — Unbiasedness and minimum variance**
   A good point estimator should be unbiased (its average value across repeated sampling equals the true parameter) and should have minimum variance (its estimates should vary as little as possible from sample to sample), making it both accurate and precise.

---

## 📝 Additional Practice Questions

4. (Multiple Choice) For a Binomial distribution with parameters *n* and *p*, what is the variance?
   - **A.** np
   - **B.** npq
   - **C.** p(1-p)
   - **D.** n²p

5. (Multiple Choice) Which of the following is a necessary condition for a Binomial experiment?
   - **A.** The number of trials is infinite
   - **B.** Trials are independent, each with only two possible outcomes and constant probability of success
   - **C.** The probability of success changes after each trial
   - **D.** The variable is continuous

6. (Short Answer) Under what condition can the Poisson distribution be used as a good approximation to the Binomial distribution?

7. (Multiple Choice) In a standard Normal distribution, approximately what percentage of observations lie within ±2 standard deviations of the mean?
   - **A.** 50%
   - **B.** 68%
   - **C.** 95%
   - **D.** 99.7%

8. (Short Answer) Explain the difference between a Probability Density Function (PDF) and a Cumulative Distribution Function (CDF) for a continuous random variable.

9. (Multiple Choice) Which statement correctly distinguishes a discrete distribution from a continuous distribution?
   - **A.** Discrete variables can take any value in an interval; continuous variables take only countable values
   - **B.** Discrete variables take countable values (described by a PMF); continuous variables take any value in a range (described by a PDF)
   - **C.** Both use the same PMF formula
   - **D.** Continuous distributions never have a mean

10. (Short Answer) Why is the sample mean generally considered a "good" estimator of the population mean?

11. (Multiple Choice) A quality control process rejects a shipment if more than 3 defective items are found out of 20 inspected. Which distribution most naturally models the number of defective items, assuming each item independently has the same small probability of being defective?
    - **A.** Normal distribution
    - **B.** Poisson or Binomial distribution
    - **C.** Uniform distribution
    - **D.** Exponential distribution only

12. (Short Answer) What does it mean for an estimator to be "biased," and give a simple example of what that would look like in practice.

---

### Answers

4. **Correct answer: B — npq**
   The variance of a Binomial(n, p) distribution is npq (equivalently np(1−p)), combining the number of trials with both the success and failure probabilities; np alone is the mean, not the variance.

5. **Correct answer: B — Trials are independent, each with only two possible outcomes and constant probability of success**
   A Binomial setting requires a fixed number of independent trials, each with exactly two outcomes (success/failure) and the same probability of success on every trial — violating any of these (e.g., changing p, more than two outcomes) means the Binomial model doesn't apply.

6. **Answer:** The Poisson distribution is a good approximation to the Binomial when the number of trials *n* is large and the probability of success *p* is small, such that the mean λ = np remains moderate. This "rare event" condition avoids the computational difficulty of large-*n* binomial calculations while giving nearly identical results.

7. **Correct answer: C — 95%**
   Per the empirical (68-95-99.7) rule for the normal distribution, about 68% of data lies within ±1σ, about 95% within ±2σ, and about 99.7% within ±3σ of the mean.

8. **Answer:** The PDF, f(x), describes the relative likelihood of the variable being near a given value — for continuous variables, the probability of any exact point is zero, so you interpret area under the PDF curve over an interval as probability. The CDF, F(x) = P(X ≤ x), is the running total (integral of the PDF from −∞ to x) and directly gives the probability that the variable is less than or equal to x; the PDF is the derivative of the CDF.

9. **Correct answer: B — Discrete variables take countable values (described by a PMF); continuous variables take any value in a range (described by a PDF)**
   Discrete random variables (e.g., number of heads in 10 flips) have a countable set of outcomes with probabilities assigned via a PMF; continuous random variables (e.g., time, height) take any value in an interval and use a PDF, where probabilities are computed over ranges rather than at single points.

10. **Answer:** The sample mean is a good estimator of the population mean because it is unbiased (its expected value across repeated sampling equals the true population mean) and, among linear unbiased estimators, it has minimum variance (it is efficient), so it tends to be both accurate on average and precise from sample to sample.

11. **Correct answer: B — Poisson or Binomial distribution**
    This is a classic fixed-trials, small-success-probability scenario: it can be modeled exactly with the Binomial distribution (n = 20, defect probability p), and if p is small and n is reasonably large, the Poisson distribution (with λ = np) offers a close and computationally simpler approximation.

12. **Answer:** An estimator is biased when its expected (average) value over repeated sampling does not equal the true population parameter — it systematically over- or under-estimates. For example, if you estimated a population's average height using only people over 6 feet tall as your sample, the sample mean would be biased upward, consistently overestimating the true population average height regardless of sample size.
