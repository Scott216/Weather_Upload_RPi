# Uses Moteino to get wireless weather data from Davis ISS weather station
# and sends it to Weather Underground
# Git Repo: https://github.com/Scott216/Weather_Upload_RPi



# To Do:
# Get Pressure sensor and connect to RPi instead of getting pressure from another station
# Cron jobs
#   - Start weather station on bootup
#   - Reboot RPi if weather station program stops 
# If WU_download.getDailyRain() fails on startup, then read the rain from the log file
# Error exception  handling for twilio SMS
# Weekly status text like you do with water leak detector



# Change Log
# 11/28/18 v1.00 - Initial RPi version
# 12/27/18 v1.01 - Changed I/O pins
# 12/31/18 v1.02 - Added packet printout in hex to data table
# 01/01/19 v1.03 - Removed Cap voltage from printout.  Fixed wind gust error in URL
# 01/02/19 v1.04 - changed WU upload timing. Added wind direction logging.  Added I2C error counter
# 01/03/19 v1.05 - Fixed bug in avgWindDir(), didn't have "self" infront of the arrays
# 01/03/19 v1.06 - Removed wind direction logging.  Added comments
# 01/04/19 v1.07 - Added timeout and error handling in WU_upload.py and WU_download.py.  Couple other small bug fixes
# 01/05/19 v1.08 - Added current wind dir and data type (from packet header) to printout.
#                  In weatherData.cls.py added gotHumidityData() and gotTemperatureData() to gotDewPointData() 
#                  Doesn't upload any data until RPi has temperature and R/H and can calculate dewpoint
# 01/06/19 v1.09 - Moved new day reset to main loop
# 01/06/19 v1.10 - Used .format() with getUrl string in WU_download.py. Changed primary station for getting pressure data
# 01/07/19 v1.11 - Changed pressure upload so it would return last valid pressure instead of nothing. WU treats no data as zero
# 01/21/19 v1.12 - In WU_decodeWirelessData.py, fixed temperature() to return negative numbers properly
# 02/02/19 v1.13 - Added wind chill, removed dewPointLocal()
# 02/11/19 v1.14 - Switched from test station to Suntec station
# 02/17/19 v1.15 - Changed timeout in WU_download.py from 5 to 10
# 02/18/19 v1.16 - Changed except errors in WU_Upload.py and changed timeout from 5 to 30
# 04/23/19 v1.17 - Can't get pressure from other weather stations because Weather Underground turned off their API. Removed code that grabs pressure
# 04/24/19 v1.18 - Updated WU_download.getDailyRain() and getPressure() to work with new API.  Got new API key and updated WU_credentials.py
# 10/13/20 v1.19 - in WU_download.py I changed download station KVTDOVER7 (Mt Snow base) to KVTDOVER19 becuase DVTDOVER7 is offline.
#                  Changed KVTDOVER8 to KVTDOVER25. In startup, added suntec.rainToday = 0 if error in getting rain.
#                  Changed  gotRainTodayData() to check >= zero instead of NO_DATA_YET
#                  Installed Adafruit BME280 module: "sudo pip3 install Adafruit_BME280"
# 10/14/20 v1.20 - Added time since last successful upload output when upload fails
# 10/15/20 v1.21 - Added code to reset Moteino if I2C errors reach 50
# 10/16/20 v1.22 - Fixed bug in resetting Moteino when I2C is high.  Added option to select whether to print raw data or not
# 10/19/20 v1.23 - Removed some debugging code.  Moved startup section next to main.  Added I2C consecutive error counter.
#                  Added resetMoteino() to startup section.
# 10/20/20 v1.24 - Write data to a log file.  Changed timing of getPressure to every hour. I think I'm hitting WU limits.  Also changed
#                  WU upload from 10 to 60 seconds.
# 10/21/20 v1.25 - Redid log files do new file is created every day, one for weather data and one for errors
# 10/22/20 v1.26 - Redid upload2WU() and getDailyRain() so they return a list so that error message can be sent back to main program
# 11/02/20 v1.27 - Redid error tracking so output is to log is in a table format
# 11/03/20 v1.28 - Fixed  bug in print(), removed several calls to logfile()
# 11/09/20 v1.29 - Added code to give more detail about what's going on when nothing is being sent to W/U
# 11/10/20 v1.30 - Added g_NewISSDataTimeStamp.  There's a problem where weather station data is getting to Moteino,
#                  but it's unchanged.  That's not what's really happening, I'm not sure what's going on.  This timestamp will be
#                  used to reset Moteino
# 11/15/20 v1.31 - Added SMS text with Twilio.  Send text if there's no uploads for 30 minutes.  Only do once day.
#                  Change decodeRawData() to return a list 0: T/F of decode success, 1: error message
# 12/14/20 v1.32 - Moved statemate that prints SMS to console ahead of twilio code in case twilio code crashes.  Changed detail log format, put ISS data at the end
# 02/18/21 v1.33 - Moved log files to USB thumb drive
# 02/27/21 v1.34 - Changed path for Deatal Log
# 07/07/21 v1.35 - Added g_SMS_Offline_Msg_Sent to prevent multiple SMS messages sent when weather station is offline
# 09/26/21 v1.36 - Turned off logging.  I think USB drives have issues
# 10/29/21 v1.37 - Fixed typo in line 254, Variable was datasent, should have been dataSent (with capital S)
# 10/08/22 v1.38 - Fixed bug where sometimes rain rate would be 36, this happened when rain seconds was 1. Don't know why it would ever be this, but sometimes it was.
#                  now rain seconds has to be > 10 for a valid calculation
# 03/01/23 v1.39 - Added code to get and print public IP address on startup.

