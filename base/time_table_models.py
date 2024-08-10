import uuid
from django.db import models
from django.contrib.auth import get_user_model

from .models import User


class Timetable(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='timetables')
    score = models.IntegerField(null=True, blank=True)
    optimal = models.BooleanField(default=False)
    feasible = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class StandardLevel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    standard_id = models.UUIDField()  # Changed to UUIDField and removed unique constraint
    name = models.CharField(max_length=50)
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='standard_levels')
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='standard_levels')

    class Meta:
        unique_together = ('standard_id', 'timetable')  # Ensure uniqueness within a timetable

    def __str__(self):
        return self.name

class ClassSection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    classroom_id = models.UUIDField()  # Changed to UUIDField and removed unique constraint
    standard = models.ForeignKey(StandardLevel, on_delete=models.CASCADE)
    division = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='class_sections')
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='class_sections')

    class Meta:
        unique_together = ('classroom_id', 'timetable')  # Ensure uniqueness within a timetable

    def __str__(self):
        return f"{self.standard.name} - {self.division}"

class Course(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject_id = models.UUIDField()  # Changed to UUIDField and removed unique constraint
    name = models.CharField(max_length=100)
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='courses')
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses')

    class Meta:
        unique_together = ('subject_id', 'timetable')  # Ensure uniqueness within a timetable

    def __str__(self):
        return self.name

class Tutor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher_id = models.UUIDField()  # Changed to UUIDField and removed unique constraint
    name = models.CharField(max_length=100)
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='tutors')
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tutors')

    class Meta:
        unique_together = ('teacher_id', 'timetable')  # Ensure uniqueness within a timetable

    def __str__(self):
        return self.name

class ClassroomAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room_id = models.UUIDField()  # Changed to UUIDField and removed unique constraint
    name = models.CharField(max_length=100)
    capacity = models.IntegerField()
    room_type = models.CharField(max_length=50)
    occupied = models.BooleanField(default=False)
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='classroom_assignments')
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='classroom_assignments')

    class Meta:
        unique_together = ('room_id', 'timetable')  # Ensure uniqueness within a timetable

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
    alotted_teacher = models.ForeignKey(Tutor, on_delete=models.CASCADE, related_name='allotted_lessons')
    # available_teachers = models.ManyToManyField(Tutor, related_name='available_lessons')
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE)
    classroom_assignment = models.ForeignKey(ClassroomAssignment, on_delete=models.CASCADE)
    timeslot = models.ForeignKey(Timeslot, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.course.name} - {self.class_section} - {self.timeslot}"