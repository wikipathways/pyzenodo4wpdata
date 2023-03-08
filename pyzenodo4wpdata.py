import argparse
import json
import requests
import os

# Define the command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("token", help="the Zenodo access token")
parser.add_argument("meta", help="the metadata file")
parser.add_argument("release", help="the release date")
parser.add_argument("file", help="the file to upload")
parser.add_argument("-s", "--use-sandbox", action="store_true", help="whether to use sandox for testing")
parser.add_argument("-d", "--debug", action="store_true", help="whether to test run without actually uploading")
parser.add_argument("-n", "--no-publish", action="store_true", help="whether to skip the publishing step")

# Parse the command line arguments
args = parser.parse_args()

# Update metadata
with open(args.meta, 'r') as f:
    data = json.load(f)
fn = os.path.basename(args.file)
release = int(args.release)
year = str(release // 10000)
month = str((release // 100) % 100).zfill(2)
day = str(release % 100).zfill(2)
pubdate = f"{year}-{month}-{day}"
data['metadata']['title'] = fn
data['metadata']['version'] = args.release
data['metadata']['publication_date'] = pubdate
#print(json.dumps(data))

# extract query from filename
timestamp_start = fn.find("-") + 1
timestamp_end = fn.find("-", timestamp_start)
extension_start = fn.rfind(".") + 1
fnquery = fn[timestamp_end:extension_start]

# api baseurl
baseurl = f"https://zenodo.org/api"
if args.use_sandbox:
    baseurl = f"https://sandbox.zenodo.org/api"

# header data attached to request
headers = {"Content-Type": "application/json"}

# parameters attached to uploads
params = {'access_token': f"{args.token}"}

# TEST token - FOR DEBUG
if args.debug:
    r = requests.get(f"{baseurl}/deposit/depositions",
                  params=params)
    print(f"\nDEBUG: status code: {r.status_code}.")

# GET request to query for deposition of earlier versions
r = requests.get(f"{baseurl}/records",
                        params={'communities':'wikipathways',
                        'size':100,
                        'all_versions':0,
                        'access_token': f"{args.token}"})
if args.debug:
    print(f"\nPrinting first hit only: {json.dumps(list(r.json()['hits']['hits'])[0], indent=2)}")
title_id_dict = {}
id_bucket_dict = {}
for obj in r.json()['hits']['hits']:
    if "id" in obj and "metadata" in obj:
        title_id_dict[obj["metadata"]["title"]] = obj["id"]
    if "id" in obj and "links" in obj:
        id_bucket_dict[obj["id"]] = obj["links"]['bucket']
print(f"\nTitle-ID mappings: {title_id_dict}")
if args.debug:
    print(f"\nID-Bucket mappings: {id_bucket_dict}")

# If existing deposition, then create new version
# If not, then create a project
deposition_id = ""
for key in title_id_dict:
    if fnquery in key:
        deposition_id=title_id_dict[key]
        bucket_link=id_bucket_dict[deposition_id]

if deposition_id:
    print(f"\nFound earlier version of {fnquery}. Creating a new version of {deposition_id}.")
    if not args.debug:
        # POST request to create new version
        r = requests.post(f"{baseurl}/deposit/depositions/{deposition_id}/actions/newversion",
                  params=params)
        print(r.status_code)
        print(json.dumps(r.json(), indent=2))

        deposition_id = r.json()['links']['latest_draft'].split("/")[-1]
        bucket_link = r.json()['links']['bucket'] #should be the same as before
        prior_version_file = r.json()['files'][0]['id'] 

        print(f"\nDeleting prior version of file {prior_version_file}.")
        # DELETE request to clear out prior version file from this new version
        r = requests.delete(f"{baseurl}/deposit/depositions/{deposition_id}/files/{prior_version_file}",
                    params=params)
        print(r.status_code)
else:
    print(f"\nNo earlier version found. Creating a new project.")
    if not args.debug:
        # POST request to create project
        r = requests.post(f"{baseurl}/deposit/depositions", 
                  headers=headers, 
                  params=params,
                  data=json.dumps({}))
        print(r.status_code)
        print(json.dumps(r.json(), indent=2))

        deposition_id = r.json()['id']
        bucket_link = r.json()['links']['bucket']

if args.debug: 
    print(f"\nDEBUG: Would upload these metadata: {json.dumps(data, indent=2)}.")
else:
    print(f"\nUpdating metadata for deposition {deposition_id}.")
    # PUT request to change metadata
    r = requests.put(f"{baseurl}/deposit/depositions/{deposition_id}", 
                 headers=headers,  
                 params=params,
                 data=json.dumps(data))
    print(r.status_code)
    print(json.dumps(r.json(), indent=2))

if args.debug: 
    print(f"\nDEBUG: Would upload this file: {args.file}.")
else:
    print(f"\nUploading file for deposition {deposition_id}.")
    # POST request to upload file
    r = requests.post(f"{baseurl}/deposit/depositions/{deposition_id}/files",
                  params=params, 
                  data={'name': f"{fn}"}, 
                  files={'file': open(f"{args.file}", 'rb')})
    print(r.status_code)
    print(json.dumps(r.json(), indent=2))

if args.debug: 
    print(f"\nDEBUG: Would publish deposition {deposition_id}.\n")
elif args.no_publish:
    print(f"\nNOTE: Deposition {deposition_id} has not been published.\n")
else:
    print(f"\nPublishing deposition {deposition_id}.\n")
    # POST request to publish deposition
    r = requests.post(f"{baseurl}/deposit/depositions/{deposition_id}/actions/publish",
                  params=params)
    print(r.status_code)
    print(json.dumps(r.json(), indent=2))
