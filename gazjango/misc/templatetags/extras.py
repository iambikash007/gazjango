from django import template
from django.core.urlresolvers import reverse
from django.utils.safestring  import mark_safe
from django.utils.html        import conditional_escape, strip_tags

from django.contrib.humanize.templatetags.humanize import ordinal
from gazjango.misc.helpers import get_static_path, get_jquery_path
import gazjango.misc.helpers # would import smart_truncate, but the filter has same name

from datetime import date

register = template.Library()


### curly-quotes removal

@register.filter
def plain_text(str):
    return strip_tags(str).replace(u'\u201c', '"').replace(u'\u201d', '"')


### filter that should maybe go in views, but it's convenient

@register.filter
def order_by(queryset, args):
    args = [x.strip() for x in args.split(',')]
    return queryset.order_by(*args)


### replace emails with numeric entities, to fight spam

@register.filter
def entity_sub(string, to_replace=None):
    if to_replace:
        def rep(x):
            return ord(x) if x in to_replace else x
    else:
        rep = ord
    return mark_safe(''.join("&#%d;" % rep(x) for x in string))


### various filters to ease the outputting of more human text

@register.filter
def smart_truncate(string, length, autoescape=True):
    if autoescape:
        string = conditional_escape(string)
    try:
        length = int(length)
    except ValueError:
        return string # fail silently
    return gazjango.misc.helpers.smart_truncate(string, length, 5)
smart_truncate.needs_autoescape = True
smart_truncate.is_safe = True


@register.filter
def join_authors(authors, format='', autoescape=None):
    """
    Takes an m2m with users (eg `story.authors_in_order`) and returns
    a string formatted for bylines: something along the lines of
    "JOE SCHMOE, STAFF REPORTER; JANE MCBANE, ARTS EDITOR".
    
    The format argument tells the filter how to format the return value
    (surprisingly enough). This is a string, which can specify as many of the
    following arguments as you want, in whatever order. If you supply
    conflicting format args (and really, why would you?), the last one wins.
    
    If the format string includes an integer, we return only that many authors;
    an "a" returns them all, which is the default.
    
    If the format string includes an "l", we link to authors' profile pages;
    if it includes a "p", for "plain", we do not. Not linking is the default.
    
    If the format string includes a "u", the whole string is upper-case; a
    "d" means the whole string is downcased; a "t" means the string is in
    title-case (like "Joe Schmoe, Staff Reporter"). "u" is default.
    
    If the format string includes an "s", positions are shown; if it includes
    an "x", positions are not shown. "s" is default.
    
    If the format string includes a "," or a ";", it uses that to separate
    authors. (Note that a "," with positions will look stupid.) A "b" means
    to insert a <br/>.
    """
    if not authors:
        return ''
    
    limit = None
    link = False
    case = 'u'
    positions = True
    sep = '; '
    for char in format.lower():
        if char.isdigit():
            limit = int(char)
        elif char == 'a':
            limit = None
        elif char in 'lp':
            link = (char == 'l')
        elif char in 'dtu':
            case = char
        elif char in 'sx':
            positions = (char == 's')
        elif char in ";,b":
            sep = '<br/> ' if char == 'b' else (char + ' ')
        else:
            pass
    
    result = list(authors.all()[:limit] if limit else authors.all())
    
    esc = conditional_escape if autoescape else (lambda x: x)
    
    if case == 'd':
        casify = lambda s: esc(s).lower()
    elif case == 'u':
        casify = lambda s: esc(s).upper()
    else: # case == 't'
        casify = esc
        #casify = lambda s: ' '.join(x.capitalize() for x in esc(s).split())
    
    def reps(author):
        results = { 'name': casify(author.name) }
        if positions:
            pos = author.position()
            results['pos'] = ', ' + casify(pos) if pos else ''
        if link:
            results['url'] = author.get_absolute_url()
        return results
    
    base = "%(name)s"
    if positions: base += "%(pos)s"
    if link:      base = "<a href='%(url)s'>" + base + "</a>"
    
    return mark_safe(sep.join(base % reps(author) for author in result))

join_authors.needs_autoescape = True
join_authors.is_safe = True




@register.filter
def issue_url(date):
    "Returns the url for ``date``'s issue."
    d = { 'year': date.year, 'month': date.month, 'day': date.day }
    return reverse('issue', kwargs=d)
issue_url.is_safe = True


@register.filter
def rsd_url(date):
    """Returns the url for ``date``'s RSD."""
    d = { 'year': date.year, 'month': date.month, 'day': date.day }
    return reverse('rsd', kwargs=d)
rsd_url.is_safe = True



@register.filter
def near_future_date(date):
    """
    Returns just the name of the day if it's in the next few days; if it's
    in the next month, a string like "Tuesday the 5th"; otherwise, a string
    like "May 12".
    """
    distance = (date - date.today()).days
    if 0 <= distance < 6:
        return date.strftime("%A")
    elif 0 < distance < 20:
        return date.strftime("%A the ") + ordinal(date.day)
    else:
        return date.strftime("%B ") + str(date.day)

