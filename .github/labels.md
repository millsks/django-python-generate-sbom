# Repository Labels

The [Label Management workflow](workflows/labeler.yml) applies these labels
automatically. They must exist in the repo first — GitHub does not create a
label on demand. Run this one-time bootstrap once (idempotent via `--force`):

```sh
# Path / component labels (actions/labeler + .github/labeler.yml)
gh label create backend       -c "#0052CC" -d "Backend (Django/DRF/Celery) changes"        --force
gh label create frontend      -c "#5319E7" -d "Frontend (React/MUI/Vite) changes"          --force
gh label create docker        -c "#0DB7ED" -d "Docker / compose changes"                   --force
gh label create ci            -c "#FBCA04" -d "CI / GitHub workflow changes"               --force
gh label create documentation -c "#0075CA" -d "Documentation changes"                      --force
gh label create dependencies  -c "#B60205" -d "Dependency / lockfile changes"             --force

# Keyword labels for issues (github/issue-labeler + .github/issue-labeler.yml)
gh label create bug           -c "#D73A4A" -d "Something isn't working"                     --force
gh label create enhancement   -c "#A2EEEF" -d "New feature or request"                      --force
gh label create question      -c "#D876E3" -d "Further information is requested"            --force

# PR size labels (codelytv/pr-size-labeler)
gh label create size/xs       -c "#3CBF00" -d "Extra small PR (< 10 lines)"                 --force
gh label create size/s        -c "#5D9801" -d "Small PR (< 100 lines)"                      --force
gh label create size/m        -c "#7F7203" -d "Medium PR (< 500 lines)"                     --force
gh label create size/l        -c "#A14C05" -d "Large PR (< 1000 lines)"                     --force
gh label create size/xl       -c "#C32607" -d "Extra large PR (>= 1000 lines)"              --force
```
