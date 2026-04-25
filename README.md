# HackUPC-2026
Here is your text perfectly formatted in Markdown, ready to be copied and pasted into Devpost, GitHub, or any other platform:

***

## Inspiration
The Mecalux 2D Bin Packing challenge revolves around a very specific scoring metric:

$$Q = \left(\frac{\sum Price}{\sum Loads}\right)^{2 - \text{Area Ratio}}$$

Because the Area Ratio acts as an exponent, leaving dead aisles or fragmented space exponentially wrecks the final score. Our first instinct—and what most AI tools suggested we do—was to use a standard greedy algorithm paired with a meta-heuristic like Simulated Annealing. 

We quickly hit a wall. Python is fundamentally too slow to run enough iterations within the strict 30-second execution limit, and standard heuristics just created a "Swiss cheese" effect of fragmented, unusable space. Furthermore, pure Python couldn't effectively leverage the hardware's multi-core parallelization capabilities. We needed a massive paradigm shift to achieve true density.

## What it does
CherokeeTeams has built an industrial-grade, High-Performance Computing (HPC) solver for complex warehouse bin packing. It ingests floor plans, variable ceiling height maps, and catalogues of shelving bays (with strict aisle-clearance constraints), and outputs the mathematically optimal spatial layout to maximize financial efficiency. 

It acts as a dual-architecture system: a blisteringly fast mathematical backend that calculates tens of thousands of permutations per second, paired with a cross-platform desktop application that renders the final warehouse topologies in interactive, real-time 3D.

## How we built it
We realized we couldn't rely on Python for the heavy mathematical lifting. Instead, we used Python strictly as an interface and wrapper. The actual solver engine was rewritten to live entirely in C-compiled code using Numba (`@njit(nogil=True)`). This allowed us to bypass the Global Interpreter Lock (GIL) and squeeze every drop of performance out of the CPU.

* **Fast Orthogonal Scanline:** We dropped floating-point trigonometry and modeled the warehouse as a discrete matrix, using Axis-Aligned Bounding Boxes (AABB) to scan for valid placements pixel by pixel.
* **Parallel GRASP (Greedy Randomized Adaptive Search Procedure):** Instead of slow backtracking, we used all CPU cores to construct tens of thousands of layouts from scratch per second. We injected 15-30% stochastic noise into our catalogue sorting, forcing the threads to explore drastically different topologies in parallel.
* **The "Gravel Sweep":** A two-pass system. Pass one packs the massive, highly profitable bays. Pass two re-scans the leftover "dead" space to cram in the absolute smallest bays available, artificially pushing the Area Ratio as close to 100% as possible.
* **Frontend:** To debug and showcase the results, we built a cross-platform desktop app using Tauri (Rust), React, and Three.js for interactive 3D visualization.

## Challenges we ran into
Building an industrial-grade solver in a weekend meant hitting several technical roadblocks:

* **Escaping the GIL:** Initially, our Python multithreading was practically fake due to the GIL taking nearly 30 seconds to run a single sweep. Once we moved the sweep logic to a C-compiled kernel, execution time plummeted from 28.5 seconds to 0.01 seconds. This allowed us to run 50,000+ iterations and implement Early Stopping.
* **The "Aisle-to-the-Past" Routing:** Naively placing a bay and reserving its required aisle forward ruined empty space for future boxes. We engineered a 6-way dynamic anchoring system that forces aisles to project backwards into already occupied or dead space. This enabled back-to-back racking and saved massive amounts of room.
* **The Zero-Ceiling Bug:** The dataset uses `0` to represent areas without ceiling limits. Our collision logic checked if `0 < bay_height`, which falsely flagged infinite-ceiling zones as illegal. Catching this edge case instantly unlocked the hardest test cases.
* **RAM Exhaustion:** Huge warehouses caused our discrete matrices to trigger Out-Of-Memory (OOM) errors. We bypassed this by implementing Geometric GCD (Greatest Common Divisor) Compression—dividing all spatial coordinates by their GCD before processing. This compressed RAM usage by up to 10,000x with zero loss in precision.

## Accomplishments that we're proud of
* **Execution Speed:** Successfully dropping our processing time from 28.5 seconds down to 10 milliseconds per sweep by defeating Python's GIL and compiling down to C.
* **Memory Optimization:** Implementing the Geometric GCD compression allowed us to process massive industrial warehouses on standard laptop hardware without crashing.
* **Full-Stack Delivery:** We didn't just write a script that outputs a CSV. We managed to pair a hardcore mathematical backend with a beautiful, fully functional Rust/React 3D desktop application within the hackathon timeframe.

## What we learned
* **Hardware > Theory:** We proved firsthand that flat, contiguous memory arrays processed by SIMD registers completely outperform "smart" dynamic data structures (like Priority Queues or Trees) in high-performance computing due to CPU cache misses.
* **Language Limits:** We learned how to push Python beyond its typical boundaries by dropping down to LLVM compilation and manual memory management to achieve true parallel execution.

## What's next for CherokeeTeams
* **Unified Rust Stack:** Porting the entire mathematical backend natively to Rust to eliminate the Python dependency entirely and integrate it directly into the Tauri app.

