from rest_framework import serializers
from ...models import User,Grade,Subject,UserConstraintSettings,DaySchedule,UserAcademicSchedule,Period



class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = ['name', 'short_name','id']
        
class PeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Period
        fields = ['period_number', 'start_time', 'end_time']

        
class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['name', 'id']
        
class DayScheduleSerializer(serializers.ModelSerializer):
    periods = PeriodSerializer(many=True, required=False)

    class Meta:
        model = DaySchedule
        fields = ['day', 'teaching_slots', 'periods']

class AcademicScheduleSerializer(serializers.ModelSerializer):
    day_schedules = DayScheduleSerializer(many=True)

    class Meta:
        model = UserAcademicSchedule
        fields = [
            'average_students_allowed',
            'period_name',
            'total_weekly_teaching_slots',
            'day_schedules',
            'academic_year_start',
            'academic_year_end',
            'is_auto_timetable_creation',
        ]

    def update(self, instance, validated_data):
        day_schedules_data = validated_data.pop('day_schedules', [])

        # Update the main schedule fields
        instance.average_students_allowed = validated_data.get('average_students_allowed', instance.average_students_allowed)
        instance.period_name = validated_data.get('period_name', instance.period_name)
        instance.academic_year_end = validated_data.get('academic_year_end', instance.academic_year_end)
        instance.academic_year_start = validated_data.get('academic_year_start', instance.academic_year_start)
        instance.is_auto_timetable_creation = validated_data.get('is_auto_timetable_creation', instance.is_auto_timetable_creation)
        instance.save()

        # Handle day schedules
        instance.day_schedules.all().delete()  # Remove existing schedules
        for day_schedule_data in day_schedules_data:
            periods_data = day_schedule_data.pop('periods', [])
            day_schedule = DaySchedule.objects.create(
                schedule=instance,
                day=day_schedule_data['day'],
                teaching_slots=day_schedule_data['teaching_slots']
            )

            # Create periods for the day schedule
            for period_data in periods_data:
                Period.objects.create(
                    day_schedule=day_schedule,
                    period_number=period_data['period_number'],
                    start_time=period_data.get('start_time', None),
                    end_time=period_data.get('end_time', None),
                )

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        for day_schedule in representation['day_schedules']:
            teaching_slots = day_schedule['teaching_slots']
            periods = day_schedule.get('periods', [])

            # Add empty periods if they are missing
            if len(periods) < teaching_slots:
                existing_period_numbers = {p['period_number'] for p in periods}
                for period_number in range(1, teaching_slots + 1):
                    if period_number not in existing_period_numbers:
                        periods.append({
                            'period_number': period_number,
                            'start_time': None,
                            'end_time': None,
                        })

                # Sort periods by period_number
                day_schedule['periods'] = sorted(periods, key=lambda p: p['period_number'])

        return representation

class UserSerializer(serializers.ModelSerializer):
    profile_image = serializers.ImageField(read_only=True)
    grades = GradeSerializer(many=True, read_only=True, source='grade_set')
    academic_schedule = AcademicScheduleSerializer()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'school_name', 'school_id', 
            'address', 'city', 'state', 'country', 'postal_code', 
            'profile_image', 'academic_schedule', 'teaching_slots', 
            'average_students_allowed_in_a_class', 'period_name',
            'all_classes_subject_assigned_atleast_one_teacher',
            'all_classes_assigned_subjects', 
            'grades',
        ]
        read_only_fields = ['id', 'school_id', 'email', 'profile_image']

    def update(self, instance, validated_data):
        academic_schedule_data = validated_data.pop('academic_schedule', None)
        
        # Update User instance
        instance = super().update(instance, validated_data)

        # Update Academic Schedule if data is provided
        if academic_schedule_data:
            academic_schedule = instance.academic_schedule
            academic_schedule_serializer = AcademicScheduleSerializer()
            academic_schedule_serializer.update(academic_schedule, academic_schedule_data)

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.profile_image:
            representation['profile_image'] = instance.profile_image.url
        return representation
class UserConstraintSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserConstraintSettings
        exclude = ['user']  # Exclude user field as it will be set automatically
        
        def validate(self, data):
        # First validate that both aren't True
            assign_class_teacher = data.get('assign_class_teacher_at_first_period', False)
            same_teacher = data.get('same_teacher_first_period_constraint', False)

            # Automatically set the other to False if one is True
            if assign_class_teacher:
                data['same_teacher_first_period_constraint'] = False
            elif same_teacher:
                data['assign_class_teacher_at_first_period'] = False

            return data

    def update(self, instance, validated_data):
        # Handle partial updates by explicitly setting the opposite field to False
        if 'assign_class_teacher_at_first_period' in validated_data and validated_data['assign_class_teacher_at_first_period']:
            validated_data['same_teacher_first_period_constraint'] = False
        elif 'same_teacher_first_period_constraint' in validated_data and validated_data['same_teacher_first_period_constraint']:
            validated_data['assign_class_teacher_at_first_period'] = False
            
        return super().update(instance, validated_data)