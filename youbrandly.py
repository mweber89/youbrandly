#!/usr/bin/python

import argparse
import pprint
import sys
import os
import requests
import json
import base64
from datetime import datetime
from datetime import date

import httplib2
import oauth2client
from oauth2client import file
from oauth2client import tools
from googleapiclient.discovery import build

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


# Google Stuff
CLIENT_ID = ''
CLIENT_SECRET = ''
SCOPE = ['https://www.googleapis.com/auth/youtube.readonly', 'https://www.googleapis.com/auth/gmail.send']
USER_AGENT = ''
OAUTH_DISPLAY_NAME = ''
TOKENFILE = './oauth_token.dat'
argv = sys.argv

# GMAIL
EMAIL = ''

# Rebrandly stuff
API_KEY = ''
WORKSPACE = ''
LINK_ID = ''
DEFAULT_LINK = ''

def auth():
    # Parse command line flags used by the oauth2client library.
    parser = argparse.ArgumentParser(
        description='Authentication',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[tools.argparser])
    flags = parser.parse_args(argv[1:])

    # Acquire and store oauth token.
    storage = oauth2client.file.Storage(TOKENFILE)
    credentials = storage.get()

    if credentials.access_token_expired:
        print('OAuth Token is expired. Trying to refresh.')
        credentials.refresh(httplib2.Http())
        print(credentials)


    if credentials is None or credentials.invalid:
        flow = oauth2client.client.OAuth2WebServerFlow(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scope=SCOPE,
            user_agent=USER_AGENT,
            oauth_displayname=OAUTH_DISPLAY_NAME)
        credentials = tools.run_flow(flow, storage, flags)
    http = httplib2.Http()
    http = credentials.authorize(http)

    return(http)

def get_next_broadcast():

    service = build('youtube', 'v3', http = auth())

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
        log = "Problem beim abrufen des Link. " + str(r.status_code)
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
            return sendmail, current_link, url
        else:
            log = "Problem beim aktualisieren des Link. " + str(r.status_code)
            print(log)
    else:
        log = "Link ist bereits korrekt gesetzt."
        print(log)

def SendMessage(sender, to, subject, msgHtml, msgPlain):

    service = build('gmail', 'v1', http = auth())

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

    print('')
    print('##################################')
    print('##################################')
    print(datetime.now().strftime("%d.%m.%Y %H:%M"))
    
    next_broadcast = get_next_broadcast()

    # Check if broadcast is today
    if next_broadcast['start'].split('T')[0] == str(date.today()):
        mailinfo = 'Heute findet ein Livestream statt.'
        print(mailinfo)
        setLink = setRebrandly(next_broadcast['link'])
    else:
        mailinfo = 'Heute findet KEIN Livestream statt.'
        print(mailinfo)
        setLink = setRebrandly(DEFAULT_LINK)

    # Send Mail if Link was updated
    try:
        if setLink[0] == True:
            to = EMAIL
            sender = EMAIL
            subject = "Rebrandy-Link aktualisiert: " + setLink[1]['slashtag']
            msgHtml = mailinfo + "<br/>Alter Link:" + setLink[1]['destination'] + "<br/>Neuer Link: " + setLink[2]
            msgHtml += "<br/><br/>Unser nächster Livestream:<br/>" + "Titel: " + next_broadcast['title'] + "<br/>Start: " + next_broadcast['start'] + "<br/>Link: " + next_broadcast['link']
            msgPlain = "Hi\nPlain Email"
            SendMessage(sender, to, subject, msgHtml, msgPlain)
            print("Mail versendet.")
    except TypeError:
        print("Keine Mail versendet.")
    
    print('##################################')
    print('##################################')
    print('')