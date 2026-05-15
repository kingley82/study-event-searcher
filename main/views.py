from django.shortcuts import render, redirect
from .forms import *
from django.contrib.auth import login, logout
# from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.shortcuts import get_object_or_404
from django.utils.timezone import now, localdate, localtime
from zoneinfo import ZoneInfo
from django.db.models import Avg, Q, Exists, OuterRef, F, Value, BooleanField
from django.utils.dateparse import parse_datetime
from urllib.parse import quote, unquote
import math, requests
from itertools import chain
from operator import attrgetter

@never_cache
def index(request):
    age = 18
    if not request.user.is_anonymous:
        today = localdate()
        bday = request.user.birthday
        age = today.year - bday.year - ((today.month, today.day) < (bday.month, bday.day))
    params = request.GET
    search = params.get("search")
    startdate = params.get("startdate")
    enddate = params.get("enddate")
    show_ended = params.get("show_ended")
    near = params.get("near")
    clear_btn = False
    events = Event.objects.all().order_by("date")
    if age < 18:
        events = events.filter(explicit=False)
    if near == "1":
        user = request.user
        if (user.is_anonymous): return redirect("login")
        if (user.lat == None or user.lon == None): return redirect("/profile/edit/address?redirect="+quote(request.get_full_path(), safe=""))
        delta_lat = 15 / 111
        delta_lon = 15 / (111 * math.cos(math.radians(float(user.lat))))
        events = events.filter(latitude__range=(float(user.lat)-delta_lat, float(user.lat)+delta_lat), longitude__range=(float(user.lon)-delta_lon, float(user.lon)+delta_lon))
        clear_btn = True
    if search is not None:
        events = events.filter(Q(name__icontains=search) | Q(desc__icontains=search) | Q(address__icontains=search))
        clear_btn = True
    if startdate is not None:
        events = events.filter(date__gte=parse_datetime(startdate))
        clear_btn = True
    if enddate is not None:
        events = events.filter(enddate__lte=parse_datetime(enddate))
        if show_ended is None:
            events = events.filter(enddate__gte=now())
        clear_btn = True
    else:
        if show_ended is None:
            events = events.filter(enddate__gte=now())
    for e in events:
        e.now = now().astimezone(ZoneInfo(e.timezone))
        e.date = e.date.astimezone(ZoneInfo(e.timezone))
        e.showdate = e.date.strftime("%d.%m.%Y %H:%M")
        e.enddate = e.enddate.astimezone(ZoneInfo(e.timezone))
        e.avg_rating = Comment.objects.filter(event=e, user__usereventregister__event=e).aggregate(avg=Avg("rating"))["avg"] or 0
        if len(e.desc) > 256: e.desc = e.desc[:256] + "..."
    return render(request, 'index.html', {"events": events, "now": now(), "clear_btn": clear_btn})

@login_required(login_url='/login/')
@never_cache
def profile(request, id=None):
    editable = True
    user = request.user
    registered = None
    if id != None and id != user.id:
        print(id)
        editable = False
        user = get_object_or_404(User, id=id)
    else:
        registered = Event.objects.filter(usereventregister__user_id=user.id, enddate__gte=now())
        for event in registered:
            event.avg_rating = Comment.objects.filter(event=event, user__usereventregister__event=event).aggregate(avg=Avg("rating"))["avg"] or 0
    comments = Comment.objects.filter(user=user.id).order_by('time').reverse()
    events_count = Event.objects.filter(org_id=user.id, enddate__lt=now()).count()
    # avg_rating = round(Comment.objects.filter(event__org_id=user.id).aggregate(avg=Avg("rating"))["avg"] or 0.0, 2)
    reg = UserEventRegister.objects.filter(
        user_id=OuterRef("user_id"),
        event_id=OuterRef("event_id")
    )
    # events = Event.objects.filter(org=user.id).annotate(avg_rating=Avg("comments__rating", filter=Exists(reg))).order_by("-enddate")
    events = Event.objects.filter(org=user.id).order_by("-enddate")
    for event in events:
        event.avg_rating = Comment.objects.filter(event=event, user__usereventregister__event=event).aggregate(avg=Avg("rating"))["avg"] or 0
        if len(event.desc) > 256: event.desc = event.desc[:256] + "..."
    avg_rating = round(Comment.objects.filter(event__org_id=user.id).filter(Exists(reg)).aggregate(avg=Avg("rating"))["avg"] or 0.0,2)
    media = {}
    for i in ["tg", "max", "vk", "whatsapp", "insta"]:
        if getattr(user, i+"_account") not in [None, ""]: media[i] = getattr(user, i+"_account")
    return render(request, "profile.html", context={"user": user, "editable": editable, 'events': list(events), 'comments': list(comments), "media": media, "now": now(), "events_count": events_count, "avg_rating": avg_rating, "registered": registered})

