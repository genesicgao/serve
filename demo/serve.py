# -*- encoding:utf-8 -*-
"""
Views and functions for serving static files. These are only to be used
during development, and SHOULD NOT be used in a production setting.
"""
from __future__ import unicode_literals

import mimetypes
import os
import posixpath
import re
import stat
import StringIO
from django.conf import settings
from django.http import (
    FileResponse, Http404, HttpResponse, HttpResponseNotModified,
    HttpResponseRedirect,
)
from django.template import Context, Engine, TemplateDoesNotExist, loader
from django.utils.http import http_date, parse_http_date
from django.utils.six.moves.urllib.parse import unquote
from django.utils.translation import ugettext as _, ugettext_lazy
from PIL import Image, ImageDraw, ImageFont, ImageEnhance


def serve(request, path, document_root=None, show_indexes=False):
    """
    Serve static files below a given point in the directory structure.

    To use, put a URL pattern such as::

        from django.views.static import serve

        url(r'^(?P<path>.*)$', serve, {'document_root': '/path/to/my/files/'})

    in your URLconf. You must provide the ``document_root`` param. You may
    also set ``show_indexes`` to ``True`` if you'd like to serve a basic index
    of the directory.  This index view will use the template hardcoded below,
    but if you'd like to override it, you can create a template called
    ``static/directory_index.html``.
    """
    path = posixpath.normpath(unquote(path))
    path = path.lstrip('/')
    newpath = ''
    for part in path.split('/'):
        if not part:
            # Strip empty path components.
            continue
        drive, part = os.path.splitdrive(part)
        head, part = os.path.split(part)
        if part in (os.curdir, os.pardir):
            # Strip '.' and '..' in path.
            continue
        newpath = os.path.join(newpath, part).replace('\\', '/')
    if newpath and path != newpath:
        return HttpResponseRedirect(newpath)
    true_path = newpath
    size_mode = (0, 0)
    rotate_mode = 0
    width_mode = 0
    height_mode = 0
    long_mode = 0
    short_mode = 0
    max_mode = 0
    cut_mode = (0, 0)
    cut_px_mode = (0, 0)
    cut_py_mode = (0, 0)
    u_mode = (0, 0)
    size_regex = re.compile(r'(.*/?.+\..+)_(\d+)X(\d+)')
    rotate_regex = re.compile(r'(.*/?.+\..+)_A(\d+)')
    width_regex = re.compile(r'(.*/?.+\..+)_W(\d+)')
    height_regex = re.compile(r'(.*/?.+\..+)_H(\d+)')
    thumb_regex = re.compile(r'(.*/?.+\..+)_THUMB')
    long_regex = re.compile(r'(.*/?.+\..+)_L(\d+)')
    short_regex = re.compile(r'(.*/?.+\..+)_S(\d+)')
    max_regex = re.compile(r'(.*/?.+\..+)_MAX(\d+)')
    cut_regex = re.compile(r'(.*/?.+\..+)_C(\d+)-(\d+)')
    cut_px_regex = re.compile(r'(.*/?.+\..+)_PX(\d+)-(\d+)')
    cut_py_regex = re.compile(r'(.*/?.+\..+)_PY(\d+)-(\d+)')
    u_regex = re.compile(r'(.*/?.+\..+)_U(\d+)-(\d+)')
    if size_regex.findall(newpath):
        true_path = size_regex.findall(newpath)[0][0]
        size_mode = (int(size_regex.findall(newpath)[0][1]),
                     int(size_regex.findall(newpath)[0][2]))
    if rotate_regex.findall(newpath):
        true_path = rotate_regex.findall(newpath)[0][0]
        rotate_mode = int(rotate_regex.findall(newpath)[0][1])
    if width_regex.findall(newpath):
        true_path = width_regex.findall(newpath)[0][0]
        width_mode = int(width_regex.findall(newpath)[0][1])
    if height_regex.findall(newpath):
        true_path = height_regex.findall(newpath)[0][0]
        height_mode = int(height_regex.findall(newpath)[0][1])
    if thumb_regex.findall(newpath):
        true_path = thumb_regex.findall(newpath)[0]
        width_mode = 1000
    if long_regex.findall(newpath):
        true_path = long_regex.findall(newpath)[0][0]
        long_mode = int(long_regex.findall(newpath)[0][1])
    if short_regex.findall(newpath):
        true_path = short_regex.findall(newpath)[0][0]
        short_mode = int(short_regex.findall(newpath)[0][1])
    if max_regex.findall(newpath):
        true_path = max_regex.findall(newpath)[0][0]
        max_mode = int(max_regex.findall(newpath)[0][1])
    if cut_regex.findall(newpath):
        true_path = cut_regex.findall(newpath)[0][0]
        cut_mode = (int(cut_regex.findall(newpath)[0][1]),
                    int(cut_regex.findall(newpath)[0][2]))
    if cut_px_regex.findall(newpath):
        true_path = cut_px_regex.findall(newpath)[0][0]
        cut_px_mode = (int(cut_px_regex.findall(newpath)[0][1]),
                       int(cut_px_regex.findall(newpath)[0][2]))
    if cut_py_regex.findall(newpath):
        true_path = cut_py_regex.findall(newpath)[0][0]
        cut_py_mode = (int(cut_py_regex.findall(newpath)[0][1]),
                       int(cut_py_regex.findall(newpath)[0][2]))
    if u_regex.findall(newpath):
        true_path = u_regex.findall(newpath)[0][0]
        u_mode = (int(u_regex.findall(newpath)[0][1]),
                  int(u_regex.findall(newpath)[0][2]))
    fullpath = os.path.join(document_root, true_path)
    if os.path.isdir(fullpath):
        if show_indexes:
            return directory_index(newpath, fullpath)
        raise Http404(_("Directory indexes are not allowed here."))
    if not os.path.exists(fullpath):
        raise Http404(_('"%(path)s" does not exist') % {'path': fullpath})
    # Respect the If-Modified-Since header.
    statobj = os.stat(fullpath)
    content_type, encoding = mimetypes.guess_type(fullpath)
    content_type = content_type or 'application/octet-stream'
    try:
        image_file = Image.open(fullpath)
        out_image = image_file
        if size_mode != (0, 0):
            resize_rate = min(image_file.width * 1.0 / size_mode[0],
                              image_file.height * 1.0 / size_mode[1])
            target_size = (int(image_file.width / resize_rate + 0.5),
                           int(image_file.height / resize_rate + 0.5))
            out_image = image_file.resize(target_size, resample=Image.LANCZOS)
            out_image = out_image.crop((int(
                0.5 * (target_size[0] - size_mode[0])), int(
                0.5 * (target_size[1] - size_mode[1])),
                                        int(0.5 * (
                                            target_size[0] + size_mode[0])),
                                        int(0.5 * (
                                            target_size[1] + size_mode[1]))))
        if rotate_mode != 0:
            out_image = image_file.rotate(rotate_mode, expand=True)
        if width_mode != 0:
            width = width_mode
            height = int(image_file.height * width * 1.0 / image_file.width)
            out_image = image_file.resize((width, height))
        if height_mode != 0:
            height = height_mode
            width = int(image_file.width * height * 1.0 / image_file.height)
            out_image = image_file.resize((width, height))
        if long_mode != 0:
            if image_file.width >= image_file.height:
                width = long_mode
                height = int(image_file.height * width * 1.0 / image_file.width)
                out_image = image_file.resize((width, height))
            else:
                height = long_mode
                width = int(image_file.width * height * 1.0 / image_file.height)
                out_image = image_file.resize((width, height))
        if short_mode != 0:
            if image_file.width <= image_file.height:
                width = short_mode
                height = int(image_file.height * width * 1.0 / image_file.width)
                out_image = image_file.resize((width, height))
            else:
                height = short_mode
                width = int(image_file.width * height * 1.0 / image_file.height)
                out_image = image_file.resize((width, height))
        if max_mode != 0:
            if image_file.width >= image_file.height:
                if image_file.width > max_mode:
                    width = max_mode
                    height = int(
                        image_file.height * width * 1.0 / image_file.width)
                    out_image = image_file.resize((width, height))
            else:
                if image_file.height > max_mode:
                    height = max_mode
                    width = int(
                        image_file.width * height * 1.0 / image_file.height)
                    out_image = image_file.resize((width, height))
        if cut_mode != (0, 0):
            width = int(image_file.width * 1.0 / (cut_mode[1] + 1))
            height = int(image_file.height * 1.0 / (cut_mode[0] + 1))
            out_image = image_file.crop((0, 0, width, height))
        if cut_px_mode != (0, 0):
            height = int(image_file.height * 1.0 / (cut_px_mode[0] + 1))
            out_image = image_file.crop((0, (cut_px_mode[1] - 1) * height,
                                         image_file.width,
                                         cut_px_mode[1] * height))
        if cut_py_mode != (0, 0):
            width = int(image_file.width * 1.0 / (cut_py_mode[0] + 1))
            out_image = image_file.crop(((cut_py_mode[1] - 1) * width, 0,
                                         cut_py_mode[1] * width,
                                         image_file.height))
        if u_mode != (0, 0):
            if image_file.width >= image_file.height:
                if u_mode[0] < image_file.width < u_mode[1]:
                    width = u_mode[0]
                    height = int(
                        image_file.height * width * 1.0 / image_file.width)
                    out_image = image_file.resize((width, height))
                elif image_file >= u_mode[1]:
                    width = image_file.width / 2
                    height = image_file.height / 2
                    out_image = image_file.resize((width, height))
            else:
                if u_mode[0] < image_file.height < u_mode[1]:
                    height = u_mode[0]
                    width = int(
                        image_file.width * height * 1.0 / image_file.height)
                    out_image = image_file.resize((width, height))
                elif image_file >= u_mode[1]:
                    height = image_file.height / 2
                    width = image_file.width / 2
                    out_image = image_file.resize((width, height))
        out = StringIO.StringIO()
        out_image.save(out, image_file.format)
        s = out.getvalue()
        out.close()
        response = FileResponse(s, content_type=content_type)
        response["Last-Modified"] = http_date(statobj.st_mtime)
        response["Content-Length"] = len(s)
        if encoding:
            response["Content-Encoding"] = encoding
        return response
    except Exception:
        response = FileResponse(open(fullpath, 'rb'), content_type=content_type)
        response["Last-Modified"] = http_date(statobj.st_mtime)
        if stat.S_ISREG(statobj.st_mode):
            response["Content-Length"] = statobj.st_size
        if encoding:
            response["Content-Encoding"] = encoding
        return response


