from django.urls import path

from .views import CategoryView
from .views import CategoryItemView


app_name = "categories"

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('categories/<int:category_id>/', CategoryItemView.as_view()),
    path('categories/', CategoryView.as_view()),
]