version = "v1.39"

import time
import smbus  # Used by I2C
import os.path # used to see if a file exist
import math # Used by humidity calculation
import adafruit_bme280  # https://github.com/adafruit/Adafruit_BME280_Library, to install: "sudo pip3 install adafruit-circuitpython-bme280"
import RPi.GPIO as GPIO # reads/writes GPIO pins
import WU_credentials # Weather underground password, API key and station IDs
import WU_download  # downloads daily rain on startup, and pressure from other weather staitons
import WU_upload  # uploads data to Weather Underground
import WU_decodeWirelessData # Decodes wireless data coming from Davis ISS weather station
import weatherData_cls # class to hold weather data for the Davis ISS station
from subprocess import check_output # used to print RPi IP address
from twilio.rest import Client  # https://pypi.org/project/twilio
from twilio.base.exceptions import TwilioRestException
import requests # used to get public IP address   Ref: https://stackoverflow.com/questions/61347442/how-can-i-find-my-ip-address-with-python-not-local-ip



I2C_ADDRESS = 0x04 # I2C address of Moteino
ISS_STATION_ID = 1
WU_STATION = WU_credentials.WU_STATION_ID_SUNTEC # Main weather station
# WU_STATION = WU_credentials.WU_STATION_ID_TEST # Test weather station

# Instantiate suntec object from weatherStation class (weatherData_cls.py)
suntec = weatherData_cls.weatherStation(ISS_STATION_ID)

# Header byte 0, 4 MSB describe data in bytes 3-4
ISS_CAP_VOLTS    = 0x2
ISS_UV_INDEX     = 0x4
ISS_RAIN_SECONDS = 0x5
ISS_SOLAR_RAD    = 0x6
ISS_OUT_TEMP     = 0x8
ISS_WIND_GUST    = 0x9
ISS_HUMIDITY     = 0xA
ISS_RAIN_COUNT   = 0xE

# GPIO pins, these are board # pins, not BCM pin
MOTEINO_HEARTBEAT_PIN     = 18  # Input pin connected to Moteino heartbeat output. (BCM 24)
MOTEINO_READY_PIN         = 33  # Input pin connected to Moteino output pin that signals Moteino is ready to send data to RPi.  (BDM 13)
MOTEINO_RESET_PIN         = 36  # Output pin connected to Moteino Reset pin (BCM 16)


