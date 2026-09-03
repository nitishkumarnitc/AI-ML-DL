# Lesson 7 Knowledge Checks: Recommendation Systems

## Concept Primer

**Recommendation engines** are systems that predict which items (products, movies, articles, etc.) a user is most likely to want, based on data about that user and about other users or items. Almost every modern recommender falls into one of three broad families: **content-based filtering**, **collaborative filtering**, and **hybrid** approaches that combine the two. Before any recommendation can be generated, the system must go through a **data collection** step — gathering raw signals such as page views, browsing/view history, cart events, purchase history, ratings, or explicit feedback. This data is the raw material that all downstream modeling depends on; without it, no filtering technique has anything to learn from.

**Content-based filtering** recommends items by comparing item attributes (genre, keywords, price, category, ingredients, etc.) to a profile of what a specific user has liked before. It essentially asks, "what are the properties of things this user already likes, and what other items share those properties?" It works well for a single user even with little data about other users, but it tends to over-specialize — recommending only things very similar to what's already been consumed — and it requires rich, well-structured item metadata.

**Collaborative filtering (CF)** instead recommends items based on the interests and behavior of *similar users* (user-based CF) or on items that are *frequently liked together* (item-based CF), without needing to understand the content of the items themselves. The core assumption is that people who agreed in the past will agree again in the future. CF is powerful because it can surface non-obvious recommendations (it doesn't need item descriptions), but it requires a substantial amount of interaction data (ratings, clicks, purchases) across many users to find meaningful similarity patterns.

**Matrix factorization** is a mathematical technique commonly used to implement collaborative filtering at scale. The user–item interaction data is represented as a large, sparse matrix (rows = users, columns = items, values = ratings/interactions). Matrix factorization decomposes this matrix into two smaller, dense matrices of "latent factors" — one describing users, one describing items — such that multiplying them back together approximates the original ratings. These latent factors capture hidden patterns (e.g., a "preference for comedy" dimension) that aren't explicitly labeled in the data, and they let the system predict a user's rating for items they haven't yet interacted with. Techniques like Singular Value Decomposition (SVD) and Alternating Least Squares (ALS) are classic ways to compute this factorization.

The **cold-start problem** is one of the biggest practical challenges in recommendation systems: how do you recommend anything to a brand-new user (no history) or recommend a brand-new item (no ratings yet)? Pure collaborative filtering fails here because there's no interaction data to compute similarity from. Common mitigations include falling back to content-based filtering for new items/users, using popularity-based or demographic defaults, asking new users for explicit preferences during onboarding, or blending in hybrid approaches that lean on content signals until enough interaction data accumulates.

Finally, **hybrid recommenders** combine content-based and collaborative techniques (and sometimes other signals like context, location, or time) to get the strengths of both — the personalization depth of collaborative filtering plus the robustness to sparse/cold-start data that content-based filtering provides. Most production-grade recommendation systems used by large e-commerce and streaming platforms are hybrids.

---

## Original Knowledge Check Questions

### Question 1

**What are the three types of recommendation engines?**

- **A.** Hybrid, analytical, and batch
- **B.** Collaborative filtering, content-based filtering, and hybrid
- **C.** Online, offline, and nearline
- **D.** Real time, passive, and hybrid

### Question 2

**What is the purpose of data collection in recommendation engines?**

- **A.** To create a list of recommended products
- **B.** To narrow down relevant information
- **C.** To perform real-time analysis
- **D.** To procure data such as page views, view history, or cart events

### Question 3

**What is collaborative filtering?**

- **A.** Filtering data to narrow down on relevant information
- **B.** Providing recommendations based on the interests of similar users
- **C.** Modulating offerings based on clients' internet consumption patterns
- **D.** Analyzing data to create a list of recommended products

---

## Answers

**1. Answer: B — Collaborative filtering, content-based filtering, and hybrid.**
The three fundamental types of recommendation engines are collaborative filtering (recommends based on similar users' behavior), content-based filtering (recommends based on item attributes and a user's own history), and hybrid systems (a combination of both). The other options describe unrelated system-architecture or delivery concepts, not recommender types.

**2. Answer: D — To procure data such as page views, view history, or cart events.**
Data collection is the first stage in the recommendation engine pipeline. Its job is simply to gather raw behavioral signals — page views, browsing/view history, cart events, purchases, ratings — that later stages (filtering, modeling, ranking) will use to generate the actual recommendations.

**3. Answer: B — Providing recommendations based on the interests of similar users.**
Collaborative filtering works by identifying users (or items) with similar behavior/preference patterns and using that similarity to predict what a user will like, rather than analyzing the content/attributes of the items directly (that would be content-based filtering).

---

## 📝 Additional Practice Questions

**Q4 (Multiple Choice).** Which of the following best describes content-based filtering?
- **A.** Recommending items based on what similar users have liked
- **B.** Recommending items based on the attributes of items a user has previously liked
- **C.** Recommending items purely at random to increase diversity
- **D.** Recommending the most popular items to every user regardless of history

**Q5 (Multiple Choice).** A streaming service wants to recommend movies to a user who just signed up and has no viewing history. This scenario is best described as:
- **A.** Overfitting
- **B.** The cold-start problem
- **C.** Matrix factorization
- **D.** Item-based collaborative filtering

**Q6 (Multiple Choice).** In matrix factorization for collaborative filtering, the original user–item rating matrix is decomposed into:
- **A.** A single matrix of item popularity scores
- **B.** Two smaller matrices representing latent user and item factors
- **C.** A list of content tags for each item
- **D.** A decision tree over user demographics

**Q7 (Multiple Choice).** Which of the following is a disadvantage most associated with collaborative filtering (rather than content-based filtering)?
- **A.** It cannot recommend items outside a user's own past preferences
- **B.** It requires a large amount of user interaction data and struggles with new users/items
- **C.** It only works for text-based items like articles
- **D.** It cannot use latent factors

**Q8 (Multiple Choice).** Which technique is commonly used to compute matrix factorization for collaborative filtering?
- **A.** K-means clustering
- **B.** Singular Value Decomposition (SVD)
- **C.** Linear regression on item price
- **D.** Breadth-first search

**Q9 (Short Answer).** Explain, in 1-2 sentences, why a hybrid recommendation system is often preferred over a purely collaborative or purely content-based system in production.

**Q10 (Short Answer).** Describe one practical way a company could mitigate the cold-start problem for a brand-new item that has just been added to their catalog.

**Q11 (Multiple Choice).** Item-based collaborative filtering recommends products by:
- **A.** Finding items frequently rated/purchased similarly by the same users
- **B.** Finding items with similar text descriptions
- **C.** Finding the cheapest items in a category
- **D.** Randomly sampling from the catalog

**Q12 (Short Answer).** What is a "latent factor" in the context of matrix factorization, and why can't it be directly observed in the raw data?

### Answers

**Q4. Answer: B.**
Content-based filtering compares the attributes/features of items (genre, keywords, category, etc.) against a profile built from a specific user's own past preferences — it does not rely on other users' behavior at all.

**Q5. Answer: B.**
This is the classic cold-start problem: with no interaction history for the new user, collaborative filtering has no similarity signal to work from, so the system must fall back on content-based, popularity-based, or onboarding-survey approaches.

**Q6. Answer: B.**
Matrix factorization decomposes the large, sparse user–item ratings matrix into two smaller, dense matrices — one of latent user factors and one of latent item factors — whose product approximates the original ratings and allows prediction of missing entries.

**Q7. Answer: B.**
Collaborative filtering depends on having enough interaction data (ratings, clicks, purchases) across many users; it performs poorly for brand-new users or items with little to no interaction history (the cold-start problem), unlike content-based filtering, which can work from item metadata alone.

**Q8. Answer: B.**
Singular Value Decomposition (SVD), along with related techniques like Alternating Least Squares (ALS), is a classic algorithm used to factorize the user-item matrix into latent user and item factor matrices.

**Q9. Answer (sample):**
A hybrid system combines the personalization strength of collaborative filtering with the robustness of content-based filtering to sparse data and cold-start scenarios, producing more accurate and more broadly applicable recommendations than either technique alone.

**Q10. Answer (sample):**
Use the new item's content attributes (category, description, tags, price range) to match it against users who have shown interest in similar existing items — i.e., temporarily rely on content-based filtering (or feature-based similarity) until enough user interactions accumulate for collaborative filtering to become effective. (Other valid answers: promote it via popularity/editorial placement, or use metadata-based "similar item" substitution.)

**Q11. Answer: A.**
Item-based collaborative filtering looks for items that tend to be rated, purchased, or interacted with similarly by the same set of users (e.g., "customers who bought X also bought Y"), rather than comparing textual/content descriptions of the items.

**Q12. Answer (sample):**
A latent factor is a hidden, inferred dimension (e.g., an implicit "preference for comedy" or "preference for budget items") that the matrix factorization algorithm derives mathematically from patterns in the rating data. It isn't directly observed or labeled in the raw dataset — it emerges purely from the statistical structure of user-item interactions, which is why it's called "latent" (hidden).
