"""

Usage:
  fedora.py fetch bugs
  fedora.py fetch pkgs
  fedora.py fetch patches
  fedora.py fetch attachments
  fedora.py mark upstream_fixed
  fedora.py mark local_fixed
  fedora.py map pkg_category
  fedora.py remove duplicate_ids
  
Options:
  -h --help     Show this screen.
  
"""

from re import T
from docopt import docopt
import fedora.bugzilla_helper as bugzilla_helper
import fedora.pkg_helper as pkg_helper
import pandas, os, csv, re
import numpy as np

SEVERITY_LIST = ["high", "urgent"]

def fetch_bugs(args):
    field_names = ['id','product','severity','status','creator','assigned_to','component','summary','creation_time','last_change_time','cf_last_closed', 'version','priority','resolution','op_sys', 'cc_detail', 'duplicate_ids', 'ext_num_comments', 'ext_num_devs','ext_num_ext_links','ext_num_int_links']

    if not os.path.exists('fedora_comments/'):
        os.mkdir('fedora_comments')

    bugzilla_helper.fetch_bugs('fedora_bugs.csv', field_names, SEVERITY_LIST)

def fetch_pkgs(args):
    if not os.path.exists('fedora_bugs.csv'):
        print('ERRPR! The bug file does not exist. Please download bugs ...')
        return

    projs = pandas.read_csv('fedora_bugs.csv', index_col=None, header=0, delimiter=';')
    arr_pkg = pandas.unique(projs[['component']].values.ravel())
    
    field_names = ['name', 'pack_desc', 'upstream_url', 'is_upstream']
    with open('fedora_pkgs.csv', 'w+', newline='\n') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=field_names, delimiter=';')
        writer.writeheader()

        # print(len(arr_pkg))
        for pkg in arr_pkg:
            is_unknown = pkg_helper.is_unknown_pkg(pkg)
            
            if is_unknown:
                continue
            
            raw_hide_ob = pkg_helper.fetch_pkg_rawhide_info(pkg)
            newob = {}
            newob['name'] = pkg
            src_ob = pkg_helper.fetch_pkg_info(pkg)
            if src_ob == None and raw_hide_ob == None:
                continue
            newob['pack_desc'] = src_ob['description'].replace("\r","",100).replace("\n","",100)
            if raw_hide_ob != None:
                newob['upstream_url'] = raw_hide_ob['url']
                if newob['upstream_url'] != "":
                    newob['is_upstream'] = True
                else:
                    newob['is_upstream'] = False
            else:
                newob['is_upstream'] = False
            writer.writerow(newob)
            
        csvfile.close()
