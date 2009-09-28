import base64

from django.contrib.auth import authenticate, login
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext


def render_with(template_name):
    """
    Renders the view wrapped by this decorator with the given template.  The
    view should return the context to be used in the template, or an
    HttpResponse.
    
    If the view returns an HttpResponseRedirect, the decorator will redirect
    to the given URL, or to request.REQUEST['next'] (if it exists).
    """
    def render_with_decorator(view_func):
        def wrapper(*args, **kwargs):
            request = args[0]
            response = view_func(*args, **kwargs)
            
            if isinstance(response, HttpResponse):
                if isinstance(response, HttpResponseRedirect) and \
                  'next' in request.REQUEST:
                    return HttpResponseRedirect(request.REQUEST['next'])
                else:
                    return response
            else:
                # assume response is a context dictionary
                context = response
                return render_to_response(
                    template_name, 
                    context, 
                    context_instance=RequestContext(request),
                )
        return wrapper
    return render_with_decorator


# based on http://www.djangosnippets.org/snippets/243/
def view_or_basicauth(view, request, test_func, realm='', *args, **kwargs):
    """
    This is a helper function used by both 'logged_in_or_basicauth' and
    'has_perm_or_basicauth' that does the nitty of determining if they
    are already logged in or if they have provided proper http-authorization
    and returning the view if all goes well, otherwise responding with a 401.
    """
    if test_func(request.user):
        # Already logged in, just return the view.
        return view(request, *args, **kwargs)

    # They are not logged in. See if they provided login credentials
    if 'HTTP_AUTHORIZATION' in request.META:
        auth = request.META['HTTP_AUTHORIZATION'].split()
        if len(auth) == 2:
            # NOTE: We are only supporting basic authentication for now.
            if auth[0].lower() == "basic":
                uname, passwd = base64.b64decode(auth[1]).split(':')
                user = authenticate(username=uname, password=passwd)
                if user is not None:
                    if user.is_active:
                        login(request, user)
                        request.user = user
                        if test_func(user):
                            return view(request, *args, **kwargs)

    # Either they did not provide an authorization header or
    # something in the authorization attempt failed. Send a 401
    # back to them to ask them to authenticate.
    response = HttpResponse()
    response.status_code = 401
    response['WWW-Authenticate'] = 'Basic realm="%s"' % realm
    return response


def logged_in_or_basicauth(realm=''):
    """
    A simple decorator that requires a user to be logged in. If they are not
    logged in the request is examined for a 'authorization' header.

    If the header is present it is tested for basic authentication and
    the user is logged in with the provided credentials.

    If the header is not present a http 401 is sent back to the
    requestor to provide credentials.

    The purpose of this is that in several django projects I have needed
    several specific views that need to support basic authentication, yet the
    web site as a whole used django's provided authentication.

    The uses for this are for urls that are access programmatically such as
    by rss feed readers, yet the view requires a user to be logged in. Many rss
    readers support supplying the authentication credentials via http basic
    auth (and they do NOT support a redirect to a form where they post a
    username/password.)

    Use is simple:

    @logged_in_or_basicauth()
    def your_view:
        ...

    You can provide the name of the realm to ask for authentication within.
    Don't forget to include the () even if you aren't passing any arguments
    to the decorator.
    """
    def view_decorator(func):
        def wrapper(request, *args, **kwargs):
            return view_or_basicauth(
                func,
                request,
                lambda u: u.is_authenticated(),
                realm, 
                *args, 
                **kwargs
            )
        return wrapper
    return view_decorator


def has_perm_or_basicauth(perm, realm=''):
    """
    This is similar to the above decorator 'logged_in_or_basicauth'
    except that it requires the logged in user to have a specific
    permission.

    Use:

    @has_perm_or_basicauth('app.view_forumcollection')
    def your_view:
        ...
    
    """
    def view_decorator(func):
        def wrapper(request, *args, **kwargs):
            return view_or_basicauth(
                func,
                request,
                lambda u: u.has_perm(perm),
                realm, 
                *args, 
                **kwargs
            )
        return wrapper
    return view_decorator