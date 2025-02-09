#!/usr/bin/env python3
"""
NAME: test_l4.py

PURPOSE:
test_l4.py will create stations and endpoints to generate and verify layer-4 traffic

This script will monitor the urls/s, bytes-rd, or bytes-wr attribute of the endpoints.
These attributes can be tested over FTP using a --ftp flag.
If the monitored value does not continually increase, this test will not pass.

This script replaces the functionality of test_ipv4_l4.py, test_ipv4_l4_ftp_upload.py, test_ipv4_l4_ftp_urls_per_ten.py,
test_ipv4_l4_ftp_wifi.py, test_ipv4_l4_urls_per_ten.py, test_ipv4_l4_urls_per_ten.py, test_ipv4_l4_wifi.py

EXAMPLE (urls/s):
    ./test_l4.py --mgr localhost --upstream_port eth1 --radio wiphy0 --num_stations 3
                 --security {open|wep|wpa|wpa2|wpa3} --ssid <ssid> --passwd <password> --test_duration 1m
                 --url "dl http://192.168.1.101 /dev/null" --requests_per_ten 600 --test_type 'urls'
                 --csv_outfile test_l4.csv --test_rig Test-Lab --test_tag L4 --dut_hw_version Linux
                 --dut_model_num 1 --dut_sw_version 5.4.5 --dut_serial_num 1234 --test_id "L4 data"

EXAMPLE (bytes-rd):
    ./test_l4.py --mgr localhost --upstream_port eth1 --radio wiphy0 --num_stations 3
                 --security {open|wep|wpa|wpa2|wpa3} --ssid <ssid> --passwd <password> --test_duration 2m
                 --url "dl http://192.168.1.101 /dev/null" --requests_per_ten 600 --test_type bytes-rd
                 --csv_outfile test_l4.csv --test_rig Test-Lab --test_tag L4 --dut_hw_version Linux
                 --dut_model_num 1 --dut_sw_version 5.4.5 --dut_serial_num 1234 --test_id "L4 data"

EXAMPLE (ftp urls/s):
    ./test_l4.py --mgr localhost --upstream_port eth1 --radio wiphy0 --num_stations 3
                 --security {open|wep|wpa|wpa2|wpa3} --ssid <ssid> --passwd <password> --test_duration 1m
                 --url "ul ftp://lanforge:lanforge@192.168.1.101/large-file.bin /home/lanforge/large-file.bin"
                 --requests_per_ten 600 --test_type 'urls' --csv_outfile test_l4.csv --test_rig Test-Lab
                 --test_tag L4 --dut_hw_version Linux --dut_model_num 1 --dut_sw_version 5.4.5
                 --dut_serial_num 1234 --test_id "L4 data"

EXAMPLE (ftp bytes-wr):
    ./test_l4.py --mgr localhost --upstream_port eth1 --radio wiphy0 --num_stations 3
                 --security {open|wep|wpa|wpa2|wpa3} --ssid <ssid> --passwd <password> --test_duration 1m
                 --url "ul ftp://lanforge:lanforge@192.168.1.101/large-file.bin /home/lanforge/large-file.bin"
                 --requests_per_ten 600 --test_type bytes-wr --csv_outfile test_l4.csv --test_rig Test-Lab
                 --test_tag L4 --dut_hw_version Linux --dut_model_num 1 --dut_sw_version 5.4.5
                 --dut_serial_num 1234 --test_id "L4 data"

EXAMPLE (ftp bytes-rd):
    ./test_l4.py --mgr localhost --upstream_port eth1 --radio wiphy0 --num_stations 3
                 --security {open|wep|wpa|wpa2|wpa3} --ssid <ssid> --passwd <password> --test_duration 1m
                 --url "dl ftp://192.168.1.101 /dev/null" --requests_per_ten 600 --test_type bytes-rd
                 --csv_outfile test_l4.csv --test_rig Test-Lab --test_tag L4 --dut_hw_version Linux
                 --dut_model_num 1 --dut_sw_version 5.4.5 --dut_serial_num 1234 --test_id "L4 data"

Use './test_l4.py --help' to see command line usage and options
Copyright 2021 Candela Technologies Inc
License: Free to distribute and modify. LANforge systems must be licensed.
"""
import sys
import os
import csv
import importlib
import time
import argparse
import datetime
import logging

if sys.version_info[0] != 3:
    print("This script requires Python 3")
    exit(1)

