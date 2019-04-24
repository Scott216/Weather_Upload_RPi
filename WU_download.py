# This mododule downloads data from Weather Underground, specifically rain accumulation for the day and pressure
# This module has the following functions
# getDailyRain() - used on reboot to get the daily rain accumulation for the day.  This sets the starting point for the rain counter
# getPressure() - connects to nearby weather station to get the pressure since my station has no baromoter wireless data,
#                 the baromoter is in the console and that info isn't available
#  WU doc on API for current conditions: https://docs.google.com/document/d/1KGb8bTVYRsNgljnNH67AMhckY8AQT2FVwZ9urj8SWBs/edit#
#

WU_STATIONS = ["KVTDOVER7", "KVTWESTD4", "KVTDOVER8"]  # nearby weather station IDs to get pressure data

import requests        # Allows you to send HTTP/1.1 requests
import WU_credentials  # Weather underground password, station IDs and API key
import time

ERR_INVALID_DATA = -102
ERR_FAILED_GET   = -103


# Get daily rain data from Suntec station.  Need this on reboot of RPi
# Returns inches of rain since midnight
def getDailyRain():
    getUrl = "https://api.weather.com/v2/pws/observations/current?stationId={}&format=json&units=e&apiKey={}".format(WU_credentials.WU_STATION_ID_SUNTEC, WU_credentials.WU_API_KEY)

    try:
        response = requests.get(getUrl, timeout=10).json()

        if len(response['observations'][0]) >= 16:  # should return 16, not sure what it will return if there's an error
            if isNumber(response['observations'][0]['imperial']['precipTotal']):
                daily_rain = float(response['observations'][0]['imperial']['precipTotal'])
                if (daily_rain >=0 and daily_rain < 10.0):
                    print('Suntec station daily rain={}'.format(daily_rain))  
                    return(daily_rain)
                else:
                    print('Suntec station daily rain out of bounds: {}'.format(daily_rain))
                    return(ERR_INVALID_DATA)
            else:
                # if daily rain is zero, WU ruturns "none" as the value, not 0.0
                return(0) 
        return(ERR_INVALID_DATA)

    except Exception:
        print("Error in getDailyRain() - failed get() request")
        return(ERR_FAILED_GET)
        
def getPressure():
    i = 0
    while i < len(WU_STATIONS):  # loops through stations in WU_STATIONS list

        # Get pressure from nearby station
        getUrl = "https://api.weather.com/v2/pws/observations/current?stationId={}&format=json&units=e&apiKey={}".format(WU_STATIONS[i], WU_credentials.WU_API_KEY)
            
        try:
            response = requests.get(getUrl, timeout=10).json()
            if len(response['observations'][0]) >= 16: # should return 16, not sure what it will return if there's an error
                if isNumber(response['observations'][0]['imperial']['pressure']):
                    nearby_pressure = float(response['observations'][0]['imperial']['pressure'])
                    nearby_last_update_time = int(response['observations'][0]['epoch'])
                    if (nearby_pressure) > 25: # a pressure less than 25 inHg isn't valid
                        return(nearby_pressure)

            # Didn't get a valid pressure. Try the next station in WU_STATIONS tuple
            print("Couldn't get pressure data from {}".format(WU_STATIONS[i]))
            nearby_pressure = ERR_INVALID_DATA
            nearby_last_update_time = 0
            i = i + 1
            time.sleep(10)

        except Exception:
            print("Error in getPressure(), failed get() request for station {}".format(WU_STATIONS[i]))
            i = i + 1
            if (i >= len(WU_STATIONS)):
                return(ERR_FAILED_GET)

        
    # Couldn't get pressure, return an error
    return(ERR_INVALID_DATA)
        

# Checks to see if a string is numeric
def isNumber(str):
    try:
        float(str)
        return True
    except ValueError:
        return False


    
