import main, config
import requests
from typing import Text
from requests_oauthlib import OAuth1, OAuth1Session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import insert, select, update
from sqlalchemy.sql.functions import count, user
from sqlalchemy.sql import func
from flask import session

api_key = config.etsy_api_creds["api_key"]
secret_key = config.etsy_api_creds["secret_key"]
callback_uri = "http://127.0.0.1:8080/home"

# Fetch Request Token 
def authorizeEtsy():
    # if user hasn't authorized yet, set the resource owner tokens and allow them to access link. 
    if(config.etsy_resource["key"] == None): 
        oauth = OAuth1Session(api_key, client_secret=secret_key, callback_uri=callback_uri)
        request_token_url = "https://openapi.etsy.com/v2/oauth/request_token?scope=email_r%20billing_r"
        fetch_response = oauth.fetch_request_token(request_token_url)

        login_url = fetch_response.get('login_url')
        
        config.etsy_resource["key"] = fetch_response.get('oauth_token')
        config.etsy_resource["secret"] = fetch_response.get('oauth_token_secret')

        print(login_url)
        session["etsy_url"] = login_url
        return login_url

# Fetch Access Token 
def fetchToken(verifier, user): 
    oauth = OAuth1Session(api_key,
                            client_secret=secret_key,
                            resource_owner_key=config.etsy_resource["key"],
                            resource_owner_secret=config.etsy_resource["secret"],
                            verifier=verifier)

    access_url = "https://openapi.etsy.com/v2/oauth/access_token"
    oauth_tokens = oauth.fetch_access_token(access_url)
   
    # store oauth token to user in persistent db
    oauth_key = oauth_tokens.get('oauth_token')
    oauth_secret = oauth_tokens.get('oauth_token_secret')
    user_ = main.User.query.filter_by(username=user.username).first()
    user_.etsy_key = oauth_key
    user_.etsy_secret = oauth_secret
    main.db.session.commit()
  
# Access Protected Resources
def getEtsyCharges(etsy_key, etsy_secret):
    headeroauth = OAuth1(api_key, secret_key,
                        etsy_key, etsy_secret,
                        signature_type='auth_header')

    get_charges = 'https://openapi.etsy.com/v2/users/509187507/charges?min_created=1626400643'

    r = requests.get(url=get_charges, auth=headeroauth)
    print(r.text)
    return r