sys.path.append(os.path.join(os.path.abspath(__file__ + "../../../")))

LFUtils = importlib.import_module("py-json.LANforge.LFUtils")
realm = importlib.import_module("py-json.realm")
Realm = realm.Realm
TestGroupProfile = realm.TestGroupProfile
port_utils = importlib.import_module("py-json.port_utils")
PortUtils = port_utils.PortUtils
lf_kpi_csv = importlib.import_module("py-scripts.lf_kpi_csv")
lf_report = importlib.import_module("py-scripts.lf_report")
lf_graph = importlib.import_module("py-scripts.lf_graph")
logger = logging.getLogger(__name__)
lf_logger_config = importlib.import_module("py-scripts.lf_logger_config")


class IPV4L4(Realm):
    def __init__(self,
                 host="localhost",
                 port=8080,
                 ssid=None,
                 security=None,
                 password=None,
                 url=None,
                 ftp_user=None,
                 ftp_passwd=None,
                 requests_per_ten=None,
                 station_list=None,
                 test_duration="2m",
                 ap=None,
                 outfile=None,
                 kpi_csv=None,
                 mode=0,
                 target_requests_per_ten=60,
                 number_template="00000",
                 num_tests=1,
                 radio="wiphy0",
                 _debug_on=False,
                 upstream_port="eth1",
                 ftp=False,
                 source=None,
                 dest=None,
                 test_type=None,
                 _exit_on_error=False,
                 _exit_on_fail=False):
        super().__init__(lfclient_host=host, lfclient_port=port, debug_=_debug_on)

        self.host = host
        self.port = port
        self.radio = radio
        self.upstream_port = upstream_port
        self.ssid = ssid
        self.security = security
        self.password = password
        self.url = url
        self.mode = mode
        self.ap = ap
        self.outfile = outfile
        self.kpi_csv = kpi_csv
        self.epoch_time = int(time.time())
        self.debug = _debug_on
        self.requests_per_ten = int(requests_per_ten)
        self.number_template = number_template
        self.test_duration = test_duration
        self.sta_list = station_list
        self.num_tests = int(num_tests)
        self.target_requests_per_ten = int(target_requests_per_ten)

        self.station_profile = self.new_station_profile()
        self.cx_profile = self.new_l4_cx_profile()

        self.port_util = PortUtils(self)

        self.station_profile.lfclient_url = self.lfclient_url
        self.station_profile.ssid = self.ssid
        self.station_profile.ssid_pass = self.password
        self.station_profile.security = self.security
        self.station_profile.number_template_ = self.number_template
        self.station_profile.mode = self.mode
        self.test_type = test_type
        self.ftp_user = ftp_user
        self.ftp_passwd = ftp_passwd
        self.source = source
        self.dest = dest
        if self.ap is not None:
            self.station_profile.set_command_param("add_sta", "ap", self.ap)

        self.cx_profile.url = self.url
        self.cx_profile.test_type = self.test_type
        self.cx_profile.requests_per_ten = self.requests_per_ten
        self.cx_profile.target_requests_per_ten = self.target_requests_per_ten

        if self.outfile is not None:
            results = self.outfile[:-4]
            results = results + "-results.csv"
            self.csv_results_file = open(results, "w")
            self.csv_results_writer = csv.writer(self.csv_results_file, delimiter=",")

        self.ftp = ftp
        if self.ftp and 'ftp://' not in self.url:
            logger.info("WARNING! FTP test chosen, but ftp:// not present in url!")

        test_types = {'urls', 'bytes-wr', 'bytes-rd'}
        if self.test_type not in test_types:
            raise ValueError(
                "Unknown test type: %s\nValid test types are urls, bytes-rd, or bytes-wr" % self.test_type)

        self.report = lf_report.lf_report(_results_dir_name="test_l4", _output_html="ftp_test.html", _output_pdf="ftp_test.pdf")

    def get_csv_name(self):
        logger.info("self.csv_results_file {}".format(self.csv_results_file.name))
        return self.csv_results_file.name

    # Common code to generate timestamp for CSV files.
    def time_stamp(self):
        return time.strftime('%m_%d_%Y_%H_%M_%S', time.localtime(self.epoch_time))

    # Query all endpoints to generate rx and other stats, returned
    # as an array of objects.
    def get_rx_values(self):
        endp_list = self.json_get("/layer4/all")
        # logger.info("endp_list: {endp_list}".format(endp_list=endp_list))

        endp_rx_drop_map = {}
        endp_rx_map = {}
        our_endps = {}
        endps = []

        total_bytes_rd = 0
        total_bytes_wr = 0
        total_rx_rate = 0
        total_tx_rate = 0
        urls_seconds = 0
        total_urls = 0

        '''
        for e in self.cx_profile.created_endp.keys():
            our_endps[e] = e
        print("our_endps {our_endps}".format(our_endps=our_endps))
        '''
        for endp_name in endp_list['endpoint']:
            if endp_name != 'uri' and endp_name != 'handler':
                for item, endp_value in endp_name.items():
                    # if item in our_endps:
                    if True:
                        endps.append(endp_value)
                        logger.debug("endpoint: {item} value:\n".format(item=item))
                        logger.debug(endp_value)
                        # print("item {item}".format(item=item))

                        for value_name, value in endp_value.items():
                            if value_name == 'bytes-rd':
                                endp_rx_map[item] = value
                                total_bytes_rd += int(value)
                            if value_name == 'bytes-wr':
                                endp_rx_map[item] = value
                                total_bytes_wr += int(value)
                            if value_name == 'rx rate':
                                endp_rx_map[item] = value
                                total_rx_rate += int(value)
                            if value_name == 'tx rate':
                                endp_rx_map[item] = value
                                total_tx_rate += int(value)
                            if value_name == 'urls/s':
                                endp_rx_map[item] = value
                                urls_seconds += int(value)
                            if value_name == 'total-urls':
                                endp_rx_map[item] = value
                                total_urls += int(value)

        # logger.debug("total-dl: ", total_dl, " total-ul: ", total_ul, "\n")
        return endp_rx_map, endps, total_bytes_rd, total_bytes_wr, total_rx_rate, total_tx_rate, urls_seconds, total_urls

    def build(self):
        # Build stations
        self.station_profile.use_security(self.security, self.ssid, self.password)
        logger.info("Creating stations")
        self.station_profile.set_command_flag("add_sta", "create_admin_down", 1)
        self.station_profile.set_command_param("set_port", "report_timer", 1500)
        self.station_profile.set_command_flag("set_port", "rpt_timer", 1)
        self.station_profile.create(radio=self.radio, sta_names_=self.sta_list, debug=self.debug)
        self._pass("PASS: Station build finished")

        temp_url = self.url.split(" ")
        if temp_url[0] == 'ul' or temp_url[0] == 'dl':
            if len(temp_url) == 2:
                if self.url.startswith("ul") and self.source not in self.url:
                    self.cx_profile.url += " " + self.source
                elif self.url.startswith("dl") and self.dest not in self.url:
                    self.cx_profile.url += " " + self.dest
        else:
            raise ValueError("ul or dl required in url to indicate direction")
        if self.ftp:
            if self.ftp_user is not None and self.ftp_passwd is not None:
                if ("%s:%s" % (self.ftp_user, self.ftp_passwd)) not in self.url:
                    temp_url = self.url.split("//")
                    temp_url = ("//%s:%s@" % (self.ftp_user, self.ftp_passwd)).join(temp_url)
                    self.cx_profile.url = temp_url
            self.cx_profile.create(ports=self.station_profile.station_names, sleep_time=.5, debug_=self.debug,
                                   suppress_related_commands_=True)
        else:
            self.cx_profile.create(ports=self.station_profile.station_names, sleep_time=.5, debug_=self.debug,
                                   suppress_related_commands_=None)

    def start(self, print_pass=False, print_fail=False):
        if self.ftp:
            self.port_util.set_ftp(port_name=self.name_to_eid(self.upstream_port)[2], resource=1, on=True)
        temp_stas = self.sta_list.copy()

        self.station_profile.admin_up()

        if self.wait_for_ip(temp_stas):
            self._pass("All stations got IPs", print_pass)
        else:
            self._fail("Stations failed to get IPs", print_fail)
            exit(1)

        self.csv_add_column_headers()
        self.cx_profile.start_cx()
        logger.info("Starting test")

    def stop(self):
        self.cx_profile.stop_cx()
        if self.ftp:
            self.port_util.set_ftp(port_name=self.name_to_eid(self.upstream_port)[2], resource=1, on=False)
        self.station_profile.admin_down()

    def cleanup(self, sta_list):
        self.cx_profile.cleanup()
        self.station_profile.cleanup(sta_list)
        LFUtils.wait_until_ports_disappear(base_url=self.lfclient_url, port_list=sta_list,
                                           debug=self.debug)

    # builds test data into kpi.csv report
    def record_kpi_csv(
            self,
            station_list,
            total_test,
            total_pass,
            total_bytes_rd,
            total_bytes_wr,
            total_rx_rate,
            total_tx_rate,
            urls_second,
            total_urls):

        sta_count = len(station_list)
        # logic for Subtest-Pass & Subtest-Fail columns
        subpass_bytes_rd = 0
        subpass_bytes_wr = 0
        subpass_rx_rate = 0
        subpass_tx_rate = 0
        subpass_urls = 0
        subfail_bytes_rd = 1
        subfail_bytes_wr = 1
        subfail_rx_rate = 1
        subfail_tx_rate = 1
        subfail_urls = 1

        if total_bytes_rd > 0:
            subpass_bytes_rd = 1
            subfail_bytes_rd = 0
        if total_bytes_wr > 0:
            subpass_bytes_wr = 1
            subfail_bytes_wr = 0
        if total_rx_rate > 0:
            subpass_rx_rate = 1
            subfail_rx_rate = 0
        if total_tx_rate > 0:
            subpass_tx_rate = 1
            subfail_tx_rate = 0
        if urls_second > 0:
            subpass_urls = 1
            subfail_urls = 0


        # logic for pass/fail column
        # total_test & total_pass values from lfcli_base.py
        if total_test == total_pass:
            pass_fail = "PASS"
        else:
            pass_fail = "FAIL"

        results_dict = self.kpi_csv.kpi_csv_get_dict_update_time()

        # kpi data for combined station totals
        if self.url.startswith('dl'):
            # kpi data for Total Bytes-RD
            results_dict['Graph-Group'] = "L4 Total Bytes-RD"
            results_dict['pass/fail'] = pass_fail
            results_dict['Subtest-Pass'] = subpass_bytes_rd
            results_dict['Subtest-Fail'] = subfail_bytes_rd
            results_dict['short-description'] = "Total Bytes-RD"
            results_dict['numeric-score'] = "{}".format(total_bytes_rd)
            results_dict['Units'] = "bytes-rd"
            self.kpi_csv.kpi_csv_write_dict(results_dict)

            # kpi data for RX Rate
            results_dict['Graph-Group'] = "L4 Total RX Rate"
            results_dict['pass/fail'] = pass_fail
            results_dict['Subtest-Pass'] = subpass_rx_rate
            results_dict['Subtest-Fail'] = subfail_rx_rate
            results_dict['short-description'] = "{sta_count} Stations Total RX Rate".format(sta_count=sta_count)
            results_dict['numeric-score'] = "{}".format(total_rx_rate)
            results_dict['Units'] = "bps"
            self.kpi_csv.kpi_csv_write_dict(results_dict)

        if self.url.startswith('ul'):
            # kpi data for Bytes-WR
            results_dict['Graph-Group'] = "L4 Total Bytes-WR"
            results_dict['pass/fail'] = pass_fail
            results_dict['Subtest-Pass'] = subpass_bytes_wr
            results_dict['Subtest-Fail'] = subfail_bytes_wr
            results_dict['short-description'] = "Total Bytes-WR"
            results_dict['numeric-score'] = "{}".format(total_bytes_wr)
            results_dict['Units'] = "bytes-wr"
            self.kpi_csv.kpi_csv_write_dict(results_dict)

            # kpi data for TX Rate
            results_dict['Graph-Group'] = "L4 Total TX Rate"
            results_dict['pass/fail'] = pass_fail
            results_dict['Subtest-Pass'] = subpass_tx_rate
            results_dict['Subtest-Fail'] = subfail_tx_rate
            results_dict['short-description'] = "{sta_count} Stations Total TX Rate".format(sta_count=sta_count)
            results_dict['numeric-score'] = "{}".format(total_tx_rate)
            results_dict['Units'] = "bps"
            self.kpi_csv.kpi_csv_write_dict(results_dict)

        # kpi data for URLs/s
        results_dict['Graph-Group'] = "Average URLs per Second"
        results_dict['pass/fail'] = pass_fail
        results_dict['Subtest-Pass'] = subpass_urls
        results_dict['Subtest-Fail'] = subfail_urls
        results_dict['short-description'] = "Average URLs per Second"
        results_dict['numeric-score'] = "{}".format(urls_second)
        results_dict['Units'] = "urls/s"
        self.kpi_csv.kpi_csv_write_dict(results_dict)

        # kpi data for Total URLs
        results_dict['Graph-Group'] = "Total URLs"
        results_dict['pass/fail'] = pass_fail
        results_dict['Subtest-Pass'] = subpass_urls
        results_dict['Subtest-Fail'] = subfail_urls
        results_dict['short-description'] = "Total URLs"
        results_dict['numeric-score'] = "{}".format(total_urls)
        results_dict['Units'] = "total-urls"
        self.kpi_csv.kpi_csv_write_dict(results_dict)

    # record results for .html & .pdf reports
    def record_results(
            self,
            sta_count,
            bytes_rd,
            bytes_wr,
            rx_rate,
            tx_rate,
            urls_second,
            total_urls):

        tags = dict()
        tags['station-count'] = sta_count
        # tags['attenuation'] = atten
        tags["script"] = 'test_l4'

        # now = str(datetime.datetime.utcnow().isoformat())

        if self.csv_results_file:
            row = [self.epoch_time, self.time_stamp(), sta_count,
                   bytes_rd, bytes_wr, rx_rate, tx_rate,
                   urls_second, total_urls
                   ]

            self.csv_results_writer.writerow(row)
            self.csv_results_file.flush()

    def csv_generate_results_column_headers(self):
        csv_rx_headers = [
            'Time epoch',
            'Time',
            'Station-Count',
            'Bytes-RD',
            'Bytes-WR',
            'RX Rate',
            'TX Rate',
            'URLs/s',
            'Total URLs',
            ]

        return csv_rx_headers

    # Write initial headers to csv file.
    def csv_add_column_headers(self):
        logger.info("self.csv_results_file: {csv_results_file}".format(csv_results_file=self.csv_results_file))
        if self.csv_results_file is not None:
            self.csv_results_writer.writerow(
                self.csv_generate_results_column_headers())
            self.csv_results_file.flush()


