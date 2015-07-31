# components
#   network sync
#   play audio
#   hardware events
#   logging
# 
# 
# multiple threads or multiple processes?
#   stability: thread safety vs. socket stability
#   start with threads
# 
# how to prevent crashes?   
#   thread safety
#   try/except blocks
# 
# 
# 
# 
# 

import logging
import os
import pygame
import time
import threading
import RPi.GPIO as GPIO # External module imports - GPIO


MATRIX = [  [4,5,14,6],
            [1,2,15,3],
            [7,8,16,9],
            [12,0,13,11]   ]

ROW = [12,16,18,22]
COL = [7,11,13,15]

GPIO.setmode(GPIO.BOARD) # Set GPIO using BOARD pin numberss

for j in range(4):
    GPIO.setup(COL[j],GPIO.OUT)
    GPIO.output(COL[j],1)

for i in range(4):
    GPIO.setup(ROW[i],GPIO.IN,pull_up_down=GPIO.PUD_UP)

GPIO.setup(24,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)

config = {
    "audio_directory" : "/home/pi/CMI/phone/audiofiles/",
    "log_directory" : "/home/pi/CMI/phone/logs/temp.log"
}

HWListener_lock = threading.Event()

class HWListener(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.lock = HWListener_lock
    def run(self): 
        while True:
            hang = GPIO.input(24)
            if (hang==0):
                #print ("ACTIVE")
                pass
            if (hang==1):
                #print ("INACTIVE")
                audioPlayer.stopAudioFile()

            for j in range(4):
                GPIO.output(COL[j],0)
                for i in range(4):
                    prev_input = 0
                    if ((GPIO.input(ROW[i])==0 and not prev_input)):
                        audioPlayer.playAudioFile(audioPlayer.audioFileNames_l[MATRIX[i][j]])
                        print(MATRIX[i][j])
                        while(GPIO.input(ROW[i])==0):
                            pass
                        prev_input=GPIO.input(ROW[i])
                        time.sleep(0.5)
                    # if (([i][j])==13):
                    #     audioPlayer.stopAudioFile()
                    #     time.sleep(0.5)

                GPIO.output(COL[j],1)
        GPIO.cleanup()




            # # selection = raw_input("type track number or 's' to stop")
            # if selection in ['0','1','2','3','4','5','6','7','8','9']:
            #     audioPlayer.playAudioFile(audioPlayer.audioFileNames_l[int(selection)])
            # if selection == "s":
                
            # #print repr(selection)

AudioPlayer_lock = threading.Event()

class AudioPlayer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.lock = AudioPlayer_lock
        pygame.mixer.pre_init(48000, -16, 2, 16384)
        pygame.mixer.init()
        pygame.TIMER_RESOLUTION = 5
        self.rootDirectory_str = config["audio_directory"]
        self.audioFileNames_l = []
        self.getFileNames()
        self.sound = None
    def run(self): 
        #while True:
            pass

    def getFileNames(self):
        audioFileNames_l = []
        for i in range(0,10):
            foundFileName_str = ""
            searchPattern = "0" + str(i) + "_"
            directoryListing_l = os.listdir(self.rootDirectory_str)
            for fName in directoryListing_l:
                if fName[0:3] == searchPattern:
                    foundFileName_str = fName
                    break
            audioFileNames_l.append(foundFileName_str)
        self.lock.set()
        self.audioFileNames_l = audioFileNames_l
        self.lock.clear()

    def playAudioFile(self, filename):
        logger.logEvent('audio.play ' + filename)
        self.stopAudioFile()
        filePath = self.rootDirectory_str + filename
        self.lock.set()
        self.sound = pygame.mixer.Sound(filePath)
        self.sound.play(loops=0)
        self.lock.clear()

    def stopAudioFile(self):
        logger.logEvent('audio.stop')
        if self.sound:
            self.sound.stop()

NetSync_lock = threading.Event()

class NetSync(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.lock = NetSync_lock
    def run(self): 
        while True:
            time.sleep(10)

class Logger():
    def __init__(self):
        logging.basicConfig(
                format='%(asctime)s %(message)s',
                level=logging.DEBUG,
                filename=config["log_directory"]
        )
        #logging.basicConfig(filename=config["log_directory"],level=logging.DEBUG)
    def logEvent(self, msg):
        #longMsg = time.strftime("    %Y-%m-%d %H:%M:%S    ") + msg
        logging.info(msg)
    def delete(self):
        pass
    def getContents(self):
        pass

def main():
    global hwListener, audioPlayer,netSync, logger
    logger = Logger()
    hwListener = HWListener()
    audioPlayer = AudioPlayer()
    netSync = NetSync()
    hwListener.start()
    audioPlayer.start()
    netSync.start()
    
main()
