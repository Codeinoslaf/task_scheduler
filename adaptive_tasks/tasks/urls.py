from django.urls import path
from . import views

urlpatterns = [
    path('calendar/', views.calendar_view, name='calendar'),
    path('profile/', views.profile_view, name='profile'),
    path('task-list/', views.task_list_view, name='task_list'),
    path('task/<int:task_id>/complete/', views.complete_task, name='complete_task'),
    path('task/<int:task_id>/delete/', views.delete_task, name='delete_task'),
    path('task/<int:task_id>/edit/', views.edit_task, name='edit_task'),
]