#---------------------------------------------------------------------
# Validate weather data from wireless packet
# Returns a list
#  0: True/False if successfule
#  1: error message
#---------------------------------------------------------------------
def decodeRawData(packet):
    # check CRC
    if (WU_decodeWirelessData.crc16_ccitt(packet) == False):
        errmsg = "Invalid CRC {0[6]}, {0[7]}".format(packet) 
        return[False, errmsg] # CRC Failed, stop processing packet

    # Check station ID, don't want to get data from another nearby station
    packetStationID = WU_decodeWirelessData.stationID(packet)
    if (packetStationID != suntec.stationID):
        errmsg = 'Wrong station ID.  Expected {} but got{}'.format(suntec.stationID, packetStationID) 
        return[False, errmsg] # wrong station ID, stop processing packet
    
    # CRC passed and staion ID okay, extract weather data from packet

    # Wind speed is in every packet
    newWindSpeed = WU_decodeWirelessData.windSpeed(packet)
    if (newWindSpeed >= 0):
        suntec.windSpeed = newWindSpeed
    else:
        errmsg = 'Error exrtacting wind speed from packet. Got {} from {}'.format(newWindSpeed, packet) 
        suntec.windSpeed  = 0
        return[False, errmsg] # error extracing wind speed, stop processing packet
    
    # Wind direction is in every packet
    newWindDir = WU_decodeWirelessData.windDirection(packet)
    if (newWindDir >= 0):
        suntec.windDir = newWindDir
        suntec.avgWindDir(newWindDir)
    else:
        errmsg = 'Error exrtacting wind direction from packet. Got {} from {}'.format(newWindDir, packet) 
        return[False, errmsg] # Error extracing wind direction, stop processing packet
     
    dataSent = packet[0] >> 4 # From header byte 0, determine what data has been sent, then decode appropriate data below

    # Returns rain bucket tip counter.  1 count = 0.01".  Counter rolls over at 127
    if (dataSent == ISS_RAIN_COUNT):
        global g_rainCounterOld  # convert from local to global variable
        global g_rainCntDataPts  # convert from local to global variable
        
        rainCounterNew = WU_decodeWirelessData.rainCounter(packet)
        if (rainCounterNew < 0 or rainCounterNew > 127):
            errmsg = 'Invalid rain counter value:{} from {}'.format(rainCounterNew, packet) 
            return[False, errmsg] # Invalid rain counter value
        
        # Don't calculate rain counts until program has received 2nd data point.  First data point will be the
        # starting value, then 2nd data point will be the accumulation, if any.  For example, if first time
        # data arrives its 50, we don't want to take 50-0 = 50 (ie 0.5") and add that to the daily rain accumulation.
        # Wait until the next data point comes in, which will probably be 50 (in this example), so 50-50 = 0.  No rain accumulated.
        # If it's raining at the time of reboot, you might get 51, so 51 - 50 = 1 or 0.01" added.
        if (g_rainCntDataPts == 1):
            g_rainCounterOld = rainCounterNew
            
        if ( (g_rainCntDataPts >= 2) and (g_rainCounterOld != rainCounterNew) ):

            # See how many bucket tips counter went up.  Should be only one unless it's 
            # raining really hard or there is a long transmission delay from ISS
            if (rainCounterNew < g_rainCounterOld):
                newRain = (128 - g_rainCounterOld) + rainCounterNew # Rain counter has rolled over (counts from 0 - 127)
            else:
                newRain = rainCounterNew - g_rainCounterOld
            
            suntec.rainToday += newRain/100.0;  # Increment daily rain counter
            g_rainCounterOld = rainCounterNew
                
        g_rainCntDataPts += 1 # Increment number times RPi received rain count data

        return[True, "rain count"]
        
    # Returns rain rate in inches per hour
    if (dataSent == ISS_RAIN_SECONDS):
        rainSeconds = WU_decodeWirelessData.rainRate(packet) # seconds between bucket tips, 0.01" per tip
        fifteenMin = 60 * 15 # seconds in 15 minutes
        if (rainSeconds > 10): # If no error 
            if (rainSeconds < fifteenMin):
                suntec.rainRate = (0.01 * 3600.0) / rainSeconds
            else:
                suntec.rainRate = 0.0 # More then 15 minutes since last bucket tip, can't calculate rain rate until next bucket tip
            return[True, "rain rate"]
        errmsg = 'Invalid rain seconds. Got {} from {}'.format(rainSeconds, packet) 
        return[False, errmsg]
    
    # Returns temperature F
    if (dataSent == ISS_OUT_TEMP):
        newTemp = WU_decodeWirelessData.temperature(packet)
        if (newTemp > -100): #If no error
            suntec.outsideTemp = newTemp
            suntec.calcWindChill() # calculate windchill
            # If we have R/H too, then calculate dew point
            if (suntec.gotHumidityData() == True):
                newDewPoint = suntec.calcDewPoint() # Calculate dew point
                if (newDewPoint <= -100): 
                    errmsg = 'Invalid dewpoint: {} from temp={} and humidity={}'.format(newDewPoint, suntec.outsideTemp, suntec.humidity) 
            return[True, "Temperature"]
        else:
            errmsg = 'Invalid temperature. Got {} from {}'.format(newTemp, packet) 
            return[False, errmsg]
    
    # Returns wind gusts in MPH
    if (dataSent == ISS_WIND_GUST):
        newWindGust = WU_decodeWirelessData.windGusts(packet)
        if newWindGust >= 0:
            suntec.windGust = newWindGust
            return[True, "Wind Gust"]
        errmsg = 'Invalid wind gust. Got {} from {}'.format(newWindGuest, packet) 
        return[False, errmsg]
    
    # Returns relative humidity
    if (dataSent == ISS_HUMIDITY):
        newHumidity = WU_decodeWirelessData.humidity(packet)
        if (newHumidity > 0):
            suntec.humidity = newHumidity
            # If we have outside temperature too, then calculate dew point
            if (suntec.gotTemperatureData() == True):
                newDewPoint = suntec.calcDewPoint() # Calculate dew point
                if (newDewPoint <= -100):
                    errmsg = 'Invalid dewpoint: {} from temp={} and humidity={}'.format(newDewPoint, suntec.outsideTemp, suntec.humidity) 
                    print(errmsg)

            return[True, "Humidity"]
        errmsg = 'Invalid humidity. Got {} from {}'.format(newHumidity, packet) 
        return[False, errmsg]

    # Returns capicator voltage
    if (dataSent == ISS_CAP_VOLTS):
        newCapVolts = WU_decodeWirelessData.capVoltage(packet)
        if (newCapVolts >= 0):
            suntec.capacitorVolts = newCapVolts
            return[True, "Cap volts"]
        else:
            errmsg = 'Invalid cap volts.  Got {} from {}'.format(newCapVolts, packet) 
            suntec.capacitorVolts = -1
            return[False, errmsg]

    # Returns relative UV Index
    if (dataSent == ISS_UV_INDEX):
        return[True, "UV Index"]

    # Returns relative Solar Radiation
    if (dataSent == ISS_SOLAR_RAD):
        return[True, "Solar Radiation"]

    # If it makes it here, there's an if() missing for datatype. 
    return[False, "{}  {}".format("Missing if() statement for byte header:", dataSent)]    