near_future_date.is_safe = True

@register.filter
def day(date):
    """
    Returns the # of the day.
    """
    return """%s %s""" % (date.day,date.strftime("%A"))
        
@register.filter
def month(date):
    """
    Returns the name of the month
    """
    return date.strftime("%B")

@register.filter
def year(date):
    return date.strftime("%Y")

@register.filter
def month_name(num):
    """Returns the (full) name of the month numbered `num`."""
    return date(2008, int(num), 1).strftime("%B")

month_name.is_safe = True


@register.filter
def negate(n):
    """Returns the negative of the number."""
    return -int(n)


@register.filter
def in_groups_of(lst, num=2):
    """
    Returns the list split up into groups of length `num`. For example, calling
    this with `num=2` on range(5) would return [ [0, 1], [2, 3], [4] ].
    """
    if lst is None:
        return [[]]
    return [lst[num*i:num*(i+1)] for i in range((len(lst) + num - 1) // num)]


@register.filter
def before(arg, prefix):
    return prefix + arg if arg else ''

@register.filter
def follow(arg, suffix):
    return arg + suffix if arg else ''


@register.filter
def dict_lookup(dictionary, key):
    return dictionary[key]

### stuff related to the AddThis button


ADD_THIS_PRE = """
<script type="text/javascript">
addthis_pub  = 'dailygazette';
addthis_options = 'facebook, favorites, delicious, twitter, google, live, furl, more';
</script>"""

ADD_THIS_HOVER = """
<a href="http://www.addthis.com/bookmark.php" onmouseover="return addthis_open(this, '', '[URL]', '[TITLE]')" onmouseout="addthis_close()" onclick="return addthis_sendto()"><img src="http://s9.addthis.com/button1-addthis.gif" alt="" border="0" height="16" width="125"></a>
"""

ADD_THIS_NO_HOVER = """
<a href="http://www.addthis.com/bookmark.php" onclick="return addthis_sendto()"><img src="http://s9.addthis.com/button1-addthis.gif" alt="" border="0" height="16" width="125"></a>
"""

ADD_THIS_POST = """
<script type="text/javascript" src="http://s7.addthis.com/js/152/addthis_widget.js"></script>"""


class AddThisNode(template.Node):
    def __init__(self, popup_on_hover):
        self.text = ADD_THIS_PRE
        if popup_on_hover:
            self.text += ADD_THIS_HOVER
        else:
            self.text += ADD_THIS_NO_HOVER
        self.text = mark_safe(self.text + ADD_THIS_POST)
    
    def render(self, context):
        return self.text
    

@register.tag(name="add_this")
def get_addthis_button(parser, token):
    """
    This will output a button for AddThis.com, with the "hover" argument
    telling whether the button should pop-up a small window with links
    to bookmarking services or not.
    
    Usage::
    
        {% add_this [hover|no-hover] %}
    """
    split = token.split_contents()
    if len(split) == 1:
        tag_name = split[0]
    elif len(split) == 2:
        tag_name, popup_on_hover = split
    else:
        raise template.TemplateSyntaxError, "%r tag requires one or zero arguments" % token.contents.split()[0]
    
    if popup_on_hover and popup_on_hover not in ('hover', 'no-hover'):
        raise template.TemplateSyntaxError, "invalid argument to %r" % tag_name
    
    return AddThisNode(popup_on_hover == 'hover' if popup_on_hover else True)



### static file URLs: change this if/when the static serving scheme changes
STATIC_FILE_KINDS = ('css', 'js', 'images', 'uploads', 'admin', 'v2')

class StaticFileURLNode(template.Node):
    def __init__(self, kind, name):
        self.kind = kind
        self.name = name
    
    def render(self, context):
        return get_static_path(self.kind, self.name)
    

@register.tag(name="static")
def get_static_file_link(parser, token):
    """
    This will link to a static file on the site, to be served by a regular
    webserver (in production).
    
    Usage::
    
        {% static [type] [path] %}
    
    [type] should be one of STATIC_FILE_KINDS: css, js, images, or uploads.
    [path] is the name of the resource. For example:
    
        {% static css page/story.css %}
    """
    split = token.split_contents()
    if len(split) != 3:
        raise template.TemplateSyntaxError, "%r tag requires two arguments" % split[0]
    tag_name, kind, path = split
    if kind not in STATIC_FILE_KINDS:
        raise template.TemplateSyntaxError, "%r: invalid kind '%s'" % (tag_name, kind)
    return StaticFileURLNode(kind, path)



### jquery linking tag

class jQueryNode(template.Node):
    def __init__(self):
        self.url = get_jquery_path()
    
    def render(self, context):
        return '<script type="text/javascript" src="%s"></script>' % self.url
    

@register.tag(name='jQuery')        
def get_jquery_link(parser, token):
    """
    This will output the script necessary to load the jQuery library, either
    from Google or locally, depending on the value of settings.LOCAL_JQUERY.
    """
    split = token.split_contents()
    if len(split) != 1:
        raise template.TemplateSyntaxError, "%r tag takes no arguments." % split[0]
    return jQueryNode()

