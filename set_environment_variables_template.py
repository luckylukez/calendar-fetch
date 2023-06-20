import os
import json

def set_env_vars():
    os.environ['EVENTOR_ORG_ID'] = ''
    os.environ['EVENTOR_API_KEY'] = ''

    # Copy contents of service account key json file into this variable
    google_service_key = {}
    # convert json to a string. Converted back in cloud_upload.
    google_service_key = json.dumps(google_service_key)
    os.environ['GOOGLE_SERVICE_KEY'] = google_service_key


if __name__ == '__main__':
    set_env_vars()