DEFAULT_DIRECTORY_INDEX_TEMPLATE = """
{% load i18n %}
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta http-equiv="Content-type" content="text/html; charset=utf-8" />
    <meta http-equiv="Content-Language" content="en-us" />
    <meta name="robots" content="NONE,NOARCHIVE" />
    <title>{% blocktrans %}Index of {{ directory }}{% endblocktrans %}</title>
  </head>
  <body>
    <h1>{% blocktrans %}Index of {{ directory }}{% endblocktrans %}</h1>
    <ul>
      {% if directory != "/" %}
      <li><a href="../">../</a></li>
      {% endif %}
      {% for f in file_list %}
      <li><a href="{{ f|urlencode }}">{{ f }}</a></li>
      {% endfor %}
    </ul>
  </body>
</html>
"""
template_translatable = ugettext_lazy("Index of %(directory)s")


def directory_index(path, fullpath):
    try:
        t = loader.select_template([
            'static/directory_index.html',
            'static/directory_index',
        ])
    except TemplateDoesNotExist:
        t = Engine().from_string(DEFAULT_DIRECTORY_INDEX_TEMPLATE)
    files = []
    for f in os.listdir(fullpath):
        if not f.startswith('.'):
            if os.path.isdir(os.path.join(fullpath, f)):
                f += '/'
            files.append(f)
    c = Context({
        'directory': path + '/',
        'file_list': files,
    })
    return HttpResponse(t.render(c))


def was_modified_since(header=None, mtime=0, size=0):
    """
    Was something modified since the user last downloaded it?

    header
      This is the value of the If-Modified-Since header.  If this is None,
      I'll just return True.

    mtime
      This is the modification time of the item we're talking about.

    size
      This is the size of the item we're talking about.
    """
    try:
        if header is None:
            raise ValueError
        matches = re.match(r"^([^;]+)(; length=([0-9]+))?$", header,
                           re.IGNORECASE)
        header_mtime = parse_http_date(matches.group(1))
        header_len = matches.group(3)
        if header_len and int(header_len) != size:
            raise ValueError
        if int(mtime) > header_mtime:
            raise ValueError
    except (AttributeError, ValueError, OverflowError):
        return True
    return False
