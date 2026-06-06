import re
import html

def urlify_old(value):
    pat1 = re.compile(
        r"(^|[\n ])(([\w]+?://[\w\#$%&~.\-;:=,?@\[\]+]*)(/[\w\#$%&~/.\-;:=,?@\[\]+]*)?)",
        re.IGNORECASE | re.DOTALL
    )
    value = pat1.sub(r'\1<a href="\2">\3</a>', value)
    return value

def urlify_new(value):
    value = html.escape(value)
    pat1 = re.compile(
        r"(^|[\n ])(([\w]+?://[\w\#$%&~.\-;:=,?@\[\]+]*)(/[\w\#$%&~/.\-;:=,?@\[\]+]*)?)",
        re.IGNORECASE | re.DOTALL
    )
    value = pat1.sub(r'\1<a href="\2">\3</a>', value)
    return value

print("OLD:", urlify_old("I love <http://example.com/>"))
print("NEW:", urlify_new("I love <http://example.com/>"))

print("OLD2:", urlify_old("Visit http://example.com/foo'bar"))
print("NEW2:", urlify_new("Visit http://example.com/foo'bar"))
