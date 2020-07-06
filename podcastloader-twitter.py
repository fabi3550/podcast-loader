#!/usr/bin/python3

import tweepy

class PodcastTwitter(object):

    def __init__(self, twitter_configuration):

        # extract OAuth information from configuration json
        self.consumer_key = twitter_configuration["consumer_key"]
        self.consumer_secret = twitter_configuration["consumer_secret"]
        self.access_token = twitter_configuration["access_token"]
        self.access_token_secret = twitter_configuration["access_token_secret"]

        # authenticate the given user
        authenticator = self.register()

        # build api object from authentication
        try:
            
            if authenticator:
                self.api = tweepy.API(authenticator)
                    
        except tweepy.TweepError as e:
            print(e)
            

    # method to authenticate a user by given OAuth credentials
    # returns an authentification object if OAuth credentials are valid
    def register(self):

        auth = None
        
        try:
            auth = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret)
            auth.set_access_token(self.access_token, self.access_token_secret)
            
        except tweepy.TweepError as e:
            print(e)

        return auth

    
    # wrapper method around sending a direct message to a twitter user
    def send_direct_message(self, screen_name, message):

        try:
            user = self.api.get_user(screen_name)
            self.api.send_direct_message(user.id, message)
            
        except tweepy.TweepError as e:
            print(e)

