# Source
#   https://projects.raspberrypi.org/en/projects/sense-hat-data-logger/4

from csv import writer
import csv
import time


def windDataLogging(windDirRaw, windDirNow, windDirAvg):
    with open('wind.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([time.time(), windDirRaw, round(windDirNow, 2), round(windDirAvg, 2)])

    return(True)
