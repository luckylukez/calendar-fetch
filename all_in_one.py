import functions_framework

#########################################################################################################################

import functions_framework
import os
from set_environment_variables import set_env_vars


def update_calendar_endpoint():
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
        }
    }

    days_in_advance = 100
    generate_calendarfeed(days_in_advance, config, 'latest_calendar')

@functions_framework.http
def main():
    
    set_env_vars()
    update_calendar_endpoint()



#########################################################################################################################
#calendarfeeds.py

import json
import logging
import os
from datetime import date, timedelta, time

import requests
from dateutil import parser
import pytz
from flask import Blueprint, make_response, request, jsonify
from icalendar import Calendar, Event, vDatetime
from icalendar.prop import vCategory, vText

calendarfeeds_app = Blueprint('calendarfeeds', __name__)

timezone = pytz.timezone('Europe/Stockholm')


def add_activities(root, calendar: Calendar, config):
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
            logging.warning(err)
            continue


def is_cancelled(event):
    if 'EventStatusId' in [t.tag for t in event.iter()]:
        return event.find('EventStatusId').text == config['Calendar']['cancelled_status_id']
    return False


def add_events(root, calendar: Calendar, config):
    for event in root:
        try:
            cal_event = Event()

            name = event.find('Name').text
            if is_cancelled(event):
                name = '[INSTÄLLD] ' + name

            org_id = event.find('Organiser').find('OrganisationId').text
            org_name = eventor_utils.org_name(org_id)
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
            logging.warning(err)
            continue


def add_idrottonline_feeds(calendar: Calendar):
    try:
        with open(ROOT_DIR + '/idrottonline_feeds.json', "r") as json_file:
            data = json.load(json_file)

        for feed in data:
            feed_calendar = Calendar.from_ical(requests.get(feed['url']).text)
            calendar_name = vText.from_ical(feed_calendar['X-WR-CALNAME'])
            for component in feed_calendar.subcomponents:
                if 'categories' in component:
                    old_categories = [vCategory.from_ical(c)[0] for c in component['categories'].cats if
                                      vCategory.from_ical(c)[0] != '"']
                    new_categories = feed['categories'] + old_categories
                    component['categories'] = ','.join(new_categories)
                else:
                    component['categories'] = ','.join(feed_calendar['categories'])

                idrottonline_id = vText.from_ical(component['UID']).split('Activity')[1].split('@')[0]

                if 'description' in component:
                    description = vText.from_ical(component['description'])
                    description = description.replace('[', '<').replace(']', '>')
                else:
                    description = ''
                component['description'] = description + config['Messages']['eventor_import']
                if 'base_url' in feed and feed['base_url'] != '':
                    url = feed['base_url'] + '/' + calendar_name + '?calendarEventId=' + idrottonline_id
                    component['url'] = url
                    component['description'] = component['description'] + ' ' + config['Messages'][
                        'original_ref'] + ' ' + url

                calendar.add_component(component)
    except IOError as e:
        logging.info(e)
        return


def generate_calendarfeed(days_in_advance: int, config, bucket_name):
    logging.info('Trying to create calendar feed')
    calendar = Calendar()
    calendar['method'] = 'REQUEST'
    calendar['prodid'] = '-//Svenska Orienteringsförbundet//' + config['General']['name']
    calendar['version'] = '2.0'

    start = date.today()
    end = start + timedelta(days=days_in_advance)

    # Fetch club activities
    activities_root = club_activities(start, end, config)
    add_activities(activities_root, calendar, config)

    # Fetch district events
    if config['Calendar']['district_event_class_ids'].rstrip() != '':
        districts_events_root = events(start, end, config['Calendar']['district_event_class_ids'].split(','),
                                                    [config['EventorApi']['district_id']], config)
        add_events(districts_events_root, calendar, config)

    # Fetch club events
    if config['Calendar']['club_event_class_ids'].rstrip() != '':
        club_events_root = events(start, end, config['Calendar']['club_event_class_ids'].split(','),
                                                [config['EventorApi']['organisation_id']], config)
        add_events(club_events_root, calendar, config)

    # Add feeds from other webcals
    add_idrottonline_feeds(calendar)

    # f = open('./' + config['Calendar']['filename'], 'wb')
    # f.write(calendar.to_ical())
    # f.close()
    # logging.info('Calendar feed created')

    upload_to_bucket(calendar.to_ical())

    #return jsonify({'message': 'Calendarfeed successfully generated for next {} days'.format(days_in_advance)})
    print('Calendarfeed successfully generated for next {} days'.format(days_in_advance))

