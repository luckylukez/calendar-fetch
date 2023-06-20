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


# from google.cloud import storage
# from oauth2client.service_account import ServiceAccountCredentials
# import os

# os.environ['BACKUP_CLIENT_ID'] = '117900820865845195625'
# os.environ['BACKUP_CLIENT_EMAIL'] = 'eventor-calendar@appspot.gserviceaccount.com'
# os.environ['BACKUP_PRIVATE_KEY_ID'] = '117900820865845195625'
# os.environ['BACKUP_PRIVATE_KEY'] = '17875f68ed560281ec793585f95cba3519519ad6'


# credentials_dict = {
#     'type': 'service_account',
#     'client_id': os.environ['BACKUP_CLIENT_ID'],
#     'client_email': os.environ['BACKUP_CLIENT_EMAIL'],
#     'private_key_id': os.environ['BACKUP_PRIVATE_KEY_ID'],
#     'private_key': os.environ['BACKUP_PRIVATE_KEY'],
# }
# credentials = ServiceAccountCredentials.from_json_keyfile_dict(
#     credentials_dict
# )


# bucket_name = 'latest_calendar'
# file_name = 'latest_calendar.ics'
# project_name = 'eventor-calendar'

# client = storage.Client(credentials=credentials, project=project_name)
# bucket = client.get_bucket(bucket_name)
# blob = bucket.blob(file_name)
# blob.upload_from_filename(file_name)