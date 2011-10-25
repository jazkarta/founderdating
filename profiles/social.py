### END of traditional models definition. Should this be moved to __init__.py?
# Listen for new accounts/updates via social auth and update the FdProfile
from social_auth.signals import pre_update
from social_auth.backends.contrib.linkedin import LinkedinBackend
from .models import LinkedinProfile, FdProfile


def linkedin_extra_values(sender, user, response, details, **kwargs):
    """
    """

    linkedin_url = response.get('public-profile-url', u'')

    try:
        fd_profile = FdProfile.objects.get(linkedin_url=linkedin_url)
        return True
    except FdProfile.DoesNotExist:
        pass

    fd_profile = FdProfile(linkedin_url=linkedin_url)
    ll_profile = LinkedinProfile(
        fd_profile=fd_profile,
        profile_raw=response.get('summary', u''),
        profile_picture=response.get('picture-url', u''),
        profile_location=response.get('location', u''),
        profile_industry=response.get('industry', u''),
        #connections_raw=response['connections'],
        )
    fd_profile.save()
    ll_profile.save()
    return True

pre_update.connect(linkedin_extra_values, sender=LinkedinBackend)
