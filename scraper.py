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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

# read config from .env
from src.config import get_config

# Reconfigure console streams on Windows
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

cfg = get_config()
username = cfg.get("user", "")
password = cfg.get("password", "")
root = cfg.get("output_dir", "output")
baseurls = cfg.get("baseurls", ["https://moodle.iitd.ac.in/", "https://moodlenew.iitd.ac.in/"])

sections = itertools.count()
files = itertools.count()

def sanitize_name(name: str) -> str:
    """Sanitizes a single file or directory component without altering drive letters or full paths."""
    cleaned = re.sub(r'[<>:"/\\|?*]', '_', str(name)).strip()
    return cleaned or "unnamed"


def realign_lecture_filename(filename: str, activity_name: str = None) -> str:
    """
    If the activity title indicates a lecture/sequence number that contradicts the
    uploaded filename's number (e.g. activity is "Lecture 6: ...", but file is "Lecture7.pdf"),
    the Moodle activity name represents the professor's syllabus sequence and takes
    precedence to re-align/normalize the filename (e.g. to "Lecture6.pdf").
    """
    if not filename or not activity_name:
        return filename

    act_m = re.search(r'\b(?:lecture|lec|assignment|assign|tutorial|tut|ps|problem\s*set)\s*[-_.:#]?\s*0*(\d+)\b', str(activity_name), re.IGNORECASE)
    file_m = re.search(r'\b(?:lecture|lec|assignment|assign|tutorial|tut|ps|problem\s*set)\s*[-_.:#]?\s*0*(\d+)\b', str(filename), re.IGNORECASE)

    if act_m and file_m:
        try:
            act_num = int(act_m.group(1))
            file_num = int(file_m.group(1))
            if act_num != file_num:
                base, ext = os.path.splitext(filename)
                if not ext:
                    ext = '.pdf'
                # Preserve leading zero padding if the original filename used it (e.g. Lec07 -> Lec06)
                orig_num_str = file_m.group(1)
                num_str = str(act_num)
                if len(orig_num_str) > len(num_str):
                    num_str = num_str.zfill(len(orig_num_str))
                start, end = file_m.span(1)
                new_base = base[:start] + num_str + base[end:]
                return f"{new_base}{ext}"
        except (ValueError, IndexError):
            pass
    return filename


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
    
    # Configure connection pooling and retries for performance and stability
    retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=retries)
    ses.mount('http://', adapter)
    ses.mount('https://', adapter)
    
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


import zipfile
import shutil

def extract_zip(zip_path, extract_dir, on_file_saved=None):
    """Safely extracts a ZIP archive and triggers on_file_saved on all contents."""
    os.makedirs(extract_dir, exist_ok=True)
    extracted_files = []
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for member in zf.infolist():
                member_path = os.path.abspath(os.path.join(extract_dir, member.filename))
                if not member_path.startswith(os.path.abspath(extract_dir)):
                    continue
                if member.is_dir():
                    os.makedirs(member_path, exist_ok=True)
                    continue
                os.makedirs(os.path.dirname(member_path), exist_ok=True)
                with zf.open(member) as source, open(member_path, 'wb') as target:
                    shutil.copyfileobj(source, target)
                extracted_files.append(member_path)
                print('[' + colors.OKGREEN + 'unzip' + colors.ENDC + '] |  |  +--%s' % os.path.relpath(member_path, extract_dir))
                
                # If extracted file is itself a zip, recursively extract it
                if member_path.lower().endswith('.zip'):
                    nested_dir = os.path.splitext(member_path)[0]
                    nested_files = extract_zip(member_path, nested_dir, on_file_saved=on_file_saved)
                    extracted_files.extend(nested_files)
                elif on_file_saved:
                    try:
                        on_file_saved(member_path, is_new=True)
                    except Exception as ex:
                        print(f"Error in on_file_saved for {member_path}: {ex}")
    except Exception as e:
        print('[' + colors.FAIL + 'unzip-error' + colors.ENDC + '] |  |  +--%s (%s)' % (os.path.basename(zip_path), e))
    return extracted_files


