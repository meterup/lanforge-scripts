#!/usr/bin/env python3

# Copies the data from a CSV file from the KPI file generated from a Wifi Capacity test to an Influx database

# The CSV requires three columns in order to work: Date, test details, and numeric-score.

# Date is a unix timestamp, test details is the variable each datapoint is measuring, and numeric-score is the value for that timepoint and variable.

import sys
import os
from pprint import pprint
from influx2 import RecordInflux

if sys.version_info[0] != 3:
    print("This script requires Python 3")
    exit(1)

if 'py-json' not in sys.path:
    sys.path.append(os.path.join(os.path.abspath('..'), 'py-json'))

import argparse
from realm import Realm
import datetime

def influx_add_parser_args(parser):
    parser.add_argument('--influx_host', help='Hostname for the Influx database', default="")
    parser.add_argument('--influx_port', help='IP Port for the Influx database', default=8086)
    parser.add_argument('--influx_org', help='Organization for the Influx database', default="")
    parser.add_argument('--influx_token', help='Token for the Influx database', default="")
    parser.add_argument('--influx_bucket', help='Name of the Influx bucket', default="")
    parser.add_argument('--influx_tag', action='append', nargs=2,
                        help='--influx_tag <key> <val>   Can add more than one of these.', default=[])


class CSVtoInflux(Realm):
    def __init__(self,
                 lfclient_host="localhost",
                 lfclient_port=8080,
                 debug=False,
                 _exit_on_error=False,
                 _exit_on_fail=False,
                 _proxy_str=None,
                 _capture_signal_list=[],
                 influxdb=None,
                 _influx_tag=[],
                 target_csv=None):
        super().__init__(lfclient_host=lfclient_host,
                         lfclient_port=lfclient_port,
                         debug_=debug,
                         _exit_on_error=_exit_on_error,
                         _exit_on_fail=_exit_on_fail,
                         _proxy_str=_proxy_str,
                         _capture_signal_list=_capture_signal_list)
        self.influxdb = influxdb
        self.target_csv = target_csv
        self.influx_tag = _influx_tag

    # Submit data to the influx db if configured to do so.
    def post_to_influx(self):
        with open(self.target_csv) as fp:
            line = fp.readline()
            line = line.split('\t')
            # indexes tell us where in the CSV our data is located. We do it this way so that even if the columns are moved around, as long as they are present, the script will still work.
            numeric_score_index = line.index('numeric-score')
            test_id_index = line.index('test-id')
            date_index = line.index('Date')
            test_details_index = line.index('test details')
            short_description_index = line.index('short-description')
            graph_group_index = line.index('Graph-Group')
            units_index = line.index('Units')
            line = fp.readline()
            while line:
                line = line.split('\t') #split the line by tabs to separate each item in the string
                date = line[date_index]
                date = datetime.datetime.utcfromtimestamp(int(date) / 1000).isoformat() #convert to datetime so influx can read it, this is required
                numeric_score = line[numeric_score_index]
                numeric_score = float(numeric_score) #convert to float, InfluxDB cannot
                test_details = line[test_details_index]
                short_description = line[short_description_index]
                test_id = line[test_id_index]
                tags = dict()
                tags['script'] = line[test_id_index]
                tags['short-description'] = line[short_description_index]
                tags['test_details'] = line[test_details_index]
                tags['Graph-Group'] = line[graph_group_index]
                tags['Units'] = line[units_index]
                for item in self.influx_tag: # Every item in the influx_tag command needs to be added to the tags variable
                    tags[item[0]] = item[1]
                self.influxdb.post_to_influx(short_description, numeric_score, tags, date)
                line = fp.readline()
                #influx wants to get data in the following format:
                # variable n  ame, value, tags, date
                # total-download-mbps-speed-for-the-duration-of-this-iteration 171.085494 {'script': 'WiFi Capacity'} 2021-04-14T19:04:04.902000


def main():
    lfjson_host = "localhost"
    lfjson_port = 8080
    endp_types = "lf_udp"
    debug = False

    parser = argparse.ArgumentParser(
        prog='test_l3_longevity.py',
        # formatter_class=argparse.RawDescriptionHelpFormatter,
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''
            ''',

        description='''\
csv_to_influx.py:
--------------------

Summary : 
----------
Copies the data from a CSV file generated by a wifi capacity test to an influx database.

Column names are designed for the KPI file  generated by our Wifi Capacity Test.

A user can of course change the column names to match these in order to input any csv file.

The CSV file needs to have the following columns:
    --date - which is a UNIX timestamp
    --test details - which is the variable being measured by the test
    --numeric-score - which is the value for that variable at that point in time.

Generic command layout:
-----------------------
python .\\csv_to_influx.py


Command:
python3 csv_to_influx.py --influx_host localhost --influx_org Candela --influx_token random_token --influx_bucket lanforge
    --target_csv kpi.csv


        ''')

    influx_add_parser_args(parser)

    # This argument is specific to this script, so not part of the generic influxdb parser args
    # method above.
    parser.add_argument('--target_csv', help='CSV file to record to influx database', default="")

    args = parser.parse_args()

    influxdb = RecordInflux(_lfjson_host=lfjson_host,
                            _lfjson_port=lfjson_port,
                            _influx_host=args.influx_host,
                            _influx_port=args.influx_port,
                            _influx_org=args.influx_org,
                            _influx_token=args.influx_token,
                            _influx_bucket=args.influx_bucket)

    csvtoinflux = CSVtoInflux(influxdb=influxdb,
                              target_csv=args.target_csv,
                              _influx_tag=args.influx_tag)
    csvtoinflux.post_to_influx()


if __name__ == "__main__":
    main()
