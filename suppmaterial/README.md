# replicataion of the upstream bug management in Linux distributions

## Prerequisites
Make sure you have installed all of the following prerequisites on your machine:
- Git - [Download & Install Git](https://git-scm.com/downloads). OSX and Linux machines typically have this already installed.
- Python 3.8+ - [Downaload & Install Python](https://www.python.org/downloads/).
- Make - Download & Install make, .e.g., [OSX](https://formulae.brew.sh/formula/make), [Linux](https://tldp.org/HOWTO/Software-Building-HOWTO-3.html)

We recommend using an [Anaconda](https://docs.anaconda.com/anaconda/install/) environment with Python version 3.8, and every Python requirement should be met.

## Introduction 

This supplementary material contains scripts for collecting and processing data. The scripts are organized in the `supplementerial` folder.

1. The `supplementerial/fedora.py` file contains scripts for collecting data from Fedora
2. The `supplementerial/fedora/` folder contains functions to archieve particular purposes for Fedora. These functions are invoked in the `fedora.py` file.
3. The `supplementerial/debian.py` file contains scripts for collecting data from Debian.
4. The `supplementerial/debian/` folder contains functions to archieve particular purposes for Debian. These functions are invoked in the `debian.py` file.
5. The `supplementerial/utils/` folder contains functions for general purposes.

To run the scripts, using the following command to install the required Python modeuls. If you cannot run the command, please find the required modules from the `supplementerial/requirements.txt` file and install them manually.
```
$ make install
```

Download bugs, packages, and patches from Debian and Fedora. This takes a long time. Make sure your machine has a stable network connection and a power supply.
```
$ make download
```

After fetching the data, mark upstream fixed bugs in Debain and Fedora.
```
$ make mark-upstream
```

Mark local fixed bugs in Debian and Fedora.
```
mark mark-local-fixes
```

Assgin Debian's package categories on Fedora's packages and remove duplicate bugs in the dataset.
```
$ make mapping
```