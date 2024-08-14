import cv2
import dlib
from imutils import face_utils
import numpy as np
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pygame
from twilio.rest import Client

class SMSThread(threading.Thread):
    def __init__(self, account_sid, auth_token, twilio_phone_number, receiver_phone_number):
        super().__init__()
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.twilio_phone_number = twilio_phone_number
        self.receiver_phone_number = receiver_phone_number
        self.client = Client(self.account_sid, self.auth_token)
        self.sms_event = threading.Event()
        self._stop_event = threading.Event()
        self.daemon = True  # Ensures the thread exits when the main program exits
        self.start()

    def run(self):
        while not self._stop_event.is_set():
            self.sms_event.wait()  # Wait until the event is set
            if self._stop_event.is_set():
                break
            self.sms_event.clear()  # Reset the event for the next use
            self.send_sms()  # Send the SMS

    def send_sms(self):
        try:
            message = self.client.messages.create(
                body="Driver Drowsiness Detection System Alert!!! Driver is sleeping please Wake him up",
                from_=self.twilio_phone_number,
                to=self.receiver_phone_number
            )
            print(f"Message sent to {self.receiver_phone_number}: {message.sid}")
        except Exception as e:
            print(f"Failed to send SMS to {self.receiver_phone_number}: {e}")

    def trigger_sms(self):
        self.sms_event.set()  # Trigger the SMS sending

    def terminate(self):
        self._stop_event.set()
        self.sms_event.set()  # Unblocks the thread if it's waiting


class SMTPThread(threading.Thread):
    def __init__(self, receiver_email):
        super(SMTPThread, self).__init__()
        self.receiver_email = receiver_email
        self._stop_event = threading.Event()
        self._mail_queue = threading.Event()
        self.daemon = True  # Ensures the thread exits when the main program exits
        self.start()

    def run(self):
        while not self._stop_event.is_set():
            if self._mail_queue.is_set():
                self._mail_queue.clear()
                self.send_mail()

    def send_mail(self):
        # Email configuration
        sender_email = "devmahawaryt25@gmail.com"
        password = "loeh rdui miyl kmvw"

        # Create message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = self.receiver_email
        message["Subject"] = "DROWSINESS ALERT"
        body = "WARNING!!! Driver is feeling sleepy. Please take a break."
        message.attach(MIMEText(body, "plain"))

        try:
            # Connect to SMTP server
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, password)
                server.send_message(message)
            print("Email sent successfully!")
        except Exception as e:
            print(f"Error sending email: {str(e)}")

    def trigger_mail(self):
        self._mail_queue.set()

    def terminate(self):
        self._stop_event.set()
        self._mail_queue.set()  # Unblocks the thread if it's waiting




class AlarmThread(threading.Thread):
	def __init__(self, sound_path):
		super(AlarmThread, self).__init__()
		self.sound_path = sound_path
		self._stop_event = threading.Event()
		self._pause_event = threading.Event()
		self._pause_event.set()  # Initially set to pause
		self._mute_event = threading.Event()  # Initially set to unmute

	def run(self):
		pygame.mixer.init()
		while not self._stop_event.is_set():
			while self._pause_event.is_set() or self._mute_event.is_set():
				pygame.time.delay(100)
			pygame.mixer.music.load(self.sound_path)
			pygame.mixer.music.play()
			while pygame.mixer.music.get_busy():
				pygame.time.delay(100)

	def pause(self):
		self._pause_event.set()

	def resume(self, new_sound_path=None):
		if new_sound_path:
			self.sound_path = new_sound_path
		self._pause_event.clear()

	def mute(self):
		self._mute_event.set()

	def unmute(self):
		self._mute_event.clear()

	def terminate(self):
		self._stop_event.set()
		self.resume()  # Resume in case the thread is paused



# Creating a function which calculates euclidian distance between two points.
def compute(ptA,ptB):
	dist = np.linalg.norm(ptA - ptB)
	return dist

# Function for checking whether eyes blinked or not.
def blinked(a,b,c,d,e,f):
	up = compute(b,d) + compute(c,e)
	down = compute(a,f)
	ratio = up/(2.0*down)

	#Checking if it is blinked
	if(ratio>0.25):
		return 2	#indicates eye is open
	elif(ratio>0.18 and ratio<=0.25):
		return 1	#indicates eye is drowsy
	else:
		return 0	#ndicates eye is closed



