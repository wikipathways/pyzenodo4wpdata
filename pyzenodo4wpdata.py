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
file_name, file_ext = os.path.splitext(fn)
parts = file_name.split("-")
pre_title = "XXX for "
if file_ext == ".gmt":
    pre_title = "GMT file for "
elif file_ext == ".zip":
    pre_title = "GPML files for "
this_title = pre_title + parts[-1].replace("_"," ") + " pathways"
release = int(args.release)
year = str(release // 10000)
month = str((release // 100) % 100).zfill(2)
day = str(release % 100).zfill(2)
pubdate = f"{year}-{month}-{day}"
data['metadata']['title'] = this_title
data['metadata']['version'] = args.release
data['metadata']['publication_date'] = pubdate
#print(json.dumps(data))

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
try:
    r = requests.get(f"{baseurl}/records",
                    params={'communities':'wikipathways',
                    'size':100,
                    'all_versions':0,
                    'access_token': f"{args.token}"})
    title_id_dict = {}
    try:
        for obj in r.json()['hits']['hits']:
            if "id" in obj and "metadata" in obj:
                title_id_dict[obj["metadata"]["title"]] = obj["id"]
    except (json.JSONDecodeError, KeyError) as e:
        print(f"\nWarning: Could not process Zenodo records for {fn}, continuing with new upload...")
        title_id_dict = {}  # Reset to empty dict to force new upload
except requests.exceptions.RequestException as e:
    print(f"\nWarning: Could not connect to Zenodo for {fn}, continuing with new upload...")
    title_id_dict = {}  # Reset to empty dict to force new upload

print(f"\nTitle-ID mappings: {title_id_dict}")
#if args.debug:
    #print(f"\nID-Bucket mappings: {id_bucket_dict}")

# If existing deposition, then create new version
# If not, then create a project
deposition_id = ""
for key in title_id_dict:
    if this_title in key:
        deposition_id=title_id_dict[key]
        #bucket_link=id_bucket_dict[deposition_id] #Not used and no longer provided by Zenodo API

if deposition_id:
    print(f"\nFound earlier version of {this_title}. Creating a new version of {deposition_id}.")
    if not args.debug:
        try:
            # POST request to create new version
            r = requests.post(f"{baseurl}/deposit/depositions/{deposition_id}/actions/newversion",
                      params=params)
            print(r.status_code)
            print(json.dumps(r.json(), indent=2))
            
            if r.status_code == 400 and "Please remove all files first" in str(r.json()):
                print("\nRemoving existing files before creating new version...")
                # First get the current version to find files
                r = requests.get(f"{baseurl}/deposit/depositions/{deposition_id}",
                          params=params)
                if r.status_code == 200:
                    files = r.json().get('files', [])
                    for file in files:
                        file_id = file.get('id')
                        if file_id:
                            print(f"Removing file {file_id}")
                            r = requests.delete(f"{baseurl}/deposit/depositions/{deposition_id}/files/{file_id}",
                                        params=params)
                            print(f"Delete status: {r.status_code}")
                    
                    # Now try creating new version again
                    r = requests.post(f"{baseurl}/deposit/depositions/{deposition_id}/actions/newversion",
                              params=params)
                    print(f"New version creation status: {r.status_code}")
                    print(json.dumps(r.json(), indent=2))
            
            if r.status_code != 201:  # 201 is success for new version creation
                print(f"Error creating new version: {r.status_code}")
                print("Falling back to creating new deposition...")
                deposition_id = ""  # Reset to create new deposition
            else:
                deposition_id = r.json()['links']['latest_draft'].split("/")[-1]
                bucket_link = r.json()['links']['bucket']
                
        except (KeyError, json.JSONDecodeError) as e:
            print(f"Error processing new version response: {str(e)}")
            print("Falling back to creating new deposition...")
            deposition_id = ""  # Reset to create new deposition
        except requests.exceptions.RequestException as e:
            print(f"Error in API request: {str(e)}")
            print("Falling back to creating new deposition...")
            deposition_id = ""  # Reset to create new deposition

if not deposition_id:
    print(f"\nCreating a new project.")
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