# Decode Davis Weather Station data from wireless ISS weather station

# MSB in first byte that dictates what data is sent in bytes 3-4
ISS_CAP_VOLTS    = 0x2
ISS_UV_INDEX     = 0x4
ISS_RAIN_SECONDS = 0x5
ISS_SOLAR_RAD    = 0x6
ISS_OUT_TEMP     = 0x8
ISS_WIND_GUST    = 0x9
ISS_HUMIDITY     = 0xA
ISS_RAIN_COUNT   = 0xE

SENSOR_OFFLINE   = 0xFF

# Error message values
ERR_WRONG_PACKET = -100
ERR_OUT_OF_RANGE = -101
ERR_INVALID_DATA = -102


# ---------------------------------------------------------------------------------------------
# Davis station ID
# In header byte, bits 0-2 determine station ID
def stationID(rawData):
    ID = rawData[0] & 0x7
    ID += 1 # Davis station IDs start at 1, in the raw data, they start at 0.  Add 1 to return the actual ID
    return(ID)


# ---------------------------------------------------------------------------------------------
# Battery status is bit 3 in header 
def batteryStatus(rawData):
    bat = (rawData[0] & 8) >> 3
    return(bat)


# ---------------------------------------------------------------------------------------------
# Seconds between bucket tips, used to calculate rain rate in inches per hour
# Goes up to 15 minutes/900 seconds (I think).
# Data decoding is kind of wonky. The data comes in differently depending on if it's raining hard or not
def rainRate(rawData):
    #Verify packet contains rain rate data
    if (rawData[0] >> 4) != ISS_RAIN_SECONDS:
        return (-100)  ## Wrong packet type - doesn't contain rain rate seconds

    if ( rawData[4] & 0x40 == 0 ):
        rainRateSeconds =  (rawData[3] >> 4) + rawData[4] - 1         # Light rain
    else:
        rainRateSeconds = rawData[3] + ((rawData[4] >> 4) - 4) * 256  # Heavy rain

    if (rainRateSeconds < 0 or rainRateSeconds > 3600): # check for realistic range
        return(ERR_OUT_OF_RANGE)
    
    return(rainRateSeconds)


# ---------------------------------------------------------------------------------------------
# Different formula for rain rate
def rainRate2(rawData):
    # Verify packet contains rain rate data
    if (rawData[0] >> 4) != ISS_RAIN_SECONDS:
        return (ERR_WRONG_PACKET)  # Wrong packet type - doesn't contain rain rate seconds

    if ( rawData[4] & 0x40 == 0 ):
        rainRateSeconds =  ((rawData[4] & 0x30) / 16 * 250) + rawData[3]        # Light Rain
    else:
        rainRateSeconds = (((rawData[4] & 0x30) / 16 * 250) + rawData[3]) / 16  # Heavy Rain

    if (rainRateSeconds < 0 or rainRateSeconds > 3600): # check for realistic range
        return(ERR_OUT_OF_RANGE)

    return(rainRateSeconds)


# ---------------------------------------------------------------------------------------------
# Counter 0-127 that increments each time bucket tips.  Each bucket tip is 0.01"
# Uses first 3 bits of byte 3
def rainCounter(rawData):
    # Verify packet contains rain rate data
    if (rawData[0] >> 4) != ISS_RAIN_COUNT:
        return (ERR_WRONG_PACKET)  # Wrong packet type - doesn't contain rain counter

    rainCntr = rawData[3] & 0x7F # Return first 3 bits of byte 3

    if (rainCntr < 0 or rainCntr > 127): # check for valid range
        return(ERR_OUT_OF_RANGE)
    
    return (rainCntr) 


# ---------------------------------------------------------------------------------------------
# Counter 0-127 that increments each time bucket tips.  Each bucket tip is 0.01"
# This function returns the inches instead of the count
# Uses first 3 bits of byte 3
# ---- NOT USED ---
def rainInch(rawData):
    # Verify packet contains rain rate data
    if (rawData[0] >> 4) != ISS_RAIN_COUNT:
        return (ERR_WRONG_PACKET)  # Wrong packet type - doesn't contain rain counter

    rainCountInch = (rawData[3] & 0x7F) / 100.0 # Counter is first 3 bits

    if (rainCountInch < 0 or rainCountInch > 1.27): # check for valid range
        return(ERR_OUT_OF_RANGE)
    
    return (rainCountInch) 


# ---------------------------------------------------------------------------------------------
# There is a dead zone on the wind vane. No values are reported between 8 and 352 degrees inclusive.
# These values correspond to received byte values of 1 and 255 respectively
# Byte 2 is always wind direction, 
def windDirection(rawData):
    if ( rawData[2] == 0 ):
        return (0)
    else:
        windDir = (rawData[2] * 1.40625) + 0.3

    if (windDir < 0 or windDir > 360):  # check for valid range
        return(ERR_OUT_OF_RANGE)

    return (windDir)


# ---------------------------------------------------------------------------------------------
# Wind speed in MPH is always byte 1
def windSpeed(rawData):

    speed = rawData[1]

    if (speed < 0 or speed > 240): # check for valid range
        return(ERR_OUT_OF_RANGE)
        
    return (speed)


