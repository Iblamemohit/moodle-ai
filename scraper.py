#!/usr/bin/env python3
import os
import sys
import itertools
import re
import datetime
import configparser
import urllib.request
import urllib.parse
from requests import session
from bs4 import BeautifulSoup

# read config from .env
from src.config import get_config

cfg = get_config()
username = cfg.get("user", "")
password = cfg.get("password", "")
root = cfg.get("output_dir", "output")
baseurls = cfg.get("baseurls", ["https://moodle.iitd.ac.in/", "https://moodlenew.iitd.ac.in/"])

if not username or not password or username == "your_kerberos_id_here":
    print("Error: Kerberos credentials not found in '.env'.")
    print("Please copy '.env.sample' to '.env' and fill in your Moodle credentials:")
    print("  cp .env.sample .env")
    sys.exit(1)

if not root.endswith('/'):
    root += '/'

sections = itertools.count()
files = itertools.count()


class colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def solve_captcha(text):
    text = ' '.join(text.split())
    m1 = re.search(r'first\s+value\s+(\d+)\s*,\s*(\d+)', text, re.IGNORECASE)
    if m1:
        return str(int(m1.group(1)))
    m2 = re.search(r'second\s+value\s+(\d+)\s*,\s*(\d+)', text, re.IGNORECASE)
    if m2:
        return str(int(m2.group(2)))
    m3 = re.search(r'add\s+(\d+)\s*\+\s*(\d+)', text, re.IGNORECASE)
    if m3:
        return str(int(m3.group(1)) + int(m3.group(2)))
    m4 = re.search(r'subtract\s+(\d+)\s*-\s*(\d+)', text, re.IGNORECASE)
    if m4:
        return str(int(m4.group(1)) - int(m4.group(2)))
    return None


def login(baseurl, user, pwd):
    ses = session()
    ses.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    })
    login_url = baseurl + 'login/index.php'
    try:
        r = ses.get(login_url, timeout=15)
    except Exception as e:
        print(colors.FAIL + f"Connection Error: Could not reach {login_url}" + colors.ENDC)
        print(f"Details: {e}")
        return None

    soup = BeautifulSoup(r.text, 'html.parser')
    
    authdata = {
        'username': user,
        'password': pwd
    }
    
    # Collect form inputs & CSRF tokens if any (e.g. logintoken)
    form = soup.find('form', id='login') or soup.find('form')
    if form:
        for inp in form.find_all('input'):
            name = inp.get('name')
            if name and name not in authdata:
                authdata[name] = inp.get('value', '')
        
        # Check for captcha in form text (e.g. classic IIT Delhi Moodle)
        form_text = form.get_text(' ')
        captcha_ans = solve_captcha(form_text)
        if captcha_ans:
            print(f"[{urllib.parse.urlparse(baseurl).netloc}] Solving login captcha: {captcha_ans}")
            if 'valuepkg3' in authdata or form.find('input', id='valuepkg3'):
                authdata['valuepkg3'] = captcha_ans
            else:
                for inp in form.find_all('input'):
                    if inp.get('type') in ('text', 'number') and inp.get('name') not in ('username', 'password'):
                        authdata[inp.get('name')] = captcha_ans

    try:
        post_resp = ses.post(login_url, data=authdata, timeout=15)
        post_soup = BeautifulSoup(post_resp.text, 'html.parser')
        err = post_soup.find(class_='loginerrors') or post_soup.find(class_='alert-danger')
        if err:
            print(colors.FAIL + f"[{urllib.parse.urlparse(baseurl).netloc}] Login failed: {err.get_text().strip()}" + colors.ENDC)
            return None
    except Exception as e:
        print(colors.FAIL + f"[{urllib.parse.urlparse(baseurl).netloc}] Connection Error during login: {e}" + colors.ENDC)
        return None

    return ses


