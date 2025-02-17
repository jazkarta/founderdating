from django.contrib import admin
from django.template import Template, Context, Library
from django.core.mail import EmailMessage
from profiles.models import Applicant, EmailTemplate, Event, EventLocation, Interest, Skillset, LinkedinProfile
import json
from profiles.csv_export import CsvExport
from django.contrib.admin.views.main import ChangeList

def csv_export(admn, request, queryset):
    return CsvExport().csv_export(queryset)
csv_export.short_description = "Export selected records as csv"
admin.site.add_action(csv_export, 'csv_export')

def csv_export_all(admn, request, queryset):
    # We want the original criteria from the query set, but with a much higher limit
    cl = ChangeList(request, admn.model, admn.list_display, admn.list_display_links, admn.list_filter, admn.date_hierarchy, admn.search_fields, admn.list_select_related, 100000, admn.list_editable, admn)
    return CsvExport().csv_export(cl.get_query_set())
csv_export_all.short_description = "Export ALL records as csv (select at least one record to use)"
admin.site.add_action(csv_export_all, 'csv_export_all')

class ApplicantAdmin(admin.ModelAdmin):
    def linkedin_link(self, obj):
        return '<a href="%s" target="_new"><nobr><img src="/static/img/linkedin_icon.png">Profile</nobr></a>' % (obj.linkedin_url)
    linkedin_link.allow_tags = True
    linkedin_link.short_description = 'LinkedIn'

    class Media:
        js = (
            "js/fd_applicant_admin.js", # first because it puts jquery back into main name space
            "js/jquery-ui-1.8.13.min.js"
        )
        css = {
            "all": ("css/jquery-ui-1.8.13.custom.css", "css/admin.css",)
        }

    def references(self, obj):
        out = ''
        if len(obj.recommend_json) > 1:
            jrec = json.loads(obj.recommend_json)
            for rec in jrec:
                if rec['name'] != "":
                    if len(rec['name']) > 25:
                        name = rec['name'][:25] + "..."
                    else:
                        name = rec['name']
                    out += '<a href="mailto:' + rec['email'] + '">' + name + '</a><br />'
        return out
    references.allow_tags = True

    def bulk_email(self, request, queryset):
        emails_sent = 0
        try: 
            subject_template = Template("{% load fd_tags %} " + request.POST.get("subject"))
            message_template = Template("{% load fd_tags %} " + request.POST.get("message"))
        except Exception as e:
            self.message_user(request, "Error parsing template: " + str(e))
            return 

        email = EmailMessage(
            bcc = request.POST.get("bcc"),
            from_email = request.POST.get("from"))

        for applicant in queryset:
            c = Context({"applicant": applicant, "event": applicant.event})
            try:
                email.subject = subject_template.render(c)
                email.body = message_template.render(c)
            except Exception as e:
                self.message_user(request, "Error rendering message: " % str(e))
                break

            email.to = [request.POST.get("override_to", applicant.email)]
            email.send()
            emails_sent += 1
        
        self.message_user(request, "%s e-mails sent" % emails_sent)

    def email_references(self, request, queryset):
        queryset.update(event_status="checking references")
        emails_sent = 0
        try: 
            subject_template = Template("{% load fd_tags %} " + request.POST.get("subject"))
            message_template = Template("{% load fd_tags %} " + request.POST.get("message"))
        except Exception as e:
            self.message_user(request, "Error parsing template: " + str(e))
            return 

        email = EmailMessage(
            bcc = request.POST.get("bcc"),
            from_email = request.POST.get("from"))

        for applicant in queryset:
            references = json.loads(applicant.recommend_json)

            for reference in references:
                c = Context({"applicant": applicant, "event": applicant.event, "reference": reference })
                try:
                    email.subject = subject_template.render(c)
                    email.body = message_template.render(c)
                except Exception as e:
                    self.message_user(request, "Error rendering message: " % str(e))
                    break

                email.to = [request.POST.get("override_to", applicant.email)]
                email.send()
                emails_sent += 1
        
        self.message_user(request, "%s reference e-mails sent" % emails_sent)

    email_references.short_description = "Email the references for the selected applicants"

    def email_declination(self, request, queryset):
        queryset.update(event_status="denied")
        self.bulk_email(request, queryset)
    email_declination.short_description = "Email a declination to selected applicants"

    def invite_to_event(self, request, queryset):
        self.bulk_email(request, queryset)
    invite_to_event.short_description = "Invite the selected candidates to event"
        
    def email_applicant(self, request, queryset):
        self.bulk_email(request, queryset)
    email_applicant.short_description = "Email selected applicants"


    list_display = ('name', 'event_status', 'idea_status', 'founder_type', 'event_group', 'linkedin_link', 'references', 'comments')
    list_filter = ['event', 'event_status', 'founder_type', 'event_group', 'can_start', 'idea_status']
    list_editable = ('founder_type', 'event_group', 'event_status', 'idea_status', 'comments')
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    save_on_top = True
    list_select_related = True
    search_fields = ['name', 'email']
    actions = [email_references, email_declination, invite_to_event, email_applicant]
    radio_fields  = {"founder_type": admin.HORIZONTAL}

    fieldsets = (
        ("Basic", {
            'fields': ('name', 'email', 'linkedin_url')
        }),
        ('Event Categorization', {
            'fields': ('event', 'event_status', 'founder_type', 'event_group')
        }),
        ('Bio', {
            'fields': ('can_start', 'idea_status', 'bring_skillsets_json', 'need_skillsets_json', 'recommend_json', 'interests_json', 'past_experience_blurb', 'bring_blurb', 'building_blurb')
        })
    )
    
admin.site.register(Applicant, ApplicantAdmin)

class EventAdmin(admin.ModelAdmin):
    list_display = ('event_location', 'event_date')
    list_filter = ['event_location']
    ordering = ["-event_date"]
    date_hierarchy = "event_date"
admin.site.register(Event, EventAdmin)

class EventLocationAdmin(admin.ModelAdmin):
    list_display = ('display', 'city', 'state', 'country')
    ordering = ["display"]
admin.site.register(EventLocation, EventLocationAdmin)

class SkillsetAdmin(admin.ModelAdmin):
    list_display = ('name', 'ord')
    ordering = ["ord"]
admin.site.register(Skillset, SkillsetAdmin)

class InterestAdmin(admin.ModelAdmin):
    list_display = ('name', 'ord')
    ordering = ["ord"]
admin.site.register(Interest, InterestAdmin)

class EmailTemplateAdmin(admin.ModelAdmin):
    search_fields = ['name', 'subject', 'message']
admin.site.register(EmailTemplate, EmailTemplateAdmin)


class LinkedinProfileAdmin(admin.ModelAdmin):
    search_fields = []
admin.site.register(LinkedinProfile, LinkedinProfileAdmin)
