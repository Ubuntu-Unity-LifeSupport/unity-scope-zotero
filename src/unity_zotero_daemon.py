#! /usr/bin/python3
# -*- coding: utf-8 -*-

# Copyright(C) 2013 Mark Tully <markjtully@gmail.com>
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Unity
from gi.repository import Gio, GLib
import gettext
import os.path
import shutil
import sqlite3
import html

APP_NAME = 'unity-scope-zotero'
LOCAL_PATH = '/usr/share/locale/'
gettext.bindtextdomain(APP_NAME, LOCAL_PATH)
gettext.textdomain(APP_NAME)
_ = gettext.gettext

GROUP_NAME = 'com.canonical.Unity.Scope.Academic.Zotero'
UNIQUE_PATH = '/com/canonical/unity/scope/academic/zotero'
SEARCH_URI = ''
SEARCH_HINT = _('Search Zotero')
NO_RESULTS_HINT = _('Sorry, there are no Zotero results that match your search.')
PROVIDER_CREDITS = _('Powered by Zotero')
SVG_DIR = '/usr/share/icons/unity-icon-theme/places/svg/'
PROVIDER_ICON = SVG_DIR + 'service-zotero.svg'
DEFAULT_RESULT_ICON = SVG_DIR + 'result-academic.svg'
DEFAULT_RESULT_MIMETYPE = 'text/html'
DEFAULT_RESULT_TYPE = Unity.ResultType.DEFAULT

PATHS = [os.getenv("HOME") + "/.mozilla/firefox/", os.getenv("HOME") + "/.zotero/zotero/"]
QUERY = '''SELECT title.value, COALESCE(url.value, url2.value), pub.value, GROUP_CONCAT(COALESCE(c1.lastName, "") || ' ' || COALESCE(c2.lastName, "") || ' ' || COALESCE(c3.lastName, "") || ' ' || COALESCE(c4.lastName, "") || ' ' || COALESCE(c5.lastName, "")) as creator, abstract.value
FROM items i
INNER JOIN itemDataValues title ON title.valueID =(SELECT itemData.valueID FROM itemData WHERE itemData.fieldID =(SELECT fieldID FROM fields WHERE fields.fieldName = 'title' LIMIT 1) AND itemData.itemID=i.itemID LIMIT 1)
LEFT JOIN itemTypes t ON t.itemTypeID = i.itemTypeID
LEFT JOIN itemDataValues url ON url.valueID = (SELECT itemData.valueID FROM itemData WHERE itemData.fieldID =(SELECT fieldID FROM fields WHERE fields.fieldName = 'url' LIMIT 1) AND itemData.itemID=i.itemID LIMIT 1)
LEFT JOIN itemDataValues url2 on url2.valueID = (SELECT itemData.valueID FROM itemData WHERE itemData.fieldID =(SELECT fieldID FROM fields WHERE fields.fieldName = 'url' LIMIT 1) AND itemData.itemID = (SELECT itemAttachments.itemID FROM itemAttachments WHERE itemAttachments.sourceItemID = i.itemID) LIMIT 1)
LEFT JOIN creatorData c1 ON c1.creatorDataID =(SELECT creatorDataID FROM creators WHERE creatorID =(SELECT creatorID FROM itemCreators WHERE itemID = i.itemID ORDER BY orderIndex LIMIT 0,1) LIMIT 1)
LEFT JOIN creatorData c2 ON c2.creatorDataID =(SELECT creatorDataID FROM creators WHERE creatorID =(SELECT creatorID FROM itemCreators WHERE itemID = i.itemID ORDER BY orderIndex LIMIT 1,1) LIMIT 1)
LEFT JOIN creatorData c3 ON c3.creatorDataID =(SELECT creatorDataID FROM creators WHERE creatorID =(SELECT creatorID FROM itemCreators WHERE itemID = i.itemID ORDER BY orderIndex LIMIT 2,1) LIMIT 1)
LEFT JOIN creatorData c4 ON c4.creatorDataID =(SELECT creatorDataID FROM creators WHERE creatorID =(SELECT creatorID FROM itemCreators WHERE itemID = i.itemID ORDER BY orderIndex LIMIT 3,1) LIMIT 1)
LEFT JOIN creatorData c5 ON c5.creatorDataID =(SELECT creatorDataID FROM creators WHERE creatorID =(SELECT creatorID FROM itemCreators WHERE itemID = i.itemID ORDER BY orderIndex LIMIT 4,1) LIMIT 1)
LEFT JOIN itemDataValues pub ON pub.valueID =(SELECT itemData.valueID FROM itemData WHERE itemData.fieldID =(SELECT fieldID FROM fields WHERE fields.fieldName = 'publicationTitle' LIMIT 1) AND itemData.itemID=i.itemID LIMIT 1)
LEFT JOIN itemDataValues abstract ON abstract.valueID =(SELECT itemData.valueID FROM itemData WHERE itemData.fieldID =(SELECT fieldID FROM fields WHERE fields.fieldName = 'abstractNote' LIMIT 1) AND itemData.itemID=i.itemID LIMIT 1)
LEFT JOIN deletedItems ON i.itemID = deletedItems.itemID
WHERE deletedItems.itemID IS NULL AND t.typeName = "journalArticle"
GROUP BY title.value'''

c1 = {'id': 'scholar',
      'name': _('Articles'),
      'icon': SVG_DIR + 'group-installed.svg',
      'renderer': Unity.CategoryRenderer.VERTICAL_TILE}
CATEGORIES = [c1]

FILTERS = []

META0 = {'id': 'authors',
         'type': 's',
         'field': Unity.SchemaFieldType.OPTIONAL}
META1 = {'id': 'journal',
         'type': 's',
         'field': Unity.SchemaFieldType.OPTIONAL}
