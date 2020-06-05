#!/usr/bin/env python3

#  This will create a station, create TCP and UDP traffic, run it a short amount of time,
#  and verify whether traffic was sent and received.  It also verifies the station connected
#  to the requested BSSID if bssid is specified as an argument.
#  The script will clean up the station and connections at the end of the test.

import sys

if sys.version_info[0] != 3:
    print("This script requires Python 3")
    exit(1)

if 'py-json' not in sys.path:
    sys.path.append('../py-json')

import argparse
from LANforge import LFUtils
# from LANforge import LFCliBase
import LANforge.lfcli_base
from LANforge.lfcli_base import LFCliBase
from LANforge.LFUtils import *


class StaConnect(LFCliBase):
    def __init__(self, host, port, _dut_ssid="MyAP", _dut_passwd="NA", _dut_bssid="",
                 _user="", _passwd="", _sta_mode="0", _radio="wiphy0",
                 _resource=1, _upstream_resource=1, _upstream_port="eth2",
                 _sta_name="sta001", _debugOn=False):
        # do not use `super(LFCLiBase,self).__init__(self, host, port, _debugOn)
        # that is py2 era syntax and will force self into the host variable, making you
        # very confused.
        super().__init__(host, port, _debug=_debugOn, _halt_on_error=False)
        self.dut_ssid = _dut_ssid
        self.dut_passwd = _dut_passwd
        self.dut_bssid = _dut_bssid
        self.user = _user
        self.passwd = _passwd
        self.sta_mode = _sta_mode  # See add_sta LANforge CLI users guide entry
        self.radio = _radio
        self.resource = _resource
        self.upstream_resource = _upstream_resource
        self.upstream_port = _upstream_port
        self.sta_name = _sta_name
        self.sta_url = None  # defer construction
        self.upstream_url = None  # defer construction

    def getStaUrl(self):
        if self.sta_url is None:
            self.sta_url = "port/1/%s/%s" % (self.resource, self.sta_name)
        return self.sta_url

    def getUpstreamUrl(self):
        if self.upstream_url is None:
            self.upstream_url = "port/1/%s/%s" % (self.upstream_resource, self.upstream_port)
        return self.upstream_url

    # Compare pre-test values to post-test values
    def compareVals(self, name, postVal, print_pass=False, print_fail=True):
        # print(f"Comparing {name}")
        if postVal > 0:
            self._pass("%s %s" % (name, postVal), print_pass)
        else:
            self._fail("%s did not report traffic: %s" % (name, postVal), print_fail)

    def run(self):
        self.clear_test_results()
        self.check_connect()
        eth1IP = self.json_get(self.getUpstreamUrl())
        if eth1IP is None:
            self._fail("Unable to query %s, bye" % self.upstream_port, True)
            return False
        if eth1IP['interface']['ip'] == "0.0.0.0":
            self._fail("Warning: %s lacks ip address" % self.getUpstreamUrl())
            return False

        url = self.getStaUrl()
        response = self.json_get(url)
        if response is not None:
            if response["interface"] is not None:
                print("removing old station")
                LFUtils.removePort(self.resource, self.sta_name, self.mgr_url)
                LFUtils.waitUntilPortsDisappear(self.resource, self.mgr_url, [self.sta_name])

        # Create stations and turn dhcp on
        print("Creating station %s and turning on dhcp..." % self.sta_name)
        flags = 0x10000
        if "" != self.dut_passwd:
            flags += 0x400
        data = {
            "shelf": 1,
            "resource": self.resource,
            "radio": self.radio,
            "sta_name": self.sta_name,
            "ssid": self.dut_ssid,
            "key": self.dut_passwd,
            "mode": self.sta_mode,
            "mac": "xx:xx:xx:xx:*:xx",
            "flags": flags  # verbose, wpa2
        }
        print("Adding new station %s " % self.sta_name)
        self.json_post("/cli-json/add_sta", data)

        data = {
            "shelf": 1,
            "resource": self.resource,
            "port": self.sta_name,
            "current_flags": 0x80000000,  # use DHCP, not down
            "interest": 0x4002  # set dhcp, current flags
        }
        print("Configuring %s..." % self.sta_name)
        self.json_post("/cli-json/set_port", data)

        data = {"shelf": 1,
                "resource": self.resource,
                "port": self.sta_name,
                "probe_flags": 1}
        self.json_post("/cli-json/nc_show_ports", data)
        LFUtils.waitUntilPortsAdminUp(self.resource, self.mgr_url, [self.sta_name])

        # station_info = self.jsonGet(self.mgr_url, "%s?fields=port,ip,ap" % (self.getStaUrl()))
        duration = 0
        maxTime = 300
        ip = "0.0.0.0"
        ap = ""
        print("Waiting for %s associate to AP [%s]..." % (self.sta_name, ap))
        while (ip == "0.0.0.0") and (duration < maxTime):
            duration += 2
            time.sleep(2)
            station_info = self.json_get(self.getStaUrl() + "?fields=port,ip,ap")

            # LFUtils.debug_printer.pprint(station_info)
            if (station_info is not None) and ("interface" in station_info):
                if "ip" in station_info["interface"]:
                    ip = station_info["interface"]["ip"]
                if "ap" in station_info["interface"]:
                    ap = station_info["interface"]["ap"]

            if (ap == "Not-Associated") or (ap == ""):
                print("Waiting for %s associate to AP [%s]..." % (self.sta_name, ap))
            else:
                if ip == "0.0.0.0":
                    print("Waiting for %s to gain IP ..." % self.sta_name)

        if (ap != "") and (ap != "Not-Associated"):
            print("Connected to AP: "+ap)
            if self.dut_bssid != "":
                if self.dut_bssid.lower() == ap.lower():
                    self._pass("Connected to BSSID: " + ap)
                    # self.test_results.append("PASSED: )
                    # print("PASSED: Connected to BSSID: "+ap)
                else:
                    self._fail("Connected to wrong BSSID, requested: %s  Actual: %s" % (self.dut_bssid, ap))
        else:
            self._fail("Did not connect to AP")
            return False

        if ip == "0.0.0.0":
            self._fail("%s did not get an ip. Ending test" % self.sta_name)
            print("Cleaning up...")
            removePort(self.resource, self.sta_name, self.mgr_url)
            return False
        else:
            self._pass("Connected to AP: %s  With IP: %s" % (ap, ip))

        # create endpoints and cxs
        # Create UDP endpoints
        data = {
            "alias": "testUDP-A",
            "shelf": 1,
            "resource": self.resource,
            "port": self.sta_name,
            "type": "lf_udp",
            "ip_port": "-1",
            "min_rate": 1000000
        }
        self.json_post("/cli-json/add_endp", data)

        data = {
            "alias": "testUDP-B",
            "shelf": 1,
            "resource": self.upstream_resource,
            "port": self.upstream_port,
            "type": "lf_udp",
            "ip_port": "-1",
            "min_rate": 1000000
        }
        self.json_post("/cli-json/add_endp", data)

        # Create CX
        data = {
            "alias": "testUDP",
            "test_mgr": "default_tm",
            "tx_endp": "testUDP-A",
            "rx_endp": "testUDP-B",
        }
        self.json_post("/cli-json/add_cx", data)

        # Create TCP endpoints
        data = {
            "alias": "testTCP-A",
            "shelf": 1,
            "resource": self.resource,
            "port": self.sta_name,
            "type": "lf_tcp",
            "ip_port": "0",
            "min_rate": 1000000
        }
        self.json_post("/cli-json/add_endp", data)

        data = {
            "alias": "testTCP-B",
            "shelf": 1,
            "resource": self.upstream_resource,
            "port": self.upstream_port,
            "type": "lf_tcp",
            "ip_port": "-1",
            "min_rate": 1000000
        }
        self.json_post("/cli-json/add_endp", data)

        # Create CX
        data = {
            "alias": "testTCP",
            "test_mgr": "default_tm",
            "tx_endp": "testTCP-A",
            "rx_endp": "testTCP-B",
        }
        self.json_post("/cli-json/add_cx", data)

        cxNames = ["testTCP", "testUDP"]
        endpNames = ["testTCP-A", "testTCP-B",
                     "testUDP-A", "testUDP-B"]

        # start cx traffic
        print("\nStarting CX Traffic")
        for name in range(len(cxNames)):
            data = {
                "test_mgr": "ALL",
                "cx_name": cxNames[name],
                "cx_state": "RUNNING"
            }
            self.json_post("/cli-json/set_cx_state", data)

        # Refresh stats
        print("\nRefresh CX stats")
        for name in range(len(cxNames)):
            data = {
                "test_mgr": "ALL",
                "cross_connect": cxNames[name]
            }
            self.json_post("/cli-json/show_cxe", data)

        time.sleep(15)

        # stop cx traffic
        print("\nStopping CX Traffic")
        for name in range(len(cxNames)):
            data = {
                "test_mgr": "ALL",
                "cx_name": cxNames[name],
                "cx_state": "STOPPED"
            }
            self.json_post("/cli-json/set_cx_state", data)

        # Refresh stats
        print("\nRefresh CX stats")
        for name in range(len(cxNames)):
            data = {
                "test_mgr": "ALL",
                "cross_connect": cxNames[name]
            }
            self.json_post("/cli-json/show_cxe", data)

        # print("Sleeping for 5 seconds")
        time.sleep(5)

        # get data for endpoints JSON
        print("Collecting Data")
        try:
            ptestTCPA = self.json_get("/endp/testTCP-A?fields=tx+bytes,rx+bytes")
            ptestTCPATX = ptestTCPA['endpoint']['tx bytes']
            ptestTCPARX = ptestTCPA['endpoint']['rx bytes']

            ptestTCPB = self.json_get("/endp/testTCP-B?fields=tx+bytes,rx+bytes")
            ptestTCPBTX = ptestTCPB['endpoint']['tx bytes']
            ptestTCPBRX = ptestTCPB['endpoint']['rx bytes']

            ptestUDPA = self.json_get("/endp/testUDP-A?fields=tx+bytes,rx+bytes")
            ptestUDPATX = ptestUDPA['endpoint']['tx bytes']
            ptestUDPARX = ptestUDPA['endpoint']['rx bytes']

            ptestUDPB = self.json_get("/endp/testUDP-B?fields=tx+bytes,rx+bytes")
            ptestUDPBTX = ptestUDPB['endpoint']['tx bytes']
            ptestUDPBRX = ptestUDPB['endpoint']['rx bytes']
        except Exception as e:
            self.error(e)
            print("Cleaning up...")
            data = {
                "shelf": 1,
                "resource": self.resource,
                "port": self.sta_name
            }
            self.json_post("/cli-json/rm_vlan", data)
            removeCX(self.mgr_url, cxNames)
            removeEndps(self.mgr_url, endpNames)
            return False

        # print("\n")
        # self.test_results.append("Neutral message will fail")
        # self.test_results.append("FAILED message will fail")

        self.compareVals("testTCP-A TX", ptestTCPATX)
        self.compareVals("testTCP-A RX", ptestTCPARX)

        self.compareVals("testTCP-B TX", ptestTCPBTX)
        self.compareVals("testTCP-B RX", ptestTCPBRX)

        self.compareVals("testUDP-A TX", ptestUDPATX)
        self.compareVals("testUDP-A RX", ptestUDPARX)

        self.compareVals("testUDP-B TX", ptestUDPBTX)
        self.compareVals("testUDP-B RX", ptestUDPBRX)
        # print("\n")

        # remove all endpoints and cxs
        LFUtils.removePort(self.resource, self.sta_name, self.mgr_url)

        removeCX(self.mgr_url, cxNames)
        removeEndps(self.mgr_url, endpNames)

