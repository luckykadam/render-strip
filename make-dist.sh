if [ -z "$1" ]
  then
    echo "No argument supplied. Usage: ./make-dist v1.0"
    exit 1
fi

echo "preparing release $1"

addon_zip="Render Strip $1 - Do not unzip!.zip"
mkdir render-strip
cp *.py render-strip
zip -r "$addon_zip" render-strip -x '*/.git/*' -x '*/.DS_Store/*' -x '*/__pycache__/*'