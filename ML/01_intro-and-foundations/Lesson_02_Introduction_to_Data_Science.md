# Lesson 02: Introduction to Data Science

*Applied Data Science with Python*

## 🎯 Learning Objectives

By the end of this lesson, you will be able to:

- **List the steps of the data science process** to solve problems systematically — i.e., walk through the full pipeline from defining a business problem to deploying a working model.
- **Explain the basics of data science** and its application to derive meaningful insights from raw data.
- **Explore the Python packages for data science** to efficiently perform data analysis, data manipulation, and data visualization.
- **Describe the types of plots available for visualization** to communicate data insights and trends effectively to both technical and non-technical audiences.

---

## 1. What Is Data Science?

**Data science** is a multidisciplinary field that uses scientific methods, processes, algorithms, and systems to derive meaningful insights from **structured** data (neatly organized in rows/columns, like a spreadsheet or SQL table) and **unstructured** data (text, images, audio, sensor streams, etc.).

In practice, data science sits at the intersection of three things:

1. **Domain expertise** — understanding the business or scientific problem well enough to ask the right questions.
2. **Mathematics and statistics** — the analytical models used to find patterns, correlations, and predictions.
3. **Computer science / technology** — the tools, programming languages, and infrastructure used to store, process, and scale the analysis.

### Everyday Example

Every time you use a search engine or make a purchase on Amazon, you generate valuable data that is consumed by data-science-driven systems running quietly in the background. These systems collect data about your interactions with the platform — what you searched for, what you clicked, what you bought — in order to understand your preferences and then personalize the results you see next (search rankings, "recommended for you" product lists, etc.). This feedback loop of *collect → analyze → personalize* is one of the most common real-world applications of data science.

### Where Data Science Comes From

Data science isn't a single skill — it emerges from combining several disciplines:

| Pillar | What It Contributes | Examples |
|---|---|---|
| **Domain expertise & scientific methods** | Frames the problem correctly and validates whether results make sense | Scientific tools and methods, analysis techniques |
| **Mathematical & statistical models** | Provides the analytical backbone for finding patterns and making predictions | Statistical inference, probability, linear algebra |
| **Technology** | Provides the means to store, process, and operationalize data at scale | Data processing tools, the Python language, libraries, application design, operating systems |

Think of it as a Venn diagram where "data science" only truly happens in the overlap of all three circles — a brilliant statistician with no domain knowledge, or a great engineer with no statistics background, will each struggle to produce genuinely useful insights on their own.

---

## 2. Applications of Data Science

Data science isn't confined to tech companies — it shows up across nearly every industry. The slides highlight three concrete examples:

### 2.1 Healthcare — Wearable Devices

Wearable devices (like fitness trackers and smartwatches) use data science to make sense of the continuous stream of data coming from their biometric sensors (heart rate, steps, sleep patterns, blood oxygen, etc.).

The data flow typically looks like this:

**Wearable device → Biometric data transfer → IoT gateway → Data transfer to servers → Enterprise infrastructure → Data analytics → Engagement dashboard → Informed decision-making**

In other words: the sensor captures raw biometric signals, an IoT gateway relays that data to cloud servers, the enterprise infrastructure stores and processes it, analytics are run on top of it, and the results are surfaced on a dashboard that helps either the user or a clinician make better health decisions (e.g., flagging an irregular heartbeat or recommending more activity).

### 2.2 Search Engines — Google

Google uses data science to offer relevant search recommendations *as you type* your query (autocomplete/predictive search). This is only possible because of fast, real-time analytics powered by modern, highly scalable infrastructure, tools, and technologies that can process billions of queries and match them against historical search patterns in milliseconds.

### 2.3 Finance — Loan Approval

When a loan applicant submits an application through a **loan application portal**, that data is transferred to servers and enterprise infrastructure, where data analytics are applied to it. The output — things like the applicant's **credit report, credit history, approved amount, and risk score** — is surfaced on an **engagement dashboard** that helps a loan manager make an informed decision quickly, rather than manually sifting through paperwork.

**Common thread across all three examples:** raw data is captured at the source → transferred/stored in enterprise infrastructure → processed with analytics → presented via a dashboard → used to make a faster, more informed decision. This "capture → process → decide" pattern is essentially the blueprint for most real-world data science systems.

---

## 3. The Data Science Process

Solving a data science problem isn't a single step — it's a structured, iterative pipeline. The slides describe a **7-step process**:

```
1. Problem definition
2. Data collection
3. Data cleaning and exploration
4. Feature engineering
5. Model building and training
6. Model evaluation
7. Model deployment
```

