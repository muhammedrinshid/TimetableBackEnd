from django.contrib.auth.models import AbstractUser, BaseUserManager
import uuid
from django.db import models
from django.db.models import UniqueConstraint,Max,Sum
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField




















# this will alter the abstract user creating and super user creatiion
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)
    
    
    
    




class User(AbstractUser):
    
    def get_working_days_display(self):
        return [dict(self.DAYS_OF_WEEK).get(day, day) for day in self.working_days]
    def get_working_days_codes(self):
        return self.working_days
    username = None  # Remove username field
    id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, primary_key=True)
    
    # Basic Fields
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    school_name = models.CharField(max_length=255, default='Unnamed School')   
    school_id = models.CharField(max_length=50, unique=True)

    # Address Fields
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
     #Image Field
    profile_image = models.ImageField(upload_to='school_profiles/', blank=True, null=True)

    
    # School-specific Fields
    DAYS_OF_WEEK = [
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
        ('SAT', 'Saturday'),
        ('SUN', 'Sunday'),
    ]
    working_days = ArrayField(
    models.CharField(max_length=3, choices=DAYS_OF_WEEK),
    default=list,
    blank=True
)
    teaching_slots = models.PositiveIntegerField(default=0)
    average_students_allowed_in_a_class=models.PositiveIntegerField(null=True,blank=True,default=40)
    period_name=models.CharField(blank=True,null=True,default="session")

    @property
    def all_classes_subject_assigned_atleast_one_teacher(self):
 
        class_subject_subjects = self.class_subject_subjects.all()
        return class_subject_subjects.exists() and all(css.has_assigned_teacher for css in class_subject_subjects)
    @property 
    def all_classes_assigned_subjects(self):
        class_rooms=self.classrooms.all()
        return class_rooms.exists() and all(room.is_fully_allocated_subjects_to_class_rooms  for room in class_rooms)
    @property
    def all_class_subjects_have_correct_elective_groups(self):
        class_subjects = self.class_subjects.all()
        
        if not class_subjects.exists():
            return False  # Or True, depending on how you want to handle schools with no class subjects
        
        return all(
            class_subject.elective_group_added_correctly 
            for class_subject in class_subjects
        )
        
    @property
    def all_classrooms_have_rooms(self):
        return not self.classrooms.filter(room__isnull=True).exists()
    @property
    def all_classrooms_have_class_teacher(self):
        # If 'assign_class_teacher_at_first_period' is false, consider timetable ready
        if not self.constraint_settings.assign_class_teacher_at_first_period:
            return True
        
        # Use the 'is_class_teacher_assigned' property from Classroom model
        return not self.classrooms.filter(class_teacher__isnull=True).exists()

    @property
    def is_ready_for_timetable(self):
        return (self.all_classes_subject_assigned_atleast_one_teacher and 
                self.all_classes_assigned_subjects and 
                self.all_class_subjects_have_correct_elective_groups and
                self.all_classrooms_have_rooms and
                self.all_classrooms_have_class_teacher
                ) 


    # Role field (for future use)
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('TEACHER', 'Teacher'),
        ('STUDENT', 'Student'),
        ('PARENT', 'Parent'),
        ('STAFF', 'Staff'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['school_name', ]

    objects = CustomUserManager()
    
    def save(self, *args, **kwargs):
        if not self.school_id:
            last_school = User.objects.order_by('-school_id').first()
            if last_school:
                last_id = int(last_school.school_id[2:])
                self.school_id = f'SC{last_id + 1:04d}'
            else:
                self.school_id = 'SC0001'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.school_name} (UUID: {self.id})" if self.school_name else f"{self.email} (UUID: {self.id})"

    class Meta:
        verbose_name = 'School'
        verbose_name_plural = 'Schools'
        
class DayChoices(models.TextChoices):
    MONDAY = 'MON', 'Monday'
    TUESDAY = 'TUE', 'Tuesday'
    WEDNESDAY = 'WED', 'Wednesday'
    THURSDAY = 'THU', 'Thursday'
    FRIDAY = 'FRI', 'Friday'
    SATURDAY = 'SAT', 'Saturday'
    SUNDAY = 'SUN', 'Sunday'

class UserAcademicSchedule(models.Model):
  
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='academic_schedule'
    )
    average_students_allowed = models.PositiveIntegerField(
        default=40, 
        null=True, 
        blank=True
    )
    period_name = models.CharField(
        max_length=50, 
        default="session", 
        null=True, 
        blank=True
    )

    def __str__(self):
        return f"Schedule for {self.user.username}"

    @property
    def total_weekly_teaching_slots(self):
        """
        Calculate total teaching slots across all working days in the week
        """
        return sum(
            day_schedule.teaching_slots 
            for day_schedule in self.day_schedules.all()
        )

