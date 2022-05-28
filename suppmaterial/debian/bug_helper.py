import requests
import utils.tool as tool
from datetime import datetime
import html
from dateutil import parser
import pytz, re

BUG_LIST_URL = "https://bugs.debian.org/cgi-bin/pkgreport.cgi?package=%s"
BUG_LIST_ARCHIVE_URL = "https://bugs.debian.org/cgi-bin/pkgreport.cgi?package=%s&archive=yes"
BUG_URL = "https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=%d"

def generate_bug_obj(bug_id, bug_title, reporter, reporter_email, severity, d, pkg_name, bl_archive):
    obj = {}
    obj['id'] = bug_id
    obj['summary'] = bug_title
    obj['creator'] = reporter+"#"+reporter_email
    obj['severity'] = severity
    obj['creation_time'] = d.strftime("%Y-%m-%d %H:%M:%S+00:00")
    obj['component'] = pkg_name
    if bl_archive:
        obj['status'] = "Closed"
    else:
        obj['status'] = ""
    return(obj)

def parse_bug_context(pkg_name, context, bl_archive):

    if '<div class="shortbugstatus">' not in context:
        return []
    context = context[context.index('<div class="shortbugstatus">'):]
    cnt = context.count('<div class="shortbugstatus">')
    # print(cnt)

    bugs = []
    for i in range(0,cnt):
        bug_text = context[context.index('<div class="shortbugstatus">'):]
        bug_id = bug_text[bug_text.index('<a href='):bug_text.index('</a>')]
        bug_id = tool.remove_html_tags(bug_id).strip()[1:]

        bug_text = bug_text[bug_text.index('</a>')+4:]
        bug_title = bug_text[bug_text.index('<a href='):]
        bug_title = bug_title[:bug_title.index('</a>')]
        bug_title = tool.remove_html_tags(bug_title).strip()

        bug_text = bug_text[bug_text.index('</a>')+4:]
        reporter = bug_text[bug_text.index('<span>Reported by'):bug_text.index('</span>')]
        reporter = html.unescape(tool.remove_html_tags(reporter).replace("Reported by:", "", 10).replace(";", "", 10).strip())
        # print(reporter)
        if "<" in reporter:
            reporter_email = reporter[reporter.index("<")+1:].strip()
            if ">" in reporter_email:
                reporter_email = reporter_email[:reporter_email.index(">")].strip()
            reporter = reporter.replace(reporter_email,"",10).replace("<","",1).replace(">","",1).replace(";","",1).strip()
        elif "(" in reporter: 
            reporter_email = reporter[:reporter.index("(")].strip()
            reporter = reporter[reporter.index("(")+1:reporter.index(")")].strip()
        else:
            reporter_email = ""

        if reporter.startswith('"') and reporter.endswith('"'):
            reporter = reporter[1:-1]

        bug_text = bug_text[bug_text.index('</span>')+7:]
        creation_time = bug_text[bug_text.index('<span>Date:'):bug_text.index('</span>')]
        creation_time = tool.remove_html_tags(creation_time).replace("UTC;","",1).strip()
        d = datetime.strptime(creation_time, 'Date: %a, %d %b %Y %H:%M:%S') #.strftime("%a, %-d %b %Y %H:%M:%S", pytz.UTC)

        bug_text = bug_text[bug_text.index('</span>')+7:]
        severity = bug_text[bug_text.index('<span>Severity:'):bug_text.index('</span>')]
        severity = tool.remove_html_tags(severity).replace("Severity:","",1).replace(";","",1).strip().lower()

        bugs.append(generate_bug_obj(bug_id, bug_title, reporter, reporter_email, severity, d, pkg_name, bl_archive))
        if i < cnt -1:
            context = context[context.index('<div class="shortbugstatus">', 10):]
        
    return bugs

def fetch_bug_list(pkg_name):
    turl = BUG_LIST_URL % pkg_name
    t_archive_url = BUG_LIST_ARCHIVE_URL % pkg_name

    r = requests.get(turl)
    # print(turl)
    ids = parse_bug_context(pkg_name, r.text, False)
    r = requests.get(t_archive_url)
    ids2 = parse_bug_context(pkg_name, r.text, True)
    return ids+ids2

