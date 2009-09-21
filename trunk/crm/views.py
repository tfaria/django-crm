# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# $Id: views.py 425 2009-07-14 03:43:01Z tobias $
# ----------------------------------------------------------------------------
#
#    Copyright (C) 2008-2009 Caktus Consulting Group, LLC
#
#    This file is part of django-crm and was originally extracted from minibooks.
#
#    django-crm is published under a BSD-style license.
#    
#    You should have received a copy of the BSD License along with django-crm.  
#    If not, see <http://www.opensource.org/licenses/bsd-license.php>.
#

import datetime
import difflib

from django.template import RequestContext, Context, loader
from django.shortcuts import get_object_or_404, render_to_response
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponseRedirect
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import simplejson as json
from django.http import HttpResponse, Http404
from django.db.models import Q
from django.db import transaction
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate, login
from django.core.mail import send_mass_mail, send_mail

from caktus.django.forms import AutoCompleterForm
from caktus.django.decorators import render_with
from caktus.iter import all_true

from contactinfo.helpers import create_edit_location
from contactinfo import models as contactinfo

from crm import models as crm
from crm import forms as crm_forms


@login_required
@render_with('crm/dashboard.html')
def dashboard(request):
    if request.contact:
        # soonest first
        upcoming_interactions = request.contact.interactions.select_related(
            'cdr',
            'contacts',
            'project',
            'project__business',
        ).filter(completed=False).order_by('date')

        # most recent first
        recent_interactions = request.contact.interactions.select_related(
            'cdr',
            'contacts',
            'project',
            'project__business',
        ).filter(completed=True)[:6]

        projects = request.contact.contact_projects.order_by(
            'name',
        ).select_related('business')
    else:
        upcoming_interactions = []
        recent_interactions = []
        projects = []
    
    context = {
        'recent_interactions': recent_interactions,
        'upcoming_interactions': upcoming_interactions,
        'projects': projects,
    }
    
    try:
        from ledger.models import Exchange
        # there are no permissions on this view, so all DB access
        # must filter by request.user
        context['recent_exchanges'] = Exchange.objects.filter(
            business__type='business',
            business__contacts=request.contact,
        ).select_related('type', 'business')[:10]
    except ImportError:
        pass
    
    return context

### not a view
def compare_by(fieldname):
    def compare_two_dicts(a, b):
        return cmp(a[fieldname], b[fieldname])
    return compare_two_dicts


@login_required
def quick_search(request):
    results = []
    if request.POST:
        if request.user.has_perm('crm.view_business'):
            for business in crm.Contact.objects.filter(
                type='business',
                name__icontains=request.REQUEST['search'],
            ):
                results.append({
                    'label': business.name,
                    'href': reverse('view_business', kwargs={
                        'business_id': business.id,
                    }),
                    'element_class': 'business',
                })
        if request.user.has_perm('crm.view_project'):
            for project in crm.Project.objects.filter(
                name__icontains=request.REQUEST['search'],
            ).select_related():
                results.append({
                    'label': project.name,
                    'href': reverse('view_project', kwargs={
                        'business_id': project.business.id,
                        'project_id': project.id,
                    }),
                    'element_class': 'project',
                })
        if request.user.has_perm('crm.view_profile'):
            for profile in crm.Contact.objects.filter(type='individual').filter(
                Q(first_name__icontains=request.REQUEST['search']) | 
                Q(last_name__icontains=request.REQUEST['search']) |
                Q(email__icontains=request.REQUEST['search'])
            ).select_related():
                results.append({
                    'label': profile.get_full_name(),
                    'href': reverse('view_person', kwargs={'person_id': profile.id}),
                    'element_class': 'contact',
                })
                results.sort(compare_by('label'))
    return HttpResponse(json.dumps(results[:10]), mimetype="text/json")


