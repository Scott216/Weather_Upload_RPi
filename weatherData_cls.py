# This class holds all the weather data after it's been decoced
# from the ISS Station
# It also has functions to calculate average wind direction and dew point

import math

class weatherStation:

    # class variables
    NO_DATA_YET = -100.0
    AVG_WIND_DIR_NUM_DATA_POINTS = 30

    def __init__(self, stationID): # This function runs when the instance is created

        self.stationID      = stationID # Davis ISS station ID

        # initialize weather data variables
        self.outsideTemp    = weatherStation.NO_DATA_YET
        self.windChill      = weatherStation.NO_DATA_YET
        self.humidity       = weatherStation.NO_DATA_YET
        self.pressure       = weatherStation.NO_DATA_YET
        self.windSpeed      = weatherStation.NO_DATA_YET
        self.windGust       = weatherStation.NO_DATA_YET
        self.windDir        = weatherStation.NO_DATA_YET
        self.rainRate       = weatherStation.NO_DATA_YET
        self.rainToday      = weatherStation.NO_DATA_YET
        self.dewPoint       = weatherStation.NO_DATA_YET
        self.uvIndex        = weatherStation.NO_DATA_YET
        self.solar          = weatherStation.NO_DATA_YET
        self.capacitorVolts = weatherStation.NO_DATA_YET
        self.batteryStatus  = weatherStation.NO_DATA_YET

        # initialize variables for avgWindDir()
        self.c             = 0    # counter
        self.sumNorthSouth = 0.0 
        self.sumEastWest   = 0.0 
        self.northSouth    = [0] * weatherStation.AVG_WIND_DIR_NUM_DATA_POINTS 
        self.eastWest      = [0] * weatherStation.AVG_WIND_DIR_NUM_DATA_POINTS

        
        
    # got...Data() functions return True once good weather data for that variable has been set
    def gotTemperatureData(self):
        return (self.outsideTemp > weatherStation.NO_DATA_YET)

    def gotWindChillData(self):
        return (self.windChill > weatherStation.NO_DATA_YET)
        
    def gotHumidityData(self):
        return (self.humidity > weatherStation.NO_DATA_YET)

    def gotPressureData(self):
        return (self.pressure > weatherStation.NO_DATA_YET)

    def gotWindSpeedData(self):
        return (self.windSpeed > weatherStation.NO_DATA_YET)

    def gotWindGustData(self):
        return (self.windGust > weatherStation.NO_DATA_YET)

    def gotWindDirData(self):
        return (self.windDir > weatherStation.NO_DATA_YET)

    def gotRainRateData(self):
        return (self.rainRate > weatherStation.NO_DATA_YET)

    def gotRainTodayData(self):
        return (self.rainToday > weatherStation.NO_DATA_YET)

    def gotDewPointData(self):
        return ( (self.dewPoint > weatherStation.NO_DATA_YET) and self.gotHumidityData() and self.gotTemperatureData())

    def gotUvIndexData(self):
        return (self.uvIndex > weatherStation.NO_DATA_YET)

    def gotSolarData(self):
        return (self.solar > weatherStation.NO_DATA_YET)

    def gotCapacitorVoltsData(self):
        return (self.capacitorVolts > weatherStation.NO_DATA_YET)

    def gotBatteryStatusData(self):
        return (self.batteryStatus > weatherStation.NO_DATA_YET)

##    # Averages numPoints of wind direction data. When numPoints is reached, data is cleared
##    # out and waits for numPoints of new data before calculating the average again.
##    def avgWindDir(self, windDirNow):
##
##        numPoints = weatherStation.AVG_WIND_DIR_NUM_DATA_POINTS
##        self.c += 1
##     
##        self.sumNorthSouth += math.cos(math.radians(windDirNow))
##        self.sumEastWest   += math.sin(math.radians(windDirNow))
##    
##        if self.c == numPoints:
##            avgWindDir = math.degrees(math.atan2(self.sumEastWest, self.sumNorthSouth))
##            if avgWindDir < 0:
##                avgWindDir += 360
##            elif avgWindDir > 360:
##                avgWindDir = avgWindDir % 360 # atan2() result can be > 360, so use modulus to just return remainder
##
##            self.windDir = int(avgWindDir + 0.5)  # Round to nearest integer
##            self.c = 0 # reset counter
##            self.sumNorthSouth = 0.0
##            self.sumEastWest = 0.0
##
##        if (self.windDir >= 0):
##            return (self.windDir)
##        return (0)

    # Averages numPoints of wind direction data. When numPoints is reached
    # Uses a list and shifts data in
    def avgWindDir(self, windDirNow):

        numPoints = weatherStation.AVG_WIND_DIR_NUM_DATA_POINTS
        
        # Put first 30 data pionts in lists
        if self.c < numPoints:
            self.northSouth[self.c] = math.cos(math.radians(windDirNow))
            self.eastWest[self.c]   = math.sin(math.radians(windDirNow))
            self.c += 1
            return(weatherStation.NO_DATA_YET)

        # Lists are full, can calculate average now
        if self.c >= numPoints:
            # Shift oldest reading out 
            self.northSouth = list(self.northSouth[1:numPoints]) 
            self.eastWest   = list(self.eastWest[1:numPoints])
            # Append new wind direction to end of list
            self.northSouth.append(math.cos(math.radians(windDirNow)))
            self.eastWest.append(math.sin(math.radians(windDirNow)))
            # Sum the 2 lists
            sumNorthSouth = sum(self.northSouth)
            sumEastWest   = sum(self.eastWest)

            # Calculate average wind direction
            avgWindDir = math.degrees(math.atan2(sumEastWest, sumNorthSouth))
            if avgWindDir < 0:
                avgWindDir += 360
            elif avgWindDir > 360:
                avgWindDir = avgWindDir % 360 # atan2() result can be > 360, so use modulus to just return remainder
            self.windDir = int(avgWindDir + 0.5)  # Round to nearest integer
            self.c += 1
            return (self.windDir)



    def calcDewPoint(self):
        if (self.gotTemperatureData() and self.gotHumidityData()):
            celsius = (self.outsideTemp - 32.0 ) / 1.8 # convert to celcius
            a = 17.271
            b = 237.7
            alpha = ((a * celsius) / (b + celsius)) + math.log(self.humidity / 100)
            Td = (b * alpha) / (a - alpha)
            Td = Td * 1.8 + 32.0  # convert back to Fahrenheit
            self.dewPoint = Td
            return (Td)
        return(weatherStation.NO_DATA_YET)

    #---------------------------------------------------------------------
    # Calculate Wind Chill
    #---------------------------------------------------------------------
    def calcWindChill(self):

        if self.gotTemperatureData() and self.gotWindSpeedData():
            self.windChill = (self.outsideTemp * 0.6215) - (35.75 * self.windSpeed**0.16) + (0.4275 * self.outsideTemp * self.windSpeed**0.16) + 35.74
            return(self.windChill)
        else:
            suntec.windChill = weatherStation.NO_DATA_YET
            return (weatherStation.NO_DATA_YET)

