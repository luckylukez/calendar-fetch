import os
from google.cloud import storage
import json
import pytz
import xml.etree.cElementTree as ET
from datetime import date, timedelta, time
import requests
from requests import HTTPError
from dateutil import parser
import pytz
from icalendar import Calendar, Event, vDatetime

timezone = pytz.timezone('Europe/Stockholm')

config = {
        'General': {
            'name': 'Rigor IF'
        },
        'Messages': {
            'user_created': 'Skapade framgångsrikt ny användare på {Wordpress:url}',
            'wrong_api_key': 'API-nyckeln fanns inte med eller är felaktig.',
            'eventor_fail': 'Kommunikationen med Eventor fungerar inte för tillfället, försök igen senare.',
            'eventor_validation_fail': 'Misslyckades att validera användare på Eventor. Kontrollera att användarnamn och lösenord är korrekt.',
            'failed_create_user': 'Misslyckades att skapa användare.',
            'not_in_club': 'Du finns inte registrerad som medlem i {General:name} på Eventor',
            'already_registered': 'Det finns redan en användare på {Wordpress:url} som är kopplat till denna Eventor-inloggning. <a href="{Wordpress:lost_password_dir}">Om du har glömt lösenord kan du återställa det här.</a>',
            'wp_fail': 'Ett fel inträffade i kommunikationen med {Wordpress:url}. Försök vid ett senare tillfälle.',
            'user_attr_exists': 'Det finns redan en användare på {Wordpress:url} med angivet användarnamn.',
            'request_bug': 'Method must be either GET or POST. Please report this error to the administrator.',
            'io_error': 'Fel inträffade vid skrivning till fil. Försök igen vid ett senare tillfälle.',
            'file_creation_error': 'Ett fel inträffade när filen skapades. Försök igen vid ett senare tillfälle.',
            'eventor_import': 'Denna aktivitet är importerad från Eventor.',
            'idrottonline_import': 'Denna aktivitet är importerad från IdrottOnline.',
            'original_ref': 'För info, se'
        },
        'Calendar': {
            'target_feed': '.', #'https://{Wordpress:url}/?plugin=all-in-one-event-calendar&controller=ai1ec_exporter_controller&action=export_events',
            'filename': 'latest_calendar.ics',
            'district_event_class_ids': '1,2,3,4,6',
            'club_event_class_ids': '5',
            'cancelled_status_id': '10'
        },
        'EventorApi': {
            'apikey': os.environ.get('EVENTOR_API_KEY'),
            'base_url': 'eventor.orientering.se',
            'members_endpoint': 'https://eventor.orientering.se/api/persons/organisations/',
            'authenticate_endpoint': 'https://eventor.orientering.se/api/authenticatePerson',
            'activities_endpoint': 'https://eventor.orientering.se/api/activities',
            'events_endpoint': 'https://eventor.orientering.se/api/events',
            'organisation_endpoint': 'https://eventor.orientering.se/api/organisation/',
            'event_base_url': 'https://eventor.orientering.se/Events/Show/',
            'lost_password_url': 'https://eventor.orientering.se/Home/ForgotPassword',
            'organisation_id': os.environ.get('EVENTOR_ORG_ID'),
            'district_id': 'your_district_id'
        },
        'Time': {
            'timezone': 'Europe/Stockholm'

        },
        # Eventor's classification of events
        'EventClassification': {
            'Mästerskapstävling':1,
            'Nationell tävling':2,
            'Distriktstävling':3,
            'Närtävling':4,
            'Klubbtävling':5,
            'Internationell tävling':6
        },

        'Google': {
            'BucketName' : 'latest_calendar'
        }
    }

def main(): # main(request):
    # In cloud functions this is done manually during deployment
    from set_environment_variables import set_env_vars
    set_env_vars() 

    update_calendar_endpoint()
    #return update_calendar_endpoint()


def update_calendar_endpoint():
    days_in_advance = 100
    generate_calendarfeed(days_in_advance)
    #return generate_calendarfeed(days_in_advance)


