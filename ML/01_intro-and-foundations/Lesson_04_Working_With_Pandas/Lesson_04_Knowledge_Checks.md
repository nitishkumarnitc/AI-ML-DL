# Lesson 04: Working with Pandas — Knowledge Check

## Concept Primer

Pandas represents tabular data with two core structures: the **Series** (a single labeled 1‑D array) and the **DataFrame** (a 2‑D table made up of aligned Series, one per column). Every axis — rows and columns — carries an *index*, which is what lets Pandas align, filter, and combine data intelligently instead of relying on raw positional order. Understanding that a DataFrame is fundamentally a dictionary-like collection of columns, each with its own dtype, explains why column access, row access, and whole-table summaries each have their own dedicated syntax.

**Accessing columns and rows** is one of the most common sources of confusion for beginners. A single column is retrieved with bracket notation and the column name as a string (`df['Age']`) or, when the name is a valid Python identifier, via attribute access (`df.Age`). Parentheses (`df('Age')`) never work because `df` is not callable, and `df[0]` only works if `0` happens to be a column label — otherwise it raises a `KeyError`. For label-based row/column selection Pandas provides `.loc[]`, and for purely integer-position-based selection it provides `.iloc[]`; mixing the two mental models (e.g., using `.loc` with integer positions on a non-integer index) is a classic bug source.

**Descriptive statistics and inspection** are handled by a small set of purpose-built methods rather than one universal function. `df.describe()` computes count, mean, std, min, quartiles, and max for numeric columns (and counts/unique/top/freq for object columns when explicitly requested). `df.info()` instead reports structural metadata — dtypes, non-null counts, and memory usage — which is a different concern from statistical summaries. Methods like `df.statistics()` or `df.summary()` do not exist in Pandas; recognizing which real method maps to which concept (structure vs. statistics) is exactly what this quiz is testing.

**Datetime handling** in Pandas revolves around the `.dt` accessor. Once a column or Series is converted to a proper `datetime64` dtype (commonly via `pd.to_datetime()`), the `.dt` accessor exposes component properties such as `.dt.year`, `.dt.month`, `.dt.day`, `.dt.dayofweek`, and methods like `.dt.strftime()`. This mirrors the `.str` accessor used for vectorized string operations — both are namespaces that unlock type-specific operations on an otherwise generic Series. Calling `.year()` directly on a Series, or wrapping the Series in a bare `year()` function, fails because those are not Series methods or built-ins.

**Combining and reshaping data** — via `merge()`, `join()`, `concat()`, and `groupby()` — builds on the same indexing and alignment principles. `merge()` performs SQL-style joins on key columns, `groupby()` splits data into groups, applies an aggregation, and combines the results ("split-apply-combine"), and functions like `.apply()` and `.map()` let you push custom row-wise, column-wise, or element-wise logic through a Series or DataFrame. Missing data (`NaN`) is a first-class concept throughout Pandas, with dedicated tools (`isna()`, `dropna()`, `fillna()`) rather than ad hoc `None`/`null` checks, because Pandas needs a consistent way to represent "no value" across many numeric and non-numeric dtypes.

## Original Knowledge Check Questions

**1. How can you access the column 'Age' in a Pandas DataFrame named 'df'?**

- **A.** `df('Age')`
- **B.** `df[0]`
- **C.** `df['Age']`
- **D.** `df.Age()`

**2. Which Pandas function is used to obtain a summary of descriptive statistics for a DataFrame named df?**

- **A.** `df.describe()`
- **B.** `df.statistics()`
- **C.** `df.summary()`
- **D.** `df.info()`

**3. How is the year extracted from a Pandas Series `date_series` containing datetime objects?**

- **A.** `date_series.year()`
- **B.** `date_series.get('year')`
- **C.** `date_series.dt.year`
- **D.** `year(date_series)`

## Answers

**1. Correct answer: C — `df['Age']`**
In Pandas, DataFrame columns can be accessed using square-bracket notation with the column name passed as a string. `df('Age')` fails because a DataFrame isn't callable, `df[0]` would only work if `0` were itself a column label, and `df.Age()` incorrectly treats the attribute-style column access as a method call.

**2. Correct answer: A — `df.describe()`**
The `describe()` method returns a summary of descriptive statistics — including count, mean, standard deviation, min/max, and quartiles — for the numeric columns of a DataFrame. `statistics()` and `summary()` are not real Pandas methods, and `info()` reports structural metadata (dtypes, non-null counts) rather than statistical measures.

**3. Correct answer: C — `date_series.dt.year`**
Pandas exposes datetime component properties through the `.dt` accessor on a Series with datetime64 dtype; `.dt.year` returns the year of each element. `.year()` and `year(date_series)` aren't valid because `year` isn't a callable method or built-in function, and `.get('year')` is dictionary-style access that doesn't apply here.

## 📝 Additional Practice Questions

**4. (Multiple choice) Which of the following correctly selects the row with integer position 2 (the third row) from a DataFrame `df`, regardless of what its index labels are?**

- **A.** `df.loc[2]`
- **B.** `df.iloc[2]`
- **C.** `df.at[2]`
- **D.** `df[2]`

**5. (Multiple choice) What does `df.groupby('department')['salary'].mean()` compute?**

- **A.** The overall average salary across the entire DataFrame
- **B.** The average salary for each unique value in the `department` column
- **C.** A new DataFrame with one row per employee and a `mean` column appended
- **D.** An error, because `groupby` requires two arguments

**6. (Short answer) Explain the difference between `df.loc[]` and `df.iloc[]` for selecting rows and columns.**

**7. (Multiple choice) Which method would you use to combine two DataFrames `orders` and `customers` on a shared column `customer_id`, similar to a SQL join?**

