# Uses Moteino to get wireless weather data from Davis ISS weather station
# and sends it to Weather Underground
# Git Repo: https://github.com/Scott216/Weather_Upload_RPi



# To Do
# Get Pressure sensor and connect to RPi instead of getting pressure from another station
# Cron jobs
#   - Start weather station on bootup
#   - Reboot RPi if weather station program stops 


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

version = "v1.26"

import time
import smbus  # Used by I2C
import os.path # used to see if a file exist
import math # Used by humidity calculation
import Adafruit_BME280  # https://github.com/adafruit/Adafruit_BME280_Library, to install: "sudo pip3 install Adafruit_BME280"
import RPi.GPIO as GPIO # reads/writes GPIO pins
import WU_credentials # Weather underground password, API key and station IDs
import WU_download  # downloads daily rain on startup, and pressure from other weather staitons
import WU_upload  # uploads data to Weather Underground
import WU_decodeWirelessData # Decodes wireless data coming from Davis ISS weather station
import weatherData_cls # class to hold weather data for the Davis ISS station
from subprocess import check_output # used to print RPi IP address

I2C_ADDRESS = 0x04 # I2C address of Moteino
ISS_STATION_ID = 1
WU_STATION = WU_credentials.WU_STATION_ID_SUNTEC # Main weather station
# WU_STATION = WU_credentials.WU_STATION_ID_TEST # Test weather station

# Instantiate suntec object from weatherStation class (weatherData_cls.py)
suntec = weatherData_cls.weatherStation(ISS_STATION_ID)

