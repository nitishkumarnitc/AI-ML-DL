# Lesson 6: Unsupervised Learning Algorithms — Knowledge Checks

## Concept Primer

**Unsupervised learning** works with data that has no labeled target variable. Instead of predicting a known output, the algorithm looks for structure — groups, patterns, or lower-dimensional representations — hidden in the input features themselves. The two big families covered in this lesson are **clustering** (grouping similar observations) and **dimensionality reduction** (compressing many features into fewer, more informative ones).

**K-means clustering** partitions data into *k* clusters by iteratively assigning each point to the nearest centroid and then recomputing centroids as the mean of the points assigned to them. It requires you to choose *k* up front (often via the elbow method, plotting within-cluster sum of squares against *k*), assumes roughly spherical, similarly sized clusters, and is sensitive to the initial placement of centroids and to outliers.

**Hierarchical clustering** builds a nested tree of clusters rather than a flat partition. Agglomerative (bottom-up) hierarchical clustering starts with every point as its own cluster and repeatedly merges the two closest clusters based on a distance metric and a linkage rule (single, complete, average, or Ward), until everything collapses into one cluster. The result is visualized as a **dendrogram**, a tree-shaped diagram whose vertical axis represents the distance (dissimilarity) at which clusters merge. To choose the number of clusters after the fact, you look at the dendrogram and find the tallest vertical line that can be drawn without crossing any horizontal merge line — cutting through that gap gives the most "natural" number of clusters for the data.

**DBSCAN** (Density-Based Spatial Clustering of Applications with Noise) groups points that are densely packed together and marks sparse, isolated points as noise/outliers. Unlike k-means, it does not require specifying the number of clusters in advance, can find arbitrarily shaped clusters, and naturally handles outliers — but it does require tuning two parameters: `eps` (neighborhood radius) and `min_samples` (minimum points to form a dense region).

**Dimensionality reduction** techniques such as **PCA (Principal Component Analysis)** and **ICA (Independent Component Analysis)** reduce the number of features while preserving the most useful information, which helps with visualization, noise reduction, and speeding up downstream models. PCA finds orthogonal directions (principal components) that capture the maximum **variance** in the data, ranked by how much variance each explains. ICA instead searches for components that are **statistically independent** of one another, which makes it especially useful for separating mixed signals (e.g., separating individual voices from an audio recording — the classic "cocktail party problem"), whereas PCA is better suited to compressing correlated features into fewer variance-maximizing dimensions.

A useful way to keep these straight: k-means and hierarchical clustering both group *observations*, but differ in whether you must pre-specify *k* (k-means) or can decide the cut point after seeing the whole merge tree (hierarchical). DBSCAN groups observations by density rather than distance-to-centroid, and it alone treats "does not belong to any cluster" as a first-class outcome. PCA and ICA both reduce *features* rather than group rows, but they optimize for different statistical properties — variance vs. independence — so choosing between them depends on whether your goal is compact summarization (PCA) or unmixing hidden independent sources (ICA).

---

## Original Knowledge Check Questions

### Question 1

What is the goal of hierarchical clustering?

- **A.** To classify data into distinct groups
- **B.** To identify anomalies in data sets
- **C.** To reduce the dimensionality of input data
- **D.** To create a tree-shaped structure known as a dendrogram

### Question 2

What is the first step in choosing the optimal number of clusters in hierarchical clustering?

- **A.** Choosing a random number
- **B.** Identifying the longest line that traverses the maximum vertical distance without intercepting any of the merging points in the dendrogram
- **C.** Counting the number of horizontal lines in the dendrogram
- **D.** Looking at the colors in the dendrogram

### Question 3

How does ICA differ from PCA?

- **A.** ICA and PCA are the same techniques with different names.
- **B.** ICA is used for supervised learning, while PCA is used for unsupervised learning.
- **C.** ICA focuses on maximizing the independence of components, while PCA focuses on maximizing the variance of data points.
- **D.** ICA and PCA are both used for data reduction in machine learning.

---

## Answers

**1. Answer: D — To create a tree-shaped structure known as a dendrogram**
The goal of hierarchical clustering is to build a dendrogram that shows the hierarchical relationships between items, revealing the best way to group items into clusters based on their similarities and dissimilarities.

**2. Answer: B — Identifying the longest line that traverses the maximum vertical distance without intercepting any of the merging points in the dendrogram**
The optimal number of clusters is found by locating the tallest vertical span in the dendrogram that isn't crossed by a merge line, then drawing a horizontal cut through it — the number of vertical lines the cut crosses is the suggested cluster count.

**3. Answer: C — ICA focuses on maximizing the independence of components, while PCA focuses on maximizing the variance of data points.**
PCA finds orthogonal directions that capture the most variance in the data, which is ideal for compression and summarization; ICA instead seeks statistically independent components, which is better suited for unmixing separate signal sources.

