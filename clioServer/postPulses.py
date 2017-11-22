from mastodon import Mastodon

def post_content(api_instance, pulses):
    for p in pulses:
        api_instance.toot(p)
    return len(pulses)
