# Journal And Experiment Plan

## Recommended Journal Order

1. `Machine Learning: Science and Technology`
   Reason: official scope includes methodological advances in machine learning motivated by scientific problems and ML applications in the sciences.
   Link: https://publishingsupport.iopscience.iop.org/journals/machine-learning-science-and-technology/about-machine-learning-science-technology/

2. `Frontiers in Artificial Intelligence`
   Reason: broad AI scope, practical systems focus, logic/reasoning/NLP relevance, realistic venue for an architecture plus benchmark paper.
   Link: https://www.frontiersin.org/journals/artificial-intelligence/about

3. `npj Artificial Intelligence`
   Reason: good fit if the paper becomes stronger and more selective, especially if the final contribution is framed as a notable AI methodology with interdisciplinary impact.
   Link: https://www.nature.com/npjai/aims

4. `Communications AI & Computing`
   Reason: fit for interpretable AI, multi-agent systems, reasoning, and AI applications to scientific domains, but likely more selective.
   Link: https://www.nature.com/commsaicomp/aims

## What To Submit First

Submit first to `Machine Learning: Science and Technology` unless the next experiment round becomes substantially stronger than expected.

## Why This Route Is Realistic

- The paper is methodological.
- The target task is scientific reasoning rather than a general LLM benchmark.
- The implementation is inspectable and reproducible.
- The evaluation can be sized for one researcher.

## Experimental Plan Under Limited Compute

### Goal

Show architectural value, not frontier-model supremacy.

### Recommended setup

- Local open model for most runs
- Small API comparison slice
- 100 to 300 curated benchmark items
- Single-GPU rental only for batch reruns if needed

### Core ablations

1. direct output
2. structured cognition only
3. mirror without memory
4. mirror with local memory
5. mirror with dual-layer memory

### Most convincing results for reviewers

- lower unsupported-certainty rate
- higher correction retention
- better abstention on underspecified cases
- fewer weak-prior-as-fact failures
- better condition and unit preservation on scientific questions

### What not to do

- Do not rely on a huge benchmark that cannot be rerun
- Do not center the paper on consciousness or philosophy
- Do not claim autonomous scientific discovery
- Do not make the evaluation depend entirely on expensive frontier APIs