---

## 📝 Additional Practice Questions

**Q4 (Multiple Choice).** In k-means clustering, what does the "elbow method" help you determine?

- **A.** The best distance metric to use
- **B.** The optimal number of clusters (k)
- **C.** Whether the data contains outliers
- **D.** The order in which points are assigned to clusters

**Q5 (Multiple Choice).** Which of the following is a key limitation of k-means clustering compared to DBSCAN?

- **A.** K-means cannot be used on numeric data
- **B.** K-means requires the number of clusters to be specified in advance and struggles with non-spherical clusters
- **C.** K-means always produces a dendrogram
- **D.** K-means cannot run on large data sets

**Q6 (Short Answer).** What is a dendrogram, and what does the height of a merge point on it represent?

**Q7 (Multiple Choice).** In agglomerative hierarchical clustering, what is the initial state of the clustering process?

- **A.** All points belong to a single cluster
- **B.** Each point starts as its own individual cluster
- **C.** Points are randomly assigned to k clusters
- **D.** Points are grouped by class label

**Q8 (Multiple Choice).** Which parameter(s) must be tuned when using DBSCAN?

- **A.** The number of clusters, k
- **B.** The number of principal components
- **C.** The neighborhood radius (eps) and the minimum number of points (min_samples)
- **D.** The linkage method

**Q9 (Short Answer).** Explain, in one or two sentences, why DBSCAN is often preferred over k-means when a data set contains outliers or noise.

**Q10 (Multiple Choice).** What does a principal component in PCA represent?

- **A.** A single original feature from the data set
- **B.** A cluster centroid
- **C.** A direction in feature space that captures the maximum remaining variance in the data
- **D.** A label predicted by a supervised model

**Q11 (Short Answer).** Give one real-world example where ICA would be more appropriate than PCA, and briefly explain why.

**Q12 (Multiple Choice).** Which linkage method in hierarchical clustering merges clusters based on the minimum distance between any two points in the two clusters?

- **A.** Complete linkage
- **B.** Average linkage
- **C.** Single linkage
- **D.** Ward's linkage

**Q13 (Short Answer).** Why is it generally good practice to scale/standardize features before applying k-means, hierarchical clustering, PCA, or DBSCAN?

### Answers

**A4. Answer: B — The optimal number of clusters (k)**
The elbow method plots the within-cluster sum of squares (inertia) against different values of k; the "elbow" point where the decrease sharply levels off is taken as a good estimate of the optimal k.

**A5. Answer: B — K-means requires the number of clusters to be specified in advance and struggles with non-spherical clusters**
K-means needs k chosen beforehand and assumes roughly spherical, equally sized clusters, while DBSCAN discovers the number of clusters automatically and can capture arbitrarily shaped, density-based clusters.

**A6.** A dendrogram is a tree-shaped diagram produced by hierarchical clustering that shows the order and distance at which individual points and clusters are merged. The height (vertical position) of a merge point represents the distance/dissimilarity between the two clusters being joined — higher merges mean less similar clusters were combined.

**A7. Answer: B — Each point starts as its own individual cluster**
Agglomerative ("bottom-up") hierarchical clustering begins with every observation as its own singleton cluster and progressively merges the closest pairs of clusters until only one remains.

**A8. Answer: C — The neighborhood radius (eps) and the minimum number of points (min_samples)**
DBSCAN's two core hyperparameters define what counts as a "dense" region: `eps` sets the radius of a point's neighborhood, and `min_samples` sets how many neighbors are needed for a point to be considered a core point.

**A9.** DBSCAN classifies sparse, isolated points as noise rather than forcing them into a cluster, whereas k-means assigns every point to some centroid regardless of how far away or atypical it is, which can distort cluster centers when outliers are present.

**A10. Answer: C — A direction in feature space that captures the maximum remaining variance in the data**
Each principal component is an orthogonal linear combination of the original features chosen so that the first component captures the most variance possible, the second captures the most remaining variance orthogonal to the first, and so on.

**A11.** A classic example is audio/signal separation — e.g., separating multiple overlapping voice recordings picked up by different microphones (the "cocktail party problem"). ICA is preferred here because the goal is to recover statistically independent underlying source signals, not simply to compress correlated variables into a smaller number of variance-maximizing dimensions, which is what PCA is optimized for.

**A12. Answer: C — Single linkage**
Single linkage defines the distance between two clusters as the minimum distance between any point in one cluster and any point in the other, which tends to produce elongated, "chained" clusters compared to complete or average linkage.

**A13.** These algorithms rely on distance or variance calculations (Euclidean distance for k-means/hierarchical/DBSCAN, variance for PCA), so features measured on larger numeric scales would dominate the distance/variance calculations purely due to their units, not their actual importance. Standardizing (e.g., zero mean, unit variance) puts all features on a comparable scale so that each contributes fairly to the clustering or component extraction.