def fetch_patches(args):
    if not os.path.exists('fedora_pkgs.csv'):
        print('The package file does not exist. Please download packages ...')
        return

    projects = pandas.read_csv('fedora_pkgs.csv', index_col=None, header=0, delimiter=';')

    fieldnames = ["pkg_name", "os_version", "patch_index", "num_changed_files", "num_added_lines", "num_deleted_lines"]
    with open('fedora_patches.csv', 'w+', newline='\n', encoding='utf8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()

        for index, row in projects.iterrows():
            os.system("mkdir -p fedora_src/"+row['name'])
            branches = pkg_helper.clone_pkg_source(row['name'])
            for bb in branches:
                if bb == "origin/master":
                    continue

                os_version = -1
                if bb.replace("origin/f","").isdigit():
                    os_version = int(bb.replace("origin/f",""))
                elif bb.replace("origin/","").isdigit():
                    os_version = int(bb.replace("origin/",""))
                else:
                    # print(bb)
                    continue
                # print(os_version)
                    
                patches = pkg_helper.fetch_patches(row['name'],bb, os_version)
                writer.writerows(patches)
                # print(patches)

            os.system("rm -rf fedora_src/"+row['name'])
            
            if index > 0 and index % 100 == 0:
                print(index, " packages passed ...")
                csvfile.flush()

        csvfile.close()
        os.system("rm -rf fedora_src")
        
def mark_upstream_fixed_bugs(args):
    if not os.path.exists('fedora_pkgs.csv'):
        print('ERRPR! The package file does not exist. Please download packages ...')
        return
    if not os.path.exists('fedora_bugs.csv'):
        print('ERRPR! The bug file does not exist. Please download bugs ...')
        return

    projects = pandas.read_csv('fedora_pkgs.csv', index_col=None, header=0, delimiter=';')
    df_up_pkgs = projects.loc[projects['is_upstream'] == True]
    
    # by changelogs
    upstream_fixed_bug_ids = []
    for index, row in df_up_pkgs.iterrows():
        os.system("mkdir -p fedora_src/"+row['name'])
        pkg_helper.clone_pkg_source_depth_5(row['name'])
        
        if not os.path.exists('fedora_src/'+row['name']+'/'+row['name']+'.spec'):
            continue
        with open('fedora_src/'+row['name']+'/'+row['name']+'.spec', 'r', newline='\n', encoding='utf8') as rFile:
            bl_changelogs = False
            rexp_bug = "#[\d]{4,7}"
            num_left_spaces = 100
            bl_start_with_dash = False
            bl_upstream_release = False
            for line in rFile:

                if bl_changelogs and line.strip().startswith("%"):
                    bl_changelogs = False

                if line.strip().startswith("%changelog"):
                    bl_changelogs = True
                
                if bl_changelogs:
                    cnt_left_space = len(line) - len(line.lstrip(' '))
                    if "upstream" in line.lower():
                        bug_ids = re.findall(rexp_bug, line, re.I)
                        if len(bug_ids) > 0:
                            upstream_fixed_bug_ids = upstream_fixed_bug_ids+ bug_ids

                        bl_upstream_release = True
                        if line.strip().startswith("-"):
                            bl_start_with_dash = True
                        num_left_spaces = len(line) - len(line.lstrip(' '))
                        
                    else:
                        if cnt_left_space < num_left_spaces:
                            num_left_spaces = 100
                            bl_start_with_dash = False
                            bl_upstream_release = False
                        elif bl_start_with_dash and cnt_left_space == num_left_spaces:
                            num_left_spaces = 100
                            bl_start_with_dash = False
                            bl_upstream_release = False
                    
                    if bl_upstream_release:
                        if cnt_left_space > num_left_spaces:
                            bug_ids = re.findall(rexp_bug, line, re.I)
                            if len(bug_ids) > 0:
                                # print(bug_ids, line.strip())
                                upstream_fixed_bug_ids = upstream_fixed_bug_ids+ bug_ids

                        elif cnt_left_space == num_left_spaces and bl_start_with_dash:
                            bug_ids = re.findall(rexp_bug, line, re.I)
                            if len(bug_ids) > 0:
                                # print(bug_ids, line.strip())
                                upstream_fixed_bug_ids = upstream_fixed_bug_ids+ bug_ids


        rFile.close()
        upstream_fixed_bug_ids = list(set(upstream_fixed_bug_ids))
        os.system('rm -rf fedora_src/'+row['name'])

        if index > 0 and index % 100 == 0:
            print(index, " packages passed ...")
    os.system("rm -rf fedora_src")
    # print(len(upstream_fixed_bug_ids))
    # print("Done parsing changelogs...")

    os.system('mv fedora_bugs.csv temp_fedora_bugs.csv')
    projects = pandas.read_csv('temp_fedora_bugs.csv', index_col=None, header=0, delimiter=';')
    field_names = projects.columns.values.tolist()
    
    field_names.append('fixed_upstream')
    # by tags
    with open('fedora_bugs.csv', 'w+', newline='\n', encoding='utf8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=field_names, delimiter=';')
        writer.writeheader()

        for index, row in projects.iterrows():
            ob = {}
            for ff in field_names:
                if ff != 'fixed_upstream':
                    ob[ff] = row[ff]
            ob['fixed_upstream'] = False
            if row['resolution'] == "UPSTREAM":
                ob['fixed_upstream'] = True
            if '#'+str(row['id']) in upstream_fixed_bug_ids:
                ob['fixed_upstream'] = True

            if index > 0 and index % 100 == 0:
                print(index, " bugs passed ...")
                csvfile.flush()
            writer.writerow(ob)

        csvfile.close()

    os.system('rm temp_fedora_bugs.csv')

def fetch_attachments(args):
    if not os.path.exists('fedora_pkgs.csv'):
        print('ERRPR! The package file does not exist. Please download packages ...')
        return
    if not os.path.exists('fedora_bugs.csv'):
        print('ERRPR! The bug file does not exist. Please download bugs ...')
        return

    projects = pandas.read_csv('fedora_bugs.csv', index_col=None, header=0, delimiter=';')
    fieldnames = ["id","attachment_id","is_patch","creator","flags","is_obsolete","is_private","summary","file_name","last_change_time","creation_time","size","content_type"]
    ids = []
    with open("fedora_bug_attachments.csv", 'w+', newline='\n', encoding='utf8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()

        for index, row in projects.iterrows():
            if index >0 and index % 50 == 0:
                datas = bugzilla_helper.batch_fetch_attachments(ids)
                writer.writerows(datas)
                ids = []
            
            ids.append(row['id'])

        if len(ids)>0:
            datas = bugzilla_helper.batch_fetch_attachments(ids)
            writer.writerows(datas)
            ids = []
        csvfile.close()

def mark_local_fixed_bugs(args):
    if not os.path.exists('fedora_bug_attachments.csv'):
        print('ERRPR! The bug attachments file does not exist. Please download bug attachements ...')
        return
    if not os.path.exists('fedora_pkgs.csv'):
        print('ERRPR! The package file does not exist. Please download packages ...')
        return
    if not os.path.exists('fedora_bugs.csv'):
        print('ERRPR! The bug file does not exist. Please download bugs ...')
        return

    projects = pandas.read_csv('fedora_pkgs.csv', index_col=None, header=0, delimiter=';')
    df_up_pkgs = projects.loc[projects['is_upstream'] == True]
    
    # by changelogs
    local_fixed_bug_ids = []
    for index, row in df_up_pkgs.iterrows():
        os.system("mkdir -p fedora_src/"+row['name'])
        pkg_helper.clone_pkg_source_depth_5(row['name'])
        
        if not os.path.exists('fedora_src/'+row['name']+'/'+row['name']+'.spec'):
            continue
        with open('fedora_src/'+row['name']+'/'+row['name']+'.spec', 'r', newline='\n', encoding='utf8') as rFile:
            bl_changelogs = False
            rexp_bug = "[\d]{4,8}"
            for line in rFile:

                if bl_changelogs and line.strip().startswith("%"):
                    bl_changelogs = False

                if line.strip().startswith("%changelog"):
                    bl_changelogs = True
                
                if bl_changelogs:
                    if "bz" in line.lower() and "upstream" not in line.lower() and "workaround" in line.lower():
                        bug_ids = re.findall(rexp_bug, line, re.I)
                        local_fixed_bug_ids.extend(bug_ids)
                    if "bz" in line.lower() and "upstream" not in line.lower() and "work-around" in line.lower():
                        bug_ids = re.findall(rexp_bug, line, re.I)
                        local_fixed_bug_ids.extend(bug_ids)
                    if "bz" in line.lower() and "upstream" not in line.lower() and "temporar" in line.lower():
                        bug_ids = re.findall(rexp_bug, line, re.I)
                        local_fixed_bug_ids.extend(bug_ids)
                    if "bz" in line.lower() and "upstream" not in line.lower() and "patch" in line.lower():
                        bug_ids = re.findall(rexp_bug, line, re.I)
                        local_fixed_bug_ids.extend(bug_ids)

        rFile.close()

        # only unique ids
        local_fixed_bug_ids = list(set(local_fixed_bug_ids))
        os.system('rm -rf fedora_src/'+row['name'])

        if index > 0 and index % 100 == 0:
            print(index, " packages passed ...")
            
    os.system("rm -rf fedora_src")

    # by attachments
    df_patches = pandas.read_csv('fedora_bug_attachments.csv', index_col=None, header=0, delimiter=';')
    df_patched_bugs = df_patches.loc[(df_patches['is_patch'] == True) & (df_patches['is_obsolete'] == False)]
    
    os.system('mv fedora_bugs.csv temp_fedora_bugs.csv')
    projects = pandas.read_csv('temp_fedora_bugs.csv', index_col=None, header=0, delimiter=';')
    field_names = projects.columns.values.tolist()
    
    field_names.append('fixed_locally')
    with open('fedora_bugs.csv', 'w+', newline='\n', encoding='utf8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=field_names, delimiter=';')
        writer.writeheader()

        for index, row in projects.iterrows():
            ob = {}
            for ff in field_names:
                if ff != 'fixed_locally':
                    ob[ff] = row[ff]
            ob['fixed_locally'] = False
            if str(row['id']) in local_fixed_bug_ids:
                ob['fixed_locally'] = True
            else:
                if len(df_patched_bugs[df_patched_bugs['id'] == row['id']].index)>0:
                    ob['fixed_locally'] = True

            if index > 0 and index % 100 == 0:
                print(index, " bugs passed ...")
                csvfile.flush()
            writer.writerow(ob)

        csvfile.close()

    os.system('rm temp_fedora_bugs.csv')

def map_pkg_category(args):
    if not os.path.exists('fedora_pkgs.csv'):
        print('ERRPR! The package file does not exist. Please download packages ...')
        return
    if not os.path.exists('debian_pkgs.csv'):
        print("ERRPR! The Debian's package file does not exist. Please download packages ...")
        return

    os.system('mv fedora_pkgs.csv temp_fedora_pkgs.csv')
    deb_pkgs = pandas.read_csv('debian_pkgs.csv', index_col=None, header=0, delimiter=';')
    projects = pandas.read_csv('temp_fedora_pkgs.csv', index_col=None, header=0, delimiter=';')
    df = projects.merge(deb_pkgs[['name', 'pkg_category']], on='name', how='left')
    
    # by prefix, suffix, keywords
    mask = df['pkg_category'].isna() & df['pack_desc'].str.contains('game')
    df.loc[mask,["pkg_category"]] = "games"
    mask = df['pkg_category'].isna() & df['name'].str.contains('(?i)abrt|grubby|dnf|yumex')
    df.loc[mask,["pkg_category"]] = "admin"
    mask = df['pkg_category'].isna() & df['name'].str.contains('(?i)mysql')
    df.loc[mask,["pkg_category"]] = "database"
    mask = df['pkg_category'].isna() & df['name'].str.contains('(?i)-java-|glibc|anaconda|golang')
    df.loc[mask,["pkg_category"]] = "devel"
    mask = df['pkg_category'].isna() & df['name'].str.startswith('(?i)python-|perl-')
    df.loc[mask,["pkg_category"]] = "devel"
    mask = df['pkg_category'].isna() & df['name'].str.endswith('(?i)-devel')
    df.loc[mask,["pkg_category"]] = "devel"
    mask = df['pkg_category'].isna() & df['name'].str.startswith('(?i)kde-')
    df.loc[mask,["pkg_category"]] = "desktop"
    mask = df['pkg_category'].isna() & df['name'].str.contains('(?i)document|documentation|-doc|javadoc')
    df.loc[mask,["pkg_category"]] = "editor"
    mask = df['pkg_category'].isna() & df['name'].str.contains('(?i)library|-lib|mesa|lroax')
    df.loc[mask,["pkg_category"]] = "libs"
    mask = df['pkg_category'].isna() & df['name'].str.contains('(?i)i18n|-l10n')
    df.loc[mask,["pkg_category"]] = "localization"
    mask = df['pkg_category'].isna() & df['name'].str.contains('(?i)font')
    df.loc[mask,["pkg_category"]] = "fonts"
    mask = df['pkg_category'].isna() & df['name'].str.contains('(?i)networkmanager|freeipa|firefox')
    df.loc[mask,["pkg_category"]] = "network"
    mask = df['pkg_category'].isna() & df['name'].str.contains('(?i)firefox')
    df.loc[mask,["pkg_category"]] = "web"
    
    df = df.replace(np.nan, '', regex=True)
    field_names = df.columns.values.tolist()
    with open('fedora_pkgs.csv', 'w+', newline='\n', encoding='utf8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=field_names, delimiter=';')
        writer.writeheader()

        for _, row in df.iterrows():
            ob = {}
            for ff in field_names:
                ob[ff] = row[ff]
            writer.writerow(ob)

        csvfile.close()

    os.system('rm temp_fedora_pkgs.csv')

def remove_duplicate_ids(args):
    if not os.path.exists('fedora_bugs.csv'):
        print('ERRPR! The bug file does not exist. Please download bugs ...')
        return
    
    projects = pandas.read_csv('fedora_bugs.csv', index_col=None, header=0, delimiter=';')
    res_list = ["CURRENTRELEASE", "UPSTREAM","NEXTRELEASE","ERRATA"]
    df = projects.loc[projects['resolution'].isin(res_list)]
    df = df[df['status'] == "CLOSED"] 
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

            look_id = new_look_ids
            cnt -= 1

        dup_ids_chain[row['id']] = arr
    
    drop_ids = []
    for ids in dup_ids_chain:
        arr = dup_ids_chain[ids].copy()
        arr.append(ids)
        
        df2 = df.loc[df['id'].isin(arr) & df['fixed_upstream'] == True]
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
    projects.to_csv('fedora_bugs.csv', sep=';', index=False)


if __name__== "__main__":
    args = docopt(__doc__)
    if bool(args['fetch']) and bool(args['bugs']):
        fetch_bugs(args)
    elif bool(args['fetch']) and bool(args['pkgs']):
        fetch_pkgs(args)
    elif bool(args['fetch']) and bool(args['patches']):
        fetch_patches(args)
    elif bool(args['fetch']) and bool(args['attachments']):
        fetch_attachments(args)
    elif bool(args['mark']) and bool(args['upstream_fixed']):
        mark_upstream_fixed_bugs(args)
    elif bool(args['mark']) and bool(args['local_fixed']):
        mark_local_fixed_bugs(args)
    elif bool(args['map']) and bool(args['pkg_category']):
        map_pkg_category(args)
    elif bool(args['remove']) and bool(args['duplicate_ids']):
        remove_duplicate_ids(args)
