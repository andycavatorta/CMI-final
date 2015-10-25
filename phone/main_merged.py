#!/usr/bin/env python

import base64
import commands
import hashlib
import ip_email
import json
import logging
import os
import pygame
import sys
import time
import threading
import urllib
import urllib2 

PI_NATIVE = os.uname()[4].startswith("arm") # TRUE if running on RPi
AUDIO_DIRECTORY = "audiofiles/"
AUDIO_TEMP_DIRECTORY = "audiofiles_temp/"
DTMF_DIRECTORY = "dtmf/"
RINGTONE_PATH = "ringtone/ringtone.ogg"
LOG_PATH = "logs/temp.log"
BASE_PATH = "/media/usb0/CMI-final/phone/" if PI_NATIVE else "/home/stella/Dropbox/projects/current/CMI/gitrepo/CMI-final/phone/" 
BASE_URL = "https://callmeishmael-api.herokuapp.com"

with open(BASE_PATH + 'settings.json', 'r') as f:
    CONFIG = json.load(f)

print CONFIG

try:
    ip_email.main(
        CONFIG["to_field"], 
        CONFIG["from_field"], 
        CONFIG["password_field"], 
        CONFIG["SMTP_field"], 
        CONFIG["SMTP_port"]
    )
except Exception as e:
    print "exception in ip_email.py", e


if PI_NATIVE:
    import RPi.GPIO as GPIO
else:
    import RPi_stub.GPIO as GPIO

HWListener_lock = threading.Event()

#print "PI_NATIVE=", PI_NATIVE