### Step-by-Step Breakdown

| # | Step | What Happens | Why It Matters |
|---|---|---|---|
| 1 | **Problem definition** | Clearly define the goal or question to be addressed through data analysis. | This forms the foundation for every subsequent step — if the problem is poorly defined, even a technically perfect model will solve the wrong thing. |
| 2 | **Data collection** | Gather relevant datasets or information sources necessary to address the defined problem. | Data can come from databases, APIs, sensors, logs, surveys, or third-party sources — the quality and relevance of this data caps how good your final model can be. |
| 3 | **Data cleaning and exploration** | Preprocess the data by handling missing values, outliers, and other inconsistencies; explore the dataset to gain insights and identify patterns. | Real-world data is messy — this step (often called EDA, or Exploratory Data Analysis) ensures the data is trustworthy before modeling. |
| 4 | **Feature engineering** | Create or transform new features to enhance the dataset's information and improve model performance. | Example: turning a raw "date of birth" column into an "age" feature, which is usually more directly useful to a model. |
| 5 | **Model building and training** | Develop a predictive or descriptive model using machine learning algorithms and train it on the prepared dataset. | This is where the actual "learning" happens — the algorithm finds patterns in the training data. |
| 6 | **Model evaluation** | Evaluate, optimize, and fine-tune the model for peak performance. | Metrics (accuracy, precision, recall, RMSE, etc.) tell you whether the model is actually good enough to trust. |
| 7 | **Model deployment** | Deploy the finalized model into a production environment for real-world use. | A model only creates business value once it's actually running and making predictions on live data. |

> **Key insight:** This process is rarely a straight line. In practice, teams frequently loop back — for example, discovering during model evaluation that a feature was engineered incorrectly, which sends you back to step 4 or even step 2.

---

## 4. Python for Data Science

Python has become the **preferred programming language for data science projects across industries**. It comes with a rich ecosystem of open-source packages — such as **NumPy** and **Pandas** — that are purpose-built for data cleaning, exploration, and visualization, which is why it's the default choice taught in this course.

### 4.1 Why Python? — Key Advantages

- **Open-source, interpreted, high-level language** that supports object-oriented programming — meaning it's free to use, doesn't need to be compiled before running, and lets you structure code around reusable objects and classes.
- **Ease of use and simple syntax** — Python reads almost like plain English, which lowers the learning curve for people coming from non-programming backgrounds (e.g., statisticians, domain scientists).
- **Scalability when compared to R** — Python generally handles larger production workloads and integrates more easily into full software systems than R, which is more narrowly focused on statistics.
- **A wide variety of data science libraries and packages** are available out of the box or via package managers like `pip`.
- **Compatibility with all major operating systems** (Windows, macOS, Linux) — code written on one platform typically runs unchanged on another.
- **New data science libraries are created daily** by a vast, active global community of contributors, meaning the ecosystem keeps growing and improving.
- **Powerful visualization libraries** (Matplotlib, Seaborn, Plotly, etc.) make it easy to turn numeric results into compelling charts.

---

## 5. Key Python Packages for Data Science

Each package below solves a different piece of the data science puzzle. Together, they form the backbone of almost every Python-based analysis.

### 5.1 NumPy (Numerical Python)

**What it is:** A Python library for scientific computing that supports large multi-dimensional arrays and matrices, along with a comprehensive mathematical function library.

**What it's used for:** Performing complex mathematical operations on large datasets — such as linear algebra calculations, statistical analysis, and Fourier transforms — far faster than would be possible with plain Python lists.

**Real-world example:** Financial analysts use NumPy for quantitative analysis, such as calculating the mean return and volatility of stocks, to inform investment decisions. Because NumPy operations are vectorized (they operate on entire arrays at once rather than looping element-by-element), this kind of calculation on thousands of stock price records can run almost instantly.

### 5.2 Pandas

**What it is:** A library for the efficient storage and manipulation of structured data, such as time series and tables (its core objects are the `Series` and `DataFrame`).

**What it's used for:** Loading, cleaning, filtering, grouping, and reshaping tabular data.

**Real-world examples:**
- E-commerce companies use Pandas to analyze customer purchase history in order to recommend products and personalize the shopping experience.
- Researchers use Pandas to manage and analyze large datasets of health records to identify trends in disease outbreaks.

### 5.3 SciPy (Scientific Python)

**What it is:** An open-source library built on top of NumPy, used for implementing scientific formulas — the slides give the examples of the ideal gas law (**PV = nRT**) and Ohm's law (**V = IR**).

**What it's used for:** Tailored for scientific and engineering applications, such as weather forecasting and drug discovery.

