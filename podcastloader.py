#!/usr/bin/python3
import logging
import requests
import json
import xml.dom.minidom
import os
import sys
from podcastloadertwitter import PodcastTwitter

class PodcastLoader(object):

    def __init__(self):

        # init logging module
        logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
        logging.info("Started PodcastLoader")

        # read config file
        self.configuration = self.read_config_file(os.path.join(os.path.dirname(sys.argv[0]), "podcastloader.conf"))
        logging.debug(self.configuration)

        # check for twitter auth information
        has_twitter = False
        
        try:
            if 'twitter' in self.configuration:
                if all (keys in self.configuration['twitter'] for keys in ('consumer_key', 'consumer_secret', 'access_token', 'access_token_secret')):
                    has_twitter = True
                    logging.info("Found Twitter Account data")
                
        except KeyError as e:
            logging.error(e)

        except TypeError as e:
            logging.error(e)

        # dict for possible twitter notifications
        twitter_dm = {}
        
        # iterate podcast list
        for podcast in self.configuration["podcasts"]:

            # fix for issues 2 and 3: 'podcast' and 'url' will now checked.
            # episodes is an optional parameter. if not set, all episodes will be downloaded
            # https://github.com/fabi3550/podcast-loader/issues/2
            # https://github.com/fabi3550/podcast-loader/issues/3
            if all (keys in podcast for keys in ('podcast', 'url')):
                logging.debug("found %s (%s)" % (podcast["podcast"], podcast["url"]))
                if "episodes" in podcast:
                    rss_feed = self.load_rss_information(podcast["url"], podcast["episodes"])
                else:
                    rss_feed = self.load_rss_information(podcast["url"])
                    
            logging.debug(rss_feed)

            try:

                podcast_directory = os.path.join(self.configuration["target_directory"], podcast["podcast"])
                loaded_episodes = []
            
                # create podcast subdirectory if not exists
                if not os.path.exists(podcast_directory):
                    os.makedirs(podcast_directory)
                    logging.info("created directory %s" % (podcast_directory))
            
                # check for existing podcasts, download if not existing
                for rss_entry in rss_feed:
                    filename = rss_entry["url"].split("/")[-1]
                    logging.debug("searching for %s" % (filename))

                    if not filename in os.listdir(podcast_directory):
                        logging.info("downloading %s to %s" % (filename, podcast_directory))
                        self.download_episode(rss_entry["url"], podcast_directory)

                        # if twitter notifications are enabled, collect data about the loaded episodes
                        if has_twitter:
                            podcast_information = [rss_entry["title"]]

                            if 'description' in rss_entry:
                                podcast_information.append(rss_entry["description"][:100] + "...")

                            loaded_episodes.append(podcast_information)
                            

                    # checking reverse - are there too much podcasts?
                    for podcast_file in os.listdir(podcast_directory):
                        found = False
                        for rss_entry in rss_feed:
                            if podcast_file == rss_entry["url"].split("/")[-1]:
                                found = True
                                break

                        if not found:
                            logging.info("removing %s from %s" % (podcast_file, podcast_directory))
                            os.remove(os.path.join(podcast_directory, podcast_file))

            except OSError as e:
                logging.error(e)

            twitter_dm[podcast["podcast"]] = loaded_episodes
            logging.debug(twitter_dm)
                
        if has_twitter:
            
            message_text = ""

            for loaded_podcast in twitter_dm:

                if len(twitter_dm[loaded_podcast]) > 0:
                    message_text += "Podcast: " + loaded_podcast + "\r\n"
                    for loaded_episode in twitter_dm[loaded_podcast]:
                        message_text += "Episode: " + loaded_episode[0] + "\r\n"

                        if len(loaded_episode) > 1:
                            message_text += "Beschreibung: " + loaded_episode[1] + "\r\n"

            if len(message_text) > 0:
                str_twitter_dm = "Neue Podcasts verfügbar: \r\n" + message_text
                logging.info("Sending message: \r\n " + str_twitter_dm)
                podcast_twitter = PodcastTwitter(self.configuration["twitter"])
                podcast_twitter.send_direct_message("fabi3550", str_twitter_dm)
                            
        logging.info("Stopped PodcastLoader")
        
                    
    # read configuration file
    # function checks for different kind of json errors
    # and returns a json object
    def read_config_file(self, config_file):

        logging.debug("call read_config_file")
        is_config_file_found = False
        try:
            f = open(config_file, "r")
            configuration = json.loads(f.read())
            is_config_file_found = True
            
        except IOError as e:
            logging.error(e)

        except KeyError as e:
            logging.error(e)

        except ValueError as e:
            logging.error(e)

        except JSONDecodeError as e:
            logging.error(e)

        if is_config_file_found:
            return configuration
        
        
    # load rss information
    # returns a list of podcast episode urls

    # fix for issues 2 and 3: max_episodes is now an optional parameter
    def load_rss_information(self, url, max_episodes=None):

        episodes = []

        try:
            response = requests.get(url)
            document = xml.dom.minidom.parseString(response.text)
            items = document.getElementsByTagName("item")
            counter = 0
            for item in items:
                
                episode = {}
                
                for node in item.childNodes:
                    if node.nodeType == node.ELEMENT_NODE:
                        if node.tagName in ["title", "description"]:
                            for subnode in node.childNodes:
                                if subnode.nodeType == subnode.TEXT_NODE:
                                    logging.debug(subnode.nodeValue)
                                    episode[node.tagName] = subnode.nodeValue

                        if node.tagName == "enclosure":
                            logging.debug(node.getAttribute("url"))
                            episode["url"] = node.getAttribute("url")

                logging.debug(episode)

                # issue 1: if no url is found in rss feed, the application
                # crashes - this is fixed now
                # https://github.com/fabi3550/podcast-loader/issues/1
                if all (keys in episode for keys in ('title','url')):
                    episodes.append(episode)
                    counter += 1

                if counter == max_episodes:
                    break
        
        except requests.ConnectionError as e:
            logging.error(e)

        except requests.HTTPError as e:
            logging.error(e)

        except requests.Timeout as e:
            logging(e)

        return episodes
    

    # downloads an podcast episode to the given directory
    def download_episode(self, url, target_directory):

        filename = url.split("/")[-1]
        logging.debug(filename)

        try:
        
            response = requests.get(url, stream=True)

            with open(os.path.join(target_directory, filename), "wb") as episode:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        episode.write(chunk)
        
        except requests.HTTPError as e:
            logging.error(e)

        except OSError as e:
            logging.error(e)

    
if __name__ == "__main__":
    podcastloader = PodcastLoader()
