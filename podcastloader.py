#!/usr/bin/python3
import logging
import requests
import json
import xml.dom.minidom
import os
import sys

class PodcastLoader(object):

    def __init__(self):

        # init logging module
        logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)
        logging.info("Started PodcastLoader")

        # read config file
        self.configuration = self.read_config_file(os.path.join(os.path.dirname(sys.argv[0]), "podcastloader.conf"))
        logging.debug(self.configuration)

        # iterate podcast list
        for podcast in self.configuration["podcasts"]:
            logging.debug("found %s (%s)" % (podcast["podcast"], podcast["url"]))
            rss_feed = self.load_rss_information(podcast["url"], podcast["episodes"])
            logging.debug(rss_feed)

            try:

                podcast_directory = os.path.join(self.configuration["target_directory"], podcast["podcast"])
            
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
                        self.download_episode(rss_entry ["url"], podcast_directory)

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
    def load_rss_information(self, url, max_episodes):

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