def _get_courses_for_instance(baseurl, ses):
    """Scrapes all enrolled courses from a single Moodle instance (supporting 2.x, 3.x, and 4.x)"""
    courses_dict = {}
    netloc = urllib.parse.urlparse(baseurl).netloc
    site_tag = netloc.split('.')[0]  # e.g. moodle or moodlenew

    # 1. Try Moodle 4.x AJAX WebService
    try:
        my_page = ses.get(baseurl + 'my/', timeout=10)
        sesskey_m = re.search(r'\"sesskey\":\s*\"([^\"]+)\"', my_page.text) or re.search(r'sesskey=([a-zA-Z0-9]+)', my_page.text)
        if sesskey_m:
            sesskey = sesskey_m.group(1)
            ajax_url = f'{baseurl}lib/ajax/service.php?sesskey={sesskey}&info=core_course_get_enrolled_courses_by_timeline_classification'
            payload = [{
                'index': 0,
                'methodname': 'core_course_get_enrolled_courses_by_timeline_classification',
                'args': {
                    'offset': 0,
                    'limit': 0,
                    'classification': 'all',
                    'sort': 'fullname',
                    'customfieldname': '',
                    'customfieldvalue': ''
                }
            }]
            ajax_resp = ses.post(ajax_url, json=payload, timeout=10)
            if ajax_resp.status_code == 200:
                data = ajax_resp.json()
                if isinstance(data, list) and len(data) > 0:
                    courses = data[0].get('data', {}).get('courses', [])
                    for c in courses:
                        cid = str(c.get('id'))
                        fullname = c.get('fullname', '')
                        shortname = c.get('shortname', '')
                        viewurl = c.get('viewurl') or f'{baseurl}course/view.php?id={cid}'
                        
                        key = shortname if shortname else (fullname.split()[0] if fullname else f'Course_{cid}')
                        sem = 'General'
                        prefix_match = re.match(r'^(\d{4})[-_]', key) or re.match(r'^(\d{4})[-_]', fullname)
                        if prefix_match:
                            sem = prefix_match.group(1)

                        display_name = f"{key}: {fullname}" if shortname and shortname != fullname else (fullname or key)
                        courses_dict[f"{site_tag}_{cid}"] = {
                            'url': viewurl,
                            'name': display_name,
                            'key': key,
                            'sem': sem,
                            'type': 'Course',
                            'baseurl': baseurl,
                            'session': ses,
                            'site_tag': site_tag
                        }
    except Exception:
        pass

    # 2. Try User Profile page (/user/profile.php)
    if not courses_dict:
        try:
            prof_resp = ses.get(baseurl + 'user/profile.php', timeout=10)
            if prof_resp.status_code == 200:
                psoup = BeautifulSoup(prof_resp.text, 'html.parser')
                for a in psoup.find_all('a', href=lambda h: h and ('course=' in h or '/course/view.php?id=' in h)):
                    url = a.get('href')
                    text = a.get_text().strip()
                    if not text or text.lower() in ('view course', 'course', 'edit profile'):
                        continue
                    m = re.search(r'(?:course=|id=)(\d+)', url)
                    if m:
                        cid = m.group(1)
                        c_unique_key = f"{site_tag}_{cid}"
                        if c_unique_key not in courses_dict:
                            key = text.split()[0] if text else f"Course_{cid}"
                            sem = "General"
                            prefix_match = re.match(r'^(\d{4})[-_]', key)
                            if prefix_match:
                                sem = prefix_match.group(1)
                            courses_dict[c_unique_key] = {
                                'url': f'{baseurl}course/view.php?id={cid}',
                                'name': text,
                                'key': key,
                                'sem': sem,
                                'type': 'Course',
                                'baseurl': baseurl,
                                'session': ses,
                                'site_tag': site_tag
                            }
        except Exception:
            pass

    # 3. Try Static HTML links on /my/ and /index.php
    if not courses_dict:
        for page in ('my/', 'index.php'):
            try:
                r = ses.get(baseurl + page, timeout=10)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, 'html.parser')
                    for a in soup.find_all('a', href=lambda h: h and '/course/view.php?id=' in h):
                        url = a.get('href')
                        text = a.get_text().strip()
                        if not text or text.lower() in ('view course', 'course'):
                            continue
                        m = re.search(r'id=(\d+)', url)
                        if m:
                            cid = m.group(1)
                            c_unique_key = f"{site_tag}_{cid}"
                            if c_unique_key not in courses_dict:
                                parts = text.split()
                                key = parts[0] if parts else f"Course_{cid}"
                                sem = "General"
                                prefix_match = re.match(r'^(\d{4})[-_]', key)
                                if prefix_match:
                                    sem = prefix_match.group(1)
                                courses_dict[c_unique_key] = {
                                    'url': url,
                                    'name': text,
                                    'key': key,
                                    'sem': sem,
                                    'type': 'Course',
                                    'baseurl': baseurl,
                                    'session': ses,
                                    'site_tag': site_tag
                                }
            except Exception:
                pass

    return list(courses_dict.values())


