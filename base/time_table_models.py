import uuid
from django.db import models

from .models import User
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.core.exceptions import ValidationError

from .models import Classroom,Subject,Teacher,Room,Standard
class DayChoices(models.TextChoices):
    MONDAY = 'MON', 'Monday'
    TUESDAY = 'TUE', 'Tuesday'
    WEDNESDAY = 'WED', 'Wednesday'
    THURSDAY = 'THU', 'Thursday'
    FRIDAY = 'FRI', 'Friday'
    SATURDAY = 'SAT', 'Saturday'
    SUNDAY = 'SUN', 'Sunday'

class Timetable(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='timetables')
    score = models.IntegerField(null=True, blank=True)
    hard_score = models.IntegerField( null=True, blank=True) 
    soft_score = models.IntegerField( null=True, blank=True)  
    optimal = models.BooleanField(default=False, null=True, blank=True)
    feasible = models.BooleanField(default=False, null=True, blank=True)
    number_of_lessons=models.IntegerField(editable=True,null=True,blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    is_default = models.BooleanField(default=False)
    

    def __str__(self):
        return self.name

    def set_as_default(self):
        Timetable.objects.filter(school=self.school, is_default=True).update(is_default=False)
        self.is_default = True
        self.save()

@receiver(post_save, sender=Timetable)
def set_default_timetable(sender, instance, created, **kwargs):
    if created:
        # If this is the only timetable for the user, set it as default
        if Timetable.objects.filter(school=instance.school).count() == 1:
            instance.set_as_default()
            

class TimeTableDaySchedule(models.Model):
    table = models.ForeignKey(
        'Timetable', 
        on_delete=models.CASCADE, 
        related_name='day_schedules'
    )
    day = models.CharField(
        max_length=3, 
        choices=DayChoices.choices
    )
    teaching_slots = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ['table', 'day']
        ordering = ['day']

    def __str__(self):
        return f"{self.get_day_display()} - {self.teaching_slots} slots"    
    
    
    
class TimeTablePeriod(models.Model):
    day_schedule = models.ForeignKey(
        TimeTableDaySchedule, 
        on_delete=models.CASCADE, 
        related_name='periods'
    )
    period_number = models.PositiveIntegerField()  # New field to represent the period number
    start_time = models.TimeField(null=True, blank=True)  # Allow null values
    end_time = models.TimeField(null=True, blank=True)

    class Meta:
        unique_together = ['day_schedule', 'period_number']  # Ensure unique period numbers within a schedule
        ordering = ['period_number']

    def __str__(self):
        return f"Period {self.period_number}: {self.start_time} - {self.end_time}"
    def clean(self):
        super().clean()
        if self.period_number > self.day_schedule.teaching_slots:
            raise ValidationError(
                f"Period number {self.period_number} exceeds the allowed teaching slots ({self.day_schedule.teaching_slots}) for this day."
            )
    
class StandardLevel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    standard = models.ForeignKey(Standard,on_delete=models.SET_NULL,related_name='class_sectons',null=True)  # Changed to UUIDField and removed unique constraint
    name = models.CharField(max_length=50)
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='standard_levels')
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='standard_levels')

    # class Meta:
        # unique_together = ('standard_id', 'timetable')  # Ensure uniqueness within a timetable

    def __str__(self):
        return self.name

class ClassSection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    classroom = models.ForeignKey(Classroom,on_delete=models.SET_NULL,related_name='class_sectons',null=True)  # Changed to UUIDField and removed unique constraint
    standard = models.ForeignKey(StandardLevel, on_delete=models.CASCADE)
    division = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='class_sections')
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='class_sections')

    # class Meta:
        # unique_together = ('classroom_id', 'timetable')  # Ensure uniqueness within a timetable

    def __str__(self):
        return f"{self.standard.name} - {self.division}"

class Course(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.ForeignKey(Subject,on_delete=models.SET_NULL,related_name='courses',null=True)
    name = models.CharField(max_length=100)
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='courses')
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses')

    # class Meta:
    # unique_together = ('subject_id', 'timetable')  # Ensure uniqueness within a timetable

    def __str__(self):
        return self.name

class Tutor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(Teacher,on_delete=models.SET_NULL,related_name='tutors',null=True) # Changed to UUIDField and removed unique constraint
    name = models.CharField(max_length=100)
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='tutors')
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tutors')

    # class Meta:
        # unique_together = ('teacher_id', 'timetable')  # Ensure uniqueness within a timetable

    def __str__(self):
        return self.name

class ClassroomAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room,on_delete=models.SET_NULL,related_name='classroom_asingments',null=True)  # Changed to UUIDField and removed unique constraint
    name = models.CharField(max_length=100)
    capacity = models.IntegerField()
    room_type = models.CharField(max_length=50)
    occupied = models.BooleanField(default=False)
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='classroom_assignments')
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='classroom_assignments')

    # class Meta:
        # unique_together = ('room_id', 'timetable')  # Ensure uniqueness within a timetable

    def __str__(self):
        return self.name

class Timeslot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    day_of_week = models.CharField(max_length=10)
    period = models.IntegerField()
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='timeslots')
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='timeslots')

    class Meta:
        unique_together = ('day_of_week', 'period', 'timetable')  # Ensure uniqueness within a timetable

    def __str__(self):
        return f"{self.day_of_week} - Period {self.period}"
class Lesson(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='lessons')
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lessons')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    allotted_teacher = models.ForeignKey(Tutor, on_delete=models.CASCADE, related_name='allotted_lessons')
    # available_teachers = models.ManyToManyField(Tutor, related_name='available_lessons')
    class_sections = models.ManyToManyField(ClassSection, through='LessonClassSection', related_name="lessons")
    classroom_assignment = models.ForeignKey(ClassroomAssignment, on_delete=models.CASCADE) #room in main data base model
    timeslot = models.ForeignKey(Timeslot, on_delete=models.CASCADE)
    is_elective=models.BooleanField(default=False, null=True, blank=True)
    elective_subject_name=models.CharField(max_length=100,null=True,blank=True)
    elective_group_id=models.UUIDField(null=True,blank=True)
    def __str__(self):
        return f"{self.course.name} - {self.timeslot} {self.elective_group_id}"

    
class LessonClassSection(models.Model):
    lesson = models.ForeignKey('Lesson', on_delete=models.CASCADE)
    class_section = models.ForeignKey('ClassSection', on_delete=models.CASCADE)
    number_of_students = models.IntegerField()




class DayTimetableDate(models.Model):  
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name="timetable_dates")
    date = models.DateField()
    day_of_week = models.CharField(
        max_length=3, 
        choices=DayChoices.choices
    )
    day_timetable = models.OneToOneField(
        "DayTimetable",
        on_delete=models.CASCADE,  # Delete the related DayTimetableDate when DayTimetable is deleted
        related_name="timetable_date",
        null=True  # Allow null values if needed
    )

    def __str__(self):
        return f"{self.date} ({self.day_of_week}) for {self.school}"

class DayTimetable(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timetable = models.ForeignKey("Timetable", on_delete=models.CASCADE, related_name="day_timetables")
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name="day_timetables")
    teaching_slots = models.IntegerField()
    auto_generated = models.BooleanField(default=True)

    def __str__(self):
        return f"DayTimetable for {self.school} from {self.timetable}"
    

class DayTimeTablePeriod(models.Model):
    day_timetable = models.ForeignKey(
        DayTimetable, 
        on_delete=models.CASCADE, 
        related_name='periods'
    )
    period_number = models.PositiveIntegerField()  # New field to represent the period number
    start_time = models.TimeField(null=True, blank=True)  # Allow null values
    end_time = models.TimeField(null=True, blank=True)

    class Meta:
        unique_together = ['day_timetable', 'period_number']  # Ensure unique period numbers within a schedule
        ordering = ['period_number']

    def __str__(self):
        return f"Period {self.period_number}: {self.start_time} - {self.end_time}"
    def clean(self):
        super().clean()
        if self.period_number > self.day_timetable.teaching_slots:
            raise ValidationError(
                f"Period number {self.period_number} exceeds the allowed teaching slots ({self.day_timetable.teaching_slots}) for this day."
            )
    
class DayLesson(models.Model):  
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    day_timetable = models.ForeignKey(DayTimetable, on_delete=models.CASCADE, related_name="lessons")
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name="day_lessons")
    course = models.ForeignKey("DayCourse", on_delete=models.CASCADE)
    allotted_teacher = models.ForeignKey(
        "DayTutor",
        on_delete=models.CASCADE,
        related_name="day_lessons"  # Unique related_name for DayLesson
    )
    class_sections = models.ManyToManyField(
        "DayClassSection",
        through="DayLessonClassSection",
        related_name="day_lessons"
    )
    classroom_assignment = models.ForeignKey("DayClassroomAssignment", on_delete=models.CASCADE)
    is_elective = models.BooleanField(default=False, null=True, blank=True)
    elective_subject_name = models.CharField(max_length=100, null=True, blank=True)
    elective_group_id=models.UUIDField(null=True,blank=True)
    period = models.IntegerField()

    def __str__(self):
        return f"DayLesson for {self.course} by {self.allotted_teacher}"
    
    