- **A.** `pd.concat([orders, customers])`
- **B.** `orders.append(customers)`
- **C.** `pd.merge(orders, customers, on='customer_id')`
- **D.** `orders.join(customers, axis=1)`

**8. (Short answer) What is the difference between `df.dropna()` and `df.fillna(0)`? When might you prefer one over the other?**

**9. (Multiple choice) Given `s = pd.Series([1, 2, 3])`, what does `s.apply(lambda x: x ** 2)` return?**

- **A.** `9` (the square of the last element)
- **B.** A Series: `[1, 4, 9]`
- **C.** A single scalar sum: `14`
- **D.** A `TypeError`, because `apply` only works on DataFrames

**10. (Multiple choice) Which statement about `df.map()` versus `df.applymap()` (or `DataFrame.apply`) is correct?**

- **A.** `.map()` is a Series method for element-wise substitution/transformation; applying a function to every element of a whole DataFrame is typically done with `.apply(..., axis=None)`-style helpers or (historically) `.applymap()`
- **B.** `.map()` and `.apply()` are exactly interchangeable on both Series and DataFrames with no differences
- **C.** `.map()` only works on numeric dtypes
- **D.** `.applymap()` operates on whole rows only, never on individual cells

**11. (Short answer) You have `df['price']` with dtype `object` because some values are strings like `"$19.99"`. Describe the steps you'd take to convert this column to a proper numeric (float) dtype.**

**12. (Multiple choice) What does `pd.isna(df).sum()` return?**

- **A.** The total number of rows in `df`
- **B.** A Series showing, for each column, the count of missing (NaN) values
- **C.** A single boolean indicating whether any value anywhere is missing
- **D.** A DataFrame with all missing values replaced by 0

### Answers

**4. Correct answer: B — `df.iloc[2]`**
`.iloc` is purely position-based (like a Python list index), so `df.iloc[2]` always returns the third row by position. `.loc[2]` would look for a row whose *label* is `2`, which may not exist or may not be the third row if the index isn't the default RangeIndex; `.at[2]` is a fast scalar accessor requiring both row and column labels, and `df[2]` on a DataFrame targets columns, not rows, and would raise a `KeyError` unless `2` is a column name.

**5. Correct answer: B — the average salary for each unique department**
`groupby('department')` splits the DataFrame into groups sharing the same department value; selecting `['salary']` and calling `.mean()` applies the aggregation within each group, following Pandas' "split-apply-combine" pattern. It does not collapse everything into one overall average (that would be `df['salary'].mean()` without grouping), and it returns a Series indexed by department, not a per-row column.

**6. Explanation:** `.loc[]` is **label-based** — you select rows/columns using their index labels or column names (and it's inclusive of both endpoints in slices). `.iloc[]` is **position-based** — you select using integer positions (0-based), similar to list indexing, and slices exclude the endpoint like standard Python slicing. Use `.loc` when you know the label you want (e.g., a date or a named column); use `.iloc` when you want "the Nth row/column" regardless of what its label is.

**7. Correct answer: C — `pd.merge(orders, customers, on='customer_id')`**
`merge()` is Pandas' SQL-style join operation, matching rows between two DataFrames based on one or more key columns (here `customer_id`). `pd.concat()` stacks DataFrames along an axis without matching on keys, `.append()` is a deprecated row-stacking convenience (also not key-based), and `.join()` combines on the *index* by default, not on an arbitrary shared column, unless that column is first set as the index.

**8. Explanation:** `df.dropna()` **removes** any row (by default) that contains at least one missing value, shrinking the DataFrame — useful when missing rows are rare and you can afford to lose them, or when imputing would introduce bias. `df.fillna(0)` **replaces** missing values with a specified value (here `0`) while keeping every row, which is preferable when dropping rows would lose too much data or when a sensible default/imputed value exists (e.g., filling missing counts with 0, or using `.fillna(df.mean())` for a numeric average).

**9. Correct answer: B — a Series: `[1, 4, 9]`**
`Series.apply()` applies the given function element-wise to every value in the Series and returns a new Series of the same length with the transformed values. It does not reduce the Series to a single scalar (that would be an aggregation like `.sum()`), and `apply` works on Series as well as DataFrames.

**10. Correct answer: A**
`Series.map()` performs element-wise mapping/substitution (often via a dict, function, or another Series) on a single column. Whole-DataFrame element-wise transformation is conceptually different from row/column-wise `DataFrame.apply()`; historically Pandas offered `.applymap()` for this cell-by-cell case (now commonly superseded by `.apply(func)` combined with appropriate broadcasting in modern Pandas, but the "map = elementwise on a Series" vs. "apply = operates along an axis" distinction remains the key idea being tested). `.map()` is not restricted to numeric dtypes, and `.applymap()`-style operations work on individual cells, not just whole rows.

**11. Explanation:** A typical approach: (1) strip non-numeric characters, e.g. `df['price'] = df['price'].str.replace('$', '', regex=False).str.replace(',', '', regex=False)`; (2) convert the cleaned strings to numeric with `pd.to_numeric(df['price'], errors='coerce')`, where `errors='coerce'` turns any value that still can't be parsed into `NaN` instead of raising; (3) optionally handle the resulting `NaN`s with `dropna()` or `fillna()`; (4) confirm the dtype changed via `df['price'].dtype` or `df.info()`.

**12. Correct answer: B — a Series showing, per column, the count of missing values**
`pd.isna(df)` produces a same-shaped DataFrame of booleans marking which cells are missing; `.sum()` on that boolean DataFrame sums down each column (since `True` counts as 1), yielding a Series with one missing-value count per column. It does not report total row count, collapse to a single boolean, or modify the original data.