def getAllCoursesAndSemesters(sessions_by_url):
    """Aggregates courses and semester groupings from all active Moodle sessions"""
    all_courses = []
    for baseurl, ses in sessions_by_url.items():
        if ses:
            site_courses = _get_courses_for_instance(baseurl, ses)
            all_courses.extend(site_courses)

    # Build semester groups
    semesters = {}
    sem_groups = set(c['sem'] for c in all_courses)
    for s in sorted(sem_groups):
        count = sum(1 for c in all_courses if c['sem'] == s)
        semesters[s] = f"Semester {s} ({count} courses)" if s != "General" else f"General Courses ({count} courses)"
    if len(sem_groups) > 1:
        semesters['all'] = f"All Enrolled Courses ({len(all_courses)} courses across all sites)"

    return all_courses, semesters


def saveFile(session_obj, src, path, name, on_file_saved=None):
    global files
    next(files)
    dst = os.path.join(path, name) if not path.endswith('/') else path + name
    dst = dst.replace(':', '-').replace('"', '')

    if os.path.exists(dst):
        print('[' + colors.OKBLUE + 'skip' + colors.ENDC + '] |  |  +--%s' % name)
        if on_file_saved:
            try:
                on_file_saved(dst, is_new=False)
            except Exception:
                pass
        return

    try:
        with open(dst, 'wb') as handle:
            print('[' + colors.OKGREEN + 'save' + colors.ENDC + '] |  |  +--%s' % name)
            r = session_obj.get(src, stream=True, allow_redirects=True)
            for block in r.iter_content(1024):
                if not block:
                    break
                handle.write(block)
        if on_file_saved:
            try:
                on_file_saved(dst, is_new=True)
            except Exception:
                pass
    except Exception as e:
        print('[' + colors.FAIL + 'fail' + colors.ENDC + '] |  |  +--%s (%s)' % (name, e))


def saveLink(session_obj, url, path, name, on_file_saved=None):
    global files
    next(files)
    fname = name.replace('/', '') + '.html'
    dst = os.path.join(path, fname) if not path.endswith('/') else path + fname
    dst = dst.replace(':', '-').replace('"', '')

    if os.path.exists(dst):
        print('[' + colors.OKBLUE + 'skip' + colors.ENDC + '] |  |  +--%s' % name)
        if on_file_saved:
            try:
                on_file_saved(dst, is_new=False)
            except Exception:
                pass
        return

    try:
        with open(dst, 'w', encoding='utf-8') as handle:
            print('[' + colors.OKGREEN + 'save' + colors.ENDC + '] |  |  +--%s' % name)
            r = session_obj.get(url)
            soup = BeautifulSoup(r.text, 'html.parser')
            region = soup.find(class_='region-content') or soup.find(class_='urlworkaround')
            if region and region.find('a'):
                link = region.find('a').get('href', url)
                handle.write(f'<a href="{link}">{name}</a>')
            else:
                handle.write(f'<a href="{url}">{name}</a>')
        if on_file_saved:
            try:
                on_file_saved(dst, is_new=True)
            except Exception:
                pass
    except Exception as e:
        if os.path.exists(dst):
            os.remove(dst)
        print('[' + colors.FAIL + 'fail' + colors.ENDC + '] |  |  +--%s (%s)' % (name, e))


def saveInfo(path, info, tab, on_file_saved=None):
    if "Foren" not in info and info.strip():
        global files
        next(files)
        name = 'info.txt'
        dst = os.path.join(path, name) if not path.endswith('/') else path + name
        dst = dst.replace(':', '-').replace('"', '')

        if os.path.exists(dst):
            print('[' + colors.OKBLUE + 'skip' + colors.ENDC + '] ' + tab + '+--%s' % name)
            if on_file_saved:
                try:
                    on_file_saved(dst, is_new=False)
                except Exception:
                    pass
            return

        try:
            with open(dst, 'w', encoding='utf-8') as handle:
                print('[' + colors.OKGREEN + 'save' + colors.ENDC + '] ' + tab + '+--%s' % name)
                handle.write(info)
            if on_file_saved:
                try:
                    on_file_saved(dst, is_new=True)
                except Exception:
                    pass
        except Exception as e:
            print('[' + colors.FAIL + 'fail' + colors.ENDC + '] ' + tab + '+--%s (%s)' % (name, e))