# Header byte 0, 4 MSB describe data in bytes 3-4
ISS_CAP_VOLTS    = 0x2
ISS_UV_INDEX     = 0x4d
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
# Decode weather data from wireless packet
#---------------------------------------------------------------------
def decodeRawData(packet):
    # check CRC
    if WU_decodeWirelessData.crc16_ccitt(packet) == False:
        print('Invalid CRC {0[6]}, {0[7]}'.format(packet))
        return(False) # CRC Failed, stop processing packet

    # Check station ID, don't want to get data from another nearby station
    packetStationID = WU_decodeWirelessData.stationID(packet)
    if packetStationID != suntec.stationID:
        print('Wrong station ID.  Expected {} but got{}'.format(suntec.stationID, packetStationID))
        return(False) # wrong station ID, stop processing packet
    
    # CRC passed and staion ID okay, extract weather data from packet

    # Wind speed is in every packet
    newWindSpeed = WU_decodeWirelessData.windSpeed(packet)
    if newWindSpeed >= 0:
        suntec.windSpeed = newWindSpeed
    else:
        print('Error exrtacting wind speed from packet. Got {} from {}'.format(newWindSpeed, packet))
        suntec.windSpeed  = 0
        return(False) # error extracing wind speed, stop processing packet
    
    # Wind direction is in every packet
    newWindDir = WU_decodeWirelessData.windDirection(packet)
    if newWindDir >= 0:
        suntec.windDir = newWindDir
        suntec.avgWindDir(newWindDir)
    else:
        print('Error exrtacting wind direction from packet. Got {} from {}'.format(newWindDir, packet))
        return(False) # Error extracing wind direction, stop processing packet
     
    dataSent = packet[0] >> 4 # From header byte 0, determine what data has been sent, then decode appropriate data below

    # Returns rain bucket tip counter.  1 count = 0.01".  Counter rolls over at 127
    if dataSent == ISS_RAIN_COUNT:
        global g_rainCounterOld
        global g_rainCntDataPts
        
        rainCounterNew = WU_decodeWirelessData.rainCounter(packet)
        if rainCounterNew < 0 or rainCounterNew > 127:
            print('Invalid rain counter value:{} from {}'.format(rainCounterNew, packet))
            return(False) # Invalid rain counter value
        
        # Don't calculate rain counts until RPi has received 2nd data point.  First data point will be the
        # starting value, then 2nd data point will be the accumulation, if any.  For example, if first time
        # data arrives its 50, we don't want to take 50-0 = 50 (ie 0.5") and add that to the daily rain accumulation.
        # Wait until the next data point comes in, which will probably be 50 (in this example), so 50-50 = 0.  No rain accumulated.
        # If it's raining at the time of reboot, you might get 51, so 51 - 50 = 1 or 0.01" added.
        if (g_rainCntDataPts == 1):
            g_rainCounterOld = rainCounterNew
            
        if (g_rainCntDataPts >= 2) and (g_rainCounterOld != rainCounterNew):

            # See how many bucket tips counter went up.  Should be only one unless it's 
            # raining really hard or there is a long transmission delay from ISS
            if (rainCounterNew < g_rainCounterOld):
                newRain = (128 - g_rainCounterOld) + rainCounterNew # Rain counter has rolled over (counts from 0 - 127)
            else:
                newRain = rainCounterNew - g_rainCounterOld
            
            suntec.rainToday += newRain/100.0;  # Increment daily rain counter
            g_rainCounterOld = rainCounterNew
                
        g_rainCntDataPts += 1 # Increment number times RPi received rain count data

        return(True)
        
    # Returns rain rate in inches per hour
    if dataSent == ISS_RAIN_SECONDS:
        rainSeconds = WU_decodeWirelessData.rainRate(packet) # seconds between bucket tips, 0.01" per tip
        fifteenMin = 60 * 15 # seconds in 15 minutes
        if rainSeconds > 0: #If no error
            if (rainSeconds < fifteenMin):
                suntec.rainRate = (0.01 * 3600.0) / rainSeconds
            else:
                suntec.rainRate = 0.0 # More then 15 minutes since last bucket tip, can't calculate rain rate until next bucket tip
            return(True)
        print('Invalid rain seconds. Got {} from {}'.format(rainSeconds, packet))
        return(False)
    
    # Returns temperature F
    if dataSent == ISS_OUT_TEMP:
        newTemp = WU_decodeWirelessData.temperature(packet)
        if newTemp > -100: #If no error
            suntec.outsideTemp = newTemp
            suntec.calcWindChill() # calculate windchill
            # If we have R/H too, then calculate dew point
            if suntec.gotHumidityData():
                newDewPoint = suntec.calcDewPoint() # Calculate dew point
                if (newDewPoint <= -100): 
                    print('Invalid dewpoint: {} from temp={} and humidity={}'.format(newDewPoint, suntec.outsideTemp, suntec.humidity))
            return(True)
        else: 
            print('Invalid temperature. Got {} from {}'.format(newTemp, packet))
            return(False)
    
    # Returns wind gusts in MPH
    if dataSent == ISS_WIND_GUST:
        newWindGust = WU_decodeWirelessData.windGusts(packet)
        if newWindGust >= 0:
            suntec.windGust = newWindGust
            return(True)
        print('Invalid wind gust. Got {} from {}'.format(newWindGuest, packet))
        return(False)
    
    # Returns relative humidity
    if dataSent == ISS_HUMIDITY:
        newHumidity = WU_decodeWirelessData.humidity(packet)
        if newHumidity > 0:
            suntec.humidity = newHumidity
            # If we have outside temperature too, then calculate dew point
            if suntec.gotTemperatureData():
                newDewPoint = suntec.calcDewPoint() # Calculate dew point
                if (newDewPoint <= -100): 
                    print('Invalid dewpoint: {} from temp={} and humidity={}'.format(newDewPoint, suntec.outsideTemp, suntec.humidity))

            return(True)
        print('Invalid humidity. Got {} from {}'.format(newHumidity, packet))
        return(False)

    # Returns capicator voltage
    if dataSent == ISS_CAP_VOLTS:
        newCapVolts = WU_decodeWirelessData.capVoltage(packet)
        if newCapVolts >= 0:
            suntec.capacitorVolts = newCapVolts
            return(True)
        else:
            print('Invalid cap volts.  Got {} from {}'.format(newCapVolts, packet))
            suntec.capacitorVolts = -1
            return(False)


#---------------------------------------------------------------------
# Get Pressure from BME280 sensor
#---------------------------------------------------------------------
def getAtmosphericPressure():
# Create BME280 object