def parse_comments(context):
    cnt = context.count('<p class="msgreceived">')
    buglogs = []
    for i in range(0,cnt):
        comment = context[:context.index('<hr>')]
        if '<div class="headers">' not in comment:
            break
        header = comment[comment.index('<div class="headers">'):]
        # print(header)
        if '<pre class="' in header:
            header = header[:header.index('<pre class="'):]
        
        date = ""
        if '<span class="headerfield">Date:</span>' in header:
            meta = header[header.index('<span class="headerfield">Date:</span>'):]
            meta = meta[meta.index('</span>'):meta.index('</div>')]
            meta = tool.remove_html_tags(meta).strip()
            date = meta
        writer = ""
        if '<span class="headerfield">From:</span>' in header:
            meta = header[header.index('<span class="headerfield">From:</span>'):]
            meta = meta[meta.index('</span>'):meta.index('</div>')]
            meta = tool.remove_html_tags(meta).strip()
            writer = meta
            
        # print(writer, date)
        # print(comment)

        message = ""
        if '<pre class="message' in comment:
            message = comment[comment.index('<pre class="message'):]
            message = message[message.index('">')+2:]
            message = message[:message.index("</pre>")]
            message = tool.remove_html_tags(message).strip()

        context = context[1:]
        if '<p class="msgreceived">' in context:
            context = context[context.index('<p class="msgreceived">'):]
        buglog ={}
        buglog["date_created"] = date
        buglog["writer"] = writer
        buglog["content"] = message
        buglogs.append(buglog)
   
    return buglogs

