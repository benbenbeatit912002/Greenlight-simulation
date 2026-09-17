# Upstream acknowledgements and citations

The scientific foundations of this application belong to the original GreenLight and GreenLight-Gym authors. This interface repository does not claim authorship of their model or environment. Attribution here does not imply that those authors developed, reviewed or endorsed this wrapper.

## GreenLight model

David Katzin, Simon van Mourik, Frank Kempkes, and Eldert J. van Henten (2020). **GreenLight – An open source model for greenhouses with supplemental lighting: Evaluation of heat requirements under LED and HPS lamps.** *Biosystems Engineering*, 194, 61–81.

[DOI](https://doi.org/10.1016/j.biosystemseng.2020.03.010) · [Original software](https://github.com/davkat1/GreenLight) · [Wageningen publication record](https://research.wur.nl/en/publications/greenlight-an-open-source-model-for-greenhouses-with-supplemental/)

```bibtex
@article{katzin2020greenlight,
  author = {Katzin, David and van Mourik, Simon and Kempkes, Frank and van Henten, Eldert J.},
  title = {{GreenLight} -- An open source model for greenhouses with supplemental lighting: Evaluation of heat requirements under {LED} and {HPS} lamps},
  journal = {Biosystems Engineering},
  year = {2020},
  volume = {194},
  pages = {61--81},
  doi = {10.1016/j.biosystemseng.2020.03.010}
}
```

## GreenLight-Gym2 implementation

The upstream repository identifies **Bart van Laatum** as its author and asks research users to cite the following conference publication by **Bart van Laatum, Eldert J. van Henten, and Sjoerd Boersma** (2025): **GreenLight-Gym: Reinforcement learning benchmark environment for control of greenhouse production systems.** *IFAC-PapersOnLine*, 59(23), 437–442.

[DOI](https://doi.org/10.1016/j.ifacol.2025.11.827) · [Software and upstream citation instructions](https://github.com/BartvLaatum/GreenLight-Gym2#citation)

```bibtex
@inproceedings{vanLaatum2025GreenLightGym,
  title = {{GreenLight-Gym}: Reinforcement learning benchmark environment for control of greenhouse production systems},
  author = {van Laatum, Bart and van Henten, Eldert J. and Boersma, Sjoerd},
  journal = {IFAC-PapersOnLine},
  year = {2025},
  volume = {59},
  number = {23},
  pages = {437--442},
  doi = {10.1016/j.ifacol.2025.11.827},
  note = {8th IFAC Conference on Sensing, Control and Automation Technologies for Agriculture (AGRICONTROL 2025)}
}
```

The second entry follows the upstream repository's requested conference citation. Citation information was checked on 2026-09-17.

## Citing this interface and a specific run

In addition to the relevant upstream publications, identify this interface repository and the exact application/upstream commits used for a result. Retain model, configuration and weather provenance as described in [MODEL_CARD](MODEL_CARD.md). Citations acknowledge the scientific foundation; they do not independently validate the wrapper's predictions.

The upstream researchers are not listed as authors of this interface repository. A repository-level `CITATION.cff` can be added when this wrapper's own author metadata is confirmed. Upstream attribution is provided now through this document and the README.
