---
name: Maintenance Request
about: Identify areas of the code that need maintenance or updates.
title: 'update(scope of problem): basic description'
labels: ['update', 'maintenance']
assignees: k8redfern
type: maintenance

---

**Issue Title**
A title template is provided, but please see the commit subject line guidance from our [contribution guidelines](https://brainhealthlabstfx.github.io/AnalysisMultiverse/contributing_wrapper.html#subject-line) for more details.

**Location**
A description of which lines of code require maintenance. 
Be as specific as possible.
> e.g.
> run_multiverse.py: lines 28 - 34
> multiverse.py: throughout

**Specify**
What exactly needs to be updated?
> e.g.
> Import
> Function Call

**Reason**
Why does this need to be updated or maintained?
> e.g. 
> The Singularity module has been renamed to Apptainer. 
> subprocess.call() has been replaced by subprocess.run()

**Additional Context**
Add any other context about the maintenance request here.