# Lesson 08: Advanced Statistics — Knowledge Check

## Concept Primer

**Hypothesis testing** is the formal procedure statisticians use to decide, using sample data, whether a claim about a population is credible. The process starts with two competing statements: the **null hypothesis (H₀)**, which typically asserts "no effect" or "no difference" and is assumed true until evidence says otherwise, and the **alternative hypothesis (H₁ or Hₐ)**, which represents the claim we are trying to find support for. A hypothesis itself is simply a proposed, testable assumption about a population parameter (such as a mean or proportion) — it is not yet a conclusion, just the statement being put on trial.

To decide between H₀ and H₁, we compute a **test statistic** (e.g., a z-score or t-score) from the sample and compare it against a **critical value** determined by the chosen significance level (α, commonly 0.05). The set of test-statistic values extreme enough to lead us to reject H₀ is called the **critical region** (or rejection region). If the observed test statistic falls inside this region, we reject the null hypothesis; if it falls outside, we fail to reject it. Closely related is the **p-value**: the probability of observing a result as extreme as, or more extreme than, the sample result, assuming H₀ is true. A p-value smaller than α leads to rejecting H₀.

Because we are making a decision under uncertainty, two kinds of errors are possible. A **Type I error** (false positive) occurs when we reject a true null hypothesis — we conclude there's an effect when there really isn't one; its probability is exactly α. A **Type II error** (false negative) occurs when we fail to reject a false null hypothesis — we miss a real effect; its probability is denoted β, and **1 − β** is the test's **power** (its ability to correctly detect a true effect). There is an inherent trade-off: tightening the criteria to reduce Type I errors (lowering α) tends to increase the risk of Type II errors, all else equal.

A **confidence interval (CI)** is a range of plausible values for a population parameter, built from sample data, associated with a confidence level (e.g., 95%). A 95% CI means that if we repeated the sampling process many times, about 95% of the intervals constructed this way would contain the true population parameter. CIs and hypothesis tests are two sides of the same coin: if a 95% CI for a parameter excludes the null value, a two-sided test at α = 0.05 would reject H₀.

Different test statistics apply depending on the data and question at hand. The **t-test** compares means (one sample against a known value, or two sample means against each other) and is preferred over the z-test when the population standard deviation is unknown and/or the sample size is small, since it uses the t-distribution, which has heavier tails to account for that extra uncertainty. The **chi-square test** is used for categorical data — testing goodness-of-fit or independence between two categorical variables (e.g., in a contingency table). **ANOVA (Analysis of Variance)** extends the two-sample t-test to compare the means of three or more groups simultaneously, using an F-statistic to determine whether at least one group mean differs significantly from the others, while controlling the overall Type I error rate that would build up from running many pairwise t-tests.

## Knowledge Check Questions

**1. A statement made about a population for a testing purpose is called:**
- **A.** Statistics
- **B.** Hypothesis
- **C.** Parameter estimate
- **D.** Test statistics

**2. What does critical region lead to?**
- **A.** Acceptance of the null hypothesis
- **B.** Rejection of null hypothesis
- **C.** Depends upon whether the test is one- or two-sided
- **D.** Depends on the sample size

**3. In the context of hypothesis testing, what does a Type I error represent?**
- **A.** Accepting a true null hypothesis
- **B.** Rejecting a false null hypothesis
- **C.** Rejecting a true null hypothesis
- **D.** Accepting a false null hypothesis

## Answers

**1. Correct answer: B. Hypothesis**
A hypothesis in statistics is a proposed explanation or assumption about a population parameter, made in order to test it through statistical analysis. It is a claim about the population, not a computed number like a statistic or test statistic.

**2. Correct answer: B. Rejection of null hypothesis**
The critical region is the range of test-statistic values that, if the observed statistic falls within it, leads to the rejection of the null hypothesis. It is defined by the significance level, independent of whether the test is one- or two-tailed.

**3. Correct answer: C. Rejecting a true null hypothesis**
A Type I error occurs when the null hypothesis is actually true but the test incorrectly rejects it — a "false positive." Its probability equals the chosen significance level, α.

## 📝 Additional Practice Questions

**4. (Multiple Choice)** What is the probability of committing a Type I error called?
- **A.** Power of the test
- **B.** Significance level (α)
- **C.** p-value
- **D.** Confidence level

