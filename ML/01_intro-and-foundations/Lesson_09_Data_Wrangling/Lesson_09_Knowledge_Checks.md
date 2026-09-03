# Lesson 09: Data Wrangling — Knowledge Check

## Concept Primer

**Data wrangling** (also called data munging) is the process of cleaning, structuring, and transforming raw, messy data into a form that is suitable for analysis or modeling. It sits between raw data collection and exploratory data analysis / machine learning, and typically includes tasks such as handling missing values, removing duplicates, fixing inconsistent formats, converting data types, merging datasets, and treating outliers. The goal is not to analyze or visualize the data itself, but to make it *analysis-ready* — poor wrangling leads to biased, misleading, or outright broken downstream results ("garbage in, garbage out").

**Handling missing and duplicate data.** Missing values commonly appear as `NaN`, empty strings, or placeholder codes (e.g., `-999`). In Pandas, `isnull()`/`isna()` detect them, `dropna()` removes rows/columns containing them, and `fillna()` imputes them (with a constant, mean/median/mode, or a forward/backward fill via `ffill()`/`bfill()`). The right strategy depends on *why* data is missing and how much of it is missing — dropping is safe when missingness is small and random, while imputation preserves sample size but can introduce bias if done carelessly. Duplicate records are detected with `duplicated()` and removed with `drop_duplicates()`; duplicates often arise from repeated data entry, merges, or scraping, and left unchecked they silently inflate counts and skew statistics.

**Merging and combining datasets.** Real-world data is rarely in one table. Pandas provides three core combination tools: `pd.merge()` performs SQL-style joins (inner, left, right, outer) on one or more key columns, matching rows where key values align; `pd.concat()` stacks DataFrames along an axis (rows or columns) without needing a matching key, useful for appending similar datasets; and `.join()` is a convenience method for combining DataFrames on their index. Choosing the wrong join type (e.g., inner vs. outer) is a common source of silently dropped rows.

**Data type conversion.** Columns loaded from CSV or Excel often have incorrect types — numbers stored as strings, dates stored as generic objects, categorical labels stored as free text. `astype()` casts a column to a specified type (e.g., `int`, `float`, `category`), while `pd.to_datetime()` and `pd.to_numeric()` handle more robust, error-tolerant conversions (e.g., via the `errors='coerce'` parameter, which turns unparseable values into `NaN` instead of raising). Correct typing matters because arithmetic, sorting, filtering, and grouping all behave differently on strings versus numbers versus dates.

**Outlier detection and treatment.** Outliers are values that deviate markedly from the rest of the data and can distort means, standard deviations, and model fits. Common detection techniques include the Z-score method (flagging points beyond ~2–3 standard deviations from the mean) and the IQR method (flagging points below Q1 − 1.5×IQR or above Q3 + 1.5×IQR), often visualized with a box plot. Treatment options include removing the outlier, capping/winsorizing it to a boundary value, transforming the variable (e.g., log transform), or leaving it if it reflects a genuine, meaningful extreme rather than an error — the decision should always be driven by domain knowledge, not just statistics.

**Loading and inspecting data in Pandas.** Before any wrangling can happen, data must be loaded into a DataFrame — most commonly with `pd.read_csv()` for CSV files, alongside siblings like `pd.read_excel()` and `pd.read_json()`. Immediately after loading, analysts typically inspect the data with `.head()`, `.info()`, `.describe()`, and `.shape` to understand column types, size, and obvious data-quality issues before deciding on a wrangling strategy.

---

## Original Questions

**1. What is the primary purpose of data wrangling in the data preparation pipeline?**

- A. To analyze the data
- B. To clean, structure, and transform data for analysis
- C. To visualize data
- D. To store data in databases

**2. Which method is used to load data into a Pandas DataFrame from a CSV file?**

- A. `pd.load_csv()`
- B. `pd.read_csv()`
- C. `pd.open_csv()`
- D. `pd.import_csv()`

**3. Which method is typically used to combine two DataFrames based on a common column?**

- A. `pd.combine()`
- B. `pd.merge()`
- C. `pd.join()`
- D. `pd.concat()`

---

## Answers

**1. Answer: B — To clean, structure, and transform data for analysis**
Data wrangling is specifically the process of cleaning, structuring, and transforming raw data so that it becomes suitable for downstream analysis. Analyzing (A) and visualizing (C) the data are later pipeline steps, and storing data in databases (D) is a data engineering/persistence concern, not wrangling itself.

**2. Answer: B — `pd.read_csv()`**
`pd.read_csv()` is the standard Pandas function for reading a CSV file into a DataFrame. The other options (`load_csv`, `open_csv`, `import_csv`) are not real Pandas functions.

**3. Answer: B — `pd.merge()`**
`pd.merge()` combines two DataFrames based on one or more shared key columns, similar to a SQL join. `pd.concat()` (D) stacks DataFrames along an axis without requiring a matching key, and `pd.combine()` / `pd.join()` in the options given are either not the primary merge tool (`.join()` exists but merges on index, not an arbitrary common column) or not a real Pandas top-level function (`pd.combine()`).

---