#---------------------------------------------------------------------
# Get Pressure from BME280 sensor
#---------------------------------------------------------------------
def getAtmosphericPressure():
# Create BME280 object
    
# Adafruit Github code
#  https://github.com/adafruit/Adafruit_IO_Python/blob/master/examples/basics/environmental_monitor.py
    bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c_bus)
    bme280.sea_level_pressure = 1013.25
# Read BME280 pressure
    suntec.pressure = bme280.pressure


#---------------------------------------------------------------------
# Prints uploaded weather data
#---------------------------------------------------------------------
def printWeatherDataTable(printRawData=None):

    global g_TableHeaderCntr1
    dataType = ["0x0", "0x1", "Super Cap", "0x3", "UV Index", "Rain Seconds", "Solar Radiation", "Solar Cell Volts", \
                "Temperature", "Gusts", "Humidity", "0xB", "0xC", "0xD", "Rain Counter", "0xF"]
    
    windDirNow = (g_rawDataNew[2] * 1.40625) + 0.3
    
    strHeader =  'temp\tR/H\tpres\twind\tgust\t dir\tavg\trrate\ttoday\t dew\ttime stamp'
    strSummary = '{0.outsideTemp}\t{0.humidity}\t{0.pressure}\t {0.windSpeed}\t {0.windGust}\t {1:03.0f}\t{0.windDir:03.0f}\t{0.rainRate:.2f}\t{0.rainToday:.2f}\t {0.dewPoint:.2f}\t' \
                 .format(suntec, windDirNow) + time.strftime("%m/%d/%Y %I:%M:%S %p")

    if (printRawData == True):
        strHeader = strHeader + '\t\t raw wireless data'
        strSummary = strSummary + "   " + ''.join(['%02x ' %b for b in g_rawDataNew]) + "("  + dataType[g_rawDataNew[0] >> 4] + ")"
    
    if (g_TableHeaderCntr1 == 0):
        print(strHeader)
        g_TableHeaderCntr1 = 20 # reset header counter
    print(strSummary)
    
    g_TableHeaderCntr1 -= 1

    logFile(False, "Data", strSummary) # append data (first param False if append vs. write) to log file



#---------------------------------------------------------------------
# Create or append log files: weather data and errors
# newFile = True, then a new file will be created;'w' parameter in open()).  This would be at
# midnight every day, and sometimes when program is restarted.
# If newFile = False, then data should be appended to existing file; 'a" parameter in open().
#
# logType is eather "Data" or "Error"
#
# logData is data to be appended to the log file
#---------------------------------------------------------------------
def logFile(newFile, logType, logData):

    return(False) # SRG added 9/26/21 so there would be no logging

    datafilename =  "/media/pi/WEATHERDATA/Upload Data_" + time.strftime("%y%m%d") + ".txt"
    errorfilename = "/media/pi/WEATHERDATA/Error log_"   + time.strftime("%y%m%d") + ".txt"
    

    if (newFile == True):
        # Create new data log file
        if not os.path.exists(datafilename):
            # If data log doesn't exist, create it and add header
            datalog = open(datafilename, "w")
            strHeader =  "temp\tR/H\tpres\twind\tgust\t dir\tavg\trrate\ttoday\t dew\ttime stamp\n"
            datalog.write(strHeader)
            datalog.close()             
            
        # Create new error log file
        if not os.path.exists(errorfilename):
            # If error log doesn't exist, create it and add header
            errlog = open(errorfilename, "w")
            strErrHeader =  "Uploads\t  HTTP Err\tLast U/L Hrs\tI2C Success\tISS Err\tISS Avg Min\tISS Age\t\ttime stamp\n"
            errlog.write(strErrHeader)
            errlog.close()             

    else: # append data to existing log file
        if(logType == "Data"):
            # log type is data log
            datalog = open(datafilename, "a")
            datalog.write(logData)
            datalog.write('\n') # Add eol character
            datalog.close()             

        else: # log type is error log
            errlog = open(errorfilename, "a")
            errlog.write(logData)
            errlog.write(time.strftime("%m/%d/%Y %I:%M:%S %p\n"))  # Add timestamp and eol character
            errlog.close()             
        

