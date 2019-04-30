import sys
import configparser
from pathlib import Path
import json
import re
import requests
import base64
from datetime import datetime
from jsonmerge import merge
from jsonmerge import Merger

#currently using WeeklyHoldings env
#python catdate.py 01-13-2019 01-16-2019
def main(arglist):
    # Read config file
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    startdate, enddate, save_dir = arglist
    #print('Save dir:' + save_dir)
    out_dir = Path(save_dir)
    
    # jsonmerge setup
    schema = {"properties":{"entries":{"mergeStrategy":"append"}}}
    merger = Merger(schema)
    
    # Read create list criteria from file, inserting dates and starting bib number
    with open('catdate_nodates_bib_limiter.json', 'r') as file:
        data = file.read().replace('xx-xx-xxxx', startdate).replace('yy-yy-yyyy', enddate).replace('bxxxxxxx', 'b1000000')
    #print(data)
    
    # Authenticate to get token, using Client Credentials Grant https://techdocs.iii.com/sierraapi/Content/zReference/authClient.htm
    key_secret = config.get('Sierra API', 'key') + ':' + config.get('Sierra API', 'secret')
    #print(key_secret)
    key_secret_encoded = base64.b64encode(key_secret.encode('UTF-8')).decode('UTF-8')
    #print(encoded)
    headers = {'Authorization': 'Basic ' + key_secret_encoded,
                'Content-Type': 'application/x-www-form-urlencoded'}
    #print(headers)
    response = requests.request('POST', 'https://catalog.lib.jmu.edu/iii/sierra-api/v5/token', headers=headers)
    #print(response.text)
    j = response.json()
    token = j['access_token']
    auth = 'Bearer ' + token
    headers = {
        'Accept': 'application/json',
        'Authorization': auth}
    
    # Retrieve first set of record IDs for create list query
    response = requests.request('POST', 'https://catalog.lib.jmu.edu/iii/sierra-api/v5/bibs/query?offset=0&limit=2000', headers=headers, data=data) #FYI this takes a long time to run
    #print('request sent')
    #print(response.text)
    j = response.json()
    records_returned = j['total']
    print('Records returned:', j['total'])
    j_all = j
    
    today = datetime.now().strftime('%Y%m%d')
    out_filename = today + ' bibs_to_set_catdate.txt'
    
    if j['total'] == 0:
        #print('No records need a catdate')
        #write message to file
        with open(out_dir / out_filename, 'w') as file:
            file.write('No records need a catdate')
    else:
        # If limit was reached, repeat until all record IDs are retrieved
        while j['total'] == 2000:
            print('--------------------------------')
            last_record_id = j['entries'][-1:][0]['link'].replace('https://catalog.lib.jmu.edu/iii/sierra-api/v5/bibs/', '')
            print('id of last record returned:', last_record_id)
            next_record_id = str(int(last_record_id) + 1)
            print('id of starting record for next query:', next_record_id)
            
            # Read create list criteria from file, inserting dates and starting bib number
            with open('catdate_nodates_bib_limiter.json', 'r') as file:
                data = file.read().replace('xx-xx-xxxx', startdate).replace('yy-yy-yyyy', enddate).replace('bxxxxxxx', 'b' + next_record_id)
            
            response = requests.request('POST', 'https://catalog.lib.jmu.edu/iii/sierra-api/v5/bibs/query?offset=0&limit=2000', headers=headers, data=data)
            j = response.json()
            records_returned += j['total']
            print('Records returned:', records_returned)
            # print(response.text)
                
            # Add new response to previous ones
            j_all = merger.merge(j_all, j)
            j_all['total'] = records_returned 
        
        # Put bib IDs in list
        bib_id_list = []
        for i in j_all['entries']:
            bib_id = i['link'].replace('https://catalog.lib.jmu.edu/iii/sierra-api/v5/bibs/', '')
            bib_id_list.append(bib_id)
        #print(bib_id_list)
        #print(len(bib_id_list))
        
        # Get bib varField info for all records, 500 bib IDs at a time
        fields = 'varFields'
        #querystring = {'id':'3323145', 'fields':fields}
        j_data_all = {}
        records_returned_data = 0
        chunk_size = 499
        for i in range(0, len(bib_id_list), chunk_size):
            bib_id_list_partial = bib_id_list[i:i+chunk_size]
            querystring = {'id':','.join(bib_id_list_partial), 'fields':fields, 'limit':2000}
            response = requests.request('GET', 'https://catalog.lib.jmu.edu/iii/sierra-api/v5/bibs/', headers=headers, params=querystring)
            j_data = response.json()
            records_returned_data += j_data['total']
            j_data_all = merger.merge(j_data_all, j_data)
            j_data_all['total'] = records_returned_data
        
        # with open('20190430_test_catdate_jall.json', 'w') as file:
            # file.write(json.dumps(j_all))
        # with open('20190430_test_catdate_jdataall.json', 'w') as file:
            # file.write(json.dumps(j_data_all))
            
        # Identify and remove records with no OCLC# and no call#
        for i in j_data_all['entries']:
            id = i['id']
            var_fields = i['varFields']
            
            oclc_num_exist = False
            call_num_exist = False
            for v in var_fields:
                if 'marcTag' in v:
                    if '001' in v['marcTag']:
                        # Remove record if 001 starts with 'pct'
                        if re.search(r'^pct', v['content']) is not None:
                            oclc_num_exist = False
                        else:
                            oclc_num_exist = True
                    if '050' in v['marcTag'] or '090' in v['marcTag'] or '092' in v['marcTag'] or '099' in v['marcTag']:
                        call_num_exist = True
            #print(id, oclc_num_exist)
            #print(id, call_num_exist)
    
            if not oclc_num_exist:
                bib_id_list.remove(id)
            if not call_num_exist:
                if id in bib_id_list:
                    bib_id_list.remove(id)
            #print(bib_id_list)
        #print(bib_id_list)
        #print(len(bib_id_list))
        
        # If no bibs remain in list, print message; otherwise print bib numbers
        if not bib_id_list:
            with open(out_dir / out_filename, 'w') as file:
                file.write('No records need a catdate')
        else:   
            # Turn bib IDs into bib numbers
            bib_num_list = []
            for b in bib_id_list:
                bib_reversed = b[::-1]
                total = 0
                for i, digit, in enumerate(bib_reversed):
                    prod = (i+2)*int(digit)
                    total += prod
                checkdigit = total%11
                if checkdigit == 10:
                    checkdigit = 'x'
                bib_num_list.append('b' + b + str(checkdigit))
            #print(bib_num_list)
                
            # Write bib numbers to file
            with open(out_dir / out_filename, 'w') as file:
                for i in bib_num_list:
                    file.write(i + '\n')
    
if __name__ == '__main__':
    main(sys.argv[1:])