def overwrite_changed(calendar):
    if config['Calendar']['target_feed'].rstrip() == '':
        return
    target_feed = Calendar.from_ical(api_request('GET', config['Calendar']['target_feed'], '', '').text)

    target_dict = dict()
    for component in target_feed.subcomponents:
        if 'UID' in component and 'DESCRIPTION' in component:
            target_dict[component['UID']] = component['DESCRIPTION']

    for component in calendar.subcomponents:
        if 'UID' in component and component['UID'] in target_dict:
            component['DESCRIPTION'] = target_dict[component['UID']]


def fetch_calendarfeed():
    if not os.path.exists(config['Calendar']['filename']):
        logging.warning(f'Calendarfeed file {config["Calendar"]["filename"]} not generated')
        return jsonify({"message": "Calendarfeed not generated"}), 503

    latest_ics = ROOT_DIR + '/' + config['Calendar']['filename']
    with open(latest_ics, 'rb') as f:
        calendar = Calendar.from_ical(f.read())

    try:
        response = make_response(calendar.to_ical())
        response.headers["Content-Disposition"] = "attachment; filename=Events.ics"
        return response
    except IOError as e:
        logging.error(e)
        raise KnownError(config['Messages']['io_error'], 'eventor')


@calendarfeeds_app.route('/calendarfeed', methods=['GET'])
@calendarfeeds_app.route('/calendarfeed/<int:days_in_advance>', methods=['POST'])
def calendarfeed(days_in_advance: int = None):
    if request.method == 'POST':
        logging.info(f'Calendar POST request from {request.remote_addr}')
        if not check_api_key(request.headers):
            logging.warning('Wrong API key')
            return jsonify({"message": "ERROR: Unauthorized"}), 401
        if isinstance(days_in_advance, int):
            return generate_calendarfeed(days_in_advance)
        else:
            logging.warning('Days in advance misspecified')
            return jsonify('Specify how many days to generate feed for'), 400
    elif request.method == 'GET':
        logging.info(f'Calendar GET request from {request.remote_addr}')
        return fetch_calendarfeed()




#########################################################################################################################
#cloud_upload.py

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





#########################################################################################################################
# eventor_utils.py

import json
import xml.etree.cElementTree as ET
from datetime import date
import logging

from cache_to_disk import cache_to_disk

from request_handler import api_request
from common import KnownError

#organisation_id = config.getint('EventorApi', 'organisation_id')


def eventor_request(method, api_endpoint, config, query_params: dict = None, headers: dict = None, success_codes=(200,)):
    return api_request(method, api_endpoint, config['Messages']['eventor_fail'], 'eventor', config, query_params, headers,
                       success_codes)


def club_activities(start_date: date, end_date: date, config):
    query_params = {'from': start_date.strftime('%Y-%m-%d'),
                    'to': end_date.strftime('%Y-%m-%d'),
                    'organisationId': config['EventorApi']['organisation_id']}

    headers = {'ApiKey': config['EventorApi']['apikey']}
    xml_str = eventor_request('GET', config['EventorApi']['activities_endpoint'], config, query_params, headers).text
    logging.info(f'Fetched club activities between {start_date} and {end_date}')
    return ET.fromstring(xml_str)


def events(start_date: date, end_date: date, classification_ids: list, organisations_ids: list, config):
    query_params = {'fromDate': start_date.strftime('%Y-%m-%d'),
                    'toDate': end_date.strftime('%Y-%m-%d'),
                    'classificationIds': ','.join(map(str, classification_ids)),
                    'organisationIds': ','.join(map(str, organisations_ids))
                    }

    headers = {'ApiKey': config['EventorApi']['apikey']}
    xml_str = eventor_request('GET', config['EventorApi']['events_endpoint'], config, query_params, headers).text
    logging.info(f'Fetched events between {start_date} and {end_date}')
    return ET.fromstring(xml_str)


