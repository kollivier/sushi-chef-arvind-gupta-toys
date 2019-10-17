#!/usr/bin/env python

import os
import pprint
import requests
import urllib
import json
import youtube_dl
import uuid
import re

from arvind import ArvindVideo, ArvindLanguage

from bs4 import BeautifulSoup
from copy import copy

from ricecooker.chefs import SushiChef
from ricecooker.classes.files import VideoFile
from ricecooker.classes.licenses import get_license
from ricecooker.classes.nodes import ChannelNode, VideoNode, TopicNode


LE = 'Learning Equality'

ARVIND = "Arvind Gupta Toys"

ARVIND_URL = "http://www.arvindguptatoys.com/films.html"

ROOT_DIR_PATH = os.getcwd()
DOWNLOADS_PATH = os.path.join(ROOT_DIR_PATH, "downloads")
DOWNLOADS_VIDEOS_PATH = os.path.join(DOWNLOADS_PATH, "videos/")

SKIP_VIDEOS_PATH = os.path.join(ROOT_DIR_PATH, "skip_videos.txt")

# These are the laguages that has no sub topics on its contents.
SINGLE_TOPIC_LANGUAGES = [
    "bhojpuri", "nepali", "malayalam", "telugu", "bengali", \
    "odiya", "punjabi", "marwari", "assamese", "urdu", \
     "spanish", "chinese", "indonesian", "sci_edu", "science/educational"
    ]

# List of multiple languages on its sub topics
MULTI_LANGUAGE_TOPIC = ["russian", "french",]

# This are the estimate total count of languages
TOTAL_ARVIND_LANG = 23


SINGLE_TOPIC = "single"
STANDARD_TOPIC = "standard"
MULTI_LANGUAGE = "multi"


def clean_video_title(title, lang_obj):
    # Remove redundant and misleading words in the video title
    pp = pprint.PrettyPrinter()
    clean_title = title
    try:
        if title != None:
            clean_str = title.replace("-", " ").replace("MB", "").replace("|", "")
            clean_uplang = clean_str.replace(lang_obj.name.upper(), "")
            clean_lowlang = clean_uplang.replace(lang_obj.name.lower(), "")
            clean_caplang = clean_lowlang.replace(lang_obj.name.capitalize() , "")
            clean_format = clean_caplang.replace(".avi", "").replace(".wmv", "").strip()
            clean_extra_spaces = re.sub(" +", " ",clean_format)
            is_int = clean_extra_spaces[-2:]
            if is_int.isdigit():
                clean_extra_spaces = clean_extra_spaces.replace(is_int, "")
            clean_title = clean_extra_spaces
            print("clean video title ====> ", clean_title)
    except Exception as e:
        print('Error cleaning this video title: ', clean_title)

    return clean_title


def include_video_topic(topic_node, video_data):
    video = video_data
    create_id = uuid.uuid4().hex[:12].lower()
    video_source_id = create_id + str(video.uid) 
    video_node = VideoNode(
        source_id=video_source_id, 
        title=clean_video_title(video.title, lang_obj), 
        description=video.description,
        aggregator=LE,
        thumbnail=video.thumbnail,
        license=get_license("CC BY-NC", copyright_holder=ARVIND),
        files=[
            VideoFile(
                path=video.filepath,
                language=video.language
            )
        ])
    topic_node.add_child(video_node)


def save_skip_videos(video, topic, lang_obj):
    if not os.path.exists(SKIP_VIDEOS_PATH):
        open(SKIP_VIDEOS_PATH,"w+")
    text_file = open(SKIP_VIDEOS_PATH, "a")
    video_info = video.language + " - "  + topic + " - " + video.url + " - "  + video.license + "\n" 
    text_file.write(video_info)
    text_file.close()


def download_video_topics(data, topic, topic_node, lang_obj):
    """
    Scrape, collect, and download the videos and their thumbnails.
    """
    pp = pprint.PrettyPrinter()

    for vinfo in data[topic]:
        try:
            video = ArvindVideo(
                url=vinfo['video_url'], 
                title=vinfo['video_title'], 
                language=lang_obj.code,
                filename_prefix=vinfo['filename_prefix'])
            print('==> DOWNLOADING', vinfo['video_url'])

            download_path = vinfo['download_path'] + "/" + topic + "/"
            if video.download(download_dir=download_path):
                if video.license_common:
                    include_video_topic(topic_node, topic, video)
                else:
                    print("=====> Video has no available creative common license", video.url)
                    save_skip_videos(video, topic, lang_obj)
            else:
                save_skip_videos(video, topic, lang_obj)

        except Exception as e:
            print('Error downloading videos:', e)