class DayLessonClassSection(models.Model):
    day_lesson = models.ForeignKey(
        DayLesson, on_delete=models.CASCADE, related_name="class_section_assignments"
    )
    class_section = models.ForeignKey(
        "DayClassSection", on_delete=models.CASCADE, related_name="day_lesson_assignments"
    )
    number_of_students = models.IntegerField()

    def __str__(self):
        return f"Class Section {self.class_section} for {self.day_lesson} with {self.number_of_students} students"

    
  
class DayStandardLevel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    standard = models.ForeignKey(Standard,on_delete=models.SET_NULL,related_name='day_standard_levels',null=True)  # Changed to UUIDField and removed unique constraint
    name = models.CharField(max_length=50)
    day_timetable = models.ForeignKey(DayTimetable, on_delete=models.CASCADE, related_name='day_standard_levels')
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='day_standard_levels')

    # class Meta:
        # unique_together = ('standard_id', 'timetable')  # Ensure uniqueness within a timetable

    def __str__(self):
        return self.name

class DayClassSection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    classroom = models.ForeignKey(Classroom,on_delete=models.SET_NULL,related_name='day_class_sectons',null=True)  # Changed to UUIDField and removed unique constraint
    standard = models.ForeignKey(DayStandardLevel, on_delete=models.CASCADE)
    division = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    day_timetable = models.ForeignKey(DayTimetable, on_delete=models.CASCADE, related_name='day_class_sections')
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='day_class_sections')

    # class Meta:
        # unique_together = ('classroom_id', 'timetable')  # Ensure uniqueness within a timetable

    def __str__(self):
        return f"{self.standard.name} - {self.division}"

class DayCourse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.ForeignKey(Subject,on_delete=models.SET_NULL,related_name='day_courses',null=True)
    name = models.CharField(max_length=100)
    day_timetable = models.ForeignKey(DayTimetable, on_delete=models.CASCADE, related_name='day_courses')
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='day_courses')

    # class Meta:
    # unique_together = ('subject_id', 'timetable')  # Ensure uniqueness within a timetable

    def __str__(self):
        return self.name

class DayTutor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(Teacher,on_delete=models.SET_NULL,related_name='day_tutors',null=True) # Changed to UUIDField and removed unique constraint
    name = models.CharField(max_length=100)
    day_timetable = models.ForeignKey(DayTimetable, on_delete=models.CASCADE, related_name='day_tutors')
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='day_tutors')

    # class Meta:
        # unique_together = ('teacher_id', 'timetable')  # Ensure uniqueness within a timetable

    def __str__(self):
        return self.name

class DayClassroomAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room,on_delete=models.SET_NULL,related_name='day_classroom_asingments',null=True)  # Changed to UUIDField and removed unique constraint
    name = models.CharField(max_length=100)
    capacity = models.IntegerField()
    room_type = models.CharField(max_length=50)
    occupied = models.BooleanField(default=False)
    timetable = models.ForeignKey(DayTimetable, on_delete=models.CASCADE, related_name='day_classroom_assignments')
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='day_classroom_assignments')

    # class Meta:
        # unique_together = ('room_id', 'timetable')  # Ensure uniqueness within a timetable

    def __str__(self):
        return self.name
    
    
    
    
    
    
    
    
    
    
class TeacherActivityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField()
    period = models.IntegerField()
    activity_type = models.CharField(
        max_length=20,
        choices=[
            ("leave", "Leave"),
            ("extra_load", "Extra Load")
        ],
    )
    primary_teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name="activities",  # Teacher whose activity (leave or extra load) is being recorded.
    )
    substitute_teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="substitute_activities",  # Teacher taking the extra load, if applicable.
    )
    day_lesson = models.ForeignKey(
        DayLesson,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activity_logs",  # Links the log to a specific lesson.
    )
    remarks = models.TextField(blank=True, null=True)  # Optional field for additional comments.

    class Meta:
        unique_together = ("date", "period", "primary_teacher")  # Prevent duplicate records for the same teacher, date, and period.
        indexes = [
            models.Index(fields=["date", "primary_teacher", "activity_type"]),
        ]

    def __str__(self):
        if self.activity_type == "leave":
            return f"{self.primary_teacher.name} - Leave on {self.date} (Period {self.period})"
        elif self.activity_type == "extra_load":
            return f"{self.substitute_teacher.name} took extra load for {self.primary_teacher.name} on {self.date} (Period {self.period})"