def saveFile(session_obj, src, path, name, on_file_saved=None):
    global files
    next(files)
    safe_name = sanitize_name(name)
    dst = os.path.join(path, safe_name)

    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        print('[' + colors.OKBLUE + 'skip' + colors.ENDC + '] |  |  +--%s' % safe_name)
        if on_file_saved:
            try:
                on_file_saved(dst, is_new=False)
            except Exception:
                pass
        if dst.lower().endswith('.zip'):
            extract_dir = os.path.splitext(dst)[0]
            if not os.path.exists(extract_dir) or not os.listdir(extract_dir):
                extract_zip(dst, extract_dir, on_file_saved=on_file_saved)
        return

    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as handle:
            print('[' + colors.OKGREEN + 'save' + colors.ENDC + '] |  |  +--%s' % safe_name)
            r = session_obj.get(src, stream=True, allow_redirects=True)
            for block in r.iter_content(65536):
                if not block:
                    break
                handle.write(block)
        if on_file_saved:
            try:
                on_file_saved(dst, is_new=True)
            except Exception:
                pass
        if dst.lower().endswith('.zip'):
            extract_dir = os.path.splitext(dst)[0]
            extract_zip(dst, extract_dir, on_file_saved=on_file_saved)
    except Exception as e:
        print('[' + colors.FAIL + 'fail' + colors.ENDC + '] |  |  +--%s (%s)' % (safe_name, e))