@cache_to_disk(100)
def org_name(org_id: int):
    headers = {'ApiKey': config['EventorApi']['apikey']}
    xml_str = eventor_request('GET', config['EventorApi']['organisation_endpoint'] + '/' + org_id, headers=headers).text
    root = ET.fromstring(xml_str)
    return root.find('Name').text


def extract_info(columns_dict: dict, person: ET.Element):
    person_info_dict = {column: '' for column in columns_dict.keys()}

    for column_name, column_dict in columns_dict.items():
        person_info_dict[column_name] = find_value(column_dict['path'], person)
        if 'length' in column_dict.keys():
            person_info_dict[column_name] = person_info_dict[column_name][:int(column_dict['length'])]

    return person_info_dict


def person_in_organisation(person_info, org_id: int):
    roles = person_info.findall('Role')
    for r in roles:
        role_org = r.find('OrganisationId')
        if role_org is not None and int(role_org.text) == org_id:
            return True
    return False


def fetch_members():
    api_endpoint = config['EventorApi']['members_endpoint'] + '/' + config['EventorApi']['organisation_id']
    query_params = {'includeContactDetails': 'true'}
    headers = {'ApiKey': config['EventorApi']['apikey']}
    xml_str = eventor_request('GET', api_endpoint, query_params=query_params, headers=headers).text
    logging.info('Fetched member records from Eventor')

    return ET.fromstring(xml_str)


def get_membership(person_info):
    organisation_id = person_info.find('OrganisationId')
    if organisation_id is not None and organisation_id.text != config['EventorApi']['organisation_id']:
        return config['Wordpress']['guest_member']
    return config['Wordpress']['member']


def find_value(path: list, person: ET.Element):
    element = person
    element_path = path[0]
    for child in element_path:
        element = element.find(child)
        if element is None:
            return ''

    if len(path) == 1:
        return element.text

    values = [value for key, value in element.attrib.items() if key in path[1]]

    return ', '.join(values)


def validate_eventor_user(eventor_user, eventor_password):
    headers = {'Username': eventor_user, 'Password': eventor_password}
    logging.info(f'Trying validate Eventor user {eventor_user}')
    request = eventor_request('GET', config['EventorApi']['authenticate_endpoint'],
                              headers=headers, success_codes=(200, 403))
    if request.status_code == 403:
        logging.warning(f'Failed to validate Eventor user {eventor_user}. Full error: {request.text}')
        raise KnownError(config['Messages']['eventor_validation_fail'], 'eventor')
    logging.info(f'Fetched person info for eventor user {eventor_user}')

    person_info = ET.fromstring(request.text)
    # Check if Eventor user is member of organization
    if not person_in_organisation(person_info, organisation_id):
        logging.warning(f'Eventor user {eventor_user} not found in organization')
        raise KnownError(config['Messages']['not_in_club'], 'eventor')

    # Create dict with essential person info
    eventor_info_dict = dict()
    eventor_info_dict['first_name'] = find_value([["PersonName", "Given"]], person_info)
    eventor_info_dict['last_name'] = find_value([["PersonName", "Family"]], person_info)
    eventor_info_dict['id'] = find_value([["PersonId"]], person_info)
    eventor_info_dict['membership'] = get_membership(person_info)

    logging.info(f'User with eventor id {eventor_user} validated as {eventor_info_dict["membership"]}')

    return eventor_info_dict


def get_members_matrix():
    parse_settings_file = ROOT_DIR + '/' + config['Member']['parse_settings_file']
    with open(parse_settings_file, encoding='utf-8') as f:
        columns_dict = json.load(f)

    # Fetch XML with current members
    root = fetch_members()

    array = [list(columns_dict.keys())]

    for i, person in enumerate(root):
        person_info = extract_info(columns_dict, person)
        array.append(list(person_info.values()))

    return array




#########################################################################################################################
# common.py

class KnownError(Exception):
    def __init__(self, message, error_type=None):
        self.message = message
        self.error_type = error_type

    def __str__(self):
        return self.message


def check_api_key(headers, config):
    if config['ApiSettings']['ApiKey'].rstrip() == '':
        return True
    auth = headers.get("X-Api-Key")
    return auth == config['ApiSettings']['ApiKey']



#########################################################################################################################

if __name__ == '__main__':
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    main()