# ~class


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def main():
    lfjson_host = "localhost"
    lfjson_port = 8080
    parser = argparse.ArgumentParser(
        description="""LANforge Unit Test:  Connect Station to AP
Example:
./sta_connect.py --dest 192.168.100.209 --dut_ssid OpenWrt-2 --dut_bssid 24:F5:A2:08:21:6C
""")
    parser.add_argument("-d", "--dest", type=str, help="address of the LANforge GUI machine (localhost is default)")
    parser.add_argument("-o", "--port", type=int, help="IP Port the LANforge GUI is listening on (8080 is default)")
    parser.add_argument("-u", "--user", type=str, help="TBD: credential login/username")
    parser.add_argument("-p", "--passwd", type=str, help="TBD: credential password")
    parser.add_argument("--resource", type=str, help="LANforge Station resource ID to use, default is 1")
    parser.add_argument("--upstream_resource", type=str, help="LANforge Ethernet port resource ID to use, default is 1")
    parser.add_argument("--upstream_port", type=str, help="LANforge Ethernet port name, default is eth2")
    parser.add_argument("--radio", type=str, help="LANforge radio to use, default is wiphy0")
    parser.add_argument("--sta_mode", type=str,
                        help="LANforge station-mode setting (see add_sta LANforge CLI documentation, default is 0 (auto))")
    parser.add_argument("--dut_ssid", type=str, help="DUT SSID")
    parser.add_argument("--dut_passwd", type=str, help="DUT PSK password.  Do not set for OPEN auth")
    parser.add_argument("--dut_bssid", type=str, help="DUT BSSID to which we expect to connect.")

    args = parser.parse_args()
    if args.dest is not None:
        lfjson_host = args.dest
    if args.port is not None:
        lfjson_port = args.port

    staConnect = StaConnect(lfjson_host, lfjson_port)

    if args.user is not None:
        staConnect.user = args.user
    if args.passwd is not None:
        staConnect.passwd = args.passwd
    if args.sta_mode is not None:
        staConnect.sta_mode = args.sta_mode
    if args.upstream_resource is not None:
        staConnect.upstream_resource = args.upstream_resource
    if args.upstream_port is not None:
        staConnect.upstream_port = args.upstream_port
    if args.radio is not None:
        staConnect.radio = args.radio
    if args.resource is not None:
        staConnect.resource = args.resource
    if args.dut_passwd is not None:
        staConnect.dut_passwd = args.dut_passwd
    if args.dut_bssid is not None:
        staConnect.dut_bssid = args.dut_bssid
    if args.dut_ssid is not None:
        staConnect.dut_ssid = args.dut_ssid

    staConnect.run()
    run_results = staConnect.get_result_list()


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


if __name__ == "__main__":
    main()
