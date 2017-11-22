from mastodon import Mastodon
import sys
import os

DOMAIN_NAME='https://cliowire.dhlab.epfl.ch'

CLIENT_CRED='_clientcred.secret'
USER_CRED='_usercred.secret'

# Register app - only once!
def register_app(appName):
    Mastodon.create_app(
     appName,
     api_base_url = DOMAIN_NAME,
     to_file = appName + CLIENT_CRED
    )

def log_in(appName, userLogin, userPswd):
    mastodon = Mastodon(
        client_id = appName+CLIENT_CRED,
        api_base_url = DOMAIN_NAME
    )

    mastodon.log_in(
        userLogin,
        userPswd,
        to_file = appName+USER_CRED
    )

    # Create actual API instance
    return Mastodon(
        client_id = appName+CLIENT_CRED,
        access_token = appName+USER_CRED,
        api_base_url = DOMAIN_NAME
    )

def checkIfCredentials(appName):
    filepath = appName+CLIENT_CRED
    if not os.path.isfile(filepath):
        register_app(appName)
