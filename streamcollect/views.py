from dateutil.parser import *
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q
from .models import User, Relo, CeleryTask, Keyword
from .forms import AddUserForm
from twdata import userdata
from twdata.tasks import twitter_stream_task

from celery.task.control import revoke

from streamcollect.tasks import add_user_task, update_user_relos_task, trim_spam_accounts
from .methods import kill_celery_task
from .config import REQUIRED_IN_DEGREE, REQUIRED_OUT_DEGREE

def monitor_user(request):
    return render(request, 'streamcollect/monitor_user.html', {})

def list_users(request):
    users = User.objects.filter(user_class__gte=2)
    return render(request, 'streamcollect/list_users.html', {'users': users})

def view_network(request):
    return render(request, 'streamcollect/view_network.html')

def user_details(request, user_id):
    user = get_object_or_404(User, user_id=user_id)
    return render(request, 'streamcollect/user_details.html', {'user': user})

def stream_status(request):
    keywords = Keyword.objects.all().values_list('keyword', flat=True).order_by('created_at')
    if not CeleryTask.objects.filter(task_name='stream_kw'):
        stream_status = False
    else:
        stream_status = True
    return render(request, 'streamcollect/stream_status.html', {'stream_status': stream_status, 'keywords': keywords})

def testbed(request):
    return render(request, 'streamcollect/testbed.html')

def submit(request):
    if "screen_name" in request.POST:
        #TODO: Add validation function here
        info = request.POST['info']
        if len(info) > 0:
            add_user_task.delay(screen_name = info)
        return redirect('monitor_user')
    elif "add_keyword" in request.POST:
        info = request.POST['info']
        if len(info) > 0:
            k = Keyword()
            k.keyword = info
            k.save()
        return redirect('monitor_user')
    elif "start_stream" in request.POST:
        task = twitter_stream_task.delay()
        task_object = CeleryTask(celery_task_id = task.task_id, task_name='stream_kw')
        task_object.save()
        return redirect('stream_status')
    elif "stop_stream" in request.POST:
        #TODO: Include stream_gps here
        kill_celery_task('stream_kw')
        return redirect('stream_status')
    elif "trim_spam_accounts" in request.POST:
        task = trim_spam_accounts.delay()
        return redirect('testbed')
    elif "update_user_relos" in request.POST:
        task = update_user_relos_periodic.delay()
        return redirect('testbed')
    elif "delete_keywords" in request.POST:
        Keyword.objects.all().delete()
        return redirect('testbed')
    elif "terminate_tasks" in request.POST:
        for t in CeleryTask.objects.all():
            revoke(t.celery_task_id, terminate=True)
            t.delete()
        return redirect('testbed')
    else:
        print("Unlabelled button pressed")
        return redirect('monitor_user')

#API returns users above a 'relevant in degree' threshold and the links between them
def network_data_API(request):
    print("Collecting network_data...")

    #Users with an in/out degree of X or greater, exclude designated spam.
    #TODO: Add ego users with smaller degrees?
    relevant_users = User.objects.filter(user_class__gte=0).filter(Q(in_degree__gte=REQUIRED_IN_DEGREE) | Q(out_degree__gte=REQUIRED_OUT_DEGREE))

    resultsuser = [ob.as_json() for ob in relevant_users]

    #Get relationships which connect two 'relevant users'. This is slow. Could pre-generate?
    relevant_relos = Relo.objects.filter(targetuser__in=relevant_users, sourceuser__in=relevant_users, end_observed_at=None)
    resultsrelo = [ob.as_json() for ob in relevant_relos]

    data = {"nodes" : resultsuser, "links" : resultsrelo}
    jsondata = json.dumps(data)

    #TODO: HttpReponse vs Jsonresponse? Latter doesn't work with current d3
    return HttpResponse(jsondata)
