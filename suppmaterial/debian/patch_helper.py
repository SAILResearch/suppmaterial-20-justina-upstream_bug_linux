import requests
import utils.tool as tool

DOMAIN_URL = "https://sources.debian.org"
PATCH_URL = DOMAIN_URL+"/patches/"


def fetch_list(pkg_name):
    turl = PATCH_URL + pkg_name+"/"

    r = requests.get(turl, timeout = 60)

    links = []
    if '<ul id="ls">' in r.text:
        content = r.text[r.text.index('<ul id="ls">'):]
        content = content[:content.index('</ul>')]
        cnt = content.count('<a href="')

        for i in range(0, cnt):
            ob ={}
            href = content[content.index('<a href="'):content.index('</a>', 4)]
            link = href[href.index('href="'):href.index('">')].replace('"',"").replace("href=","")
            

            ob['link'] = link.strip()
            ob['pkg_version'] = tool.remove_html_tags(href).strip()

            temp = content[content.index('</a>', 4):]
            temp = temp[:temp.index('</li>')]
            temp = tool.remove_html_tags(temp).replace("(main)","").replace("\n","").replace("[","").replace("]","")
            vers = temp.split(',')
            vers = [x.strip() for x in vers if x.strip() != "sid"]
            ob['version'] = '#'.join(vers)

            links.append(ob)
            content = content[content.index("</a>"):]
    
    return links

def get_patches(pkg_name, link, ver, pkg_version):
    turl = DOMAIN_URL + link

    r = requests.get(turl, timeout = 60)

    patches = []
    # print(turl)
    # print(r.text)
    if "<h3>Patch series</h3>" in r.text:
        content = r.text[r.text.index('<h3>Patch series</h3>'):]
        
        content = content[content.index('<tr class="head">')+4:]
        content = content[content.index('</tr>'):]
        cnt = content.count('<tr')
        # print(cnt)
        for i in range(0, cnt):
            ob = {}
            tmp = content[content.index("<tr"):]
            tmp = tmp[:tmp.index('</tr>')]
            # print(tmp)
            link = tmp[tmp.index("<td>"):]
            link = link[:link.index("</td>")]
            info = link.split("|")
            ob['patch_index'] = tool.remove_html_tags(info[0]).strip()
            link = info[1][info[1].index('href="'):info[1].index('">')].replace('"',"").replace("href=","").strip()
            ob['link'] = DOMAIN_URL + link

            changes = tmp[tmp.index("<td><p>"):]
            changes = changes[:changes.index("</p>")]
            arr = changes.split('<br />')
            files = []
            add_lines = 0
            del_lines = 0
            for ff in arr:
                if "|" in ff:
                    fname = ff[ff.index('<a href='):ff.index('</a>')]
                    fname = tool.remove_html_tags(fname).strip()
                    files.append(fname)
                else:
                    info = tool.remove_html_tags(ff).split(',')
                    if len(info) == 2:
                        if "insertion" in info[1]:
                            add_lines = int(info[1][:info[1].index("insertion")].strip())
                        elif "deletion" in info[1]:
                            del_lines = int(info[1][:info[1].index("deletion")].strip())
                    elif len(info) == 3:
                        add_lines= int(info[1][:info[1].index("insertion")].strip())
                        del_lines = int(info[2][:info[2].index("deletion")].strip())
            
            ob['num_added_lines'] = add_lines
            ob['num_deleted_lines'] = del_lines
            ob['num_changed_files'] = len(files)
            ob['os_version'] = ver
            ob['pkg_name'] = pkg_name
            ob['pkg_version'] = pkg_version
            # print(ob)
            patches.append(ob)
            content = content[content.index("</tr>", 4):]
            # print(content)

    return patches

def fetch_patch_by_link(link):
    r = requests.get(link)

    if r.status_code != 200:
        # print(r.status_code)
        return ""
    

    return r.text