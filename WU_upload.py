# Weather Underground API - Response fileds
# https://www.wunderground.com/weather/api/d/docs?d=data/conditions


import requests        # Allows you to send HTTP/1.1 requests
import WU_credentials  # Weather underground password, station IDs and API key
import weatherData_cls # class to hold weather data for the Davis ISS station


# This function uploads the weather data to Weather Underground
# weatherData parameter is an instance of the weatherStation class in weather_Data_cls.py
# stationID is the Weather Underground station ID
# Note, if you don't send WU temperature and dewpoint, it will assume zero
def upload2WU(weatherData, stationID):
    # create strings to hold various parts of upload URL
    WU_url = "https://rtupdate.wunderground.com/weatherstation/updateweatherstation.php?"
    WU_creds = 'ID={}&PASSWORD={}'.format(stationID, WU_credentials.WU_PASSWORD)
    WU_software = "&softwaretype=RPi-Moteino"
    WU_action = "&action=updateraw&realtime=1"          # &rtfreq=" + str(UploadFreqSeconds)

    # Assemble URL to send to WU
    full_URL = WU_url + WU_creds + "&dateutc=now" 
    if weatherData.gotWindDirData():
        full_URL = full_URL + '&winddir={:.0f}'.format(weatherData.windDir)
    if weatherData.gotWindSpeedData():
        full_URL = full_URL + '&windspeedmph={:.1f}'.format(weatherData.windSpeed)
    if weatherData.gotWindGustData():
        full_URL = full_URL + '&windgustmph={:.1f}'.format(weatherData.windGust)
    if weatherData.gotTemperatureData():
        full_URL = full_URL + '&tempf={:.1f}'.format(weatherData.outsideTemp)
    if weatherData.gotRainRateData():
        full_URL = full_URL + '&rainin={:.2f}'.format(weatherData.rainRate)
    if weatherData.gotRainTodayData():
        full_URL = full_URL + '&dailyrainin={:.2f}'.format(weatherData.rainToday)
    if weatherData.gotPressureData():
        full_URL = full_URL + '&baromin={:.2f}'.format(weatherData.pressure)
    else:
        full_URL = full_URL + '&baromin=29.00'  # if pressure is ommitted, WU assumes zero, so just enter 29 as a default
    if weatherData.gotDewPointData():
        full_URL = full_URL + '&dewptf={:.1f}'.format(weatherData.dewPoint)
    if weatherData.gotHumidityData():
        full_URL = full_URL + '&humidity={:.1f}'.format(weatherData.humidity)
    if weatherData.gotWindChillData():
        full_URL = full_URL + '&windchill_f={:.1f}'.format(weatherData.windChill)

    # print(full_URL)  # srg debug
    
    full_URL = full_URL + WU_software + WU_action

    try:
        r = requests.get(full_URL, timeout=10) # send data to WU

        # If uploaded successfully, website will reply with 200
        if r.status_code == 200:
            return([True, "No Errors"])
        else:
            uploadErrMsg = "HTTP Response:{},  {}".format(r.status_code, r.text)
            return([False, uploadErrMsg])
        
    # Info on requests errors:
    #  http://docs.python-requests.org/en/master/_modules/requests/exceptions/
    except requests.exceptions.ConnectionError:
        uploadErrMsg = "ConnectionError"
        return([False, uploadErrMsg])

    except requests.exceptions.HTTPError:
        uploadErrMsg = "HTTPError"
        return([False, uploadErrMsg])

    except requests.exceptions.ConnectTimeout:
        uploadErrMsg = "ConnectTimeout"
        return([False, uploadErrMsg])

    except requests.exceptions.ReadTimeout:
        uploadErrMsg = "ReadTimeout"
        return([False, uploadErrMsg])

    except requests.exceptions.RetryError:
        uploadErrMsg = "RetryError"
        return([False, uploadErrMsg])

    except requests.exceptions.Timeout:
        uploadErrMsg = "Timeout"
        return([False, uploadErrMsg])

    except Exception:
        uploadErrMsg = "Other"
        return([False, uploadErrMsg])
