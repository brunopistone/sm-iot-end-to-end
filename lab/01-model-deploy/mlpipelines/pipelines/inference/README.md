### buildspec.sh

Script used for running the pipeline in a specific environment

Parameters:
* ENV: Mandatory - environment related to the .yml file with the configurations
* PIPELINE: Mandatory - name of the pipeline you want to run

### IMPORTANT

If your pipeline needs some input parameters for starting, please edit the *buildspec.sh*

Command:

```
./buildspec.sh <ENV> <PIPELINE>
```

Example:

```
./buildspec.sh dev inference

```