def main():
    parser = Realm.create_basic_argparse(
        prog='test_l4',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''\
               This script will monitor the urls/s, bytes-rd, or bytes-wr attribute of the endpoints.
               ''',
        description='''\
---------------------------
Layer-4 Test Script - test_l4.py
---------------------------
Summary:
This script will create stations and endpoints to generate and verify layer-4 traffic by monitoring the urls/s, 
 bytes-rd, or bytes-wr attribute of the endpoints.
---------------------------
Generic command example:
./test_l4.py --mgr <ip_address> --upstream_port eth1 --radio wiphy0 --num_stations 3 --security wpa2 
--ssid <ssid> --passwd <password> --test_duration 2m --url "ul http://<ap_ip_address> /dev/null" 
--requests_per_ten 600 --test_type bytes-wr --debug
---------------------------

            ''')
    parser.add_argument('--requests_per_ten', help='--requests_per_ten number of request per ten minutes',
                        default=600)
    parser.add_argument('--num_tests', help='--num_tests number of tests to run. Each test runs 10 minutes',
                        default=1)
    parser.add_argument('--url', help='--url specifies upload/download, address, and dest',
                        default="dl http://10.40.0.1 /dev/null")
    parser.add_argument('--test_duration', help='duration of test', default="2m")
    parser.add_argument('--target_per_ten',
                        help='--target_per_ten target number of request per ten minutes. test will check for 90 percent this value',
                        default=600)
    parser.add_argument('--mode', help='Used to force mode of stations')
    parser.add_argument('--ap', help='Used to force a connection to a particular AP')
    parser.add_argument('--report_file', help='where you want to store results')
    parser.add_argument('--output_format', help='choose csv or xlsx')  # update once other forms are completed
    parser.add_argument('--ftp', help='Use ftp for the test', action='store_true')
    parser.add_argument('--test_type', help='Choose type of test to run {urls, bytes-rd, bytes-wr}',
                        default='bytes-rd')
    parser.add_argument('--ftp_user', help='--ftp_user sets the username to be used for ftp', default=None)
    parser.add_argument('--ftp_passwd', help='--ftp_user sets the password to be used for ftp', default=None)
    parser.add_argument('--dest',
                        help='--dest specifies the destination for the file, should be used when downloading',
                        default="/dev/null")
    parser.add_argument('--source',
                        help='--source specifies the source of the file, should be used when uploading',
                        default="/var/www/html/data_slug_4K.bin")
    parser.add_argument('--local_lf_report_dir',
                        help='--local_lf_report_dir override the report path, primary use when running test in test suite',
                        default="")
    # kpi_csv arguments
    parser.add_argument(
        "--test_rig",
        default="",
        help="test rig for kpi.csv, testbed that the tests are run on")
    parser.add_argument(
        "--test_tag",
        default="",
        help="test tag for kpi.csv,  test specific information to differenciate the test")
    parser.add_argument(
        "--dut_hw_version",
        default="",
        help="dut hw version for kpi.csv, hardware version of the device under test")
    parser.add_argument(
        "--dut_sw_version",
        default="",
        help="dut sw version for kpi.csv, software version of the device under test")
    parser.add_argument(
        "--dut_model_num",
        default="",
        help="dut model for kpi.csv,  model number / name of the device under test")
    parser.add_argument(
        "--dut_serial_num",
        default="",
        help="dut serial for kpi.csv, serial number / serial number of the device under test")
    parser.add_argument(
        "--test_priority",
        default="",
        help="dut model for kpi.csv,  test-priority is arbitrary number")
    parser.add_argument(
        '--csv_outfile',
        help="--csv_outfile <Output file for csv data>",
        default="")

    args = parser.parse_args()

    # set up logger
    logger_config = lf_logger_config.lf_logger_config()
    if args.lf_logger_config_json:
        # logger_config.lf_logger_config_json = "lf_logger_config.json"
        logger_config.lf_logger_config_json = args.lf_logger_config_json
        logger_config.load_lf_logger_config()

    # for kpi.csv generation
    local_lf_report_dir = args.local_lf_report_dir
    test_rig = args.test_rig
    test_tag = args.test_tag
    dut_hw_version = args.dut_hw_version
    dut_sw_version = args.dut_sw_version
    dut_model_num = args.dut_model_num
    dut_serial_num = args.dut_serial_num
    # test_priority = args.test_priority  # this may need to be set per test
    test_id = args.test_id

    if local_lf_report_dir != "":
        report = lf_report.lf_report(
            _path=local_lf_report_dir,
            _results_dir_name="test_l4",
            _output_html="test_l4.html",
            _output_pdf="test_l4.pdf")
    else:
        report = lf_report.lf_report(
            _results_dir_name="test_l4",
            _output_html="test_l4.html",
            _output_pdf="test_l4.pdf")

    kpi_path = report.get_report_path()
    # kpi_filename = "kpi.csv"
    logger.info("kpi_path :{kpi_path}".format(kpi_path=kpi_path))

    kpi_csv = lf_kpi_csv.lf_kpi_csv(
        _kpi_path=kpi_path,
        _kpi_test_rig=test_rig,
        _kpi_test_tag=test_tag,
        _kpi_dut_hw_version=dut_hw_version,
        _kpi_dut_sw_version=dut_sw_version,
        _kpi_dut_model_num=dut_model_num,
        _kpi_dut_serial_num=dut_serial_num,
        _kpi_test_id=test_id)

    if args.csv_outfile is not None:
        current_time = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
        csv_outfile = "{}_{}-test_l4.csv".format(
            args.csv_outfile, current_time)
        csv_outfile = report.file_add_path(csv_outfile)
        logger.info("csv output file : {}".format(csv_outfile))

    num_sta = 2
    if (args.num_stations is not None) and (int(args.num_stations) > 0):
        num_stations_converted = int(args.num_stations)
        num_sta = num_stations_converted
    if args.report_file is None:
        if args.output_format in ['csv', 'json', 'html', 'hdf', 'stata', 'pickle', 'pdf', 'parquet', 'png', 'df',
                                  'xlsx']:
            output_form = args.output_format.lower()
        else:
            logger.info("Defaulting data file output type to Excel")
            output_form = 'xlsx'

    else:
        if args.output_format is None:
            output_form = str(args.report_file).split('.')[-1]
        else:
            output_form = args.output_format

    # Create directory
    if args.report_file is None:
        if os.path.isdir('/home/lanforge/report-data'):
            homedir = str(datetime.datetime.now().strftime("%Y-%m-%d-%H-%M")).replace(':', '-') + 'test_l4'
            path = os.path.join('/home/lanforge/report-data/', homedir)
            logger.info(path)
            os.mkdir(path)
        else:
            path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            logger.info('Saving file to local directory')
        if args.output_format in ['csv', 'json', 'html', 'hdf', 'stata', 'pickle', 'pdf', 'png', 'df', 'parquet',
                                  'xlsx']:
            rpt_file = path + '/data.' + args.output_format
            logger.info(rpt_file)
        else:
            logger.info('Defaulting data file output type to Excel')
            rpt_file = path + '/data.xlsx'
            logger.info(rpt_file)
    else:
        rpt_file = args.report_file
        logger.info(rpt_file)

    station_list = LFUtils.portNameSeries(prefix_="sta", start_id_=0, end_id_=num_sta - 1, padding_number_=10000,
                                          radio=args.radio)

    ip_test = IPV4L4(host=args.mgr, port=args.mgr_port,
                     ssid=args.ssid,
                     password=args.passwd,
                     radio=args.radio,
                     upstream_port=args.upstream_port,
                     security=args.security,
                     station_list=station_list,
                     url=args.url,
                     mode=args.mode,
                     ap=args.ap,
                     outfile=args.csv_outfile,
                     kpi_csv=kpi_csv,
                     ftp=args.ftp,
                     ftp_user=args.ftp_user,
                     ftp_passwd=args.ftp_passwd,
                     source=args.source,
                     dest=args.dest,
                     test_type=args.test_type,
                     _debug_on=args.debug,
                     test_duration=args.test_duration,
                     num_tests=args.num_tests,
                     target_requests_per_ten=args.target_per_ten,
                     requests_per_ten=args.requests_per_ten)
    ip_test.cleanup(station_list)
    ip_test.build()
    ip_test.start()
    l4_cx_results = {}

    layer4traffic = ','.join([[*x.keys()][0] for x in ip_test.json_get('layer4')['endpoint']])
    ip_test.cx_profile.monitor(col_names=['name', 'bytes-rd', 'urls/s', 'bytes-wr'],
                               report_file=rpt_file,
                               duration_sec=args.test_duration,
                               created_cx=layer4traffic,
                               output_format=output_form,
                               script_name='test_l4',
                               arguments=args,
                               debug=args.debug)

    temp_stations_list = []
    temp_stations_list.extend(ip_test.station_profile.station_names.copy())
    logger.info("temp_stations_list: {temp_stations_list}".format(temp_stations_list=temp_stations_list))
    total_test = len(ip_test.get_result_list())
    total_pass = len(ip_test.get_passed_result_list())

    endp_rx_map, endps, total_bytes_rd, total_bytes_wr, total_rx_rate, total_tx_rate, urls_second, total_urls = ip_test.get_rx_values()
    #endp_rx_map, endp_rx_drop_map, endps, bytes_rd, bytes_wr, rx_rate, tcp_ul, tx_rate, urls_sec, total_urls, total_ul_ll = ip_test.get_rx_values()

    ip_test.record_kpi_csv(temp_stations_list, total_test, total_pass, total_bytes_rd, total_bytes_wr, total_rx_rate, total_tx_rate, urls_second, total_urls)
    ip_test.record_results(len(temp_stations_list), total_bytes_rd, total_bytes_wr, total_rx_rate, total_tx_rate, urls_second, total_urls)
    # ip_test.record_results(len(temp_stations_list), bytes_rd, bytes_wr, rx_rate, tx_rate, urls_sec, total_urls)

    # Reporting Results (.pdf & .html)
    csv_results_file = ip_test.get_csv_name()
    logger.info("csv_results_file: %s", csv_results_file)
    # csv_results_file = kpi_path + "/" + kpi_filename
    report.set_title("L4 Test")
    report.build_banner()
    report.set_table_title("L4 Test Key Performance Indexes")
    report.build_table_title()
    report.set_table_dataframe_from_csv(csv_results_file)
    report.build_table()
    report.write_html_with_timestamp()
    report.write_index_html()
    # report.write_pdf(_page_size = 'A3', _orientation='Landscape')
    # report.write_pdf_with_timestamp(_page_size='A4', _orientation='Portrait')
    report.write_pdf_with_timestamp(_page_size='A4', _orientation='Landscape')

    is_passing = ip_test.passes()

    ip_test.stop()
    # cleanup stations:

    if not args.no_cleanup:
        # time.sleep(15)
        ip_test.cleanup(station_list)

    if not is_passing:
        logger.info(ip_test.get_fail_message())
        ip_test.exit_fail()
    if is_passing:
        logger.info("Full test passed")
        ip_test.exit_success()


if __name__ == "__main__":
    main()
