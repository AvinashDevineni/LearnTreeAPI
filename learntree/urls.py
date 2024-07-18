from django.urls import path
from .views import generate_topics

urlpatterns = [
    path('topics', generate_topics)
]