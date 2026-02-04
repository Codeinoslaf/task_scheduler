from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from django.db.models import Avg, Count, Q
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
    active_tasks = Task.objects.filter(user=user).exclude(
        Q(status='completed') | Q(status='overdue')
    ).count()

    avg_delay = TaskExecutionStats.objects.filter(user=user).aggregate(
        Avg('delay_days')
    )['delay_days__avg'] or 0

    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks else 0

    return render(request, 'tasks/profile.html', {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'overdue_tasks': overdue_tasks,
        'active_tasks': active_tasks,
        'avg_delay': round(avg_delay, 2),
        'completion_rate': round(completion_rate, 1),
    })


@login_required
def task_list_view(request):
    user = request.user
    filter_type = request.GET.get('filter', 'all')

    # Базовый queryset
    tasks_query = Task.objects.filter(user=user)

    # Применяем фильтр
    if filter_type == 'completed':
        tasks = tasks_query.filter(status='completed').order_by('-actual_deadline')
        page_title = 'Выполненные задачи'
        page_subtitle = 'Все завершенные задачи'
    elif filter_type == 'overdue':
        tasks = tasks_query.filter(status='overdue').order_by('planned_deadline')
        page_title = 'Просроченные задачи'
        page_subtitle = 'Задачи, требующие внимания'
    elif filter_type == 'active':
        tasks = tasks_query.exclude(
            Q(status='completed') | Q(status='overdue')
        ).order_by('planned_deadline')
        page_title = 'Активные задачи'
        page_subtitle = 'Задачи в работе'
    else:
        tasks = tasks_query.order_by('planned_deadline')
        page_title = 'Все задачи'
        page_subtitle = 'Полный список ваших задач'

    # Подсчет для фильтров
    total_count = tasks_query.count()
    completed_count = tasks_query.filter(status='completed').count()
    overdue_count = tasks_query.filter(status='overdue').count()
    active_count = tasks_query.exclude(
        Q(status='completed') | Q(status='overdue')
    ).count()

    return render(request, 'tasks/task_list.html', {
        'tasks': tasks,
        'page_title': page_title,
        'page_subtitle': page_subtitle,
        'current_filter': filter_type,
        'total_count': total_count,
        'completed_count': completed_count,
        'overdue_count': overdue_count,
        'active_count': active_count,
    })


@login_required
def complete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)

    if request.method == 'POST':
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

    # Определяем откуда пришел запрос
    referer = request.META.get('HTTP_REFERER', '')
    if 'task-list' in referer:
        return redirect('task_list')
    return redirect('calendar')


@login_required
@require_POST
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    task.delete()

    # Проверяем, откуда пришел запрос
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    # Если это обычная форма, редиректим
    referer = request.META.get('HTTP_REFERER', '')
    if 'task-list' in referer:
        return redirect('task_list')
    return redirect('calendar')


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