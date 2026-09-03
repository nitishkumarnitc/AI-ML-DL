# Lesson 03 – NumPy: Knowledge Check

## Concept Primer

NumPy (Numerical Python) is the foundational library for numerical and scientific computing in Python. Unlike native Python lists, which store elements as generic, individually-boxed Python objects, NumPy provides the `ndarray` (N-dimensional array) — a fixed-type, contiguous block of memory that lets Python code perform bulk mathematical operations at speeds close to C. This is why NumPy underpins nearly every major data science, machine learning, and scientific library in the Python ecosystem (pandas, scikit-learn, TensorFlow, PyTorch, SciPy, and others all build on it).

At the core of NumPy is the `ndarray` object, which is described by a small set of key attributes: `ndim` (the number of dimensions/axes), `shape` (a tuple giving the size along each dimension), `size` (the total number of elements), `dtype` (the data type of the elements, e.g., `int64`, `float32`), and `itemsize` (the number of bytes each element occupies in memory). Together these attributes let you reason about an array's structure and memory footprint without inspecting every value. Note that `data` and `index` are *not* standard ndarray attributes in this sense — `data` is a low-level buffer object rarely used directly, and `index` is a pandas concept, not a NumPy one.

Reshaping is one of the most common array manipulations. `ndarray.reshape(new_shape)` returns a new view (when possible) of the same data organized into a different shape, as long as the total number of elements stays the same (e.g., reshaping a 12-element 1D array into a 3×4 2D array). This is distinct from `ndarray.transpose()`, which permutes (swaps) the axes of an array without changing the number of elements per axis in the way reshape does, and from `ndarray.flatten()`, which collapses a multi-dimensional array down to one dimension (the "inverse" of a general reshape). Because reshape does not create new data, it is efficient — it just changes how the existing data is interpreted.

Beyond structure, NumPy arrays are strongly typed via `dtype`. Every element in an array shares the same data type, which is what allows NumPy to store data compactly and operate on it with vectorized, loop-free operations (arithmetic, statistical functions, comparisons, etc.) implemented in optimized C code. This vectorization — applying an operation to an entire array at once instead of writing an explicit Python `for` loop — is the single biggest reason NumPy code is both faster and more concise than equivalent pure-Python code.

Finally, NumPy supports powerful indexing, slicing, and broadcasting mechanics. Indexing/slicing lets you extract sub-arrays or individual elements using the familiar `array[start:stop:step]` syntax (extended across multiple axes with commas, e.g., `array[1:3, 0:2]`). Broadcasting lets NumPy perform arithmetic between arrays of different (but compatible) shapes by "stretching" the smaller array without actually copying data, which is what makes it possible to, say, add a single scalar to every element of a 2D array, or add a 1D row to every row of a 2D matrix.

---

## Original Knowledge Check Questions

### Question 1

**What is NumPy and what is it used for?**

- **A.** NumPy is used for building dynamic websites.
- **B.** NumPy is used to perform mathematical operations in science and engineering applications.
- **C.** NumPy is used for image and speech recognition.
- **D.** NumPy is used for building mobile applications.

### Question 2

**What are the key attributes of ndarray?**

- **A.** ndim, shape, size, dtype, itemsize
- **B.** ndim, shape, dtype, data, index
- **C.** ndim, size, dtype, itemsize, data
- **D.** ndim, index, dtype, itemsize, shape

### Question 3

**Which of the following is used to change the dimension of an array?**

- **A.** ndarray.reshape
- **B.** ndarray.transpose
- **C.** ndarray.data
- **D.** ndarray.flatten

---

## Answers (Original Questions)

**1. Answer: B — NumPy is used to perform mathematical operations in science and engineering applications.**
NumPy's core purpose is efficient numerical computation (arrays, linear algebra, statistics), which is why it's the backbone of scientific and engineering software rather than web development, image/speech recognition apps, or mobile app frameworks (those rely on other specialized libraries, even if some may use NumPy internally).

**2. Answer: A — ndim, shape, size, dtype, itemsize.**
These five attributes fully describe an ndarray's structure: number of axes, shape along each axis, total element count, element data type, and bytes per element. `data` (raw buffer) and `index` (a pandas, not NumPy, concept) are not part of this standard attribute set.

**3. Answer: A — ndarray.reshape.**
`reshape()` changes an array's shape/dimensionality while preserving the total number of elements and the underlying data. `transpose()` swaps axes rather than changing dimensionality in the same sense, `flatten()` only collapses to 1D, and `data` is just a buffer reference, not a reshaping tool.

---

## 📝 Additional Practice Questions

**Q4 (Multiple Choice).** Which function is the standard way to create a NumPy array from a Python list?
- **A.** `numpy.array()`
- **B.** `numpy.list()`
- **C.** `numpy.create()`
- **D.** `numpy.vector()`

**Q5 (Multiple Choice).** What does broadcasting allow NumPy to do?
- **A.** Convert arrays to Python lists automatically
- **B.** Perform arithmetic operations between arrays of different but compatible shapes without explicit loops
- **C.** Automatically remove duplicate elements from an array
- **D.** Sort an array in ascending order by default

**Q6 (Multiple Choice).** Given `a = np.arange(10)`, what does `a[2:7:2]` return?
- **A.** `[2, 3, 4, 5, 6]`
- **B.** `[2, 4, 6]`
- **C.** `[3, 5, 7]`
- **D.** `[2, 4, 6, 8]`

