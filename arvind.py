import json
import os
import pprint
import re
import youtube_dl

from le_utils.constants.languages import getlang_by_name


YOUTUBE_CACHE_DIR = os.path.join('chefdata', 'youtubecache')
YOUTUBE_ID_REGEX = re.compile(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?(?P<youtube_id>[A-Za-z0-9\-=_]{11})')

# List of languages not avialble at the le_utils
UND_LANG = {
            "marwari":{
                "name":"Marwari",
                "native_name":"marwari",
                "code": "und",      # temporary while le-utils updated in Studio
            },
            "bhojpuri":{
                "name":"Bhojpuri",
                "native_name":"bhojpuri",
                "code":"und",       # temporary while le-utils updated in Studio
            },
            "odiya":{
                "name":"Odiya",
                "native_name":"odiya",
                "code":"or",
            },
            "sci_edu":{
                "name":"Science/Educational",
                "native_name":"hindi",
                "code":"hi",
            },
    }


class ArvindLanguage():
    name = ''
    code = ''
    native_name = ''

    def __init__(self, name='', code='', native_name=''):
        self.name = name.lower()
        self.code = code
        self.native_name = native_name

    def set_value(self, name, code, native_name):
        self.name = name
        self.code = code
        self.native_name = native_name

    def get_lang_obj(self):

        if self.name != "":
            lang_name = self.name
            language_obj = getlang_by_name(lang_name)

            if not language_obj:
                
                if UND_LANG[self.name]:
                    self.set_value(UND_LANG[self.name]["name"], UND_LANG[self.name]["code"], UND_LANG[self.name]["native_name"])
                    return True
            else:
                self.set_value(language_obj.name, language_obj.code, language_obj.native_name)
                return True
        return False



class ArvindVideo():

    uid = 0   # value from `id` after `youtube_dl.extract_info()`
    title = ''
    description = ''
    url = ''
    language = ''
    thumbnail = ''  # local path to thumbnail image
    license = ''
    download_dir = './'
    license_common = False

    def __init__(self, uid=0, url='', title='', description='', language='',):
        self.uid = str(uid)
        self.url = url
        self.title = title
        self.description = description
        self.thumbnail = None
        self.language = language

    def __str__(self):
        return 'ArvindVideo (%s - %s - %s)' % (self.uid, self.url, self.title)

    def download_info(self, download_dir="./", download=False):

        match = YOUTUBE_ID_REGEX.match(self.url)
        if not match:
            print('==> URL ' + self.url + ' does not match YOUTUBE_ID_REGEX')
            return False
        youtube_id = match.group('youtube_id')
        if not os.path.isdir(YOUTUBE_CACHE_DIR):
            os.mkdir(YOUTUBE_CACHE_DIR)
        vinfo_json_path = os.path.join(YOUTUBE_CACHE_DIR, youtube_id+'.json')
        # First try to get from cache:
        if os.path.exists(vinfo_json_path):
            vinfo = json.load(open(vinfo_json_path))
        # else get using youtube_dl:
        else:
            ydl_options = {
                'outtmpl': youtube_id,
                'writethumbnail': True,
                'no_warnings': True,
                'continuedl': False,
                'restrictfilenames': True,
                'quiet': False,
                # Note the format specification is important so we get mp4 and not taller than 480
                'format': "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]"
            }
            with youtube_dl.YoutubeDL(ydl_options) as ydl:
                pp = pprint.PrettyPrinter()
                try:
                    ydl.add_default_info_extractors()
                    # vinfo = ydl.extract_info(self.url, download=True)
                    vinfo = ydl.extract_info(self.url, download=download)
                    # Save the remaining "temporary scraped values" of attributes with actual values
                    # from the video metadata.
                    json.dump(vinfo, open(vinfo_json_path, 'w'), indent=4, ensure_ascii=False, sort_keys=True)

                except (youtube_dl.utils.DownloadError,
                        youtube_dl.utils.ContentTooShortError,
                        youtube_dl.utils.ExtractorError,) as e:
                        print('==> Error downloading this video', e)
                        # pp.pprint(e)
                        return False

        self.uid = vinfo['id']  # video must have id because required to set youtube_id later
        self.title = vinfo.get('title', '')
        self.description = vinfo.get('description', '')
        if not vinfo['license']:
            self.license = "Licensed not available"
        elif "Creative Commons" in vinfo['license']:
            self.license_common = True
        else:
            self.license = vinfo['license']

        return True
