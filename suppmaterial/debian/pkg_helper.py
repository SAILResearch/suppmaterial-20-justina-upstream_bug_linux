import requests
import gzip, os, csv
import utils.tool as tool
import utils.wayback_helper as wayback_helper

PKG_LIST = 'https://packages.debian.org/stable/allpackages?format=txt.gz'
PKGS_URL = "https://packages.debian.org/"

def fetch_pkg_list(file_name, field_names):
    r = requests.get(PKG_LIST)
    open('deb_temp.txt.gz', 'wb').write(r.content)
    with gzip.open('deb_temp.txt.gz','rt') as r_file:
        with open(file_name, 'w+', newline='\n') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames= field_names, delimiter=';')
            writer.writeheader()

            bl_start = False
            for line in r_file:
                if bl_start and line.strip() != "" and not "virtual package" in line:
                    name = line[:line.index('(')].strip()
                    desc = line[line.index(')')+1:].strip()
                    ob = {}
                    ob['name'] = name
                    ob['desc'] = desc
                    writer.writerow(ob)

                if line.startswith("See <URL") and "the license terms" in line:
                    bl_start = True
        csvfile.close()
    r_file.close()
                
    os.system("rm deb_temp.txt.gz")


def parse_pkg_info(context, wb_url_prefix):
    ob= {}
    if '<div id="pdesc"' in context:
        desc = context[context.index('<div id="pdesc"'):]
        desc = desc[desc.index("<h2>"):desc.index("</h2>")]
        desc = tool.remove_html_tags(desc).strip()
        ob["desc"] = desc
    else:
        ob["desc"] = ""

    if '<div id="pnavbar">' in context:
        subsection = context[context.index('<div id="pnavbar">'):]
        # print(subsection)
        if '</div>' in subsection:
            subsection = subsection[:subsection.index('</div>')]
            subsection = subsection[subsection.rfind("<a href"):]
            subsection = subsection[:subsection.index("</a>")]
            subsection = tool.remove_html_tags(subsection).strip()
            ob["subsection"] = merge_category(subsection)
        else:
            ob["subsection"] =""
    else:
        ob["subsection"] = ""


    if "<h3>External Resources:</h3>" in context:
        url = context[context.index('<h3>External Resources:</h3>'):]
        url = url[:url.index('</ul>')]
        url = url[url.index('<a href="')+len('<a href="'):]
        url = url[:url.index('"')].strip()
        ob["url"] = url.replace(wb_url_prefix,"",10)
    else:
        ob["url"] = ""
    return ob

def fetch_package_detail(cname, versions, old_versions):

    pack_infos = []
    blFound = False

    # check the latest 3 versions
    for vv in versions:
        turl = PKGS_URL+ vv.lower()+"/"+ cname
        # print(turl)
        
        r = requests.get(turl)
        if r.status_code != 200:
            # print(r.status_code)
            continue
        
        if "<h1>Error</h1>" in r.text and "<p>No such package.</p>" in r.text:
            continue
        if "<h1>Error</h1>" in r.text and "<p>Package not available in this suite.</p>" in r.text:
            continue
        if "<h1>Error</h1>" in r.text:
            continue
        # print(r.text)
        
        ob = parse_pkg_info(r.text, "")
        ob['version'] = vv.lower()
        pack_infos.append(ob)
        blFound = True
        break
    
    # check the archived old versions
    if not blFound:
        for vv in old_versions:
            # https://archive.org/wayback/available?url=packages.debian.org/etch/bigloo-ude
            turl = PKGS_URL+ vv.lower()+"/"+ cname
            turl = turl.replace("https://","",10)
            # print(turl)
            wb_url = wayback_helper.get_available_archive(turl)
            if wb_url != "":
                r = requests.get(wb_url)
                print(wb_url)

                if r.status_code != 200:
                    # print(r.status_code)
                    continue
                if "<h1>Error</h1>" in r.text and "<p>No such package.</p>" in r.text:
                    continue
                if "<h1>Error</h1>" in r.text and "<p>Package not available in this suite.</p>" in r.text:
                    continue
                if "<h1>Error</h1>" in r.text:
                    continue

                if "https://" in wb_url:
                    wb_url_prefix = wb_url[:wb_url.index("https://",6)]
                else:
                    wb_url_prefix = wb_url[:wb_url.index("http://",6)]
                ob = parse_pkg_info(r.text, wb_url_prefix)
                ob['version'] = vv.lower()
                # print(ob)
                pack_infos.append(ob)

                blFound = True
                break


    # print(pack_infos)
    return(pack_infos)

def identify_unknown_package(cname, versions):

    is_unknown = 1

    # check the latest 3 versions
    for vv in versions:
        turl = PKGS_URL+ vv.lower()+"/"+ cname
        # print(turl)
        
        r = requests.get(turl)
        if r.status_code != 200:
            continue
        
        if "<h1>Error</h1>" in r.text and "<p>No such package.</p>" in r.text:
            continue
        if "<h1>Error</h1>" in r.text and "<p>Package not available in this suite.</p>" in r.text:
            continue
        if "<h1>Error</h1>" in r.text:
            continue
        # print(r.text)
        is_unknown = 0
        break
    
    return(is_unknown)

def merge_category(name):
    if name.lower() == "oldlibs" or name.lower() == "libdevel": 
        return "libs"
    elif name.lower() == "python" or name.lower() == "java" or name.lower() == "php" or name.lower() == "javascript" or name.lower() == "ruby" or name.lower() == "vcs" or name.lower() == "debug" or name.lower() == "haskell" or name.lower() == "perl" or name.lower() == "interpreters" or name.lower() == "rust" or name.lower() == "lisp" or name.lower() == "otherosfs": 
        return "devel"
    elif name.lower() == "net" :
        return "network"
    elif name.lower() == "xfce" or name.lower() == "kde" or name.lower() == "gnome" or name.lower() == "x11" or name.lower() == "gnustep" :
        return "desktop"
    elif name.lower() == "gnu-r" :
        return "graphics"
    elif name.lower() == "httpd":
        return "web"
    elif name.lower() == "debian-installer" or name.lower() == "cli-mono":
        return "admin"
    elif name.lower() == "education" or name.lower() == "math" or name.lower() == "ocaml":
        return "science"
    elif name.lower() == "electronics" or name.lower() == "misc" or name.lower() == "virtual":
        return "utils"
    elif name.lower() == "tex" or name.lower() == "text" or name.lower() == "doc":
        return "editors"
    elif name.lower() == "sound" or name.lower() == "video" or name.lower() == "radio" or name.lower() == "news" or name.lower() == "hamradio":
        return "media"
    else:
        return name
  