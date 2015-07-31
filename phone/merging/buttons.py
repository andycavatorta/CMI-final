import RPi.GPIO as GPIO # External module imports - GPIO
import time # External module imports - time
import pygame # External module imports - pygame

MATRIX = [	[4,5,"6x",6],
			[1,2,"3x",3],
			[7,8,"9x",9],
			[12,10,"PUSH",11]	]

ROW = [12,16,18,22]
COL = [7,11,13,15]

# def play(key):
	# print(key)

# def main():
GPIO.setmode(GPIO.BOARD) # Set GPIO using BOARD pin numberss



for j in range(4):
	GPIO.setup(COL[j],GPIO.OUT)
	GPIO.output(COL[j],1)

for i in range(4):
	GPIO.setup(ROW[i],GPIO.IN,pull_up_down=GPIO.PUD_UP)

try:
	while(True):
		for j in range(4):
			GPIO.output(COL[j],0)
			for i in range(4):
				prev_input = 0
				if ((GPIO.input(ROW[i])==0 and not prev_input)):
					# play(MATRIX[i][j])
					print(MATRIX[i][j])
					while(GPIO.input(ROW[i])==0):
						pass
					prev_input=GPIO.input(ROW[i])
					time.sleep(0.5)
						
				
				
			GPIO.output(COL[j],1)
		#code

except KeyboardInterrupt:
		GPIO.cleanup()

# if __name__=="__main__":
#     main()
