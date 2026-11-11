---
name: explain
description: Explain a part of the system, a pull request, a decision or a term in plain words, grounded in the actual code, one level deeper each time it is asked. Use whenever the human says they are lost, asks what something means, or asks for a simpler explanation.
---

# explain — understanding on demand

1. **Ground it.** Read the code (and brief, if any) for the target now; do not rely on memory or old
   docs. Cite the files you used.
2. **Concrete first.** Start with one real scenario that walks through what happens, then the general
   rule. Define every term at first use; give one analogy for any concept that is new to the reader.
3. **One level at a time:** at most 15 lines. End by offering the next level down (for example: "the
   data model", "the failure cases", "why it was built this way").
4. **Never change code** in this skill.
5. If the confusion came from a brief, PR body or comment, propose the one-line fix to that text.
6. **A decision card** (its Explain choice): walk through each option as a scenario, say why the
   recommendation holds, then show the same card again instead of offering a next level; choosing
   Explain again goes one level deeper. Its decision stays open.

Log each request: `isv log explain.requested --change <id> target=<area> stage=frame|slice|verify|other depth=<n>`.
