### END of traditional models definition. Should this be moved to __init__.py?
# Listen for new accounts/updates via social auth and update the FdProfile
from social_auth.signals import pre_update
from social_auth.backends.contrib.linkedin import LinkedinBackend
from .models import LinkedinProfile, FdProfile


# last field mappings as provided by Jessica
# - Name - use LinkedIn
# - City - Use LinkedIN (new)
# * Note: Event - this should be different than city in that it will
#         be the event date
# Previous Experience: this is where we want to pull in both previous
# and current work experience and education. If there is text filled
# in on LInkedIn about each position, we should pull that in as well.
# - websites - - use linkedin
# - Twitter - use linkedin
# - Connections In Common
# - this is a nice to have, but if it's easy or part of the API we
#   can show the # of connections the viewer of the profile has in
#   common with the profile owner


def linkedin_extra_values(sender, user, response, details, **kwargs):
    """
    """

    linkedin_url = response.get('public-profile-url', u'')

    try:
        fd_profile = FdProfile.objects.get(linkedin_url=linkedin_url)
        return True
    except FdProfile.DoesNotExist:
        pass

    fd_profile = FdProfile(linkedin_url=linkedin_url,
                           user=user)
    fd_profile.save()
    ll_profile = LinkedinProfile(
        fd_profile_id=fd_profile.id,
        profile_raw=response.get('summary', u''),
        profile_picture=response.get('picture-url', u''),
        profile_location=response.get('location', u''),
        profile_industry=response.get('industry', u''),
        #connections_raw=response['connections'],
        )
    ll_profile.save()
    return True

pre_update.connect(linkedin_extra_values, sender=LinkedinBackend)