def saveLink(session_obj, url, path, name, on_file_saved=None):
    global files
    next(files)
    try:
        # Check if the HTML bookmark or target file already exists
        fname = sanitize_name(name) + '.html'
        dst_html = os.path.join(path, fname)

        # 1. Fetch Moodle URL wrapper page to resolve destination
        r = session_obj.get(url, allow_redirects=True)
        target_url = url
        soup = BeautifulSoup(r.text, 'html.parser')
        region = soup.find(class_='region-content') or soup.find(class_='urlworkaround')
        if region and region.find('a'):
            target_url = region.find('a').get('href', url)
        elif r.url and r.url != url:
            target_url = r.url

        # 2. Transform Google Drive / Docs / Cloud storage links to direct download endpoints
        if 'drive.google.com/file/d/' in target_url:
            m = re.search(r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)', target_url)
            if m:
                target_url = f"https://drive.google.com/uc?export=download&id={m.group(1)}"
        elif 'drive.google.com/open?id=' in target_url:
            m = re.search(r'id=([a-zA-Z0-9_-]+)', target_url)
            if m:
                target_url = f"https://drive.google.com/uc?export=download&id={m.group(1)}"
        elif 'docs.google.com/presentation/d/' in target_url:
            m = re.search(r'docs\.google\.com/presentation/d/([a-zA-Z0-9_-]+)', target_url)
            if m:
                target_url = f"https://docs.google.com/presentation/d/{m.group(1)}/export/pptx"
        elif 'docs.google.com/document/d/' in target_url:
            m = re.search(r'docs\.google\.com/document/d/([a-zA-Z0-9_-]+)', target_url)
            if m:
                target_url = f"https://docs.google.com/document/d/{m.group(1)}/export?format=pdf"
        elif 'dropbox.com' in target_url and 'dl=0' in target_url:
            target_url = target_url.replace('dl=0', 'dl=1')

        # 3. Probe target URL with stream=True (headers only)
        res = session_obj.get(target_url, stream=True, allow_redirects=True)
        headers = {k.lower(): v for k, v in res.headers.items()}
        content_type = headers.get('content-type', '').lower()
        
        # Check Content-Disposition for filename
        cd = headers.get('content-disposition', '')
        dl_name = None
        m_cd = re.search(r"filename\*?=(?:UTF-8'')?[\"']?([^\"';\r\n]+)", cd, re.IGNORECASE)
        if m_cd:
            dl_name = m_cd.group(1).strip('\"\' ')

        parsed_target = urllib.parse.urlparse(res.url)
        path_base = os.path.basename(parsed_target.path)
        
        doc_extensions = ('.pdf', '.pptx', '.ppt', '.docx', '.doc', '.zip', '.txt', '.md', '.html', '.htm', '.csv', '.xlsx', '.py', '.c', '.cpp')
        is_direct_doc = (
            dl_name is not None or
            any(parsed_target.path.lower().endswith(ext) for ext in doc_extensions) or
            'application/pdf' in content_type or
            'application/vnd.openxmlformats' in content_type or
            'application/vnd.ms-powerpoint' in content_type or
            'application/zip' in content_type or
            'application/x-zip' in content_type
        )

        if is_direct_doc:
            if not dl_name:
                if path_base and '.' in path_base:
                    dl_name = path_base
                else:
                    ext = '.pdf'
                    if 'presentation' in content_type or 'powerpoint' in content_type:
                        ext = '.pptx'
                    elif 'zip' in content_type:
                        ext = '.zip'
                    elif 'word' in content_type:
                        ext = '.docx'
                    dl_name = f"{name}{ext}"
            dl_name = sanitize_name(urllib.request.url2pathname(dl_name))
            dst_doc = os.path.join(path, dl_name)
            if os.path.exists(dst_doc) and os.path.getsize(dst_doc) > 0:
                res.close()
                print('[' + colors.OKBLUE + 'skip' + colors.ENDC + '] |  |  +--%s' % dl_name)
                if on_file_saved:
                    on_file_saved(dst_doc, is_new=False)
                return
            saveFile(session_obj, res.url, path, dl_name, on_file_saved=on_file_saved)
            return

        # 4. If it is an HTML webpage, check for embedded lecture notes / file downloads
        page_soup = BeautifulSoup(res.text, 'html.parser')
        embedded_docs = []
        for a_tag in page_soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            abs_href = urllib.parse.urljoin(res.url, href)
            p_h = urllib.parse.urlparse(abs_href).path.lower()
            if any(p_h.endswith(ext) for ext in ('.pdf', '.pptx', '.ppt', '.zip', '.docx')):
                embedded_docs.append((abs_href, a_tag.get_text().strip()))

        if embedded_docs:
            print('[' + colors.OKGREEN + 'link-page' + colors.ENDC + f'] |  |  +--Found {len(embedded_docs)} downloadable document(s) on linked page: {name}')
            for doc_url, doc_label in embedded_docs:
                doc_fname = os.path.basename(urllib.parse.urlparse(doc_url).path)
                if not doc_fname:
                    doc_fname = f"{doc_label or 'document'}.pdf"
                saveFile(session_obj, doc_url, path, doc_fname, on_file_saved=on_file_saved)

        # 5. Also save HTML bookmark
        if not os.path.exists(dst_html) or os.path.getsize(dst_html) == 0:
            with open(dst_html, 'w', encoding='utf-8') as handle:
                print('[' + colors.OKGREEN + 'save-link' + colors.ENDC + '] |  |  +--%s' % name)
                handle.write(f'<a href="{target_url}">{name}</a>')
            if on_file_saved:
                try:
                    on_file_saved(dst_html, is_new=True)
                except Exception:
                    pass
        else:
            if on_file_saved:
                on_file_saved(dst_html, is_new=False)

    except Exception as e:
        print('[' + colors.FAIL + 'link-error' + colors.ENDC + '] |  |  +--%s (%s)' % (name, e))


def saveInfo(path, info, tab, on_file_saved=None):
    if "Foren" not in info and info.strip():
        global files
        next(files)
        name = 'info.txt'
        dst = os.path.join(path, name)

        if os.path.exists(dst) and os.path.getsize(dst) > 0:
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


