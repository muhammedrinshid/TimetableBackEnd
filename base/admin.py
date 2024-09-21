from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.postgres.forms import SimpleArrayField
from .models import User,Subject
from .models import Teacher  # Replace with the correct import path for Teacher model
from .models import Standard, ElectiveGroup, Classroom,Room
from .time_table_models import Timetable, StandardLevel, ClassSection, Course, Tutor, ClassroomAssignment, Timeslot, Lesson,LessonClassSection

@admin.register(Standard)
class StandardAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'school', 'grade', 'created_at', 'updated_at')
    search_fields = ('name', 'short_name')
    list_filter = ('school', 'grade')
    ordering = ('name',)

@admin.register(ElectiveGroup)
class ElectiveGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'school','be_included_in_second_selection')
    search_fields = ('name',)
    list_filter = ('school',)
    ordering = ('name',)
    filter_horizontal = ('preferred_rooms',)

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('name', 'standard', 'school', 'number_of_students', 'class_id', 'division', 'created_at', 'updated_at')
    search_fields = ('name', 'standard__name', 'division')
    list_filter = ('standard', 'school', 'division')
    ordering = ('name',)
    readonly_fields = ('class_id',)

    def save_model(self, request, obj, form, change):
        if not obj.class_id:
            obj.class_id = f'CR{Classroom.objects.count() + 1:04d}'
        super().save_model(request, obj, form, change)
class DaysMultipleChoiceField(forms.MultipleChoiceField):
    def __init__(self, *args, **kwargs):
        kwargs['choices'] = User.DAYS_OF_WEEK
        kwargs['widget'] = forms.CheckboxSelectMultiple
        super().__init__(*args, **kwargs)

    def clean(self, value):
        return [v for v in value if v]  # Remove empty values

class CustomUserAdminForm(forms.ModelForm):
    working_days = DaysMultipleChoiceField(required=False)

    class Meta:
        model = User
        fields = '__all__'

    def clean_working_days(self):
        return self.cleaned_data['working_days']

class CustomUserAdmin(UserAdmin):
    form = CustomUserAdminForm
    model = User
    list_display = ('email', 'school_name', 'school_id', 'is_staff', 'is_active','is_ready_for_timetable')
    list_filter = ('email', 'school_name', 'is_staff', 'is_active',)
    readonly_fields = ('all_classes_subject_assigned_atleast_one_teacher', 'all_classes_assigned_subjects')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('School Info', {'fields': ('school_name', 'school_id', 'phone_number')}),
        ('Address', {'fields': ('address', 'city', 'state', 'country', 'postal_code')}),
        ('School Details', {'fields': ('working_days', 'teaching_slots', 'all_classes_subject_assigned_atleast_one_teacher', 'all_classes_assigned_subjects')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'role')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'school_name', 'school_id', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('email', 'school_name')
    ordering = ('email',)
    
    def all_classes_subject_assigned_atleast_one_teacher(self, obj):
        return obj.all_classes_subject_assigned_atleast_one_teacher
    all_classes_subject_assigned_atleast_one_teacher.short_description = "All classes have at least one teacher assigned"

    def all_classes_assigned_subjects(self, obj):
        return obj.all_classes_assigned_subjects
    all_classes_assigned_subjects.short_description = "All classes have assigned subjects"

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'school')
    list_filter = ('school',)  # Add filters as needed
    search_fields = ('name', 'school__username')  # Search by subject name or school username


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('name', 'surname', 'email', 'phone', 'teacher_id', 'created_at', 'updated_at')
    list_filter = ('school', 'grades', 'qualified_subjects')
    search_fields = ('name', 'surname', 'email', 'teacher_id')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('school', 'name', 'surname', 'email', 'phone', 'profile_image')
        }),
        ('Qualifications', {
            'fields': ('qualified_subjects', 'grades')
        }),
        ('Lesson Constraints', {
            'fields': ('min_lessons_per_week', 'max_lessons_per_week')
        }),
        ('ID and Timestamps', {
            'fields': ('teacher_id', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('teacher_id', 'created_at')
        return self.readonly_fields



class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'room_number', 'school', 'capacity', 'occupied','room_type')
    search_fields = ('name', 'room_number', 'school__username')
    list_filter = ('school', 'occupied')

admin.site.register(Room, RoomAdmin)

admin.site.register(User, CustomUserAdmin)


class StandardLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'standard_id', 'timetable', 'school')
    list_filter = ('timetable', 'school')
    search_fields = ('name', 'standard_id', 'timetable__name', 'school__username')

class ClassSectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'classroom_id', 'standard', 'division', 'timetable', 'school')
    list_filter = ('standard', 'division', 'timetable', 'school')
    search_fields = ('name', 'classroom_id', 'standard__name', 'timetable__name', 'school__username')

class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_subject_ids', 'timetable', 'school')
    list_filter = ('timetable', 'school')
    search_fields = ('name', 'timetable__name', 'school__username')

    def get_subject_ids(self, obj):
        return ', '.join(str(uuid) for uuid in obj.subject_ids)
    get_subject_ids.short_description = 'Subject IDs'

class TutorAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher_id', 'timetable', 'school')
    list_filter = ('timetable', 'school')
    search_fields = ('name', 'teacher_id', 'timetable__name', 'school__username')

class ClassroomAssignmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'room_id', 'capacity', 'room_type', 'occupied', 'timetable', 'school')
    list_filter = ('room_type', 'occupied', 'timetable', 'school')
    search_fields = ('name', 'room_id', 'timetable__name', 'school__username')

class TimeslotAdmin(admin.ModelAdmin):
    list_display = ('day_of_week', 'period', 'timetable', 'school')
    list_filter = ('day_of_week', 'timetable', 'school')
    search_fields = ('day_of_week', 'period', 'timetable__name', 'school__username')
class TimetableAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'score', 'optimal', 'feasible', 'is_default')
    list_filter = ('school', 'optimal', 'feasible', 'is_default')
    search_fields = ('name', 'school__username')
    readonly_fields = ('id', 'created', 'updated')
    autocomplete_fields = ['school']
    fieldsets = (
        (None, {'fields': ('name', 'school')}),
        ('Scores', {'fields': ('score', 'hard_score', 'soft_score')}),
        ('Status', {'fields': ('optimal', 'feasible', 'is_default')}),
        ('Metadata', {'fields': ('created', 'updated', 'id')}),
        ('Lesson Settings', {'fields': ('number_of_lessons',)}),
    )

class LessonAdmin(admin.ModelAdmin):
    list_display = ('course', 'allotted_teacher', 'timeslot', 'timetable', 'school','elective_subject_name')
    list_filter = ('timetable', 'school', 'course')
    search_fields = ('course__name', 'allotted_teacher__name', 'timeslot__day_of_week', 'timetable__name', 'school__username')

    # Display class sections as a list
    def get_class_sections(self, obj):
        return ', '.join(section.name for section in obj.class_sections.all())
    get_class_sections.short_description = 'Class Sections'
@admin.register(LessonClassSection)
class LessonClassSectionAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'class_section', 'number_of_students')
    search_fields = ('lesson__name', 'class_section__name')  # Adjust field names if necessary
    list_filter = ('lesson', 'class_section')
# Register the models with the admin site
admin.site.register(Timetable, TimetableAdmin)
admin.site.register(StandardLevel, StandardLevelAdmin)
admin.site.register(ClassSection, ClassSectionAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Tutor, TutorAdmin)
admin.site.register(ClassroomAssignment, ClassroomAssignmentAdmin)
admin.site.register(Timeslot, TimeslotAdmin)
admin.site.register(Lesson, LessonAdmin)




