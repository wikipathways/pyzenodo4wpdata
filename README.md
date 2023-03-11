# pyzenodo4wpdata
A pyzenodo library for archiving versions of WikiPathways data files

## Usage
See the example shell script `monthly-depo.sh`, which is specific to archiving GMT and GPML files from data.wikipathways.org. In general, the script details the expected files and variables. In addition, there are some options flags:
 * -s -- Use Zenodo sandbox. _Note: this didn't really work in my hands_
 * -d -- Debug mode. Nothing will actually be uploaded to Zenodo, but most of the code will be run.
 * -n -- No publish. Do everything except publish. This final step can easily be done on the GUI, if you're only testing or unsure.

Note: there is a 100/minute rate limit for the Zenodo REST API requests.

 ## Access Token
 You will need a Zenodo access token to run the Zenodo API steps in this script:
  * [Create an access token](https://zenodo.org/account/settings/applications/tokens/new/)
  * Required scopes: deposit:actions, deposite:write
  * Add this to a local .env file relative to shell script or use a GH Action Secret.

## Design
This pyzenodo library is specifically designed to integrate into bash or GH Action scripts where pertinent files and variables are passed to lib for each upload.

The python script will update a metadata template, check to see if the file-to-upload is novel or a new version of existing file, and then perform the upload and publishing.

These aspects of the script are really specific to WikiPathways data files:
 * Release dates of the format `YYYYMMDD` are assumed
 * Data filenames with the pattern: xxx-xxx-type-species.xxx are assumed (see ~line 33)
 * Only the files in the WikiPathways community collection at Zenodo are checked (see ~line 58)

 With a bit of careful work, this script could be adapted to other use cases. See [Zenodo REST API docs](https://developers.zenodo.org/#rest-api).
