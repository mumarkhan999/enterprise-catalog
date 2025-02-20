from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework_xml.renderers import XMLRenderer

from enterprise_catalog.apps.api.v1.decorators import (
    require_at_least_one_query_parameter,
)
from enterprise_catalog.apps.api.v1.serializers import (
    EnterpriseCatalogSerializer,
)
from enterprise_catalog.apps.api.v1.utils import unquote_course_keys
from enterprise_catalog.apps.api.v1.views.base import BaseViewSet
from enterprise_catalog.apps.catalog.models import EnterpriseCatalog


class EnterpriseCatalogContainsContentItems(BaseViewSet, viewsets.ModelViewSet):
    """
    View to determine if an enterprise catalog contains certain content
    """
    queryset = EnterpriseCatalog.objects.all().order_by('created')
    renderer_classes = [JSONRenderer, XMLRenderer]
    serializer_class = EnterpriseCatalogSerializer
    permission_required = 'catalog.has_learner_access'
    lookup_field = 'uuid'

    def get_permission_object(self):
        """
        Retrieves the appropriate object to use during edx-rbac's permission checks.

        This object is passed to the rule predicate(s).
        """
        if self.kwargs.get('uuid'):
            enterprise_catalog = self.get_object()
            return str(enterprise_catalog.enterprise_uuid)
        return None

    @method_decorator(require_at_least_one_query_parameter('course_run_ids', 'program_uuids'))
    @action(detail=True)
    def contains_content_items(self, request, uuid, course_run_ids, program_uuids, **kwargs):  # pylint: disable=unused-argument
        """
        Returns whether or not the EnterpriseCatalog contains the specified content.

        Multiple course_run_ids and/or program_uuids query parameters can be sent to this view to check for their
        existence in the specified enterprise catalog.
        """
        course_run_ids = unquote_course_keys(course_run_ids)

        enterprise_catalog = self.get_object()
        contains_content_items = enterprise_catalog.contains_content_keys(course_run_ids + program_uuids)
        return Response({'contains_content_items': contains_content_items})
