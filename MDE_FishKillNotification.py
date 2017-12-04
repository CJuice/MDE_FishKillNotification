r"""
Modified from 'https://community.esri.com/docs/DOC-10163-send-email-when-a-feature-is-added-to-a-arcgis-online-hosted-feature-service'
Monitor an ArcGIS Online hosted feature service for new entries. The hosted feature service is is fed by a Survey123
form designed for capturing fish kill information for the MDE.

Author: CJuice
"""

import PrivateInformation
import urllib2, json, urllib, smtplib
import time, datetime
from datetime import timedelta
import logging

# Variables
strUsername = PrivateInformation.PrivateInformation.strAGOUsername                                          # AGOL Username
strPassword = PrivateInformation.PrivateInformation.strAGOCredentialSecret                                  # AGOL Password
strURL = PrivateInformation.PrivateInformation.strProtectedServiceURL                                       # Feature Service URL
strUniqueIDFieldName = PrivateInformation.PrivateInformation.strUniqueIDFieldName                           # i.e. OBJECTID
dateDateCreatedFieldName = PrivateInformation.PrivateInformation.dateDateCreatedFieldName                   # Date field to query
strUserNameEventCreatorFieldName = PrivateInformation.PrivateInformation.strUserNameEventCreatorFieldName   # Name of user who submitted report
strUserPhoneFieldName = PrivateInformation.PrivateInformation.strUserPhoneFieldName                         # User phone number
strUserEmailFieldName = PrivateInformation.PrivateInformation.strUserEmailFieldName                         # User email address
strDeadFishCountEstimateFieldName = PrivateInformation.PrivateInformation.strDeadFishCountEstimateFieldName # Estimate of number of dead fish
intHoursCheckValue = PrivateInformation.PrivateInformation.intHoursCheckValue                               # Number of hours to check when a feature was added
strFromEmail = PrivateInformation.PrivateInformation.strEmailUsername_From                                  # Email sender
strToEmail = PrivateInformation.PrivateInformation.strEmailUsername_To                                      # Email receiver
strSMTPServer = PrivateInformation.PrivateInformation.strSMTPServer                                         # SMPT Server Name
intPortNumber = 25                                                                                         # SMTP Server port. For TLS not SSL
strTokenURL = PrivateInformation.PrivateInformation.strTokenURL                                             # URL for generating token
strLOGFileName = "LOG_MDEFishKillNotificationProcess.log"
# strLOGFileName = "test.log"
tupTodayDateTime = datetime.datetime.utcnow().timetuple()
strTodayDateTimeForLogging = "{}/{}/{} UTC[{}:{}:{}]".format(tupTodayDateTime[0]
                                                          , tupTodayDateTime[1]
                                                          , tupTodayDateTime[2]
                                                          , tupTodayDateTime[3]
                                                          , tupTodayDateTime[4]
                                                          , tupTodayDateTime[5])
logging.basicConfig(filename=strLOGFileName,level=logging.INFO)
logging.info(" {} - Initiated".format(strTodayDateTimeForLogging))
# Create empty list for uniqueIDs
dictObjectIDandAttributes = {}

# Generate AGOL token
lsParamsTokenGeneration = {'f': 'pjson'
    , 'username': strUsername
    , 'password': strPassword
    , 'referer': 'http://www.arcgis.com'}
try:
    req = urllib2.Request(strTokenURL, urllib.urlencode(lsParamsTokenGeneration))
    response = urllib2.urlopen(req)
    dictData = json.load(response)
    token = dictData['token']
except Exception as e:
    logging.error(" Exception generating AGO token; no token generated:\n\t{}".format(e))
    # token = '' # The process won't run successfully without a token. Modifying script to exit.
    exit()

# Query service and check if created_date time is within the last intHoursCheckValue
lsParamsQueryService = {'f': 'pjson'
    , 'where': "1=1"
    , 'outfields' : '{}, {}, {}, {}, {}, {}'.format(strUniqueIDFieldName
                                                    , dateDateCreatedFieldName
                                                    , strUserNameEventCreatorFieldName
                                                    , strUserPhoneFieldName
                                                    , strUserEmailFieldName
                                                    , strDeadFishCountEstimateFieldName)
    , 'returnGeometry' : 'false'
    , 'token' : token}
try:
    req = urllib2.Request(strURL, urllib.urlencode(lsParamsQueryService))
    response = urllib2.urlopen(req)
    dictData = json.load(response)
except Exception as e:
    logging.error(" Exception querying protected service:\n\t{}".format(e))
    exit()
try:
    if dictData['features']:
        for feat in dictData['features']:
            createDate = feat['attributes'][dateDateCreatedFieldName]
            createDate = int(str(createDate)[0:-3])
            dtT = datetime.datetime.now() - timedelta(hours=intHoursCheckValue)
            dtT = time.mktime(dtT.timetuple())
            if createDate > dtT:
                dictObjectIDandAttributes[feat['attributes'][strUniqueIDFieldName]] = (feat['attributes'][strUserNameEventCreatorFieldName]
                                                                                       , feat['attributes'][strUserPhoneFieldName]
                                                                                       , feat['attributes'][strUserEmailFieldName]
                                                                                       , feat['attributes'][strDeadFishCountEstimateFieldName])
except Exception as e:
    logging.error(" Exception seeking 'features' key in response dictionary:\n\t{}".format(e))
    exit()

# Email Info
strTO = [strToEmail]
strSubjectLineText = "New Fish Kill Event(s) Reported"
strEmailBodyText = "{} New Features -  {}'s {} were added.".format(len(dictObjectIDandAttributes)
                                                                   , strUniqueIDFieldName
                                                                   , dictObjectIDandAttributes.keys())
message = "From: {}\nTo: {}\nSubject: {}\n\n{}\n".format(strFromEmail
                                                         , ", ".join(strTO)
                                                         , strSubjectLineText
                                                         , strEmailBodyText)

# If new features exist, send email
if len(dictObjectIDandAttributes) > 0:
    for key in dictObjectIDandAttributes.iterkeys():
        strNewEntryDetails = "\nOID: {}\n\tSize - {}\n\t{}, {}, {}".format(key
                                                                           , dictObjectIDandAttributes[key][3]
                                                                           , dictObjectIDandAttributes[key][0]
                                                                           , dictObjectIDandAttributes[key][1]
                                                                           , dictObjectIDandAttributes[key][2])
        message = message + strNewEntryDetails
    try:
        # server = smtplib.SMTP(strSMTPServer, 587)
        server = smtplib.SMTP(strSMTPServer, intPortNumber)
        server.ehlo()
        server.starttls()
        # server.login(PrivateInformation.PrivateInformation.strEmailUsername, PrivateInformation.PrivateInformation.strEmailCredentialSecret)
        server.sendmail(strFromEmail, strTO, message)
        server.quit()
        logging.info("\t\tEmail generated")

        # print "FORCED EXIT FOR TESTING"
        # print "EMAIL CONTENT FOLLOWS\n\n{}".format(message)

    except Exception as e:
        logging.error(" Exception emailing:\n\t{}".format(e))
else:
    pass

logging.info(" complete")