#---------------------------------------------------------------------
# Log stats every minute if data isn't being uploaded to W/U
##  - moteino ready
##  - moteino min since last Rx
##  - moteino heartbeat
##  - got dewpoint
##  - last W/U upload (min)
##  - Perf Status
##    - WU Uploads
##    - HTTP Failes
##    - Upload timestamp
##    - I2C Success
##    - I2C Fail
##    - ISS Fail
##    - ISS Success
#---------------------------------------------------------------------
detailStatTimer = time.time() + 60  # global variable to print logFileDetail every minute if no w/u uploads
def logFileDetail():

    moteinoTimer = round(time.time() - g_tmr_Moteino, 2)
    lastUploadMin = round((time.time() - perfStats[STAT_UPLOAD_TIMESTAMP])/20,2)  # minutes since last W/U upload
    minSinceLastNewISSData = (time.time() - perfStats[STAT_NEW_ISS_TIMESTAMP])/60
##    detailLogData = [g_moteinoReady,
##                     moteinoTimer,
##                     isHeartbeatOK(),
##                     suntec.gotDewPointData(),
##                     lastUploadMin,
##                     minSinceLastNewISSData,
##                     perfStats]
##    print("{}  {}".format(detailLogData, time.strftime("%m/%d/%Y %I:%M:%S %p")))

    detailLogOutput = "{}\t{}\t{}\t{}\t{}\t{:0.1f}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}".format(
                                   g_moteinoReady,
                                   moteinoTimer,
                                   isHeartbeatOK(),
                                   suntec.gotDewPointData(),
                                   lastUploadMin,
                                   minSinceLastNewISSData,
                                   perfStats[STAT_UPLOADS],
                                   perfStats[STAT_HTTP_FAIL],
                                   perfStats[STAT_I2C_SUCCESS],
                                   perfStats[STAT_I2C_FAIL],
                                   perfStats[STAT_ISS_SUCCESS],
                                   perfStats[STAT_ISS_FAIL],
                                   time.strftime("%m/%d/%Y %I:%M:%S %p"),
                                   g_rawDataNew
                                )
    print(detailLogOutput)

##  SRG disabled logging 9/26/21
##    detailErrFilename = "/media/pi/WEATHERDATA/Detail Error log.txt"
##    detErrlog = open(detailErrFilename, "a")
##    detErrlog.write(detailLogOutput)
##    detErrlog.write('\n')    
##    detErrlog.close()


#---------------------------------------------------------------------
# Prints wireless packet data
#---------------------------------------------------------------------
def printWirelessData():

    wirelessData =  ''.join(['%02x ' %b for b in g_rawDataNew])
    print(wirelessData)

#------------------------------------------------------------------
# Send SMS via Twilio
#------------------------------------------------------------------
def sendSMS(sms_msg):

    print("About to send SMS message: {}".format(sms_msg))

    try:
        smsclient = Client(WU_credentials.TWILIO_ACCOUNT_SID, WU_credentials.TWILIO_AUTH_TOKEN)
        message = smsclient.messages.create(body=sms_msg, from_=WU_credentials.TWILIO_PHONE, to=WU_credentials.TO_PHONE)
    except TwilioRestException as smserr:
        print("Twilio SMS failed: {}".format(smserr))

    g_SMS_Sent_Today = True
    time.sleep(3)  # In case there are more than 1 message close together, don't send to quickly
    

