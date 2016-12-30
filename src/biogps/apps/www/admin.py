from django.contrib import admin
from django.contrib.auth import admin as user_admin
from django.contrib.auth.models import User

from biogps.apps.www.models import BiogpsTip, BiogpsInfobox, BiogpsAltLayout
from biogps.apps.plugin.models import BiogpsPlugin
from biogps.apps.layout.models import BiogpsGenereportLayout, BiogpsLayoutPlugin
from biogps.apps.genelist.models import BiogpsGeneList
from biogps.apps.auth2.models import UserProfile

#class BiogpsAnounceEmailListAdmin(admin.ModelAdmin):
#    pass
#admin.site.register(BiogpsAnounceEmailList, BiogpsAnounceEmailListAdmin)

def get_popularity_score(obj):
    return obj.popularity.score
get_popularity_score.short_description = 'popularity'

class LayoutInline(admin.TabularInline):
    model = BiogpsLayoutPlugin
    verbose_name = "Layout using this plugin"
    verbose_name_plural = "Layouts using this plugin"
    extra = 0
    readonly_fields=('layout', 'top', 'left', 'width', 'height')

def get_role_permission(obj):
    return '<br />'.join(obj.role_permission)
get_role_permission.short_description = 'Role Permission'
get_role_permission.allow_tags = True

def get_layout_cnt(obj):
    return obj.usage.count()
get_layout_cnt.short_description = 'no. of layouts using it'

class BiogpsPluginAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'type', get_layout_cnt, get_role_permission, 'options','lastmodified','created')
    list_filter = ('author',)
    search_fields = ['title', 'author', 'description']
    readonly_fields = ('species', 'options')
    list_select_related = True
    inlines = [LayoutInline,]
    raw_id_fields = ("ownerprofile",)
admin.site.register(BiogpsPlugin, BiogpsPluginAdmin)

class PluginsInline(admin.TabularInline):
    model = BiogpsLayoutPlugin
    verbose_name = "Plugin in this layout"
    verbose_name_plural = "Plugins used in this layout"
    extra = 0

def get_plugin_cnt(obj):
    return obj.plugins.count()
get_plugin_cnt.short_description = 'no. of plugins'

class BiogpsGenereportLayoutAdmin(admin.ModelAdmin):
    list_display = ('layout_name', 'author', get_plugin_cnt, get_role_permission, 'lastmodified','created')
    list_filter = ('author',)
    search_fields = ['layout_name', 'author']
    filter_horizontal = ('plugins',)
    inlines = [PluginsInline,]
admin.site.register(BiogpsGenereportLayout, BiogpsGenereportLayoutAdmin)

class BiogpsGeneListAdmin(admin.ModelAdmin):
    pass
admin.site.register(BiogpsGeneList, BiogpsGeneListAdmin)

class  BiogpsTipAdmin(admin.ModelAdmin):
    list_display = ('id', 'html')
admin.site.register(BiogpsTip, BiogpsTipAdmin)

class BiogpsInfoboxAdmin(admin.ModelAdmin):
    list_display = ('type', 'content', 'detail', 'options')
    list_filter = ('type',)

    # TinyMCE .js location
    class Media:
        js = ('js/tiny_mce/tiny_mce.js',)
admin.site.register(BiogpsInfobox, BiogpsInfoboxAdmin)

class BiogpsAltLayoutAdmin(admin.ModelAdmin):
    list_display = ('layout_name', 'layout_number')
    list_filter = ('layout_name',)
admin.site.register(BiogpsAltLayout, BiogpsAltLayoutAdmin)

class MyUserAdmin(user_admin.UserAdmin):
    #add two more fields, 'last_login', 'date_joined', to display and filtering.
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'last_login', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'last_login', 'date_joined')
#unregister default one and replace it by our own
admin.site.unregister(User)
admin.site.register(User, MyUserAdmin)


def get_user_username(userprofile):
    return userprofile.user.username
get_user_username.short_description = "username"
def get_user_full_name(userprofile):
    return userprofile.user.get_full_name()
get_user_full_name.short_description = "full name"
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [get_user_username, get_user_full_name, 'roles', 'affiliation']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    list_select_related = True
    readonly_fields = ('uiprofile',)

admin.site.register(UserProfile, UserProfileAdmin)