def generate_child_topics(arvind_contents, main_topic, lang_obj, topic_type):

    pp = pprint.PrettyPrinter()
    data = arvind_contents[lang_obj.name]
    for topic_index in data:
        print("======> Language topic", topic_index)
        if topic_type == STANDARD_TOPIC:
            source_id = topic_index + lang_obj.code
            topic_node = TopicNode(title=topic_index, source_id=source_id)
            download_video_topics(data, topic_index, topic_node, lang_obj)
            main_topic.add_child(topic_node)

        if topic_type == SINGLE_TOPIC:
            download_video_topics(data, topic_index, main_topic, lang_obj)
    return main_topic


def create_language_data(lang_data, lang_obj):
    # Todo clean up this function
    pp = pprint.PrettyPrinter()

    topic_contents = {}
    initial_topics = []
    prev_topic = ""
    counter = 1
    topic_limit = 0
    parent_topic = 0
    total_loop = len(lang_data)

    lang_name = lang_obj.name.lower() 
    # pp.pprint(lang_data)
    for item in lang_data:
        total_loop -= 1
        try:
            title = item.text.rstrip().strip()
            # pp.pprint(title)
            video_link = ""

            try:
                video_link = item.a.get("href")
                topic_details = {}
                ytd_domain = "youtube.com"
                if ytd_domain in video_link:

                    download_path = DOWNLOADS_VIDEOS_PATH + lang_name

                    if lang_name in MULTI_LANGUAGE_TOPIC:
                        current_lang = title.split()[0].lower()
                        if counter == 1:
                            # print("prev_topic ====>", current_lang)
                            counter = 0
                            prev_topic = current_lang

                        download_path = DOWNLOADS_VIDEOS_PATH + prev_topic

                    topic_details['video_url'] = video_link
                    topic_details['video_title'] = title
                    topic_details['filename_prefix'] = 'arvind-video-'
                    topic_details['download_path'] = download_path
                    # uncomment this to limit topic
                    # if topic_limit != 1:
                    #     topic_limit += 1

                    if lang_name in MULTI_LANGUAGE_TOPIC:
         
                        if prev_topic != current_lang:
                            topic_contents[prev_topic] = initial_topics
                            initial_topics = []
                            prev_topic = current_lang

                            # uncomment this to limit topic
                            if parent_topic == 10:
                                break
                            parent_topic += 1

                    initial_topics.append(topic_details)
            except:
                pass
            if counter == 1:
                if ":" in title:
                    counter = 0
                    prev_topic = title.replace(":", "").strip()

            if video_link == "":
                if ":" in title:
                    topic_contents[prev_topic] = initial_topics
                    prev_topic = title.replace(":", "").strip()
                    initial_topics = []
                    topic_limit = 0
                    # uncomment this to limit topic
                    # if parent_topic == 2:
                    #     break
                    # parent_topic += 1
                    # pp.pprint(title)
        except:
            pass
        if total_loop == 0:
            topic_contents[prev_topic] = initial_topics
    return topic_contents


def scrape_arvind_page():
    url = ARVIND_URL
    pp = pprint.PrettyPrinter()

    response = requests.get(url)
    page = BeautifulSoup(response.text, 'html5lib')
    content_divs = page.body.div
    list_divs = list(content_divs.children)
    laguages_div_start = 5
    languages_list = list(list_divs[laguages_div_start].children)
    return languages_list

def get_language_details(lang_name):
    video_lang = ArvindLanguage(name=lang_name)
    if video_lang.get_lang_obj():
        return video_lang
    return None