def fetch_bug(id):
    turl = BUG_URL % id

    r = requests.get(turl)
    if r.status_code == 500:
        return 
    
    ob = {}

    if '<h1>' in r.text:
        tmp = r.text[r.text.index("<h1>"):]
        tmp = tmp[:tmp.index("</h1>")]
        tmp = tmp[tmp.index('<br>'):]
        ob['summary'] = tool.remove_html_tags(tmp).strip()

    comp = ""
    if '<div class="pkginfo">' in r.text:
        comp = r.text[r.text.index('<div class="pkginfo">'):]
        comp = comp[:comp.index(';')]
        comp = comp[comp.index('<a'):]
        comp = tool.remove_html_tags(html.unescape(comp)).strip().replace("src:","")



    content = r.text[r.text.index('<div class="buginfo">'):]
    buginfo = content[:content.index("</div>")]
    exclude_links = ["debian.org", "debian.net"]

    if 'Reported by:' in buginfo:
        tmp = buginfo[buginfo.index("Reported by:"):]
        tmp = tmp[tmp.index("<a"):tmp.index("</a>")].replace("#64;","@").replace("&lt;","#").replace("&gt;","")
        ob['creator'] = tool.remove_html_tags(tmp).strip()

    if '<p>Date:' in buginfo:
        tmp = buginfo[buginfo.index("<p>Date:"):]
        tmp = tmp[:tmp.index("</p>")]
        tmp = tool.remove_html_tags(tmp).strip().replace("Date:","")
        ptime = parser.parse(tmp).astimezone(pytz.utc)
        ob['creation_time'] =  ptime.strftime('%Y-%m-%d %H:%M:%S')

    if '<p>Severity:' in buginfo:
        tmp = buginfo[buginfo.index("<p>Severity:"):]
        tmp = tmp[:tmp.index("</p>")]
        tmp = tool.remove_html_tags(tmp).strip().replace("Severity:","")
        ob['severity'] = tmp.strip()
    
    is_archive = False
    if 'Bug is archived':
        is_archive = True
        ob['status'] = "Closed"
    else:
        ob['status'] = "Opened"

    if "<p>Merged with" in buginfo:
        tmp = buginfo[buginfo.index("<p>Merged with"):]
        tmp = tmp[tmp.index("<a"):tmp.index("</p>")]
        tmp = tool.remove_html_tags(tmp).strip()
        dup_bugs = tmp.split(',')
        ob['duplicate_ids'] = ','.join(x.strip() for x in dup_bugs)
    
    affected_versions = []
    if "<p>Found in" in buginfo:
        tmp = buginfo[buginfo.index("<p>Found in"):]
        tmp = tmp[:tmp.index("</p>")]
        tmp = tool.remove_html_tags(tmp).replace("Fixed in versions", "",10).replace("Found in version", "",10).strip()
        affected_versions = tmp.split(',')
    
    if "<p>Fixed in" in buginfo:
        tmp = buginfo[buginfo.index("<p>Fixed in"):]
        tmp = tmp[:tmp.index("</p>")]
        tmp = tool.remove_html_tags(tmp).replace("Fixed in versions", "",10).replace("Fixed in version", "",10).strip()
        ob['cf_fixed_in'] = tmp.strip()
    
    tags = ""
    if "<p>Tags:" in buginfo:
        tmp = buginfo[buginfo.index("<p>Tags:"):]
        tmp = tmp[:tmp.index("</p>")]
        tags = tool.remove_html_tags(tmp).replace("Tags:", "",10).strip().split(',')

    num_comments = content.count('<hr><p class="msgreceived">')
    comments = parse_comments(r.text[r.text.index('<p class="msgreceived">'):])

    # save comments in the debian_comments folder
    with open("debian_comments/"+str(id)+".txt", 'w+', newline='\n', encoding='utf8') as wFile:
        for cc in comments:
            wFile.write("DATE_CREATED: "+cc["date_created"]+"\n")
            wFile.write("WRITER: "+str(cc["writer"])+"\n")
            wFile.write("CONTENT: "+cc["content"]+"\n")
            wFile.write("==============SPILIT_LINE==============\n")
    wFile.close()

    # count devs in comments
    ob['ext_num_devs'] = 0
    if len(comments) > 0:
        devs = set([ e['writer'] for e in comments ])
        ob['ext_num_devs'] = len(devs)

    # count links in comments
    ext_links = []
    int_links = []
    for cc in comments:
        links = re.findall("(?P<url>https?://[^\s]+)", cc['content'])
        int_cmt_links = [x for x in links if any(y in x for y in exclude_links)]
        int_links = int_links + int_cmt_links
        ext_cmt_links = [x for x in links if not any(y in x for y in exclude_links)]
        ext_links = ext_links + ext_cmt_links
    ext_links = set(ext_links)
    int_links = set(int_links)
    ob['ext_num_ext_links'] = len(ext_links)
    ob['ext_num_int_links'] = len(int_links)
    # print(id, ob['ext_num_devs'], ob['ext_num_ext_links'], ob['ext_num_int_links'] )

    # find fixed time
    cf_last_closed = ""
    cf_last_closed_cant_parse = ""
    if is_archive:
        # print(done_user)
        last_activity = content[content.rfind('<hr><p class="msgreceived">'):]

        if '<div class="headers">' in last_activity:
            meta = last_activity[last_activity.index('<div class="headers">'):]
            if '<span class="headerfield">Date:</span>' in meta:
                meta = meta[meta.index('<span class="headerfield">Date:</span>'):]
                meta = meta[meta.index('</span>'):meta.index('</div>')]
                meta = tool.remove_html_tags(meta).strip()
                # print(meta)
                if "(" in meta:
                    meta = meta[:meta.index("(")].strip()
                try:
                    cf_last_closed = datetime.strptime(meta, '%a, %d %b %Y %H:%M:%S %z') 
                    utc_dt = cf_last_closed.astimezone(pytz.utc)
                    cf_last_closed = utc_dt
                except ValueError:
                    cf_last_closed_cant_parse = meta
                
    
    # print(tags)
    ob["component"] = comp
    ob["tags"] = '#'.join(tags)
    ob["affected_versions"] = '#'.join(affected_versions)
    ob["ext_num_comments"] = num_comments -1
    if cf_last_closed != "":
        ob["cf_last_closed"] = cf_last_closed.strftime("%Y-%m-%d %H:%M:%S+00:00")
    elif cf_last_closed_cant_parse != "":
        ob["cf_last_closed"] = cf_last_closed_cant_parse


    return ob

def fetch_bug_comments(id):
    turl = BUG_URL % id

    r = requests.get(turl)
    if r.status_code == 500:
        return 

    comments = parse_comments(r.text[r.text.index('<p class="msgreceived">'):])
    return comments