@login_required(login_url='/login/')
@never_cache
def profile_edit(request):
    user = request.user
    if request.method == "POST":
        form = ProfileEditForm(
            request.POST,
            request.FILES,
            instance=user
        )
        if form.is_valid():
            form.save()
            return redirect("profile")
    else:
        form = ProfileEditForm(instance=user)
    return render(request, "edit_profile.html", {"form": form})

@login_required(login_url='/login/')
@never_cache
def profile_edit_address(request):
    user = request.user
    params = request.GET
    redirect_ = unquote(params.get("redirect")) if params.get("redirect") else None
    return render(request, 'edit_address.html', {"lat": float(user.lat) if user.lat is not None else None, "lon": float(user.lon) if user.lon is not None else None, "redirect": redirect_})

@login_required(login_url='/login/')
@never_cache
def profile_edit_address_set(request):
    lat = request.GET.get("lat")
    lon = request.GET.get("lon")
    if lat is None or lon is None: return redirect("profile_edit_address")
    try:
        lat = float(lat)
        lon = float(lon)
    except ValueError: return redirect("profile_edit_address")
    user = request.user
    user.lat = lat
    user.lon = lon
    user.save()
    redirect_ = request.GET.get("redirect")
    redirect_ = unquote(redirect_) if redirect_ else None
    if not redirect_ or redirect_ == "None":
        return redirect("profile_edit")
    return redirect(redirect_)

@login_required(login_url='/login/')
@never_cache
def profile_edit_address_delete(request):
    request.user.lat = None
    request.user.lon = None
    request.user.save()
    return redirect('profile_edit')

@login_required(login_url='/login/')
@never_cache
def event_create(request):
    if request.method == "POST":
        form = EventCreateForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.org = request.user
            timezone = requests.get(f"https://timeapi.io/api/v1/timezone/coordinate?latitude={event.latitude}&longitude={event.longitude}").json()['timezone']
            event.timezone = timezone
            tz = ZoneInfo(timezone)
            event.date = event.date.replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))
            event.enddate = event.enddate.replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))
            event.save()
            return redirect(f"/event/{event.id}")
    else:
        form = EventCreateForm()
    return render(request, "event_create.html", {"form": form})

