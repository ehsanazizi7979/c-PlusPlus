# C++ Concurrency in Action — Chapters 1–10 + Appendices A–D + Resources

Open [`index.html`](index.html) in a browser for a self-contained, interactive study guide to Chapters 1–10, Appendices A–D, and the Resources section of Anthony Williams's *C++ Concurrency in Action: Practical Multithreading* (Manning, 2012).

The guide includes Chapter 1's figures; Chapter 2's thread-management summary and lifecycle simulator; Chapter 3's shared-data summary and list figure; Chapter 4's queue lab and futures/timeouts examples; Chapter 5's memory-model summary, atomic examples, ordering figures, and interactive demo; Chapter 6's lock-based data structures and lock-scope lab; Chapter 7's lock-free progress guarantees, reclamation strategies, memory-ordering guidance, and queue-helping simulator; Chapter 8's work-partitioning patterns, performance and locality guidance, Amdahl's-law calculator, and parallel-algorithm examples; Chapter 9's thread-pool design, task-dependency lab, work stealing, cooperative interruption, and C++20 stop-token note; and Chapter 10's concurrency bug taxonomy, code-review checklist, stress/model-testing strategies, coordinated test harness, performance-testing guidance, and interactive readiness-gate lab. Appendix A summarizes C++11 rvalue references and move semantics, deleted/defaulted functions, constexpr, lambda captures, variadic templates, auto deduction, and thread_local storage, with interactive move-ownership and capture examples. Appendix B adds a historical comparison matrix for Java, POSIX C, Boost.Thread, and C++11, with semantic caveats and chapter cross-references. Appendix C explains the typed-mailbox actor framework and adds a deterministic ATM message-trace simulator. Appendix D is a C++11 thread-library quick reference with a task-first API chooser and safe-use recipes. The final Resources section maps the source bibliography to focused reading paths and flags its historical web references. Review prompts, copyable C++ excerpts, and light/dark themes are included throughout.

Selected source figures and brief code excerpts are included with attribution. Original teaching aids include the Chapter 2 lifecycle diagram; Chapter 4 queue demo; Chapter 5 memory-order demo; Chapter 6 lock-scope lab; Chapter 7 queue-helping simulator; Chapter 8 pipeline diagram, tile map, and Amdahl calculator; Chapter 9 pool-dependency lab; Chapter 10 readiness-gate lab; Appendix A move-ownership and lambda-capture labs; the Appendix B feature matrix; the Appendix C ATM message-trace simulator; the Appendix D library API chooser; and the Resources reading-path guide. All assets are embedded in the page; there are no external assets or package dependencies.

For a local HTTP server instead of opening the file directly:

```sh
python3 -m http.server 8000 --bind 0.0.0.0
```

Then open `http://localhost:8000` on the same machine.
