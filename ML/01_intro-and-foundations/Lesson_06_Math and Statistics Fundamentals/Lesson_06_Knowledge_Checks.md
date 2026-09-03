# Lesson 06 — Math and Statistics Fundamentals: Knowledge Check

## Concept Primer

**Scalars and vectors.** A *scalar* is a quantity fully described by a single number — its magnitude — such as mass, temperature, or speed. A *vector* has both magnitude and direction, such as velocity, displacement, or force. Vectors are typically written as a lowercase letter with an arrow on top (e.g. 𝑥⃗) or as an ordered list of components, e.g. A = [2, -3, 7]. The **dot product** of two vectors A = [a₁, a₂, a₃] and B = [b₁, b₂, b₃] is a scalar computed as A·B = a₁b₁ + a₂b₂ + a₃b₃. It shows up constantly in ML (e.g. computing similarity, projections, and the core operation inside matrix multiplication).

**Measures of central tendency.** The **mean** is the arithmetic average (sum of values divided by count) and is sensitive to outliers — a single extreme value can pull it strongly in one direction. The **median** is the middle value of a sorted dataset (or the average of the two middle values for an even-sized dataset) and is robust to outliers. The **mode** is the most frequently occurring value in a dataset; a dataset can have no mode, one mode (unimodal), or multiple modes (multimodal). Choosing which measure to report depends on the data's shape and the presence of outliers.

**Measures of spread.** **Range** is the difference between the maximum and minimum values — simple but very sensitive to outliers. **Variance** measures the average squared deviation of each data point from the mean, capturing how spread out the data is; because it's in squared units, we usually take its square root to get the **standard deviation**, which is in the same units as the original data and is easier to interpret. Low standard deviation means data points cluster tightly around the mean; high standard deviation means they're spread widely.

**Distribution shape and skewness.** A distribution is **symmetric** when its left and right halves mirror each other around the center (mean ≈ median ≈ mode), as in a normal/bell-shaped distribution, and its skewness is near 0. **Positive (right) skewness** means the right tail is longer/fatter than the left — a few unusually large values pull the mean above the median. **Negative (left) skewness** means the left tail is longer — a few unusually small values pull the mean below the median. Recognizing skew matters because many statistical techniques assume roughly symmetric, normal-like data.

**Correlation.** Correlation quantifies the strength and direction of a linear relationship between two variables, typically summarized by the Pearson correlation coefficient, which ranges from -1 (perfect negative/inverse relationship) to +1 (perfect positive relationship), with 0 indicating no linear relationship. Correlation does not imply causation — two variables can be strongly correlated without one causing the other.

## Knowledge Check Questions (Original)

**Question 1.** If A = [2, -3, 7] and B = [-4, 2, -4], find the dot product of the vectors A and B.
- **A.** 42
- **B.** -42
- **C.** 12
- **D.** 22

**Question 2.** What is/are true about scalars and vectors?
- **A.** Scalar quantities can be described by specifying only their magnitude
- **B.** Distance is an example of a vector quantity
- **C.** Vectors are represented using a lowercase letter with an arrow on top, like 𝑥⃗
- **D.** Vector quantities require both magnitude and direction

**Question 3.** What is the mode in statistics?
- **A.** The middle value in a dataset
- **B.** The most frequently occurring data point in a dataset
- **C.** The average value in a dataset
- **D.** The difference between the largest and smallest data points in a dataset

**Question 4.** What does a positive skewness value indicate?
- **A.** The data is skewed left, that is, the left tail is longer than the right tail.
- **B.** The data is skewed right, that is, the right tail is longer than the left tail.
- **C.** The data has a near 0 skewness.
- **D.** The data is symmetric.

### Answers

**1. Answer: B (-42)**
A·B = (2)(-4) + (-3)(2) + (7)(-4) = -8 - 6 - 28 = -42. Multiply each corresponding pair of components and sum the results.