@login_required(login_url='/login/')
@never_cache
def view_event(request, id):
    event = get_object_or_404(Event, id=id)
    today = localdate(timezone=ZoneInfo(event.timezone))
    bday = request.user.birthday
    age = today.year - bday.year - ((today.month, today.day) < (bday.month, bday.day))
    org = User.objects.get(id=event.org.id)
    rec = UserEventRegister.objects.filter(user=request.user.id).filter(event=event).exists()
    prev_comment = Comment.objects.filter(event=event).filter(user=request.user)
    registered_users = UserEventRegister.objects.filter(event=event).values("user_id")
    reg = UserEventRegister.objects.filter(
        user_id=OuterRef("user_id"),
        event_id=OuterRef("event_id")
    )
    org_avg_rating = round(Comment.objects.filter(event__org_id=org.id).filter(Exists(reg)).aggregate(avg=Avg("rating"))["avg"] or 0.0,2)
    comments = Comment.objects.filter(event=event, user_id__in=registered_users).order_by("time").reverse()
    org_comments = OrgComment.objects.filter(event=event).annotate(is_org=Value(True, output_field=BooleanField())).order_by("time").reverse()
    comments = sorted(chain(list(comments), list(org_comments)), key=attrgetter('time'), reverse=True)
    for c in comments:
        c.time = c.time.astimezone(ZoneInfo(event.timezone)).strftime("%d.%m.%Y %H:%M")
    avg_rating = round(Comment.objects.filter(event=event, user_id__in=registered_users).aggregate(avg=Avg("rating"))['avg'] or 0.0, 2)
    media = {}
    for i in ["tg", "max", "vk", "whatsapp", "insta"]:
        if getattr(org, i+"_account") not in [None, ""]: media[i] = getattr(org, i+"_account")
    if request.method == "POST":
        if prev_comment.exists(): return redirect(f"/event/{id}")
        if not rec: return redirect(f"/event/{id}")
        form = CommentForm(request.POST, request.FILES)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.event = event
            comment.user = request.user
            comment.save()
            return redirect(f"/event/{id}")
    else:
        form = CommentForm()
    return render(request, 'event.html', {"event": event, "org": org, "org_avg_rating": org_avg_rating, "now": now().astimezone(ZoneInfo(event.timezone)), 'media': media, "rec": rec, "age": age, "form": form, "prev_comment": prev_comment.first(), "comments": comments, "avg_rating": avg_rating, "org_comment_form": OrgCommentForm(), "timezoned_date": event.date.astimezone(ZoneInfo(event.timezone)).strftime("%d.%m.%Y %H:%M"), "timezoned_enddate": event.enddate.astimezone(ZoneInfo(event.timezone)).strftime("%d.%m.%Y %H:%M"),
                                          "comments_count": len(comments), "events_count" : Event.objects.filter(org_id=event.org.id, enddate__lt=now()).count()})

@login_required(login_url='/login/')
@never_cache
def org_comment(request, id):
    event = Event.objects.get(id=id)
    if request.user.id == event.org.id and request.method == "POST":
        form = OrgCommentForm(request.POST, request.FILES)
        summary = form.save(commit=False)
        summary.event = event
        summary.user = request.user
        summary.save()
    return redirect(f"/event/{id}")

@login_required(login_url='/login/')
@never_cache
def cancel_event(request, id):
    user = request.user
    event = get_object_or_404(Event, id=id)
    if user.id == event.org.id:
        event.delete()
        Comment.objects.filter(event=event.id).delete()
        OrgComment.objects.filter(event=event.id).delete()
        UserEventRegister.objects.filter(event=event.id).delete()
    return redirect("/profile")

@login_required(login_url='/login/')
@never_cache
def event_register(request, id):
    user = request.user
    event = get_object_or_404(Event, id=id)
    if user.id != event.org.id and now() < event.enddate and not UserEventRegister.objects.filter(user=user.id).filter(event=event).exists():
        rec = UserEventRegister()
        rec.event = event
        rec.user = user
        rec.save()
    return redirect(f"/event/{id}")

@login_required(login_url='/login/')
@never_cache
def event_cancel_register(request, id):
    user = request.user
    event = get_object_or_404(Event, id=id)
    rec = UserEventRegister.objects.filter(user=user.id)
    rec.delete()
    return redirect(f"/event/{id}")

@never_cache
@login_required(login_url='/login/')
def delete_comment(request, id):
    user = request.user
    comment = get_object_or_404(Comment, id=id)
    event_id = comment.event.id
    if comment.user.id == user.id:
        comment.delete()
    return redirect(f"/event/{event_id}")

@never_cache
@login_required(login_url='/login/')
def delete_org_comment(request, id):
    user = request.user
    comment = get_object_or_404(OrgComment, id=id)
    event_id = comment.event.id
    if comment.user.id == user.id:
        comment.delete()
    return redirect(f"/event/{event_id}")

@never_cache
# @login_required(login_url='/login/')
def search(request):
    return render(request, "search.html")

@never_cache
def search_user(request, s):
    found = set()
    if s.isnumeric():
        searchid = User.objects.filter(id=int(s))
        print(searchid)
        if searchid.exists():
            found.add(searchid.first())
    a = User.objects.filter(name__icontains=s).order_by("name")
    for b in a: found.add(b)
    return render(request, 'search_user.html', {"users": found})

@never_cache
def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})

@never_cache
def login_(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data["user"]
            login(request, user)
            return redirect("profile")
    else:
        form = LoginForm()

    return render(request, "login.html", {"form": form})

@never_cache
def logout_(request):
    logout(request)
    return redirect("login")