def downloadResource(session_obj, res, path, on_file_saved=None):
    try:
        if isinstance(res, str):
            src = res
        elif hasattr(res, 'get') and res.get('href'):
            src = res.get('href')
        elif getattr(res, 'a', None) and res.a.get('href'):
            src = res.a.get('href')
        else:
            return
    except (TypeError, AttributeError, KeyError):
        return

    r = session_obj.get(src, allow_redirects=True)
    if r.status_code == 200:
        headers = {k.lower(): v for k, v in r.headers.items()}
        name = None
        if 'content-disposition' in headers:
            cd = headers['content-disposition']
            m = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';\r\n]+)', cd, re.IGNORECASE)
            if m:
                name = m.group(1).strip('"\' ')
        
        if not name:
            parsed = urllib.parse.urlparse(r.url)
            basename = os.path.basename(parsed.path)
            if basename and '.' in basename:
                name = basename
            else:
                soup = BeautifulSoup(r.text, 'html.parser')
                region = soup.find(class_='region-content') or soup.find(class_='resourcecontent')
                if region and region.find('a'):
                    src = region.find('a').get('href', src)
                frames = soup.find_all('frame')
                if len(frames) > 1 and frames[1].get('src'):
                    src = frames[1]['src']
                name = os.path.basename(urllib.parse.urlparse(src).path) or 'resource'

        name = urllib.request.url2pathname(name)
        saveFile(session_obj, r.url if r.url else src, path, name, on_file_saved=on_file_saved)
    else:
        print('ERROR: ' + str(r.status_code) + ' ' + str(r.reason))


def downloadFolder(session_obj, folder_url, path, on_file_saved=None):
    """Downloads all files inside a Moodle folder activity (/mod/folder/view.php)"""
    r = session_obj.get(folder_url)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        # Check for download folder button
        btn = soup.find('form', action=lambda a: a and 'download_folder.php' in a)
        if btn:
            action = btn.get('action')
            inputs = {i.get('name'): i.get('value') for i in btn.find_all('input') if i.get('name')}
            resp = session_obj.post(action, data=inputs)
            if resp.status_code == 200:
                name = 'folder.zip'
                cd = resp.headers.get('content-disposition', '')
                m = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';\r\n]+)', cd, re.IGNORECASE)
                if m:
                    name = m.group(1).strip('"\' ')
                saveFile(session_obj, resp.url, path, name, on_file_saved=on_file_saved)
                return
        
        # Parse individual files inside folder view
        for a in soup.find_all('a', href=lambda h: h and '/pluginfile.php/' in h):
            downloadResource(session_obj, a.get('href'), path, on_file_saved=on_file_saved)


def is_generic_or_date_section(name):
    clean = name.strip().strip('/').strip()
    if not clean or clean.lower() in ('general', 'section-0', 'section 0', 'section_section-0'):
        return True
    
    # Generic "Topic 1", "Topic 2", "Thema 1", "Section 1", "Section_1"
    if re.match(r'^(?:Topic|Thema|Section|Unit)\s*[-_]?\s*\d+$', clean, re.IGNORECASE):
        return True
        
    months = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    if re.search(rf'\b\d{{1,2}}\s+{months}\s*[-–—]\s*\d{{1,2}}\s+{months}', clean, re.IGNORECASE):
        return True
    if re.search(rf'\b{months}\s+\d{{1,2}}\s*[-–—]\s*(?:{months}\s+)?\d{{1,2}}', clean, re.IGNORECASE):
        return True
    if re.search(r'\b\d{1,2}[./]\d{1,2}\s*[-–—]\s*\d{1,2}[./]\d{1,2}', clean):
        return True
    return False