**Q7 (Short Answer).** What is the difference between a "view" and a "copy" when slicing a NumPy array?

**Q8 (Multiple Choice).** Which NumPy function computes the mean of all elements in an array?
- **A.** `np.total()`
- **B.** `np.mean()`
- **C.** `np.average_value()`
- **D.** `np.center()`

**Q9 (Short Answer).** Why are NumPy arrays generally faster than Python lists for numerical computation?

**Q10 (Multiple Choice).** If `arr.shape` is `(4, 3)`, which reshape call is valid?
- **A.** `arr.reshape(3, 4)`
- **B.** `arr.reshape(2, 5)`
- **C.** `arr.reshape(6, 3)`
- **D.** `arr.reshape(12, 2)`

**Q11 (Multiple Choice).** Which of the following correctly creates a 3x3 array of all zeros?
- **A.** `np.zeros(3, 3)`
- **B.** `np.zeros((3, 3))`
- **C.** `np.zero((3, 3))`
- **D.** `np.empty(3, 3)`

**Q12 (Short Answer).** What does `dtype` control in a NumPy array, and why does keeping a single dtype per array matter for performance?

**Q13 (Multiple Choice).** Which aggregation function would you use to find the largest value along a specific axis of a 2D array?
- **A.** `np.max(arr, axis=0)` or `np.max(arr, axis=1)`
- **B.** `np.top(arr)`
- **C.** `np.biggest(arr)`
- **D.** `np.peak(arr, axis=None)`

**Q14 (Short Answer).** Given `a = np.array([1, 2, 3])` and `b = np.array([[10], [20], [30]])`, explain what shape the result of `a + b` will have and why.

---

### Answers

**4. Answer: A — `numpy.array()`.**
`numpy.array()` (commonly imported as `np.array()`) is the standard constructor that converts Python lists, tuples, or nested sequences into an `ndarray`. There is no built-in `numpy.list()`, `numpy.create()`, or `numpy.vector()` function.

**5. Answer: B — Perform arithmetic operations between arrays of different but compatible shapes without explicit loops.**
Broadcasting is NumPy's rule set for implicitly expanding smaller arrays (e.g., a scalar or a 1D array) so they align with a larger array's shape during element-wise operations, avoiding manual loops and unnecessary memory copies.

**6. Answer: B — `[2, 4, 6]`.**
Slice syntax is `[start:stop:step]`. Starting at index 2, stopping before index 7, and stepping by 2 gives indices 2, 4, 6 → values 2, 4, 6 (since `a = np.arange(10)` produces `[0,1,2,...,9]`, and values equal their indices here).

**7. Answer: A slice of a NumPy array returns a *view* — it shares the same underlying memory buffer as the original array, so modifying the view also modifies the original array. A *copy* (e.g., via `.copy()` or certain indexing operations like boolean/fancy indexing) allocates new memory, so changes to the copy do not affect the original.**
This distinction matters because relying on a view when you intended an independent copy (or vice versa) is a common source of subtle bugs.

**8. Answer: B — `np.mean()`.**
`np.mean()` computes the arithmetic average of array elements (optionally along a specified axis). The other function names are not part of NumPy's API.

**9. Answer: NumPy arrays store elements of a single, fixed data type in a contiguous block of memory, and its operations are implemented as vectorized routines in compiled C code. This avoids the overhead of Python's per-element type checking and interpreter loop overhead that occurs with native Python lists, resulting in significantly faster execution for numerical workloads.**

**10. Answer: A — `arr.reshape(3, 4)`.**
The original array has 4 × 3 = 12 elements. A valid reshape must preserve the total element count: 3 × 4 = 12 works. 2 × 5 = 10, 6 × 3 = 18, and 12 × 2 = 24 do not match 12, so they would raise a `ValueError`.

**11. Answer: B — `np.zeros((3, 3))`.**
`np.zeros()` requires the shape to be passed as a single tuple argument, e.g., `(3, 3)`, not as separate positional arguments. `np.zero` (singular) does not exist, and `np.empty(3, 3)` has the same tuple-argument issue plus doesn't guarantee zero-initialized values.

**12. Answer: `dtype` specifies the data type of every element in the array (e.g., `int32`, `float64`, `bool`). Because all elements share one dtype, NumPy knows the exact, fixed number of bytes per element ahead of time, letting it store data in one uniform contiguous block and run vectorized C-level operations efficiently — mixed types (as in a Python list) would prevent this optimization.**

**13. Answer: A — `np.max(arr, axis=0)` or `np.max(arr, axis=1)`.**
`np.max()` (or the equivalent `arr.max()` method) with an `axis` argument reduces along the specified axis (0 = down columns, 1 = across rows) to find the maximum value(s). The other function names do not exist in NumPy.

**14. Answer: The result has shape `(3, 3)`. `a` has shape `(3,)` and `b` has shape `(3, 1)`. Broadcasting aligns shapes from the trailing dimension: `a`'s shape is treated as `(1, 3)`, which is compatible with `b`'s `(3, 1)` — each dimension is either equal or one of them is 1. NumPy "stretches" both arrays virtually to shape `(3, 3)` and adds them element-wise, producing a 3x3 matrix where each row of `b` is added to all of `a`.**

