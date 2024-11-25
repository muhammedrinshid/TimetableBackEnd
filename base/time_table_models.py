import uuid
from django.db import models

from .models import User
from django.dispatch import receiver
from django.db.models.signals import post_save

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
