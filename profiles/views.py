from django import forms
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.template import RequestContext
from django.views.decorators.http import require_POST
from profiles.models import (LinkedinProfile, Applicant, EmailTemplate,
                             Event, FdProfile, Interest, Skillset)
from userena.utils import get_profile_model
from userena import views as userena_views
import json
from django.db.models import Q
from django.core.paginator import Paginator
from userena import forms as userena_forms
import logging

logger = logging.getLogger('fd')


@login_required
def attend(request):
    context_instance = RequestContext(request)
    user = context_instance['user']

    extra_data = {}
    if hasattr(user, 'social_auth'):
        sa = context_instance['user'].social_auth.all()
        if sa is not None and len(sa) >= 1:
            extra_data = sa[0].extra_data

    twitter = u''
    info = extra_data.get('twitter-accounts', {})
    if info:
        for info in info.get('twitter-account', []):
            if isinstance(info, dict):
                twitter = info.get('provider-account-name', u'')
            else:
                twitter = unicode(info)
            break

    location = extra_data.get('location', {})
    location = location.get('name', u'')

    positions = extra_data.get('positions', {})
    experience = u''
    pos = positions.get('position', [])
    if isinstance(pos, dict):
        pos = [pos]

    for position in pos:
        if 'start-date' not in position:
            end = u'current'
            experience += u'current, %s, %s\n' % (position['title'],
                                                   position['company']['name'])
        else:
            enddate = position.get('end-date', {})
            endyear = enddate.get('year', u'now')
            end = u'%s' % endyear
            experience += u'%s to %s, %s, %s\n' % (
                position['start-date']['year'],
                end,
                position['title'],
                position['company']['name'])
    education = u''
    e = extra_data.get('educations', {})
    if isinstance(e, dict):
        for edu in extra_data.get('educations', {}).values():
            if isinstance(edu, dict):
                edu = edu.values()
            for v in edu:
                if isinstance(v, dict):
                    v = v.values()[0]
                education += unicode(v) + u', '
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


@login_required
@require_POST
def attend_save(request):
    context_instance = RequestContext(request)
    user = context_instance['user']
    fdprofile = FdProfile.objects.get(user=user)

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
        recommend_json=json.dumps(recommend),
        fdprofile_id=fdprofile.id,
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


def event_detail(request, event_id):
    event = Event.objects.filter(id=event_id)[0]
    return render_to_response('event.html', {'event': event, },
                              RequestContext(request))


@login_required
def email_form(request):
    c = {}
    email_templates = EmailTemplate.objects.filter(
        name=request.GET.get("email_template"))
    if len(email_templates) > 0:
        c.update({"email_template": email_templates[0]})

    return render_to_response('email_form.html', c,
                              context_instance=RequestContext(request))


member_search_fields = [
    'user__first_name__icontains',
    'user__last_name__icontains',
    'user__username__icontains',
    'bio__icontains',
    'past_experience_blurb__icontains',
    'bring_blurb__icontains',
    'building_blurb__icontains',
    ]


def member_dict(profile):
    portrait_url = None
    if isinstance(profile, FdProfile):
        try:
            linkedin = LinkedinProfile.objects.get(fd_profile=profile)
            portrait_url = linkedin.profile_picture
        except LinkedinProfile.DoesNotExist:
            pass

    username = u''
    if hasattr(profile, 'user'):
        name = profile.user.first_name + u' ' + profile.user.last_name
        username = profile.user.username
    else:
        name = profile.name

    member = {
        'portrait_url': portrait_url,
        'name': name,
        'bio': getattr(profile, 'bio', u'') or u'',
        'username': username,
        'user': getattr(profile, 'user', None),
        }
    return member


class IterJoiner(object):
    def __init__(self, *args):
        self.iters = args

    def __iter__(self):
        for x in self.iters:
            for y in x:
                yield y

    def __len__(self):
        total = 0
        for x in self.iters:
            total += len(x)
        return total

    def get_single_item(self, x):
        for xiter in self.iters:
            if x >= len(xiter):
                x -= len(xiter)
            else:
                return xiter[x]

        raise KeyError('no such item')

    def __getitem__(self, slice_):
        if isinstance(slice_, int):
            return self.get_single_item(slice_)

        items = []
        for x in range(slice_.start, slice_.stop, slice_.step or 1):
            items.append(self.get_single_item(x))
        return items


possible = {'filter_applicant_': Applicant,
            'filter_fdprofile_': FdProfile}

member_search_fields = {
    Applicant: [
        'name__icontains',
        ],

    FdProfile: [
        'user__first_name__icontains',
        'user__last_name__icontains',
        'user__username__icontains',
        'bio__icontains',
        'past_experience_blurb__icontains',
        'bring_blurb__icontains',
        'building_blurb__icontains',
        ],
    }


