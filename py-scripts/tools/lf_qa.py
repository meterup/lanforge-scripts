#!/usr/bin/env python3
'''
File: read kpi.csv place in sql database, create png of historical kpi and present graph on dashboard
Usage: kpi_csv_sq.py --store --png --show --path <path to directories to traverse> --database <name of database> 
Example: kpi_csv_sq.py --show  (show dashboard generated from database)
Example: kpi_csv_sq.py --store --png --show --path <path to read kpi.csv> (read kpi.csv store to database, write png, show dashboard )

'''
# visit http://127.0.0.1:8050/ in your web browser.

import sys
import os
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import pandas as pd
import sqlite3
import argparse
from  pathlib import Path
import time

# lf_report is from the parent of the current file
dir_path = os.path.dirname(os.path.realpath(__file__))
parent_dir_path = os.path.abspath(os.path.join(dir_path, os.pardir))
sys.path.insert(0, parent_dir_path)

from lf_report import lf_report
sys.path.append('/')

# Any style components can be used
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
class csv_sqlite_dash():
    def __init__(self,
                _path = '.',
                _file = 'kpi.csv',
                _database = 'qa_db',
                _table = 'qa_table',
                _server = 'http://192.168.95.6/',
                _cut = '/home/lanforge/',
                _png = False):
        self.path = _path
        self.file = _file
        self.database = _database
        self.table = _table
        self.server = _server
        self.cut = _cut
        self.png = _png
        self.png_generated = False
        self.kpi_list = []
        self.html_list = []
        self.conn = None
        self.df = pd.DataFrame()
        self.plot_figure = []
        self.children_div = []
        self.html_results =""
        self.test_rig_list = []
        self.server_html_reports = self.server + 'html-reports/' #TODO : hard coded - is this needed? have server
        self.server_started = False
        self.dut_model_num_list = "NA"
        self.dut_sw_version_list = "NA"
        self.dut_hw_version_list = "NA"
        self.dut_serial_num_list = "NA"

        self.app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
        # https://community.plotly.com/t/putting-a-dash-instance-inside-a-class/6097/3
        #https://dash.plotly.com/dash-html-components/button
        #self.app.callback(dash.dependencies.Output('container-button-basic', 'children'),
        #                [dash.dependencies.Input(component_id ='submit-val', component_property ='n_clicks')])(self.show)

    # Helper methods
    def get_test_rig_list(self):
        return self.test_rig_list

    def get_html_results(self):
        return self.html_results

    def get_dut_info(self):
        #try:
        print("DUT: {DUT} SW:{SW} HW:{HW} SN:{SN}"
            .format(DUT=self.dut_model_num_list,SW=self.dut_sw_version_list,HW=self.dut_hw_version_list,SN=self.dut_serial_num_list))

        # use the list length to get the latest DUT - 
        dut_model_num_list_len = len(self.dut_model_num_list)
        print("dut_model_num_list_len {len}".format(len=dut_model_num_list_len))
        dut_sw_version_list_lem = len(self.dut_sw_version_list)
        dut_hw_version_list_len = len(self.dut_hw_version_list)
        dut_serial_num_list_len = len(self.dut_serial_num_list)

        if dut_model_num_list_len > 0 and self.dut_model_num_list[-1] != None:
            dut = self.dut_model_num_list[-1]
            print("LIST (-1) {list}".format(list=self.dut_model_num_list[-1]))
            print("DUT (-1) {dut}".format(dut=dut))
        elif dut_model_num_list_len > 1 and self.dut_model_num_list[-2] != None:
            dut = self.dut_model_num_list[-2]
            print("LIST (-2) {list}".format(list=self.dut_model_num_list[-2]))
            print("DUT (-2) {dut}".format(dut=dut))
        else:
            dut = 'NA'            

        if dut_sw_version_list_lem > 0 and self.dut_sw_version_list[-1] != None:
            sw_ver = self.dut_sw_version_list[-1]
        elif dut_sw_version_list_lem > 1 and self.dut_sw_version_list[-2] != None:
            sw_ver = self.dut_sw_version_list[-2]
        else:
            sw_ver = 'NA'            
        
        if dut_hw_version_list_len > 0 and self.dut_hw_version_list[-1] != None:
            hw_ver = self.dut_hw_version_list[-1]
        elif dut_hw_version_list_len > 1 and self.dut_hw_version_list[-2] != None:
            hw_ver = self.dut_hw_version_list[-2]
        else:
            hw_ver = 'NA'            

        if dut_serial_num_list_len > 0 and self.dut_serial_num_list[-1] != None:
            sn = self.dut_serial_num_list[-1]
        elif dut_serial_num_list_len > 1 and self.dut_serial_num_list[-2] != None:
            sn = self.dut_serial_num_list[-2]
        else:
            sn = 'NA'            

        print("DUT lists: {DUT} SW:{SW} HW:{HW} SN:{SN}"
            .format(DUT=self.dut_model_num_list,SW=self.dut_sw_version_list,HW=self.dut_hw_version_list,SN=self.dut_serial_num_list))

        dut_dict = {
            'DUT':[dut],
            'SW version': [sw_ver],
            'HW version':[hw_ver],
            'SN':[sn]
        }
        print('DUT dict: {dict}'.format(dict=dut_dict))
        dut_info_df = pd.DataFrame(dut_dict)
        print("DUT df from dict: {df}".format(df=dut_info_df))

        return dut_info_df

    def get_parent_path(self,_path):
        parent_path = os.path.dirname(_path)
        return parent_path

    def get_test_id_test_tag(self,_kpi_path):
        test_tag = "NA"
        try:
            kpi_df = pd.read_csv(_kpi_path, sep='\t')
            test_id_list = list(kpi_df['test-id']) 
            test_id = list(set(test_id_list))
            test_id = test_id[-1] # done to get element of list
            test_tag_list = list(kpi_df['test-tag']) 
            test_tag = list(set(test_tag_list))
            test_tag = test_tag[-1] # done to get element of list
        except:
            print("exception reading csv _kpi_path {}".format(_kpi_path))
        return test_id , test_tag

    #TODO pass in list to lf_report
    #  <table border="1" class="dataframe">
    def get_suite_html(self):
        suite_html_results =  """ 
            <table class="dataframe" border="1">
                    <thead>
                        <tr style="text-align: center;">
                          <th>Test</th>
                          <th>Test_Tag</th>
                          <th>Links</th>
                        </tr>
                    </thead>
                <tbody>
        """
               
        path = Path(self.path)
        pdf_info_list= list(path.glob('**/*.pdf'))  # Hard code for now 
        print("pdf_info_list {}".format(pdf_info_list))
        for pdf_info in pdf_info_list:
            if "lf_qa" in str(pdf_info):
                pass
            else:
                pdf_base_name = os.path.basename(pdf_info)
                if "check" in str(pdf_base_name):
                    pass
                else:
                    parent_path = os.path.dirname(pdf_info)
                    pdf_path = os.path.join(parent_path,pdf_base_name)
                    pdf_path = self.server + pdf_path.replace(self.cut,'')
                    html_path = os.path.join(parent_path,"index.html")
                    html_path = self.server + html_path.replace(self.cut,'')
                    kpi_path = os.path.join(parent_path,"kpi.csv")
                    test_id, test_tag = self.get_test_id_test_tag(kpi_path)
                    suite_html_results += """
                    <tr style="text-align: center; margin-bottom: 0; margin-top: 0;">
                        <td>{}</td><td>{}</td><td><a href="{}" target="_blank">html</a> / <a href="{}" target="_blank">pdf</a></td></tr>
                    """.format(test_id,test_tag,html_path,pdf_path)
        suite_html_results += """
                    </tbody>
                </table>
                <br> 
                """

        return suite_html_results

    def get_kpi_chart_html(self):
        kpi_chart_html =  """ 
            <table border="0">
                <tbody>
        """
        path = Path(self.path)
        kpi_chart_list= list(path.glob('**/kpi-chart*.png'))  # Hard code for now 
        table_index = 0 
        for kpi_chart in kpi_chart_list:
            parent_path = os.path.dirname(kpi_chart)
            kpi_path = os.path.join(parent_path,"kpi.csv")
            test_tag , test_id = self.get_test_id_test_tag(kpi_path)
            kpi_chart = os.path.abspath(kpi_chart) # Path returns a list of objects
            kpi_chart = self.server + kpi_chart.replace(self.cut,'')
            if "print" in kpi_chart:
                pass
            else: 
                if (table_index %2) == 0:           
                    kpi_chart_html += """<tr>"""
                kpi_chart_html += """
                    <td>
                        {test_tag}  {test_id}
                    </td>
                    <td>
                        <a href="{kpi_chart_0}"  target="_blank">
                            <img src="{kpi_chart_1}" style="width:400px;max-width:400px" title="{kpi_chart_2}">
                        </a> 
                    </td>
                """.format(test_tag=test_tag,test_id=test_id,kpi_chart_0=kpi_chart,kpi_chart_1=kpi_chart,kpi_chart_2=kpi_chart)
                table_index += 1
                if (table_index %2) == 0:
                    kpi_chart_html += """</tr>"""
        if (table_index %2) != 0:
                    kpi_chart_html += """</tr>"""
        kpi_chart_html += """</tbody></table>"""
        return kpi_chart_html

    # information on sqlite database
    # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_sql.html
    def store(self):
        print("reading kpi and storing in db {}".format(self.database))
        path = Path(self.path)
        self.kpi_list = list(path.glob('**/kpi.csv'))  # Hard code for now 

        if not self.kpi_list:
            print("WARNING: used --store , no new kpi.csv found, check input path or remove --store from command line")

        for kpi in self.kpi_list: #TODO note empty kpi.csv failed test 
            df_kpi_tmp = pd.read_csv(kpi, sep='\t')  
            df_kpi_tmp['kpi_path'] = str(kpi).replace('kpi.csv','')  # only store the path to the kpi.csv file
            df_kpi_tmp = df_kpi_tmp.append(df_kpi_tmp, ignore_index=True)
            self.df = self.df.append(df_kpi_tmp, ignore_index=True)

        self.conn = sqlite3.connect(self.database) 
        try:
            self.df.to_sql(self.table,self.conn,if_exists='append')
        except:
            print("attempt to append to database with different column layout, casused exception, input new name --database <new name>")            
            exit(1)
        self.conn.close()

    def generate_graph_png(self):
        print("generate png and html to display, generate time: {}".format(time.time()))

        #https://datacarpentry.org/python-ecology-lesson/09-working-with-sql/index.html-
        self.conn = sqlite3.connect(self.database)
        df3 = pd.read_sql_query("SELECT * from {}".format(self.table) ,self.conn) #current connection is sqlite3 /TODO move to SQLAlchemy
        # sort by date from oldest to newest. 
        try:
            df3 = df3.sort_values(by='Date')
        except:
            print("Database empty: KeyError(key) when sorting by Date, check Database name, path to kpi, typo in path, exiting")
            exit(1)
        self.conn.close()

        # graph group and test-tag are used for detemining the graphs, can use any columns
        # the following list manipulation removes the duplicates
        graph_group_list = list(df3['Graph-Group'])
        graph_group_list = list(set(graph_group_list)) 
        print("graph_group_list: {}".format(graph_group_list))

        test_tag_list = list(df3['test-tag'])
        test_tag_list = list(set(test_tag_list))
        print("test_tag_list: {}".format(test_tag_list) )
        
        test_rig_list = list(df3['test-rig'])
        test_rig_list = list(set(test_rig_list))
        self.test_rig_list = test_rig_list
        print("test_rig_list: {}".format(test_rig_list) )

        self.children_div.append(html.A('html_reports', href=self.server_html_reports, target='_blank'))
        for test_rig in test_rig_list:
            for test_tag in test_tag_list:
                for group in graph_group_list:
                    df_tmp = df3.loc[(df3['test-rig'] == test_rig) & (df3['Graph-Group'] == str(group)) & (df3['test-tag'] == str(test_tag))]
                    if df_tmp.empty == False:

                        df_tmp = df_tmp.sort_values(by='Date')
                        test_id_list = list(df_tmp['test-id'])
                        kpi_path_list = list(df_tmp['kpi_path'])
                        # get Device Under Test Information , 
                        # the set reduces the redundency , list puts it back into a list
                        self.dut_model_num_list = list(set(list(df_tmp['dut-model-num'])))
                        self.dut_sw_version_list = list(set(list(df_tmp['dut-sw-version'])))
                        self.dut_hw_version_list = list(set(list(df_tmp['dut-hw-version'])))
                        self.dut_serial_num_list = list(set(list(df_tmp['dut-serial-num'])))
                        print("DUT: {DUT} SW:{SW} HW:{HW} SN:{SN}"
                            .format(DUT=self.dut_model_num_list,SW=self.dut_sw_version_list,HW=self.dut_hw_version_list,SN=self.dut_serial_num_list))

                        units_list = list(df_tmp['Units'])
                        print("GRAPHING::: test-rig {} test-tag {}  Graph-Group {}".format(test_rig,test_tag,group))
                        kpi_fig = (px.scatter(df_tmp, x="Date", y="numeric-score",
                             color="short-description", hover_name="short-description",
                             size_max=60)).update_traces(mode='lines+markers')

                        kpi_fig.update_layout(
                            title="{} : {} : {} : {}".format(test_id_list[-1], group, test_tag, test_rig),
                            xaxis_title="Time",
                            yaxis_title="{}".format(units_list[-1]),
                            xaxis = {'type' : 'date'}
                        )
                        # save the figure - figures will be over written png 
                        # for testing 
                        png_server_img = ''
                        #TODO work out when to generate the png files
                        if self.png:
                            if self.png_generated:
                                pass
                            else:
                                print("generate png and kpi images from kpi kpi_path:{}".format(df_tmp['kpi_path']))
                                # generate png img path
                                png_path = os.path.join(kpi_path_list[-1],"{}_{}_{}_kpi.png".format( group, test_tag, test_rig))
                                png_path = png_path.replace(' ','')
                                # generate html graphics path
                                html_path = os.path.join(kpi_path_list[-1],"{}_{}_{}_kpi.html".format( group, test_tag, test_rig))
                                html_path = html_path.replace(' ','')
                                # NOTE: html links to png do not like spaces
                                png_server_img = self.server + png_path.replace(self.cut,'')
                                # generate png image
                                try:
                                    kpi_fig.write_image(png_path,scale=1,width=1200,height=350)
                                except:
                                    print("ERROR: {database} Was correct database passed in, moved or duplicates of same name?".format(database=self.database))
                                #https://plotly.com/python/interactive-html-export/
                                # generate html image (interactive)
                                kpi_fig.write_html(html_path)
                                # generate link for dashboard
                                self.children_div.append(html.Img(src=png_server_img))
                                #HERE add clickable link
                                img_kpi_html_path = self.server + html_path
                                img_kpi_html_path = img_kpi_html_path.replace(self.cut,'')

                                self.html_results += """
                                <a href={img_kpi_html_path} target="_blank">
                                    <img src={png_server_img}>
                                </a>
                                """.format(img_kpi_html_path=img_kpi_html_path,png_server_img=png_server_img)

                        # WARNING: DO NOT USE os.path.join will use the path for where the script is RUN which can be container.
                        # Constructed path to server manually.  
                        # link to interactive results
                        kpi_html_path = self.server + html_path
                        kpi_html_path = kpi_html_path.replace(self.cut,'')
                        self.children_div.append(html.Br())
                        self.html_results +="""<br>"""
                        self.children_div.append(html.A('{test_id}_{group}_{test_tag}_{test_rig}_kpi.html'
                        .format(test_id=test_id_list[-1], group=group, test_tag=test_tag, test_rig=test_rig),
                            href=kpi_html_path, target='_blank'))

                        # link to full test results
                        report_index_html_path = self.server + kpi_path_list[-1] + "index.html"
                        report_index_html_path = report_index_html_path.replace(self.cut,'')
                        self.children_div.append(html.Br())
                        #self.html_results +="""<br>"""
                        self.children_div.append(html.A('{test_id}_{group}_{test_tag}_{test_rig}_report.html'
                        .format(test_id=test_id_list[-1], group=group, test_tag=test_tag, test_rig=test_rig),
                            href=report_index_html_path, target='_blank'))
                        self.html_results +="""<a href={report_index_html_path} target="_blank">{test_id}_{group}_{test_tag}_{test_rig}_Report </a>
                        """.format(report_index_html_path=report_index_html_path,test_id=test_id_list[-1], group=group, test_tag=test_tag, test_rig=test_rig)
                        self.children_div.append(html.Br())
                        self.children_div.append(html.Br())
                        self.children_div.append(html.Br())
                        self.html_results +="""<br>"""
                        self.html_results +="""<br>"""
                        self.html_results +="""<br>"""
        
        # TODO see if this stops the regenration of the graphs each time
        self.png_generated = True


    # access from server
    # https://stackoverflow.com/questions/61678129/how-to-access-a-plotly-dash-app-server-via-lan
    #def show(self,n_clicks):
    def show(self):
        # gererate dash display
        #print("refreshes: {}".format(n_clicks))
        self.generate_graph_png()
        if not self.children_div:
            print("NOTE: test-tag may not be present in the kpi thus no results generated")
        print("show: {}".format(time.time()))
        self.app.layout = html.Div([
            html.Div(id='my-output'),
            html.H1(children= "LANforge Testing",className="lanforge",
            style={'color':'green','text-align':'center'}),
            #For dash refresh # html.Button('Submit Recalculate',id='submit-val', n_clicks=0),  
            #For dash refresh # html.Div(id='container-button-basic', children='to recalculate hit submit'),
            html.H2(children= "Results",className="ts1",
            style={'color':'#00361c','text-align':'left'}),
            # images_div is already a list, children = a list of html components
            # remove scrolling : html.Div(children= self.children_div, style={"maxHeight": "600px", "overflow": "scroll"} ), 
            html.Div(children= self.children_div ), 
            html.A('www.candelatech.com',href='http://www.candelatech.com', target='_blank',
            style={'color':'#00361c','text-align':'left'}),
        ])

        # save as standalone files
        #https://plotly.com/python/static-image-export/
        
        if self.server_started:
            print("refresh complete")
            pass
        else:
            self.server_started = True
            print("self.server_started {}".format(self.server_started))
            #NOTE: the server_started flag needs to be set prior to run_server (or you get to debug an infinite loop)
            #NOTE: debug=False will prevent init going though twice, also stops auto reload when editing code
            self.app.run_server(host= '0.0.0.0', debug=True)
            # host = '0.0.0.0'  allows for remote access,  local debug host = '127.0.0.1'
            # app.run_server(host= '0.0.0.0', debug=True) 

