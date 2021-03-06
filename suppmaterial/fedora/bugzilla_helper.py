import requests
import utils.tool as tool
import time, json, csv, re
import ssl
from datetime import datetime
from dateutil import parser
import pytz

utc=pytz.UTC

REST_URL = "https://bugzilla.redhat.com/"

# REST API methods
REST_VERSION = 'rest/version'
REST_BUG = 'rest/bug'
REST_BUG_COMMENT = 'rest/bug/{0}/comment'
REST_BUG_HISTORY = 'rest/bug/{0}/history'

# REST params
PARAM_API_KEY = "api_key"
PARAM_IDS = "ids"
PARAM_LOGIN = 'login'
PARAM_PASSWD = 'password'
PARAM_ID = "id"
PARAM_INCLUDE_FIELDS = "include_fields"
PARAM_PRODUCT = 'product'
PARAM_COMPONENT = 'component'
PARAM_LIMIT = 'limit'
PARAM_OFFSET = 'offset'
PARAM_CREATION_TIME = 'creation_time'
PARAM_CHFIELD = 'chfield' # chfield=[Bug creation]
PARAM_CHFROM = 'chfieldfrom' # chfieldfrom=7d


MAX_BUGS = 500

def fetch_bug_from_api(product, component, offset, ch_field, ch_from, specific_fields):

    # param
    dtParam = {}
    if component != "":
        dtParam[PARAM_COMPONENT] = component
    if product != "":
        dtParam[PARAM_PRODUCT] = product
    dtParam[PARAM_LIMIT] = str(MAX_BUGS)
    dtParam[PARAM_OFFSET] = str(offset*MAX_BUGS)
    if ch_field != "":
        dtParam[PARAM_CHFIELD] = ch_field 
        dtParam[PARAM_CHFROM] = ch_from 
    dtParam[PARAM_INCLUDE_FIELDS] = ','.join(specific_fields)
    
    urllist = REST_URL+REST_BUG
    if len(dtParam)>0:
        urllist = urllist +"?"+ tool.url_param_From_dict(dtParam)
    
    # print(urllist)
    ssl._create_default_https_context = ssl._create_unverified_context
    arr_bugs = []

    # fetch bugs from api
    r = requests.get(urllist)
    bugs = json.loads(r.text)
    # print(r.text)
    
    for bug in bugs["bugs"]:
        res = bug
        if len(specific_fields) > 0:
            res = dict((k, bug[k]) for k in specific_fields
                                        if k in bug) 

        arr_bugs.append(res)

    return arr_bugs


def fetch_bug_comment(pid, specific_fields):
    
    urllist = REST_URL+REST_BUG_COMMENT.format(pid)
    arr_comments = []

    # print(urllist)

    r = requests.get(urllist)
    cmts = json.loads(r.text)
    for cmt in cmts["bugs"][str(pid)]["comments"]:
        res = cmt
        if len(specific_fields) > 0:
            res = dict((k, cmt[k]) for k in specific_fields
                                        if k in cmt) 

        arr_comments.append(res)

    return arr_comments

def fetch_bugs(file_name, field_names, severity_list):
    with open(file_name, 'w+', newline='\n') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames= field_names, delimiter=';')
        writer.writeheader()

        nbug = MAX_BUGS
        offset = 0
        latest_bug_id = "2005-01-01"    

        bz_fileds = field_names.copy()
        bz_fileds = [x for x in bz_fileds if not x.startswith('ext_')]   
        exclude_links = ["fedoraproject.org", "bugzilla.redhat.com"]

        while nbug == MAX_BUGS:
            bugs = fetch_bug_from_api("Fedora", "", offset, "[Bug creation]", latest_bug_id, bz_fileds)
            nbug = len(bugs)

            for ob in bugs:
                if ob['severity'] not in severity_list:
                    continue
                if isinstance(ob["version"], list):
                    ob['version'] = ' '.join(ob["version"])
                if isinstance(ob["component"], list):
                    ob['component'] = ' '.join(ob["component"])

                comments = fetch_bug_comment(ob['id'],["id","creator_id","text","time"])
                with open("fedora_comments/"+ob['id']+".txt", 'w+', newline='\n', encoding='utf8') as wFile:
                    for cc in comments:
                        wFile.write("DATE_CREATED: "+ob["time"]+"\n")
                        wFile.write("WRITER: "+str(ob["creator_id"])+"\n")
                        wFile.write("CONTENT: "+ob["text"]+"\n")
                        wFile.write("==============SPILIT_LINE==============\n")
                    wFile.close() 

                ob['ext_num_comments'] = len(comments) -1
                ob['ext_num_devs'] = 0
                if len(comments) > 0:
                    devs = set([ e['creator_id'] for e in comments ])
                    ob['ext_num_devs'] = len(devs)

                ext_links = []
                int_links = []
                dup_ids = []
                for cc in comments:
                    links = re.findall("(?P<url>https?://[^\s]+)", cc['text'])
                    int_cmt_links = [x for x in links if any(y in x for y in exclude_links)]
                    int_links = int_links + int_cmt_links
                    ext_cmt_links = [x for x in links if not any(y in x for y in exclude_links)]
                    ext_links = ext_links + ext_cmt_links
                    if "has been marked as a duplicate of this bug. ***" in cc['text'].lower():
                        dup_id = cc['text'][cc['text'].lower().index('bug')+3:]
                        dup_id = dup_id[:dup_id.index('has')].strip()
                        dup_ids.append(dup_id)
                
                ob['duplicate_ids'] = ','.join(dup_ids)
                ext_links = set(ext_links)
                int_links = set(int_links)
                ob['ext_num_ext_links'] = len(ext_links)
                ob['ext_num_int_links'] = len(int_links)

                writer.writerow(ob)

            offset+=1
            if offset % 10 ==0:
                time.sleep(30)

    csvfile.close()

def batch_fetch_attachments(pids):
    specific_fields = ["id","attachments","is_patch","creator","flags","is_obsolete","is_private","summary","file_name","last_change_time","creation_time","size","content_type"]

    urllist = REST_URL+REST_BUG
    if len(specific_fields) ==0:
        return[]

    urllist = urllist +'?'+PARAM_ID+ '='+','.join([str(x) for x in pids])+'&'+PARAM_INCLUDE_FIELDS+'='+','.join(specific_fields)
    res = []

    retry = 3
    while retry > 0:
        try:
            r = requests.get(urllist, timeout = 60)
            his = json.loads(r.text)
            for data in his["bugs"]:
                # print(data['id'])
                for att in data['attachments']:
                    ob = {}
                    ob['id'] = data['id'] # bug_id
                    ob['attachment_id'] = att['id']
                    ob['creation_time'] = att['creation_time']
                    ob['content_type'] = att['content_type']
                    ob['file_name'] = att['file_name']
                    ob['is_patch'] = att['is_patch']
                    ob['is_obsolete'] = att['is_obsolete']
                    ob['is_private'] = att['is_private']
                    ob['last_change_time'] = att['last_change_time']
                    ob['size'] = att['size']
                    ob['summary'] = att['summary']
                    res.append(ob)
            break
        except Exception as inst:
            retry -= 1
            print(inst.args) 
            print(inst) 
    return res