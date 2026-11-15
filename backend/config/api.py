from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param


def extract_query_data(request) -> dict:
    return {
        key: value[0] if len(value) == 1 else value
        for key, value in request.query_params.lists()
    }


def paginate_queryset(request, queryset, *, page: int, page_size: int, serializer_cls):
    total_count = queryset.count()
    if total_count == 0:
        if page > 1:
            raise ValidationError(
                {"page": ["Сторінка виходить за межі наявних результатів."]}
            )
        return Response(
            {"count": 0, "next": None, "previous": None, "results": []},
            status=status.HTTP_200_OK,
        )
    offset = (page - 1) * page_size
    if offset >= total_count:
        raise ValidationError(
            {"page": ["Сторінка виходить за межі наявних результатів."]}
        )
    items = list(queryset[offset : offset + page_size])
    base_url = request.build_absolute_uri()
    return Response(
        {
            "count": total_count,
            "next": replace_query_param(base_url, "page", page + 1)
            if offset + page_size < total_count
            else None,
            "previous": None
            if page == 1
            else replace_query_param(base_url, "page", page - 1),
            "results": serializer_cls(items, many=True).data,
        },
        status=status.HTTP_200_OK,
    )
