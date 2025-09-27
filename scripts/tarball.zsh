#!/bin/zsh

cd ..

echo " --> usage: tarball.py 0890b380bec2879c3b037d6679a29e39fd05315d"

commit="$1"
if [ "$1" = "" ]; then exit 1; fi

tag_name="${commit:0:5}"
dir_name="/Users/willipe/github/${tag_name}/"

if [ -d "$dir_name" ]; then
  rm -rf "$dir_name"
fi

mkdir "$dir_name"

echo "Creating tarball at ${dir_name} from ${commit}"

cmd="/usr/bin/git tag -a ${tag_name} -m ${tag_name} ${commit}"

eval $cmd

cmd="/usr/bin/git archive ${tag_name} | tar -x -C ${dir_name}"

eval $cmd

cd $dir_name

npm install


# subprocess.call(["git tag -a", tag_name, "-m", tag_name, commit])
# subprocess.call(["git archive " + tag_name + " | tar -x -C " + dir_name + "/"])


# aws cloudfront create-invalidation --distribution-id="E3SJ64HEFXXBIO" --paths "/$base/*" 
# dt="$(date "+%s000")" 
# var="final DateTime buildDate = DateTime.fromMillisecondsSinceEpoch(($dt));"
# echo "$var" > lib/build_date.dart
# rm -rf build/web/*.dart.js
# flutter build web --base-href "/$base/" --pwa-strategy=none
# mv build/web/main.dart.js build/web/$dt.main.dart.js
# sed "s/main.dart.js/$dt.main.dart.js/g" build/web/index.html >build/web/newindex.html
# mv build/web/newindex.html build/web/index.html
# aws s3 rm s3://ditchnavigation-website/$base/ --recursive --only-show-errors
# aws s3 cp build/web s3://ditchnavigation-website/$base/ --recursive --no-progress --only-show-errors