**Real-world example:** Engineers use SciPy to solve complex mathematical problems in structural engineering, such as stress and strain analysis in materials — helping determine whether a bridge or building design can safely bear its expected load.

### 5.4 Statsmodels

**What it is:** A Python module that provides classes and functions for estimating a wide range of statistical models and for conducting statistical data exploration (e.g., regression, hypothesis testing, time-series analysis).

**Real-world examples:**
- Market researchers use Statsmodels to perform regression analysis to understand how factors like advertising spend affect sales.
- Policy analysts use Statsmodels to evaluate the impact of public policies on social and economic outcomes through statistical testing and analysis.

### 5.5 Scikit-learn

**What it is:** A widely-used, open-source machine learning library for Python known for its simplicity, ease of use, and versatility across many machine learning tasks (classification, regression, clustering, model selection, etc.).

**Real-world examples:**
- Identifying objects in images for autonomous vehicles and facial recognition systems.
- Detecting fraudulent transactions in banking and e-commerce platforms.
- Analyzing customer reviews for sentiment classification in marketing and social media analysis.

### 5.6 Matplotlib

**What it is:** A comprehensive plotting library for building static, animated, and interactive visualizations — including line plots, scatter plots, bar charts, histograms, pie charts, and more.

**Key fact:** Matplotlib is open-source and free to use, and it underpins many higher-level plotting libraries (including Seaborn).

### 5.7 Seaborn

**What it is:** A data visualization library built on top of Matplotlib.

**Why use it:**
- Provides a high-level interface for creating attractive, informative statistical graphics — histograms, box plots, violin plots, heatmaps, and error bars.
- Simplifies the process of creating aesthetically pleasing, informative plots, especially for statistical and categorical data (it requires far less manual styling code than raw Matplotlib).

### 5.8 Plotly

**What it is:** A Python library for creating interactive, publication-quality graphs and visualizations, well suited for web-based applications.

**Why use it:**
- Enables Python users to create interactive and customizable visualizations for data analysis (e.g., hover tooltips, zooming, panning).
- Supports various plot types, such as line plots, scatter plots, and histograms, which enhance data exploration — especially useful for dashboards viewed in a browser.

### Quick Reference Table

| Package | Category | Primary Purpose |
|---|---|---|
| NumPy | Numerical computing | Arrays, matrices, linear algebra, statistics |
| Pandas | Data manipulation | Tabular/time-series data storage & analysis |
| SciPy | Scientific computing | Scientific/engineering formulas & computations |
| Statsmodels | Statistics | Statistical modeling, regression, hypothesis testing |
| Scikit-learn | Machine learning | Classification, regression, clustering, ML pipelines |
| Matplotlib | Visualization | Foundational static/animated/interactive plots |
| Seaborn | Visualization | High-level statistical graphics (built on Matplotlib) |
| Plotly | Visualization | Interactive, web-ready visualizations |

---

## 6. Types of Plots (with Examples)

> **Note from the original slides:** Detailed examples of these plots, accompanied by explanations and Python code, are provided in the dedicated Data Visualization lesson. This lesson only introduces *when* and *why* to use each plot type.

### 6.1 Line Plot

A line plot displays data points connected by straight lines. It's the go-to choice for visualizing trends or relationships between two variables over time or other continuous intervals.

**Use cases:**
- Visualizing stock prices over time to track trends and inform investment decisions based on historical data.
- Displaying temperature variations throughout the year to analyze seasonal patterns and plan agricultural activities.

### 6.2 Marker Plot

A marker plot displays data points using distinct markers (dots, triangles, etc.) instead of, or in addition to, connecting lines. It's useful for scatter-style visualizations and for highlighting individual observations.

**Use cases:**
- Displaying individual data points on a map, such as marking specific survey locations.
- Plotting stock prices over time with markers indicating specific events, like buy or sell signals.

### 6.3 Scatter Plot

A scatter plot is a collection of points plotted along two axes (horizontal and vertical), where each point represents one observation's values for two variables.

**Use cases:**
- Analyzing the relationship between two variables, such as comparing height and weight across a population.
- Visualizing data clusters — for example, grouping students based on exam scores.

### 6.4 Area Plot

An area plot represents data with shaded regions beneath a line, which is useful for showing cumulative totals or proportions over time. (Area plots are also sometimes called **stack plots** when multiple categories are layered on top of one another.)

**Use cases:**
- Visualizing cumulative data changes over time, such as tracking total sales revenue across successive quarters.
- Illustrating how different categories contribute to a whole, such as displaying the evolution of market share over time.

