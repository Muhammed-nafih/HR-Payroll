"""
utils.py

This module is used write custom methods
"""

import calendar
from datetime import datetime, time, timedelta

import pandas as pd
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from base.methods import get_pagination
from base.models import WEEK_DAYS, CompanyLeaves, Holidays
from employee.models import Employee
from horilla.horilla_settings import HORILLA_DATE_FORMATS, HORILLA_TIME_FORMATS






MONTH_MAPPING = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def format_time(seconds):
    """
    this method is used to formate seconds to H:M and return it
    args:
        seconds : seconds
    """

    hour = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int((seconds % 3600) % 60)
    return f"{hour:02d}:{minutes:02d}"


"""def strtime_seconds(time):
    
    this method is used reconvert time in H:M formate string back to seconds and return it
    args:
        time : time in H:M format
    

    ftr = [3600, 60, 1]
    return sum(a * b for a, b in zip(ftr, map(int, time.split(":")))) """



def strtime_seconds(time_obj):
    # Check if time_obj is a datetime.time instance using hasattr()
    if hasattr(time_obj, 'strftime'):
        # Convert time_obj to string in HH:MM format
        time_obj = time_obj.strftime("%H:%M")
    
    # Now proceed with the splitting logic (assuming the input is always in HH:MM format)
    hours, minutes = map(int, time_obj.split(":"))
    return hours * 3600 + minutes * 60

def get_diff_obj(first_instance, other_instance, exclude_fields=None):
    """
    Compare the fields of two instances and identify the changes.

    Args:
        first_instance: The first instance to compare.
        other_instance: The second instance to compare.
        exclude_fields: A list of field names to exclude from comparison (optional).

    Returns:
        A dictionary of changed fields with their old and new values.
    """
    difference = {}

    fields_to_compare = first_instance._meta.fields

    if exclude_fields:
        fields_to_compare = [
            field for field in fields_to_compare if field.name not in exclude_fields
        ]

    for field in fields_to_compare:
        old_value = getattr(first_instance, field.name)
        new_value = getattr(other_instance, field.name)

        if old_value != new_value:
            difference[field.name] = (old_value, new_value)

    return difference


def get_diff_dict(first_dict, other_dict, model=None):
    """
    Compare two dictionaries and identify differing key-value pairs.

    Args:
        first_dict: The first dictionary to compare.
        other_dict: The second dictionary to compare.
        model: The model class

    Returns:
        A dictionary of differing keys with their old and new values.
    """
    # model is passed as argument if any need of verbose name instead of field name
    difference = {}
    if model is None:
        for key in first_dict:
            if first_dict[key] != other_dict[key]:
                # get the verbose name of the field
                difference[key] = (first_dict[key], other_dict[key])
        return difference
    for key in first_dict:
        if first_dict[key] != other_dict[key]:
            # get the verbose name of the field
            field = model._meta.get_field(key)
            verb_key = field.verbose_name
            value = first_dict[key]
            other_value = other_dict[key]
            if isinstance(field, models.DateField):
                if value is not None and value != "None":
                    value = datetime.strptime(value, "%Y-%m-%d").strftime("%d %b %Y")
                if other_value is not None and other_value != "None":
                    other_value = datetime.strptime(other_value, "%Y-%m-%d").strftime(
                        "%d %b %Y"
                    )
            elif isinstance(field, models.TimeField):
                if value is not None and value != "None":
                    if len(value.split(":")) == 2:
                        value = value + ":00"
                    value = datetime.strptime(value, "%H:%M:%S").strftime("%I:%M %p")
                if other_value is not None and value != "None":
                    if len(other_value.split(":")) == 2:
                        other_value = other_value + ":00"
                    if other_value != "None":
                        other_value = datetime.strptime(
                            other_value, "%H:%M:%S"
                        ).strftime("%I:%M %p")
                    else:
                        other_value = "None"
            elif isinstance(field, models.ForeignKey):
                if value is not None and len(str(value)):
                    value = field.related_model.objects.get(id=value)
                if other_value is not None and len(str(other_value)):
                    other_value = field.related_model.objects.get(id=other_value)
            difference[verb_key] = (value, other_value)
    return difference