def downloadResource(session_obj, res, path, activity_name=None, course_key=None, known_catalog=None, on_file_saved=None):
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

    # Request headers only with stream=True so large payloads aren't buffered prematurely
    try:
        r = session_obj.get(src, stream=True, allow_redirects=True)
    except Exception as e:
        print('[' + colors.FAIL + 'fail' + colors.ENDC + '] |  |  +--%s (%s)' % (activity_name or src, e))
        return

    if r.status_code == 200:
        headers = {k.lower(): v for k, v in r.headers.items()}
        content_type = headers.get('content-type', '').lower()
        name = None
        
        # Priority 1: Original uploaded filename in Content-Disposition header
        if 'content-disposition' in headers:
            cd = headers['content-disposition']
            m = re.search(r"filename\*?=(?:UTF-8'')?[\"']?([^\"';\r\n]+)", cd, re.IGNORECASE)
            if m:
                name = m.group(1).strip('\"\' ')
        
        # Priority 2: Original uploaded filename in final redirected URL
        if not name:
            parsed = urllib.parse.urlparse(r.url)
            basename = os.path.basename(parsed.path)
            if basename and '.' in basename and not basename.endswith('.php'):
                name = basename
        
        # Check if it's an HTML frame/redirect page
        if not name and 'text/html' in content_type:
            soup = BeautifulSoup(r.text, 'html.parser')
            region = soup.find(class_='region-content') or soup.find(class_='resourcecontent')
            if region and region.find('a'):
                inner_src = region.find('a').get('href')
                if inner_src and inner_src != src:
                    return downloadResource(session_obj, inner_src, path, activity_name=activity_name, course_key=course_key, known_catalog=known_catalog, on_file_saved=on_file_saved)
            frames = soup.find_all('frame')
            if len(frames) > 1 and frames[1].get('src'):
                inner_src = frames[1]['src']
                if inner_src and inner_src != src:
                    return downloadResource(session_obj, inner_src, path, activity_name=activity_name, course_key=course_key, known_catalog=known_catalog, on_file_saved=on_file_saved)

        # Priority 3: Clean activity name with proper detected extension
        if not name:
            ext = '.pdf'
            if 'presentation' in content_type or 'powerpoint' in content_type:
                ext = '.pptx'
            elif 'zip' in content_type:
                ext = '.zip'
            elif 'word' in content_type:
                ext = '.docx'
            elif 'text/plain' in content_type:
                ext = '.txt'
            elif 'text/html' in content_type:
                ext = '.html'

            if activity_name:
                clean_act = sanitize_name(activity_name)
                if not any(clean_act.lower().endswith(e) for e in ('.pdf', '.pptx', '.ppt', '.docx', '.zip', '.txt', '.html')):
                    clean_act += ext
                name = clean_act
            else:
                name = f"resource{ext}"

        # Re-align lecture/sequence number if activity title contradicts uploaded file number
        name = realign_lecture_filename(name, activity_name)
        name = sanitize_name(urllib.request.url2pathname(name))
        dst = os.path.abspath(os.path.join(path, name))

        # Inspect Content-Length response header
        content_length = None
        if 'content-length' in headers:
            try:
                content_length = int(headers['content-length'])
            except (ValueError, TypeError):
                content_length = None

        # Collision Disambiguation on Differing Content Length:
        # If dst exists on disk, but content_length is known and differs from local file,
        # the incoming file is a different file that happens to share the same filename.
        if os.path.exists(dst) and content_length is not None and os.path.getsize(dst) != content_length:
            local_size = os.path.getsize(dst)
            orig_name = name
            
            # Step A: Attempt disambiguation using sanitized activity_name
            base_ext = os.path.splitext(name)[1] or '.pdf'
            if activity_name:
                clean_act = sanitize_name(activity_name)
                if not any(clean_act.lower().endswith(e) for e in ('.pdf', '.pptx', '.ppt', '.docx', '.zip', '.txt', '.html')):
                    clean_act += base_ext
                candidate_dst = os.path.abspath(os.path.join(path, clean_act))
                if candidate_dst != dst:
                    name = clean_act
                    dst = candidate_dst

            # Step B: If still collides or no activity_name, append a clean suffix (_1, _2, etc.)
            if os.path.exists(dst) and (content_length is not None and os.path.getsize(dst) != content_length):
                base_stem, ext = os.path.splitext(name)
                suffix_idx = 1
                while True:
                    candidate_name = f"{base_stem}_{suffix_idx}{ext}"
                    candidate_dst = os.path.abspath(os.path.join(path, candidate_name))
                    if not os.path.exists(candidate_dst) or (content_length is not None and os.path.getsize(candidate_dst) == content_length):
                        name = candidate_name
                        dst = candidate_dst
                        break
                    suffix_idx += 1
            
            print('[' + colors.WARNING + 'collision' + colors.ENDC + '] |  |  +--%s -> %s (local %d B vs remote %d B)' % (orig_name, name, local_size, content_length))

        # Check if already cataloged in list.md or on disk with matching content size
        if known_catalog and (dst in known_catalog.get("paths", set()) or (course_key, name) in known_catalog.get("course_files", set())) \
           and os.path.exists(dst) and os.path.getsize(dst) > 0:
            if content_length is None or os.path.getsize(dst) == content_length:
                r.close()
                print('[' + colors.OKBLUE + 'skip' + colors.ENDC + '] |  |  +--%s' % name)
                if on_file_saved:
                    try:
                        on_file_saved(dst, is_new=False)
                    except Exception:
                        pass
                return

        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            if content_length is None or os.path.getsize(dst) == content_length:
                r.close()
                print('[' + colors.OKBLUE + 'skip' + colors.ENDC + '] |  |  +--%s' % name)
                if on_file_saved:
                    try:
                        on_file_saved(dst, is_new=False)
                    except Exception:
                        pass
                if dst.lower().endswith('.zip'):
                    extract_dir = os.path.splitext(dst)[0]
                    if not os.path.exists(extract_dir) or not os.listdir(extract_dir):
                        extract_zip(dst, extract_dir, on_file_saved=on_file_saved)
                return

        # It's a new or disambiguated file - stream blocks directly to file
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as handle:
                print('[' + colors.OKGREEN + 'save' + colors.ENDC + '] |  |  +--%s' % name)
                for block in r.iter_content(65536):
                    if not block:
                        break
                    handle.write(block)
            if on_file_saved:
                try:
                    on_file_saved(dst, is_new=True)
                except Exception:
                    pass
            if dst.lower().endswith('.zip'):
                extract_dir = os.path.splitext(dst)[0]
                extract_zip(dst, extract_dir, on_file_saved=on_file_saved)
        except Exception as e:
            print('[' + colors.FAIL + 'fail' + colors.ENDC + '] |  |  +--%s (%s)' % (name, e))
    else:
        print('ERROR: ' + str(r.status_code) + ' ' + str(r.reason))


