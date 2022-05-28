"""

Usage:
  debian.py fetch bugs
  debian.py fetch pkgs
  debian.py fetch patches
  debian.py mark upstream_fixed
  debian.py mark local_fixed
  debian.py remove duplicate_ids

Options:
  -h --help     Show this screen.
  
"""

from datetime import datetime
from threading import local
from docopt import docopt
import debian.bug_helper as bug_helper
import debian.pkg_helper as pkg_helper
import debian.patch_helper as patch_helper
import pandas, time, csv, os, re
from dateutil import parser
import pytz


RELEASE_CODE_NAMES = ["Buster", "Stretch", "Jessie"] 
ARCHIVE_RELEASE_CODE_NAMES = ["Wheezy", "Squeeze", "Lenny", "Etch", "Woody"]
SEVERITY_LIST = ["serious", "critical", "important", "grave"]
START_DATE = "2005-01-01 00:00:00"

def fetch_bugs(args):
    if not os.path.exists('debian_pkgs.csv'):
        print('ERRPR! The package file does not exist. Please download packages ...')
        return

    field_names = ['id', 'severity', 'summary','status','component','creation_time','creator', 'is_upstream', 'comp_category']
    pkgs = pandas.read_csv('debian_pkgs.csv', index_col=None, header=0, delimiter=';')
    with open("temp_debian_bug_list.csv", 'w+', newline='\n', encoding='utf8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=field_names, delimiter=';')
        writer.writeheader()
        
        # cnt = 0
        for index, row in pkgs.iterrows():
            ids = bug_helper.fetch_bug_list(row["name"])
            for bb in ids:
                if bb['severity'] not in SEVERITY_LIST:
                    continue
                if parser.parse(bb['creation_time']).astimezone(pytz.utc) < parser.parse(START_DATE).astimezone(pytz.utc):
                    continue
                bb['is_upstream'] = row['is_upstream']
                bb['comp_category'] = row['pkg_category']
                writer.writerow(bb)
                # cnt+=1
            
            if index % 20 == 0:
                time.sleep(5)
            if index % 100 == 0 and index > 0:
                csvfile.flush()
                print(index, " rows passed...")
                time.sleep(60)
            # if cnt > 500:
            #     break
        csvfile.close()

    print("Done with downloading the list of bugs, starting to fetch bugs....")
    
    if not os.path.exists('debian_comments/'):
        os.mkdir('debian_comments')

    field_names = ['id','severity','status','creator','assigned_to','component','summary','creation_time','last_change_time','cf_last_closed', 'version','priority','resolution','op_sys', 'cc_detail', 'tags', 'affected_versions', 'duplicate_ids', 'cf_fixed_in', 'ext_num_comments', 'ext_num_devs','ext_num_ext_links','ext_num_int_links', 'is_upstream', 'folder']
    bug_list = pandas.read_csv("temp_debian_bug_list.csv", index_col=None, header=0, delimiter=';')
    with open('debian_bugs.csv', 'w+', newline='\n', encoding='utf8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=field_names, delimiter=';')
        writer.writeheader()
    
        for index, row in bug_list.iterrows():
            
            ob = bug_helper.fetch_bug(row["id"])
            if ob is None:
                print("Bug #", row["id"], " is not available")
                continue
            ob["id"] = row["id"]
            ob['is_upstream'] = row['is_upstream']
            ob['folder'] = row['comp_category']
            
            writer.writerow(ob)
            if index % 20 == 0:
                time.sleep(5)
            if index % 100 == 0 & index >0:
                csvfile.flush()
                time.sleep(60)
                
        csvfile.close()
    print("Done with fetching bugs....")
    os.system("rm temp_debian_bug_list.csv")
    
def fetch_pkgs(args):
    pkg_helper.fetch_pkg_list('temp_debian_pkgs.csv', ['name','desc'])

    field_names = ['name', 'pack_desc', 'upstream_url', 'pkg_category', 'is_upstream']
    projects = pandas.read_csv('temp_debian_pkgs.csv', index_col=None, header=0, delimiter=';')
    with open('debian_pkgs.csv', 'w+', newline='\n', encoding='utf8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=field_names, delimiter=';')
        writer.writeheader()

        for index, row in projects.iterrows():
            ob ={}
            pkgs = pkg_helper.fetch_package_detail(row["name"], RELEASE_CODE_NAMES, ARCHIVE_RELEASE_CODE_NAMES)
            has_upurl = False
            for pp in pkgs:
                if pp['url'] != "":
                    has_upurl = True
                # print(pp)
                ob["pkg_category"] = pp["subsection"]
                ob["name"] = row["name"]
                ob["pack_desc"] = pp["desc"]
                ob["upstream_url"] = pp["url"]
                if has_upurl:
                    break

            if len(pkgs) == 0:
                continue
            
            is_unknown = 0
            if ob['upstream_url'] == "":
                is_unknown = pkg_helper.identify_unknown_package(row["name"], RELEASE_CODE_NAMES)
                ob['is_upstream'] = False
            else:
                ob['is_upstream'] = True
            if is_unknown == 1:
                continue
            
            writer.writerow(ob)

            if index % 20 == 0:
                time.sleep(5)
            if index > 0 and index % 100 == 0:
                csvfile.flush()
                time.sleep(60)
        csvfile.close()
    os.system("rm temp_debian_pkgs.csv")
def fetch_patches(args):
    if not os.path.exists('debian_pkgs.csv'):
        print('The package file does not exist. Please download packages ...')
        return

    projects = pandas.read_csv('debian_pkgs.csv', index_col=None, header=0, delimiter=';')
    fieldnames = ["pkg_name" ,"pkg_version" ,"os_version", "patch_index", "num_changed_files", "num_added_lines", "num_deleted_lines", "link"]
    with open('debian_patches.csv', 'w+', newline='\n', encoding='utf8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()

        for index, row in projects.iterrows():
            links = patch_helper.fetch_list(row['name'])
            # print(links)
            for ll in links:
                patches = patch_helper.get_patches(row['name'],ll['link'], ll['version'], ll['pkg_version'])
                writer.writerows(patches)
                # print(patches)
            
            if index > 0 and index % 100 == 0:
                # break
                print(index, " packages passed ...")
                csvfile.flush()

        csvfile.close()

def mark_upstream_fixed_bugs(args):
    if not os.path.exists('debian_bugs.csv'):
        print('ERRPR! The bug file does not exist. Please download bugs ...')
        return

    if not os.path.exists('debian_patches.csv'):
        print('ERRPR! The patch file does not exist. Please download patches ...')
        return
    
    projects = pandas.read_csv('debian_bugs.csv', index_col=None, header=0, delimiter=';')
    upstream_fixed_bug_ids = []

    # by changelogs
    for index, row in projects.iterrows():
        comts = bug_helper.fetch_bug_comments(row['id'])
        rexp = "new upstream [\w ]*(?=release|version|fix)"
        rexp_bug = "#[\d]{5,7}"
        for cc in comts:
            if '-----BEGIN PGP SIGNED MESSAGE-----' in cc['content']:
                arr_lines = cc['content'].split('\n')
                bl_pkg_changes = False
                bl_upstream_release = False
                bl_fixed_upstream = False
                num_before_star = 100
                for ll in arr_lines:
                    if ll.startswith("-----BEGIN PGP SIGNED MESSAGE-----"):
                        bl_pkg_changes = True
                    if ll.startswith("Checksums-") or ll.startswith("Files"):
                        bl_pkg_changes = False

                    if bl_pkg_changes:
                        bl_obj = re.findall(rexp, ll.lower(), re.I)
                        if bl_obj:
                            bl_upstream_release = True
                            
                            if "*" in ll or "-" in ll or "+" in ll:
                                num_before_star = len(ll) - len(ll.lstrip(' '))
                            
                            bug_ids = re.findall(rexp_bug, ll, re.I)
                            if '#'+str(row['id']) in bug_ids:
                                bl_fixed_upstream = True

                        elif bl_upstream_release:
                            cnt_left_space = len(ll) - len(ll.lstrip(' '))
                            if cnt_left_space > num_before_star:
                                bug_ids = re.findall(rexp_bug, ll, re.I)
                                if '#'+str(row['id']) in bug_ids:
                                    bl_fixed_upstream = True
                            else:
                                num_before_star = 100
                if bl_fixed_upstream:
                    if row['id'] not in upstream_fixed_bug_ids:
                        upstream_fixed_bug_ids.append(row['id'])
    print('Done parsing changelogs...')
    # print(len(upstream_fixed_bug_ids))
    
    # by the DEP-3 header
    deb_patches = pandas.read_csv('debian_patches.csv', index_col=None, header=0, delimiter=';')
    for index, row in deb_patches.iterrows():
        if pandas.isnull(row['link']):
            continue

        patch_content = patch_helper.fetch_patch_by_link(row['link'])
        bl_has_origin = False
        bl_origin_not_deb = False
        lines = patch_content.split('\n')
        for ll in lines:
            if ll.startswith("Origin:"):
                # print(ll)
                bl_has_origin = True
                if "debian" not in ll.lower():
                    bl_origin_not_deb = True
            if bl_has_origin and ll.startswith("Bug-Debian:") and bl_origin_not_deb:
                bug_id = ""
                if "?bug=" in ll:
                    bug_id = ll[ll.index("?bug=")+5:]
                else:
                    bug_id = ll.split('/')[-1]

                if bug_id not in upstream_fixed_bug_ids:
                    upstream_fixed_bug_ids.append(bug_id)
            if ll.startswith("---"):
                break

    print('Done using the DEP-3 header...')

    os.system('mv debian_bugs.csv temp_debian_bugs.csv')
    projects = pandas.read_csv('temp_debian_bugs.csv', index_col=None, header=0, delimiter=';')
    field_names = projects.columns.values.tolist()
    field_names.append('fixed_upstream')
    # by tags
    with open('debian_bugs.csv', 'w+', newline='\n', encoding='utf8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=field_names, delimiter=';')
        writer.writeheader()

        for index, row in projects.iterrows():
            ob = {}
            for ff in field_names:
                if ff != 'fixed_upstream' and not pandas.isnull(row[ff]):
                    ob[ff] = row[ff]
                else:
                    ob[ff] = ''
            ob['fixed_upstream'] = False
            if not pandas.isnull(row['tags']) and 'fixed-upstream' in row['tags']:
                ob['fixed_upstream'] = True
            if row['id'] in upstream_fixed_bug_ids:
                ob['fixed_upstream'] = True
            if index > 0 and index % 100 == 0:
                # break
                print(index, " bugs passed ...")
                csvfile.flush()
            writer.writerow(ob)

        csvfile.close()

    os.system('rm temp_debian_bugs.csv')
    return

def mark_local_fixed_bugs(args):
    if not os.path.exists('debian_bugs.csv'):
        print('ERRPR! The bug file does not exist. Please download bugs ...')
        return
    if not os.path.exists('debian_comments/'):
        print('ERRPR! The bug comment folder does not exist. Please download bugs ...')
        return

    projects = pandas.read_csv('debian_bugs.csv', index_col=None, header=0, delimiter=';')
    bug_comment_folder = "debian_comments/"
    
    # find bug ids from bug comments
    local_fixed_bug_ids = []
    for index, row in projects.iterrows():
        bid = int(row['id'])
        if not os.path.exists(bug_comment_folder+str(bid)+".txt"):
            continue

        bl_cmt_area = False
        bl_pkg_changes = False
        
        with open(bug_comment_folder+str(bid)+".txt", 'r', newline='\n', encoding='utf8') as rFile:
            for line in rFile:
                if line.startswith("CONTENT:"):
                    bl_cmt_area = True
                
                if line.startswith("==============SPILIT_LINE=============="):
                    bl_cmt_area = False
                    bl_pkg_changes = False
                if bl_cmt_area:
                    if ".diff.gz" in line.lower():
                        continue

                    if "We believe that the bug you reported is fixed in the latest version" in line:
                        bl_pkg_changes = True
                    if line.startswith("Checksums-") or line.startswith("Files"):
                        bl_pkg_changes = False
                    if bl_pkg_changes:
                        continue

                    if ".patch" in line.lower() or ".diff" in line.lower() or ".debdiff" in line.lower():
                        local_fixed_bug_ids.append(bid)
                        break
            rFile.close()
    
    os.system('mv debian_bugs.csv temp_debian_bugs.csv')
    projects = pandas.read_csv('temp_debian_bugs.csv', index_col=None, header=0, delimiter=';')
    field_names = projects.columns.values.tolist()
    field_names.append('fixed_locally')

    # mark fixed_locally
    with open('debian_bugs.csv', 'w+', newline='\n', encoding='utf8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=field_names, delimiter=';')
        writer.writeheader()

        for index, row in projects.iterrows():
            ob = {}
            for ff in field_names:
                if ff != 'fixed_locally' and not pandas.isnull(row[ff]):
                    ob[ff] = row[ff]
                else:
                    ob[ff] = ''
            ob['fixed_locally'] = False
            if row['id'] in local_fixed_bug_ids:
                ob['fixed_locally'] = True
            if index > 0 and index % 100 == 0:
                # break
                print(index, " bugs passed ...")
                csvfile.flush()
            writer.writerow(ob)

        csvfile.close()
    return

def remove_duplicate_ids(args):
    if not os.path.exists('debian_bugs.csv'):
        print('ERRPR! The bug file does not exist. Please download bugs ...')
        return

    projects = pandas.read_csv("debian_bugs.csv", index_col=None, header=0, delimiter=';')
    df = projects.loc[projects['cf_fixed_in'].isnull() == False]
    df = df.loc[df['status'] == "Closed"]
    df = df.loc[df['cf_last_closed'].isnull() == False]
    df_dup = projects.loc[projects['duplicate_ids'].isnull() == False]
    
    dup_ids_chain = {}
    parsed_ids = []
    for index, row in df_dup.iterrows():
        if row['id'] in parsed_ids:
            continue
        arr = []
        if row['id'] in dup_ids_chain:
            arr = dup_ids_chain[row['id']]
        if row['duplicate_ids'] not in arr:
            arr.append(row['duplicate_ids'])

        look_id = []
        df = df_dup.loc[df_dup['duplicate_ids'] == row['id']]
        if len(df.index) >0:
            for df_index, df_row in df.iterrows():
                look_id.append(df_row['id'])

        cnt = 5
        look_id.append(row['duplicate_ids'])
        while cnt >0:
            new_look_ids = []
            for lid in look_id:
                df = df_dup.loc[df_dup['duplicate_ids'] == lid]
                for df_index, df_row in df.iterrows():
                    if df_row['id'] != row['id'] and df_row['id'] not in arr:
                        arr.append(df_row['id'])
                        new_look_ids.append(df_row['id'])

                df = df_dup.loc[df_dup['id'] == lid]
                for df_index, df_row in df.iterrows():
                    if df_row['duplicate_ids'] != row['id'] and df_row['duplicate_ids'] not in arr:
                        arr.append(df_row['duplicate_ids'])
                        new_look_ids.append(df_row['duplicate_ids'])

                parsed_ids.append(lid)
            if len(new_look_ids) == 0:
                break
            # print(len(new_look_ids) , new_look_ids)
            look_id = new_look_ids
            cnt -= 1

        dup_ids_chain[row['id']] = arr
    
    print(len(dup_ids_chain))
    drop_ids = []
    for ids in dup_ids_chain:
        arr = dup_ids_chain[ids].copy()
        arr.append(ids)
        # print(arr)
        df2 = df.loc[df['id'].isin(arr) & df['fixed_upstream'] == True]
        # print(len(df.index))
        if len(df2.index) > 0:
            arr.remove(df.iloc[0]['id'])
            drop_ids.extend(arr)
            continue
        df2 = df.loc[df['id'].isin(arr)]
        if len(df2.index) > 0:
            arr.remove(df.iloc[0]['id'])
            drop_ids.extend(arr)
            continue
        
        drop_ids.extend(dup_ids_chain[ids])

    projects = projects.drop(projects[projects['id'].isin(drop_ids)].index)
    projects.to_csv('debian_bugs.csv', sep=';', index=False)

if __name__== "__main__":
    
    args = docopt(__doc__)

    if bool(args['fetch']) and bool(args['pkgs']):
        fetch_pkgs(args)
    elif bool(args['fetch']) and bool(args['bugs']):
        fetch_bugs(args)
    elif bool(args['fetch']) and bool(args['patches']):
        fetch_patches(args)
    elif bool(args['mark']) and bool(args['upstream_fixed']):
        mark_upstream_fixed_bugs(args)
    elif bool(args['mark']) and bool(args['local_fixed']):
        mark_local_fixed_bugs(args)
    elif bool(args['remove']) and bool(args['duplicate_ids']):
        remove_duplicate_ids(args)