@permission_required('crm.view_profile')
@render_with('crm/person/list.html')
def list_people(request):
    form = crm_forms.SearchForm(request.GET)
    if form.is_valid() and 'search' in request.GET:
        search = form.cleaned_data['search']
        people = crm.Contact.objects.filter(type='individual').filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
        if people.count() == 1:
            return HttpResponseRedirect(
                reverse(
                    'view_person', 
                    kwargs={'person_id':people[0].id}
                )
            )
    else:
        people = crm.Contact.objects.filter(type='individual')
    
    context = {
        'form': form,
        # it'd be nice if we could grab 'phones' too, but that isn't supported:
        # http://code.djangoproject.com/ticket/6432
        'people': people.select_related('user').order_by('sort_name'),
        'phone_types': contactinfo.Phone.PHONE_TYPES,
    }
    return context


@login_required
@render_with('crm/person/view.html')
def view_person(request, person_id):
    try:
        person = crm.Contact.objects.filter(
            type='individual'
        ).select_related().get(pk=person_id)
    except crm.Contact.DoesNotExist:
        raise Http404
    
    interactions = person.interactions.order_by('-date').select_related(
        'contacts',
        'project',
        'project__business',
    )[0:10]
    
    context = {
        'contact': person,
        'interactions': interactions,
        'can_edit': person.is_editable_by(request.user),
    }
    return context


@render_with('crm/contact/email.html')
def email_contact(request, contact_slug):
    try:
        contact = crm.Contact.objects.select_related().get(slug=contact_slug)
    except crm.Contact.DoesNotExist:
        raise Http404
    form = crm_forms.EmailContactForm(request, recipients=[contact.email])
    if request.POST and form.is_valid():
        form.save()
        request.notifications.add('Message sent successfully to %s.' % contact)
        return HttpResponseRedirect(reverse('view_person', args=[contact.id]))
    return {
        'form': form,
        'contact': contact,
    }


@login_required
@transaction.commit_on_success
@render_with('crm/person/create_edit.html')
def create_edit_person(request, person_id=None):
    if person_id:
        profile = get_object_or_404(crm.Contact, pk=person_id)
        try:
            location = profile.locations.get()
        except contactinfo.Location.DoesNotExist:
            location = None
    else:
        profile = None
        location = None
    new_location = not location
    
    if profile and not profile.is_editable_by(request.user):
        return HttpResponseRedirect(reverse('auth_login'))
    
    if request.POST:
        pre_save = ''
        if profile:
            pre_save = profile.as_text_block()
        profile_form = crm_forms.ProfileForm(
            request.POST,
            instance=profile,
            request=request,
        )
        location, location_saved, location_context = create_edit_location(
            request, 
            location,
            profile_form.is_valid(),
        )
        
        if location_saved:
            # no e-mail will be sent if dict is empty or None
            email = {
#                'template': 'path/to/email/template.txt',
#                'subject': 'Welcome!',
#                'extra_context': { 'somekey': 'someval' },
            }
            saved_profile = profile_form.save()
            
            if new_location:
                saved_profile.locations.add(location)
            if saved_profile:
                message = 'Person updated successfully'
            else:
                message = 'New person created successfully'
            request.notifications.add(message)
            post_save = saved_profile.as_text_block()
            
            try:
                group = Group.objects.get(name='Contact Notifications')
            except Group.DoesNotExist:
                group = None
            if group and post_save != pre_save:
                body = "At %s, %s %s changed the profile of %s:\n\n%s" % (
                    datetime.datetime.now(),
                    request.user.first_name,
                    request.user.last_name,
                    saved_profile,
                    ''.join(list(difflib.ndiff(pre_save, post_save))),
                )
                send_mail(
                    'CRM Contact Update: %s' % saved_profile,
                    body,
                    settings.DEFAULT_FROM_EMAIL,
                    [u.email for u in group.user_set.all()],
                )
            
            if 'associate' in request.REQUEST:
                return HttpResponseRedirect(
                    '%s&associate=true&search_selection=user-%d' % (
                            request.REQUEST['associate'],
                            saved_user.id,
                        )
                )
            
            return HttpResponseRedirect(
                reverse(
                    'view_person',
                    kwargs={'person_id': saved_profile.id,},
                )
            )
    else:
        profile_form = crm_forms.ProfileForm(
            instance=profile,
            request=request,
        )
        location, location_saved, location_context = create_edit_location(
            request, 
            location,
            False,
        )
    context = {
        'forms': [profile_form],
        'contact': profile,
    }
    context.update(location_context)
    return context