def downloadFolder(session_obj, folder_url, path, course_key=None, known_catalog=None, on_file_saved=None):
    """Downloads all files inside a Moodle folder activity (/mod/folder/view.php) preserving uploaded file names."""
    r = session_obj.get(folder_url)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # 1. Parse individual files inside folder view (preserves exact uploaded filenames)
        pluginfile_links = soup.find_all('a', href=lambda h: h and '/pluginfile.php/' in h)
        if pluginfile_links:
            for a in pluginfile_links:
                a_copy = BeautifulSoup(str(a), 'html.parser')
                for hide in a_copy.find_all(class_='accesshide'):
                    hide.decompose()
                clean_f_text = a_copy.get_text().strip()
                downloadResource(session_obj, a.get('href'), path, activity_name=clean_f_text, course_key=course_key, known_catalog=known_catalog, on_file_saved=on_file_saved)
            return

        # 2. Check for download folder button as fallback
        btn = soup.find('form', action=lambda a: a and 'download_folder.php' in a)
        if btn:
            action = btn.get('action')
            inputs = {i.get('name'): i.get('value') for i in btn.find_all('input') if i.get('name')}
            resp = session_obj.post(action, data=inputs)
            if resp.status_code == 200:
                name = 'folder.zip'
                cd = resp.headers.get('content-disposition', '')
                m = re.search(r"filename\*?=(?:UTF-8'')?[\"']?([^\"';\r\n]+)", cd, re.IGNORECASE)
                if m:
                    name = m.group(1).strip('\"\' ')
                saveFile(session_obj, resp.url, path, name, on_file_saved=on_file_saved)
                return


