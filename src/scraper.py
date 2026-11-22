#!/usr/bin/env python3
import os
import sys
import re
import urllib.request
import urllib.parse
import concurrent.futures
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from requests import session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

# read config from .env
from src.config import get_config
from src.parser import DocumentParser, compute_file_hash
from src.indexer import KnowledgeIndexer
from src.list_manager import ListManager
from src.custom_scraper import CustomUrlManager, scrape_custom_source

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


class _ColorsMeta(type):
    """Dynamic ANSI color dispatcher: full colors for human terminal, stripped for MCP / pipes."""
    @property
    def HEADER(cls): return '\033[95m' if cls._is_enabled() else ''
    @property
    def OKBLUE(cls): return '\033[94m' if cls._is_enabled() else ''
    @property
    def OKGREEN(cls): return '\033[92m' if cls._is_enabled() else ''
    @property
    def WARNING(cls): return '\033[93m' if cls._is_enabled() else ''
    @property
    def FAIL(cls): return '\033[91m' if cls._is_enabled() else ''
    @property
    def ENDC(cls): return '\033[0m' if cls._is_enabled() else ''
    @property
    def BOLD(cls): return '\033[1m' if cls._is_enabled() else ''

    def _is_enabled(cls):
        if os.environ.get("MCP_MODE") == "1" or os.environ.get("NO_COLOR"):
            return False
        return sys.stdout.isatty()


class colors(metaclass=_ColorsMeta):
    pass


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
    
    form = soup.find('form', id='login') or soup.find('form')
    if form:
        for inp in form.find_all('input'):
            name = inp.get('name')
            if name and name not in authdata:
                authdata[name] = inp.get('value', '')
        
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

    def _record_course(cid, fullname, shortname="", viewurl=None):
        cid = str(cid).strip()
        if not cid:
            return
        c_unique_key = f"{site_tag}_{cid}"
        if c_unique_key in courses_dict:
            return
        key = shortname or (fullname.split()[0] if fullname else f'Course_{cid}')
        sem = 'General'
        m = re.match(r'^(\d{4})[-_]', key) or re.match(r'^(\d{4})[-_]', fullname)
        if m:
            sem = m.group(1)
        disp = f"{key}: {fullname}" if shortname and shortname != fullname else (fullname or key)
        courses_dict[c_unique_key] = {
            'url': viewurl or f'{baseurl}course/view.php?id={cid}',
            'name': disp,
            'key': key,
            'sem': sem,
            'type': 'Course',
            'baseurl': baseurl,
            'session': ses,
            'site_tag': site_tag
        }

    # 1. Try Moodle 4.x AJAX WebService
    try:
        my_page = ses.get(baseurl + 'my/', timeout=10)
        sesskey_m = re.search(r'\"sesskey\":\s*\"([^\"]+)\"', my_page.text) or re.search(r'sesskey=([a-zA-Z0-9]+)', my_page.text)
        if sesskey_m:
            ajax_url = f'{baseurl}lib/ajax/service.php?sesskey={sesskey_m.group(1)}&info=core_course_get_enrolled_courses_by_timeline_classification'
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
                    for c in data[0].get('data', {}).get('courses', []):
                        _record_course(c.get('id'), c.get('fullname', ''), c.get('shortname', ''), c.get('viewurl'))
    except Exception:
        pass

    # 2. Try User Profile page (/user/profile.php)
    if not courses_dict:
        try:
            prof_resp = ses.get(baseurl + 'user/profile.php', timeout=10)
            if prof_resp.status_code == 200:
                psoup = BeautifulSoup(prof_resp.text, 'html.parser')
                for a in psoup.find_all('a', href=lambda h: h and ('course=' in h or '/course/view.php?id=' in h)):
                    text = a.get_text().strip()
                    if not text or text.lower() in ('view course', 'course', 'edit profile'):
                        continue
                    m = re.search(r'(?:course=|id=)(\d+)', a.get('href', ''))
                    if m:
                        _record_course(m.group(1), text)
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
                        text = a.get_text().strip()
                        if not text or text.lower() in ('view course', 'course'):
                            continue
                        m = re.search(r'id=(\d+)', a.get('href', ''))
                        if m:
                            _record_course(m.group(1), text, viewurl=a.get('href'))
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