def main():

    parser = argparse.ArgumentParser(
        prog='kpi_csv_sq.py',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''\
        read kpi.csv into sqlite database , save png of history and preset on dashboard

            ''',
        description='''\
File: read kpi.csv place in sql database, create png of historical kpi and present graph on dashboard
Usage: kpi_csv_sq.py --store --png --show --path <path to directories to traverse> --database <name of database> 
Example: kpi_csv_sq.py --show  (show dashboard generated from database)
Example: kpi_csv_sq.py --store --png --show --path <path to read kpi.csv> (read kpi.csv store to database, write png, show dashboard )

        ''')
    parser.add_argument('--path', help='--path top directory path to kpi if regererating database or png files',default='')
    parser.add_argument('--file', help='--file kpi.csv  default: kpi.csv',default='kpi.csv') #TODO is this needed
    parser.add_argument('--database', help='--database qa_test_db  default: qa_test_db',default='qa_test_db')
    parser.add_argument('--table', help='--table qa_table  default: qa_table',default='qa_table')
    parser.add_argument('--server', help='--server http://<server ip>/   default: http://192.168.95.6/',default='http://192.168.95.6/')
    parser.add_argument('--cut', help='--cut /home/lanforge/ used to adjust server path default: /home/lanforge/',default='/home/lanforge/')
    parser.add_argument('--store', help='--store , store kpi to db, action store_true',action='store_true')
    parser.add_argument('--png', help='--png,  generate png for kpi in path, generate display, action store_true',action='store_true')
    parser.add_argument('--show', help='--show generate display and show dashboard, action store_true',action='store_true')
    parser.add_argument('--dir', help="--dir <results directory> default lf_qa", default="lf_qa")

    args = parser.parse_args()

    __path = args.path
    __file = args.file
    __database = args.database
    __table = args.table
    __server = args.server
    __png = args.png
    __dir = args.dir
    __cut = args.cut

    # needed for refresh button 
    # n_clicks = 0

    print("config: path:{} file:{} database:{} table:{} server:{} store:{} png:{} show:{} "
        .format(__path,__file,__database,__table,__server,args.store, args.png,args.show))

    if(__path == '' and args.store == True):
        print("--path <path of kpi.csv> must be entered if --store ,  exiting")
        exit(1)

    if(args.png == True and args.store == False):
        print("if --png set to create png files then --store must also be set, exiting")
        exit(1)

    if(args.png == True and args.show == True):
        print("generating png files will effect initial display performance")

    if args.store == False and args.png == False and args.show == False:
        print("Need to enter an action of --store --png --show ")

    # create report class for reporting
    report = lf_report(_path = __path,
                       _results_dir_name =__dir,
                       _output_html="lf_qa.html",
                       _output_pdf="lf_qa.pdf" )        

    csv_dash = csv_sqlite_dash(
                _path = __path,
                _file = __file,
                _database = __database,
                _table = __table,
                _server = __server,
                _cut = __cut,
                _png = __png)
    if args.store:
        csv_dash.store()
    if args.png:
        csv_dash.generate_graph_png()
        
        # generate output reports
        report.set_title("LF QA: Verification Test Run")
        report.build_banner_left()
        report.start_content_div2()
        report.set_obj_html("Objective", "QA Verification")
        report.build_objective()
        report.set_table_title("Device Under Test")
        report.build_table_title()
        dut_info_df = csv_dash.get_dut_info()
        print("DUT Results: {}".format(dut_info_df))
        report.set_table_dataframe(dut_info_df)
        report.build_table()
        
        test_rig_list = csv_dash.get_test_rig_list()
        report.set_table_title("Test Rig: {} Links".format(test_rig_list[-1])) # keep the list, currently one test bed results
        report.build_table_title()

        pdf_link_path = report.get_pdf_path()
        pdf_link_path = __server + pdf_link_path.replace(__cut,'')
        report.build_pdf_link("PDF_Report",pdf_link_path)

        report_path = report.get_path()
        report_path = __server + report_path.replace(__cut,'')
        report.build_link("Current Test Suite Results Directory",report_path)

        report_parent_path = report.get_parent_path()
        report_parent_path = __server + report_parent_path.replace(__cut,'')
        report.build_link("All Test-Rig Test Suites Results Directory",report_parent_path)

 # links table for tests TODO : can this be a table
        report.set_table_title("Test Suite")
        report.build_table_title()
        suite_html = csv_dash.get_suite_html()
        print("suite_html {}".format(suite_html))
        report.set_custom_html(suite_html)
        report.build_custom()

        # png summary of test
        report.set_table_title("Suite Summary")
        report.build_table_title()
        kpi_chart_html = csv_dash.get_kpi_chart_html()
        report.set_custom_html(kpi_chart_html)
        report.build_custom()
        

        report.set_table_title("QA Test Results")
        report.build_table_title()
        # report.set_text("lanforge-scripts git sha: {}".format(git_sha))
        # report.build_text()
        html_results = csv_dash.get_html_results()
        report.set_custom_html(html_results)
        report.build_custom()
        report.build_footer()
        html_report = report.write_html_with_timestamp()
        print("html report: {}".format(html_report))
        try:
            report.write_pdf_with_timestamp()
        except:
            print("exception write_pdf_with_timestamp()")

    if args.show:        
        #csv_dash.show(n_clicks)
        csv_dash.show()

if __name__ == '__main__':
    main()
    