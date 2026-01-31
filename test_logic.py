from datetime import time, date, datetime

def calculate_duration(start, end):
    dummy_date = date.today()
    dt1 = datetime.combine(dummy_date, start)
    dt2 = datetime.combine(dummy_date, end)
    diff = dt2 - dt1
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    if hours > 0:
        return f"{hours}시간 {minutes}분" if minutes > 0 else f"{hours}시간"
    return f"{minutes}분"

# Test cases
print(f"15:30 ~ 17:30 -> {calculate_duration(time(15,30), time(17,30))}") # Should be 2 hours
print(f"15:30 ~ 16:00 -> {calculate_duration(time(15,30), time(16,0))}")   # Should be 30 mins
print(f"15:30 ~ 16:45 -> {calculate_duration(time(15,30), time(16,45))}")  # Should be 1 hour 15 mins