def downloadAssignment(session_obj, assign_url, path, activity_name=None, course_key=None, known_catalog=None, on_file_saved=None):
    """
    Downloads instructor question attachments from Moodle Assignment activities (/mod/assign/view.php).
    Strictly ignores student submission files (e.g. assignsubmission_file).
    """
    try:
        r = session_obj.get(assign_url, timeout=15)
        if r.status_code != 200:
            return
        
        soup = BeautifulSoup(r.text, 'html.parser')
        found_links = []
        
        # 1. Target instructor intro/attachment containers
        intro_containers = (
            soup.find_all(id='intro')
            + soup.find_all(class_='introattachment')
            + soup.find_all(class_='activity-description')
            + soup.find_all(attrs={'data-region': 'activity-information'})
        )
        
        for container in intro_containers:
            for a in container.find_all('a', href=True):
                href = urllib.parse.urljoin(assign_url, a['href'].strip())
                # Safety constraint: Do NOT download student submission files
                if 'assignsubmission_' in href:
                    continue
                if '/pluginfile.php/' in href or 'introattachment' in href:
                    if not any(href == item[0] for item in found_links):
                        found_links.append((href, a))
        
        # 2. Also search page-wide for explicit introattachment links
        for a in soup.find_all('a', href=lambda h: h and 'mod_assign/introattachment/' in h):
            href = urllib.parse.urljoin(assign_url, a['href'].strip())
            if 'assignsubmission_' in href:
                continue
            if not any(href == item[0] for item in found_links):
                found_links.append((href, a))

        # 3. Fallback: Check for direct document links within intro containers
        if not found_links:
            for container in intro_containers:
                for a in container.find_all('a', href=True):
                    href = urllib.parse.urljoin(assign_url, a['href'].strip())
                    if 'assignsubmission_' in href:
                        continue
                    if any(href.lower().split('?')[0].endswith(ext) for ext in ('.pdf', '.docx', '.pptx', '.ppt', '.zip', '.txt', '.xlsx')):
                        if not any(href == item[0] for item in found_links):
                            found_links.append((href, a))
        
        # Download each instructor attachment
        for href, a_tag in found_links:
            a_copy = BeautifulSoup(str(a_tag), 'html.parser')
            for hide in a_copy.find_all(class_='accesshide'):
                hide.decompose()
            link_text = a_copy.get_text().strip()
            
            # Use link text if informative; otherwise fall back to activity name
            effective_act = link_text if (link_text and not link_text.lower().endswith(('.php', '.html'))) else activity_name
            downloadResource(
                session_obj,
                href,
                path,
                activity_name=effective_act,
                course_key=course_key,
                known_catalog=known_catalog,
                on_file_saved=on_file_saved
            )
    except Exception as e:
        print('[' + colors.FAIL + 'fail' + colors.ENDC + '] |  |  +--%s (%s)' % (activity_name or assign_url, e))


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


def downloadSection(session_obj, s, path, course_key=None, known_catalog=None, on_file_saved=None):
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
        name = sanitize_name(raw_name)
        secpath = os.path.join(path, name)
        if not os.path.exists(secpath):
            os.makedirs(secpath, exist_ok=True)
        print('       |  +--' + colors.BOLD + name + colors.ENDC)
    if info:
        saveInfo(secpath, info, '|  ', on_file_saved=on_file_saved)
        
    if summary_tag:
        for a_tag in summary_tag.find_all('a', href=True):
            href = a_tag['href'].strip()
            link_name = a_tag.get_text().strip() or 'inline_link'
            if '/mod/resource/' in href:
                downloadResource(session_obj, href, secpath, activity_name=link_name, course_key=course_key, known_catalog=known_catalog, on_file_saved=on_file_saved)
            elif '/mod/folder/' in href:
                f_name = sanitize_name(link_name)
                f_path = os.path.join(secpath, f_name)
                os.makedirs(f_path, exist_ok=True)
                downloadFolder(session_obj, href, f_path + '/', course_key=course_key, known_catalog=known_catalog, on_file_saved=on_file_saved)
            elif '/mod/assign/' in href:
                downloadAssignment(session_obj, href, secpath, activity_name=link_name, course_key=course_key, known_catalog=known_catalog, on_file_saved=on_file_saved)
            elif '/mod/url/' in href or href.startswith('http'):
                saveLink(session_obj, href, secpath, link_name, on_file_saved=on_file_saved)

    # Activities: resources, folders, assignments, urls
    activities = s.find_all('li', class_=lambda c: c and 'activity' in c) or s.find_all(class_=lambda c: c and 'activity-item' in c)
    for act in activities:
        classes = act.get('class', [])
        link_tag = act.find('a')
        if not link_tag:
            continue
        href = link_tag.get('href', '')
        
        # Clean activity name (remove accesshide / accessibility labels)
        inst = act.find(class_='instancename') or act.find(class_='activityname')
        act_name = ''
        if inst:
            inst_copy = BeautifulSoup(str(inst), 'html.parser')
            for hide in inst_copy.find_all(class_='accesshide'):
                hide.decompose()
            act_name = inst_copy.get_text().strip()
        
        if any('resource' in c for c in classes) or '/mod/resource/' in href:
            downloadResource(session_obj, href, secpath, activity_name=act_name, course_key=course_key, known_catalog=known_catalog, on_file_saved=on_file_saved)
        elif any('folder' in c for c in classes) or '/mod/folder/' in href:
            f_name = sanitize_name(act_name) if act_name else 'Folder'
            f_path = os.path.join(secpath, f_name)
            os.makedirs(f_path, exist_ok=True)
            downloadFolder(session_obj, href, f_path + '/', course_key=course_key, known_catalog=known_catalog, on_file_saved=on_file_saved)
        elif any('assign' in c for c in classes) or '/mod/assign/' in href:
            downloadAssignment(session_obj, href, secpath, activity_name=act_name, course_key=course_key, known_catalog=known_catalog, on_file_saved=on_file_saved)
        elif any('url' in c for c in classes) or '/mod/url/' in href:
            url_name = act_name if act_name else 'link'
            saveLink(session_obj, href, secpath, url_name, on_file_saved=on_file_saved)

    # Generalbox foldertree
    folders = s.find_all(class_='box generalbox foldertree')
    for f in folders:
        res = f.find_all(class_='fp-filename-icon')
        if res:
            label = res.pop(0).text
            sub_label = sanitize_name(urllib.request.url2pathname(label))
            subpath = os.path.join(secpath, sub_label)
            if not os.path.exists(subpath):
                os.makedirs(subpath, exist_ok=True)
            print('       |  +--' + colors.BOLD + sub_label + colors.ENDC)
            for r in res:
                downloadResource(session_obj, r, subpath + '/', course_key=course_key, known_catalog=known_catalog, on_file_saved=on_file_saved)

    # Remove directory if empty
    if os.path.exists(secpath) and not os.listdir(secpath):
        try:
            os.rmdir(secpath)
        except OSError:
            pass


