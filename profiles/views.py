from django.shortcuts import render_to_response, redirect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.views.decorators.http import require_POST
from profiles.models import Applicant, EmailTemplate, Event, FdProfile
import json
from collections import OrderedDict


def attend(request):
    context_instance = RequestContext(request)
    user = context_instance['user']

    if hasattr(user, 'social_auth'):
        extra_data = context_instance['user'].social_auth.all()[0].extra_data
    else:
        extra_data = {}

    twitter = u''
    info = extra_data.get('twitter-accounts', {})
    if info:
        for info in info.get('twitter-account', []):
            twitter = info['provider-account-name']
            break

    location = extra_data.get('location', {})
    location = location['name']

    positions = extra_data.get('positions', {})
    experience = u''
    for position in positions.get('position', []):
        end = position.get('end-date', {})
        endyear = end.get('year', u'now')
        experience += u'%s to %s, %s, %s\n' % (position['start-date']['year'],
                                               endyear,
                                               position['title'],
                                               position['company']['name'])
    education = u''
    for edu in extra_data.get('educations', {}).values():
        for v in edu.values():
            if isinstance(v, dict):
                v = v.values()[0]
            education += v + u', '
        education += u'\n'

    c = {
        "three": [1, 2, 3],
        "idea_status_choices": dict(FdProfile.IDEA_STATUS_CHOICES),
        "start_choices": dict(FdProfile.START_CHOICES),
        "linkedin_data": extra_data,
        "linkedin_url": extra_data.get('public-profile-url', u''),
        'location': location,
        'twitter': twitter,
        'experience': experience,
        'education': education,
    }
    return render_to_response('attend.html', c,
                              context_instance=context_instance)


@require_POST
def attend_save(request):
    e = Event.objects.filter(pk=request.POST.get("event_id", -1))
    if len(e) < 1:
        raise Exception("Invalid Event")

    interests = (request.POST.getlist("interests"))
    if request.POST.get("interests_more"):
        for i in request.POST.get("interests_more").split(","):
            interests.append(i)

    recommend = []
    recommend_names = request.POST.getlist("recommend_name")
    recommend_emails = request.POST.getlist("recommend_email")
    for i in [0, 1, 2]:
        recommend.append({"name": recommend_names[i],
                          "email": recommend_emails[i]})

    applicant = Applicant(
        name=request.POST.get("name"),
        email=request.POST.get("email"),
        event=e[0],
        bring_skillsets_json=json.dumps(
            request.POST.getlist("bring_skillsets")),
        past_experience_blurb=request.POST.get("past_experience_blurb"),
        linkedin_url=request.POST.get("linkedin_url"),
        bring_blurb=request.POST.get("bring_blurb"),
        building_blurb=request.POST.get("building_blurb"),
        interests_json=json.dumps(interests),
        can_start=request.POST.get("can_start"),
        idea_status=request.POST.get("idea_status"),
        need_skillsets_json=json.dumps(
            request.POST.getlist("need_skillsets")),
        recommend_json=json.dumps(recommend)
    )
    applicant.save()

    return redirect("/attend/thanks")


def attend_thanks(request):
    c = {}
    return render_to_response('attend_thanks.html', c,
                              context_instance=RequestContext(request))


def events(request):
    c = {}
    return render_to_response('events.html', c,
                              context_instance=RequestContext(request))


@login_required
def email_form(request):
    c = {}
    email_templates = EmailTemplate.objects.filter(
        name=request.GET.get("email_template"))
    if len(email_templates) > 0:
        c.update({"email_template": email_templates[0]})

    return render_to_response('email_form.html', c,
                              context_instance=RequestContext(request))


member_search_fields = []


def member_dict(profile):
    member = {
        'portrait_url': '',
        'name': profile.user.first_name + u' ' + profile.user.last_name,
        }
    return member


from django.db.models import Q
from django.core.paginator import Paginator


def members(request):
    search = request.POST.get('s', '')

    if search:
        for fields in member_search_fields:
            q = Q()
            for field in fields:
                kwargs = {field: search}
                q = q | Q(**kwargs)
    else:
        q = Q()

    paginator = Paginator(FdProfile.objects.filter(q), 20)
    page = paginator.page(int(request.GET.get('p', 1)))

    profiles = OrderedDict()
    for profile in page.object_list:
        profiles[profile.id] = member_dict(profile)

    c = {'profiles': profiles}
    return render_to_response('members.html', c,
                              context_instance=RequestContext(request))
