#!/usr/bin/python

import os
import requests
import json
import base64
from google.oauth2.credentials import Credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# CLIENT_SECRETS_FILE = 'client_secret.json'
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly', 'https://www.googleapis.com/auth/gmail.send']
API_VERSION = 'v3'

# GMAIL
EMAIL = ''

# Rebranfly stuff
API_KEY = ''
WORKSPACE = ''
LINK_ID = ''

# Google OAuth
def get_credentials():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    #return build(API, API_VERSION, credentials = creds)
    return creds

# Retrieve upcoming broadcasts
def get_broadcasts():

    service = build('youtube', 'v3', credentials = get_credentials())

    list_broadcasts_request = service.liveBroadcasts().list(
        broadcastStatus='upcoming',
        part='id,snippet',
        maxResults=5
    )

    broadcasts = {}

    list_broadcasts_response = list_broadcasts_request.execute()
    for broadcast in list_broadcasts_response.get('items', []):
        try:
            # Get only the first valid Broadcast
            if not broadcasts:
                broadcast_id = broadcast['id']
                broadcast_link = "https://youtu.be/" + broadcast['id']
                broadcast_title = broadcast['snippet']['title']
                broadcast_start = broadcast['snippet']['scheduledStartTime']
                broadcasts = {
                    'id': broadcast_id, 
                    'link': broadcast_link, 
                    'title': broadcast_title, 
                    'start': broadcast_start
                }
                log = "Nächster YouTube Stream: " + broadcast_title + " | Link: " + broadcast_link + " | Geplanter Start: " + broadcast_start
                print(log)
        except KeyError:
            pass
    
    return(broadcasts)

def setRebrandly(url):

    # Get current Link
    get_request = requests.get("https://api.rebrandly.com/v1/links/"+LINK_ID, headers = {"apikey": API_KEY})
    if (get_request.status_code == requests.codes.ok):
        current_link = get_request.json()
        print("Aktueller Link: " + current_link['destination'])
    else:
        log = "Problem beim abrufen des Link. " + r.status_code
        print(log)
        return log

    # Check if current link is already correct
    if current_link['destination'] != url:
        r = requests.post("https://api.rebrandly.com/v1/links/"+LINK_ID, data = json.dumps({"destination": url}), headers = {"Content-type": "application/json", "apikey": API_KEY})
        if (r.status_code == requests.codes.ok):
            link = r.json()
            log = "Link aktualisiert. Alter YouTube-Link: " + current_link['destination'] + " | Neuer YouTube-Link: " + url
            sendmail = True
            print(log)
            return sendmail, current_link
        else:
            log = "Problem beim aktualisieren des Link. " + r.status_code
            print(log)
    else:
        log = "Link ist bereits korrekt gesetzt."
        print(log)

def SendMessage(sender, to, subject, msgHtml, msgPlain):

    service = build('gmail', 'v1', credentials = get_credentials())

    message1 = CreateMessage(sender, to, subject, msgHtml, msgPlain)
    result = SendMessageInternal(service, "me", message1)
    return result

def SendMessageInternal(service, user_id, message):
    try:
        message = (service.users().messages().send(userId=user_id, body=message).execute())
        print('Message Id: %s' % message['id'])
        return message
    except errors.HttpError as error:
        print('An error occurred: %s' % error)

def CreateMessage(sender, to, subject, msgHtml, msgPlain):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to
    msg.attach(MIMEText(msgPlain, 'plain'))
    msg.attach(MIMEText(msgHtml, 'html'))
    raw = base64.urlsafe_b64encode(msg.as_bytes())
    raw = raw.decode()
    body = {'raw': raw}
    return body

if __name__ == '__main__':

    next_bc = get_broadcasts()
    setLink = setRebrandly(next_bc['link'])
    #print(setLink)
    try:
        if setLink[0] == True:
            to = EMAIL
            sender = EMAIL
            subject = "Rebrandy-Link aktualisiert: " + setLink[1]['slashtag']
            msgHtml = "Alter Link:" + setLink[1]['destination'] + "<br/>Neuer Link: " + next_bc['link'] + "<br/>Titel: " + next_bc['title'] + "<br/>Start: " + next_bc['start']
            msgPlain = "Hi\nPlain Email"
            SendMessage(sender, to, subject, msgHtml, msgPlain)
            print("Mail versendet.")
    except TypeError:
        print("Keine Mail versendet.")


    