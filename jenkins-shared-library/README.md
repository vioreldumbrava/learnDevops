# Jenkins Shared Library (lab 43)

Reusable pipeline steps for the Dojo's Jenkins pipelines. In real teams this lives in its
**own git repository** so many services can share one build vocabulary; here it lives in a
subfolder and Jenkins loads it via the *Library Path* setting (see
[labs/43-jenkins-shared-library](../labs/43-jenkins-shared-library/)).

Layout (fixed by convention — Jenkins looks for these exact folders):

```
jenkins-shared-library/
└── vars/                 # each file = one global step, named after the file
    ├── buildImage.groovy         # buildImage(name, context, tag)
    ├── scanImage.groovy          # scanImage(image) — Trivy report
    ├── bumpPatchVersion.groovy   # VERSION x.y.z → x.y.(z+1), returns new value
    ├── ciSkipRequested.groovy    # true if last commit message contains [ci skip]
    └── commitVersionBump.groovy  # commit VERSION with [ci skip] and push
```

A `src/` folder (Groovy classes under a package) and `resources/` (files for
`libraryResource`) are the other two conventional roots — not needed at this size.
