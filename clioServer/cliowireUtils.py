import mastodon
import math
import os
import re

METAFILE_PATTERN='\n The file of bot logins should hold at least those two informations in the following order : \n<bot\'s login>\n<bot\'s username>\n\n Make sure they are correctly separated by a line break\n Do not delete this file after using the bot, as it will hold metainformations relevant to the bot internal workings for further uses'

def retrieveBotsMetadata(args):
    if len(args) == 0:
        raise Exception('[ERROR] You need to provide the name of the file which holds'+
                ' the bot login informations as the first argument of this program')
    else:
        filename = args[0]
        if not os.path.isfile(filename):
            raise Exception('[ERROR] The file name you specified refer'+
                    ' to a non existent file. Please create such'+
                    ' a file follwing this pattern : '+METAFILE_PATTERN)
        else:
            f = open(filename, 'r')
            lines = f.readlines()
            if len(lines) < 2:
                f.close()
                raise Exception('[ERROR] The file given as argument did not hold'+
                    ' the required informations. Please make sure your file '+
                    'conform to this patter : '+METAFILE_PATTERN)

            login = lines[0].replace('\n', '')
            pswd = lines[1].replace('\n', '')
            last_id = None
            if len(lines) > 2:
                last_id = int(lines[2].replace('\n', ''))
            f.close()
            return login, pswd, last_id


def updateBotsMetadata(filename, last_id):
    f = open(filename, 'r')
    lines = f.readlines()
    if len(lines) <= 2:
        #this branch will be reached if it's the first time the bot is launched
        lines.append(str(last_id))
    else:
        lines[2] = str(last_id)
    for l in lines:
        l.replace('\n', '')
    f.close()
    f = open(filename, 'w')
    f.write(''.join(lines))
    f.close()



def cleanHTTP(content):
    #Remove href balises, but keep the url
    cleanHref = re.compile('<a[^>]+href=\"(.*?)\"[^>]*>')
    #Remove every other http balises
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanHref, '', content)
    cleantext = re.sub(cleanr, '', cleantext)
    return cleantext

'''
Small class that is a downsampled object representation of pulses retrived on
ClioWire. Made for the sake of mudalirity, clarity, and for future additions.
'''
class Pulse:
    def __init__(self, id, content, reply_to_id=None, hashtags=None):
        self.id=id
        self.reply_to_id=reply_to_id
        self.content=content
        self.hashtags=[]
        if hashtags != None:
            for h in hashtags:
                self.hashtags.append(h['name'])
'''
Iterator that will retrieve pulses in a batch each time its next method is
called. Produce the illusion that all the pulses querried are in the RAM, while in
fact they are retrieved online each time the next is called.
'''
class PulseIterator():

    def __init__(self, api_instance, batch_size=200, hashtag=None, recent_id=None, oldest_id=None, user=None):
        self.batch_size = batch_size
        self.api_instance = api_instance
        self.hashtag = hashtag
        self.latest_id = recent_id
        self.curr = recent_id
        self.oldest_id = oldest_id
        self.userid = user
        self.hasnext = True

    def __iter__(self):
        return self


    def __next__(self):
        pulses = []
        retrieved = None
        if self.curr == None:
            retrieved = self.retrieve_pulses(None)
            self.curr = math.inf
            self.latest_id = 0
        else:
            retrieved = self.retrieve_pulses(self.curr)
        if retrieved == None or len(retrieved) == 0:
            raise StopIteration()
        else:
            for r in retrieved:
                nP = Pulse(r['id'], r['content'], r['in_reply_to_id'], r['tags'])
                if nP.id < self.curr:
                    self.curr = nP.id
                if nP.id > self.latest_id:
                    self.latest_id = nP.id
                pulses.append(nP)
        return pulses

    def latest_id(self):
        return self.curr


    def retrieve_pulses(self, recent_id):
        if self.hashtag == None and self.userid == None:
            return self.api_instance.timeline_local(max_id=recent_id, since_id=self.oldest_id, limit=self.batch_size)
        elif self.userid == None:
            return self.api_instance.timeline_hashtag(self.hashtag, max_id=recent_id, since_id=self.oldest_id, limit=self.batch_size, local=True)
        else:
            return self.api_instance.account_statuses(self.userid, max_id=recent_id, since_id=self.oldest_id, limit=self.batch_size)
