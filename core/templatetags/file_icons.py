
from django import template
import os

register = template.Library()

EXT_ICON_MAP = {
    '.pdf': 'pdf.svg',
    '.doc': 'word.svg',
    '.docx': 'word.svg',
    '.xls': 'excel.svg',
    '.xlsx': 'excel.svg',
    '.csv': 'csv.svg',
    '.ppt': 'pptx.svg',
    '.pptx': 'pptx.svg',
}

@register.filter
def file_icon(value):
    """Return the filename of the icon for a given file name or path.
    Usage in template: {{ item.file.name|file_icon }}
    """
    if not value:
        return 'file.svg'
    name = os.path.basename(value)
    _, ext = os.path.splitext(name.lower())
    return EXT_ICON_MAP.get(ext, 'file.svg')

@register.filter
def file_format(value):
    """Return the file extension label for a given file name or path.
    Usage in template: {{ item.file.name|file_format }}
    """
    if not value:
        return 'FILE'
    name = os.path.basename(value)
    _, ext = os.path.splitext(name)
    return ext.replace('.', '').upper() if ext else 'FILE'