@transaction.commit_on_success
@render_with('crm/person/register.html')
def register_person(request):
    form = crm_forms.PersonForm(request)
    if request.POST:
        if form.is_valid():
            email = {
                'template': 'crm/person/new_account_email.txt',
                'subject': 'Your account information',
                'extra_context': { 'app_url_base': settings.APP_URL_BASE },
            }
            user = form.save(email)
            return HttpResponseRedirect(reverse('auth_login'))

    context = {
        'form': form,
    }
    return context


# TODO make these use flot (or something else) and re-enable
# TODO remove links to Trac
#@login_required
#def graph(request, type, developer):
#    # XXX remove import *s
#    from trac_tickets.alchemy import *
#    from trac_tickets.graphs import *
#    from trac_tickets.models import TracConnection
#    
#    if type == 'developer_hours_sum':
#        developer_usernames = developers()
#        graph = graph_hours_sum(developer_usernames, 'PNG')
#    if type == 'commit_hours':
#        graph = graph_developer_hour_commits(developer)
#    if type == 'account':
#        account = Account.objects.get(id=developer)
#        graph = graph_account_sum(account, 'PNG')
#    
#    return HttpResponse(graph, mimetype='image/png')
#
#
#@login_required
#@render_with('crm/hours.html')
#def hours(request):
#    context = {
#        'graph_url' : reverse(
#            'graph_commit_hours',
#            kwargs={'developer': request.user.username,},
#        ),
#        'request' : request,
#    }
#    return context


@permission_required('crm.add_interaction')
@permission_required('crm.change_interaction')
@render_with('crm/interaction/create_edit.html')
def create_edit_interaction(request, person_id=None, interaction_id=None):
    if interaction_id:
        interaction = get_object_or_404(crm.Interaction, pk=interaction_id)
    else:
        interaction = None
    
    if person_id:
        person = get_object_or_404(crm.Contact, pk=person_id)
    else:
        person = None
    
    form = crm_forms.InteractionForm(
        request, 
        instance=interaction,
        person=person,
        crm_user=request.contact,
        url=reverse('quick_add_person'),
    )
    
    if request.POST and form.is_valid():
        form.save()
        return HttpResponseRedirect(reverse('list_interactions'))
    
    context = {
        'form': form,
        'person': person,
    }
    return context


@permission_required('crm.delete_interaction')
@render_with('crm/interaction/remove.html')
def remove_interaction(request, interaction_id):
    interaction = get_object_or_404(crm.Interaction, pk=interaction_id)
    
    if request.POST:
        interaction.delete()
        return HttpResponseRedirect(reverse('list_interactions'))
    
    context = {
        'interaction': interaction,
    }
    return context


@permission_required('crm.view_interaction')
@render_with('crm/interaction/list.html')
def list_interactions(request):
    form = crm_forms.SearchForm(request.GET)
    if form.is_valid():
        search = form.cleaned_data['search']
        interactions = crm.Interaction.objects.filter(
            Q(type__icontains=search) |
            Q(project__name__icontains=search) |
            Q(contacts__first_name__icontains=search) |
            Q(contacts__last_name__icontains=search) |
            Q(memo__icontains=search)
        ).distinct()
    #    if interactions.count() == 1:
    #        return HttpResponseRedirect(
    #            reverse(
    #                'view_interaction', 
    #                kwargs={'interaction_id':interactions[0].id}
    #            )
    #        )
    else:
        interactions = request.contact.interactions.all()
        
    interactions = interactions.select_related(
        'cdr',
        'contacts',
        'project',
        'project__business',
    )
    
    context = {
        'form': form,
        'interactions': interactions,
    }
    return context