# Adafruit Github code
#  https://github.com/adafruit/Adafruit_IO_Python/blob/master/examples/basics/environmental_monitor.py
    bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
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

    datafilename =  "Logs/Upload Data_" + time.strftime("%y%m%d") + ".txt"
    errorfilename = "Logs/Error log_"   + time.strftime("%y%m%d") + ".txt"

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
            strHeader =  "\n"
            errlog.write(strHeader)
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
            errlog.write(time.strftime("    %m/%d/%Y %I:%M:%S %p\n"))  # Add timestamp and eol character
            errlog.close()             
        
    
#---------------------------------------------------------------------
# Prints wireless packet data
#---------------------------------------------------------------------
def printWirelessData():

    wirelessData =  ''.join(['%02x ' %b for b in g_rawDataNew])
    print(wirelessData)
    

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
            print(errMsg)
            logFile(False, "Error", errMsg)
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
print("RPi IP Address: {}".format(IP)) 
print("Ver: {}    {}".format(version, time.strftime("%m/%d/%Y %I:%M:%S %p")))

# Create log files for data and errors, First Param = True means to create a new file, vs append to a file
logFile(True, "Data",   "")
logFile(True, "Errors", "")


# Set to zero, weatherStation class initially sets these to -100 for No Data yet
suntec.windGust = 0.0
suntec.rainToday = 0.0

# Get daily rain data from weather station
newRainToday = WU_download.getDailyRain()  # getDailyRain returns a list [0] = success/failure, [1] error message
if newRainToday[0] >= 0:
    print('Suntec station daily rain={}'.format(newRainToday[0]))
    suntec.rainToday = newRainToday[0]
else:
    errMsg = "getDailyRain() error: " + newRainToday[1]
    print(errMsg)
    logFile(False, "Error", errMsg)
    

# Get pressure from other nearby weather stations
newPressure = WU_download.getPressure()
if newPressure > 25:
   suntec.pressure = newPressure
else:
   errMsg = "Error getting pressure data on startup"
   print(errMsg)
   logFile(False, "Error", errMsg)

i2c_bus = smbus.SMBus(1)  # for I2C

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

g_rainCounterOld = 0   # Previous value of rain counter, used in def decodeRawData()
g_rainCntDataPts = 0   # Counts the times RPi has received rain counter data, this is not the actual rain counter, thats g_rainCounterOld and rainCounterNew

g_rawDataNew = [0.0] * 8 # Initialize rawData list. This is weather data that's sent from Moteino

g_TableHeaderCntr1 = 0 # Used to print header for weather data summary every so often

g_moteinoReady = False # Monitors GPIO pin to see when Moteino is ready to send data to RPi
g_i2cErrorCnt = 0 # Daily counter for I2C errors

g_uploadFreqWU = 60 # Seconds between uploads to Weather Underground

g_oldDayOfMonth = int(time.strftime("%d"))   # Initialize day of month variable, used to detect when new day starts
g_tmr_Moteino = time.time()  # Used to request data from moteino every second
tmr_upload = time.time()     # Initialize timer to trigger when to upload to Weather Underground
g_uploadSuccessTime = time.time()  # Used to hold timestamp of last successful upload. Setting this to current time so program can calculate
                                   # how ong it takes for first block of data to come in from weather station on startup


# Variables for keeping track of stats per hour
cntUploadSuccess = 0
cntUploadFailures = 0
cntI2CSuccess =    0
cntI2CFailures =   0
hourTimer = time.time() + 3600


# Only use this until you get pressure sensor installed
tmr_hourly_pressure = time.time() + 3600

g_gotNewISSDataTimer = time.time()

