#!/bin/zsh
aws s3 sync . s3://onebor-web-root \
  --exclude "*" --include "index.html" --include "favicon.ico" --include "oneborlogo.png"
aws cloudfront create-invalidation --distribution-id="EPZLOBGCZS220" --profile onebor --paths "/*"