def create_languages_topic():
    arvind_languages = scrape_arvind_page()
    pp = pprint.PrettyPrinter()
    main_topic_list = []

    if os.path.exists(SKIP_VIDEOS_PATH):
        os.remove(SKIP_VIDEOS_PATH)
    loop_max = TOTAL_ARVIND_LANG
    language_next_counter = 7
    lang_limit = 0
    loop_couter = 0
    # for i in range(loop_count):
    while (loop_couter != loop_max):
        try:
            lang_name = arvind_languages[language_next_counter].get('id')
            # Increase the language_next_counter to get the next language contents
            lang_obj = get_language_details(lang_name.lower())
            if lang_obj != None:

                language_source_id = "arvind_main_" + lang_obj.code
                lang_name = lang_obj.name
                # print("=====> Creating Language topic for ", lang_name)
                lang_name_lower = lang_name.lower()

                get_language_data = list(arvind_languages[language_next_counter])
                data_contents = { lang_name: create_language_data(get_language_data, lang_obj) }
                language_topic = TopicNode(title=lang_name.capitalize(), source_id=language_source_id)

                # Filter languages that only has a language topics contents format
                if lang_name_lower not in SINGLE_TOPIC_LANGUAGES and lang_name_lower not in MULTI_LANGUAGE_TOPIC:
                    # uncomment this to limit language
                    # if lang_limit == 8:
                    #     break
                    # lang_limit += 1

                    # print("=======> This Language in standard format", lang_name)
                    # print("=====>")

                    topic_type = STANDARD_TOPIC
                    generate_child_topics(data_contents, language_topic, lang_obj, topic_type)
                    main_topic_list.append(language_topic)

                    print("=====>finished", lang_name)

                if lang_name_lower in SINGLE_TOPIC_LANGUAGES:
                    # Handle the single topic languages
                    # print("=====> This Language in single topic format ", lang_name)
                    # print("=====>")
                    # uncomment this to limit language
                    # if lang_limit == 1:
                    #     break
                    # lang_limit += 1

                    topic_type = SINGLE_TOPIC
                    generate_child_topics(data_contents, language_topic, lang_obj, topic_type)
                    main_topic_list.append(language_topic)

                    print("=====>finished", lang_name)

                if lang_name_lower in MULTI_LANGUAGE_TOPIC:
                    # Handle the multi topic languages


                    # generate_child_topics(data_contents, language_topic, lang_obj, topic_type)
                    print("=====> This Language in multiple langauage topic format ", lang_name)
                    print("=====>")
                    lang_data = create_language_data(get_language_data, lang_obj)
                    for lang in lang_data:
                        current_lang = get_language_details(lang.lower())
                        if current_lang != None:
                            topic_type = SINGLE_TOPIC
                            parent_source_id = "arvind_main_" + lang.lower()
                            parent_topic = TopicNode(title=lang.capitalize(), source_id=parent_source_id)
                            # print("lang data ==>", lang_data[lang])
                            # print("topic_type ==>", topic_type)
                            # print("current_lang ==>", current_lang.name)
                            data_dic = {current_lang.name: {"": lang_data[lang]}}

                            # if lang_limit == 1:
                            #     break
                            # lang_limit += 1

                            topic_type = SINGLE_TOPIC
                            # pp.pprint(data_dic)
                            generate_child_topics(data_dic, parent_topic, current_lang, topic_type)
                            main_topic_list.append(parent_topic)

                            print("=====>finished", lang)

        except Exception as e:
            print("===> error getting laguage topics==", e)
        language_next_counter += 4
        loop_couter += 1

    # pp.pprint(data_contents)
    return main_topic_list


class ArvindChef(SushiChef):
    channel_info = {
        "CHANNEL_TITLE": "Arvind Gupta Toys",
        # where you got the content (change me!!)
        "CHANNEL_SOURCE_DOMAIN": "arvindguptatoys.com",
        # channel's unique id (change me!!) # NOTE when you remove test- the channel_id will change; make sure to update notion card
        "CHANNEL_SOURCE_ID": "arvind-gupta-toys-beta-test",
        "CHANNEL_LANGUAGE": "mul",  # le_utils language code
        "CHANNEL_THUMBNAIL": 'chefdata/arvind_gupta_thumbnail.png',
        # (optional)
        "CHANNEL_DESCRIPTION": "Math and Science activities through low-cost " \
                "materials all in the form of videos to provide various pathways for children to explore" \
                " and deepen their understanding of concepts in low-resource contexts around the world." \
                " Valuable resource library for teachers to incorporate in their lessons, for parents to" \
                " work with children at home using readily available, simple, and low-cost materials.",
    }

    def construct_channel(self, **kwargs):

        channel = self.get_channel(**kwargs)

        languages_topic = create_languages_topic()
        for lang_topic in languages_topic:
            channel.add_child(lang_topic)
        return channel

if __name__ == "__main__":
    """
    Run this script on the command line using:
        python sushichef.py -v --reset --token=YOURTOKENHERE9139139f3a23232
    """

    chef = ArvindChef()
    chef.main()
    # create_languages_topic()