class HWListener(threading.Thread):
    def __init__(self):
        try:
            logger.logEvent("Event: HWListener thread started")
            threading.Thread.__init__(self)
            self.lock = HWListener_lock
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(23,GPIO.OUT)
            GPIO.setup(24,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(26,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
            self.bellButtonPin = False
            self.bellButtonState = False
            self.hangUpState = True
            self.matrix = [ [4,5,14,6],[1,2,15,3],[7,8,16,9],[11,0,13,10] ]
            self.row = [12,16,18,22]
            self.col = [7,11,13,15] 
            self.debounceTimeStamp = 0.0 # seconds
            self.debounceTimeout = 0.25 # seconds
            self.bellActive = False
            for j in range(4):
                GPIO.setup(self.col[j],GPIO.OUT)
                GPIO.output(self.col[j],1)
            for i in range(4):
                GPIO.setup(self.row[i],GPIO.IN,pull_up_down=GPIO.PUD_UP)
        except Exception as e:
            logger.logEvent('Exception:  HWListener.__init__: %s'  % (repr(e)))

    def checkBell(self):
        try:
            self.bellButtonPin = GPIO.input(26)
            if self.bellButtonPin and self.bellButtonState  == False:
                self.bellButtonState = True
                audioPlayer.playRingtone()
                #GPIO.output(23,1)
                logger.logEvent('Event: HWListener.checkBell detects button pushed ' )

            if self.bellButtonPin == False and self.bellButtonState == True:
                self.bellButtonState = False
                audioplayer.stopRingtone()
                #GPIO.output(23,0)

        except Exception as e:
            logger.logEvent('Exception: HWListener.checkBell: %s'  % (repr(e)))


    def checkHang(self):
        try:
            self.hangPin = GPIO.input(24)

            if self.hangUpState == False and self.hangPin == 1:  # if cradle  
                self.hangUpState = True
                self.debounceTimeStamp = time.time()
                audioPlayer.stopAudioFile()
                logger.logEvent('Event: HWListener.checkHang detects receiver hung up ')

            if self.hangUpState == True and self.hangPin == 0:  # if cradle was just lifted
                self.hangUpState = False
                #self.debounceTimeStamp = time.time()
                #audioPlayer.stopAudioFile()
                audioPlayer.playContent(12)
                logger.logEvent('Event: HWListener.checkHang detects  receiver lifted ')

        except Exception as e:
            logger.logEvent('Exception: HWListener.checkHang: %s'  % (repr(e)))


    def run(self): 
        while True:
            try:
                if time.time() - self.debounceTimeStamp > self.debounceTimeout: # event is not within debounce timeout
                    self.checkBell()
                    self.checkHang()
                    for j in range(4):
                        GPIO.output(self.col[j],0)
                        for i in range(4):
                            #hang = GPIO.input(24)
                            i#f (hang==1): # phang=1
                            #    audioPlayer.stopAudioFile()
                            if ((GPIO.input(self.row[i])==0)):
                                buttonNumber = self.matrix[i][j]
                                logger.logEvent("Event: HWListener detects button push%s" % str(buttonNumber))
                                audioPlayer.playSequence(buttonNumber)
                                #while(GPIO.input(self.row[i])==0):
                                #    pass
                                self.debounceTimeStamp = time.time()
                                #prev_input=GPIO.input(self.row[i])
                                time.sleep(0.05)
                        GPIO.output(self.col[j],1)
                    time.sleep(0.05)
                else:
                    time.sleep(0.05)
            except Exception as e:
                logger.logEvent('Exception: HWListener.run: %s'  % (repr(e)))
                time.sleep(0.05)

AudioPlayer_lock = threading.Event()

# to do: does AudioPlayer need to run in its own thread?  PyGame's threading will probably handle everything
class AudioPlayer(threading.Thread):
    def __init__(self):
        logger.logEvent("Event: AudioPlayer thread starting")
        threading.Thread.__init__(self)
        resp = commands.getstatusoutput("sudo amixer cset numid=1 400")
        self.lock = AudioPlayer_lock
        pygame.mixer.pre_init(48000, -16, 2, 4096)
        pygame.mixer.init()
        pygame.TIMER_RESOLUTION = 5
        self.rootDirectory_str = BASE_PATH + AUDIO_DIRECTORY
        self.audioFileNames_l = []
        self.contentSounds_l = []
        self.dtmfSounds_l = []
        self.ringtoneSound = None
        self.getFileNames()
        self.loadContentSounds()
        self.sound = None
        self.loadDTMFSounds()
        self.loadRingtoneSound()
        self.postRollFlag = False
        self.playbackErorDetectionTimer = 0
        logger.logEvent("Event: AudioPlayer thread initialized")
    def run(self): 
        while True:
            if pygame.mixer.get_busy() == 0:
                if self.postRollFlag:
                    #playbackLength_f = time.time() - self.playbackErorDetectionTimer
                    #if playbackLength_f > 5:
                    #    logger.logEvent('Exception: AudioPlayer.run: file not playing, possibly incomplete or damaged')
                    self.playContent(12)
                    #audioPlayer.playAudioFile(self.audioFileNames_l[11])
                    self.postRollFlag = False
                    #self.playContent(12)
                # print pygame.mixer.get_busy()

            time.sleep(1)
    def getFileNames(self):
        try:
            audioFileNames_l = []
            for i in range(13):
                foundFileName_str = ""
                searchPattern = str(i).zfill(2) + "_"
                directoryListing_l = os.listdir(self.rootDirectory_str)
                for fName in directoryListing_l:
                    if fName[0:3] == searchPattern:
                        foundFileName_str = fName
                        break
                audioFileNames_l.append(foundFileName_str)
            logger.logEvent('Event: AudioPlayer.getFileNames found %s local audio files' % str(len(directoryListing_l)))
            self.lock.set()
            self.audioFileNames_l = audioFileNames_l
            self.lock.clear()
            logger.logEvent('Event: AudioPlayer.getFileNames succeeded')
        except Exception as e:
            logger.logEvent('Exception: AudioPlayer.getFileNames: %s'  % (repr(e)))

    def loadDTMFSounds(self):
        try:
            for i in range(12):
                filePath = "%s%s%s.%s" % (BASE_PATH,DTMF_DIRECTORY, str(i), "aiff")
                sound = pygame.mixer.Sound(filePath)
                sound.set_volume(1.0) 
                self.dtmfSounds_l.append(sound)
                logger.logEvent('Event: AudioPlayer.loadDTMFSounds succeeded for %s' % (filePath))
        except Exception as e:
            logger.logEvent('Exception: AudioPlayer.loadDTMFSounds: %s'  % (repr(e)))

    def loadRingtoneSound(self):
        try:
            self.ringtoneSound = pygame.mixer.Sound("%s%s" % (BASE_PATH,RINGTONE_PATH))
            self.ringtoneSound.set_volume(1.0) 
            logger.logEvent('Event: AudioPlayer.loadRingtoneSound succeeded for %s' % (RINGTONE_PATH))
        except Exception as e:
            logger.logEvent('Exception: AudioPlayer.loadRingtoneSound: %s'  % (repr(e)))

    def loadContentSounds(self):
        try:
            for afn in self.audioFileNames_l:
                if afn == "":
                    self.contentSounds_l.append(False)
                else:
                    filePath = "%s%s%s" % (BASE_PATH, AUDIO_DIRECTORY, afn)
                    sound = pygame.mixer.Sound(filePath)
                    sound.set_volume(1.0) 
                    self.contentSounds_l.append(sound)
                    logger.logEvent('Event: AudioPlayer.loadContentSounds succeeded for %s' % (filePath))
        except Exception as e:
            logger.logEvent('Exception: AudioPlayer.loadContentSounds: %s'  % (repr(e)))

    def playContent(self, ordinal):
        try:
            filePath = "%s%s%s" % (BASE_PATH, AUDIO_DIRECTORY, self.audioFileNames_l[ordinal])
            #sound = pygame.mixer.Sound(filePath)
            #sound.set_volume(1.0) 
            #sound.play(0)
            channel = self.contentSounds_l[ordinal].play(0)
            channel.set_volume(1.0,0.0) 
            logger.logEvent('Event: AudioPlayer.playContent playing %s' % (filePath))
        except Exception as e:
            logger.logEvent('Exception: AudioPlayer.playContent: %s'  % (repr(e)))

    def stopContent(self, ordinal):
        try:
            pygame.mixer.stop()
            self.self.postRollFlag = False
        except Exception as e:
            logger.logEvent('Exception: AudioPlayer.stopContent: %s'  % (repr(e)))

    def playDTMF(self, ordinal):
        try:
            channel = self.dtmfSounds_l[ordinal].play(0)
            channel.set_volume(1.0,0.0) 
        except Exception as e:
            logger.logEvent('Exception: AudioPlayer.playDTMF: %s'  % (repr(e)))

    def playRingtone(self):
        try:
            print "1 ##################################"
            channel = self.ringtoneSound.play(0)
            print "2 ##################################"
            channel.set_volume(0.0,1.0) 
            print "3 ##################################"
        except Exception as e:
            logger.logEvent('Exception: AudioPlayer.playRingtone: %s'  % (repr(e)))

    def playSequence(self, ordinal):
        pygame.mixer.stop()
        # play DTMF
        self.playDTMF(ordinal)
        # play Content
        self.playContent(ordinal)
        #audioPlayer.playAudioFile(self.audioFileNames_l[ordinal])
        time.sleep(1)
        if 1 <= ordinal <=9:
            self.postRollFlag = True

    def stopAudioFile(self):
        try:
            pygame.mixer.stop()
            self.postRollFlag = False
            logger.logEvent('Event: AudioPlayer.stopAudioFile succeeded')
        except Exception as e:
            logger.logEvent('Exception: AudioPlayer.stopAudioFile: %s'  % (repr(e)))

    def stopRingtone(self):
        try:
            self.ringtoneSound.stop()
        except Exception as e:
            logger.logEvent('Exception: AudioPlayer.stopRingtone: %s'  % (repr(e)))

NetSync_lock = threading.Event()

class NetSync(threading.Thread):
    def __init__(self):
        try:
            logger.logEvent("Event: NetSync thread started")
            threading.Thread.__init__(self)
            self.lock = NetSync_lock
            # https://callmeishmael-api.herokuapp.com/venues/1/phones/1/ping
            self.ping_url = "%s/venues/%s/phones/%s/ping" % (BASE_URL, CONFIG["venueID"], CONFIG["phoneID"]) # GET
            self.fileNames_url = "%s/venues/%s/phones/%s/files" % (BASE_URL, CONFIG["venueID"], CONFIG["phoneID"]) # GET
            self.logFile_url = "%s/venues/%s/phones/%s/log" % (BASE_URL, CONFIG["venueID"], CONFIG["phoneID"]) # POST
            self.logFile_path = BASE_PATH+LOG_PATH
            self.audioFiles_path = BASE_PATH + AUDIO_DIRECTORY
            self.remoteFileCount = 12
            logger.logEvent("Event: NetSync thread initialized")
        except Exception as e:
            logger.logEvent('Exception: NetSync.__init__: %s'  % (repr(e)))
    def run(self): 
        try:
            logger.postToServer()
            self.syncFiles() # get fresh file names every time this boots
            while True:
                if self.minuteEquals(('00','10','20','30','40','50')): 
                    self.getPing() # ping every hour
                #if self.minuteEquals(('00')): 
                #    self.syncFiles()
                #    logger.postToServer()
                time.sleep(31) # 31 seconds so this the main conditional can fire only one per minute.
        except Exception as e:
            logger.logEvent('Exception: NetSync.run: %s'  % (repr(e)))
    def minuteEquals(self,mins_t): # for readability during dev
        try:
            return time.strftime("%M") in mins_t
        except Exception as e:
            logger.logEvent('Exception: NetSync.minuteEquals: %s' % (repr(e)))
    def hourEquals(self,hours_t): # for readability during dev
        try:
            return time.strftime("%H") in hours_t
        except Exception as e:
            logger.logEvent('Exception: NetSync.hourEquals: %s'  % (repr(e)))
    def getPing(self):
        try:
            logger.logEvent('Event: NetSync.getPing sending request')
            response = urllib2.urlopen(self.ping_url)
            html = response.read()
            logger.logEvent('Event: NetSync.getPing response: %s' % (html))
        except Exception as e:
            logger.logEvent('Exception: NetSync.getPing: %s'  % (repr(e)))
    def getRemoteFileNames(self):
        try:
            response = urllib2.urlopen(self.fileNames_url)
            paths_json = response.read()
            #print repr(paths_json)
            logger.logEvent("Event: NetSync.getRemoteFileNames retrieved remote file names from API")
            return paths_json 
        except Exception as e:
            logger.logEvent('Exception: NetSync.getRemoteFileNames: %s'  % (repr(e)))
            return False
    def downloadRemoteFile(self, remoteFilePath, localFilePath):
        try:
            logger.logEvent("Event: NetSync.downloadRemoteFile starting download of remote file %s as %s" % (remoteFilePath,localFilePath))
            u = urllib2.urlopen(remoteFilePath) 
            localFile = open(localFilePath , 'w') 
            localFile.write(u.read()) 
            localFile.close()
            logger.logEvent("Event: NetSync.downloadRemoteFile downloaded remote file %s as %s" % (remoteFilePath,localFilePath))
            return True
        except Exception as e:
            logger.logEvent('Exception: NetSync.downloadRemoteFile: %s  URL: %s'  % (repr(e), remoteFilePath))
            return False
    def getLocalFileNames(self):
        try:
            audioFileNames_l = os.listdir(self.audioFiles_path)
            audioFileNames_l.sort()
            return audioFileNames_l
        except Exception as e:
            logger.logEvent('Exception: NetSync.getLocalFileNames: %s'  % (repr(e)))
    def deleteLocalFile(self, localFilePath):
        try:
            os.remove(localFilePath)
            logger.logEvent("Event: NetSync.deleteLocalFile deleted local file %s" % localFilePath)
        except Exception as e:
            logger.logEvent('Exception: NetSync.deleteLocalFile: %s'  % (repr(e)))
    def md5(self,fname):
        try:
            hash = hashlib.md5()
            with open(fname, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash.update(chunk)
            return hash.digest()
        except Exception as e:
            logger.logEvent('Exception: NetSync.md5: %s'  % (repr(e)))
            return False
    def addOrdinalToFileName(self, ordinal, filename):
        return "%s_%s" % (str(ordinal).zfill(2),filename)
    def verifyFile(self,remoteFileData):
        try:
            # calculate MD5 checksums for downloaded files
            remoteFileData["local_MD5"] = self.md5(remoteFileData["localFilePath_str"])
            remoteMD5Path = "%s%s" % (remoteFileData["remoteFilePath_str"][:-3],"md5")
            response = urllib2.urlopen(remoteMD5Path)
            remoteFileData["remote_MD5"] =  response.read()
            # print remoteFileData["local_MD5"], remoteFileData["remote_MD5"], remoteFileData["local_MD5"] == remoteFileData["remote_MD5"]
            # print remoteFileData["MD5"]
            # download MD5 checksums for changed files
            return remoteFileData["local_MD5"] == remoteFileData["remote_MD5"]
        except Exception as e:
            logger.logEvent('Exception: NetSync.verifyFile: %s'  % (repr(e)))
            return False

        
    def moveVerifiedFile(self, remoteFileData, localFileNames_l):
        # search local files for ordinal
        
        for localFileName in localFileNames_l:
            # delete previous local file with same ordinal
            if localFileName[0:2] == str(remoteFileData["ordinal"]).zfill(2):
                self. deleteLocalFile("%s%s%s" % (BASE_PATH, AUDIO_DIRECTORY, localFileName))
        os.rename(remoteFileData["localFilePath_str"], "%s%s%s" % (BASE_PATH, AUDIO_DIRECTORY, remoteFileData["remoteFileNamePlusOrdinal_str"]))
    def syncFiles(self):
        try:
            # retrieve list of names of remote files from server
            remotePaths_json = self.getRemoteFileNames()# fetch json list of remote file names from server
            remotePaths_l =  json.loads(remotePaths_json) # 
            remoteFileNames_l = [  path_str.rsplit("/")[-1] for  path_str in remotePaths_l  ]
            remoteFileData_l = []
            for rfni in range(len(remoteFileNames_l)):
                remoteFileData_l.append(
                    {
                        "ordinal" : rfni,
                        "remoteFileName_str" : remoteFileNames_l[rfni],
                        "remoteFilePath_str" : remotePaths_l[rfni],
                        "remoteFileNamePlusOrdinal_str" : self.addOrdinalToFileName(rfni, remoteFileNames_l[rfni]),
                        "localFilePath_str" : "%s%s%s_%s" % (BASE_PATH, AUDIO_TEMP_DIRECTORY, str(rfni).zfill(2),remoteFileNames_l[rfni]),
                        "local_MD5" : "",
                        "remote_MD5" : "",
                        "download": False,
                        "verified": False
                    }
                )
            # get local file names
            localFileNames_l = self.getLocalFileNames()
            for remoteFileData in remoteFileData_l:
                if remoteFileData["remoteFileNamePlusOrdinal_str"] not in localFileNames_l: # if remote file does not match local file
                    remoteFileData["download"] = True
                    # download / verify loop
                    for tries in range(3):
                        self.downloadRemoteFile(remoteFileData["remoteFilePath_str"], "%s%s%s" % (BASE_PATH, AUDIO_TEMP_DIRECTORY, remoteFileData["remoteFileNamePlusOrdinal_str"] ))                    
                        if self.verifyFile(remoteFileData):
                            logger.logEvent('Event: NetSync.syncFiles verify %s succeeded for file %s' % (str(tries),remoteFileData["remoteFilePath_str"]))
                            self.moveVerifiedFile(remoteFileData,localFileNames_l)
                            break
                        else:
                            logger.logEvent('Event: NetSync.syncFiles verify %s failed for file %' % (str(tries),remoteFileData["remoteFilePath_str"])) 

            audioPlayer.getFileNames()
            audioPlayer.loadContentSounds()

        except Exception as e:
            logger.logEvent('Exception in NetSync.syncFiles: %s'  % (repr(e)))

class Logger():
    def __init__(self):
        self.logFile_path = BASE_PATH+LOG_PATH
        self.maxFileSize = 100000
        self.logFile_url = "%s/venues/%s/phones/%s/log" % (BASE_URL, CONFIG["venueID"], CONFIG["phoneID"]) # POST
        self.logFile_path = BASE_PATH+LOG_PATH
        self.init()
    def init(self):
        logging.basicConfig(
                format='%(asctime)s %(message)s',
                level=logging.DEBUG,
                filename=self.logFile_path
        )
    def logEvent(self, msg):
        print msg
        self.checkFileSize()
        logging.info(msg)
    def checkFileSize(self):
        try:
            if os.path.getsize(self.logFile_path) > self.maxFileSize: # log file size exceeds max size
                print "Maximum file size exceeded.  Deleting log file.", os.path.getsize(self.logFile_path)
                self.postToServer()
        except Exception as e:
            print "Logger.checkFileSize Exception deleting log file %s" % (repr(e))
    def delete(self):
        try:
            #cmd = "touch %s" % (self.logFile_path)
            #os.remove(self.logFile_path)
            open(self.logFile_path, 'w').close()
            #commands.getstatusoutput(cmd)
            self.init()
        except Exception as e:
            print "Logger.delete Exception deleting log file %s" % (repr(e))

    def postToServer(self):
        try:
            logText_str = ""
            log_file = open(self.logFile_path)
            try:
                for line in log_file:
                    logText_str += line
                logText_encoded = base64.standard_b64encode(logText_str)
                logText_encoded = urllib.quote(logText_encoded)
                logTextWithVarName_str = "log="+logText_encoded
                curl_str = "curl -i -X POST -d '%s' %s" % (logTextWithVarName_str, self.logFile_url)
                resp = commands.getstatusoutput(curl_str)
                self.delete()
            finally:
                log_file.close()
        except Exception as e:
            self.logEvent('Exception in Logger.postToServer: %s'  % (repr(e)))

def main():
    global hwListener, audioPlayer,netSync, logger
    logger = Logger()
    hwListener = HWListener()
    audioPlayer = AudioPlayer()
    netSync = NetSync()
    hwListener.start()
    audioPlayer.start()
    time.sleep(1) # slight delay to be certain audioPlayer.getFileNames
    netSync.start()
main()


