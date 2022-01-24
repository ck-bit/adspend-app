from datetime import datetime
from distutils.util import byte_compile
from subprocess import call
import main, config
import requests
import json
import base64
from flask import session
from requests_oauthlib import OAuth2Session

from googleauth import refreshToken


api_key = config.pinterest_api_key
secret_key = config.pinterest_secret_key

callback_uri = "http://localhost:8080/home"

def authorizePinterest():

    payload = {
        "client_id": api_key,
        "redirect_uri" : callback_uri,
        "response_type": "code",
        "scope": "ads:read"
    }

    r = requests.get("https://www.pinterest.com/oauth/", params=payload)

  
      
    session['pinterest_url'] = r.url

    # sets the session status to accept pinterest codes
    session['auth_code_type'] = 'pinterest'
  
   
def fetchToken(authCode):

    token_url = "https://api.pinterest.com/v5/oauth/token"
    
    payload = {
      "code": authCode,
       "redirect_uri": callback_uri,
        "grant_type": "authorization_code"
    }

    str_raw = api_key + ":" + secret_key
    str_bytes = str_raw.encode("ascii")
    base64_bytes = base64.b64encode(str_bytes)
    base64_string = base64_bytes.decode("ascii")

    print(base64_string)
    headers = {
     "Authorization" : "Basic " + base64_string,
     "Content-Type" : "application/x-www-form-urlencoded"

    }

    r = requests.post(token_url, data=payload, headers=headers)
    print("Here is your Pinterest token: ") 
    print(r.text)


    token_info = json.loads(r.text)
    access_token = token_info.get('access_token')
    refresh_token = token_info.get('refresh_token')
    
    print(access_token)
    print(refresh_token)

    session['pinterest_token'] = access_token
    session['pinterest_refresh'] = refresh_token


def getPinterestCharges():

    # first, get all ad accounts and add to add account array
    ad_account_ids = []


    pinterest = OAuth2Session(api_key, token=session.get("pinterest_token"))
    url = "https://api.pinterest.com/v5/ad_accounts"
    r = pinterest.get(url=url)
    response = json.loads(r.text)
    accounts = response["items"]


     # for each ad account, get total cost for current month and add it
    for account in accounts:
        id = account["id"]
        ad_account_ids.append(id)


    spend = 0;

    for id in ad_account_ids:
        url = "https://api.pinterest.com/v5/ad_accounts/{ad_account_id}/analytics".format(ad_account_id=id)

        # only get ads within the current month 
        payload = {
            "ad_account_id": "myaccount",
            "columns" : "SPEND_IN_DOLLAR",
            "granularity": "MONTH"
        }

        r = pinterest.get(url=url, params=payload)
        response = json.loads(r.text)
        monthly_cost = response["SPEND_IN_DOLLAR"]
        spend += monthly_cost

    return spend;
     

