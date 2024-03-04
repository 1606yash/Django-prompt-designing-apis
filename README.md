# experienced-ai-backend

# run this command 
python manage.py createsuperuser
python -m venv env
env\Scripts\activate

pip install -r requirements.txt
pip install django
pip install djangorestframework
pip install djangorestframework_simplejwt
pip install mysqlclient
pip install django-dotenv
pip install django-cors-headers
pip install openai

manage.py makemigraions
manage.py migrate

create .env file same as .envExample
with same constants