def _stream_to_file(r, dst, on_file_saved=None):
    """Unified helper: streams HTTP response chunks directly to dst and triggers optional callbacks/unzipping."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'wb') as handle:
        for block in r.iter_content(65536):
            if block:
                handle.write(block)
    if on_file_saved:
        try:
            on_file_saved(dst, is_new=True)
        except Exception:
            pass
    if dst.lower().endswith('.zip'):
        extract_dir = os.path.splitext(dst)[0]
        extract_zip(dst, extract_dir, on_file_saved=on_file_saved)


def _skip_existing_file(dst, on_file_saved=None):
    """Handles skipped files by triggering callbacks and ensuring zips are extracted."""
    if on_file_saved:
        try:
            on_file_saved(dst, is_new=False)
        except Exception:
            pass
    if dst.lower().endswith('.zip'):
        extract_dir = os.path.splitext(dst)[0]
        if not os.path.exists(extract_dir) or not os.listdir(extract_dir):
            extract_zip(dst, extract_dir, on_file_saved=on_file_saved)


def saveFile(session_obj, src, path, name, on_file_saved=None):
    safe_name = sanitize_name(name)
    dst = os.path.join(path, safe_name)

    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        print('[' + colors.OKBLUE + 'skip' + colors.ENDC + '] |  |  +--%s' % safe_name)
        _skip_existing_file(dst, on_file_saved=on_file_saved)
        return

    try:
        print('[' + colors.OKGREEN + 'save' + colors.ENDC + '] |  |  +--%s' % safe_name)
        r = session_obj.get(src, stream=True, allow_redirects=True)
        _stream_to_file(r, dst, on_file_saved=on_file_saved)
    except Exception as e:
        print('[' + colors.FAIL + 'fail' + colors.ENDC + '] |  |  +--%s (%s)' % (safe_name, e))


def saveLink(session_obj, url, path, name, on_file_saved=None):
    try:
        fname = sanitize_name(name) + '.html'
        dst_html = os.path.join(path, fname)

        r = session_obj.get(url, allow_redirects=True)
        target_url = r.url if r.url else url
        soup = BeautifulSoup(r.text, 'html.parser')
        region = soup.find(class_='region-content') or soup.find(class_='urlworkaround')
        if region and region.find('a'):
            target_url = region.find('a').get('href', target_url)

        # Check if direct document
        doc_exts = ('.pdf', '.pptx', '.ppt', '.docx', '.zip')
        if any(urllib.parse.urlparse(target_url).path.lower().endswith(ext) for ext in doc_exts):
            dl_name = sanitize_name(os.path.basename(urllib.parse.urlparse(target_url).path))
            saveFile(session_obj, target_url, path, dl_name, on_file_saved=on_file_saved)
            return

        # Save HTML bookmark
        if not os.path.exists(dst_html) or os.path.getsize(dst_html) == 0:
            with open(dst_html, 'w', encoding='utf-8') as handle:
                print('[' + colors.OKGREEN + 'save-link' + colors.ENDC + '] |  |  +--%s' % name)
                handle.write(f'<a href="{target_url}">{name}</a>')
            if on_file_saved:
                on_file_saved(dst_html, is_new=True)
        elif on_file_saved:
            on_file_saved(dst_html, is_new=False)
    except Exception as e:
        print('[' + colors.FAIL + 'link-error' + colors.ENDC + '] |  |  +--%s (%s)' % (name, e))


def saveInfo(path, info, tab, on_file_saved=None):
    if info and info.strip():
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

        name = realign_lecture_filename(name, activity_name)
        name = sanitize_name(urllib.request.url2pathname(name))
        dst = os.path.abspath(os.path.join(path, name))

        # Collision Disambiguation on Differing Content Length
        content_length = None
        if 'content-length' in headers:
            try:
                content_length = int(headers['content-length'])
            except (ValueError, TypeError):
                content_length = None

        if os.path.exists(dst) and content_length is not None and os.path.getsize(dst) != content_length:
            local_size = os.path.getsize(dst)
            orig_name = name
            base_ext = os.path.splitext(name)[1] or '.pdf'
            if activity_name:
                clean_act = sanitize_name(activity_name)
                if not any(clean_act.lower().endswith(e) for e in ('.pdf', '.pptx', '.ppt', '.docx', '.zip', '.txt', '.html')):
                    clean_act += base_ext
                candidate_dst = os.path.abspath(os.path.join(path, clean_act))
                if candidate_dst != dst:
                    name, dst = clean_act, candidate_dst

            if os.path.exists(dst) and (content_length is not None and os.path.getsize(dst) != content_length):
                base_stem, ext = os.path.splitext(name)
                suffix_idx = 1
                while True:
                    candidate_name = f"{base_stem}_{suffix_idx}{ext}"
                    candidate_dst = os.path.abspath(os.path.join(path, candidate_name))
                    if not os.path.exists(candidate_dst) or os.path.getsize(candidate_dst) == content_length:
                        name, dst = candidate_name, candidate_dst
                        break
                    suffix_idx += 1
            print('[' + colors.WARNING + 'collision' + colors.ENDC + '] |  |  +--%s -> %s (local %d B vs remote %d B)' % (orig_name, name, local_size, content_length))

        # Check if already cataloged in list.md or on disk with matching content size
        is_cataloged = bool(known_catalog and (dst in known_catalog.get("paths", set()) or (course_key, name) in known_catalog.get("course_files", set())))
        if (is_cataloged or os.path.exists(dst)) and os.path.getsize(dst) > 0:
            if content_length is None or os.path.getsize(dst) == content_length:
                r.close()
                print('[' + colors.OKBLUE + 'skip' + colors.ENDC + '] |  |  +--%s' % name)
                _skip_existing_file(dst, on_file_saved=on_file_saved)
                return

        # It's a new or disambiguated file - stream blocks directly to file
        try:
            print('[' + colors.OKGREEN + 'save' + colors.ENDC + '] |  |  +--%s' % name)
            _stream_to_file(r, dst, on_file_saved=on_file_saved)
        except Exception as e:
            print('[' + colors.FAIL + 'fail' + colors.ENDC + '] |  |  +--%s (%s)' % (name, e))
    else:
        print('ERROR: ' + str(r.status_code) + ' ' + str(r.reason))


def downloadFolder(session_obj, folder_url, path, course_key=None, known_catalog=None, on_file_saved=None):
    """Downloads all files inside a Moodle folder activity (/mod/folder/view.php) preserving uploaded file names."""
    r = session_obj.get(folder_url)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        pluginfile_links = soup.find_all('a', href=lambda h: h and '/pluginfile.php/' in h)
        if pluginfile_links:
            for a in pluginfile_links:
                a_copy = BeautifulSoup(str(a), 'html.parser')
                for hide in a_copy.find_all(class_='accesshide'):
                    hide.decompose()
                clean_f_text = a_copy.get_text().strip()
                downloadResource(session_obj, a.get('href'), path, activity_name=clean_f_text, course_key=course_key, known_catalog=known_catalog, on_file_saved=on_file_saved)
            return

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
                if 'assignsubmission_' in href:
                    continue
                if '/pluginfile.php/' in href or 'introattachment' in href:
                    if not any(href == item[0] for item in found_links):
                        found_links.append((href, a))
        
        # 2. Page-wide introattachment links
        for a in soup.find_all('a', href=lambda h: h and 'mod_assign/introattachment/' in h):
            href = urllib.parse.urljoin(assign_url, a['href'].strip())
            if 'assignsubmission_' in href:
                continue
            if not any(href == item[0] for item in found_links):
                found_links.append((href, a))

        # 3. Fallback: direct document links
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
    
    # Generic "Topic 1", "Section 1", "Unit 1"
    if re.match(r'^(?:Topic|Section|Unit)\s*[-_]?\s*\d+$', clean, re.IGNORECASE):
        return True
        
    months = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    if re.search(rf'\b\d{{1,2}}\s+{months}\s*[-–—]\s*\d{{1,2}}\s+{months}', clean, re.IGNORECASE):
        return True
    if re.search(rf'\b{months}\s+\d{{1,2}}\s*[-–—]\s*(?:{months}\s+)?\d{{1,2}}', clean, re.IGNORECASE):
        return True
    return bool(re.search(r'\b\d{1,2}[./]\d{1,2}\s*[-–—]\s*\d{1,2}[./]\d{1,2}', clean))


def downloadSection(session_obj, s, path, course_key=None, known_catalog=None, on_file_saved=None):
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

    # Check if section is a date range or generic section
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
    safe_name = sanitize_name(course_item['key'])
    safe_sem = sanitize_name(str(sem_label))
    course_dir = os.path.join(root, safe_sem, safe_name)
    if not os.path.exists(course_dir):
        os.makedirs(course_dir, exist_ok=True)
    print('       +--' + colors.BOLD + safe_name + colors.ENDC)
    r = session_obj.get(course_item['url'])
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        sec_elements = soup.find_all('li', class_=lambda c: c and 'section' in c)
        if not sec_elements:
            sec_elements = soup.find_all(class_=lambda c: c and ('course-section' in c or 'section main' in c))
        
        for s in sec_elements:
            downloadSection(session_obj, s, course_dir, course_key=course_item['key'], known_catalog=known_catalog, on_file_saved=on_file_saved)

        # Remove any empty subdirectories left behind
        for root_d, dirs, _ in os.walk(course_dir, topdown=False):
            for d in dirs:
                full_d = os.path.join(root_d, d)
                try:
                    if not os.listdir(full_d):
                        os.rmdir(full_d)
                except OSError:
                    pass
    else:
        print('ERROR: ' + str(r.status_code) + ' ' + str(r.reason))


# =====================================================================
# Streaming Synchronizer & Multi-Source Orchestrator
# =====================================================================

def get_moodle_sessions():
    config = get_config()
    user = config["user"]
    password = config["password"]
    base_urls = config["baseurls"]

    if not user or not password or user == "your_kerberos_id_here":
        return None, "Missing Kerberos credentials in .env. Please run /setup first."

    sessions_by_url = {}
    for b_url in base_urls:
        ses = login(b_url, user, password)
        if ses:
            sessions_by_url[b_url] = ses

    if not sessions_by_url:
        return None, "Could not authenticate with any Moodle instance. Please check your credentials in .env."

    return sessions_by_url, None


def discover_available_semesters() -> Dict[str, Any]:
    """Connects to Moodle and discovers all enrolled semesters and courses without downloading."""
    sessions_by_url, err = get_moodle_sessions()
    if err:
        return {"status": "error", "message": err}

    all_courses, sems = getAllCoursesAndSemesters(sessions_by_url)
    if not all_courses:
        return {"status": "error", "message": "No courses found."}

    sem_info = {}
    for s_key, s_label in sems.items():
        count = len(all_courses) if s_key == "all" else len([c for c in all_courses if c["sem"] == s_key])
        sem_info[s_key] = {"label": s_label, "course_count": count}

    return {"status": "success", "total_courses": len(all_courses), "semesters": sem_info}


def sync_custom_sources(known_catalog: Optional[Dict[str, Any]] = None, on_file_saved_callback=None, max_workers: int = 4) -> Dict[str, Any]:
    """Syncs registered custom URLs from data/custom_urls.json."""
    config = get_config()
    url_mgr = CustomUrlManager(config["workspace_dir"])
    sources = url_mgr.get_sources()
    if not sources:
        return {"status": "empty", "message": "No custom URLs registered.", "sources_count": 0, "files_downloaded": 0}

    print(f"\n[Custom URL Sync] Syncing {len(sources)} registered source(s)...")
    results = []
    total_dl = 0
    for s in sources:
        res = scrape_custom_source(s, Path(config["output_dir"]), known_catalog=known_catalog, on_file_saved=on_file_saved_callback)
        count = res.get("downloaded_files_count", 0)
        total_dl += count
        url_mgr.update_sync_stats(s["url"], count)
        results.append(res)

    return {"status": "success", "sources_synced": len(sources), "files_downloaded": total_dl, "details": results}


def sync_user_files(known_catalog: Optional[Dict[str, Any]] = None, on_file_saved_callback=None) -> Dict[str, Any]:
    """Scans local user_files/ for personal study materials and dispatches them for indexing."""
    user_files_dir = Path(get_config()["user_files_dir"])
    if not user_files_dir.exists():
        user_files_dir.mkdir(parents=True, exist_ok=True)
        return {"status": "empty", "files_found": 0, "message": "user_files/ folder is empty."}

    supported = {".pdf", ".pptx", ".ppt", ".docx", ".zip", ".txt", ".md", ".html", ".htm"}
    files_to_sync = []
    for root_dir, _, file_list in os.walk(user_files_dir):
        if ".dump" in root_dir:
            continue
        for f in sorted(file_list):
            if not f.startswith(".") and f.lower() not in ("readme.md", ".gitkeep") and Path(f).suffix.lower() in supported:
                files_to_sync.append(Path(root_dir) / f)

    if not files_to_sync:
        return {"status": "empty", "files_found": 0, "message": "No documents found in user_files/."}

    print(f"\n[User Files Sync] Discovered {len(files_to_sync)} document(s) in user_files/...")
    dispatched = 0
    for f_path in files_to_sync:
        abs_str = str(f_path.resolve())
        is_new = not (known_catalog and abs_str in known_catalog.get("paths", set()))
        if on_file_saved_callback:
            on_file_saved_callback(abs_str, is_new=is_new)
            dispatched += 1

    return {"status": "success", "files_found": len(files_to_sync), "files_dispatched": dispatched}


def sync_moodle_courses(
    semester_filter: Optional[str] = None,
    course_filter: Optional[str] = None,
    quick_check: bool = False,
    course_index: Optional[str] = None,
    max_workers: int = 4,
    sync_custom: bool = True
) -> Dict[str, Any]:
    """
    Streaming async sync pipeline: downloads new Moodle/custom files and indexes them on the fly.
    """
    config = get_config()
    output_dir = Path(config["output_dir"])
    user_files_dir = Path(config["user_files_dir"])
    parsed_dir = config["parsed_dir"]
    chroma_dir = config["chroma_dir"]
    workspace_dir = config["workspace_dir"]

    parser = DocumentParser(str(output_dir), parsed_dir, user_files_dir=str(user_files_dir))
    indexer = KnowledgeIndexer(chroma_dir)
    list_mgr = ListManager(workspace_dir, str(output_dir), parsed_dir, user_files_dir=str(user_files_dir))

    known_catalog = list_mgr.get_known_files_from_list()
    if known_catalog["total_files"] > 0:
        print(f"[Sync] [INFO] Inspected list.md: Found {known_catalog['total_files']} files already indexed across courses.")

    lock = threading.Lock()
    processed_files = set()
    indexed_chunks_total = 0
    futures = []
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def async_process_file(file_path_str: str, is_new: bool):
        nonlocal indexed_chunks_total
        p = Path(file_path_str)
        if not p.exists() or p.is_dir() or p.name.startswith("."):
            return

        with lock:
            if file_path_str in processed_files:
                return
            processed_files.add(file_path_str)

        # Do NOT rely solely on known_catalog["paths"] early-return, which erroneously skips
        # files previously cataloged as "[WAIT] Pending Parse" on subsequent sync runs.
        # Instead, verify if parsed markdown already exists with a matching content hash:
        if user_files_dir and (p == user_files_dir or user_files_dir in p.parents):
            sub_rel = p.relative_to(user_files_dir)
            rel_path = Path("User_Files") / sub_rel
        else:
            try:
                rel_path = p.relative_to(output_dir)
            except ValueError:
                rel_path = Path(p.name)

        md_dest = Path(parsed_dir) / rel_path.with_suffix('.md')
        cached_hash = parser.hashes.get(str(rel_path))
        from src.parser import compute_file_hash
        try:
            curr_hash = compute_file_hash(p)
        except Exception:
            curr_hash = None

        if not is_new and cached_hash == curr_hash and md_dest.exists():
            return

        ext = p.suffix.lower()
        if ext in (".pdf", ".txt", ".md", ".html", ".htm", ".pptx", ".ppt", ".docx", ".zip"):
            try:
                chunks = parser.parse_file(p, force=False)
                if chunks:
                    with lock:
                        count = indexer.index_parsed_chunks(chunks)
                        indexed_chunks_total += count
                    print(f"  [Async RAG] Converted & Indexed: {p.name} ({len(chunks)} pages, {count} chunks)")
            except Exception as ex:
                print(f"  [Async RAG Error] {p.name}: {ex}")

    def on_file_saved_callback(saved_path: str, is_new: bool = True):
        future = executor.submit(async_process_file, saved_path, is_new)
        futures.append(future)

    if semester_filter and semester_filter.lower() in ("user", "user_files", "local"):
        user_res = sync_user_files(known_catalog=known_catalog, on_file_saved_callback=on_file_saved_callback)
        concurrent.futures.wait(futures)
        executor.shutdown(wait=True)
        list_mgr.update_list_file()
        return {"status": "success", "type": "user_files_only", "files_found": user_res.get("files_found", 0), "files_processed": len(processed_files), "total_chunks_indexed": indexed_chunks_total, "list_file": str(list_mgr.list_file_path)}

    if semester_filter and semester_filter.lower() == "custom":
        custom_res = sync_custom_sources(known_catalog=known_catalog, on_file_saved_callback=on_file_saved_callback, max_workers=max_workers)
        concurrent.futures.wait(futures)
        executor.shutdown(wait=True)
        list_mgr.update_list_file()
        return {"status": "success", "type": "custom_only", "sources_synced": custom_res.get("sources_synced", 0), "files_processed": len(processed_files), "total_chunks_indexed": indexed_chunks_total, "list_file": str(list_mgr.list_file_path)}

    sessions_by_url, err = get_moodle_sessions()
    moodle_courses_synced = 0

    if not err:
        all_courses, sems = getAllCoursesAndSemesters(sessions_by_url)
        if all_courses:
            if not semester_filter:
                semester_filter = config.get("tracked_semester", "2601")

            if semester_filter == "all":
                target_courses = all_courses
            elif semester_filter in sems:
                target_courses = [c for c in all_courses if c["sem"] == semester_filter]
            else:
                matched = [c for c in all_courses if semester_filter in str(c.get("sem", ""))]
                target_courses = matched if matched else all_courses

            if course_filter:
                cf_clean = course_filter.lower().strip()
                matched_cf = [c for c in target_courses if cf_clean in c.get("key", "").lower() or cf_clean in c.get("name", "").lower()]
                if not matched_cf:
                    matched_cf = [c for c in all_courses if cf_clean in c.get("key", "").lower() or cf_clean in c.get("name", "").lower()]
                if matched_cf:
                    target_courses = matched_cf
                else:
                    return {"status": "course_not_found", "message": f"No enrolled Moodle course matched '{course_filter}'."}

            if course_index is not None:
                try:
                    idx = int(course_index)
                    if 0 <= idx < len(target_courses):
                        target_courses = [target_courses[idx]]
                except ValueError:
                    pass

            if quick_check:
                all_up_to_date = True
                for course_item in target_courses:
                    session_obj = course_item.get("session")
                    if not session_obj:
                        all_up_to_date = False
                        continue
                    try:
                        resp = session_obj.get(course_item["url"], timeout=10)
                        if resp.status_code == 200:
                            soup = BeautifulSoup(resp.text, "html.parser")
                            found_links = soup.find_all("a", href=lambda h: h and ("/mod/resource/" in h or "/mod/folder/" in h or "/mod/assign/" in h))
                            c_key = course_item["key"]
                            known_c_files = {fname.lower() for (ck, fname) in known_catalog.get("course_files", set()) if ck.lower() == c_key.lower()}
                            for a in found_links:
                                clean_lbl = re.sub(r"\s+", " ", a.get_text().strip()).lower()
                                if clean_lbl and not any(clean_lbl in kf or kf.startswith(clean_lbl) for kf in known_c_files):
                                    all_up_to_date = False
                                    break
                        else:
                            all_up_to_date = False
                    except Exception:
                        all_up_to_date = False

                if all_up_to_date and len(target_courses) > 0:
                    checked_keys = [c["key"] for c in target_courses]
                    return {"status": "up_to_date", "quick_check": True, "courses_checked": checked_keys, "new_files": 0, "message": f"Course(s) {', '.join(checked_keys)} are fully up to date."}

            print(f"\n[Sync] [START] Starting sync for {len(target_courses)} course(s) (Semester: {semester_filter})...")
            for course_item in target_courses:
                sem_label = f"Semester_{course_item['sem']}" if course_item.get("sem") else "General"
                downloadCourse(course_item, sem_label, known_catalog=known_catalog, on_file_saved=on_file_saved_callback)
            moodle_courses_synced = len(target_courses)
    else:
        print(f"[Sync Notice] Moodle credentials not configured or failed ({err}). Proceeding with custom sources if any.")

    custom_sources_count = 0
    if sync_custom and not course_filter:
        custom_res = sync_custom_sources(known_catalog=known_catalog, on_file_saved_callback=on_file_saved_callback, max_workers=max_workers)
        custom_sources_count = custom_res.get("sources_synced", 0)

    user_files_count = 0
    if not course_filter:
        user_res = sync_user_files(known_catalog=known_catalog, on_file_saved_callback=on_file_saved_callback)
        user_files_count = user_res.get("files_found", 0)

    print("\n[Sync] Waiting for streaming indexing pipeline to finish remaining files...")
    concurrent.futures.wait(futures)
    executor.shutdown(wait=True)

    print("[Sync] [INFO] Updating list.md file structure...")
    list_mgr.update_list_file()

    return {
        "status": "success",
        "semester": semester_filter,
        "courses_synced": moodle_courses_synced,
        "custom_sources_synced": custom_sources_count,
        "user_files_found": user_files_count,
        "files_processed": len(processed_files),
        "total_chunks_indexed": indexed_chunks_total,
        "list_file": str(list_mgr.list_file_path),
        "message": f"Successfully synced {moodle_courses_synced} Moodle course(s), {custom_sources_count} custom source(s), and {user_files_count} user file(s)."
    }
