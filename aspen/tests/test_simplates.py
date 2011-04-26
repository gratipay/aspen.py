from os.path import join
from textwrap import dedent

import dingus
from aspen.configuration import Configurable
from aspen.http import Response
from aspen.simplates import handle, load_uncached 
from aspen.tests import assert_raises
from aspen.tests.fsfix import attach_teardown, mk
from aspen._tornado.template import Template, Loader


class StubRequest(object):
    def __init__(self, fs):
        """Takes a path under ./fsfix to a simplate.
        """
        self.fs = fs
        self.website = dingus.Dingus()
        c = Configurable.from_argv(['fsfix'])
        c.copy_configuration_to(self)
        self.namespace = {}

def Simplate(fs):
    return load_uncached(StubRequest(fs))

def check(content, filename="index.html", body=True, aspenconf=""):
    mk(('.aspen/aspen.conf', aspenconf), (filename, content))
    request = StubRequest(filename)
    response = Response()
    handle(request, response)
    if body:
        return response.body
    else:
        return response


# Tests
# =====

def test_barely_working():
    mk(('index.html', "Greetings, program!"))
    simplate = Simplate('index.html')
   
    expected = 'text/html'
    actual = simplate[0]
    assert actual == expected, actual

def test_handle_barely_working():
    mk(('index.html', "Greetings, program!"))
    request = StubRequest('index.html')
    response = Response()
    handle(request, response)
    
    expected = "Greetings, program!"
    actual = response.body
    assert actual == expected, actual

def test_simplate_pages_work():
    expected = "Greetings, bar!"
    actual = check("foo = 'bar'Greetings, {{ foo }}!")
    assert actual == expected, actual

def test_simplate_pages_work_with_caret_L():
    expected = "Greetings, bar!"
    actual = check("foo = 'bar'^LGreetings, {{ foo }}!")
    assert actual == expected, actual

def test_simplate_templating_set():
    expected = "1, 2, 3, 4"
    actual = check(dedent("""
        foo = [1,2,3,4]
        nfoo = len(foo)

        
        {% set i = 0 %}
        {% for x in foo %}{% set i += 1 %}{{ x }}{% if i < nfoo %}, {% end %}{% end %}
            """)).strip()
    assert actual == expected, actual

def test_tornado_utf8_works_without_whitespace():
    expected = unichr(1758).encode('utf8')
    actual = Template(u"{{ text }}").generate(text=unichr(1758))
    assert actual == expected, actual

def test_tornado_utf8_breaks_with_whitespace():
    template = Template(u" {{ text }}")
    assert_raises(UnicodeDecodeError, template.generate, text=unichr(1758))

def test_utf8():
    expected = unichr(1758).encode('utf8')
    actual = check("""
"empty first page"
^L
text = unichr(1758)
^L
{{ text }}
    """).strip()
    assert actual == expected, actual

def test_simplates_dont_leak_whitespace():
    """This aims to resolve https://github.com/whit537/aspen/issues/8.

    It is especially weird with JSON output, which we test below. When
    you return [1,2,3,4] that's what you want in the HTTP response
    body.

    """
    actual = check(dedent("""
        
        json_list = [1,2,3,4]
        {{repr(json_list)}}"""))
    expected = "[1, 2, 3, 4]"
    assert actual == expected, repr(actual)


# Unicode example in the /templating/ doc.
# ========================================
# See also: https://github.com/whit537/aspen/issues/10

eg = """\
latinate = chr(181).decode('latin1')
response.headers.set('Content-Type', 'text/plain; charset=latin1')
^L
{{ latinate.encode('latin1') }}"""

def test_content_type_is_right_in_template_doc_unicode_example():
    response = check(eg, body=False)
    expected = "text/plain; charset=latin1"
    actual = response.headers.one('Content-Type')
    assert actual == expected, actual

def test_body_is_right_in_template_doc_unicode_example():
    expected = chr(181)
    actual = check(eg).strip()
    assert actual == expected, actual


# raise Response
# ==============

def test_raise_response_works():
    expected = 404
    response = assert_raises( Response
                            , check
                            , "from aspen import Response; raise Response(404)"
                             )
    actual = response.code
    assert actual == expected, actual


def test_website_is_in_namespace():
    expected = "\nIt worked."
    actual = check("""\
from dingus import Dingus
assert isinstance(website, Dingus), website


It worked.""")
    assert actual == expected, actual

def test_json_basically_works():
    expected = '{"Greetings": "program!"}'
    actual = check( "response.body = {'Greetings': 'program!'}"
                  , filename="foo.json"
                   )
    assert actual == expected, actual

def test_json_defaults_to_application_json():
    expected = 'application/json'
    actual = check( "response.body = {'Greetings': 'program!'}"
                  , filename="foo.json"
                  , body=False
                   ).headers.one('Content-Type')
    assert actual == expected, actual

def test_json_content_type_is_configurable():
    aspenconf = '[aspen]\njson_content_type: floober/blah'
    expected = 'floober/blah'
    actual = check( "response.body = {'Greetings': 'program!'}"
                  , filename="foo.json"
                  , body=False
                  , aspenconf=aspenconf
                   ).headers.one('Content-Type')
    assert actual == expected, actual

def test_json_handles_unicode():
    expected = '{"Greetings": "\u00b5"}'
    actual = check( "response.body = {'Greetings': unichr(181)}"
                  , filename="foo.json"
                   )
    assert actual == expected, actual

def test_json_doesnt_handle_non_ascii_bytestrings():
    assert_raises( UnicodeDecodeError
                 , check
                 , "response.body = {'Greetings': chr(181)}"
                 , filename="foo.json"
                  )


# Teardown
# ========

attach_teardown(globals())
