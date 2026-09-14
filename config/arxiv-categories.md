# arXiv categories

Codes and names from arXiv's OAI-PMH set list (`https://oaipmh.arxiv.org/oai?verb=ListSets`),
fetched 2026-09-14. "New papers per weekday" is the average number of new submissions with
that primary category over three ordinary weekday mailings in September 2026; it is a rough
size guide for choosing between keyword mode and Claude mode, not a live number.

Refresh with `python3 scripts/utilities/keyword_dryrun.py --volumes` for current volumes.
The wizard suggests keyword mode when a topic's categories add up to more than 60 a day.

High-volume categories, where a generic phrase will match hundreds of unrelated papers a
week: cs.LG (machine learning), cs.CV (computer vision), cs.AI, cs.CL (NLP and LLM papers),
quant-ph, cs.RO. The human, social and software side of computing lives in cs.HC, cs.CY,
cs.SE, cs.MA, cs.SI and cs.DL, with related work in econ.GN, stat.AP and physics.soc-ph.

## Computer Science (cs)

| Code | Name | New papers per weekday |
|---|---|---|
| cs.AI | Artificial Intelligence | 64 |
| cs.AR | Hardware Architecture | 6 |
| cs.CC | Computational Complexity | 3 |
| cs.CE | Computational Engineering, Finance, and Science | 4 |
| cs.CG | Computational Geometry | 2 |
| cs.CL | Computation and Language | 54 |
| cs.CR | Cryptography and Security | 37 |
| cs.CV | Computer Vision and Pattern Recognition | 76 |
| cs.CY | Computers and Society | 8 |
| cs.DB | Databases | 2 |
| cs.DC | Distributed, Parallel, and Cluster Computing | 11 |
| cs.DL | Digital Libraries | 3 |
| cs.DM | Discrete Mathematics | 1 |
| cs.DS | Data Structures and Algorithms | 7 |
| cs.ET | Emerging Technologies | 1 |
| cs.FL | Formal Languages and Automata Theory | 1 |
| cs.GL | General Literature | 0 |
| cs.GR | Graphics | 3 |
| cs.GT | Computer Science and Game Theory | 7 |
| cs.HC | Human-Computer Interaction | 16 |
| cs.IR | Information Retrieval | 8 |
| cs.IT | Information Theory | 12 |
| cs.LG | Machine Learning | 80 |
| cs.LO | Logic in Computer Science | 3 |
| cs.MA | Multiagent Systems | 3 |
| cs.MM | Multimedia | under 1 |
| cs.MS | Mathematical Software | under 1 |
| cs.NA | Numerical Analysis | 0 |
| cs.NE | Neural and Evolutionary Computing | 3 |
| cs.NI | Networking and Internet Architecture | 9 |
| cs.OH | Other Computer Science | 0 |
| cs.OS | Operating Systems | 1 |
| cs.PF | Performance | under 1 |
| cs.PL | Programming Languages | under 1 |
| cs.RO | Robotics | 42 |
| cs.SC | Symbolic Computation | under 1 |
| cs.SD | Sound | 10 |
| cs.SE | Software Engineering | 21 |
| cs.SI | Social and Information Networks | 3 |
| cs.SY | Systems and Control | 0 |

## Economics (econ)

| Code | Name | New papers per weekday |
|---|---|---|
| econ.EM | Econometrics | 4 |
| econ.GN | General Economics | 3 |
| econ.TH | Theoretical Economics | 5 |

## Electrical Engineering and Systems Science (eess)

| Code | Name | New papers per weekday |
|---|---|---|
| eess.AS | Audio and Speech Processing | 11 |
| eess.IV | Image and Video Processing | 4 |
| eess.SP | Signal Processing | 17 |
| eess.SY | Systems and Control | 16 |

## Mathematics (math)

| Code | Name | New papers per weekday |
|---|---|---|
| math.AC | Commutative Algebra | 4 |
| math.AG | Algebraic Geometry | 19 |
| math.AP | Analysis of PDEs | 33 |
| math.AT | Algebraic Topology | 2 |
| math.CA | Classical Analysis and ODEs | 8 |
| math.CO | Combinatorics | 31 |
| math.CT | Category Theory | 1 |
| math.CV | Complex Variables | 4 |
| math.DG | Differential Geometry | 17 |
| math.DS | Dynamical Systems | 10 |
| math.FA | Functional Analysis | 16 |
| math.GM | General Mathematics | 4 |
| math.GN | General Topology | 1 |
| math.GR | Group Theory | 5 |
| math.GT | Geometric Topology | 6 |
| math.HO | History and Overview | 2 |
| math.IT | Information Theory | 0 |
| math.KT | K-Theory and Homology | under 1 |
| math.LO | Logic | 5 |
| math.MG | Metric Geometry | 6 |
| math.MP | Mathematical Physics | 0 |
| math.NA | Numerical Analysis | 22 |
| math.NT | Number Theory | 21 |
| math.OA | Operator Algebras | 6 |
| math.OC | Optimization and Control | 26 |
| math.PR | Probability | 24 |
| math.QA | Quantum Algebra | 3 |
| math.RA | Rings and Algebras | 7 |
| math.RT | Representation Theory | 6 |
| math.SG | Symplectic Geometry | 1 |
| math.SP | Spectral Theory | 2 |
| math.ST | Statistics Theory | 7 |