def employee_exists(request):
    """
    This method return the employee instance and work info if not exists return None instead
    """
    employee, employee_work_info = None, None
    try:
        employee = request.user.employee_get
        employee_work_info = employee.employee_work_info
    finally:
        return (employee, employee_work_info)


def shift_schedule_today(day, shift):
    """
    This function is used to find shift schedules for the day,
    it will returns min hour,start time seconds  end time seconds
    args:
        shift   : shift instance
        day     : shift day object
    """
    schedule_today = day.day_schedule.filter(shift_id=shift)
    start_time_sec, end_time_sec, minimum_hour = 0, 0, "00:00"
    if schedule_today.exists():
        schedule_today = schedule_today[0]
        minimum_hour = schedule_today.minimum_working_hour
        start_time_sec = strtime_seconds(schedule_today.start_time.strftime("%H:%M"))
        end_time_sec = strtime_seconds(schedule_today.end_time.strftime("%H:%M"))
    return (minimum_hour, start_time_sec, end_time_sec)


def overtime_calculation(attendance):
    """
    This method is used to calculate overtime of the attendance, it will
    return difference between attendance worked hour and minimum hour if
    and only worked hour greater than minimum hour, else return 00:00
    args:
        attendance : attendance instance
    """

    minimum_hour = attendance.minimum_hour
    at_work = attendance.attendance_worked_hour
    at_work_sec = strtime_seconds(at_work)
    minimum_hour_sec = strtime_seconds(minimum_hour)
    if at_work_sec > minimum_hour_sec:
        return format_time((at_work_sec - minimum_hour_sec))
    return "00:00"


def is_reportingmanger(request, instance):
    """
    if the instance have employee id field then you can use this method to know the
    request user employee is the reporting manager of the instance
    args :
        request : request
        instance : an object or instance of any model contain employee_id foreign key field
    """

    manager = request.user.employee_get
    try:
        employee_workinfo_manager = (
            instance.employee_id.employee_work_info.reporting_manager_id
        )
    except Exception:
        return HttpResponse("This Employee Dont Have any work information")
    return manager == employee_workinfo_manager


def validate_hh_mm_ss_format(value):
    timeformat = "%H:%M:%S"
    try:
        validtime = datetime.strptime(value, timeformat)
        return validtime.time()  # Return the time object if needed
    except ValueError as e:
        raise ValidationError(_("Invalid format, it should be HH:MM:SS format"))


def validate_time_format(value):
    """
    this method is used to validate the format of duration like fields.
    """
    if len(value) > 6:
        raise ValidationError(_("Invalid format, it should be HH:MM format"))
    try:
        hour, minute = value.split(":")
        if len(hour) > 3 or len(minute) > 2:
            raise ValidationError(_("Invalid time"))
        hour = int(hour)
        minute = int(minute)
        if len(str(hour)) > 3 or len(str(minute)) > 2 or minute not in range(60):
            raise ValidationError(_("Invalid time, excepted MM:SS"))
    except ValueError as error:
        raise ValidationError(_("Invalid format")) from error


def attendance_date_validate(date):
    """
    Validates if the provided date is not a future date.

    :param date: The date to validate.
    :raises ValidationError: If the provided date is in the future.
    """
    today = datetime.today().date()
    if not date:
        raise ValidationError(_("Check date format."))
    elif date > today:
        raise ValidationError(_("You cannot choose a future date."))


def activity_datetime(attendance_activity):
    """
    This method is used to convert clock-in and clock-out of activity as datetime object
    args:
        attendance_activity : attendance activity instance
    """

    # in
    in_year = attendance_activity.clock_in_date.year
    in_month = attendance_activity.clock_in_date.month
    in_day = attendance_activity.clock_in_date.day
    in_hour = attendance_activity.clock_in.hour
    in_minute = attendance_activity.clock_in.minute
    # out
    out_year = attendance_activity.clock_out_date.year
    out_month = attendance_activity.clock_out_date.month
    out_day = attendance_activity.clock_out_date.day
    out_hour = attendance_activity.clock_out.hour
    out_minute = attendance_activity.clock_out.minute
    return datetime(in_year, in_month, in_day, in_hour, in_minute), datetime(
        out_year, out_month, out_day, out_hour, out_minute
    )


