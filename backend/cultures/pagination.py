from rest_framework.pagination import PageNumberPagination


class CulturePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 500