def downloadCourse(course_item, sem_label, known_catalog=None, on_file_saved=None):
    session_obj = course_item['session']
    global files
    global sections
    files = itertools.count()
    sections = itertools.count()
    safe_name = sanitize_name(course_item['key'])
    safe_sem = sanitize_name(str(sem_label))
    course_dir = os.path.join(root, safe_sem, safe_name)
    if not os.path.exists(course_dir):
        os.makedirs(course_dir, exist_ok=True)
    print('       +--' + colors.BOLD + safe_name + colors.ENDC)
    r = session_obj.get(course_item['url'])
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        dump_dir = os.path.join(course_dir, '.dump')
        if not os.path.exists(dump_dir):
            os.makedirs(dump_dir, exist_ok=True)

        dump_fname = sanitize_name(f"{course_item['key']}-{course_item.get('type', 'Course')}-{datetime.date.today()}-full") + ".html"
        dst = os.path.join(dump_dir, dump_fname)

        with open(dst, 'w', encoding='utf-8') as f:
            f.write(str(soup))
            
        sec_elements = soup.find_all('li', class_=lambda c: c and 'section' in c)
        if not sec_elements:
            sec_elements = soup.find_all(class_=lambda c: c and ('course-section' in c or 'section main' in c))
        
        for s in sec_elements:
            downloadSection(session_obj, s, course_dir, course_key=course_item['key'], known_catalog=known_catalog, on_file_saved=on_file_saved)

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

    cfg = get_config()
    uname = cfg.get("user", "")
    pwd = cfg.get("password", "")
    b_urls = cfg.get("baseurls", baseurls)
    if not uname or not pwd or uname == "your_kerberos_id_here":
        print(colors.FAIL + "Error: Kerberos credentials not found in '.env'." + colors.ENDC)
        print("Please run setup first to configure your credentials:")
        print("  python agent_tools.py /setup\n")
        sys.exit(1)

    # logging into all configured Moodle sites
    sessions_by_url = {}
    print(f"Logging into {len(b_urls)} Moodle site(s)...")
    for b_url in b_urls:
        print(f"  --> Connecting to {b_url} ...")
        ses = login(b_url, uname, pwd)
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