def downloadSection(session_obj, s, path, on_file_saved=None):
    global sections
    sec_id = s.get('id', '')
    
    # Section title
    sec_name_tag = s.find(class_='sectionname') or s.find(class_='section-title') or s.find('h3') or s.find('h4')
    if sec_name_tag:
        raw_name = sec_name_tag.get_text().strip().replace('/', '-').strip(':')
    else:
        raw_name = 'General' if sec_id == 'section-0' else f'Section_{sec_id}'

    # Summary / Info
    summary_tag = s.find(class_='summary') or s.find(class_='activity label modtype_label ')
    info = summary_tag.get_text().strip() if summary_tag else ''

    # Check if section is a date range or generic section (e.g. Topic 1, General)
    if is_generic_or_date_section(raw_name):
        secpath = path
    else:
        name = raw_name + '/'
        secpath = os.path.join(path, name) if not path.endswith('/') else path + name
        secpath = secpath.replace(':', '-').replace('"', '')
        if not os.path.exists(secpath):
            os.makedirs(secpath, exist_ok=True)
        print('       |  +--' + colors.BOLD + name + colors.ENDC)
    if info:
        saveInfo(secpath, info, '|  ', on_file_saved=on_file_saved)

    # Activities: resources, folders, urls
    activities = s.find_all('li', class_=lambda c: c and 'activity' in c) or s.find_all(class_=lambda c: c and 'activity-item' in c)
    for act in activities:
        classes = act.get('class', [])
        link_tag = act.find('a')
        if not link_tag:
            continue
        href = link_tag.get('href', '')
        
        if any('resource' in c for c in classes) or '/mod/resource/' in href:
            downloadResource(session_obj, href, secpath, on_file_saved=on_file_saved)
        elif any('folder' in c for c in classes) or '/mod/folder/' in href:
            inst = act.find(class_='instancename') or act.find(class_='activityname')
            f_name = inst.get_text().strip().replace('/', '-') if inst else 'Folder'
            f_path = os.path.join(secpath, f_name)
            os.makedirs(f_path, exist_ok=True)
            downloadFolder(session_obj, href, f_path + '/', on_file_saved=on_file_saved)
        elif any('url' in c for c in classes) or '/mod/url/' in href:
            inst = act.find(class_='instancename') or act.find(class_='activityname')
            url_name = inst.get_text().strip() if inst else 'link'
            saveLink(session_obj, href, secpath, url_name, on_file_saved=on_file_saved)

    # Generalbox foldertree
    folders = s.find_all(class_='box generalbox foldertree')
    for f in folders:
        res = f.find_all(class_='fp-filename-icon')
        if res:
            label = res.pop(0).text
            subpath = os.path.join(secpath, label.replace('/', '-'))
            subpath = urllib.request.url2pathname(subpath).replace(':', '-').replace('"', '')
            if not os.path.exists(subpath):
                os.makedirs(subpath, exist_ok=True)
            print('       |  +--' + colors.BOLD + label + colors.ENDC)
            for r in res:
                downloadResource(session_obj, r, subpath + '/', on_file_saved=on_file_saved)

    # Remove directory if empty
    if os.path.exists(secpath) and not os.listdir(secpath):
        try:
            os.rmdir(secpath)
        except OSError:
            pass


def downloadCourse(course_item, sem_label, on_file_saved=None):
    session_obj = course_item['session']
    global files
    global sections
    files = itertools.count()
    sections = itertools.count()
    name = course_item['key'].replace('/', '-') + '/'
    course_dir = os.path.join(root, str(sem_label).replace('/', '-'), name)
    course_dir = urllib.request.url2pathname(course_dir).replace(':', '-').replace('"', '')
    if not os.path.exists(course_dir):
        os.makedirs(course_dir, exist_ok=True)
    print('       +--' + colors.BOLD + name + colors.ENDC)
    r = session_obj.get(course_item['url'])
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        dump_dir = os.path.join(course_dir, '.dump')
        if not os.path.exists(dump_dir):
            os.makedirs(dump_dir, exist_ok=True)

        dst = os.path.join(dump_dir, course_item['key'].replace('/', '-') + '-' + course_item.get('type', 'Course') + '-' + str(datetime.date.today()) + '-full.html')
        dst = dst.replace(':', '-').replace('"', '')

        with open(dst, 'w', encoding='utf-8') as f:
            f.write(str(soup))
            
        sec_elements = soup.find_all('li', class_=lambda c: c and 'section' in c)
        if not sec_elements:
            sec_elements = soup.find_all(class_=lambda c: c and ('course-section' in c or 'section main' in c))
        
        for s in sec_elements:
            downloadSection(session_obj, s, course_dir, on_file_saved=on_file_saved)

        # Remove any empty subdirectories left behind
        for root_d, dirs, files_list in os.walk(course_dir, topdown=False):
            for d in dirs:
                if d == '.dump':
                    continue
                full_d = os.path.join(root_d, d)
                try:
                    if not os.listdir(full_d):
                        os.rmdir(full_d)
                except OSError:
                    pass
    else:
        print('ERROR: ' + str(r.status_code) + ' ' + str(r.reason))