**5. (Multiple Choice)** A Type II error occurs when:
- **A.** We reject a true null hypothesis
- **B.** We reject a false null hypothesis
- **C.** We fail to reject a false null hypothesis
- **D.** We fail to reject a true null hypothesis

**6. (Short Answer)** Define the p-value in your own words, and state the decision rule for rejecting H₀ when comparing it to α.

**7. (Multiple Choice)** Which test would you use to compare the mean commute time of a small sample (n = 12) against a hypothesized value, when the population standard deviation is unknown?
- **A.** z-test
- **B.** One-sample t-test
- **C.** Chi-square test
- **D.** ANOVA

**8. (Multiple Choice)** You want to test whether there is an association between two categorical variables, such as "customer region" and "product preference." Which test is most appropriate?
- **A.** Paired t-test
- **B.** Chi-square test of independence
- **C.** One-way ANOVA
- **D.** Z-test for proportions

**9. (Short Answer)** Explain, in one or two sentences, why a 95% confidence interval does NOT mean "there is a 95% probability that the true parameter lies in this specific interval."

**10. (Multiple Choice)** A researcher wants to compare the average test scores of students taught by four different instructors. Which technique is best suited for this comparison?
- **A.** Chi-square goodness-of-fit test
- **B.** Paired t-test
- **C.** One-way ANOVA
- **D.** Simple linear regression

**11. (Multiple Choice)** If a 95% confidence interval for the difference in two population means is (−2.1, 4.8), what can we conclude about a two-sided hypothesis test of H₀: μ₁ = μ₂ at α = 0.05?
- **A.** Reject H₀, since the interval contains positive and negative values
- **B.** Fail to reject H₀, since the interval contains 0
- **C.** Reject H₀, since the interval does not contain 0
- **D.** Cannot determine without the sample size

**12. (Short Answer)** What is statistical power, and name two ways a researcher can increase the power of a hypothesis test.

### Answers

**4. Correct answer: B. Significance level (α)**
α is defined as the probability of rejecting a true null hypothesis, i.e., the pre-set threshold risk of a Type I error (commonly 0.05). The p-value is the observed evidence against H₀ in a specific sample, not the pre-set error rate itself.

**5. Correct answer: C. We fail to reject a false null hypothesis**
A Type II error is a "false negative": the null hypothesis is actually false (there is a real effect), but the test does not have enough evidence to reject it, so we mistakenly retain H₀.

**6. Sample answer:** The p-value is the probability, assuming the null hypothesis is true, of observing a test statistic at least as extreme as the one actually observed. Decision rule: if p-value ≤ α, reject H₀ (the result is considered statistically significant); if p-value > α, fail to reject H₀.

**7. Correct answer: B. One-sample t-test**
With a small sample and an unknown population standard deviation, the t-distribution (which has heavier tails to reflect added uncertainty from estimating the standard deviation) is used instead of the z-distribution.

**8. Correct answer: B. Chi-square test of independence**
The chi-square test of independence evaluates whether two categorical variables are associated by comparing observed frequencies in a contingency table against the frequencies expected under independence.

**9. Sample answer:** The 95% confidence level describes the long-run reliability of the *procedure*: if we repeated the sampling and interval-construction process many times, about 95% of the resulting intervals would contain the true parameter. Any single, already-computed interval either does or does not contain the true value — it is not a random event anymore, so it's incorrect to assign it a 95% "probability" of containing the parameter.

**10. Correct answer: C. One-way ANOVA**
One-way ANOVA is designed to compare the means of three or more independent groups (here, four instructors) using a single categorical factor, testing whether at least one group mean differs significantly from the rest.

**11. Correct answer: B. Fail to reject H₀, since the interval contains 0**
Because the 95% CI for the mean difference spans from −2.1 to 4.8 and includes 0 (the null value of "no difference"), a two-sided test at α = 0.05 would not have enough evidence to reject H₀: μ₁ = μ₂.

**12. Sample answer:** Statistical power is the probability that a test correctly rejects a false null hypothesis (1 − β), i.e., the test's ability to detect a real effect when one exists. Power can be increased by: (1) increasing the sample size, (2) increasing the significance level α (accepting more Type I error risk), (3) reducing measurement/sampling variability, or (4) targeting/expecting a larger true effect size.