**2. Answer: A, C, and D**
Scalars need only a magnitude (A is true), and vectors need both magnitude and direction and are written as a lowercase letter with an arrow, e.g. 𝑥⃗ (C and D are true). B is false — distance is a scalar quantity (it has magnitude only); *displacement*, not distance, is the vector analog.

**3. Answer: B**
The mode is the value that occurs most frequently in a dataset. (Option A describes the median, C describes the mean, and D describes the range.)

**4. Answer: B**
A positive skewness value means the right tail of the distribution is longer/fatter than the left tail, so a few large outlying values pull the mean above the median.

## 📝 Additional Practice Questions

**Q5 (MCQ).** Given vectors A = [1, 2, 3] and B = [4, -5, 6], what is A·B?
a) 0
b) 12
c) -12
d) 22

**Q6 (Short answer).** What is the magnitude (Euclidean norm) of the vector v = [3, 4]?

**Q7 (MCQ).** Which of the following is NOT a vector quantity?
a) Velocity
b) Displacement
c) Speed
d) Force

**Q8 (Short answer).** What is the valid range of values for the Pearson correlation coefficient?

**Q9 (MCQ).** For the dataset {2, 4, 4, 4, 5, 5, 7, 9}, what is the mode?
a) 4
b) 5
c) 6
d) 7

**Q10 (Short answer).** Compute the mean of the dataset {2, 4, 4, 4, 5, 5, 7, 9}.

**Q11 (MCQ).** What is the median of {3, 7, 9, 15, 21}?
a) 7
b) 9
c) 15
d) 12

**Q12 (MCQ).** Which measure of central tendency is most sensitive to (most affected by) outliers?
a) Mean
b) Median
c) Mode
d) Range

**Q13 (Short answer).** In one or two sentences, define variance and explain how it relates to standard deviation.

**Q14 (MCQ).** If a distribution has skewness approximately equal to 0, which shape does it most likely have?
a) Strongly left-skewed
b) Strongly right-skewed
c) Roughly symmetric (bell-shaped/normal-like)
d) Bimodal with two distant peaks

### Answers

**Q5. Answer: b) 12**
A·B = (1)(4) + (2)(-5) + (3)(6) = 4 - 10 + 18 = 12.

**Q6. Answer: 5**
Magnitude = √(3² + 4²) = √(9 + 16) = √25 = 5. This is the classic 3-4-5 right triangle.

**Q7. Answer: c) Speed**
Speed is a scalar — it only has magnitude (how fast). Velocity, displacement, and force all require a direction in addition to magnitude, making them vectors.

**Q8. Answer: -1 to +1 (inclusive)**
A correlation of -1 indicates a perfect negative linear relationship, +1 indicates a perfect positive linear relationship, and 0 indicates no linear relationship.

**Q9. Answer: a) 4**
4 appears three times, more than any other value (5 appears twice, 2, 7, and 9 each appear once), so 4 is the mode.

**Q10. Answer: 5**
Sum = 2+4+4+4+5+5+7+9 = 40; there are 8 values, so mean = 40 / 8 = 5.

**Q11. Answer: b) 9**
The dataset is already sorted with 5 values (an odd count), so the median is the middle (3rd) value: 9.

**Q12. Answer: a) Mean**
The mean uses every value's magnitude in its calculation, so a single extreme outlier can shift it substantially. The median and mode are far more robust to outliers, and range is about spread rather than central tendency (though it too is very outlier-sensitive, it isn't a measure of central tendency).

**Q13. Answer (sample): Variance is the average of the squared differences between each data point and the mean, and it measures how spread out a dataset is.**
Standard deviation is simply the square root of the variance, which brings the measure back into the original units of the data (rather than squared units), making it easier to interpret alongside the mean.

**Q14. Answer: c) Roughly symmetric (bell-shaped/normal-like)**
A skewness value near 0 indicates the left and right tails are roughly balanced, which is characteristic of a symmetric distribution such as the normal distribution, where mean ≈ median ≈ mode.
