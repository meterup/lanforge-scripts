#!/usr/bin/env python3
"""
NAME: lf_cleanup.py

PURPOSE: clean up stations, cross connects and endpoints

EXAMPLE:  ./lf_cleanup.py --mgr <lanforge ip>

Copyright 2021 Candela Technologies Inc
License: Free to distribute and modify. LANforge systems must be licensed.
"""
import sys
import os
import importlib
import argparse
import time
import logging

if sys.version_info[0] != 3:
    print("This script requires Python 3")
    exit(1)

sys.path.append(os.path.join(os.path.abspath(__file__ + "../../../")))

LFUtils = importlib.import_module("py-json.LANforge.LFUtils")
realm = importlib.import_module("py-json.realm")
Realm = realm.Realm
logger = logging.getLogger(__name__)
lf_logger_config = importlib.import_module("py-scripts.lf_logger_config")


class lf_clean(Realm):
    def __init__(self,
                 host="localhost",
                 port=8080,
                 resource=None,
                 clean_cxs=None,
                 clean_endp=None,
                 clean_sta=None,
                 sanitze_mgr=None):
        super().__init__(lfclient_host=host,
                         lfclient_port=port),
        self.host = host
        self.port = port
        self.resource = resource
        self.clean_cxs = clean_cxs
        self.clean_endp = clean_endp
        self.clean_sta = clean_sta
        self.sanitze_mgr = sanitze_mgr
        self.cxs_done = False
        self.endp_done = False
        self.sta_done = False
        self.sanitize_done = False
        self.br_done = False
        self.misc_done = False

    def cxs_clean(self):
        still_looking_cxs = True
        iterations_cxs = 1

        while still_looking_cxs and iterations_cxs <= 10:
            iterations_cxs += 1
            logger.info("cxs_clean: iterations_cxs: {iterations_cxs}".format(iterations_cxs=iterations_cxs))
            cx_json = super().json_get("cx")
            # logger.info(cx_json)
            endp_json = super().json_get("endp")
            # logger.info(endp_json)
            if cx_json is not None:
                logger.info("Removing old cross connects")
                # delete L3-CX based upon the L3-Endp name & the resource value from
                # the e.i.d of the associated L3-Endps
                for cx_name in list(cx_json):
                    # logger.info(cx_name)
                    if cx_name != 'handler' and cx_name != 'uri' and cx_name != 'empty':
                        for endp_num in endp_json['endpoint']:
                            # get L3-Endp e.i.d & name:
                            for endp_val in endp_num.values():
                                endp_eid = endp_val['entity id']
                                # logger.info(endp_eid)
                                endp_name = endp_val['name']
                                # logger.info(endp_name)
                                # if name + '-A' in endp_name or name + '-B' in endp_name:
                                if cx_name + '-A' in endp_name:
                                    endp_eid_split = endp_eid.split('.')
                                    # endp_eid_split[1] == realm resource value:
                                    resource_eid = str(endp_eid_split[1])
                                    # logger.info(resource_eid)
                                    if resource_eid in self.resource or 'all' in self.resource:
                                        req_url = "cli-json/rm_cx"
                                        data = {
                                            "test_mgr": "default_tm",
                                            "cx_name": cx_name
                                        }
                                        # logger.info(data)
                                        logger.info("Removing {cx_name}...".format(cx_name=cx_name))
                                        super().json_post(req_url, data)
                                        time.sleep(.5)
                time.sleep(1)
            else:
                logger.info("No cross connects found to cleanup")
                still_looking_cxs = False
                logger.info("clean_cxs still_looking_cxs {cxs_looking}".format(cxs_looking=still_looking_cxs))
            if not still_looking_cxs:
                self.cxs_done = True
            return still_looking_cxs

    def endp_clean(self):
        still_looking_endp = True
        iterations_endp = 0

        while still_looking_endp and iterations_endp <= 10:
            iterations_endp += 1
            logger.info("endp_clean: iterations_endp: {iterations_endp}".format(iterations_endp=iterations_endp))
            endp_json = super().json_get("endp")
            # logger.info(endp_json)
            cx_json = super().json_get("cx")
            # logger.info(cx_json)
            if endp_json is not None:
                logger.info("Removing old endpoints")
                for name in list(endp_json['endpoint']):
                    endp_name = list(name)[0]
                    # logger.info(endp_name)
                    # get existing L3-CX names:
                    if cx_json is not None:
                        for cx_name in list(cx_json):
                            # logger.info(cx_name)
                            if cx_name != 'handler' and cx_name != 'uri' and cx_name != 'empty':
                                # remove all L3-endps without an associated L3-CX:
                                if cx_name + '-A' not in endp_name and cx_name + '-B' not in endp_name:
                                    if name[list(name)[0]]["name"] == '':
                                        continue
                                    req_url = "cli-json/rm_endp"
                                    data = {
                                        "endp_name": list(name)[0]
                                    }
                                    # logger.info(data)
                                    logger.info("Removing {endp_name}...".format(endp_name=endp_name))
                                    super().json_post(req_url, data)
                                    time.sleep(.5)
                    # if there are no L3-CX's, remove all L3-Endps:
                    else:
                        if name[list(name)[0]]["name"] == '':
                            continue
                        req_url = "cli-json/rm_endp"
                        data = {
                            "endp_name": list(name)[0]
                        }
                        # logger.info(data)
                        logger.info("Removing {endp_name}...".format(endp_name=endp_name))
                        super().json_post(req_url, data)
                        time.sleep(.5)
                time.sleep(1)
            else:
                logger.info("No endpoints found to cleanup")
                still_looking_endp = False
                logger.info("clean_endp still_looking_endp {ednp_looking}".format(ednp_looking=still_looking_endp))
            if not still_looking_endp:
                self.endp_done = True
            return still_looking_endp

    def sta_clean(self):
        still_looking_sta = True
        iterations_sta = 0

        while still_looking_sta and iterations_sta <= 10:
            iterations_sta += 1
            logger.info("sta_clean: iterations_sta: {iterations_sta}".format(iterations_sta=iterations_sta))
            try:
                sta_json = super().json_get("/port/?fields=alias".format(resource=self.resource))['interfaces']
                # logger.info(sta_json)
            except TypeError:
                sta_json = None
                logger.info("sta_json set to None")

            # get and remove current stations
            if sta_json is not None:
                logger.info("Removing old stations ")
                for name in list(sta_json):
                    for alias in list(name):
                        info = self.name_to_eid(alias)
                        sta_resource = str(info[1])
                        if sta_resource in self.resource or 'all' in self.resource:
                            # logger.info("alias {alias}".format(alias=alias))
                            if 'sta' in alias:
                                info = self.name_to_eid(alias)
                                req_url = "cli-json/rm_vlan"
                                data = {
                                    "shelf": info[0],
                                    "resource": info[1],
                                    "port": info[2]
                                }
                                # logger.info(data)
                                logger.info("Removing {alias}...".format(alias=alias))
                                super().json_post(req_url, data)
                                time.sleep(.5)
                            if 'wlan' in alias:
                                info = self.name_to_eid(alias)
                                req_url = "cli-json/rm_vlan"
                                data = {
                                    "shelf": info[0],
                                    "resource": info[1],
                                    "port": info[2]
                                }
                                # logger.info(data)
                                logger.info("Removing {alias}...".format(alias=alias))
                                super().json_post(req_url, data)
                                time.sleep(.5)
                            if 'moni' in alias:
                                info = self.name_to_eid(alias)
                                req_url = "cli-json/rm_vlan"
                                data = {
                                    "shelf": info[0],
                                    "resource": info[1],
                                    "port": info[2]
                                }
                                # logger.info(data)
                                logger.info("Removing {alias}...".format(alias=alias))
                                super().json_post(req_url, data)
                                time.sleep(.5)
                            if 'Unknown' in alias:
                                info = self.name_to_eid(alias)
                                req_url = "cli-json/rm_vlan"
                                data = {
                                    "shelf": info[0],
                                    "resource": info[1],
                                    "port": info[2]
                                }
                                # logger.info(data)
                                logger.info("Removing {alias}...".format(alias=alias))
                                super().json_post(req_url, data)
                                time.sleep(.5)
                time.sleep(1)
            else:
                logger.info("No stations found to cleanup")
                still_looking_sta = False
                logger.info("clean_sta still_looking_sta {sta_looking}".format(sta_looking=still_looking_sta))
            if not still_looking_sta:
                self.sta_done = True
            return still_looking_sta

    # cleans all gui or script created objects from Port Mgr tab
    def sanitize_all(self):
        still_looking_san = True
        iterations_san = 0

        while still_looking_san and iterations_san <= 10:
            iterations_san += 1
            logger.info("sta_clean: iterations_san: {iterations_san}".format(iterations_san=iterations_san))
            try:
                sanitize_json = super().json_get("/port/?fields=port+type,alias".format(resource=self.resource))['interfaces']
                # logger.info(sanitize_json)
                # logger.info(len(sanitize_json))
            except TypeError:
                sanitize_json = None
                logger.info("sanitize_json set to None")

            # get and remove LF Port Mgr objects
            if sanitize_json is not None:
                logger.info("Removing old stations ")
                '''
                NOTE: [LF system - APU2/CT521a]: if wiphy radios are deleted
                      run the following command and reboot to fix:
                      /root/lf_kinstall.pl --lfver 5.4.5 --do_sys_reconfig
                '''
                for name in list(sanitize_json):
                    # logger.info(name)
                    # alias is the eid (ex: 1.1.eth0)
                    for alias in list(name):
                        # logger.info(alias)
                        port_type = name[alias]['port type']
                        # logger.info(port_type)
                        if port_type != 'Ethernet' and port_type != 'WIFI-Radio' and port_type != 'NA':
                            info = self.name_to_eid(alias)
                            sanitize_resource = str(info[1])
                            if sanitize_resource in self.resource or 'all' in self.resource:
                                req_url = "cli-json/rm_vlan"
                                data = {
                                    "shelf": info[0],
                                    "resource": info[1],
                                    "port": info[2]
                                }
                                # logger.info(data)
                                logger.info("Removing {alias}...".format(alias=alias))
                                super().json_post(req_url, data)
                                time.sleep(.5)
                time.sleep(1)
            else:
                logger.info("No stations found to cleanup")
                still_looking_san = False
                logger.info("sanitize_all still_looking_san {still_looking_san}".format(still_looking_san=still_looking_san))
            if not still_looking_san:
                self.sanitize_done = True
            return still_looking_san

    def bridge_clean(self):
        still_looking_br = True
        iterations_br = 0

        while still_looking_br and iterations_br <= 10:
            iterations_br += 1
            logger.info("bridge_clean: iterations_br: {iterations_br}".format(iterations_br=iterations_br))
            try:
                # br_json = super().json_get("port/1/1/list?field=alias")['interfaces']
                br_json = super().json_get("/port/?fields=port+type,alias".format(resource=self.resource))['interfaces']
            except TypeError:
                br_json = None

            # get and remove current stations
            if br_json is not None:
                # logger.info(br_json)
                logger.info("Removing old bridges ")
                for name in list(br_json):
                    for alias in list(name):
                        port_type = name[alias]['port type']
                        # if 'br' in alias:
                        if 'Bridge' in port_type:
                            # logger.info(alias)
                            info = self.name_to_eid(alias)
                            bridge_resource = str(info[1])
                            if bridge_resource in self.resource or 'all' in self.resource:
                                req_url = "cli-json/rm_vlan"
                                data = {
                                    "shelf": info[0],
                                    "resource": info[1],
                                    "port": info[2]
                                }
                                # logger.info(data)
                                logger.info("Removing {alias}...".format(alias=alias))
                                super().json_post(req_url, data)
                                time.sleep(.5)
                time.sleep(1)
            else:
                logger.info("No bridges found to cleanup")
                still_looking_br = False
                logger.info("clean_bridge still_looking_br {br_looking}".format(br_looking=still_looking_br))
            if not still_looking_br:
                self.br_done = True
            return still_looking_br

    # Some test have various station names or a station named 1.1.eth2
    def misc_clean(self):
        still_looking_misc = True
        iterations_misc = 0

        while still_looking_misc and iterations_misc <= 10:
            iterations_misc += 1
            logger.info("misc_clean: iterations_misc: {iterations_misc}".format(iterations_misc=iterations_misc))
            try:
                # misc_json = super().json_get("port/1/1/list?field=alias")['interfaces']
                misc_json = super().json_get("/port/?fields=alias".format(resource=self.resource))['interfaces']
            except TypeError:
                misc_json = None

            # get and remove current stations
            if misc_json is not None:
                # logger.info(misc_json)
                logger.info("Removing misc station names phy, 1.1.eth (malformed station name) ")
                for name in list(misc_json):
                    for alias in list(name):
                        if 'phy' in alias and 'wiphy' not in alias:
                            # logger.info(alias)
                            info = self.name_to_eid(alias)
                            misc_resource = str(info[1])
                            if misc_resource in self.resource or 'all' in self.resource:
                                req_url = "cli-json/rm_vlan"
                                data = {
                                    "shelf": info[0],
                                    "resource": info[1],
                                    "port": info[2]
                                }
                                # logger.info(data)
                                logger.info("Removing {alias}...".format(alias=alias))
                                super().json_post(req_url, data)
                                time.sleep(.5)
                        if '1.1.1.1.eth' in alias:
                            logger.info('alias 1.1.1.1.eth {alias}'.format(alias=alias))
                            # need to hand construct for delete.
                            info = alias.split('.')
                            logger.info('info {info}'.format(info=info))
                            req_url = "cli-json/rm_vlan"
                            # info_2 = "{info2}.{info3}.{info4}".format(info2=info[2], info3=info[3], info4=info[4])
                            misc_resource = str(info[3])
                            if misc_resource in self.resource or 'all' in self.resource:
                                data = {
                                    "shelf": info[2],
                                    "resource": info[3],
                                    "port": info[4]
                                }
                                # logger.info(data)
                                logger.info("Removing {alias}...".format(alias=alias))
                                super().json_post(req_url, data)
                                time.sleep(.5)
                time.sleep(1)
            else:
                logger.info("No misc found to cleanup")
                still_looking_misc = False
                logger.info("clean_misc still_looking_misc {misc_looking}".format(misc_looking=still_looking_misc))
            if not still_looking_misc:
                self.misc_done = True
            return still_looking_misc

    '''
        1: delete cx
        2: delete endp
        3: delete sta
        when deleting sta first, you will end up with phantom CX
    '''
    def cleanup(self):
        if self.clean_cxs:
            # also clean the endp when cleaning cxs
            still_looking_cxs = self.cxs_clean()
            still_looking_endp = self.endp_clean()
            logger.info("clean_cxs: still_looking_cxs {looking_cxs} still_looking_endp {looking_endp}".format(
                looking_cxs=still_looking_cxs, looking_endp=still_looking_endp))

        if self.clean_endp and not self.clean_cxs:
            still_looking_endp = self.endp_clean()
            logger.info("clean_endp: still_looking_endp {looking_endp}".format(looking_endp=still_looking_endp))

        if self.sanitze_mgr:
            still_looking_san = self.sanitize_all()
            logger.info("clean_sta: still_looking_san {looking_sta}".format(looking_sta=still_looking_san))
        '''
        if self.clean_sta:
            still_looking_sta = self.sta_clean()
            logger.info("clean_sta: still_looking_sta {looking_sta}".format(looking_sta=still_looking_sta))

        if self.clean_br:
            still_looking_br = self.bridge_clean()
            logger.info("clean_br: still_looking_br {looking_br}".format(looking_br=still_looking_br))
        '''

        if self.clean_misc:
            still_looking_misc = self.misc_clean()
            logger.info("clean_misc: still_looking_misc {looking_misc}".format(looking_misc=still_looking_misc))