#---------------------------------------------------------------------
# Checks Moteino heartbeat
#---------------------------------------------------------------------
def isHeartbeatOK():

    global g_heartbeatNew
    global g_heartbeatOld
    global g_lastHeartbeatTime
    global MOTEINO_HEARTBEAT_PIN
    heartbeat_timeout = 5 * 60 # set timeout to 5 minutes
    
    
    #check Moteino heartbeat ouput to see if Moteino is still running
    g_heartbeatNew = GPIO.input(MOTEINO_HEARTBEAT_PIN)
    if (g_heartbeatNew != g_heartbeatOld):
        # Heartbeat has changed state
        g_heartbeatOld = g_heartbeatNew
        g_lastHeartbeatTime = time.time()
        return(True)
    else:
        # See how long it's been since the last heartbeat
        heartbeatAge = time.time() - g_lastHeartbeatTime
        if heartbeatAge > heartbeat_timeout:
            errMsg = "No Moteino heartbeat, will reset Moteino"
            print("{}  {}".format(errMsg,time.strftime("%m/%d/%Y %I:%M:%S %p")))
            resetMoteino() # Moteino has locked up, need to reset it
            return(False)
        else:
            # Heartbeat hasn't timed out yet
            return(True)

#---------------------------------------------------------------------
# Reset Moteino, used when no heartbeat is detected or hasn't received any new data
#---------------------------------------------------------------------
def resetMoteino():

    global MOTEINO_RESET_PIN

    # Reset Moteino by by grounding it's reset pin momentarily
    GPIO.output(MOTEINO_RESET_PIN, 0) # Ground the pin to reset Moteino
    time.sleep(2)
    GPIO.output(MOTEINO_RESET_PIN, 1) # Return pin to high state
    time.sleep(10) # give moteino time to reboot
    return(True)


#---------------------------------------------------------------------
# Start up 
#---------------------------------------------------------------------
IP = check_output(['hostname', '-I'])
IP = IP.rstrip()  # strips off eol characters
IP = IP.decode('utf-8') # removes b' previx
print("RPi IP Address: {}".format(IP)) 
print("Ver: {}    {}".format(version, time.strftime("%m/%d/%Y %I:%M:%S %p")))
public_IP = requests.get("http://wtfismyip.com/text").text
print("Suntec public IP: {}".format(public_IP)) 

sendSMS("Weather Station Restarted. \nPublic IP: " + public_IP)
g_SMS_Sent_Today = False

# Create log files for data and errors, First Param = True means to create a new file, vs append to a file
logFile(True, "Data",   "")
logFile(True, "Errors", "")


# Set to zero, weatherStation class initially sets these to -100 for No Data yet
suntec.windGust =  0.0
suntec.rainToday = 0.0

# Get daily rain data from weather station
newRainToday = WU_download.getDailyRain()  # getDailyRain returns a list [0] = success/failure, [1] error message
if newRainToday[0] >= 0:
    print('Suntec station daily rain={}'.format(newRainToday[0]))
    suntec.rainToday = newRainToday[0]
else:
    errMsg = "getDailyRain() error:"
    print("{} {}    {}".format(errMsg, newRainToday[1], time.strftime("%m/%d/%Y %I:%M:%S %p")))
    

i2c_bus = smbus.SMBus(1)  # for I2C

# Get pressure from other nearby weather stations
newPressure = WU_download.getPressure()
if newPressure > 25:
   suntec.pressure = newPressure
else:
   errMsg = "Error getting pressure data on startup"
   print("{}  {}".format(errMsg,time.strftime("%m/%d/%Y %I:%M:%S %p")))



# Setup GPIO using Board numbering (vs BCM numbering)
GPIO.setmode(GPIO.BOARD)

