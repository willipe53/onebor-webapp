#!/usr/bin/env bash
# download_all_lambdas.sh
# Iterate all Lambda functions in the account/region and dump their code into .py files

set -euo pipefail

REGION="us-east-2"   # change if needed

echo "Listing Lambda functions in $REGION ..."
FUNCTIONS=$(aws lambda list-functions --region "$REGION" --query 'Functions[].FunctionName' --output text)

for fn in $FUNCTIONS
do
    echo "==> Downloading $fn"
    url=$(aws lambda get-function \
            --function-name "$fn" \
            --region "$REGION" \
            --query 'Code.Location' \
            --output text)

    tmpzip=$(mktemp /tmp/lambda_zip.XXXXXX.zip)
    tmpdir=$(mktemp -d /tmp/lambda_unzip.XXXXXX)

    curl -s -L -o "$tmpzip" "$url"
    unzip -q "$tmpzip" -d "$tmpdir"

    # find first .py file
    pyfile=$(find "$tmpdir" -maxdepth 1 -name '*.py' | head -n1 || true)
    if [[ -n "$pyfile" ]]
    then
        cp "$pyfile" "./${fn}.py"
        echo "    Saved as ${fn}.py"
    else
        echo "    [WARN] No .py file found in $fn package (maybe multiple files or non-Python runtime)"
    fi

    rm -rf "$tmpzip" "$tmpdir"
done

echo "Done."