def generate_calendarfeed(days_in_advance: int):
    calendar = Calendar()
    calendar['method'] = 'REQUEST'
    calendar['prodid'] = '-//Svenska Orienteringsförbundet//' + config['General']['name']
    calendar['version'] = '2.0'

    start = date.today()
    end = start + timedelta(days=days_in_advance)

    # Fetch club activities
    activities_root = club_activities(start, end)
    add_activities(activities_root, calendar)

    # Fetch district events
    if config['Calendar']['district_event_class_ids'].rstrip() != '':
        districts_events_root = events(start, end, config['Calendar']['district_event_class_ids'].split(','),
                                                    [config['EventorApi']['district_id']])
        add_events(districts_events_root, calendar)

    # Fetch club events
    if config['Calendar']['club_event_class_ids'].rstrip() != '':
        club_events_root = events(start, end, config['Calendar']['club_event_class_ids'].split(','),
                                                [config['EventorApi']['organisation_id']])
        add_events(club_events_root, calendar)

    # Upload .ical file to google cloud bucket
    upload_to_bucket(calendar.to_ical())

    print('Calendarfeed successfully generated for next {} days'.format(days_in_advance))
    return 'Calendarfeed successfully generated for next {} days'.format(days_in_advance)



def club_activities(start_date: date, end_date: date):
    query_params = {'from': start_date.strftime('%Y-%m-%d'),
                    'to': end_date.strftime('%Y-%m-%d'),
                    'organisationId': config['EventorApi']['organisation_id']}

    headers = {'ApiKey': config['EventorApi']['apikey']}
    xml_str = eventor_request('GET', config['EventorApi']['activities_endpoint'], query_params, headers).text
    return ET.fromstring(xml_str)


def events(start_date: date, end_date: date, classification_ids: list, organisations_ids: list):
    query_params = {'fromDate': start_date.strftime('%Y-%m-%d'),
                    'toDate': end_date.strftime('%Y-%m-%d'),
                    'classificationIds': ','.join(map(str, classification_ids)),
                    'organisationIds': ','.join(map(str, organisations_ids))
                    }

    headers = {'ApiKey': config['EventorApi']['apikey']}
    xml_str = eventor_request('GET', config['EventorApi']['events_endpoint'], query_params, headers).text
    return ET.fromstring(xml_str)
    

def add_events(root, calendar: Calendar):
    for event in root:
        try:
            cal_event = Event()

            name = event.find('Name').text
            if is_cancelled(event):
                name = '[INSTÄLLD] ' + name

            org_id = event.find('Organiser').find('OrganisationId').text
            org_name = org_name(o)
            cal_event['summary'] = '{}, {}'.format(name, org_name)

            startdate_str = event.find('StartDate').find('Date').text
            starttime_str = event.find('StartDate').find('Clock').text
            startdatetime = parser.parse(startdate_str + ' ' + starttime_str)
            startdatetime = timezone.localize(startdatetime)

            enddate_str = event.find('FinishDate').find('Date').text
            endtime_str = event.find('FinishDate').find('Clock').text
            enddatetime = parser.parse(enddate_str + ' ' + endtime_str)
            enddatetime = timezone.localize(enddatetime)

            if startdatetime == enddatetime:
                if startdatetime.time() == time(0, 0, 0, tzinfo=timezone):
                    enddatetime = startdatetime + timedelta(days=1)
                else:
                    enddatetime = startdatetime + timedelta(hours=3)

            elif startdatetime.date() != enddatetime.date() and enddatetime.time() == time(0, 0, 0, tzinfo=timezone):
                enddatetime += timedelta(days=1)

            cal_event.add('dtstart', startdatetime)

            cal_event.add('dtend', enddatetime)

            classification = config['EventClassification'][str(event.find('EventClassificationId').text)]
            cal_event['categories'] = ','.join(['Eventor', classification])

            url = config['EventorApi']['event_base_url'] + '/' + event.find('EventId').text
            cal_event['url'] = url

            cal_event['description'] = config['Messages']['eventor_import'] + ' ' + config['Messages'][
                'original_ref'] + ' ' + url

            cal_event['uid'] = 'Event_' + event.find('EventId').text + '@' + config['EventorApi']['base_url']

            calendar.add_component(cal_event)
        except RuntimeError as err:
            continue