### 6.5 Bar Plot

Bar plots are rectangular graphs (oriented vertically or horizontally) that compare data values against another axis — usually the x-axis for categories.

**Use cases:**
- Comparing sales of different products over a month.
- Displaying student grades across different subjects.

### 6.6 Grid Plot

Grid plots assist chart viewers in determining what value an otherwise unlabeled data point represents, typically by adding a background grid of reference lines.

**Use cases:**
- Enabling side-by-side comparison of multiple plots, enhancing visual analysis.
- Enhancing presentation clarity by organizing complex information systematically.

### 6.7 Histogram

A histogram visually displays the distribution of a dataset by dividing the range of values into "bins" and representing the frequency (count) of observations in each bin using bars.

**Use cases:**
- Visualizing the distribution of numerical data, such as income levels or exam scores.
- Making inferences about data characteristics and underlying patterns, which helps guide decision-making.

### 6.8 Pie Chart

Pie charts are circular graphs in which data is represented as slices ("segments") of the pie, where each slice's size is proportional to the quantity it represents.

**Use cases:**
- Showing the proportions of a whole, such as market share or survey responses (the slide example shows programming language popularity: Python 30.7%, Java 26.5%, C++ 26.3%, Ruby 16.3%).
- Simplifying complex data by representing it in an easily understandable, at-a-glance format.

### Choosing the Right Plot — Cheat Sheet

| Goal | Best Plot Type(s) |
|---|---|
| Show a trend over time | Line plot |
| Highlight individual/discrete observations or events | Marker plot |
| Show relationship/correlation between two variables | Scatter plot |
| Show cumulative totals or part-to-whole change over time | Area plot |
| Compare discrete categories | Bar plot |
| Compare multiple plots side by side / add reference lines | Grid plot |
| Show the distribution/spread of a numeric variable | Histogram |
| Show proportions of a whole at a single point in time | Pie chart |

---

## 7. Key Takeaways

- **Data science** involves the analysis and interpretation of data to generate actionable insights — it's not just about algorithms, but about turning raw information into decisions.
- **NumPy** (Numerical Python) is an open-source library predominantly used when working with arrays and performing fast numerical computation.
- **Seaborn** is a data visualization library in Python that is built on top of Matplotlib, offering more attractive defaults and simpler syntax for statistical plots.
- **Python** is the preferred programming language for data science projects across industries, thanks to its simplicity, scalability, and vast ecosystem of libraries.

---

## 📝 Practice Questions

### Multiple Choice

**Q1.** Which of the following best defines data science?
- **A.** A programming language used exclusively for web development
- **B.** A multidisciplinary field that uses scientific methods, processes, algorithms, and systems to derive insights from data
- **C.** A type of database management system
- **D.** A hardware architecture for parallel computing

**Q2.** Which THREE disciplines combine to form data science, according to the lesson?
- **A.** Marketing, sales, and finance
- **B.** Domain expertise/scientific methods, mathematical/statistical models, and technology
- **C.** Biology, chemistry, and physics
- **D.** Design, UX research, and product management

**Q3.** In the healthcare wearable-device example, what is the correct order of the data flow?
- **A.** Engagement dashboard → IoT gateway → Wearable device → Servers
- **B.** Wearable device → IoT gateway → Data transfer to servers → Enterprise infrastructure → Data analytics → Engagement dashboard
- **C.** Data analytics → Wearable device → Dashboard → Servers
- **D.** Servers → Wearable device → IoT gateway → Dashboard

**Q4.** Which step of the data science process comes immediately BEFORE "Model building and training"?
- **A.** Model deployment
- **B.** Problem definition
- **C.** Feature engineering
- **D.** Model evaluation

**Q5.** What is the primary purpose of the "data cleaning and exploration" step?
- **A.** To increase the size of the dataset
- **B.** To reduce the amount of data required for the model
- **C.** To handle missing values and outliers and to gain insight into patterns in the data
- **D.** To deploy the model into production

**Q6.** Which Python library is specifically described as being "built on top of Matplotlib"?
- **A.** NumPy
- **B.** Pandas
- **C.** Seaborn
- **D.** SciPy

**Q7.** A financial analyst wants to calculate the mean return and volatility of a set of stocks for quantitative analysis. Which library is most directly suited to this task?
- **A.** Plotly
- **B.** NumPy
- **C.** Scikit-learn
- **D.** Seaborn

**Q8.** Which library would you choose specifically for building a machine learning model to detect fraudulent transactions?
- **A.** Matplotlib
- **B.** Statsmodels
- **C.** Scikit-learn
- **D.** SciPy