def main():
    print(colors.HEADER)
    banner = r"""
      _____                    .___.__              
     /     \   ____   ____   __| _/|  |   ____      
    /  \ /  \ /  _ \ /  _ \ / __ | |  | _/ __ \     
   /    Y    (  <_> |  <_> ) /_/ | |  |_\  ___/     
   \____|__  /\____/ \____/\____ | |____/\___  >    
           \/                   \/           \/     
  _________                                         
 /   _____/ ________________  ______   ___________  
 \_____  \_/ ___\_  __ \__  \ \____ \_/ __ \_  __ \ 
 /        \  \___|  | \// __ \|  |_> >  ___/|  | \/ 
/_______  /\___  >__|  (____  /   __/ \___  >__|    
        \/     \/           \/|__|        \/        
"""
    print(banner)
    print(colors.ENDC)

    # logging into all configured Moodle sites
    sessions_by_url = {}
    print(f"Logging into {len(baseurls)} Moodle site(s)...")
    for b_url in baseurls:
        print(f"  --> Connecting to {b_url} ...")
        ses = login(b_url, username, password)
        if ses:
            sessions_by_url[b_url] = ses
            print(colors.OKGREEN + f"  [OK] Logged into {b_url}" + colors.ENDC)
        else:
            print(colors.FAIL + f"  [FAIL] Could not log into {b_url}" + colors.ENDC)

    if not sessions_by_url:
        print(colors.FAIL + 'Could not log into any Moodle site. Please check your credentials and network connection.' + colors.ENDC)
        sys.exit(1)

    # discover courses & semesters across all sites
    print("\nDiscovering courses across all configured Moodle sites...")
    all_courses, sems = getAllCoursesAndSemesters(sessions_by_url)
    
    if not all_courses:
        print(colors.FAIL + 'No courses found across configured Moodle sites - Quitting!' + colors.ENDC)
        sys.exit(0)

    print(colors.WARNING + f'\nAvailable semesters ({len(all_courses)} total courses found):' + colors.ENDC)
    for s_key in sorted(sems.keys()):
        print(f'[{s_key}]: {sems[s_key]}')

    # input loop
    s = ''
    while s not in sems:
        s = input(colors.WARNING + '\nSelect semester (or "all"): ' + colors.ENDC).strip()

    # filter courses
    if s == 'all':
        courses = all_courses
    else:
        courses = [c for c in all_courses if c['sem'] == s]

    print(colors.WARNING + f'\nAvailable courses ({len(courses)} in selection):' + colors.ENDC)
    for idx, c in enumerate(courses):
        print(f'[{idx}] [{c["site_tag"]}]: {c["name"]}')

    # confirmation
    c_choice = input(colors.WARNING + '\nChoose number of course to download, (a) for all or (q) to quit: ' + colors.ENDC).strip()
    if c_choice == 'a':
        sem_label = sems[s] if s != 'all' else 'All_Courses'
        for f in courses:
            try:
                target_sem = f"Semester_{f['sem']}" if f['sem'] != 'General' else 'General_Courses'
                downloadCourse(f, target_sem)
                print(colors.WARNING + f'Successfully processed course {f["name"]}!' + colors.ENDC)
            except Exception as e:
                print(f"Error while processing {f['name']}: {e}")
        sys.exit(0)

    if c_choice == 'q':
        print(colors.FAIL + 'Quitting!' + colors.ENDC)
        sys.exit(0)

    try:
        course_idx = int(c_choice)
        if 0 <= course_idx < len(courses):
            selected_course = courses[course_idx]
            target_sem = f"Semester_{selected_course['sem']}" if selected_course['sem'] != 'General' else 'General_Courses'
            downloadCourse(selected_course, target_sem)
            print(colors.WARNING + f'Successfully processed course {selected_course["name"]}!' + colors.ENDC)
        else:
            print(colors.FAIL + 'Invalid course number!' + colors.ENDC)
    except ValueError:
        print(colors.FAIL + 'Invalid choice!' + colors.ENDC)


if __name__ == '__main__':
    main()
