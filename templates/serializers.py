# serializers.py
from rest_framework import serializers
from authentication.models import Template, Question

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'
        extra_kwargs = {'template': {'required': False}}

class TemplateSerializer(serializers.ModelSerializer):
    # questions = QuestionSerializer(many=True)  # Nested QuestionSerializer
    questions = QuestionSerializer(many=True, read_only=True, source='question_set')

    class Meta:
        model = Template
        fields = '__all__'

    def create(self, validated_data):
        request = self.context.get('request')
        questions_data = validated_data.pop('questions', [])
        
        # Create the template
        template = Template.objects.create(**validated_data)
        
        # Set the updated_by field
        if request and request.user:
            template.created_by = request.user
            template.save()
        
        # Create related questions
        for question_data in questions_data:
            questions=Question.objects.create(template=template, **question_data)
            questions.created_by = request.user
            questions.save()

        return template
  
    

    # def update(self, instance, validated_data):
    #     instance.label = validated_data.get('label', instance.label)
    #     instance.system_promt_acron_analytic_service = validated_data.get('system_promt_acron_analytic_service', instance.system_promt_acron_analytic_service)
    #     instance.system_promt_acron_safety_service = validated_data.get('system_promt_acron_safety_service', instance.system_promt_acron_safety_service)
    #     instance.system_promt_acron_srs = validated_data.get('system_promt_acron_srs', instance.system_promt_acron_srs)

    #     # Save the updated parent model
    #     instance.save()
    #     questions_data = validated_data.pop('questions', [])
        
    #     print("questions_data", questions_data)
    #     for question_data in questions_data:
    #         question_data['template'] = instance.id            
    #         question_id = question_data.get('question_id')
    #         print("question_data: ", question_data)
    #         print("question_id: ", question_id)
            
    #         question_id = question_data['question_id']
    #         print("question_data after setting template:", question_data)
    #         print("question_id:", question_id)

    #         if question_id:
    #             # If the question has an ID, update the existing question
    #             question_instance = Question.objects.get(id=question_id, template=instance)
    #             question_serializer = QuestionSerializer(question_instance, data=question_data)
    #         else:
    #             # If the question doesn't have an ID, create a new question
    #             question_serializer = QuestionSerializer(data=question_data)

    #         if question_serializer.is_valid():
    #             question_serializer.save()

    #     return instance
    