def mainfunc():
	#Creating alarm and smtp threads so if we play alarm or send email it will not interrupt driver program execution
	path = r"sound\Alarm.mp3"
	alarm_thread_run = False
	alarm_thread = AlarmThread(path)

	smtp_thread = SMTPThread("devrajmahor2004@gmail.com")
	email_send = False

	ACCOUNT_SID = 'ACc1fa7d3f2662277ce91dbce2c361cc1a'
	AUTH_TOKEN = '4998331a147ee516fbd473c4038fa0f5'
	TWILIO_PHONE_NUMBER = '+17249064644'
	RECEIVER_PHONE_NUMBER = '+918532984855'  # Replace with the actual recipient phone number
	sms_thread = SMSThread(ACCOUNT_SID, AUTH_TOKEN, TWILIO_PHONE_NUMBER, RECEIVER_PHONE_NUMBER)



	#creating face detector and landmarks predictor
	detector = dlib.get_frontal_face_detector()
	predictor = dlib.shape_predictor("models\\shape_predictor_68_face_landmarks.dat")

	#Creating driver drowsiness state variables
	sleep = 0
	drowsy = 0
	active = 0
	status=""
	color=(0,0,0)

	#accessing webcam
	camera = 0
	cap = cv2.VideoCapture(camera)

	# Main program loop
	while True:
		ret, frame = cap.read()		#Frame Capturing
		frame = cv2.flip(frame,1)	
		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		faces = detector(gray)
		# face_frame = frame.copy()  #copied frame used in line 125
		
		for face in faces:		#for every detected face in faces array which are present in frame
			#Storing these landmarks' co-ordinates into numpy array
			landmarks = predictor(gray, face)
			landmarks = face_utils.shape_to_np(landmarks)
			
			# x1 = face.left()
			# y1 = face.top()
			# x2 = face.right()
			# y2 = face.bottom()
			# cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)	
			
			#The numbers are actually the landmarks which will show eye
			left_blink = blinked(landmarks[36],landmarks[37], 
				landmarks[38], landmarks[41], landmarks[40], landmarks[39])
			right_blink = blinked(landmarks[42],landmarks[43], 
				landmarks[44], landmarks[47], landmarks[46], landmarks[45])
			

			# eyes Status decision
			if(left_blink==0 or right_blink==0):
				sleep+=1
				drowsy=0
				active=0
				if(sleep>6):
					status="SLEEPING !!!"
					color = (255,0,0)
					
					if not alarm_thread_run:	#if alarm thread is not running then start
						alarm_thread.start()
						alarm_thread_run = True
					else: 						
						#if alarm thread is already started and if it is paused because driverwas active then resume it
						alarm_thread.resume()


					if(sleep>50) and (not email_send):
						#send only one email whenever driver falls into sleeping state from active state
						sms_thread.trigger_sms()
						smtp_thread.trigger_mail()
						email_send = True


			elif(left_blink==1 or right_blink==1):
				sleep=0
				active=0
				drowsy+=1
				if(drowsy>6):
					status="Drowsy !"
					color = (0,0,255)
					if not alarm_thread_run:	#if alarm thread is not running then start
						alarm_thread.start()
						alarm_thread_run = True
					else:
						#if alarm thread is already started and if it is paused because driverwas active then resume it
						alarm_thread.resume()	

			else:
				drowsy=0
				sleep=0
				active+=1
				if(active>6):
					status="Active :)"
					color = (0,255,0)
					email_send = False
					if alarm_thread_run:		#if driver is in active state then stop alarm thread
						alarm_thread.pause()

				
			# cv2.putText(face_frame, status, (100,100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color,3)	#for landmarks checking internal code
			# for n in range(0, 68):	#it shows landmark on face
			# 		(x,y) = landmarks[n]
			# 		cv2.circle(frame, (x,y), 1, (255,255,255),-1) 
			cv2.putText(frame, status, (100,100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color,3)	
					
		cv2.imshow("RESULT", frame)
		# cv2.imshow("Landmarks", face_frame) #for landmarks checking internal code
		
		key = cv2.waitKey(1)
		if key == ord("m")and alarm_thread_run & 0xFF: 
			alarm_thread.mute()		#mute the alarm thread press m
		if key == ord("u")and alarm_thread_run & 0xFF:
			alarm_thread.unmute()	#unmute the alarm tread press u

		if key == ord("q") & 0xFF:	#exit from program press q
			break

	cap.release()
	cv2.destroyAllWindows()
	alarm_thread.terminate()
	sms_thread.terminate()
	smtp_thread.terminate()
	alarm_thread.join()
	smtp_thread.join()
	sms_thread.join()