def get_week_start_end_dates(week):
    """
    This method is use to return the start and end date of the week
    """
    # Parse the ISO week date
    year, week_number = map(int, week.split("-W"))

    # Get the date of the first day of the week
    start_date = datetime.strptime(f"{year}-W{week_number}-1", "%Y-W%W-%w").date()

    # Calculate the end date by adding 6 days to the start date
    end_date = start_date + timedelta(days=6)

    return start_date, end_date


def get_month_start_end_dates(year_month):
    """
    This method is use to return the start and end date of the month
    """
    # split year and month separately
    year, month = map(int, year_month.split("-"))
    # Get the first day of the month
    start_date = datetime(year, month, 1).date()

    # Get the last day of the month
    _, last_day = calendar.monthrange(year, month)
    end_date = datetime(year, month, last_day).date()

    return start_date, end_date


def worked_hour_data(labels, records):
    """
    To find all the worked hours
    """
    data = {
        "label": "Worked Hours",
        "backgroundColor": "rgba(75, 192, 192, 0.6)",
    }
    dept_records = []
    for dept in labels:
        total_sum = records.filter(
            employee_id__employee_work_info__department_id__department=dept
        ).aggregate(total_sum=Sum("hour_account_second"))["total_sum"]
        dept_records.append(total_sum / 3600 if total_sum else 0)
    data["data"] = dept_records
    return data


def pending_hour_data(labels, records):
    """
    To find all the pending hours
    """
    data = {
        "label": "Pending Hours",
        "backgroundColor": "rgba(255, 99, 132, 0.6)",
    }
    dept_records = []
    for dept in labels:
        total_sum = records.filter(
            employee_id__employee_work_info__department_id__department=dept
        ).aggregate(total_sum=Sum("hour_pending_second"))["total_sum"]
        dept_records.append(total_sum / 3600 if total_sum else 0)
    data["data"] = dept_records
    return data


def get_employee_last_name(attendance):
    """
    This method is used to return the last name
    """
    if attendance.employee_id.employee_last_name:
        return attendance.employee_id.employee_last_name
    return ""