## Physics (physics)

| Code | Name | New papers per weekday |
|---|---|---|
| astro-ph.CO | Cosmology and Nongalactic Astrophysics | 11 |
| astro-ph.EP | Earth and Planetary Astrophysics | 10 |
| astro-ph.GA | Astrophysics of Galaxies | 22 |
| astro-ph.HE | High Energy Astrophysical Phenomena | 18 |
| astro-ph.IM | Instrumentation and Methods for Astrophysics | 9 |
| astro-ph.SR | Solar and Stellar Astrophysics | 13 |
| cond-mat.dis-nn | Disordered Systems and Neural Networks | 1 |
| cond-mat.mes-hall | Mesoscale and Nanoscale Physics | 14 |
| cond-mat.mtrl-sci | Materials Science | 24 |
| cond-mat.other | Other Condensed Matter | under 1 |
| cond-mat.quant-gas | Quantum Gases | 3 |
| cond-mat.soft | Soft Condensed Matter | 8 |
| cond-mat.stat-mech | Statistical Mechanics | 13 |
| cond-mat.str-el | Strongly Correlated Electrons | 13 |
| cond-mat.supr-con | Superconductivity | 4 |
| gr-qc | General Relativity and Quantum Cosmology | 22 |
| hep-ex | High Energy Physics - Experiment | 4 |
| hep-lat | High Energy Physics - Lattice | under 1 |
| hep-ph | High Energy Physics - Phenomenology | 30 |
| hep-th | High Energy Physics - Theory | 21 |
| math-ph | Mathematical Physics | 8 |
| nlin.AO | Adaptation and Self-Organizing Systems | under 1 |
| nlin.CD | Chaotic Dynamics | 1 |
| nlin.CG | Cellular Automata and Lattice Gases | 0 |
| nlin.PS | Pattern Formation and Solitons | under 1 |
| nlin.SI | Exactly Solvable and Integrable Systems | 2 |
| nucl-ex | Nuclear Experiment | 2 |
| nucl-th | Nuclear Theory | 6 |
| physics.acc-ph | Accelerator Physics | 2 |
| physics.ao-ph | Atmospheric and Oceanic Physics | 3 |
| physics.app-ph | Applied Physics | 5 |
| physics.atm-clus | Atomic and Molecular Clusters | 0 |
| physics.atom-ph | Atomic Physics | 3 |
| physics.bio-ph | Biological Physics | 1 |
| physics.chem-ph | Chemical Physics | 6 |
| physics.class-ph | Classical Physics | under 1 |
| physics.comp-ph | Computational Physics | 3 |
| physics.data-an | Data Analysis, Statistics and Probability | under 1 |
| physics.ed-ph | Physics Education | 2 |
| physics.flu-dyn | Fluid Dynamics | 10 |
| physics.gen-ph | General Physics | 10 |
| physics.geo-ph | Geophysics | 2 |
| physics.hist-ph | History and Philosophy of Physics | 1 |
| physics.ins-det | Instrumentation and Detectors | 5 |
| physics.med-ph | Medical Physics | 2 |
| physics.optics | Optics | 10 |
| physics.plasm-ph | Plasma Physics | 4 |
| physics.pop-ph | Popular Physics | under 1 |
| physics.soc-ph | Physics and Society | 4 |
| physics.space-ph | Space Physics | under 1 |
| quant-ph | Quantum Physics | 61 |

## Quantitative Biology (q-bio)

| Code | Name | New papers per weekday |
|---|---|---|
| q-bio.BM | Biomolecules | under 1 |
| q-bio.CB | Cell Behavior | 0 |
| q-bio.GN | Genomics | 0 |
| q-bio.MN | Molecular Networks | under 1 |
| q-bio.NC | Neurons and Cognition | 2 |
| q-bio.OT | Other Quantitative Biology | under 1 |
| q-bio.PE | Populations and Evolution | 2 |
| q-bio.QM | Quantitative Methods | 3 |
| q-bio.SC | Subcellular Processes | 0 |
| q-bio.TO | Tissues and Organs | 0 |

## Quantitative Finance (q-fin)

| Code | Name | New papers per weekday |
|---|---|---|
| q-fin.CP | Computational Finance | 0 |
| q-fin.EC | Economics | 0 |
| q-fin.GN | General Finance | 0 |
| q-fin.MF | Mathematical Finance | 1 |
| q-fin.PM | Portfolio Management | 1 |
| q-fin.PR | Pricing of Securities | 0 |
| q-fin.RM | Risk Management | 0 |
| q-fin.ST | Statistical Finance | under 1 |
| q-fin.TR | Trading and Market Microstructure | under 1 |

## Statistics (stat)

| Code | Name | New papers per weekday |
|---|---|---|
| stat.AP | Applications | 2 |
| stat.CO | Computation | under 1 |
| stat.ME | Methodology | 13 |
| stat.ML | Machine Learning | 9 |
| stat.OT | Other Statistics | 0 |
| stat.TH | Statistics Theory | 0 |
