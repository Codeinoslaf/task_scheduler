from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from .models import Task, TaskExecutionStats, UserPerformanceProfile


@login_required
def calendar_view(request):
    user = request.user
    today = now()

    # Обработка POST запроса для создания/обновления задачи
    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        planned_deadline = request.POST.get('planned_deadline')

        if task_id:
            # Обновление существующей задачи
            task = get_object_or_404(Task, id=task_id, user=user)
            task.title = title
            task.description = description
            task.planned_deadline = planned_deadline
            task.save()
        else:
            # Создание новой задачи
            Task.objects.create(
                user=user,
                title=title,
                description=description,
                planned_deadline=planned_deadline
            )

        return redirect('calendar')

    # Получение всех задач пользователя
    tasks = Task.objects.filter(user=user).order_by('planned_deadline')

    # Преобразование задач в JSON для JavaScript
    tasks_json = json.dumps([{
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'planned_deadline': task.planned_deadline.isoformat(),
        'status': task.status
    } for task in tasks])

    return render(request, 'tasks/calendar.html', {
        'tasks': tasks,
        'tasks_json': tasks_json,
        'year': today.year,
        'month': today.month,
    })


@login_required
def profile_view(request):
    user = request.user

    total_tasks = Task.objects.filter(user=user).count()
    completed_tasks = Task.objects.filter(user=user, status='completed').count()
    overdue_tasks = Task.objects.filter(user=user, status='overdue').count()

    avg_delay = TaskExecutionStats.objects.filter(user=user).aggregate(
        Avg('delay_days')
    )['delay_days__avg'] or 0

    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks else 0

    return render(request, 'tasks/profile.html', {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'overdue_tasks': overdue_tasks,
        'avg_delay': round(avg_delay, 2),
        'completion_rate': round(completion_rate, 1),
    })


@login_required
def complete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    task.actual_deadline = now()
    task.status = 'completed'
    task.save()

    delay_days = (task.actual_deadline.date() - task.planned_deadline.date()).days

    TaskExecutionStats.objects.create(
        user=request.user,
        task=task,
        planned_deadline=task.planned_deadline,
        actual_deadline=task.actual_deadline,
        delay_days=delay_days
    )

    return redirect('calendar')


@login_required
@require_POST
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    task.delete()
    return JsonResponse({'success': True})


@login_required
def edit_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)

    if request.method == 'POST':
        task.title = request.POST.get('title')
        task.description = request.POST.get('description', '')
        task.planned_deadline = request.POST.get('planned_deadline')
        task.save()
        return redirect('calendar')

    return JsonResponse({
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'planned_deadline': task.planned_deadline.isoformat()
    })