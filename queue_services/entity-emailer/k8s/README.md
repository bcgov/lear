## Build the pipeline


1. **Setup parameters** Alter, or copy the _pipeline.param_ updating the values for your pipeline.
2. **Create the pipeline** process the template referencing your parameter file.

```bash 
oc process -f templates/pipeline.json -p pipeline.param  | oc create -f -
```