def add_activities(root, calendar: Calendar):
    for activity in root:
        try:
            attributes = activity.attrib
            cal_event = Event()

            cal_event['summary'] = '{} [{} anmälda]'.format(activity.find('Name').text, attributes['registrationCount'])

            if 'startTime' not in attributes:
                continue

            starttime = parser.parse(attributes['startTime'])
            starttime = starttime.astimezone(timezone)
            cal_event['dtstart'] = vDatetime(starttime).to_ical()

            if starttime.time() == time(0, 0, 0):
                endtime = starttime + timedelta(days=1)
            else:
                endtime = starttime + timedelta(hours=3)
            cal_event['dtend'] = vDatetime(endtime).to_ical()

            cal_event['categories'] = ','.join(['Eventor', 'Klubbaktivitet'])

            cal_event['description'] = config['Messages']['eventor_import'] + ' ' + config['Messages'][
                'original_ref'] + ' ' + attributes['url']

            cal_event['url'] = attributes['url']

            cal_event['uid'] = 'Activity_' + attributes['id'] + '@' + config['EventorApi']['base_url']

            calendar.add_component(cal_event)
        except RuntimeError as err:
            continue


def upload_to_bucket(content):
    # try:

    # Authenticate ourselves using the service account private key
    try:
        private_key_string = os.environ['GOOGLE_SERVICE_KEY']
    except: raise Exception('exception 1 in upload_to_bucket()')
    try:
        private_key_dict = json.loads(private_key_string)
    except: raise Exception('exception 2 in upload_to_bucket()')
    try:
        client = storage.Client.from_service_account_info(private_key_dict)
    except: raise Exception('exception 3 in upload_to_bucket()')
    try:
        bucket = storage.Bucket(client, config['Google']['BucketName'])
    except: raise Exception('exception 4 in upload_to_bucket()')
    try:
    # Name of the file on the GCS once uploaded
        blob = bucket.blob(config['Calendar']['filename'])
    except: raise Exception('exception 5 in upload_to_bucket()')
    try:
    # Path of the local file
        blob.upload_from_string(content)
    except: raise Exception('exception 6 in upload_to_bucket()')

    # except:
    #     raise Exception('Unable to upload calendar to bucket')


def eventor_request(method, api_endpoint, query_params: dict = None, headers: dict = None, success_codes=(200,)):
    return api_request(method, api_endpoint, config['Messages']['eventor_fail'], 'eventor', query_params, headers,
                       success_codes)


def api_request(method, api_endpoint, error_message, error_category,  query_params=None, headers=None,
                success_codes=(200,)):
    try:
        if method == 'GET':
            r = requests.get(url=api_endpoint, params=query_params, headers=headers)
        elif method == 'POST':
            r = requests.post(url=api_endpoint, params=query_params, headers=headers)
        else:
            raise Exception(config['Messages']['request_bug'])
        if r.status_code not in success_codes:
            raise KnownError(error_message, error_category)
    except HTTPError:
        raise KnownError(error_message, error_category)

    r.encoding = 'utf-8'
    return r


def is_cancelled(event):
    if 'EventStatusId' in [t.tag for t in event.iter()]:
        return event.find('EventStatusId').text == config['Calendar']['cancelled_status_id']
    return False


def org_name(org_id: int):
    headers = {'ApiKey': config['EventorApi']['apikey']}
    xml_str = eventor_request('GET', config['EventorApi']['organisation_endpoint'] + '/' + org_id, headers=headers).text
    root = ET.fromstring(xml_str)
    return root.find('Name').text


# common.py
class KnownError(Exception):
    def __init__(self, message, error_type=None):
        self.message = message
        self.error_type = error_type

    def __str__(self):
        return self.message


if __name__ == '__main__':
    main()