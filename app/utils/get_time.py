from babel.dates import format_datetime
from datetime import datetime

def get_time():
  now = datetime.now()
  formatted = format_datetime(now, "EEEE, d MMMM yyyy HH:mm:ss", locale='id')
  return formatted