# ---------------------------------------------------------------------------------------------
# Wind is in byte 3, no manipulation needed
def windGusts(rawData):
    # Verify packet contains wind gust data
    if (rawData[0] >> 4) != ISS_WIND_GUST:
        return (ERR_WRONG_PACKET)  # Wrong packet type - doesn't contain wind gust data

    gust = rawData[3]
    if (gust < 0 or gust > 240): # check for valid range
         return(ERR_OUT_OF_RANGE)
        
    return (gust)


# ---------------------------------------------------------------------------------------------
def temperature(rawData):
    # Verify packet contains temperature data
    if (rawData[0] >> 4) != ISS_OUT_TEMP:
        return (ERR_WRONG_PACKET)  # Wrong packet type - doesn't contain temperature data

    outsideTemperature = (rawData[3] * 256 + rawData[4]) >> 4  # Temp F in 1/10 degrees, ie 320 = 32.0F
    outsideTemperature = outsideTemperature / 10.0 # convert from tenths to degrees

    if (outsideTemperature < -100 or outsideTemperature > 130): # check for valid range
        return(ERR_OUT_OF_RANGE)
    
    return(outsideTemperature)


# ---------------------------------------------------------------------------------------------
def humidity(rawData):
    # Verify packet contains humidity data
    if (rawData[0] >> 4) != ISS_HUMIDITY:
        return (ERR_WRONG_PACKET)  # Wrong packet type - doesn't contain humidity data

    rh = ((rawData[4] >> 4) * 256 + rawData[3]) / 10.0

    if (rh < 0 or rh > 100): # check for valid range
        return(ERR_OUT_OF_RANGE)
    
    return (rh)


# ---------------------------------------------------------------------------------------------
# Solar radiation in Watts/Meter^2
def solarRadiation(rawData):
    # Verify packet contains humidity data
    if (rawData[0] >> 4) != ISS_SOLAR_RAD:
        return (ERR_WRONG_PACKET)  # Wrong packet type - doesn't contain solar radiation data

    if ( rawData[3] == SENSOR_OFFLINE ):
        return(0)
    else:
        tt = rawData[3] * 256 + rawData[4]
        tt = tt >> 4
        solarRad = (tt - 4) / 2.27 - 0.2488
        
    if (solarRad < 0 or solarRad > 2000): # check for valid range
        return(ERR_OUT_OF_RANGE)

    return (solarRad)


# ---------------------------------------------------------------------------------------------
def uvIndex(rawData):
    # Verify packet contains humidity data
    if (rawData[0] >> 4) != ISS_UV_INDEX:
        return (ERR_WRONG_PACKET)  # Wrong packet type - doesn't contain UV Index data

    if ( rawData[3] == SENSOR_OFFLINE ):
        return(0)
    else:
        tt = rawData[3] * 256 + rawData[4]
        tt = tt >> 4;
        uvi = (tt-4) / 200.0

    if (uvi < 0 or uvi > 16): # check for valid range
        return(ERR_OUT_OF_RANGE)

    return(uvi)

    
# ---------------------------------------------------------------------------------------------
# The ISS-internal goldcap capacitor - store the energy needed during the night,  Vue only
def capVoltage(rawData):
    # Verify packet contains humidity data
    if (rawData[0] >> 4) != ISS_CAP_VOLTS:
        return (ERR_WRONG_PACKET)  # Wrong packet type - doesn't contain capacitor voltage data

    volts = ((rawData[3] * 4) + ((rawData[4] & 0xC0) / 64.0)) / 100.0

    if (volts < 0 or volts > 10): # check for valid range
        return(ERR_OUT_OF_RANGE)
        
    return (volts)
    

# ---------------------------------------------------------------------------------------------
# CRC check, returns True if CRC matches, False if not
#
# Could also use the crcmod library. See: https://bit.ly/2TgB8VB
# First Method
#    import crcmod
#    crcfun = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0, xorOut=0)
#    result = crcfun(b'\x82\x00\x3a\x0a\x89\x00')
# Second method
#    import crcmod.predefined
#    crc = crcmod.predefined.mkCrcFun('xmodem')
#    result = crc(b'\x82\x00\x3a\x0a\x89\x00')
# or
#    bytestring = "\x82\x00\x3a\x0a\x89\x00"
#    result = crc(bytestring)

def crc16_ccitt(rawData):
    # calculate the crc of the first 6 bytes of data
    crc = 0
    length = 6 # data is in first 6 bytes, crc in last 2
    
    i = 0
    for byteData in rawData:
        if i == length:
            break
        
        crc ^= (byteData << 8)
        i += 1

        k = 0 
        while k < 8:
            k += 1
            if(crc & 0x8000):
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1 
        crc = crc & 0xFFFF  # Makes crc look like unsigned 16-bit integer

    # Extract the CRC from the last 2 bytes of packet
    crcSent = rawData[6] * 256 + rawData[7]

    if (crc == crcSent and crc != 0):
        return (True)
    else:
        return (False)



