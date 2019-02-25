import sys
import configparser
from pathlib import Path
import json
import requests
import base64
import xlwt
from datetime import datetime
import pycallnumber as pycn
import jmu_local_calls as jmulocal

#currently using WeeklyHoldings env
#python holdings.py 01-13-2019 01-16-2019
def main(arglist):
    #read config file
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    startdate, enddate, save_dir = arglist
    print('Save dir:' + save_dir)
    out_dir = Path(save_dir)
    print(out_dir)
    
    #read create list criteria from file, inserting dates
    with open('holdings-nodates.json', 'r') as file:
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
    response = requests.request('POST', 'https://catalog.lib.jmu.edu/iii/sierra-api/v5/bibs/query?offset=0&limit=2000', headers=headers, data=data)
    #print('request sent')
    #print(response.text)
    j = response.json()
    
    '''
    #for testing when not doing api call
    with open('response to create list search.json', 'r') as file:
        f = file.read()   
    #print(f)
    j = json.loads(f)
    #print(j['entries'])
    #end lines for testing
    '''
    
    ##put bib ids in list
    bib_id_list = []
    for i in j['entries']:
        bib_id = i['link'].replace('https://catalog.lib.jmu.edu/iii/sierra-api/v5/bibs/', '')
        bib_id_list.append(bib_id)
    #print(bib_id_list)
    #print(len(bib_id_list))
    
    #get bib info for all records
    fields = 'default,locations,bibLevel,varFields,orders' #orders only returns data for order records with status o (on order) and not status a (fully paid), so it's pretty useless for this and there's no other option
    #querystring = {'id':'3323145', 'fields':fields}
    querystring = {'id':','.join(bib_id_list), 'fields':fields, 'limit':2000}
    response = requests.request('GET', 'https://catalog.lib.jmu.edu/iii/sierra-api/v5/bibs/', headers=headers, params=querystring)
    j = response.json()
    #print(j)
    #with open('bib_info_loc&varFields.json', 'w') as file:
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
    print(len(bib_id_list))
    
    #split bibs into internet/not internet
    bib_id_list_e = []
    bib_id_list_no_e = []
    for i in j['entries']:
        #print(i['locations'])
        for l in i['locations']:
            if 'in' in l['code']:
                #print(l['code'])
                bib_id_list_e.append(i['id'])
            else:
                bib_id_list_no_e.append(i['id'])
    
    print('===EBOOKS===')
    print(bib_id_list_e)
    print(len(bib_id_list_e))
    print('===NOT EBOOKS===')
    print(bib_id_list_no_e)
    print(len(bib_id_list_no_e))
    print('======')
    
    #set up e-books spreadsheet with column headers
    #TODO is there a way to set the font for the whole workbook (including cells that don't get written to)?
    book1 = xlwt.Workbook(encoding='utf-8')
    sheet = book1.add_sheet('Sheet1')
    font = xlwt.Font()
    font.name = 'Calibri'
    font.height = 220 #11 pt. * 20
    style = xlwt.XFStyle()
    style.font = font
    
    style_blue = xlwt.easyxf('pattern: pattern solid, fore_colour cyan_ega')
    style_yellow = xlwt.easyxf('pattern: pattern solid, fore_colour yellow')
    
    cols = ['BIB#', 'HOLDINGS SET', 'BIB LVL', 'LOC', '001', '035|a', '090', 'ITEM NOTE', '506', '245', '856|u']
    for index, c in enumerate(cols):
        sheet.write(0, index, c, style = style)
    
    today = datetime.now().strftime('%Y%m%d')
    ebook_outname = today + ' E-Book Holdings.xls'
    book1.save(out_dir / ebook_outname)
    
    ##write ebooks to spreadsheet
    ##list of fields to export - ebook export fields and notes.txt
    #if adding additional fields, may need to also add them in line 62
    print('writing e-books to spreadsheet')
    row = 0
    for id in bib_id_list_e:
        row += 1
        #print(row)
        
        #print(id)
        
        #turn bib id into bib number
        bib_reversed = id[::-1]
        total = 0
        for i, digit, in enumerate(bib_reversed):
            prod = (i+2)*int(digit)
            total += prod
        checkdigit = total%11
        if checkdigit == 10:
            checkdigit = 'x'
        bib_num = 'b' + id + str(checkdigit)
        #print(bib_num)
        sheet.write(row, 0, bib_num, style = style)
        
        #find the part of j['entries'] with this id
        bib_data = next(item for item in j['entries'] if item['id'] == id)
        
        #locations
        #print(bib_data['locations'])
        #print(str(len(bib_data['locations'])) + '===number of locations')
        locs = ''
        for x, c in enumerate(bib_data['locations']):
            locs += c['code']
            if x != len(bib_data['locations']) - 1: #maybe change this to check for empty string before prev line
                locs += ','
        #print('LOCATIONS:', locs)
        sheet.write(row, 3, locs, style = style)
        
        #bibLevel
        bib_lvl = ''
        bib_lvl = bib_data['bibLevel']['code']
        #print(bib_lvl)
        sheet.write(row, 2, bib_lvl, style = style)
        
        #variable fields
        var_fields = bib_data['varFields']
        
        data_001 = ''
        data_035a = ''
        data_090 = ''
        data_506 = ''
        data_245 = ''
        data_856u = ''
        
        for v in var_fields: #for each variable field
            #print(v.keys())
            if 'marcTag' in v: #if it's a MARC field
                #print(v['marcTag'])
                if '001' in v['marcTag']:
                    data_001 = v['content']
                if '035' in v['marcTag']:
                    for s in v['subfields']:
                        if 'a' in s['tag']:
                            #exist_035a = True
                            # if data_035a != '':
                            if data_035a:
                                data_035a += ';'
                            data_035a += s['content']
                if '090' in v['marcTag']:
                    # for i, s in enumerate(v['subfields']):
                    for s in v['subfields']:
                        # if i != 0:
                        if data_090:
                            data_090 += ' '
                        data_090 += s['content']
                if '506' in v['marcTag']:
                    # for i, s in enumerate(v['subfields']):
                    for s in v['subfields']:
                        # if i != 0:
                        if data_506:
                            data_506 += ' '
                        data_506 += s['content']
                if '245' in v['marcTag']:
                    # for i, s in enumerate(v['subfields']):
                    for s in v['subfields']:
                        # if i != 0:
                        if data_245:
                            data_245 += ' '
                        if '6' not in s['tag']:
                            data_245 += s['content']
                if '856' in v['marcTag']:
                    for s in v['subfields']:
                        if 'u' in s['tag']:
                            # if data_856u != '':
                            if data_856u:
                                data_856u += ';'
                            data_856u += s['content']
        
        #print('001:', data_001)
        #print('035a:', data_035a)
        #print('090:', data_090)
        #print('506:', data_506)
        #print('245:', data_245)
        #print('856u:', data_856u)
        
        sheet.write(row, 4, data_001, style = style)
        sheet.write(row, 5, data_035a, style = style)
        sheet.write(row, 6, data_090, style = style)
        sheet.write(row, 8, data_506, style = style)
        sheet.write(row, 9, data_245, style = style)
        sheet.write(row, 10, data_856u, style = style)
        
        #get item info for this bib
        fields = 'varFields,location'
        #querystring = {'id':'3323145', 'fields':fields}
        querystring = {'bibIds': id, 'fields':fields, 'limit':2000}
        response = requests.request('GET', 'https://catalog.lib.jmu.edu/iii/sierra-api/v5/items/', headers=headers, params=querystring)
        i = response.json()
        #print(i)
        #with open('item_info_varFields'+id+'.json', 'w') as file:
        #    file.write(json.dumps(i))
        
        data_item_note = ''
        
        #i['entries'] is a list
        for e in i['entries']:
            #print(e['varFields'])
            for x in e['varFields']:
                if 'x' in x['fieldTag']:
                    #print(x['content'])
                    if data_item_note != '':
                        data_item_note += ';'
                    data_item_note += x['content']
                    
        sheet.write(row, 7, data_item_note, style = style)
        book1.save(out_dir / ebook_outname)
        
        #print()
        '''
        #001
        data_001 = next(f for f in var_fields if f['marcTag'] == '001')
        #data_001 = next(f for f in bib_data['varFields'] if f['marcTag'] == '001')
        print(data_001)
        #print(data_001['content'])  #this is just the OCLC number - what we want
        
        
        #035|a
        #data_035a = next(f for f in bib_data['varFields'] if f['marcTag'] == '035') #throws error if field doesn't exist
        if exist_035a:
            data_035a = next(f for f in bib_data['varFields'] if f['marcTag'] == '035')
        print(data_035a)
        
        #090
        if exist_090:
            data_090 = next(f for f in bib_data['varFields'] if f['marcTag'] == '090')
        print(data_090)
        '''
    print('e-book spreadsheet completed')
    print()
        

    #set up non-internet spreadsheet with column headers
    book2 = xlwt.Workbook(encoding='utf-8')
    sheet = book2.add_sheet('Sheet1')
    #font = xlwt.Font()
    #font.name = 'Calibri'
    #font.height = 220 #11 pt. * 20
    #style = xlwt.XFStyle()
    #style.font = font
    
    cols = ['BIB#', 'CALL#', 'TITLE', 'BIB LOCATION', 'ORDER LOCATION', 'ITEM LOCATION', 'CALL NUM TYPE']
    for index, c in enumerate(cols):
        sheet.write(0, index, c, style = style)
    
    no_e_outname = today + ' Weekly Holdings QA.xls'
    book2.save(out_dir / no_e_outname)
    
    print('writing other titles to spreadsheet')
    row = 0
    for id in bib_id_list_no_e:
        row += 1
        
        #turn bib id into bib number
        bib_reversed = id[::-1]
        total = 0
        for i, digit, in enumerate(bib_reversed):
            prod = (i+2)*int(digit)
            total += prod
        checkdigit = total%11
        if checkdigit == 10:
            checkdigit = 'x'
        bib_num = 'b' + id + str(checkdigit)
        #print(bib_num)
        sheet.write(row, 0, bib_num, style = style)
        
        #find the part of j['entries'] with this id
        bib_data = next(item for item in j['entries'] if item['id'] == id)
        var_fields = bib_data['varFields']
        
        #call number (050, 090, 099, 092) and title (245)
        call_num = ''
        call_num_problem = False
        title = ''
        for v in var_fields: #for each variable field
            #print(v.keys())
            if 'marcTag' in v: #if it's a MARC field
                #print(v['marcTag'])
                if '050' in v['marcTag']:
                    # if call_num != '':
                    if call_num:
                        call_num += ';'
                    # for i, s in enumerate(v['subfields']):
                    for s in v['subfields']:
                        # if i != 0:
                        if call_num:
                            call_num += ' '
                        call_num += s['content']
                if '090' in v['marcTag']:
                    # if call_num != '':
                    if call_num:
                        call_num += ';'
                    # for i, s in enumerate(v['subfields']):
                    for s in v['subfields']:
                        # if i != 0:
                        if call_num:
                            call_num += ' '
                        call_num += s['content']
                if '099' in v['marcTag']:
                    # if call_num != '':
                    if call_num:
                        call_num += ';'
                    # for i, s in enumerate(v['subfields']):
                    for s in v['subfields']:
                        # if i != 0:
                        if call_num:
                            call_num += ' '
                        call_num += s['content']
                if '092' in v['marcTag']:
                    if 'c' in v['fieldTag']: #only fieldTag c (CALL #), not f (DEWEY NO.)
                        # if call_num != '':
                        if call_num:
                            call_num += ';'
                        # for i, s in enumerate(v['subfields']):
                        for s in v['subfields']:
                            # if i != 0:
                            if call_num:
                                call_num += ' '
                            call_num += s['content']
                if '245' in v['marcTag']:
                    # for i, s in enumerate(v['subfields']):
                    for s in v['subfields']:
                        # if i != 0:
                        if title:
                            title += ' '
                        if '6' not in s['tag']:
                            title += s['content']
        
        #bib locations
        bib_locs = ''
        for x, c in enumerate(bib_data['locations']):
            bib_locs += c['code']
            if x != len(bib_data['locations']) - 1: #TODO change this to check for empty string before prev line?
                bib_locs += ','
        #print('LOCATIONS:', bib_locs)
        
        #order locations -- missing lots of locations because orders only returned when status is o and not a
        order_locs = ''
        for x, o in enumerate(bib_data['orders']):
            #print(o['location']['code'])
            if order_locs != '':
                order_locs += ';'
            order_locs += o['location']['code']
        
        #item locations
        #get item info for this bib
        fields = 'location'
        querystring = {'bibIds': id, 'fields':fields, 'limit':2000}
        response = requests.request('GET', 'https://catalog.lib.jmu.edu/iii/sierra-api/v5/items/', headers=headers, params=querystring)
        i = response.json()
        #print(i)
        #with open('item_info_varFields'+id+'.json', 'w') as file:
        #    file.write(json.dumps(i))
        
        item_locs = ''
        for e in i['entries']:
            #print(e['location']['code'])
            if item_locs != '':
                item_locs += ';'
            item_locs += e['location']['code']
        
        ##TODO non internet: identify duplicate or incomplete call numbers, location matches and correct call# ranges
        
        #done - duplicate call numbers - call_num has a ;
        #incomplete call numbers - 050/090 missing subfield b or not ending in a date
        #incomplete call numbers - 099 missing second subfield a (DVDs) - others probably have different schemes
        #location problems - bib and order locations don't match
        #location problems - bib and item locations don't match (item locs will sometimes be more specific and that's ok)
        #location problems - bib or order or item location is wrong based on call number
        
        
        ##TODO (potential) write ONLY problem records to spreadsheet
        
        
        
        #Carrier call number ranges
        A_F = pycn.cnrange('A 0', 'F 3799')
        GF_L = pycn.cnrange('GF 0', 'LT 1001')
        ML_ML = pycn.cnrange('ML 0', 'ML 3930')
        N_P = pycn.cnrange('N 0', 'PZ 90')
        Z_Z = pycn.cnrange('Z 0', 'ZA 5190')
    
        #Rose call number ranges
        G_GE = pycn.cnrange('G 0', 'GE 350')
        Q_V = pycn.cnrange('Q 0', 'VM 989')
        
        #Music call number ranges
        M_M = pycn.cnrange('M 0', 'M 5000')
    
        #Music or Carrier
        MT_MT = pycn.cnrange('MT 0', 'MT 960')
        
        #ETMC call number ranges/types?
        #all Dewey, local (P + author cutter [A###a], or just author cutter)
        
        #other local calls? DVD, SPA
        
        #parse call numbers
        #identify duplicate call numbers
        if ';' in call_num:
            call_num_problem = True
        
        utypes = [jmulocal.LocalSC, jmulocal.LocalCD, jmulocal.LocalCass, jmulocal.LocalJazzLP, jmulocal.LocalLP, jmulocal.LocalJuv, jmulocal.LocalPCD, pycn.units.LC, pycn.units.LcClass, pycn.units.Dewey, pycn.units.Local]
        cn = pycn.callnumber(call_num, unittypes=utypes)
        
        cn_type = type(cn)
        '''
        if cn_type is pycn.units.callnumbers.lc.LcClass: #incomplete LC call number
            print('INCOMPLETE CALL NUMBER (class only):', call_num)
            call_num_problem = True
        if cn_type is pycn.units.callnumbers.lc.LC:
            if cn.cutters is None:
                print('INCOMPLETE CALL NUMBER (cutters):', call_num)
                call_num_problem = True
            if cn.edition is None:
                print('INCOMPLETE CALL NUMBER (year):', call_num) #for some reason the PZ ones are being identified as missing a year - PZ7.B25058 Ye 1993
                call_num_problem = True
                
            #determine location based on call number
            if cn.classification in A_F or cn.classification in GF_L or cn.classification in ML_ML or cn.classification in N_P or cn.classification in Z_Z:
                print('Carrier')
            elif cn.classification in G_GE or cn.classification in Q_V:
                print('Rose')
            elif cn.classification in M_M:
                print('Music')
            elif cn.classification in MT_MT:
                print('Carrier or Music')
        elif cn_type is pycn.units.callnumbers.dewey.Dewey or cn_type is jmulocal.LocalJuv:
            print('ETMC')
        #elif type(cn) is pycn.units.callnumbers.local.Local:
        #    print(cn.parts[0])
        #    if 'P' in cn.parts[0]:
        #        print('ETMC')
        else:
            print(cn_type.__name__)
        '''
        if call_num_problem:
            sheet.write(row, 1, call_num, style = style_blue)
        else:
            sheet.write(row, 1, call_num, style = style)
        
        sheet.write(row, 2, title, style = style)
        sheet.write(row, 3, bib_locs, style = style)
        sheet.write(row, 4, order_locs, style = style)   
        sheet.write(row, 5, item_locs, style = style)
        sheet.write(row, 6, cn_type.__name__, style = style)
        
        book2.save(out_dir / no_e_outname)
            
    print('second spreadsheet completed')
    print()    
    
if __name__ == '__main__':
    main(sys.argv[1:])
