
source .env #for $ZENODO_TOKEN

RELEASE=20160610

url="https://wikipathways-data.wmcloud.org/$RELEASE/gmt"

rm -fr data_files
mkdir -p data_files
wget -r -np -nH --cut-dirs=2 --no-parent -A 'gmt,*gpml*' -P data_files "$url"

for f in data_files/*.(gmt|zip)
do
  if [ -f "$f" ]
  then
    echo "$f"
    python pyzenodo4wpdata.py $ZENODO_TOKEN meta-template.json $RELEASE $f -d
    sleep 1
  fi
done