def members(request):
    search = request.POST.get('s', '')
    queries = {}
    for model, fields in member_search_fields.items():
        queries[model] = queries.get(model, Q())
        if search:
            for field in fields:
                queries[model] |= Q(**{field: search})

    filter_counts = {}
    has_filters = False
    for k, v in request.POST.items():
        for group in k.split(','):
            s = group.split('.')
            if s[0] == 'filter':
                for model in member_search_fields:
                    if s[1] == model.__name__:
                        has_filters = True
                        filter_counts[model] = filter_counts.get(model, 0) + 1
                        queries[model] |= Q(**{s[2]: v})
                        print '%s: %s = %s' % (model.__name__,
                                               s[2],
                                               v)

    if has_filters:
        for model, query in queries.items():
            if not filter_counts.get(model, None):
                del queries[model]

    # this was setup to query both FdProfile and Applicant entries
    # but atm Applicants have no "profile" links

    # objects = []
    # for model, query in queries.items():
    #     filter_ = getattr(model, 'objects').filter
    #     objects.append(filter_(query))

    objects = [FdProfile.objects.filter(queries.get(FdProfile))]

    joiner = IterJoiner(*objects)
    paginator = Paginator(joiner, 12)
    try:
        page = paginator.page(int(request.GET.get('p', 1)))
    except:
        page = paginator.page(1)

    profiles = []
    for profile in page.object_list:
        profiles.append(member_dict(profile))

    status_options = [{'value': x[0], 'label': x[1]}
                      for x in FdProfile.STATUS_CHOICES]

    start_dates = [{'value': x[0], 'label': x[1]}
                  for x in FdProfile.START_CHOICES]

    cities = FdProfile.objects.values_list('city').order_by('city').distinct()
    cities = [x[0].title() for x in cities if x[0]]

    c = {
        'profiles': profiles,
        'events': Event.objects.all(),
        'interests': Interest.objects.all(),
        'skillsets': Skillset.objects.all(),
        'cities': cities,
        'status_options': status_options,
        'members_page': page,
        'start_dates': start_dates,
        's': request.POST.get('s', u''),
        'members_matched': len(joiner),
        }
    return render_to_response('members.html', c,
                              context_instance=RequestContext(request))


def smart_redirect(request):
    referer = request.META.get('HTTP_REFERER', '')
    if referer and '?' in referer:
        s = referer.split('?')[-1]
        if '=' in s:
            last = s.split('=')[1]
            return redirect(last)
    return redirect('/')


def get_events(fdprofile):
    events = []
    for app in Applicant.objects.filter(fdprofile=fdprofile):
        events.append(app.event)
    return events


class EventWidget(forms.Widget):

    def render(self, name, value, attrs=None):
        events = get_events(self.fdprofile)
        if len(events) == 0:
            return u'<span class="no-events">No registered events</span>'
        s = u'<ul>'
        for event in events:
            s += u'<li>' + unicode(event.event_date) + u', ' \
                + event.event_location.display + u'</li>\n'
        s += u'</ul>'
        return s


class EditProfileForm(userena_forms.EditProfileForm):
    first_name = forms.CharField(label=u'First name',
                                 max_length=30,
                                 required=False)
    last_name = forms.CharField(label='Last name',
                                max_length=30,
                                required=False)
    past_experience_blurb = forms.CharField(label=u'Previous Experience',
                                            widget=forms.Textarea,
                                            required=False)
    bring_blurb = forms.CharField(label=u'Bring to a Founding Team',
                                  widget=forms.Textarea,
                                  required=False)
    building_blurb = forms.CharField(label=u'Currently Building',
                                     widget=forms.Textarea,
                                     required=False)
    brings = forms.CharField(label=u'Bring to a Founding Team',
                                  widget=forms.Textarea,
                             required=False)
    current_idea = forms.CharField(label=u'Idea you\'re building now',
                                  widget=forms.Textarea,
                                   required=False)
    looking_for = forms.ChoiceField(label=u'Looking for a Partner With',
                                    widget=forms.SelectMultiple,
                                    required=False)
    events_attended = forms.ChoiceField(
        label=u'Events Attended',
        required=False,
        widget=EventWidget(attrs={'readonly': 'readonly'}))

    def __init__(self, *args, **kw):
        super(userena_forms.EditProfileForm, self).__init__(*args, **kw)
        new_order = self.fields.keyOrder[:-2]
        for field in ('last_name', 'first_name'):
            try:
                index = new_order.index(field)
                del new_order[index]
            except ValueError:
                pass
        new_order = [
            'first_name',
            'last_name',
            'city',
            'events_attended',
            'mugshot',
            'skillsets',
            'past_experience_blurb',
            'education',
            'looking_for',
            'interest_areas',
            'availability',
            'brings',
            'idea_status',
            'founder_type',
            'current_idea',
            ]
        self.fields.keyOrder = new_order

        self.fields['mugshot'].label = u'Profile Portrait'
        self.fields['skillsets'].label = u'Primary Skillsets'
        self.fields['interest_areas'].label = u'Areas of Interest'
        self.fields['looking_for'].choices = [(x.id, x.name)
                                              for x in Skillset.objects.all()]
        self.fields['events_attended'].widget.fdprofile = kw['instance']

    class Meta:
        model = get_profile_model()
        exclude = userena_forms.EditProfileForm.Meta.exclude + [
            'event_status',
            'bring_skillsets_json',
            'need_skillsets_json',
            'interests_json',
            'bring_blurb',
            'building_blurb',
            'can_start',
            'privacy',
            'comments',
            'bio',
            ]


def profile_edit(request, *args, **kwargs):
    return userena_views.profile_edit(request,
                                      edit_profile_form=EditProfileForm,
                                      *args, **kwargs)


def profile_detail(request, username, *args, **kwargs):
    user = get_object_or_404(User,
                             username__iexact=username)
    try:
        profile = user.get_profile()
    except Exception:
        profile = FdProfile(user=user)
        profile.save()

    context = {'events': get_events(profile)}

    return userena_views.profile_detail(request, username,
                                        extra_context=context,
                                        *args, **kwargs)
