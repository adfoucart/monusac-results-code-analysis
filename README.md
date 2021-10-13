# Analysis of MoNuSAC 2020 results

These are the supplementary materials for the following technical report:

**Adrien Foucart, Olivier Debeir, Christine Decaestecker. 
Analysis of the MoNuSAC 2020 challenge evaluation and results: implementation errors. September, 2021.**
doi: [10.5281/zenodo.5520872](https://doi.org/10.5281/zenodo.5520871)

All the results from the report should be reproducible using this code and the publicly released MoNuSAC2020 test set annotations & "top 5 teams" predictions maps, available here: https://monusac-2020.grand-challenge.org/Data/

The Jupyter Notebook "MoNuSAC challenge results analysis.ipynb" contains the main experiments performed for the technical report. The *result_parser.py* and *metrics_reproduction.py* file contain code that would otherwise make the notebook less readable and have therefore been put in separate files.

All correspondance related to this publication should be addressed at Adrien Foucart (adrien.foucart@ulb.be).

The MoNuSAC challenge organizers have been informed of the errors found in their metric's implementation. This report is based on the published results and code as they stand on September 21th, 2021. If the publication, the official leaderboards or the published code get updated after this report, we will update this document accordingly.

## Requirements

This code was executed using the following libraries:

* python == 3.8
* openslide == 1.1.2
* skimage == 0.18.1

It should be mostly compatible to later or earlier versions, as long as python3 is used, but hasn't been tested on other systems.