#!/usr/bin/env python
# -*- coding: utf-8 -*-


# <bitbar.title>Bartebuss</bitbar.title>
# <bitbar.version>v0.1</bitbar.version>
# <bitbar.author>OptimusCrime</bitbar.author>
# <bitbar.author.github>OptimusCrime</bitbar.author.github>
# <bitbar.desc>Automatically fetches bus departures based on which WiFi you are currently connected to</bitbar.desc>
# <bitbar.image>http://www.hosted-somewhere/pluginimage</bitbar.image>
# <bitbar.dependencies>python</bitbar.dependencies>
# <bitbar.abouturl>https://github.com/OptimusCrime/bitbar-bartebuss</bitbar.abouturl>


import datetime
import os
import json
import time

# Support for both Python2 and Python3
try:
    from urllib2 import urlopen
except ImportError:
    from urllib import urlopen


# User setting. Overwrite with your own. Follow instructions in README.md
SETTINGS = {

    # Bus connections to fetch
    'bus': {
        'eduroam': ['16011333']
    },

    # Maximum number of departures to fetch
    'max_departures': 5
}


class SettingParser:

    # System command used to fetch the current airport information
    AIRPORT_CMD = '/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I'

    # Awk expression to get only the SSID name from the command above
    AIRPORT_SSID = 'awk \'/ SSID/ {print substr($0, index($0, $2))}\''

    def __init__(self):
        self._departures = []
        self.parsed = False

    @staticmethod
    def network_name():
        network = str(os.popen(SettingParser.AIRPORT_CMD + ' | ' + SettingParser.AIRPORT_SSID).read()).rstrip()

        if len(network) == 0:
            return None

        return network

    def parse_departures(self):
        self.parsed = True

        network = SettingParser.network_name()
        if network is None:
            return

        if network not in SETTINGS['bus']:
            return

        self._departures = SETTINGS['bus'][network]

    @property
    def departures(self):
        if not self.parsed:
            self.parse_departures()

        return self._departures


class Information:

    def __init__(self):
        self._stop = None
        self._updated = None

    @property
    def stop(self):
        if self._stop is None:
            return 'Ukjent'
        return str(self._stop.encode('utf-8'))

    @property
    def updated(self):
        if self._updated is None:
            return None
        return 'Oppdatert ' + str(self._updated['time']['hour']) + ':' + str(self._updated['time']['minute'])


class Departure:

    def __init__(self, line, destination):
        self.line = line
        self.destination = destination

        self.raw_data = None
        self.departure = None

        self.output = ''


    def parse_data(self, data):
        self.raw_data = data

        # Parse departure time
        t = Departure.parse_date_string(data['t'])

        # Parse departure real time (if defined)
        rt = None
        if data['rt'] is not None:
            rt = Departure.parse_date_string(data['rt'])

        # Find out what time to use, real time if defined, otherwise the regular time
        obj = Departure.find_time_to_use(t, rt)

        # Add timestamp for the date itself
        self.departure = Departure.parse_departure(obj)

        # Add timestamp value from the time
        self.departure += (int(obj['time']['hour']) * 60) + int(obj['time']['minute'])

        self.output = Departure.parse_output(data, t, rt)

    @staticmethod
    def parse_date_string(date_string):
        date_string, time_string = date_string.split(' ')
        year, month, day = date_string.split('-')

        if len(time_string) == 5:
            hour, minute = time_string.split(':')
        else:
            hour, minute, seconds = time_string.split(':')

        return {
            'date': {
                'day': int(day),
                'month': int(month),
                'year': int(year)
            },
            'time': {
                'hour': hour,
                'minute': minute
            }
        }

    @staticmethod
    def find_time_to_use(t, rt):
        # Use t if rt is None, otherwise use rt
        if rt is not None:
            return rt
        return t

    @staticmethod
    def parse_departure(obj):
        day = obj['date']['day']
        if day < 10:
            day = '0' + str(obj['date']['day'])

        month = obj['date']['month']
        if month < 10:
            month = '0' + str(obj['date']['month'])

        return time.mktime(time.strptime(str(day) + '/' + str(month) + '/' + str(obj['date']['year']), "%d/%m/%Y"))

    @staticmethod
    def parse_output(data, t, rt):
        tomorrow = False
        if 'nt' in data and data['nt'] is True:
            tomorrow = True

        output = Departure.parse_output_time(t, rt)

        if tomorrow is False:
            return output + '|color=black'
        return output

    @staticmethod
    def parse_output_time(t, rt):
        # If no real time, output the time in parenthesis
        if rt is None:
            return '(' + Departure.parse_output_time_string(t) + ')'

        # Check if rt and t are similar, if they are output just the real time
        if set(t) == set(rt):
            return Departure.parse_output_time_string(rt)

        # Time and real time differs, output time in parenthesis, then real time
        return '(' + Departure.parse_output_time_string(t) + ') ' + Departure.parse_output_time_string(rt)

    @staticmethod
    def parse_output_time_string(obj):
        return obj['time']['hour'] + ':' + obj['time']['minute']

    def __str__(self):
        return str(self.line) + ' ' + str(self.destination) + ': ' + self.output