#---------------------------------------------------------------------
# Main loop
#---------------------------------------------------------------------
while True:

    # Moteino will set output pin high when it wants to send data to RPi
    if(GPIO.input(MOTEINO_READY_PIN) == 1):
        g_moteinoReady = True
    else:
        g_moteinoReady = False
        
    
    decodeStatus = False # Reset status
    
    if (g_moteinoReady and (time.time() > g_tmr_Moteino) and isHeartbeatOK()): 
        g_tmr_Moteino = time.time() + 1 # add 1 second to Moteino timer, this is used so Moteino is only queried once a second
        
        # Copy previously recieved raw data into separate list so it can be compared to new data coming in to see if it changed
        rawDataOld = list(g_rawDataNew)

        # Get new data from Moteino
        # Exception handler for: OSError: [Errno 5] Input/output error. This occures when Moteino is rebooted
        try:
            g_rawDataNew = i2c_bus.read_i2c_block_data(I2C_ADDRESS, 0, 8)  # Get data from Moteino, 0 byte offset, get 8 bytes
            cntI2CSuccess += 1

            if (g_rawDataNew != rawDataOld): # See if new data has changed
                g_gotNewISSDataTimer = time.time()
                decodeStatus = decodeRawData(g_rawDataNew) # Send packet to decodeRawData() for decoding
                if decodeStatus == False:
                    errMsg = "Error decoding ISS packet data"
                    print(errMsg)
                    logFile(False, "Error", errMsg)


        except OSError:  # Got an I2C error
            g_i2cErrorCnt += 1
            cntI2CFailures += 1
            if (g_i2cErrorCnt % 10 == 0):  # Print every 1o errors 
                errMsg = "I2C Error, errors today: {}".format(g_i2cErrorCnt)
                print("{}   {}".format(errMsg, time.strftime("%m/%d/%Y %I:%M:%S %p")))
                logFile(False, "Error", errMsg)
            time.sleep(5) # Sleep for 5 seconds

            # Reset Moteino after every 200 I2C errors errors
            if (g_i2cErrorCnt % 200 == 0):
                errMsg = "High I2C errors, resetting Moteino"
                print(errMsg)
                logFile(False, "Error", errMsg)
                resetMoteino()

    #if it's a new day, reset daily rain accumulation and I2C Error counter
    newDayOfMonth = int(time.strftime("%d"))
    if newDayOfMonth != g_oldDayOfMonth:
        suntec.rainToday = 0.0
        g_oldDayOfMonth = newDayOfMonth
        g_i2cErrorCnt = 0

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
    if ((suntec.gotDewPointData() == True) and (decodeStatus == True) & (time.time() > tmr_upload)):
#srg        newPressure = WU_download.getPressure() # get latest pressure from local weather station
#srg        if (newPressure > 25):
#srg            suntec.pressure = newPressure  # if a new valid pressure is retrieved, update data. If not, use current value
        printWeatherDataTable(printRawData=False) # print weather data. printRawData parameter deterrmines if raw ISS hex data is also printed.
        
        uploadStatus = WU_upload.upload2WU(suntec, WU_STATION) # upload2WU() returns a list, [0] is succuss/faulure of upload [1] is error message.  see: https://bit.ly/37y0gAU 
        uploadErrMsg = uploadStatus[1]
        if uploadStatus[0] == True:
            g_uploadSuccessTime = time.time()
            tmr_upload = time.time() + g_uploadFreqWU # Set next upload time 
            cntUploadSuccess += 1
        else:
            errMsg = "Error in upload2WU(), " + uploadErrMsg + ", Last successful uplaod: {:.1f} minutes ago".format((time.time() - g_uploadSuccessTime)/60)
            print(errMsg)
            logFile(False, "Error", errMsg)
            cntUploadFailures += 1


    # Every hour print and then reset some stats for debugging
    if (time.time() > hourTimer):
        stats = "\nUpload Successes:{}, Failures: {}; I2C Succeses: {}, Failures:{}\n".format(cntUploadSuccess, cntUploadFailures, cntI2CSuccess, cntI2CFailures)
        print(stats)
        logFile(False, "Error", stats)
        stats = "{:.2f} minutes since weather station sent new data.  Last upload to WU {:.1f} minutes ago".format((time.time() - g_gotNewISSDataTimer)/60, (time.time() - (tmr_upload - g_uploadFreqWU))/60)
        print(stats)
        logFile(False, "Error", stats)

        cntUploadSuccess = 0
        cntUploadFailures = 0
        cntI2CSuccess = 0
        cntI2CFailures = 0
        hourTimer = time.time() + 3600
       

GPIO.cleanup() # Used when exiting a program to reset the pins

