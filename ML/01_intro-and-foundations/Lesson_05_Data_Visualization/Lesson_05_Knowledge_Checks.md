# Lesson 05: Data Visualization — Knowledge Checks

## Concept Primer

Data visualization turns raw numbers into pictures that a human brain can interpret in seconds. The choice of chart is not cosmetic — it encodes a claim about the data (a trend, a comparison, a distribution, a relationship), so picking the wrong chart type can actively mislead a reader even when the underlying numbers are correct. Before writing any plotting code, it helps to ask: am I comparing categories, tracking change over time, showing a distribution, or showing a relationship between two variables? That question determines the chart family to reach for.

**Chart types and when to use them.** Line plots are the default choice for continuous, ordered data — most commonly time series — because connecting points with a line visually emphasizes trend and rate of change. Bar charts are for comparing discrete categories against each other (sales by region, counts by category); their length encodes magnitude, which the eye reads more accurately than area or angle. Scatter plots reveal the relationship between two continuous variables (e.g., height vs. weight) and are the go-to tool for spotting correlation, clusters, or outliers. Histograms and box plots describe the distribution of a single variable — histograms show shape and spread via binned frequency, while box plots summarize median, quartiles, and outliers compactly, which makes them excellent for comparing distributions across several groups side by side. Pie charts show parts of a whole but are best limited to a handful of categories, since the human eye is poor at comparing angles precisely.

**Matplotlib** is the foundational plotting library in the Python data-science stack. It is a comprehensive, low-level library capable of producing static, animated, and interactive visualizations, and most other Python visualization libraries (including Seaborn) are built on top of it or interoperate closely with its `Figure`/`Axes` object model. A typical Matplotlib workflow is `fig, ax = plt.subplots()` followed by calls like `ax.plot()`, `ax.bar()`, or `ax.scatter()`, then `plt.show()`. Because it exposes fine-grained control over every element of a figure (ticks, spines, colors, annotations), it is the tool of choice when you need precise, publication-quality static figures.

**Seaborn** is a statistical visualization library built on top of Matplotlib. It trades some of Matplotlib's low-level flexibility for high-level convenience: a single function call like `sns.boxplot()`, `sns.heatmap()`, or `sns.pairplot()` can produce a polished, statistically informative plot — complete with sensible default themes, color palettes, and automatic aggregation (e.g., confidence intervals on a line plot) — that would take many lines of raw Matplotlib code to replicate. Seaborn works especially well with "tidy" pandas DataFrames, where each column is a variable and each row is an observation.

**Plotly** takes a different approach: it is built for interactivity and the web. Where Matplotlib and Seaborn typically produce a static raster or vector image, Plotly generates HTML/JavaScript-backed figures that support hovering for tooltips, zooming, panning, and clicking to filter — and can be embedded directly in web applications and dashboards (e.g., with Dash). This makes Plotly the preferred choice when the audience needs to explore the data themselves rather than just view a fixed snapshot, at some cost in simplicity for quick, throwaway static plots.

**Putting it together.** In practice, a data scientist often layers these tools: Matplotlib or Seaborn for fast, static exploratory analysis and reports; Plotly for interactive dashboards or when a stakeholder needs to drill into the data live. Regardless of library, good visualizations share the same principles: choose the chart type that matches the analytical question, label axes and provide a title, avoid unnecessary decoration ("chart junk"), and use color and scale deliberately rather than by default.

## Knowledge Check Questions

**1. What is the primary use of Matplotlib in data visualization?**

- **A.** To create interactive web applications
- **B.** To develop 3D games
- **C.** To create static, animated, and interactive visualizations in Python
- **D.** To develop desktop applications

**2. What is a line plot typically used for in Matplotlib?**

- **A.** For comparing categorical data
- **B.** For displaying trends over continuous intervals or time
- **C.** For showing the relationship between two categorical variables
- **D.** For 3D surface mapping

**3. What is the primary advantage of using Plotly for data visualizations compared to other static plotting libraries?**

- **A.** Plotly is built on top of Matplotlib.
- **B.** Plotly does not support 3D plotting.
- **C.** Plotly allows the creation of interactive plots that can be used in web applications.
- **D.** Plotly charts are static and cannot be manipulated.

### Answers

**1. Correct answer: C — To create static, animated, and interactive visualizations in Python.**
Matplotlib is a comprehensive Python library designed specifically for producing a wide range of visualizations — static, animated, and (via companion tooling) interactive — rather than for game development, desktop app development, or web-app development, which are unrelated use cases.

**2. Correct answer: B — For displaying trends over continuous intervals or time.**
Line plots connect ordered data points with a continuous line, which makes them ideal for showing how a value changes across a continuous axis such as time, so trends and patterns are easy to spot. Categorical comparisons are better served by bar charts, and line plots have no inherent connection to 3D surface mapping.

**3. Correct answer: C — Plotly allows the creation of interactive plots that can be used in web applications.**
Plotly's defining advantage over static libraries is interactivity: users can hover, zoom, and pan on rendered charts, and those charts can be embedded directly into web pages and dashboards. Plotly is not built on top of Matplotlib, and it does support 3D plotting, so the other options are incorrect.

## 📝 Additional Practice Questions

**1. (Multiple Choice) Which chart type is generally best suited for comparing a numeric value across several discrete categories (e.g., total sales per product category)?**

- **A.** Line plot
- **B.** Bar chart
- **C.** Scatter plot
- **D.** Pie chart with 20 slices

**2. (Multiple Choice) In Matplotlib's object-oriented interface, which two objects do you typically create first with `plt.subplots()`?**