def attendance_day_checking(attendance_date, minimum_hour):
    # Convert the string to a datetime object
    attendance_datetime = datetime.strptime(attendance_date, "%Y-%m-%d")

    # Extract name of the day
    attendance_day = attendance_datetime.strftime("%A")

    # Taking all holidays into a list
    leaves = []
    holidays = Holidays.objects.all()
    for holi in holidays:
        start_date = holi.start_date
        end_date = holi.end_date

        # Convert start_date and end_date to datetime objects
        start_date = datetime.strptime(str(start_date), "%Y-%m-%d")
        end_date = datetime.strptime(str(end_date), "%Y-%m-%d")

        # Add dates in between start date and end date including both
        current_date = start_date
        while current_date <= end_date:
            leaves.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)

    # Checking attendance date is in holiday list, if found making the minimum hour to 00:00
    for leave in leaves:
        if str(leave) == str(attendance_date):
            minimum_hour = "00:00"
            break

    # Making a dictonary contains week day value and leave day pairs
    company_leaves = {}
    company_leave = CompanyLeaves.objects.all()
    for com_leave in company_leave:
        a = dict(WEEK_DAYS).get(com_leave.based_on_week_day)
        b = com_leave.based_on_week
        company_leaves[b] = a

    # Checking the attendance date is in which week
    week_in_month = str(((attendance_datetime.day - 1) // 7 + 1) - 1)

    # Checking the attendance date is in the company leave or not
    for pairs in company_leaves.items():
        # For all weeks based_on_week is None
        if str(pairs[0]) == "None":
            if str(pairs[1]) == str(attendance_day):
                minimum_hour = "00:00"
                break
        # Checking with based_on_week and attendance_date week
        if str(pairs[0]) == week_in_month:
            if str(pairs[1]) == str(attendance_day):
                minimum_hour = "00:00"
                break
    return minimum_hour


def paginator_qry(qryset, page_number):
    """
    This method is used to paginate queryset
    """
    paginator = Paginator(qryset, get_pagination())
    qryset = paginator.get_page(page_number)
    return qryset


def monthly_leave_days(month, year):
    leave_dates = []
    holidays = Holidays.objects.filter(start_date__month=month, start_date__year=year)
    leave_dates += list(holidays.values_list("start_date", flat=True))

    company_leaves = CompanyLeaves.objects.all()
    for company_leave in company_leaves:
        year = year
        month = month
        based_on_week = company_leave.based_on_week
        based_on_week_day = company_leave.based_on_week_day
        if based_on_week != None:
            calendar.setfirstweekday(6)
            month_calendar = calendar.monthcalendar(year, month)
            weeks = month_calendar[int(based_on_week)]
            weekdays_in_weeks = [day for day in weeks if day != 0]
            for day in weekdays_in_weeks:
                date_name = datetime.strptime(
                    f"{year}-{month:02}-{day:02}", "%Y-%m-%d"
                ).date()
                if (
                    date_name.weekday() == int(based_on_week_day)
                    and date_name not in leave_dates
                ):
                    leave_dates.append(date_name)
        else:
            calendar.setfirstweekday(0)
            month_calendar = calendar.monthcalendar(year, month)
            for week in month_calendar:
                if week[int(based_on_week_day)] != 0:
                    date_name = datetime.strptime(
                        f"{year}-{month:02}-{week[int(based_on_week_day)]:02}",
                        "%Y-%m-%d",
                    ).date()
                    if date_name not in leave_dates:
                        leave_dates.append(date_name)
    return leave_dates


def validate_time_in_minutes(value):
    """
    this method is used to validate the format of duration like fields.
    """
    if len(value) > 5:
        raise ValidationError(_("Invalid format, it should be MM:SS format"))
    try:
        minutes, sec = value.split(":")
        if len(minutes) > 2 or len(sec) > 2:
            raise ValidationError(_("Invalid time, excepted MM:SS"))
        minutes = int(minutes)
        sec = int(sec)
        if minutes not in range(60) or sec not in range(60):
            raise ValidationError(_("Invalid time, excepted MM:SS"))
    except ValueError as e:
        raise ValidationError(_("Invalid format,  excepted MM:SS")) from e


class Request:
    """
    Represents a request for clock-in or clock-out.

    Attributes:
    - user: The user associated with the request.
    - date: The date of the request.
    - time: The time of the request.
    - path: The path associated with the request (default: "/").
    - session: The session data associated with the request (default: {"title": None}).
    """

    def __init__(
        self,
        user,
        date,
        time,
        datetime,
    ) -> None:
        self.user = user
        self.path = "/"
        self.session = {"title": None}
        self.date = date
        self.time = time
        self.datetime = datetime
        self.META = META()


class META:
    """
    Provides access to HTTP metadata keys.
    """

    @classmethod
    def keys(cls):
        """
        Retrieve the list of available HTTP metadata keys.

        Returns:
            list: A list of HTTP metadata keys.
        """
        return ["HTTP_HX_REQUEST"]


def parse_time(time_str):
    if isinstance(time_str, time):  # Check if it's already a time object
        return time_str

    if isinstance(time_str, str):
        for format_str in HORILLA_TIME_FORMATS.values():
            try:
                return datetime.strptime(time_str, format_str).time()
            except ValueError:
                continue
    return None


def parse_date(date_str, error_key, activity):
    try:
        return pd.to_datetime(date_str).date()
    except (pd.errors.ParserError, ValueError):
        activity[error_key] = f"Invalid date format for {error_key.split()[-1]}"
        return None


def parse_datetime(date_str, time_str):
    return (
        datetime.strptime(f"{date_str} {time_str[:5]}", "%Y-%m-%d %H:%M")
        if date_str and time_str
        else None
    )


def get_date(date):
    if isinstance(date, datetime):
        return date
    elif isinstance(date, str):
        for format_name, format_str in HORILLA_DATE_FORMATS.items():
            try:
                return datetime.strptime(date, format_str)
            except ValueError:
                continue
    return None


def sort_activity_dicts(activity_dicts):

    for activity in activity_dicts:
        activity["Attendance Date"] = get_date(activity["Attendance Date"])

    # Filter out any entries where the date could not be parsed
    activity_dicts = [
        activity
        for activity in activity_dicts
        if activity["Attendance Date"] is not None
    ]
    sorted_activity_dicts = sorted(activity_dicts, key=lambda x: x["Attendance Date"])
    return sorted_activity_dicts



def filtersubordinates(request, queryset, permission):
    user = request.user
    if user.has_perm(permission):
       
        filtered_queryset = queryset.filter(Q(created_by=user))
    else:
        filtered_queryset = queryset.none()
    return filtered_queryset


def sortby(request, queryset, param_name):
    sort_field = request.GET.get(param_name)
    if sort_field:
        return queryset.order_by(sort_field)
    return queryset


def late_come_create(attendance):
    from attendance.models import AttendanceLateComeEarlyOut
    """
    used to create late come report
    args:
        attendance : attendance object
    """

    late_come_obj = AttendanceLateComeEarlyOut()
    late_come_obj.type = "late_come"
    late_come_obj.attendance_id = attendance
    late_come_obj.employee_id = attendance.employee_id
    late_come_obj.save()
    return late_come_obj


def late_come(attendance, start_time, end_time):
    """
    this method is used to mark the late check-in  attendance after the shift starts
    args:
        attendance : attendance obj
        start_time : attendance day shift start time
        end_time : attendance day shift end time

    """

    now_sec = strtime_seconds(datetime.now().strftime("%H:%M"))
    mid_day_sec = strtime_seconds("12:00")
    if start_time > end_time and start_time != end_time:
        # night shift
        if now_sec < mid_day_sec:
            # Here  attendance or attendance activity for new day night shift
            late_come_create(attendance)
        elif now_sec > start_time:
            # Here  attendance or attendance activity for previous day night shift
            late_come_create(attendance)
    elif start_time < now_sec:
        late_come_create(attendance)
    return True

def clock_in_attendance_and_activity(
    employee,
    date_today,
    attendance_date,
    day,
    now,
    shift,
    minimum_hour,
    start_time,
    end_time,
):
    from attendance.models import Attendance, AttendanceActivity

    """
    This method is used to create attendance activity or attendance when an employee clocks-in
    args:
        employee        : employee instance
        date_today      : date
        attendance_date : the date that attendance for
        day             : shift day
        now             : current time
        shift           : shift object
        minimum_hour    : minimum hour in shift schedule
        start_time      : start time in shift schedule
        end_time        : end time in shift schedule
    """

    # attendance activity create
    AttendanceActivity(
        employee_id=employee,
        attendance_date=attendance_date,
        clock_in_date=date_today,
        shift_day=day,
        clock_in=now,
    ).save()

    # create attendance if not exist
    attendance = Attendance.objects.filter(
        employee_id=employee, attendance_date=attendance_date
    )
    if not attendance.exists():
        attendance = Attendance()
        attendance.employee_id = employee
        attendance.shift_id = shift
        attendance.work_type_id = attendance.employee_id.employee_work_info.work_type_id
        attendance.attendance_date = attendance_date
        attendance.attendance_day = day
        attendance.attendance_clock_in = now
        attendance.attendance_clock_in_date = date_today
        attendance.minimum_hour = minimum_hour
        attendance.save()
        # check here late come or not
        late_come(attendance=attendance, start_time=start_time, end_time=end_time)
    else:
        attendance = attendance[0]
        attendance.attendance_clock_out = None
        attendance.attendance_clock_out_date = None
        attendance.save()
        # delete if the attendance marked the early out
        early_out_instance = attendance.late_come_early_out.filter(type="early_out")
        if early_out_instance.exists():
            early_out_instance[0].delete()
    return attendance





def attendance_validate(attendance):
    from attendance.models import  AttendanceValidationCondition
    """
    This method is is used to check condition for at work in AttendanceValidationCondition
    model instance it return true if at work is smaller than condition
    args:
        attendance : attendance object
    """

    conditions = AttendanceValidationCondition.objects.all()
    # Set the default condition for 'at work' to 9:00 AM
    condition_for_at_work = strtime_seconds("09:00")
    if conditions.exists():
        condition_for_at_work = strtime_seconds(conditions[0].validation_at_work)
    at_work = strtime_seconds(attendance.attendance_worked_hour)
    return condition_for_at_work >= at_work



  
def early_out_create(attendance):
    from attendance.models import AttendanceLateComeEarlyOut
    """
    Used to create early out report
    args:
        attendance : attendance obj
    """

    late_come_obj = AttendanceLateComeEarlyOut()
    late_come_obj.type = "early_out"
    late_come_obj.attendance_id = attendance
    late_come_obj.employee_id = attendance.employee_id
    late_come_obj.save()
    return late_come_obj


def early_out(attendance, start_time, end_time):
    """
    This method is used to mark the early check-out attendance before the shift ends
    args:
        attendance : attendance obj
        start_time : attendance day shift start time
        start_end : attendance day shift end time
    """

    now_sec = strtime_seconds(datetime.now().strftime("%H:%M"))
    mid_day_sec = strtime_seconds("12:00")
    if start_time > end_time:
        # Early out condition for night shift
        if now_sec < mid_day_sec:
            if now_sec < end_time:
                # Early out condition for general shift
                early_out_create(attendance)
        else:
            early_out_create(attendance)
        return
    if end_time > now_sec:
        early_out_create(attendance)
    return


def clock_out_attendance_and_activity(employee, date_today, now):
    from attendance.models import Attendance, AttendanceActivity
    """
    Clock out the attendance and activity
    args:
        employee    : employee instance
        date_today  : today's date
        now         : current time
    """
    # Fetch attendance activities for the employee, ordered by date and id
    attendance_activities = AttendanceActivity.objects.filter(
        employee_id=employee
    ).order_by("attendance_date", "id")

    # Ensure that there is at least one attendance activity
    if attendance_activities.exists():
        attendance_activity = attendance_activities.last()

        # Update clock-out time for the last attendance activity
        attendance_activity.clock_out = now
        attendance_activity.clock_out_date = date_today
        attendance_activity.save()
    else:
        return  # If no attendance activities exist, return early

    # Filter attendance activities that have clocked out, matching today's date
    attendance_activities = attendance_activities.filter(
        ~Q(clock_out=None)
    ).filter(attendance_date=attendance_activity.attendance_date)

    # Calculate total worked duration
    duration = 0
    for attendance_activity in attendance_activities:
        # Assuming activity_datetime() returns datetime objects
        in_datetime, out_datetime = activity_datetime(attendance_activity)
        difference = out_datetime - in_datetime
        days_seconds = difference.days * 24 * 3600
        seconds = difference.seconds
        total_seconds = days_seconds + seconds
        duration += total_seconds

    # Convert total duration to formatted time (e.g., HH:MM:SS)
    duration = format_time(duration)

    # Update attendance record with the clock-out details
    attendance = Attendance.objects.filter(employee_id=employee).order_by(
        "-attendance_date", "-id"
    )[0]

    attendance.attendance_clock_out = now
    attendance.attendance_clock_out_date = date_today
    attendance.attendance_worked_hour = duration
    attendance.save()

    # Calculate overtime and validate attendance
    attendance.attendance_overtime = overtime_calculation(attendance)
    attendance.attendance_validated = attendance_validate(attendance)
    attendance.save()

    return  

def employee_exists(employee_id):
    try:
        # Assuming Employee model has related work_info through a foreign key or relationship
        employee = Employee.objects.get(id=employee_id)
        work_info = employee.work_info  # Or however work_info is related to employee
        return employee, work_info
    except Employee.DoesNotExist:
        return None, None
    



