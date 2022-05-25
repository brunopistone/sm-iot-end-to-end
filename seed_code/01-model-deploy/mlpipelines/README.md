## Pipelines folder

This folder contains the ML pipelines developed

### build.sh

This script allows the creation of a packaged file for a specific pipeline

* ENV: Mandatory - environment related to the .yml file with the configurations
* PIPELINE: Mandatory - name of the pipeline you want to build

```
./build.sh <ENV> <PIPELINE>
```

Examples:

Training

```
./build.sh dev training
```

Inference

```
./build.sh dev inference
```