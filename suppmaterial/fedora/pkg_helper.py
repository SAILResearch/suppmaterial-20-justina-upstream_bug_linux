import requests
import json, os, re
import subprocess

SRC_URL = "https://src.fedoraproject.org/"
REPO_PATH = "api/0/rpms/" 
RAWHIDE_URL = "https://mdapi.fedoraproject.org/rawhide/srcpkg/"

def fetch_pkg_info(pkg_name):
    url = SRC_URL + REPO_PATH + pkg_name
    headers = {'user-agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36'}
    r = requests.get(url , headers = headers)
    if r.status_code == 404:
        return None
    
    info = json.loads(r.text)
    return info


def fetch_pkg_rawhide_info(pkg_name):
    url = RAWHIDE_URL + pkg_name
    r = requests.get(url)
    if r.status_code == 404:
        return None
    
    info = json.loads(r.text)
    return info

def is_unknown_pkg(pkg_name):
    url = SRC_URL +"rpms/" + pkg_name
    r = requests.get(url)
    if "<h2>Page not found (404)</h2>" in r.text:
        return True
    
    return False


def clone_pkg_source(pkg):
    src = SRC_URL +"rpms/"+ pkg +".git"

    os.system("cd fedora_src/; git clone "+src)
    output = subprocess.check_output("cd fedora_src/"+pkg+"; git branch -r", shell=True)
    branches = output.decode("utf-8").split('\n')
    branches = list(filter(None, branches))
    branches = [x.strip() for x in branches]
    # print(branches)
    return branches

def clone_pkg_source_depth_5(pkg):
    src = SRC_URL +"rpms/"+ pkg +".git"

    os.system("cd fedora_src/; git clone --depth 5 "+src)
    output = subprocess.check_output("cd fedora_src/"+pkg+"; git branch -r", shell=True)
    branches = output.decode("utf-8").split('\n')
    branches = list(filter(None, branches))
    branches = [x.strip() for x in branches]
    # print(branches)
    return branches


def fetch_patches(pkg, remote_branch, os_version):
    local_branch = remote_branch.replace("origin/","")
    os.system("cd fedora_src/"+pkg+"; git checkout -b "+local_branch+" "+remote_branch)
    
    patches = []
    for ff in os.listdir("fedora_src/"+pkg):
        if ff.endswith(".patch"):
            # print(ff)
            ob={}
            ob['patch_index'] = ff
            files = []
            add_lines = 0
            del_lines = 0
            with open(os.path.join("fedora_src/"+pkg,ff), 'r', newline='\n', encoding='latin1') as r_file:
                bl_section = False
                for line in r_file:
                    if line.strip().startswith("diff --git"):
                        bl_section = True
                        files.append(line.strip().split('/')[-1])
                    elif line.strip() == "---":
                        continue
                    elif line.startswith("---") or line.startswith("+++"):
                        if bl_section:
                            continue
                        arr = re.split(' |\t',line.strip())
                        if len(arr) > 1 and (arr[1].split('/')[-1] not in files):
                            if arr[1] == "/dev/null":
                                continue
                            bl_section = True
                            files.append(arr[1].split('/')[-1])
                        continue
                    elif line.startswith("@@"):
                        bl_section = False
                        continue
                    elif line.startswith("--"):
                        continue
                    elif line.startswith("+"):
                        add_lines+=1
                    elif line.startswith("-"):
                        del_lines+=1  

                r_file.close()
            
            if len(files) == 0:
                continue
            ob['num_added_lines'] = add_lines
            ob['num_deleted_lines'] = del_lines
            ob['num_changed_files'] = len(files)
            ob['os_version'] = os_version
            ob['pkg_name'] = pkg
            # print(ob)
            patches.append(ob)
    return patches