@permission_required('crm.view_business')
@render_with('crm/business/list.html')
def list_businesses(request):
    form = crm_forms.SearchForm(request.GET)
    if form.is_valid() and 'search' in request.GET:
        search = form.cleaned_data['search']
        businesses = crm.Contact.objects.filter(type='business').filter(
            Q(name__icontains=search) |
            Q(notes__icontains=search)
        )
        if businesses.count() == 1:
            return HttpResponseRedirect(
                reverse(
                    'view_business', 
                    kwargs={'business_id':businesses[0].id}
                )
            )
    else:
        businesses = crm.Contact.objects.filter(type='business')
    
    context = {
        'form': form,
        'businesses': businesses,
    }
    return context


@permission_required('crm.view_business')
@render_with('crm/business/view.html')
def view_business(request, business):
    add_contact_form = AutoCompleterForm(
        url=reverse('quick_add_person'),
        options={
            'delay': 100,
            'markQuery': False,
            'autoSubmit': True,
            'forceSelect': True,
        },
    )
    context = {
        'business': business,
        'add_contact_form': add_contact_form,
    }
    
    try:
        from ledger.models import Exchange
        exchanges = Exchange.objects.filter(business=business)
        if business.business_projects.count() > 0:
            exchanges = exchanges.filter(
                Q(transactions__project__isnull=True) |
                ~Q(transactions__project__in=business.business_projects.all())
            )
        exchanges = exchanges.distinct().select_related().order_by(
            'type',
            '-date',
            '-id',
        )
        show_delivered_column = \
            exchanges.filter(type__deliverable=True).count() > 0
        context['exchanges'] = exchanges
        context['show_delivered_column'] = show_delivered_column
    except ImportError:
        pass
    
    return context


@permission_required('crm.add_business')
@permission_required('crm.change_business')
@render_with('crm/business/create_edit.html')
def create_edit_business(request, business=None):
    location = None
    if business:
        try:
            location = business.locations.get()
        except contactinfo.Location.DoesNotExist:
            pass
    new_location = not location
    if request.POST:
        business_form = crm_forms.BusinessForm(
            request.POST,
            instance=business,
        )
        location, location_saved, location_context = create_edit_location(
            request, 
            location,
            business_form.is_valid(),
        )
        if location_saved:
            new_business = not business
            business = business_form.save()
            if new_location:
                business.locations.add(location)
            if new_business:
                return HttpResponseRedirect(
                    reverse(
                        'view_business',
                        kwargs={'business_id': business.id,},
                    ),
                )
            else:
                return HttpResponseRedirect(reverse('list_businesses'))
    else:
        business_form = crm_forms.BusinessForm(instance=business)
        location, location_saved, location_context = create_edit_location(
            request, 
            location,
            False,
        )
    
    context = {
        'business': business,
        'business_form': business_form,
    }
    context.update(location_context)
    return context


@permission_required('crm.change_business')
@transaction.commit_on_success
@render_with('crm/business/relationship.html')
def edit_business_relationship(request, business, user_id):
    contact = get_object_or_404(
        crm.Contact,
        pk=user_id,
        contacts=business,
    )
    rel = get_object_or_404(
        crm.ContactRelationship,
        from_contact=business,
        to_contact=contact,
    )
    relationship_form = crm_forms.ContactRelationshipForm(
        request,
        instance=rel,
    )
    if request.POST and relationship_form.is_valid():
        rel = relationship_form.save()
        return HttpResponseRedirect(request.REQUEST['next'])
    
    context = {
        'user': contact,
        'business': business,
        'relationship_form': relationship_form,
    }
    return context