## 📝 Additional Practice Questions

**4.** Which Pandas method removes duplicate rows from a DataFrame?
- A. `remove_duplicates()`
- B. `drop_duplicates()`
- C. `dedupe()`
- D. `clean_duplicates()`

**5.** What does `df.fillna(df.mean())` do to a numeric column with missing values?
- A. Drops all rows containing missing values
- B. Replaces missing values with the column's mean
- C. Replaces missing values with zero
- D. Raises an error because means cannot be computed with NaNs present

**6.** Which join type in `pd.merge()` keeps only the rows whose key values appear in *both* DataFrames?
- A. Left join
- B. Right join
- C. Inner join
- D. Outer join

**7.** A column of purchase amounts is loaded from CSV as text strings (e.g., `"$1,200.50"`). Which general approach correctly converts it to a usable numeric type?
- A. Call `astype(int)` directly on the raw string column
- B. Strip out the `$` and `,` characters, then convert with `pd.to_numeric()` or `astype(float)`
- C. Leave it as a string since Pandas can do arithmetic on strings automatically
- D. Use `pd.to_datetime()` on the column

**8.** Which statistical method commonly flags a data point as an outlier if it falls below Q1 − 1.5×IQR or above Q3 + 1.5×IQR?
- A. Z-score method
- B. Linear regression method
- C. IQR (interquartile range) method
- D. Chi-square test

**9. (Short answer)** Explain the difference between `pd.concat()` and `pd.merge()`, and give one scenario where you would use each.

**10. (Short answer)** Why might dropping every row with a missing value (`dropna()`) be a poor strategy for a dataset where 40% of rows have at least one missing value in a low-priority column? What would you do instead?

**11.** Which Pandas function converts a column of date strings into proper `datetime` objects?
- A. `pd.to_numeric()`
- B. `pd.to_datetime()`
- C. `pd.to_string()`
- D. `df.astype('date')`

**12. (Short answer)** You merge two customer DataFrames on a `customer_id` column using an outer join and notice many new rows with `NaN` values in columns that came from one of the two original tables. What does this indicate, and is it necessarily an error?

### Answers

**4. Answer: B — `drop_duplicates()`**
`drop_duplicates()` is the built-in Pandas method for removing duplicate rows (optionally based on a subset of columns). The other names are not real Pandas methods.

**5. Answer: B — Replaces missing values with the column's mean**
`fillna()` imputes missing (`NaN`) values with whatever is passed to it — here, the column's mean, computed via `df.mean()`. Pandas' `mean()` automatically skips existing `NaN` values by default, so no error is raised (contrary to option D).

**6. Answer: C — Inner join**
An inner join keeps only rows where the key exists in both DataFrames, discarding unmatched rows from either side. Left/right joins keep all rows from one side and matching rows from the other (filling unmatched with `NaN`), and an outer join keeps all rows from both sides.

**7. Answer: B — Strip out the `$` and `,` characters, then convert with `pd.to_numeric()` or `astype(float)`**
Currency-formatted strings contain non-numeric characters that must be removed (e.g., with `.str.replace()`) before type conversion; calling `astype(int)` or `astype(float)` directly on a string like `"$1,200.50"` raises a `ValueError`. Pandas does not do implicit numeric arithmetic on strings (ruling out C), and `pd.to_datetime()` (D) is for dates, not currency.

**8. Answer: C — IQR (interquartile range) method**
The 1.5×IQR rule is the classic Tukey method for flagging outliers based on the spread between the 25th and 75th percentiles. The Z-score method (A) instead uses standard deviations from the mean, and B/D are unrelated statistical techniques.

**9. Answer (short answer):**
`pd.concat()` stacks DataFrames along an axis (rows or columns) without needing a shared key — useful when appending multiple monthly sales files with identical columns into one long DataFrame. `pd.merge()` combines DataFrames based on matching values in one or more key columns, similar to a SQL join — useful when combining a `customers` table and an `orders` table via a shared `customer_id` column.

**10. Answer (short answer):**
Dropping all rows with any missing value can discard a large, potentially non-random chunk of the dataset (40% here), reducing statistical power and possibly introducing bias if the missingness correlates with other variables. Since the missing values are in a low-priority column, a better approach is to either impute the missing values (mean/median/mode, or a model-based imputation) or simply drop/ignore that specific low-priority column rather than the entire row, preserving the rest of the data.

**11. Answer: B — `pd.to_datetime()`**
`pd.to_datetime()` parses a variety of date/time string formats into proper `datetime64` objects, enabling date arithmetic, sorting, and time-based filtering. `pd.to_numeric()` (A) is for numbers, and C/D are not valid Pandas conversion calls in this form.

**12. Answer (short answer):**
The `NaN` values indicate that those `customer_id` keys existed in only one of the two DataFrames — an outer join keeps every key from both sides and fills in `NaN` wherever a match wasn't found on the other side. This is not necessarily an error; it may simply reflect real-world facts (e.g., a customer who has an account but has not yet placed an order). Whether it's a problem depends on the business logic — it becomes worth investigating only if those NaNs are unexpected given what the two tables are supposed to represent.
