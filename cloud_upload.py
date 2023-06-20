from google.cloud import storage
import os
import json

def upload_to_bucket(content):
    # Authenticate ourselves using the service account private key
    private_key_string = os.environ['GOOGLE_SERVICE_KEY']
    private_key_dict = json.loads(private_key_string)
    client = storage.Client.from_service_account_info(private_key_dict)

    bucket = storage.Bucket(client, 'latest_calendar')
    # Name of the file on the GCS once uploaded
    blob = bucket.blob('latest_calendar.ics')
    # Path of the local file
    blob.upload_from_string(content)