@permission_required('crm.view_project')
@render_with('crm/business/project/list.html')
def list_projects(request):
    form = crm_forms.SearchForm(request.GET)
    if form.is_valid() and 'search' in request.GET:
        search = form.cleaned_data['search']
        projects = crm.Project.objects.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
        if projects.count() == 1:
            url_kwargs = {
                'business_id': projects[0].business.id,
                'project_id': projects[0].id,
            }
            return HttpResponseRedirect(
                reverse('view_project', kwargs=url_kwargs)
            )
    else:
        projects = crm.Project.objects.all()
    
    context = {
        'form': form,
        'projects': projects.select_related('business'),
    }
    return context


@permission_required('crm.view_project')
@transaction.commit_on_success
@render_with('crm/business/project/view.html')
def view_project(request, business, project):
    add_contact_form = AutoCompleterForm(
        url=reverse('quick_add_person'),
        options={
            'delay': 100,
            'markQuery': False,
            'autoSubmit': True,
            'forceSelect': True,
        },
    )
    
    context = {
        'project': project,
        'add_contact_form': add_contact_form,
    }
    try:
        from ledger.models import Exchange
        context['exchanges'] = Exchange.objects.filter(
            business=business,
            transactions__project=project,
        ).distinct().select_related().order_by('type', '-date', '-id',)
        context['show_delivered_column'] = \
            context['exchanges'].filter(type__deliverable=True).count() > 0
    except ImportError:
        pass
    
    return context


@permission_required('crm.change_business')
@permission_required('crm.change_project')
def quick_add_person(request):
    results = []
    if request.POST:
        for contact in crm.Contact.objects.filter(
            Q(first_name__icontains=request.REQUEST['search']) | 
            Q(last_name__icontains=request.REQUEST['search']) |
            Q(email__icontains=request.REQUEST['search'])
        ).select_related():
            results.append({
                'label': contact.get_full_name(),
                'element_class': 'contact',
                'element_id': unicode(contact.id),
            })
    return HttpResponse(json.dumps(results[:10]), mimetype="text/json")


@permission_required('crm.change_business')
@permission_required('crm.change_project')
@transaction.commit_on_success
def associate_contact(request, business, project=None, user_id=None, action=None):
    if action == 'add':
        if request.POST or 'associate' in request.REQUEST:
            try:
                user_id = request.REQUEST['search_selection']
            except (ValueError, KeyError):
                request.notifications.add(
                    'Your search for "%s" did not match any contacts. You\
                    may create a new contact here.' % request.POST['search'])
                return HttpResponseRedirect('%s?associate=%s' % \
                    (reverse('create_person'), request.get_full_path()))
            
            if user_id:
                try:
                    contact = crm.Contact.objects.get(pk=user_id)
                    if project:
                        crm.ProjectRelationship.objects.get_or_create(
                            contact=contact,
                            project=project,
                        )
                    else:
                        crm.ContactRelationship.objects.get_or_create(
                            from_contact=contact,
                            to_contact=business,
                        )
                        crm.ContactRelationship.objects.get_or_create(
                            to_contact=contact,
                            from_contact=business,
                        )
                except User.DoesNotExist:
                    user = None
    else:
        try:
            contact = crm.Contact.objects.get(pk=user_id)
            if project:
                crm.ProjectRelationship.objects.get(
                    contact=contact,
                    project=project,
                ).delete()
            else:
                crm.ContactRelationship.objects.get(
                    from_contact=contact,
                    to_contact=business,
                ).delete()
                crm.ContactRelationship.objects.get(
                    to_contact=contact,
                    from_contact=business,
                ).delete()
        except crm.Contact.DoesNotExist, crm.ProjectRelationship.DoesNotExist:
            user = None
    
    return HttpResponseRedirect(request.REQUEST['next'])


