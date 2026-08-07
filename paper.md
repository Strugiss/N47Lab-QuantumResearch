---
title: "Observation of a Classical Prethermal Discrete Time Crystal on a Superconducting Quantum Processor via Phase-Anchored State Multiplexing"
authors:
  - name: Alessandro Tulli
    affiliation: "N47Lab"
    orcid: "0009-0008-9201-6080"
date: 2026-08-07
version: "v1.0.0"
doi: "10.5281/zenodo.XXXXXXXX"
repository: "https://github.com/Strugiss/N47Lab-QuantumResearch"
---

# Summary

We report the observation of a classical prethermal discrete time crystal (DTC) on a superconducting quantum processor using a novel protocol—Phase-Anchored State Multiplexing (PASM)—on two IBM Heron r2 processors (ibm_marrakesh and ibm_kingston). The PASM protocol prepares $N$ qubits in identical phase states via parallel Hadamard gates followed by a controlled-phase interaction, yielding a subharmonic response at $\phi = \pi$ with mutual information (MI) peaking at $0.785$ ($\phi$-scan), a PASM-H peak of $0.722 \pm 0.005$ at $\phi = \pi/2$, a 3-qubit scaling peak of $0.159 \pm 0.008$, and a combined $Z$-score exceeding $50\sigma$ across 14 experiments. The effect is robust across 10 independent replicas ($Z = 39.6\sigma$ on a second processor), independent of physical qubit distance ($Z = 34\sigma$), survives controlled noise injection, and vanishes under control protocols. Quantum state tomography (QST) confirms the correlation is classical (discord $< 0.01$), distinguishing it from conventional entanglement. A control with entanglement witness circuits yields MI $= 0.00013 \pm 0.0001$, below the Miller-Madow finite-shot floor of $\sim 2.6\times10^{-4}$ bit at 8192 shots. The observed phenomenology—subharmonic response at $\phi=\pi$, distance-independent classical correlations, finite-$N$ resonance at 3 qubits, noise resilience, and vanishing witness signal—is fully consistent with a classical prethermal discrete time crystal as predicted by Ye, Machado, and Yao (PRL 2021) and realized by Frey and Rachel on 57 superconducting qubits (Sci. Adv. 2022). We interpret these results as the first observation of a classical prethermal DTC on a superconducting processor, implemented via the PASM protocol.

# Statement of Need

The nature of dark matter remains one of the most consequential open questions in physics. A distinct line of inquiry, originating in quantum information theory, examines whether the quantum vacuum itself might store information inaccessible to classical measurement. The concept of a "quantum memory matrix" was formalized by Neukart, who proposed a geometry-information duality linking black hole entropy to vacuum structure. Here we introduce and experimentally test a specific protocol—Phase-Anchored State Multiplexing (PASM)—designed to probe whether identically-prepared quantum systems share a phase correlation mediated by a hypothetical sub-Planckian matrix. We report results from 14 experiments on two IBM Heron r2 quantum processors, totaling 186 circuit executions (8192 shots each, over $1.5\times10^{6}$ measurements), showing anomalous mutual information that is reproducible, scales with qubit number, survives controlled noise injection, and remains demonstrably classical in nature (as distinct from entanglement).

# Functionality

This repository contains all experimental data, analysis code, and paper source for the Classical Prethermal DTC discovery via PASM on IBM Quantum processors:

- **Experimental data**: Raw QPU results, job IDs, per-experiment outputs
- **Analysis code**: Mutual information calculation, bootstrap statistics, QST, discord analysis
- **Paper source**: LaTeX source for PRL/Nature Physics/Science Advances submission
- **Figures**: 47 figures (PNG/SVG) for paper
- **Circuits**: PASM circuit generation and submission scripts

# Installation

```bash
pip install -r requirements.txt
```

Requires: qiskit, qiskit-ibm-runtime, numpy, scipy, matplotlib, yaml

# Usage

```bash
# Submit PASM experiments to IBM Quantum
python pasm_dtc_circuits.py

# Analyze results
python scripts/analyze_results.py

# Compile paper
cd paper && pdflatex n47lab_paper.tex
```

# Testing

```bash
pytest tests/ -v
```

# License

MIT License — see LICENSE file.

# References

- Zenodo: [DOI pending]
- GitHub: https://github.com/Strugiss/N47Lab-QuantumResearch
- Related: pasm-experiments (https://github.com/Strugiss/pasm-experiments), research-timeline (https://github.com/Strugiss/research-timeline)