class DaySchedule(models.Model):
    schedule = models.ForeignKey(
        'UserAcademicSchedule', 
        on_delete=models.CASCADE, 
        related_name='day_schedules'
    )
    day = models.CharField(
        max_length=3, 
        choices=DayChoices.choices
    )
    teaching_slots = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ['schedule', 'day']
        ordering = ['day']

    def __str__(self):
        return f"{self.get_day_display()} - {self.teaching_slots} slots"    
    
class UserConstraintSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='constraint_settings')

    # Hard constraints (not changeable)
    room_conflict = models.BooleanField(default=True, editable=False)
    teacher_conflict = models.BooleanField(default=True, editable=False)
    student_group_conflict = models.BooleanField(default=True, editable=False)

    # Changeable constraints
    elective_group_timeslot = models.BooleanField(default=True)
    ensure_teacher_assigned = models.BooleanField(default=True)
    ensure_timeslot_assigned = models.BooleanField(default=True)
    consecutive_multi_block_lessons = models.BooleanField(default=False)
    avoid_first_half_period = models.BooleanField(default=False) 

    # Soft constraints
    tutor_free_period_constraint= models.BooleanField(default=True)
    tutor_lesson_load = models.BooleanField(default=True)
    daily_lesson_limit = models.BooleanField(default=True)
    prefer_consistent_teacher_for_subject = models.BooleanField(default=True)
    prefer_subject_once_per_day = models.BooleanField(default=True)
    avoid_teacher_consecutive_periods_overlapping_class = models.BooleanField(default=True)
    avoid_continuous_subjects = models.BooleanField(default=True)
    avoid_continuous_teaching = models.BooleanField(default=True)
    avoid_consecutive_elective_lessons = models.BooleanField(default=True)
    avoid_elective_in_first_period = models.BooleanField(default=True)  
    assign_class_teacher_at_first_period = models.BooleanField(default=False)
    same_teacher_first_period_constraint = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Constraint Settings for {self.user.username}"    

    
     
     
     
     
     
     
     
     
        
class Subject(models.Model):
    """
    Subject model representing each subject taught in a school.
    It includes a UUID primary key, name, and a relationship to the school.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, blank=False, null=False)
    school = models.ForeignKey(User, related_name='subjects', on_delete=models.CASCADE)

    def __str__(self):
        return self.name
        



class Grade(models.Model):
    """
    Grade model representing each grade in a school (e.g., Higher Secondary, High School, Upper Primary).
    It includes a UUID primary key, name, short name, school relationship,
    and timestamps for creation and last update.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=20)
    school = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Grade"
        verbose_name_plural = "Grades"
        ordering = ['name']

    def __str__(self):
        return self.name
    
    
    
    
