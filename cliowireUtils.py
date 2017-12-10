import mastodon
import math

class Pulse:
    def __init__(self, id, content, reply_to_id=None):
        self.id=id
        self.reply_to_id=reply_to_id
        self.content=content


class PulseIterator():

    def __init__(self, api_instance, batch_size=200, hashtag=None, recent_id=None, oldest_id=None):
        self.batch_size = batch_size
        self.api_instance = api_instance
        self.hashtag = hashtag
        self.curr = recent_id
        self.oldest_id = oldest_id
        self.hasnext = True

    def __iter__(self):
        return self


    def __next__(self):
        pulses = []
        retrieved = None
        if self.curr == None:
            retrieved = self.retrieve_pulses(None)
            self.curr = math.inf
        else:
            retrieved = self.retrieve_pulses(self.curr)
        if retrieved == None or len(retrieved) == 0:
            raise StopIteration()
        else:
            for r in retrieved:
                nP = Pulse(r['id'], r['content'], r['in_reply_to'])
                if nP.id < self.curr:
                    self.curr = nP.id
                pulses.append(np)
        return pulses


    def retrieve_pulses(self, recent_id):
        if self.hashtag == None:
            self.api_instance.timeline_local(max_id=recent_id, since_id=self.oldest_id, limit=self.batch_size)
        else:
            self.api_instance.timeline_hashtag(self.hashtag, max_id=recent_id, since_id=self.oldest_id, limit=self.batch_size)
