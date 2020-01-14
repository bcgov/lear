## Build the pipeline


1. **Setup parameters** Alter, or copy the _data-reset-tool-build-pipeline.param_ updating the values for your pipeline.
2. **Create the pipeline** process the template referencing your parameter file.

```bash 
oc process -f templates/data-reset-tool-pipeline.json -p data-reset-tool-build-pipeline.param  | oc create -f -
```