class Teacher(models.Model):
    """
    Teacher model representing each teacher in a school with their details
    and qualified subjects. It includes a UUID primary key, relationships to school,
    subjects, and grades, and fields for personal information, lesson constraints,
    a custom teacher ID, profile image, and timestamps for creation and last update.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(User, related_name='teachers', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=False, null=False)
    surname = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(unique=False,blank=True,null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    qualified_subjects = models.ManyToManyField('Subject', related_name='qualified_teachers')
    grades = models.ManyToManyField('Grade', related_name='teachers')
    min_lessons_per_week = models.PositiveIntegerField()
    max_lessons_per_week = models.PositiveIntegerField()
    teacher_id = models.CharField(max_length=20, editable=True, null=True)
    profile_image = models.ImageField(upload_to='teacher_profiles/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(min_lessons_per_week__lte=models.F('max_lessons_per_week')),
                name='min_lessons_lte_max_lessons'
            )
        ]

        unique_together = ('school', 'teacher_id')


    def __str__(self):
        return f"{self.name} {self.surname}" if self.surname else self.name







    def save(self, *args, **kwargs):
        if not self.teacher_id:
            # Auto-generate teacher_id if not provided
            last_teacher = Teacher.objects.all().order_by('teacher_id').last()
            if last_teacher:
                last_id = int(last_teacher.teacher_id[1:])
                self.teacher_id = f'T{last_id + 1:04d}'
            else:
                self.teacher_id = 'T0001'
        super().save(*args, **kwargs)
        
        
        
class Room(models.Model):
    ROOM_TYPES = [
        ('CLASSROOM', 'Classroom'),
        ('OFFICE', 'Office'),
        ('COMPUTER_LAB', 'Computer Lab'),
        ('LECTURE_HALL', 'Lecture Hall'),
        ('CONFERENCE_ROOM', 'Conference Room'),
        ('LABORATORY', 'Laboratory'),
        ('STUDY_AREA', 'Study Area'),
        ('OTHER', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, null=True, blank=True)
    room_number = models.CharField(max_length=20)
    school = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    occupied = models.BooleanField(default=False)
    room_type = models.CharField(
        max_length=20,
        choices=ROOM_TYPES,
        default='CLASSROOM',
    )

    class Meta:
        unique_together = ['room_number', 'school']

    def __str__(self):
        return self.name

class Standard(models.Model):
    """
    Standard model representing each standard in a school (e.g., LKG, UKG, 1st).
    It includes a UUID primary key, name, short name, school and grade relationships,
    and timestamps for creation and last update.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=20)
    school = models.ForeignKey(User, related_name='standards', on_delete=models.CASCADE)
    grade = models.ForeignKey(Grade, related_name='standards', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

   
class ElectiveGroup(models.Model):
    """
    ElectiveGroup model that represents a group of elective subjects.
    It contains the name of the group. Includes meta options for
    verbose name, plural name, and ordering.
    """

    id = models.UUIDField(default=uuid.uuid4, primary_key=True, unique=True)
    name = models.CharField(max_length=255)
    standard=models.ForeignKey(Standard,on_delete=models.CASCADE,related_name="electives_groups",null=True)
    school = models.ForeignKey(User, related_name='electivegroups',on_delete=models.CASCADE)
    preferred_rooms=models.ManyToManyField(Room,related_name="electvie_grops")
    @property
    def be_included_in_second_selection(self):
        class_subjects_count = self.class_subjects.count()
        if class_subjects_count > 1:
            return True
        elif class_subjects_count == 1:
            class_subject = self.class_subjects.first()
            if class_subject.subjects.count() > 1:
                return True
        return False


      
    def clean(self):
        """
        Custom validation to ensure all ClassSubjects in the group have the same name
        and lessons_per_week.
        """
        class_subjects = self.class_subjects.all()

        if class_subjects.exists():
            # Check if all class subjects have the same name
            first_name = class_subjects.first().name
            if not all(cs.name == first_name for cs in class_subjects):
                raise ValidationError("All ClassSubjects in the group must have the same name.")

            # Check if all class subjects have the same lessons_per_week
            first_lessons_per_week = class_subjects.first().lessons_per_week
            if not all(cs.lessons_per_week == first_lessons_per_week for cs in class_subjects):
                raise ValidationError("All ClassSubjects in the group must have the same lessons_per_week.")

    class Meta:
        verbose_name = "Elective Group"
        verbose_name_plural = "Elective Groups"
        ordering = ['name']
      
class Classroom(models.Model):
    """
    Classroom model with fields for UUID primary key, name, standard, school,
    number of students, room number, class ID, creation and update timestamps,
    and division. Includes methods for subject count and allocation check.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    standard = models.ForeignKey(Standard, related_name='classrooms', on_delete=models.CASCADE)
    school = models.ForeignKey(User, related_name='classrooms', on_delete=models.CASCADE)
    number_of_students = models.PositiveIntegerField(null=True, blank=True,default=0)
    class_id = models.CharField(max_length=20, editable=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    division = models.CharField(max_length=10)
    room = models.OneToOneField(Room, null=True, blank=True, related_name="classroom", on_delete=models.SET_NULL)
    class_teacher = models.OneToOneField(Teacher, null=True, blank=True, related_name="classroom_teacher", on_delete=models.SET_NULL)


   
    @property
    def total_lessons_per_week(self):
        result = self.class_subjects.aggregate(total_lessons=Sum('lessons_per_week'))
        return result['total_lessons'] or 0
    @property
    def is_class_teacher_assigned(self):
        """Checks if a class teacher is assigned to this classroom."""
        return self.class_teacher is not None
    @property
    def is_fully_allocated_subjects_to_class_rooms(self):
        number_of_lessons_in_week=self.school.academic_schedule.total_weekly_teaching_slots

        return self.total_lessons_per_week == number_of_lessons_in_week
    @property
    def lessons_assigned_subjects(self):
        return sum(cs.lessons_per_week for cs in self.class_subjects.all())

    @property
    def subjects_assigned_teacher(self):
        return sum(cs.subjects_with_assigned_teacher for cs in self.class_subjects.all())

    @property
    def total_subjects(self):
        return self.class_subjects.count()
   

    def __str__(self):
        return f'{self.standard} {self.name}'
    
    def save(self, *args, **kwargs):
        if not self.class_id:
            last_class_id = Classroom.objects.aggregate(Max('class_id'))['class_id__max']
            if last_class_id:
                last_number = int(last_class_id[2:])
                new_number = last_number + 1
            else:
                new_number = 1
            self.class_id = f'CR{new_number:04d}'
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['school', 'class_id'], name='unique_class_id_within_school'),
            models.UniqueConstraint(fields=['standard', 'division'], name='unique_standard_division')
        ]
        verbose_name = "Classroom"
        verbose_name_plural = "Classrooms"
        ordering = ['name']  
        
        
        
              
   
class ClassSubject(models.Model):
    """
    ClassSubject model that represents every subject inside a class.
    It contains the name of the subject, type of subject (core or elective),
    and links to elective groups if applicable. Includes meta options for
    verbose name, plural name, and ordering.
    """

    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False, unique=True)
    school = models.ForeignKey(User, related_name='class_subjects',on_delete=models.CASCADE)

    name = models.CharField(max_length=255)
    subjects = models.ManyToManyField(Subject, through='ClassSubjectSubject', related_name="class_subjects")
    lessons_per_week = models.IntegerField(default=1)
    multi_block_lessons = models.PositiveIntegerField(default=1)  # New field

    elective_or_core = models.BooleanField(default=False)
    elective_group = models.ForeignKey(ElectiveGroup, related_name="class_subjects", null=True, blank=True, on_delete=models.SET_NULL)
    class_room=models.ForeignKey(Classroom,on_delete=models.CASCADE,related_name="class_subjects",blank=False)
    prevent_first_half_period =models.BooleanField(default=False)
    
    @property
    def subjects_with_assigned_teacher(self):
        return sum(1 for css in self.subjects.all() if css.has_assigned_teacher)
    @property
    def needs_elective_group(self):
        if not self.elective_or_core:
            return False
        else:
            return len(self.subjects.all()) > 1
    @property
    def elective_group_added_correctly(self):
        if not self.needs_elective_group:
            return True
        else:
            return self.elective_group is not None
    @property
    def be_included_in_first_selection(self):
        if not self.elective_or_core:
            return True

        if len(self.subjects.all()) > 1:
            return False

        if self.elective_group is not None and len(self.elective_group.class_subjects.all()) > 1:
            return False

        return True

    def save(self, *args, **kwargs):
        # Call clean method to perform validation
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        if self.lessons_per_week % self.multi_block_lessons != 0:
            raise ValidationError('lessons_per_week must be divisible by multi_block_lessons.')

        if self.multi_block_lessons > self.lessons_per_week:
            raise ValidationError('multi_block_lessons must be less than or equal to lessons_per_week.')
        if self.elective_or_core and self.elective_group:
            # Check if there's already a class subject with the same elective group in this classroom
            existing = ClassSubject.objects.filter(
                class_room=self.class_room,
                elective_group=self.elective_group
            ).exclude(pk=self.pk)
            
            if existing.exists():
                raise ValidationError("This classroom already has a class subject with this elective group.")


        # Set elective_group to None if elective_or_core is False
        if not self.elective_or_core:
            self.elective_group = None
        
        if not self.elective_or_core and len(self.subjects.all()) > 1:
             raise ValidationError('Core subjects must have at most one subject.')


    class Meta:
        verbose_name = "Class Subject"
        verbose_name_plural = "Class Subjects"
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['class_room', 'elective_group'],
                condition=models.Q(elective_or_core=True),
                name='unique_elective_group_per_classroom'
            )
        ] 
        
class ClassSubjectSubject(models.Model):
    """
    ClassSubjectSubject model with fields for UUID primary key, class subject, subject,
    and assigned teachers. Includes meta options for verbose name, plural name, and ordering.

    This model serves as an intermediate model between ClassSubject and Subject,
    containing the details of teachers assigned for each subject of a class.
    """

    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False, unique=True)
    school = models.ForeignKey(User, related_name='class_subject_subjects',on_delete=models.CASCADE)
    class_subject = models.ForeignKey(ClassSubject, on_delete=models.CASCADE,related_name="class_subject_subjects")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    assigned_teachers = models.ManyToManyField(Teacher, related_name='class_subject_subjects')
    number_of_students=models.PositiveBigIntegerField(null=True,blank=True,default=0)
    preferred_rooms=models.ManyToManyField(Room,related_name="class_subject_subjects")
    @property
    def assigned_teachers_count(self):
        return self.assigned_teachers.count()
    @property
    def has_assigned_teacher(self):
        return self.assigned_teachers_count > 0
        
    def clean(self):
        super().clean()
        
        # Get all siblings (excluding self)
        siblings = self.class_subject.class_subjects.exclude(id=self.id)
        
        # Calculate total number of students from siblings
        total_students = sum(sibling.number_of_students for sibling in siblings if sibling.number_of_students is not None)
        
        # Add the current instance's number_of_students
        if self.number_of_students is not None:
            total_students += self.number_of_students
        
        # Get the classroom's total capacity
        classroom_capacity = self.class_subject.class_room.number_of_students
        
        if total_students > classroom_capacity:
            raise ValidationError(f"Total number of students ({total_students}) exceeds the classroom capacity ({classroom_capacity}).")
    class Meta:
        verbose_name = "Class Subject Subject"
        verbose_name_plural = "Class Subject Subjects"
        ordering = ['class_subject', 'subject']
        
        
        
        
        
        
        
        
        
        
    
        
  