## Build the pipeline


1. **Setup parameters** Alter, or copy the _legal-api-build-pipeline.param_ updating the values for your pipeline.
2. **Create the pipeline** process the template referencing your parameter file.

```bash 
oc process -f templates/legal-api-pipeline.json -p legal-api-build-pipeline.param  | oc create -f -
```