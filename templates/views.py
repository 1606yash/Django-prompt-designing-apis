# templates/views.py
import os
from rest_framework.decorators import api_view,permission_classes,renderer_classes
from rest_framework import status
from authentication.models import Template, Question, UserFavTemplates, Companies
from helpers import *
from authentication.api.renderers import UserRenderer
from rest_framework.permissions import IsAuthenticated
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
import requests
import json
from django.http import StreamingHttpResponse
from messages import common
import zlib
import base64
from django.http import HttpResponse
from django.shortcuts import render



@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@renderer_classes([UserRenderer])
def template_list(request):
    current_user = request.user
    if not current_user.is_admin:
        return send_failure_response(data=request.data, message=common["messages"]["USER_NOT_ADMIN"], code=status.HTTP_403_FORBIDDEN)
    if request.method == 'GET':
        page_number = request.GET.get('page', 1)
        per_page = request.GET.get('per_page', 10)
        search_query = request.GET.get('search', '')
        templates = Template.objects.filter(deleted_at=None)
        if search_query:
            templates = templates.filter(label__icontains=search_query)
        print('search_query', search_query)

        templates = templates.order_by('-created_at')  # order by descending creation date
        paginator = Paginator(templates, per_page)

        try:
            templates_paginated = paginator.page(page_number)
        except PageNotAnInteger:
            templates_paginated = paginator.page(1)
        except EmptyPage:
            templates_paginated = paginator.page(paginator.num_pages)

        template_data = []
        for template in templates_paginated:
            questions_data = []
            questions = template.question_set.all()  # Use the default related name
            for question in questions:
                question_data = {
                    'id': question.id,
                    'question_text': question.question_text,
                    'description': question.description,
                }
                questions_data.append(question_data)

            template_data.append({
                'id': template.id,
                'label': template.label,
                'system_promt_acron_analytic_service':  '' if template.system_promt_acron_analytic_service is None or template.system_promt_acron_analytic_service == '' else template.system_promt_acron_analytic_service,
                'system_promt_acron_safety_service': '' if template.system_promt_acron_safety_service is None or template.system_promt_acron_safety_service == '' else template.system_promt_acron_safety_service ,
                'system_promt_acron_srs':  '' if template.system_promt_acron_srs is None or template.system_promt_acron_srs == '' else template.system_promt_acron_srs,
                'is_active': template.is_active,
                'created_at': template.created_at.strftime("%d %b %Y %I:%M %p"),
                'updated_at': template.updated_at.strftime("%d %b %Y %I:%M %p") if template.updated_at else None,
                'deleted_at': template.deleted_at.strftime("%d %b %Y %I:%M %p") if template.deleted_at else None,
                'questions': questions_data,
                'created_by_id': template.created_by_id,
                'updated_by_id': template.updated_by_id,
                'deleted_by_id': template.deleted_by_id,
            })
        context = {
                'template_data': template_data,  
                'page': templates_paginated.number,
                'pages': paginator.num_pages,
                'per_page': per_page,
                'total': paginator.count,
            }
        return send_success_response(context, message="Template data.")
    elif request.method == 'POST':
        try:
            # Extract data from the request
            with transaction.atomic():
                data = request.data
                label = data.get('label')
                # company_id = data.get('company_id')

                if label is None or label == '':
                    return send_failure_response(data=request.data, message=common["messages"]["LABEL_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
        
                if len(label) > 250:
                    return send_failure_response(data=request.data, message=common["messages"]["LABEL_LEN_LIMIT"], code=status.HTTP_400_BAD_REQUEST)
               
                if Template.objects.filter(label=label,deleted_at=None).first():
                    return send_failure_response(data=request.data, message=common["messages"]["TEMPLATE_ALREADY_EXISTS"], code=status.HTTP_422_UNPROCESSABLE_ENTITY)

                system_promt_acron_analytic_service = data.get('system_promt_acron_analytic_service')
                system_promt_acron_safety_service = data.get('system_promt_acron_safety_service')
                system_promt_acron_srs = data.get('system_promt_acron_srs')
                questions_data = data.get('questions', [])
               
                # Create the Template instance
                template = Template.objects.create(
                    label=label,
                    system_promt_acron_analytic_service=None if system_promt_acron_analytic_service is None or system_promt_acron_analytic_service == '' else system_promt_acron_analytic_service,
                    system_promt_acron_safety_service=None if system_promt_acron_safety_service is None or system_promt_acron_safety_service == '' else system_promt_acron_safety_service ,
                    system_promt_acron_srs=None if system_promt_acron_srs is None or system_promt_acron_srs == '' else system_promt_acron_srs,
                    # company_id=company_id,
                    created_by=request.user
                )
                

                # Create related Question instances
                for question_data in questions_data:
                    question_text = question_data.get('question_text')
                    description = question_data.get('description')
                    
                    Question.objects.create(
                        template=template,
                        question_text= question_text,
                        description= description,
                    )

                # Serialize the template data for response
                # template_serializer = TemplateSerializer(template)
                return send_success_response(data=request.data, message=common["messages"]["TEMPLATE_CREATED_SUCCESS"], code=status.HTTP_201_CREATED)

        except Exception as e:
            print(e)
            error_message = str(e.args[1]) if e.args else common["messages"]["SOMETHING_WENT_WRONG"]
            return send_failure_response(data=request.data, message=error_message, code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
@permission_classes([IsAuthenticated])
@renderer_classes([UserRenderer])
@api_view(['POST'])
def template_update(request):
    current_user = request.user
    if not current_user.is_admin:
        return send_failure_response(data=request.data, message=common["messages"]["USER_NOT_ADMIN"], code=status.HTTP_403_FORBIDDEN)
   
    # template = get_object_or_404(Template, pk=request.data.get('id'))    
    try:
        template = Template.objects.get(id=request.data.get('id'))
    except Template.DoesNotExist:
        return send_failure_response(request.data, message=common["messages"]["TEMPLATE_NOT_FOUND"], code=status.HTTP_404_NOT_FOUND)
    data = request.data
    label = data.get('label')
    # company_id = data.get('company_id')

    if label is None or label == '':
        return send_failure_response(data=request.data, message=common["messages"]["LABEL_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
    if len(label) > 250:
        return send_failure_response(data=request.data, message=common["messages"]["LABEL_LEN_LIMIT"], code=status.HTTP_400_BAD_REQUEST)
   
    questions_data = data.get('questions', [])
    # Update the Template instance
    with transaction.atomic():
        template.label = label

        system_promt_acron_analytic_service = data.get('system_promt_acron_analytic_service')
        system_promt_acron_safety_service = data.get('system_promt_acron_safety_service')
        system_promt_acron_srs = data.get('system_promt_acron_srs')

        template.system_promt_acron_analytic_service=None if system_promt_acron_analytic_service is None or system_promt_acron_analytic_service == '' else system_promt_acron_analytic_service
        template.system_promt_acron_safety_service=None if system_promt_acron_safety_service is None or system_promt_acron_safety_service == '' else system_promt_acron_safety_service
        template.system_promt_acron_srs=None if system_promt_acron_srs is None or system_promt_acron_srs == '' else system_promt_acron_srs
        template.save()

        # Update or create related Question instances
        questions_ids_arr = []
        for question_data in questions_data:
            question_id = question_data.get('id')
            question_text = question_data.get('question_text')
            description = question_data.get('description')

            if question_id:
                try:
                    question = Question.objects.get(id=question_id, template=template)
                except Question.DoesNotExist:
                    # Handle the case where the Question does not exist
                    return send_failure_response(request.data, message=common["messages"]["QUESTION_NOT_FOUND"], code=status.HTTP_404_NOT_FOUND)

                question.question_text = question_text
                question.description = description
                question.save()
                questions_ids_arr.append(question.id)
            else:
                # If question_id is not provided, create a new Question instance
                new_question = Question.objects.create(template=template, question_text=question_text, description=description)
                questions_ids_arr.append(new_question.id)

        Question.objects.exclude(id__in=questions_ids_arr).filter(template_id=template.id).delete()

    return send_success_response(data=request.data, message=common["messages"]["TEMPLATE_UPDATED_SUCCESS"], code=status.HTTP_200_OK)
        


@permission_classes([IsAuthenticated])
@renderer_classes([UserRenderer])
@api_view(['DELETE'])     
def template_delete(request, template_id = None):
    try:
        template = Template.objects.get(id=template_id, deleted_at=None)
    except Template.DoesNotExist:
        return send_failure_response(request.data, message=common["messages"]["TEMPLATE_NOT_FOUND"], code=status.HTTP_404_NOT_FOUND)
    # Delete logic
    template.delete(request.user)
    return send_success_response(request.data, code=status.HTTP_200_OK, message=common["messages"]["TEMPLATE_DELETED_SUCCESS"])
 
@permission_classes([IsAuthenticated])
@api_view(['GET'])
def template_detail(request, template_id):   
    try:
        template = Template.objects.get(id=template_id, deleted_at=None)
    except Template.DoesNotExist:
        return send_failure_response(code=status.HTTP_404_NOT_FOUND, message=common["messages"]["TEMPLATE_NOT_FOUND"])
    questions_data = []

    current_user = request.user
   
    questions = template.question_set.all()  # Use the default related name
    for question in questions:
        question_data = {
            'id': question.id,
            'question_text': question.question_text,
            'description': question.description,
        }
        questions_data.append(question_data)
        
    company_id = current_user.company_id
    template_data = {
        'id': template.id,
        'label': template.label,
        'created_at': template.created_at.strftime("%d %b %Y %I:%M %p"),
        'updated_at': template.updated_at.strftime("%d %b %Y %I:%M %p") if template.updated_at else None,
        'deleted_at': template.deleted_at.strftime("%d %b %Y %I:%M %p") if template.deleted_at else None,
        'questions': questions_data,
    }
    print("company_id", company_id)
    if current_user.is_admin:
        template_data['system_promt_acron_analytic_service'] = template.system_promt_acron_analytic_service
        template_data['system_promt_acron_safety_service'] = template.system_promt_acron_safety_service
        template_data['system_promt_acron_srs'] = template.system_promt_acron_srs
    else:
        try:
            company = Companies.objects.get(id=company_id)  # Use .get() for clarity
        except Companies.DoesNotExist:
            company = ""  # Handle the case where the ID doesn't exist

      
        if company != "" :
            template_data['company_text'] = ""
            if(company.name == common["companies"]["ANALYTICAL_SERVICES"]):
                if (template.system_promt_acron_analytic_service != None and template.system_promt_acron_analytic_service  != ""):
                    template_data['company_text'] =template.system_promt_acron_analytic_service
            elif(company.name == common["companies"]["SAFETY_SERVICES"]):
                if (template.system_promt_acron_safety_service != None and template.system_promt_acron_safety_service  != ""):
                    template_data['company_text'] =template.system_promt_acron_safety_service
            elif(company.name == common["companies"]["SPECIALIST_SERVICES"]):
                if (template.system_promt_acron_srs != None and template.system_promt_acron_srs  != ""):
                    template_data['company_text'] = template.system_promt_acron_srs


    return send_success_response(template_data)

# template view page for the user
@permission_classes([IsAuthenticated])
@renderer_classes([UserRenderer])
@api_view(['GET'])
def template_list_user(request):
    if request.method == 'GET':
        page_number = request.GET.get('page', 1)
        per_page = request.GET.get('per_page', 10)
        search_query = request.GET.get('search', '')

        favourite = int(request.GET.get('favourite', 0))
        user = request.user
        user_id = user.id
        company_id = user.company_id
        if favourite:
            # Get userTemplateIds
            favourite_template_ids = UserFavTemplates.objects.filter(user_id=user_id).values_list('template_id', flat=True)

            # Get templates using userTemplateIds
            templates = Template.objects.filter(id__in=favourite_template_ids, is_active=1, deleted_at=None)
        else:
            templates = Template.objects.filter(is_active=1, deleted_at=None)

        if search_query:
            templates = templates.filter(label__icontains=search_query)
        
        print("search_query", search_query)
        templates = templates.order_by('-created_at')  # order by descending creation date
        paginator = Paginator(templates, per_page)
        
        try:
            templates_paginated = paginator.page(page_number)
        except PageNotAnInteger:
            templates_paginated = paginator.page(1)
        except EmptyPage:
            templates_paginated = paginator.page(paginator.num_pages)

        template_data = []
        for template in templates_paginated:
            questions_data = []
            questions = template.question_set.all()  # Use the default related name
            template_id = template.id
            current_user = request.user

            for question in questions:
                question_data = {
                    'id': question.id,
                    'question_text': question.question_text,
                    'description': question.description,
                }
                questions_data.append(question_data)

            is_favourite = False                
            if(UserFavTemplates.objects.filter(user_id=current_user.id, template_id=template_id).first()):                        
                is_favourite = True

            template_data.append({
                'id': template_id,
                'label': template.label,
                'system_promt_acron_analytic_service': template.system_promt_acron_analytic_service,
                'system_promt_acron_safety_service': template.system_promt_acron_safety_service,
                'system_promt_acron_srs': template.system_promt_acron_srs,
                # 'company_id': template.company_id,
                # 'company': template.company.name if template.company else None,
                'is_favourite': is_favourite,
                'created_at': template.created_at.strftime("%d %b %Y %I:%M %p"),
                'updated_at': template.updated_at.strftime("%d %b %Y %I:%M %p") if template.updated_at else None,
                'deleted_at': template.deleted_at.strftime("%d %b %Y %I:%M %p") if template.deleted_at else None,
                'questions': questions_data,
            })
        # return Response(template_data)

        context = {
                'template_data': template_data,  
                'page': templates_paginated.number,
                'pages': paginator.num_pages,
                'per_page': per_page,
                'total': paginator.count,
            }
        
        return send_success_response(context, message="Template data.")
  
# template user favourite for the user
@api_view(['POST'])
@renderer_classes([UserRenderer])
def user_favourite_template(request):
    # Extract data from the request
    data = request.data
    user_id = request.user.id
    template_id = data.get('template_id')
    mark_as_favourite = int(data.get('mark_as_favourite'))
    if template_id is None:
        return send_failure_response(message=common["messages"]["TEMPLATE_NOT_FOUND"], code=status.HTTP_400_BAD_REQUEST)
    try:
        template = Template.objects.get(id=template_id,  deleted_at=None)
    except Template.DoesNotExist:
        return send_failure_response(request.data, message=common["messages"]["TEMPLATE_NOT_FOUND"], code=status.HTTP_404_NOT_FOUND)
    
    mark_as_favourite_exist = UserFavTemplates.objects.filter(user_id=user_id, template_id=template_id).first()
    if(mark_as_favourite):
        if(mark_as_favourite_exist):
            return send_failure_response(data=request.data, message=common["messages"]["TEMPLATE_ALREADY_MARKED_AS_FAVOURITE"], code=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # Create the Template instance
        try:
            UserFavTemplates.objects.create(
                user_id=user_id,
                template_id=template_id,
                created_by=request.user
            )
            return send_success_response(data=request.data, message=common["messages"]["TEMPLATE_MARKED_AS_FAVOURITE_SUCCESS"], code=status.HTTP_200_OK)
        except Exception as e:
            error_message = str(e.args[1]) if e.args else common["messages"]["SOMETHING_WENT_WRONG"]
            return send_failure_response(data=request.data, message=error_message, code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        if(not mark_as_favourite_exist):
            return send_failure_response(data=request.data, message=common["messages"]["TEMPLATE_NOT_MARKED_AS_FAVOURITE"], code=status.HTTP_422_UNPROCESSABLE_ENTITY)

        if mark_as_favourite_exist.delete():
            return send_success_response(data=request.data, message=common["messages"]["TEMPLATE_UNMARKED_AS_FAVORITE"], code=status.HTTP_200_OK)



@api_view(['POST'])
@renderer_classes([UserRenderer])
def template_update_status(request):
    # Extract data from the request
    data = request.data
    user = request.user
    template_id = data.get('template_id')
    new_status = data.get('status')
    if template_id is None or template_id == '':
        return send_failure_response(message=common["messages"]["TEMPLATE_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
    
    if new_status is None or new_status == '':
        return send_failure_response(message=common["messages"]["STATUS_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)

    new_status = int(new_status)
    try:
        template = Template.objects.get(id=template_id,  deleted_at=None)
    except Template.DoesNotExist:
        return send_failure_response(request.data, message=common["messages"]["TEMPLATE_NOT_FOUND"], code=status.HTTP_404_NOT_FOUND)
    
    template.is_active = new_status
    template.updated_by = user
    template.save()
    return send_success_response(data=request.data, message=common["messages"]["TEMPLATE_STATUS_CHANGED_SUCCESS"], code=status.HTTP_200_OK)
    
@api_view(['POST'])
@renderer_classes([UserRenderer])
def generate_chatgpt_output_helper(request):
    try:
        data = request.data
        label = data.get('label')
        request_questions_with_answers = data.get('question_n_answer')
        company_text = data.get('company_text')

        if label is None or label == '':
            return send_failure_response(message=common["messages"]["LABEL_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)

        if len(request_questions_with_answers) < 1:
            return send_failure_response(message=common["messages"]["QUESTION_ANSWER_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)

        question_n_answer = '' + label
        question_n_answer += company_text
        for request_questions_with_answer in request_questions_with_answers:
            question_n_answer += request_questions_with_answer['question_text'] + "  "
            question_n_answer += request_questions_with_answer['answer'] + "  "

        text_bytes = question_n_answer.encode('utf-8')
        compressed_data = zlib.compress(text_bytes)
        encoded_data = base64.b64encode(compressed_data).decode('utf-8')
        result = {'encoded_data': encoded_data}
        return send_success_response(data= result)
    except Exception as e:
        return send_failure_response(message="Error processing the request.", code=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['GET'])
def generate_chatgpt_output(request):
    try:
        
        questions_with_answer = "Write poem on mahatama gandhi on 200 words"
        api_key = os.environ.get('OPENAI_APIKEY')
        model = "gpt-3.5-turbo"
        data = {
            'model': model,
            'stream': True,
            'messages': [
                {
                    'role': 'user',
                    'content': questions_with_answer
                }
            ]
        }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + api_key
        }

        def generate_chunks():
            response = requests.post('https://api.openai.com/v1/chat/completions', data=json.dumps(data), headers=headers, stream=True)

            if response.status_code == 200:
                for chunk in response.iter_content(chunk_size=None):
                    if chunk:
                        yield chunk
            else:
                yield f'Request failed with status code: {response.status_code}'.encode('utf-8')

        return StreamingHttpResponse(generate_chunks(), content_type='text/event-stream')
    except Exception as e:
        return send_failure_response(message=common["messages"]["INT_SERVER_ERR"], code=status.HTTP_400_BAD_REQUEST)

