#  Copyright 2022, Laszlo Attila Toth
#  Distributed under the terms of the Apache License, Version 2.0
import datetime


def humanize_time(seconds, format=False, trim_secs=True):
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if trim_secs:
        secs = int(secs * 100) / 100
    days = 0
    if hours > 24:
        days, hours = divmod(hours, 24)
    if format:
        result = ''
        if days > 0:
            result = '%d days' % (days,)
        result = '%s%02d:%02d:%05.2f' % (result, hours, mins, secs)
        return result
    return days, hours, mins, secs


def localtime():
    return datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%s')
