import math
from datetime import datetime, timedelta


def get_next_alarm(initial_interval: int, interval: int) -> datetime:
    current_time = datetime.now()
    start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')

    initial_interval = initial_interval / 60
    interval = interval / 60

    first_alarm_time = start_time + timedelta(minutes=initial_interval)

    if current_time <= first_alarm_time:
        return first_alarm_time

    time_since_first_alarm = current_time - first_alarm_time

    passed_intervals_count = math.floor(
        time_since_first_alarm.total_seconds() / (interval * 60)
    )

    last_passed_alarm_time = first_alarm_time + timedelta(minutes=passed_intervals_count * interval)

    if current_time == last_passed_alarm_time:
        next_alarm_time = last_passed_alarm_time + timedelta(minutes=interval)
    else:
        next_alarm_time = last_passed_alarm_time + timedelta(minutes=interval)

    return next_alarm_time


# --- Example Usage ---

start_time_str = '2025-10-03 18:00:00'
first_interval = 30
regular_interval = 20

print(f"Start Time: {start_time_str}")
print(f"First Interval: {first_interval} minutes")
print(f"Regular Interval: {regular_interval} minutes")

next_alarm = get_next_alarm(start_time_str, first_interval, regular_interval)
print(f"\nNext Alarm Time: {next_alarm.strftime('%Y-%m-%d %H:%M:%S')}")
