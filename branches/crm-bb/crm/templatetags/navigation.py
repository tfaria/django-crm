# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# $Id: navigation.py 425 2009-07-14 03:43:01Z tobias $
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

from django import template
from django.conf import settings
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.template.loader import get_template
from django.template import TemplateDoesNotExist

register = template.Library()

MENUITEMS = {
    'caktus_books':
        (
            (_('Caktus Books'), 'crm_home'),
            (_('Interactions'), 'interactions'),
            (_('Ledger'), 'crm_dashboard'),
            (_('Admin'), 'django.contrib.admin.views.main.index'),
        ),
}

class SimpleMenu(object):
    """
    Stores a tree-like menu hierarchy, and renders it up to a chosen item
    on request.
    """
    def __init__(self, menulist):
        """
        Initializes the class.
        
        menulist: a dictionary of menus. Each key is the menu
        label; the corresponding value is a list of (item_label, urlname)
        pairs.  The 'urlname' is then looked up in the URL configuration in
        order to correctly render the matching link. (See example below.)
        """
        self.menus = menulist

    def render(self, menu_name, active=None):
        """
        The render() method returns a HTML string suitable for use as a
        menu bar on a given page.
        
        menu_name: the label of a menu, as specified at class initialization.
        
        active(kw): the active label, if any, in the menu.
        """
        s = '<ul>\n'
        for label, view in self.menus[menu_name]:
            s += '<li class="%s">' % ['background','selected'][view==active]
            s += '<a href="%s">%s</a>' % (reverse(view), label)
            s += '</li>\n'
        s += '</ul>\n'
        return s

menu = SimpleMenu(MENUITEMS)

class MenuNode(template.Node):
    """
    The menu tag takes a menu path whose components are labels separated by spaces.
    All the components from the first to the next-to-last are menu labels, and
    they are going to be rendered as menu bars.  Since they are seen as
    sub-items, or (if you will) as nested tabs in a web page, each component
    is also the active component in the previous menu.
    
    The last component is not rendered as a menu, but it is taken to be the
    active item in the last menu (that is, the next-to-last component).
    """
    def __init__(self, menu_path):
        self.menu_path = menu_path

    def render(self, context):
        self.context = context
        if len(self.menu_path) == 2:
            return self._render_menu(self.menu_path[0], active=self.menu_path[1])
        elif len(self.menu_path) == 1:
            return self._render_menu(self.menu_path[0])
        else:
            raise Exception("Wrong number of arguments to 'menu' tag.  Usage: {% menu <menu name> [<active item>] %}")
            

    def _render_menu(self, menu_name, active=None):
        """
        If the menu has its own template, then use the template.  Otherwise,
        ask its class to do the rendering.
        """
        try:
            menu_template = get_template('menu/%s.html' % menu_name)
            self.context['active'] = active
            return menu_template.render(self.context)
        except TemplateDoesNotExist:
            return menu.render(menu_name, active=active)

def do_menu(parser, token):
    menu_path = token.split_contents()
    return MenuNode(menu_path[1:])

# Usage example:
# {% menu root venue_menu new_visit %}
# will render the 'root' menu with the 'venue_menu' item, if it exists, as
# active; then the 'venue_menu_ menu with the 'new_visit' item, if it
# exists, as active.

register.tag('menu', do_menu)