def main():

    parser = argparse.ArgumentParser(
        prog='lf_cleanup.py',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''\
            Clean up cxs and endpoints
            ''',
        description='''\
lf_cleanup.py:
--------------------
Generic command layout:

python3 ./lf_clean.py --mgr MGR

    default port is 8080

    clean up stations, cxs and enspoints.
    NOTE: will only cleanup what is present in the GUI
            So will need to iterate multiple times with script
            ''')
    parser.add_argument(
        '--mgr',
        '--lfmgr',
        help='--mgr <hostname for where LANforge GUI is running>',
        default='localhost')
    parser.add_argument(
        '--resource',
        '--res',
        help='--resource <realm resource> to clear a specific resource, or --resource <all> to cleanup all resources',
        default='1')
    parser.add_argument(
        '--cxs',
        help="--cxs, this will clear all the endps and cxs",
        action='store_true')
    parser.add_argument(
        '--endp',
        help="--endp, this will clear all the endps",
        action='store_true')
    parser.add_argument(
        '--sta',
        help="--sta, this will clear all the stations generated by a script",
        action='store_true')
    parser.add_argument(
        '--sanitize',
        help="--sanitze, this will clear all the created objects (wifi-sta, mac-vlans, vap, br)",
        action='store_true')
    parser.add_argument(
        '--br',
        help="--br, this will clear all the bridges",
        action='store_true')
    parser.add_argument(
        '--misc',
        help="--misc, this will clear sta with names phy (not wiphy) and 1.1.eth stations",
        action='store_true')
    parser.add_argument(
        "--debug",
        help="enable debugging",
        action="store_true")
    parser.add_argument(
        "--lf_logger_config_json",
        help="--lf_logger_config_json <json file> , json configuration of logger")

    args = parser.parse_args()

    # set up logger
    logger_config = lf_logger_config.lf_logger_config()
    if args.lf_logger_config_json:
        # logger_config.lf_logger_config_json = "lf_logger_config.json"
        logger_config.lf_logger_config_json = args.lf_logger_config_json
        logger_config.load_lf_logger_config()

    if args.debug:
        logger_config.set_level("debug")

    # if args.cxs or args.endp or args.sta or args.br or args.misc:
    if args.cxs or args.endp or args.sta or args.br or args.misc or args.sanitize:
        clean = lf_clean(host=args.mgr, resource=args.resource, clean_cxs=args.cxs, clean_endp=args.endp, clean_sta=args.sta, sanitze_mgr=args.sanitize)
        logger.info("cleaning cxs: {cxs} endpoints: {endp} stations: {sta} start".format(cxs=args.cxs, endp=args.endp, sta=args.sta))
        if args.cxs:
            logger.info("cleaning cxs will also clean endp")
            clean.cxs_clean()
            clean.endp_clean()
        if args.endp and not args.cxs:
            clean.endp_clean()
        if args.sta:
            clean.sta_clean()
        if args.sanitize:
            clean.sanitize_all()
        if args.br:
            clean.bridge_clean()
        if args.misc:
            clean.misc_clean()

        logger.info("Clean done")
        # print("Clean  cxs_done {cxs_done} endp_done {endp_done} sta_done {sta_done}"
        #    .format(cxs_done=clean.cxs_done,endp_done=clean.endp_done,sta_done=clean.sta_done))
    else:
        logger.info("please add option of --cxs ,--endp, --sta , --br, --misc to clean")


if __name__ == "__main__":
    main()