# Setup pin as input with pull-down resistor
GPIO.setwarnings(False) 
GPIO.setup(MOTEINO_HEARTBEAT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(MOTEINO_READY_PIN,     GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(MOTEINO_RESET_PIN,     GPIO.OUT)
GPIO.output(MOTEINO_RESET_PIN, 1) # set pin high. Moteino resets when it's pin is grounded

resetMoteino()

g_heartbeatNew = GPIO.input(MOTEINO_HEARTBEAT_PIN)
g_heartbeatOld = g_heartbeatNew
g_lastHeartbeatTime = time.time() 
g_moteinoReady = False # Monitors GPIO pin to see when Moteino is ready to send data to RPi
g_NewISSDataTimeStamp = time.time() + (60 * 10) # Timestamp when last NEW ISS data came in. Default to 10 min from startup 
g_SMS_Sent_Today = False  # flag so SMS is only sent once a day
g_SMS_Offline_Msg_Sent = False # flag so SMS is offline message is only sent once
g_rainCounterOld = 0   # Previous value of rain counter, used in def decodeRawData()
g_rainCntDataPts = 0   # Counts the times RPi has received rain counter data, this is not the actual rain counter, thats g_rainCounterOld and rainCounterNew
g_rawDataNew = [0.0] * 8 # Initialize rawData list. This is weather data that's sent from Moteino
g_TableHeaderCntr1 = 0 # Used to print header for weather data summary every so often
g_i2cDailyErrors = 0 # Daily counter for I2C errors
g_uploadFreqWU = 60 # Seconds between uploads to Weather Underground
g_oldDayOfMonth = int(time.strftime("%d"))   # Initialize day of month variable, used to detect when new day starts
g_tmr_Moteino = time.time()  # Used to request data from moteino every second
tmr_upload = time.time()     # Initialize timer to trigger when to upload to Weather Underground
hourTimer = time.time() + 3600


# List positions for perfStats[] list
STAT_UPLOADS = 0           # 0 - W/U Uploads in last hour
STAT_HTTP_FAIL = 1         # 1 - W/U HTTP failures in last hour
STAT_UPLOAD_TIMESTAMP = 2  # 2 - Timestamp of last successful W/U upload - does not reset every hour
STAT_I2C_SUCCESS = 3       # 3 - I2C success in last hour
STAT_I2C_FAIL = 4          # 4 - I2C failures in last hour
STAT_ISS_FAIL = 5          # 5 - ISS Packet decode errors in last hour
STAT_ISS_SUCCESS = 6       # 6 - Average time (seconds) to receive ISS packet in last hour
STAT_NEW_ISS_TIMESTAMP = 7 # 7 - Timestamp of last time received NEW weather data.  Not reset every hour. This seems to be the main problem when uploads stop - Moteino keeps sending the same packet 
perfStats = [0,0,time.time(),0,0,0,0,time.time()]  # list to hold performance stats



# Only use this until you get pressure sensor installed
tmr_hourly_pressure = time.time() + 3600


#---------------------------------------------------------------------
# Main loop
#---------------------------------------------------------------------
while True:

    # Moteino will set output pin high when it wants to send data to RPi
    if(GPIO.input(MOTEINO_READY_PIN) == 1):
        g_moteinoReady = True
    else:
        g_moteinoReady = False
        
    
    decodeStatus = [False, ""] # Reset status. decodeStatus[1] is an errmsg
    
    if (g_moteinoReady and (time.time() > g_tmr_Moteino) and isHeartbeatOK()): 
        g_tmr_Moteino = time.time() + 1 # add 1 second to Moteino timer, this is used so Moteino is only queried once a second
        
        # Copy previously recieved raw data into separate list so it can be compared to new data coming in to see if it changed
        rawDataOld = list(g_rawDataNew)

        # Get new data from Moteino
        # Exception handler for: OSError: [Errno 5] Input/output error. This occures when Moteino is rebooted
        try:
            g_rawDataNew = i2c_bus.read_i2c_block_data(I2C_ADDRESS, 0, 8)  # Get data from Moteino, 0 byte offset, get 8 bytes
            perfStats[STAT_I2C_SUCCESS] += 1 

            if (g_rawDataNew != rawDataOld): # See if new data has changed
                perfStats[STAT_NEW_ISS_TIMESTAMP] = time.time()
                g_NewISSDataTimeStamp = time.time()
                decodeStatus = decodeRawData(g_rawDataNew) # Send packet to decodeRawData() for decoding
                if (decodeStatus[0] == False):
                    print("{}   {}".format(decodeStatus[1], time.strftime("%m/%d/%Y %I:%M:%S %p")))
                    perfStats[STAT_ISS_FAIL] += 1
                else:
                    perfStats[STAT_ISS_SUCCESS] += 1

        except OSError:  # Got an I2C error
            perfStats[STAT_I2C_FAIL] += 1
            g_i2cDailyErrors += 1

    # If it's a new day, reset daily rain accumulation, I2C Error counter, and SMS flags
    newDayOfMonth = int(time.strftime("%d"))
    if newDayOfMonth != g_oldDayOfMonth:
        suntec.rainToday = 0.0
        g_oldDayOfMonth = newDayOfMonth
        g_i2cDailyErrors = 0
        g_SMS_Sent_Today = False
        g_SMS_Offline_Msg_Sent = False

        # Create new log files for data and errors, First Param = True means to create a new file (False means append to file)
        logFile(True, "Data",   "")
        logFile(True, "Errors", "")


#  get pressure from other W/U stations once an hour, once you get BME280 sensor installed, you can get it more frequently
    if (time.time() > tmr_hourly_pressure):
        newPressure = WU_download.getPressure() # Get latest pressure from local weather station
        tmr_hourly_pressure = time.time() + 3600
        if (newPressure > 25):
            suntec.pressure = newPressure


    # If RPi has reecived new valid data from Moteino, and upload timer has passed, and RPi has dewpoint data (note, dewpoint depends on Temp
    # and R/H) then upload new data to Weather Underground
    if ( (suntec.gotDewPointData() == True) and (decodeStatus[0] == True) and (time.time() > tmr_upload) ):
#srg        newPressure = WU_download.getPressure() # get latest pressure from local weather station
#srg        if (newPressure > 25):
#srg            suntec.pressure = newPressure  # if a new valid pressure is retrieved, update data. If not, use current value
        printWeatherDataTable(printRawData=False) # print weather data. printRawData parameter deterrmines if raw ISS hex data is also printed.
        
        uploadStatus = WU_upload.upload2WU(suntec, WU_STATION) # upload2WU() returns a list, [0] is succuss/faulure of upload [1] is error message.  see: https://bit.ly/37y0gAU 
        uploadErrMsg = uploadStatus[1]
        if uploadStatus[0] == True:
            perfStats[STAT_UPLOAD_TIMESTAMP] = time.time()
            tmr_upload = time.time() + g_uploadFreqWU # Set next upload time
            perfStats[STAT_UPLOADS] += 1
        else:
            errMsg = "Error in upload2WU(), {}, Last successful uplaod: {:.1f} minutes ago   {}". \
                     format(uploadErrMsg, (time.time() - perfStats[STAT_UPLOAD_TIMESTAMP])/60, time.strftime("%m/%d/%Y %I:%M:%S %p"))
            print(errMsg)
            perfStats[STAT_HTTP_FAIL] += 1

    # if no upload to W/U for at least 5 min (300 seconds), then print detail data every minute
    if ( (time.time() > detailStatTimer) and ((time.time() - perfStats[STAT_UPLOAD_TIMESTAMP]) > 300)):
        logFileDetail()
        detailStatTimer = time.time() + 60 # reset timer

    # if no upload to W/U for at least 30 min send SMS message
    if ( (time.time() - perfStats[STAT_UPLOAD_TIMESTAMP]) > (60 * 30) and (g_SMS_Sent_Today == False) and (g_SMS_Offline_Msg_Sent == False)):
        sendSMS("Weather Station is offline")
        g_SMS_Offline_Msg_Sent = True


    # Reset Moteino after every 200 I2C errors 
    if ( (g_i2cDailyErrors % 200 == 0) and (g_i2cDailyErrors > 0) ):
        print("High I2C errors:{}.  Resetting Moteino  {}".format(g_i2cDailyErrors,time.strftime("%m/%d/%Y %I:%M:%S %p")))
        g_i2cDailyErrors += 1   #  add 1 to g_i2cDailyErrors so this doesn't run again right away
        resetMoteino()


    # Reset Moteino if no new ISS data has come in for 10 minutes
    if (time.time() > g_NewISSDataTimeStamp + (60 * 10)):
        print("********************************************************************************")
        print("No new ISS data in {:0.1f} minutes; resetting Moteino.   {}".format((time.time() - g_NewISSDataTimeStamp)/60 ,time.strftime("%m/%d/%Y %I:%M:%S %p")))
        print("********************************************************************************")
        g_NewISSDataTimeStamp = time.time() + (60 * 10)   #  add 10 minutes to timer, don't want Moteino resetting again too soon
        resetMoteino()


    # Every hour print and then reset some stats for debugging
    if (time.time() > hourTimer):
        stats = "   {}\t    {}\t\t  {:.2f}\t\t  {:.1f}%\t\t  {}\t  {:.2f}\t\t{:.1f}\t\t".format(perfStats[STAT_UPLOADS], perfStats[STAT_HTTP_FAIL], 
                                                                        (time.time() - perfStats[STAT_UPLOAD_TIMESTAMP])/3600, 
                                                                         perfStats[STAT_I2C_SUCCESS] / (perfStats[STAT_I2C_FAIL] + perfStats[STAT_I2C_SUCCESS]) * 100, 
                                                                         perfStats[STAT_ISS_FAIL], perfStats[STAT_ISS_SUCCESS]/3600,
                                                                         (time.time() - perfStats[STAT_NEW_ISS_TIMESTAMP])/60 )  
        logFile(False, "Error", stats)

        # Reset hourly stats
        perfStats[STAT_UPLOADS] = 0
        perfStats[STAT_HTTP_FAIL] = 0
        perfStats[STAT_I2C_SUCCESS] = 0
        perfStats[STAT_I2C_FAIL] = 0
        perfStats[STAT_ISS_FAIL] = 0
        perfStats[STAT_ISS_SUCCESS] = 0
        hourTimer = time.time() + 3600
       

GPIO.cleanup() # Used when exiting a program to reset the pins

