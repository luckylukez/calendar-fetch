import functions_framework
import os
from set_environment_variables import set_env_vars

@functions_framework.http
def update_calendar_endpoint():
    print(os.environ['EVENTOR_ORG_ID'])
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
    import calenderfeeds as cf
    cf.generate_calendarfeed(days_in_advance, config, 'latest_calendar')

def main():
    set_env_vars()
    update_calendar_endpoint()

if __name__ == '__main__':
    main()