- **A.** `plot` and `chart`
- **B.** `figure` and `axes`
- **C.** `canvas` and `window`
- **D.** `series` and `data`

**3. (Multiple Choice) Which Python visualization library is built on top of Matplotlib and is designed to make statistical plots easier to produce with less code?**

- **A.** NumPy
- **B.** Seaborn
- **C.** Plotly
- **D.** Pandas.plot

**4. (Multiple Choice) A data scientist wants to visualize the relationship between two continuous variables, such as advertising spend and sales revenue, to check for correlation. Which chart type should they use?**

- **A.** Bar chart
- **B.** Pie chart
- **C.** Scatter plot
- **D.** Histogram

**5. (Multiple Choice) Which chart is most appropriate for showing the distribution (shape, spread, and central tendency) of a single continuous variable, such as customer ages?**

- **A.** Histogram
- **B.** Line plot
- **C.** Bar chart grouped by category
- **D.** Scatter plot

**6. (Multiple Choice) Why might a Seaborn box plot be preferred over a plain bar chart when comparing exam scores across five classrooms?**

- **A.** Box plots can only be drawn in Plotly, not Seaborn
- **B.** Box plots show median, quartiles, and outliers, giving a fuller picture of each group's distribution, not just an average
- **C.** Bar charts cannot display numeric data at all
- **D.** Box plots always require 3D rendering

**7. (Multiple Choice) Which of the following is a legitimate reason to choose Plotly over Matplotlib for a specific project?**

- **A.** The final chart needs to be embedded in an interactive web dashboard where users can hover and filter
- **B.** The chart must be printed in a black-and-white academic paper with no interactivity
- **C.** The team wants the smallest possible code footprint for a one-off static chart
- **D.** The dataset has fewer than 10 rows

**8. (Short Answer) Explain the main functional difference between Matplotlib and Plotly in terms of how a viewer can interact with the resulting chart.**

**9. (Short Answer) A colleague creates a pie chart with 15 categories to show market share. Why is this generally considered poor visualization practice, and what would you recommend instead?**

**10. (Short Answer) In a pandas + Matplotlib workflow, what is the purpose of calling `plt.title()`, `plt.xlabel()`, and `plt.ylabel()` on a plot, even though the chart would technically still render without them?**

### Answers

**1. Correct answer: B — Bar chart.**
Bar charts encode magnitude as bar length, which the human eye compares accurately across discrete categories, making them the standard choice for categorical comparisons. Line plots imply continuity/order that categories may not have, scatter plots are for two continuous variables, and a 20-slice pie chart would be unreadable.

**2. Correct answer: B — `figure` and `axes`.**
`fig, ax = plt.subplots()` returns a `Figure` object (the overall canvas/window) and one or more `Axes` objects (the individual plot areas where data is actually drawn) — this is the foundation of Matplotlib's object-oriented API.

**3. Correct answer: B — Seaborn.**
Seaborn is explicitly built on top of Matplotlib and provides high-level functions for common statistical charts (box plots, heatmaps, pair plots, etc.) with better default styling and less boilerplate code than raw Matplotlib.

**4. Correct answer: C — Scatter plot.**
Scatter plots plot individual data points along two continuous axes, making patterns of correlation, clustering, and outliers visually apparent — exactly what's needed to inspect a relationship between two continuous variables like spend and revenue.

**5. Correct answer: A — Histogram.**
A histogram bins a continuous variable into intervals and shows the frequency (count) of observations in each bin, which directly reveals the shape, spread, skew, and central tendency of a single variable's distribution.

**6. Correct answer: B — Box plots show median, quartiles, and outliers, giving a fuller picture of each group's distribution, not just an average.**
A bar chart of average scores hides variability entirely; a box plot per classroom shows the median, interquartile range, and any outlier scores, allowing a much richer, side-by-side comparison of five distributions at once. (Options A, C, and D are factually false about box plots and bar charts.)

**7. Correct answer: A — The final chart needs to be embedded in an interactive web dashboard where users can hover and filter.**
Plotly's core strength is producing HTML/JavaScript-based charts that support hovering, zooming, panning, and embedding in web applications and dashboards. For a static black-and-white print chart, a tiny one-off script, or a trivially small dataset, the added complexity of Plotly is not worth it and Matplotlib is usually a simpler fit.

**8. Sample answer:** Matplotlib produces primarily static (or, with extra effort, animated) images — once rendered, a viewer typically cannot manipulate the chart itself (no hover tooltips, no zoom/pan) unless embedded in a special interactive backend. Plotly renders charts as interactive HTML/JavaScript objects by default, so viewers can hover over points to see tooltips, zoom into regions, pan across the chart, and toggle legend items — without any extra code from the chart author. This makes Plotly better suited for exploratory dashboards and Matplotlib better suited for fixed, publication-style figures.

**9. Sample answer:** Pie charts rely on the viewer comparing angles (or areas) of slices, which humans do poorly and inaccurately once there are more than about five or six categories — with 15 slices, many will look nearly identical in size, making the chart hard to read and easy to misinterpret. A better alternative is a horizontal bar chart sorted by value (largest to smallest), which encodes magnitude as bar length — something the eye reads precisely — and scales cleanly to many categories; if the "long tail" of small categories isn't individually important, they can also be grouped into an "Other" bucket.

**10. Sample answer:** Titles and axis labels provide the context needed to correctly interpret a chart — without them, a viewer sees only unlabeled shapes and numbers and cannot know what is being measured, in what units, or what the chart is claiming. Good labeling is part of the "grammar" of visualization: it turns a technically correct plot into a communication tool that a reader can understand without needing the code or the author present to explain it.
