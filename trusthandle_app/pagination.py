# pagination.py

from rest_framework.pagination import PageNumberPagination

class TenPerPagePagination(PageNumberPagination):
    page_size = 10