import sys
import configparser
from pathlib import Path
import json
import requests
import base64
from datetime import datetime

#currently using WeeklyHoldings env
#python catdate.py 01-13-2019 01-16-2019
def main(arglist):
    #read config file
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    startdate, enddate, save_dir = arglist
    #print('Save dir:' + save_dir)
    out_dir = Path(save_dir)
    
    #read create list criteria from file, inserting dates
    with open('catdate-nodates.json', 'r') as file:
        data = file.read().replace('xx-xx-xxxx', startdate).replace('yy-yy-yyyy', enddate)
    #print(data)
    
    ##authenticate to get token, using Client Credentials Grant https://techdocs.iii.com/sierraapi/Content/zReference/authClient.htm
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
    response = requests.request('POST', 'https://catalog.lib.jmu.edu/iii/sierra-api/v5/bibs/query?offset=0&limit=2000', headers=headers, data=data) #FYI this takes a long time to run
    #print('request sent')
    #print(response.text)
    j = response.json()
    #print(j)
    
    '''
    #for testing when not doing api call
    with open('response to create list search.json', 'r') as file:
        f = file.read()   
    #print(f)
    j = json.loads(f)
    #print(j['entries'])
    #end lines for testing
    '''
    
    today = datetime.now().strftime('%Y%m%d')
    out_filename = today + ' bibs_to_set_catdate.txt'
    
    if j['total'] == 0:
        #print('No records need a catdate')
        #write message to file
        with open(out_dir / out_filename, 'w') as file:
            file.write('No records need a catdate')
    else:
        ##put bib ids in list
        bib_id_list = []
        for i in j['entries']:
            bib_id = i['link'].replace('https://catalog.lib.jmu.edu/iii/sierra-api/v5/bibs/', '')
            bib_id_list.append(bib_id)
        #print(bib_id_list)
        #print(len(bib_id_list))
        
        ##TODO (potential) review and remove low bib numbers
        
        #get bib varField info for all records
        fields = 'varFields'
        #querystring = {'id':'3323145', 'fields':fields}
        querystring = {'id':','.join(bib_id_list), 'fields':fields}
        response = requests.request('GET', 'https://catalog.lib.jmu.edu/iii/sierra-api/v5/bibs/', headers=headers, params=querystring)
        j = response.json()
        #print(j)
        #with open('bib_info_varFields.json', 'w') as file:
        #    file.write(json.dumps(j))
            
        #identify and remove records with no OCLC# and no call#
        for i in j['entries']:
            id = i['id']
            var_fields = i['varFields']
            #print(var_fields)
            
            oclc_num_exist = False
            call_num_exist = False
            for v in var_fields:
                if '001' in v.values():
                    oclc_num_exist = True
                if '050' in v.values() or '090' in v.values() or '092' in v.values() or '099' in v.values():
                    call_num_exist = True
            #print(id, call_num_exist)
    
            if not oclc_num_exist:
                bib_id_list.remove(id)
            if not call_num_exist:
                if id in bib_id_list:
                    bib_id_list.remove(id)
        #print(bib_id_list)
        #print(len(bib_id_list))
        
        #turn bib ids into bib numbers
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
            
        #write bibs to file
        with open(out_dir / out_filename, 'w') as file:
            for i in bib_num_list:
                file.write(i + '\n')
    
if __name__ == '__main__':
    main(sys.argv[1:])