@permission_required('crm.change_project')
@transaction.commit_on_success
@render_with('crm/business/project/relationship.html')
def edit_project_relationship(request, business, project, user_id):
    user = get_object_or_404(crm.Contact, pk=user_id, projects=project)
    rel = crm.ProjectRelationship.objects.get(project=project, contact=user)
    relationship_form = crm_forms.ProjectRelationshipForm(
        request,
        instance=rel,
    )
    if request.POST and relationship_form.is_valid():
        rel = relationship_form.save()
        return HttpResponseRedirect(request.REQUEST['next'])
    
    context = {
        'user': user,
        'project': project,
        'relationship_form': relationship_form,
    }
    return context


@permission_required('crm.add_project')
@permission_required('crm.change_project')
@render_with('crm/business/project/create_edit.html')
def create_edit_project(request, business=None, project=None):
    if request.POST:
        project_form = crm_forms.ProjectForm(
            request.POST,
            business=business,
            instance=project,
        )
        if project_form.is_valid():
            project = project_form.save()
            url_kwargs = {
                'business_id': project.business.id,
                'project_id': project.id,
            }
            return HttpResponseRedirect(
                reverse('view_project', kwargs=url_kwargs)
            )
    else:
        project_form = crm_forms.ProjectForm(
            business=business, 
            instance=project
        )
    
    context = {
        'business': business,
        'project': project,
        'project_form': project_form,
    }
    return context


@render_with('crm/person/address_book.xml')
def address_book(request, file_name):
    # WARNING: There is no security on this view.  Enable it with caution!
    address_book_enabled = getattr(settings, 'ADDRESS_BOOK_ENABLED', False)
    accepted_file_names = ('gs_phonebook.xml',)
    if address_book_enabled and file_name in accepted_file_names:
        contacts = crm.Profile.objects.select_related('phones', 'user').all()
        context = {
            'contacts': contacts,
        }
        return render_to_response(
            'crm/person/address_book.xml',
            context,
            mimetype='text/xml',
        )
    raise Http404


@transaction.commit_on_success
@render_with('crm/login_registration/activate.html')
def activate_login(request, activation_key):
    if request.user.is_authenticated():
        request.notifications.add(
            "You're already logged in.  Are you sure you need to activate your account?"
        )
        return HttpResponseRedirect('/')
    try:
        login_registration = crm.LoginRegistration.objects.select_related(
            'contact__user'
        ).get(
            activation_key=activation_key.lower(),
        )
    except crm.LoginRegistration.DoesNotExist:
        raise Http404
    if login_registration.has_expired():
        request.notifications.add(
            'This registration has expired.  Please contact the site administrator for a new registration.'
        )
    if login_registration.contact.user:
        request.notifications.add(
            'This account is already active.  Please use the form below to login or reset your password.'
        )
        return HttpResponseRedirect(reverse('auth_login'))
    form = crm_forms.LoginRegistrationForm(request)
    if request.POST and form.is_valid():
        password = form.cleaned_data['password1']
        user = login_registration.activate(password)
        user.groups = login_registration.groups.all()
        user = authenticate(username=user.username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            request.notifications.add(
                "You've successfully activated your account.",
            )
            return HttpResponseRedirect(
                reverse('view_person', args=[login_registration.contact.pk]),
            )
        else:
            request.notifications.add(
                "Activation failed!",
            )
            return HttpResponseRedirect('/')
    return {
        'login_registration': login_registration,
        'form': form,
    }


@transaction.commit_on_success
@render_with('crm/login_registration/create.html')
def create_registration(request):
    ids = request.GET.getlist('ids')
    form = crm_forms.RegistrationGroupForm(request)
    if request.POST and form.is_valid():
        emails = []
        groups = form.cleaned_data['groups']
        for contact in crm.Contact.objects.filter(pk__in=ids):
            profile = \
                crm.LoginRegistration.objects.create_pending_login(contact)
            if profile:
                profile.groups = groups
                emails.append(profile.prepare_email(send=False))
        if emails:
            send_mass_mail(emails)
        request.notifications.add(
            "Successfully sent %d emails" % len(emails),
        )
        return HttpResponseRedirect('/')
    return {
        'form': form,
    }