**Q9.** Which plot type is best suited to show cumulative sales revenue growing across four successive quarters?
- **A.** Pie chart
- **B.** Scatter plot
- **C.** Area plot
- **D.** Histogram

**Q10.** Which of the following is NOT listed in the lesson as an advantage of Python for data science?
- **A.** Ease of use and simple syntax
- **B.** Compatibility with all major operating systems
- **C.** Requiring a paid license for commercial use
- **D.** A wide variety of data science libraries and packages

**Q11.** Which plot type divides a dataset's values into bins and shows the frequency of observations in each bin?
- **A.** Line plot
- **B.** Histogram
- **C.** Bar plot
- **D.** Grid plot

**Q12.** According to the lesson, why is data cleaning and preparation important in the data science process?
- **A.** To decrease the accuracy of the model
- **B.** To increase the size of the dataset
- **C.** To ensure greater accuracy while building the model
- **D.** To reduce the number of features available

### Short Answer

**Q13.** Name the seven steps of the data science process in order.

**Q14.** Explain, in your own words, the difference between a scatter plot and a line plot, and give one scenario where you would prefer one over the other.

**Q15.** Why is Python often preferred over R for data science projects, according to this lesson?

**Q16.** Give one real-world example (not from the slides) of how a company might use the "capture → process → decide" pattern described in the finance/loan example from this lesson.

---

### Answers

**A1. B** — Data science is defined precisely as a multidisciplinary field using scientific methods, processes, algorithms, and systems to derive insights from structured and unstructured data.

**A2. B** — The lesson describes data science as emerging from the combination of domain expertise/scientific methodologies, mathematical and statistical models, and technology (tools, languages, infrastructure).

**A3. B** — The correct pipeline is Wearable device → Biometric data transfer → IoT gateway → Data transfer to servers → Enterprise infrastructure → Data analytics → Engagement dashboard → Informed decision-making.

**A4. C** — The 7-step process is: Problem definition → Data collection → Data cleaning and exploration → Feature engineering → Model building and training → Model evaluation → Model deployment. Feature engineering directly precedes model building and training.

**A5. C** — Data cleaning and exploration is about preprocessing the data (handling missing values, outliers, inconsistencies) and exploring it to identify patterns, which is what enables greater model accuracy later on.

**A6. C** — Seaborn is explicitly described as "a data visualization library in Python that is built on top of Matplotlib," offering a higher-level, more attractive interface for statistical graphics.

**A7. B** — NumPy is the library called out in the lesson for exactly this use case: financial analysts use it for quantitative analysis such as calculating mean return and volatility of stocks.

**A8. C** — Scikit-learn is the machine learning library highlighted for tasks like detecting fraudulent transactions in banking and e-commerce platforms.

**A9. C** — Area plots are designed to show cumulative totals or proportions over time, such as tracking total sales revenue across successive quarters — this matches the exact example given in the lesson.

**A10. C** — Python is open-source and free; requiring a paid commercial license is not one of its advantages and directly contradicts the "open-source" advantage listed in the lesson.

**A11. B** — A histogram divides a dataset's range of values into bins and shows the frequency of observations that fall into each bin, which is exactly how the lesson defines it.

**A12. C** — The lesson states data cleaning and preparation are important specifically to ensure greater accuracy while building the model — messy or inconsistent data leads to unreliable models.

**A13.** Problem definition → Data collection → Data cleaning and exploration → Feature engineering → Model building and training → Model evaluation → Model deployment. Each step builds on the previous one, and in practice the process is often iterative rather than strictly linear.

**A14.** A line plot connects data points with straight lines and is best for showing a continuous trend over an ordered variable like time (e.g., stock price over a year). A scatter plot shows individual, unconnected points along two axes and is best for examining the relationship or correlation between two variables where there is no inherent ordering (e.g., height vs. weight). You'd choose a line plot for time-series trend analysis, and a scatter plot to check whether two variables are correlated.

**A15.** According to the lesson, Python is preferred over R mainly because of its scalability, its ease of use and simple syntax, its wide variety of available libraries, its compatibility across operating systems, and the fact that new data science libraries are created daily by a large, active community — R is comparatively more narrowly focused on statistical use cases and considered less scalable.

**A16.** Answers will vary, but a strong answer should describe: (1) a data-capture point (e.g., a customer submitting an insurance claim online), (2) data transfer to backend/enterprise infrastructure, (3) analytics applied to that data (e.g., fraud-risk scoring), and (4) a dashboard or output that helps a human (e.g., a claims adjuster) make a faster, more informed decision — mirroring the loan-application example in the lesson.