class StatusFetcher:

    def __init__(self):
        self.information = Information()
        self.data = []
        self.raw_data = {}

    def run(self, departures):
        for departure in departures:
            self.departure_information(departure)

        self.handle_data()

        if not self.data:
            return

        # Sort the departures
        self.data.sort(key=lambda x: x.departure)

    def departure_information(self, departure_id):
        content = urlopen('http://bartebuss.no/api/unified/' + str(departure_id)).read().decode("utf-8")
        if content is None or len(content) == 0:
            return

        json_content = json.loads(content)
        if type(json_content) != dict:
            return

        self.raw_data[departure_id] = json_content

    def handle_data(self):
        if not self.raw_data:
            return

        for key, value in self.raw_data.items():
            if 'schedule' not in value:
                continue

            if 'name' in value and self.information._stop is None:
                self.information._stop = value['name']

            if 'serverTime' in value and self.information._updated is None:
                self.information._updated = Departure.parse_date_string(value['serverTime'])

            self.handle_schedules(value['schedule'])

    def handle_schedules(self, schedules):
        for schedule in schedules:
            if type(schedule) != dict:
                continue

            self.handle_schedule(schedule)

    def handle_schedule(self, schedule):
        # Make sure our dict has all these keys
        if not all(k in schedule for k in ('line', 'destination', 'departures')):
            return

        # If we have no departures at all we skip this schedule element
        if not schedule['departures']:
            return

        line = schedule['line']
        destination = schedule['destination']

        for departure_data in schedule['departures']:
            # Skip departures in the past
            if 'p' in departure_data and departure_data['p'] is True:
                continue

            # We have our own class for departures to make it easier to sort the final output
            departure = Departure(line, destination)
            departure.parse_data(departure_data)

            self.data.append(departure)


class BitBarFormatter:

    def __init__(self):
        pass

    @staticmethod
    def output(data, information):
        # Print main line
        print('Buss')
        print('---')

        # Print info section
        print('Avgang fra ' + information.stop + '|color=black')
        if information.updated is not None:
            print(information.updated + '|color=black')
        print('---')

        # Print departures
        for i in range(SETTINGS['max_departures']):
            print(BitBarFormatter.departure_bitbar(data[i]))

    @staticmethod
    def departure_bitbar(departure):
        return str(departure)

def main():
    # Parse the settings
    setting_parser = SettingParser()
    if not setting_parser.departures:
        return

    # Fetch the status from the Bartebuss API
    status_fetcher = StatusFetcher()
    status_fetcher.run(setting_parser.departures)

    # Format the output and print the information
    BitBarFormatter.output(status_fetcher.data, status_fetcher.information)


if __name__ == "__main__":
    main()