META2 = {'id': 'abstract',
         'type': 's',
         'field': Unity.SchemaFieldType.OPTIONAL}
META3 = {'id': 'fulltitle',
         'type': 's',
         'field': Unity.SchemaFieldType.OPTIONAL}
EXTRA_METADATA = [META0, META1, META2, META3]


def search(search, filters):
    '''
    Any search method returning results as a list of tuples.
    Available tuple fields:
    uri(string)
    icon(string)
    title(string)
    comment(string)
    dnd_uri(string)
    mimetype(string)
    category(int)
    result_type(Unity ResultType)
    extras metadata fields(variant)
    '''
    results = []

    dbFile = ""
    for path in PATHS:
        for folder in [default for default in os.listdir(path) if default.endswith(".default")]:
            dbFile = path + folder + "/zotero/zotero.sqlite"

        if os.path.exists(dbFile):
            backup_dbFile = path + folder + "/zotero/zotero-lensbackup.sqlite"
            shutil.copy2(dbFile, backup_dbFile)

        records = []
        if os.path.exists(backup_dbFile):
            conn = sqlite3.connect(backup_dbFile)
            c = conn.cursor()
            rows = c.execute(QUERY)
            records = c.fetchall()
            c.close()
        for record in records:
            title = record[0]
            uri = record[1]
            journal = record[2]
            authors = record[3]
            abstract = record[4]
            if search.lower() in title.lower():
                if uri:
                    results.append({'uri': uri,
                                    'title': title,
                                    'authors': authors,
                                    'journal': journal,
                                    'abstract': abstract})
    return results


class Preview(Unity.ResultPreviewer):
    '''
    Creates the preview for the result
    '''
    def do_run(self):
        '''
        Create a preview and return it
        '''
        preview = Unity.GenericPreview.new(self.result.title, '', None)
        preview.props.image_source_uri = 'file://%s' % self.result.icon_hint
        try:
            preview.props.subtitle = self.result.metadata['authors'].get_string()
        except KeyError as e:
            print(e)
        description = ''
        try:
            description += self.result.metadata['journal'].get_string() + '\n\n'
        except KeyError as e:
            print(e)
        try:
            description += html.escape(self.result.metadata['abstract'].get_string())
        except KeyError as e:
            print(e)
        preview.props.description_markup = description

        # Add the "View" action
        show_action = Unity.PreviewAction.new("show", _("View Article"), None)
        preview.add_action(show_action)
        return preview


# Classes below this point establish communication
# with Unity, you probably shouldn't modify them.


class MySearch(Unity.ScopeSearchBase):
    def __init__(self, search_context):
        super(MySearch, self).__init__()
        self.set_search_context(search_context)

    def do_run(self):
        '''
        Adds results to the model
        '''
        try:
            result_set = self.search_context.result_set
            for i in search(self.search_context.search_query,
                            self.search_context.filter_state):
                if not 'uri' in i or not i['uri'] or i['uri'] == '':
                    continue
                if not 'icon' in i or not i['icon'] or i['icon'] == '':
                    i['icon'] = DEFAULT_RESULT_ICON
                if not 'mimetype' in i or not i['mimetype'] or i['mimetype'] == '':
                    i['mimetype'] = DEFAULT_RESULT_MIMETYPE
                if not 'result_type' in i or not i['result_type'] or i['result_type'] == '':
                    i['result_type'] = DEFAULT_RESULT_TYPE
                if not 'category' in i or not i['category'] or i['category'] == '':
                    i['category'] = 0
                if not 'title' in i or not i['title']:
                    i['title'] = ''
                if not 'comment' in i or not i['comment']:
                    i['comment'] = ''
                if not 'dnd_uri' in i or not i['dnd_uri'] or i['dnd_uri'] == '':
                    i['dnd_uri'] = i['uri']
                i['provider_credits'] = GLib.Variant('s', PROVIDER_CREDITS)
                result_set.add_result(**i)
        except Exception as error:
            print(error)


class Scope(Unity.AbstractScope):
    def __init__(self):
        Unity.AbstractScope.__init__(self)

    def do_get_search_hint(self):
        return SEARCH_HINT

    def do_get_schema(self):
        '''
        Adds specific metadata fields
        '''
        schema = Unity.Schema.new()
        if EXTRA_METADATA:
            for m in EXTRA_METADATA:
                schema.add_field(m['id'], m['type'], m['field'])
        #FIXME should be REQUIRED for credits
        schema.add_field('provider_credits', 's', Unity.SchemaFieldType.OPTIONAL)
        return schema

    def do_get_categories(self):
        '''
        Adds categories
        '''
        cs = Unity.CategorySet.new()
        if CATEGORIES:
            for c in CATEGORIES:
                cat = Unity.Category.new(c['id'], c['name'],
                                         Gio.ThemedIcon.new(c['icon']),
                                         c['renderer'])
                cs.add(cat)
        return cs

    def do_get_filters(self):
        '''
        Adds filters
        '''
        fs = Unity.FilterSet.new()
#        if FILTERS:
#
        return fs

    def do_get_group_name(self):
        return GROUP_NAME

    def do_get_unique_name(self):
        return UNIQUE_PATH

    def do_create_search_for_query(self, search_context):
        se = MySearch(search_context)
        return se

    def do_activate(self, result, metadata, action):
        '''
        What to do when a resut is clicked
        '''
        return Unity.ActivationResponse(handled=Unity.HandledType.NOT_HANDLED, goto_uri=None)

    def do_create_previewer(self, result, metadata):
        '''
        Creates a preview when a resut is right-clicked
        '''
        result_preview = Preview()
        result_preview.set_scope_result(result)
        result_preview.set_search_metadata(metadata)
        return result_preview


def load_scope():
    return Scope()
