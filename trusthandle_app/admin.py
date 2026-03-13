from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Seller, Announcement, Category, Country, SystemConfig


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'full_name', 'role', 'is_verified', 'is_active', 'date_joined')
    list_filter = ('role', 'is_verified', 'is_active', 'date_joined')
    search_fields = ('email', 'full_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'role', 'is_verified')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2', 'role', 'is_verified'),
        }),
    )


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('name', 'currency_code', 'currency_name', 'rate_to_usd')
    search_fields = ('name', 'currency_code')
    ordering = ('name',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


class AnnouncementInline(admin.TabularInline):
    model = Announcement
    extra = 0
    readonly_fields = ('price_usd', 'created_at')
    fields = ('title', 'category', 'price_original', 'price_usd', 'followers', 'account_created_at', 'status', 'account_link', 'description')


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ('user', 'whatsapp', 'country', 'description')
    search_fields = ('whatsapp', 'user__email', 'user__full_name')
    list_filter = ('country',)
    inlines = [AnnouncementInline]


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'seller', 'category', 'price_original', 'price_usd', 'status', 'created_at')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('title', 'seller__user__email', 'seller__whatsapp')
    readonly_fields = ('price_usd', 'created_at')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    actions = ['mark_as_sold', 'mark_as_active', 'mark_as_inactive']
    
    @admin.action(description='Mark selected announcements as sold')
    def mark_as_sold(self, request, queryset):
        queryset.update(status='sold')
    
    @admin.action(description='Mark selected announcements as active')
    def mark_as_active(self, request, queryset):
        queryset.update(status='active')
    
    @admin.action(description='Mark selected announcements as inactive')
    def mark_as_inactive(self, request, queryset):
        queryset.update(status='inactive')


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ('is_ads_enabled',)
    verbose_name_plural = 'System Configuration'
    
    def has_add_permission(self, request):
        return not SystemConfig.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False